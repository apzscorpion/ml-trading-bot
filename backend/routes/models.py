"""
Model management endpoints - training history, status, clearing models
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import os
import shutil
import logging

from backend.database import get_db, ModelTrainingRecord

router = APIRouter(prefix="/api/models", tags=["models"])
logger = logging.getLogger(__name__)


@router.get("/training-history")
async def get_training_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    bot_name: Optional[str] = Query(None, description="Filter by bot name"),
    limit: int = Query(100, description="Max records to return"),
    db: Session = Depends(get_db)
):
    """
    Get training history for all models.
    Shows when each model was trained, for which stock/timeframe.
    """
    query = db.query(ModelTrainingRecord)
    
    if symbol:
        query = query.filter(ModelTrainingRecord.symbol == symbol)
    if timeframe:
        query = query.filter(ModelTrainingRecord.timeframe == timeframe)
    if bot_name:
        query = query.filter(ModelTrainingRecord.bot_name == bot_name)
    
    # Only show active models by default
    query = query.filter(ModelTrainingRecord.status == 'active')
    
    # Order by most recent first
    query = query.order_by(desc(ModelTrainingRecord.trained_at)).limit(limit)
    
    records = query.all()
    
    return {
        "total": len(records),
        "records": [record.to_dict() for record in records]
    }


@router.get("/training-status")
async def get_training_status(
    db: Session = Depends(get_db)
):
    """
    Get current training status for all symbol/timeframe/bot combinations.
    Shows the latest training record for each unique combination.
    Optimized query for better performance.
    """
    try:
        # Get latest record for each symbol/timeframe/bot combination
        # More efficient query: get latest record for each combination
        # Using trained_at (indexed) to find latest, then fetch full records
        subquery = db.query(
            ModelTrainingRecord.symbol,
            ModelTrainingRecord.timeframe,
            ModelTrainingRecord.bot_name,
            func.max(ModelTrainingRecord.trained_at).label('latest_training')
        ).filter(
            ModelTrainingRecord.status == 'active'
        ).group_by(
            ModelTrainingRecord.symbol,
            ModelTrainingRecord.timeframe,
            ModelTrainingRecord.bot_name
        ).subquery()
        
        # Join back to get full records (optimized with indexed fields)
        records = db.query(ModelTrainingRecord).join(
            subquery,
            (ModelTrainingRecord.symbol == subquery.c.symbol) &
            (ModelTrainingRecord.timeframe == subquery.c.timeframe) &
            (ModelTrainingRecord.bot_name == subquery.c.bot_name) &
            (ModelTrainingRecord.trained_at == subquery.c.latest_training) &
            (ModelTrainingRecord.status == 'active')
        ).all()
        
        # Group by symbol and timeframe
        status_by_symbol = {}
        now = datetime.utcnow()
        
        for record in records:
            key = f"{record.symbol}_{record.timeframe}"
            if key not in status_by_symbol:
                status_by_symbol[key] = {
                    "symbol": record.symbol,
                    "timeframe": record.timeframe,
                    "models": []
                }
            
            # Calculate age
            age_hours = (now - record.trained_at).total_seconds() / 3600
            is_stale = age_hours > 24  # Consider stale if > 24 hours old
            
            status_by_symbol[key]["models"].append({
                "bot_name": record.bot_name,
                "trained_at": record.trained_at.isoformat(),
                "age_hours": round(age_hours, 1),
                "is_stale": is_stale,
                "data_points": record.data_points_used,
                "test_rmse": record.test_rmse,
                "test_mae": record.test_mae,
                "model_size_mb": record.model_size_mb,
                "status": "⚠️ Stale" if is_stale else "✅ Fresh"
            })
        
        return {
            "total_combinations": len(status_by_symbol),
            "status": list(status_by_symbol.values())
        }
    except Exception as e:
        logger.error(f"Error getting training status: {e}", exc_info=True)
        # Return empty status on error rather than failing
        return {
            "total_combinations": 0,
            "status": [],
            "error": str(e)
        }


@router.get("/report")
async def get_models_report(
    limit: int = Query(1000, description="Max models to return", ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """
    Comprehensive report of all models across all stocks and timeframes.
    Shows only the LATEST training record for each symbol/timeframe/bot combination.
    Optimized with limit to prevent timeout on large datasets.
    """
    try:
        # Get latest record for each symbol/timeframe/bot combination
        # This ensures we only show the most recent training for each model
        # Include both 'active' and 'completed' status (completed means training finished successfully)
        subquery = db.query(
            ModelTrainingRecord.symbol,
            ModelTrainingRecord.timeframe,
            ModelTrainingRecord.bot_name,
            func.max(ModelTrainingRecord.trained_at).label('latest_training')
        ).filter(
            ModelTrainingRecord.status.in_(['active', 'completed'])
        ).group_by(
            ModelTrainingRecord.symbol,
            ModelTrainingRecord.timeframe,
            ModelTrainingRecord.bot_name
        ).subquery()
        
        # Join back to get full records (only the latest for each combination)
        records = db.query(ModelTrainingRecord).join(
            subquery,
            (ModelTrainingRecord.symbol == subquery.c.symbol) &
            (ModelTrainingRecord.timeframe == subquery.c.timeframe) &
            (ModelTrainingRecord.bot_name == subquery.c.bot_name) &
            (ModelTrainingRecord.trained_at == subquery.c.latest_training) &
            (ModelTrainingRecord.status.in_(['active', 'completed']))
        ).order_by(
            desc(ModelTrainingRecord.trained_at)  # Most recent first
        ).limit(limit).all()
        
        # Statistics (using database aggregation for better performance)
        total_models_query = db.query(func.count(ModelTrainingRecord.id)).filter(
            ModelTrainingRecord.status.in_(['active', 'completed'])
        ).scalar() or 0
        
        # Get unique values efficiently
        symbols_query = db.query(ModelTrainingRecord.symbol).filter(
            ModelTrainingRecord.status.in_(['active', 'completed'])
        ).distinct().all()
        symbols = [s[0] for s in symbols_query]
        
        timeframes_query = db.query(ModelTrainingRecord.timeframe).filter(
            ModelTrainingRecord.status.in_(['active', 'completed'])
        ).distinct().all()
        timeframes = [t[0] for t in timeframes_query]
        
        bots_query = db.query(ModelTrainingRecord.bot_name).filter(
            ModelTrainingRecord.status.in_(['active', 'completed'])
        ).distinct().all()
        bots = [b[0] for b in bots_query]
        
        # Calculate staleness efficiently
        now = datetime.utcnow()
        stale_count = sum(1 for r in records if (now - r.trained_at).total_seconds() > 86400)
        fresh_count = len(records) - stale_count
        
        # Total storage (only for returned records)
        total_size_mb = sum(r.model_size_mb or 0 for r in records)
        
        return {
            "summary": {
                "total_models": total_models_query,  # Total in DB
                "returned_models": len(records),  # Actually returned
                "fresh_models": fresh_count,
                "stale_models": stale_count,
                "total_size_mb": round(total_size_mb, 2),
                "unique_symbols": len(symbols),
                "unique_timeframes": len(timeframes),
                "bot_types": len(bots)
            },
            "symbols": symbols,
            "timeframes": timeframes,
            "bots": bots,
            "models": [r.to_dict() for r in records]
        }
    except Exception as e:
        logger.error(f"Error getting models report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching models report: {str(e)}")


@router.delete("/clear/{symbol}/{timeframe}/{bot_name}")
async def clear_model(
    symbol: str,
    timeframe: str,
    bot_name: str,
    db: Session = Depends(get_db)
):
    """
    Clear/delete a specific trained model.
    Removes the model file and marks training record as archived.
    """
    try:
        # Find the model record
        record = db.query(ModelTrainingRecord).filter(
            ModelTrainingRecord.symbol == symbol,
            ModelTrainingRecord.timeframe == timeframe,
            ModelTrainingRecord.bot_name == bot_name,
            ModelTrainingRecord.status == 'active'
        ).order_by(desc(ModelTrainingRecord.trained_at)).first()
        
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"No active model found for {symbol}/{timeframe}/{bot_name}"
            )
        
        # Delete model file if it exists
        if record.model_path and os.path.exists(record.model_path):
            try:
                os.remove(record.model_path)
                logger.info(f"Deleted model file: {record.model_path}")
            except Exception as e:
                logger.warning(f"Could not delete model file: {e}")
        
        # Mark as archived
        record.status = 'archived'
        db.commit()
        
        return {
            "message": f"Model cleared: {bot_name} for {symbol}/{timeframe}",
            "status": "success",
            "model_id": record.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing model: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-all/{symbol}/{timeframe}")
async def clear_all_models_for_symbol_timeframe(
    symbol: str,
    timeframe: str,
    db: Session = Depends(get_db)
):
    """
    Clear ALL models for a specific symbol and timeframe.
    """
    try:
        records = db.query(ModelTrainingRecord).filter(
            ModelTrainingRecord.symbol == symbol,
            ModelTrainingRecord.timeframe == timeframe,
            ModelTrainingRecord.status == 'active'
        ).all()
        
        if not records:
            return {
                "message": f"No active models found for {symbol}/{timeframe}",
                "cleared_count": 0
            }
        
        cleared_count = 0
        for record in records:
            # Delete model file
            if record.model_path and os.path.exists(record.model_path):
                try:
                    os.remove(record.model_path)
                    logger.info(f"Deleted model file: {record.model_path}")
                except Exception as e:
                    logger.warning(f"Could not delete model file: {e}")
            
            # Mark as archived
            record.status = 'archived'
            cleared_count += 1
        
        db.commit()
        
        return {
            "message": f"Cleared all models for {symbol}/{timeframe}",
            "cleared_count": cleared_count,
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error clearing models: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-all/{symbol}")
async def clear_all_models_for_symbol(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    Clear ALL models for a specific symbol across ALL timeframes.
    Useful for clearing all models for a stock when retraining.
    """
    try:
        records = db.query(ModelTrainingRecord).filter(
            ModelTrainingRecord.symbol == symbol,
            ModelTrainingRecord.status == 'active'
        ).all()
        
        if not records:
            return {
                "message": f"No active models found for {symbol}",
                "cleared_count": 0
            }
        
        cleared_count = 0
        deleted_files = 0
        timeframes_cleared = set()
        
        for record in records:
            # Delete model file
            if record.model_path and os.path.exists(record.model_path):
                try:
                    os.remove(record.model_path)
                    deleted_files += 1
                    logger.info(f"Deleted model file: {record.model_path}")
                except Exception as e:
                    logger.warning(f"Could not delete model file: {e}")
            
            # Track timeframes
            timeframes_cleared.add(record.timeframe)
            
            # Mark as archived
            record.status = 'archived'
            cleared_count += 1
        
        db.commit()
        
        return {
            "message": f"Cleared all models for {symbol}",
            "cleared_count": cleared_count,
            "deleted_files": deleted_files,
            "timeframes_cleared": list(timeframes_cleared),
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error clearing models for symbol {symbol}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-all")
async def clear_all_models(
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    db: Session = Depends(get_db)
):
    """
    ⚠️ DANGER: Clear ALL trained models across all symbols and timeframes.
    Requires confirmation parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to clear all models"
        )
    
    try:
        records = db.query(ModelTrainingRecord).filter(
            ModelTrainingRecord.status == 'active'
        ).all()
        
        cleared_count = 0
        deleted_files = 0
        
        for record in records:
            # Delete model file
            if record.model_path and os.path.exists(record.model_path):
                try:
                    os.remove(record.model_path)
                    deleted_files += 1
                except Exception as e:
                    logger.warning(f"Could not delete model file: {e}")
            
            # Mark as archived
            record.status = 'archived'
            cleared_count += 1
        
        db.commit()
        
        return {
            "message": "Cleared all trained models",
            "cleared_count": cleared_count,
            "deleted_files": deleted_files,
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error clearing all models: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot-types")
async def get_available_bot_types():
    """
    Get list of all available bot types that can be trained.
    """
    return {
        "bots": [
            {
                "name": "rsi_bot",
                "type": "technical",
                "description": "RSI-based technical indicator bot",
                "requires_training": False
            },
            {
                "name": "macd_bot",
                "type": "technical",
                "description": "MACD-based technical indicator bot",
                "requires_training": False
            },
            {
                "name": "ma_bot",
                "type": "technical",
                "description": "Moving Average crossover bot",
                "requires_training": False
            },
            {
                "name": "ml_bot",
                "type": "machine_learning",
                "description": "Random Forest regression bot",
                "requires_training": True
            },
            {
                "name": "lstm_bot",
                "type": "deep_learning",
                "description": "LSTM neural network bot",
                "requires_training": True
            },
            {
                "name": "transformer_bot",
                "type": "deep_learning",
                "description": "Transformer neural network bot",
                "requires_training": True
            },
            {
                "name": "ensemble_bot",
                "type": "ensemble",
                "description": "Ensemble of ML models",
                "requires_training": True
            }
        ]
    }


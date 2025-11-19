"""
Prediction endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import time
import os
import logging

from backend.database import get_db, Prediction, Candle, ModelTrainingRecord
from backend.ml.training import TrainingOrchestrator
from backend.freddy_merger import freddy_merger
from backend.utils.data_fetcher import data_fetcher
from backend.websocket_manager import manager
import asyncio
from backend.services.candle_loader import candle_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prediction", tags=["prediction"])

# Model freshness threshold - models older than this will trigger auto-training
MODEL_STALE_THRESHOLD_HOURS = 24


def determine_prediction_type(selected_bots: Optional[List[str]]) -> str:
    """
    Determine prediction type based on selected bots.
    
    Returns:
        "technical" - RSI, MACD, MA bots
        "ml" - ML bot, Ensemble bot
        "lstm" - LSTM bot only
        "transformer" - Transformer bot only
        "deep_learning" - Both LSTM and Transformer
        "ensemble" - All bots or no specific selection
        "all" - All bots explicitly selected
    """
    if not selected_bots or len(selected_bots) == 0:
        return "ensemble"
    
    selected_bots_set = set(selected_bots)
    
    # Technical analysis bots
    technical_bots = {"rsi_bot", "macd_bot", "ma_bot"}
    # ML bots
    ml_bots = {"ml_bot", "ensemble_bot"}
    # Deep learning bots
    dl_bots = {"lstm_bot", "transformer_bot"}
    
    # Check if only technical bots
    if selected_bots_set.issubset(technical_bots) and len(selected_bots_set) > 0:
        return "technical"
    
    # Check if only ML bots (but not all bots)
    if selected_bots_set.issubset(ml_bots) and not selected_bots_set.intersection(dl_bots) and not selected_bots_set.intersection(technical_bots):
        return "ml"
    
    # Check if only LSTM
    if selected_bots_set == {"lstm_bot"}:
        return "lstm"
    
    # Check if only Transformer
    if selected_bots_set == {"transformer_bot"}:
        return "transformer"
    
    # Check if both LSTM and Transformer (but not all bots)
    if selected_bots_set.issubset(dl_bots) and len(selected_bots_set) == 2:
        return "deep_learning"
    
    # If all bots or mixed selection, return "ensemble"
    all_bots = technical_bots | ml_bots | dl_bots
    if selected_bots_set == all_bots or len(selected_bots_set) >= 5:
        return "all"
    
    return "ensemble"


class PredictionRequest(BaseModel):
    symbol: str
    timeframe: str = "5m"
    horizon_minutes: int = 180
    force_refresh: bool = False
    selected_bots: Optional[List[str]] = None  # List of bot names to use


class TrainRequest(BaseModel):
    symbol: str
    timeframe: str = "5m"
    bot_name: str  # Which bot to train
    epochs: int = 50  # For deep learning models
    batch_size: int = 200  # Number of candles per batch for incremental training
    families: Optional[List[str]] = None  # For orchestrator-based training


async def check_and_trigger_training_if_stale(symbol: str, timeframe: str, db: Session):
    """
    Check if models are stale and trigger training in background if needed.
    This runs asynchronously and doesn't block prediction generation.
    """
    try:
        # Get trainable bots (LSTM, Transformer, ML, Ensemble)
        trainable_bots = ['lstm_bot', 'transformer_bot', 'ml_bot', 'ensemble_bot']
        
        # Check each trainable bot
        for bot_name in trainable_bots:
            # Get latest training record for this symbol/timeframe/bot
            latest_training = db.query(ModelTrainingRecord).filter(
                ModelTrainingRecord.symbol == symbol,
                ModelTrainingRecord.timeframe == timeframe,
                ModelTrainingRecord.bot_name == bot_name,
                ModelTrainingRecord.status.in_(['completed', 'active'])
            ).order_by(ModelTrainingRecord.trained_at.desc()).first()
            
            # Check if model is stale or doesn't exist
            is_stale = False
            if not latest_training:
                is_stale = True
                logger.info(f"No training record found for {bot_name} {symbol}/{timeframe}, will trigger training")
            else:
                age_hours = (datetime.utcnow() - latest_training.trained_at).total_seconds() / 3600
                if age_hours > MODEL_STALE_THRESHOLD_HOURS:
                    is_stale = True
                    logger.info(f"Model {bot_name} {symbol}/{timeframe} is stale ({age_hours:.1f}h old), will trigger training")
            
            # Trigger training in background if stale
            if is_stale:
                # Check if training is already running for this combination
                existing_training = db.query(ModelTrainingRecord).filter(
                    ModelTrainingRecord.symbol == symbol,
                    ModelTrainingRecord.timeframe == timeframe,
                    ModelTrainingRecord.bot_name == bot_name,
                    ModelTrainingRecord.status.in_(['queued', 'running'])
                ).first()
                
                if not existing_training:
                    logger.info(f"Triggering auto-training for {bot_name} {symbol}/{timeframe}")
                    
                    # Create training request
                    train_request = TrainRequest(
                        symbol=symbol,
                        timeframe=timeframe,
                        bot_name=bot_name,
                        epochs=50,
                        batch_size=200
                    )
                    
                    # Trigger training in background (non-blocking)
                    asyncio.create_task(train_bot_background(train_request, db))
                    
    except Exception as e:
        logger.error(f"Error checking model freshness: {e}", exc_info=True)
        # Don't fail prediction if freshness check fails


async def train_bot_background(request: TrainRequest, db: Session):
    """
    Wrapper to trigger training in background without blocking.
    """
    try:
        # Create a new DB session for background task
        from backend.database import SessionLocal
        bg_db = SessionLocal()
        try:
            # Call the train_bot endpoint logic
            await train_bot(request, bg_db)
        finally:
            bg_db.close()
    except Exception as e:
        logger.error(f"Background training failed: {e}", exc_info=True)


class PredictionRequest(BaseModel):
    symbol: str
    timeframe: str = "5m"
    horizon_minutes: int = 180
    force_refresh: bool = False
    selected_bots: Optional[List[str]] = None  # List of bot names to use


@router.post("/trigger")
async def trigger_prediction(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger a new prediction for a symbol.
    Automatically triggers training if models are stale (>24 hours old).
    """
    # Check model freshness and trigger training if needed (non-blocking)
    await check_and_trigger_training_if_stale(request.symbol, request.timeframe, db)
    
    # Fetch recent candles from DB (get more to ensure enough valid data)
    # ML bot needs 100, LSTM needs 60, Transformer needs 50, Ensemble needs 40
    # Fetch 500 to ensure we have enough even after filtering
    candles = db.query(Candle).filter(
        Candle.symbol == request.symbol,
        Candle.timeframe == request.timeframe
    ).order_by(Candle.start_ts.desc()).limit(500).all()
    
    if not candles:
        # Fetch from Yahoo Finance
        period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "4h": "3mo", "1d": "2y", "1wk": "5y", "1mo": "10y"}
        period = period_map.get(request.timeframe, "5d")
        
        fetched_candles = await data_fetcher.fetch_candles(
            symbol=request.symbol,
            interval=request.timeframe,
            period=period
        )
        
        if not fetched_candles:
            raise HTTPException(status_code=404, detail="No data available for symbol")
        
        # Store in DB
        for candle_data in fetched_candles:
            # Convert start_ts from ISO string to datetime if needed
            candle_dict = candle_data.copy()
            if isinstance(candle_dict.get('start_ts'), str):
                candle_dict['start_ts'] = datetime.fromisoformat(
                    candle_dict['start_ts'].replace('Z', '+00:00')
                )
            candle = Candle(
                symbol=request.symbol,
                timeframe=request.timeframe,
                **candle_dict
            )
            db.add(candle)
        
        db.commit()
        candles_list = fetched_candles
    else:
        candles_list = [c.to_dict() for c in reversed(candles)]
    
    # Run Freddy prediction
    result = await freddy_merger.predict(
        symbol=request.symbol,
        candles=candles_list,
        horizon_minutes=request.horizon_minutes,
        timeframe=request.timeframe,
        selected_bots=request.selected_bots
    )
    
    # Determine prediction type from selected bots
    prediction_type = determine_prediction_type(request.selected_bots)
    
    # Check if prediction_type column exists in database (for backward compatibility)
    has_prediction_type_column = False
    try:
        # Check if column exists by querying table info
        from sqlalchemy import inspect
        from backend.database import engine
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('predictions')]
        has_prediction_type_column = 'prediction_type' in columns
    except Exception as e:
        # If inspection fails, assume column doesn't exist (safer)
        logger.debug(f"Could not check for prediction_type column: {e}")
        has_prediction_type_column = False
    
    # Store prediction in DB with enhanced audit fields
    prediction_data = {
        "symbol": result["symbol"],
        "produced_at": datetime.fromisoformat(result["produced_at"].replace('Z', '+00:00')),
        "horizon_minutes": result["horizon_minutes"],
        "timeframe": result["timeframe"],
        "predicted_series": result["predicted_series"],
        "confidence": result["overall_confidence"],
        "bot_contributions": result["bot_contributions"],
        "trend": result.get("trend"),
        "bot_raw_outputs": result.get("bot_raw_outputs"),
        "validation_flags": result.get("validation_flags"),
        "feature_snapshot": result.get("feature_snapshot"),
    }
    
    # Only add prediction_type if column exists
    if has_prediction_type_column:
        prediction_data["prediction_type"] = prediction_type
    else:
        logger.warning("prediction_type column does not exist yet. Run migration or restart server.")
    
    prediction = Prediction(**prediction_data)
    
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    
    return {
        "prediction_id": prediction.id,
        "status": "completed",
        "result": result
    }


@router.get("/latest")
async def get_latest_prediction(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    db: Session = Depends(get_db)
):
    """Get the latest prediction for a symbol"""
    prediction = db.query(Prediction).filter(
        Prediction.symbol == symbol,
        Prediction.timeframe == timeframe
    ).order_by(Prediction.produced_at.desc()).first()
    
    if not prediction:
        return {"error": "No predictions available", "symbol": symbol}
    
    return prediction.to_dict()


@router.get("/{prediction_id}")
async def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific prediction by ID"""
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    return prediction.to_dict()


@router.get("/history/all")
async def get_prediction_history(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    limit: int = Query(50, description="Number of predictions to return"),
    prediction_type: Optional[str] = Query(None, description="Filter by prediction type (technical, ml, lstm, transformer, deep_learning, ensemble, all)"),
    db: Session = Depends(get_db)
):
    """Get historical predictions for a symbol, optionally filtered by prediction type"""
    query = db.query(Prediction).filter(
        Prediction.symbol == symbol,
        Prediction.timeframe == timeframe
    )
    
    if prediction_type:
        query = query.filter(Prediction.prediction_type == prediction_type)
    
    predictions = query.order_by(Prediction.produced_at.desc()).limit(limit).all()
    
    return [p.to_dict() for p in predictions]


@router.get("/history/by-type")
async def get_prediction_history_by_type(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    limit_per_type: int = Query(10, description="Number of predictions per type to return"),
    db: Session = Depends(get_db)
):
    """Get historical predictions grouped by prediction type"""
    prediction_types = ["technical", "ml", "lstm", "transformer", "deep_learning", "ensemble", "all"]
    
    result = {}
    for pred_type in prediction_types:
        predictions = db.query(Prediction).filter(
            Prediction.symbol == symbol,
            Prediction.timeframe == timeframe,
            Prediction.prediction_type == pred_type
        ).order_by(Prediction.produced_at.desc()).limit(limit_per_type).all()
        
        if predictions:
            result[pred_type] = [p.to_dict() for p in predictions]
    
    return result


@router.get("/bots/available")
async def get_available_bots():
    """Get list of available prediction bots"""
    return {
        "bots": [
            {"name": "rsi_bot", "display_name": "RSI Bot", "type": "technical"},
            {"name": "macd_bot", "display_name": "MACD Bot", "type": "technical"},
            {"name": "ma_bot", "display_name": "Moving Average Bot", "type": "technical"},
            {"name": "ml_bot", "display_name": "ML Bot (Prophet)", "type": "ml"},
            {"name": "lstm_bot", "display_name": "LSTM Deep Learning", "type": "deep_learning"},
            {"name": "transformer_bot", "display_name": "Transformer", "type": "deep_learning"},
            {"name": "ensemble_bot", "display_name": "Ensemble ML", "type": "ml"}
        ]
    }


async def train_bot_incremental(
    bot,
    candles_list: List[Dict],
    training_record: ModelTrainingRecord,
    epochs: int,
    batch_size: int,
    db: Session
):
    """Train bot incrementally in batches and emit progress updates"""
    try:
        if not candles_list:
            raise ValueError("No candles supplied for incremental training")

        # Sort candles by start_ts ascending (oldest first)
        candles_list = sorted(candles_list, key=lambda x: x.get('start_ts', ''))
        
        # Split into batches
        total_batches = (len(candles_list) + batch_size - 1) // batch_size
        training_record.total_batches = total_batches
        training_record.status = 'running'
        db.commit()
        logger.info(
            "Starting incremental training",
            extra={
                "bot": training_record.bot_name,
                "symbol": training_record.symbol,
                "timeframe": training_record.timeframe,
                "epochs": epochs,
                "batch_size": batch_size,
                "data_points": len(candles_list),
                "total_batches": total_batches,
            },
        )
        
        # Initialize accumulated data for incremental training
        accumulated_candles = []
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(candles_list))
            batch_candles = candles_list[start_idx:end_idx]
            
            # Accumulate candles (include previous batches)
            accumulated_candles.extend(batch_candles)
            
            # Update progress
            progress_percent = ((batch_num + 1) / total_batches) * 100
            training_record.current_batch = batch_num + 1
            training_record.progress_percent = progress_percent
            training_record.progress_message = f"Training batch {batch_num + 1}/{total_batches} ({len(accumulated_candles)} candles)"
            db.commit()
            
            # Emit progress via WebSocket
            await manager.broadcast_training_progress({
                "training_id": training_record.id,
                "bot_name": training_record.bot_name,
                "symbol": training_record.symbol,
                "timeframe": training_record.timeframe,
                "batch": batch_num + 1,
                "total_batches": total_batches,
                "progress_percent": progress_percent,
                "status": "running",
                "message": training_record.progress_message
            })
            
            # Train on accumulated data (for incremental learning)
            # Note: For some models, we might want to train only on the batch
            # For now, we'll train on all accumulated data for better learning
            result = await bot.train(accumulated_candles, epochs=epochs)
            
            if isinstance(result, dict) is False:
                raise ValueError("Training result must be a dictionary")

            if "error" in result:
                raise ValueError(result["error"])
            
            logger.info(f"Batch {batch_num + 1}/{total_batches} completed for {training_record.bot_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"Incremental training failed: {e}", exc_info=True)
        raise


@router.post("/train")
async def train_bot(
    request: TrainRequest,
    db: Session = Depends(get_db)
):
    """Train a specific bot on historical data (runs in background with progress updates)"""
    start_time = time.time()
    period = None
    
    # Multi-family orchestrator path
    if request.bot_name == "orchestrator":
        orchestrator = TrainingOrchestrator()
        try:
            result = orchestrator.train(
                symbol=request.symbol,
                timeframe=request.timeframe,
                families=request.families,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - safeguard
            logger.error("Orchestrator training failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Orchestrator training failed") from exc

        return {
            "status": "completed",
            "experiment_id": result.experiment_id,
            "metrics": result.metrics,
            "artifacts": result.artifacts,
        }

    try:
        period_map = {
            "1m": "60d",
            "5m": "60d",
            "15m": "60d",
            "1h": "730d",
            "4h": "730d",
            "1d": "2000d",
            "1wk": "max",
            "1mo": "max",
        }
        fallback_period = period_map.get(request.timeframe, "60d")

        candles_list = await candle_loader.load_recent_rows(
            symbol=request.symbol,
            timeframe=request.timeframe,
            rows=5000,
            fallback_period=fallback_period,
            min_points=500,
            bypass_cache=True,
        )

        if not candles_list:
            raise HTTPException(status_code=404, detail="No data available for training")

        data_points = len(candles_list)
        dataset_start = candles_list[0].get("start_ts") if candles_list else None
        dataset_end = candles_list[-1].get("start_ts") if candles_list else None
        min_required = max(request.batch_size * 2, 200)

        if data_points < min_required:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough historical candles for training (required {min_required}, got {data_points})",
            )

        logger.info(
            "Prepared training dataset",
            extra={
                "bot": request.bot_name,
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "rows": data_points,
                "window_start": dataset_start,
                "window_end": dataset_end,
            },
        )

        period = f"{data_points} candles ({dataset_start} → {dataset_end})"
        
        # Get the bot
        bot = freddy_merger.available_bots.get(request.bot_name)
        if not bot:
            raise HTTPException(status_code=404, detail=f"Bot {request.bot_name} not found")
        
        # Set model context for timeframe-specific models
        bot.set_model_context(request.symbol, request.timeframe)
        
        # Reload model with new context (will load timeframe-specific model if exists)
        if hasattr(bot, '_load_or_create_model'):
            bot._load_or_create_model()
        elif hasattr(bot, '_load_or_create_models'):
            bot._load_or_create_models()
        
        # Train the bot
        if not hasattr(bot, 'train'):
            return {
                "bot_name": request.bot_name,
                "status": "not_trainable",
                "message": f"{request.bot_name} does not support training"
            }
        
        # Create training record with queued status
        training_context = {
            "epochs": request.epochs,
            "period": period or "unknown",
            "batch_size": request.batch_size,
            "data_points": data_points,
            "window_start": dataset_start,
            "window_end": dataset_end,
        }

        training_record = ModelTrainingRecord(
            symbol=request.symbol,
            timeframe=request.timeframe,
            bot_name=request.bot_name,
            trained_at=datetime.utcnow(),
            status='queued',
            epochs=request.epochs,
            config=training_context
        )
        training_record.total_batches = max(1, (data_points + request.batch_size - 1) // request.batch_size)
        training_record.current_batch = 0
        training_record.progress_percent = 0.0
        db.add(training_record)
        db.commit()
        db.refresh(training_record)
        
        # Return training_id immediately (non-blocking)
        training_id = training_record.id
        
        # Start training in background
        async def background_training():
            # Create new DB session for background task
            bg_db = next(get_db())
            try:
                # Refresh training record in new session
                training_record_refreshed = bg_db.query(ModelTrainingRecord).filter(
                    ModelTrainingRecord.id == training_id
                ).first()
                
                if not training_record_refreshed:
                    logger.error(f"Training record {training_id} not found")
                    return
                
                # Train incrementally
                result = await train_bot_incremental(
                    bot=bot,
                    candles_list=candles_list,
                    training_record=training_record_refreshed,
                    epochs=request.epochs,
                    batch_size=request.batch_size,
                    db=bg_db
                )
                
                # Calculate training duration
                duration = time.time() - start_time
                
                # Get model file size
                model_size = 0.0
                if hasattr(bot, 'model_path') and bot.model_path and os.path.exists(bot.model_path):
                    model_size = os.path.getsize(bot.model_path) / (1024 * 1024)  # MB
                
                # Extract performance metrics
                training_loss = result.get("training_loss") or result.get("final_loss") or None
                test_rmse = result.get("test_rmse") or result.get("final_loss") or None
                test_mae = result.get("test_mae") or result.get("final_mae") or None
                validation_loss = result.get("validation_loss")
                
                # Update training record
                training_record_refreshed.training_duration_seconds = duration
                training_record_refreshed.data_points_used = len(candles_list)
                training_record_refreshed.training_period = period or "unknown"
                training_record_refreshed.training_loss = training_loss
                training_record_refreshed.validation_loss = validation_loss
                training_record_refreshed.test_rmse = test_rmse
                training_record_refreshed.test_mae = test_mae
                training_record_refreshed.model_path = bot.model_path if hasattr(bot, 'model_path') else None
                training_record_refreshed.model_size_mb = model_size
                training_record_refreshed.status = 'completed'
                training_record_refreshed.progress_percent = 100.0
                training_record_refreshed.progress_message = "Training completed successfully"
                bg_db.commit()
                
                # Emit completion
                await manager.broadcast_training_progress({
                    "training_id": training_id,
                    "bot_name": request.bot_name,
                    "symbol": request.symbol,
                    "timeframe": request.timeframe,
                    "batch": training_record.total_batches,
                    "total_batches": training_record.total_batches,
                    "progress_percent": 100.0,
                    "status": "completed",
                    "message": "Training completed successfully"
                })
                
                logger.info(f"Training completed: {request.bot_name} for {request.symbol}/{request.timeframe}")
                
            except Exception as e:
                logger.error(f"Background training failed: {e}", exc_info=True)
                training_record_refreshed.status = 'failed'
                training_record_refreshed.error_message = str(e)
                training_record_refreshed.progress_message = f"Training failed: {str(e)}"
                bg_db.commit()
                
                # Emit failure
                await manager.broadcast_training_progress({
                    "training_id": training_id,
                    "bot_name": request.bot_name,
                    "symbol": request.symbol,
                    "timeframe": request.timeframe,
                    "batch": training_record_refreshed.current_batch,
                    "total_batches": training_record_refreshed.total_batches,
                    "progress_percent": training_record_refreshed.progress_percent,
                    "status": "failed",
                    "message": f"Training failed: {str(e)}"
                })
            finally:
                bg_db.close()
        
        # Start background task
        asyncio.create_task(background_training())
        
        return {
            "bot_name": request.bot_name,
            "status": "queued",
            "training_id": training_id,
            "message": "Training started in background. Progress will be sent via WebSocket."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training failed for {request.bot_name} {request.symbol}/{request.timeframe}: {e}", exc_info=True)
        
        # Create failed record
        try:
            training_record = ModelTrainingRecord(
                symbol=request.symbol,
                timeframe=request.timeframe,
                bot_name=request.bot_name,
                trained_at=datetime.utcnow(),
                training_duration_seconds=time.time() - start_time,
                status='failed',
                error_message=str(e)
            )
            db.add(training_record)
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to create training record: {db_error}")
        
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


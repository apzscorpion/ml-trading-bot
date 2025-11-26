"""
Training management endpoints - start, stop, pause training
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import asyncio
import logging

from backend.database import get_db, ModelTrainingRecord
from backend.freddy_merger import freddy_merger
from backend.ml.training import TrainingOrchestrator
from backend.services.training_manager import training_manager
from backend.websocket_manager import manager

router = APIRouter(prefix="/api/training", tags=["training"])
logger = logging.getLogger(__name__)


class StartAutoTrainingRequest(BaseModel):
    symbols: List[str]
    timeframes: List[str]
    bots: List[str]


class WalkForwardValidationRequest(BaseModel):
    symbol: str
    timeframe: str = "5m"
    families: Optional[List[str]] = None
    dataset_version: Optional[str] = None
    alert_threshold_pct: float = 0.02

# Global training state
training_state = {
    "is_running": False,
    "is_paused": False,
    "current_training": None,  # {symbol, timeframe, bot_name, started_at}
    "queue": [],  # Queue of training tasks
    "completed": [],  # Completed training tasks
    "failed": []  # Failed training tasks
}


@router.get("/status")
async def get_training_status():
    """Get current training status"""
    try:
        return {
            "is_running": training_state["is_running"],
            "is_paused": training_state["is_paused"],
            "current_training": training_state["current_training"],
            "queue_length": len(training_state["queue"]),
            "completed_count": len(training_state["completed"]),
            "failed_count": len(training_state["failed"])
        }
    except Exception as e:
        logger.error(f"Error getting training status: {e}", exc_info=True)
        return {
            "is_running": False,
            "is_paused": False,
            "current_training": None,
            "queue_length": 0,
            "completed_count": 0,
            "failed_count": 0,
            "error": str(e)
        }


@router.post("/start-auto")
async def start_auto_training(
    request: StartAutoTrainingRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Start automatic training for multiple symbol/timeframe/bot combinations.
    Creates a queue and processes them sequentially.
    Returns immediately after queuing the background tasks.
    """
    if training_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="Training is already running. Stop it first."
        )
    
    # Build training queue
    queue = []
    for symbol in request.symbols:
        for timeframe in request.timeframes:
            for bot_name in request.bots:
                queue.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "bot_name": bot_name,
                    "status": "pending"
                })
    
    training_state["queue"] = queue
    training_state["is_running"] = True
    training_state["is_paused"] = False
    
    # Start background training process
    # Don't pass db session - create new one in background task
    background_tasks.add_task(process_training_queue)
    
    # Set response headers to ensure immediate response
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.status_code = 200
    
    logger.info(f"Auto-training started with {len(queue)} tasks - returning immediately")
    
    return {
        "message": f"Auto-training started with {len(queue)} tasks",
        "queue_size": len(queue),
        "status": "running"
    }


@router.post("/pause")
async def pause_training():
    """Pause automatic training (doesn't stop current task)"""
    if not training_state["is_running"]:
        raise HTTPException(status_code=400, detail="Training is not running")
    
    training_state["is_paused"] = True
    
    return {
        "message": "Training paused",
        "status": "paused",
        "current_task": training_state["current_training"]
    }


@router.post("/resume")
async def resume_training(background_tasks: BackgroundTasks):
    """Resume automatic training"""
    if training_state["is_running"] and not training_state["is_paused"]:
        raise HTTPException(status_code=400, detail="Training is already running")
    
    training_state["is_paused"] = False
    
    # Restart processing if queue has items
    if training_state["queue"]:
        background_tasks.add_task(process_training_queue)
    
    return {
        "message": "Training resumed",
        "status": "running",
        "queue_size": len(training_state["queue"])
    }


@router.post("/stop")
async def stop_training():
    """Stop automatic training (clears queue, stops after current task)"""
    training_state["is_running"] = False
    training_state["is_paused"] = False
    
    # Clear queue (but let current task finish)
    cleared_count = len(training_state["queue"])
    training_state["queue"] = []
    
    return {
        "message": "Training stopped. Current task will finish.",
        "status": "stopped",
        "cleared_tasks": cleared_count
    }


@router.post("/force-stop")
async def force_stop_training():
    """Force stop training immediately (may interrupt current task)"""
    training_state["is_running"] = False
    training_state["is_paused"] = False
    training_state["queue"] = []
    training_state["current_training"] = None
    
    return {
        "message": "Training force stopped",
        "status": "stopped"
    }


@router.post("/stop/{training_id}")
async def stop_training_by_id(
    training_id: int,
    reason: Optional[str] = "user_requested",
    db: Session = Depends(get_db)
):
    """
    Stop/cancel a specific training session by ID.
    Emergency stop functionality.
    """
    try:
        success = await training_manager.request_cancellation(training_id, reason)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Training {training_id} not found or already completed"
            )
        
        return {
            "status": "cancelled",
            "training_id": training_id,
            "message": f"Training cancellation requested: {reason}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping training: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop training: {str(e)}")


@router.get("/status/{training_id}")
async def get_training_status_by_id(
    training_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed status of a specific training session"""
    record = db.query(ModelTrainingRecord).filter(
        ModelTrainingRecord.id == training_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Training not found")
    
    return record.to_dict()


@router.get("/history")
async def get_training_history(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    bot_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get training history with optional filters"""
    query = db.query(ModelTrainingRecord)
    
    if symbol:
        query = query.filter(ModelTrainingRecord.symbol == symbol)
    if timeframe:
        query = query.filter(ModelTrainingRecord.timeframe == timeframe)
    if bot_name:
        query = query.filter(ModelTrainingRecord.bot_name == bot_name)
    if status:
        query = query.filter(ModelTrainingRecord.status == status)
    
    records = query.order_by(ModelTrainingRecord.trained_at.desc()).limit(limit).all()
    
    return [record.to_dict() for record in records]


@router.get("/models/status")
async def get_models_status(
    symbol: str,
    timeframe: str = "5m",
    db: Session = Depends(get_db)
):
    """Get status of all models for a symbol/timeframe"""
    model_statuses = await training_manager.get_model_status(symbol, timeframe)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "models": model_statuses,
        "active_trainings": training_manager.get_active_trainings()
    }


@router.get("/active")
async def get_active_trainings():
    """Get all currently active training sessions"""
    return {
        "active_trainings": training_manager.get_active_trainings(),
        "count": len(training_manager.active_trainings)
    }


@router.post("/validate/walk-forward")
async def walk_forward_validation(request: WalkForwardValidationRequest):
    """Run walk-forward validation for the specified symbol/timeframe."""
    orchestrator = TrainingOrchestrator()
    try:
        result = orchestrator.walk_forward_validate(
            symbol=request.symbol,
            timeframe=request.timeframe,
            families=request.families,
            dataset_version=request.dataset_version,
            alert_threshold_pct=request.alert_threshold_pct,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguard
        logger.error("Walk-forward validation failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Validation run failed") from exc


async def process_training_queue():
    """Process training queue sequentially with deduplication"""
    from backend.database import SessionLocal
    
    # Create a new database session for this background task
    db = SessionLocal()
    
    try:
        while training_state["is_running"] and training_state["queue"]:
            # Check if paused
            while training_state["is_paused"]:
                await asyncio.sleep(1)
            
            if not training_state["is_running"]:
                break
            
            # Get next task
            task = training_state["queue"].pop(0)
            
            # Check if a training job is already running for this combination
            existing_running = db.query(ModelTrainingRecord).filter(
                ModelTrainingRecord.symbol == task["symbol"],
                ModelTrainingRecord.timeframe == task["timeframe"],
                ModelTrainingRecord.bot_name == task["bot_name"],
                ModelTrainingRecord.status.in_(['queued', 'running'])
            ).first()
            
            if existing_running:
                logger.warning(
                    f"Skipping duplicate training for {task['bot_name']} "
                    f"{task['symbol']}/{task['timeframe']} - already running (ID: {existing_running.id})"
                )
                training_state["failed"].append({
                    **task,
                    "skipped_at": datetime.utcnow().isoformat(),
                    "reason": "duplicate_running"
                })
                continue
            
            training_state["current_training"] = {
                **task,
                "started_at": datetime.utcnow().isoformat()
            }
            
            try:
                # Get the bot from freddy_merger
                bot = freddy_merger.available_bots.get(task["bot_name"])
                if not bot:
                    raise ValueError(f"Bot {task['bot_name']} not found")
                
                if not hasattr(bot, 'train'):
                    raise ValueError(f"Bot {task['bot_name']} does not support training")
                
                # Call training method
                result = await train_model_async(
                    bot=bot,
                    symbol=task["symbol"],
                    timeframe=task["timeframe"],
                    db=db
                )
                
                # Mark as completed
                training_state["completed"].append({
                    **task,
                    "completed_at": datetime.utcnow().isoformat(),
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Training failed for {task}: {e}")
                training_state["failed"].append({
                    **task,
                    "failed_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                })
            
            finally:
                training_state["current_training"] = None
        
        # Training finished
        training_state["is_running"] = False
    finally:
        # Close database session
        db.close()


async def train_model_async(bot, symbol: str, timeframe: str, db: Session):
    """Async wrapper for model training"""
    import time
    from backend.utils.data_fetcher import data_fetcher
    from backend.database import ModelTrainingRecord
    
    start_time = time.time()
    
    try:
        # Get training data
        # Note: Yahoo Finance limits:
        # - 4h data: max 730 days
        # - 1h data: max 730 days
        # - Other timeframes have different limits
        period_map = {
            "1m": "5d", "5m": "60d", "15m": "60d", 
            "1h": "730d",  # Yahoo Finance max for 1h
            "4h": "730d",   # Yahoo Finance max for 4h (not 1000d!)
            "1d": "2000d", "5d": "2000d",
            "1wk": "5y", "1mo": "10y", "3mo": "10y"
        }
        period = period_map.get(timeframe, "60d")
        
        candles = await data_fetcher.fetch_candles(symbol, timeframe, period)
        
        if not candles or len(candles) < 100:
            raise ValueError(f"Not enough data: {len(candles) if candles else 0} candles")
        
        # Train the model
        # Only pass epochs if bot accepts it (deep learning bots)
        epochs = 30 if 'transformer' in bot.name else 50
        import inspect
        train_signature = inspect.signature(bot.train)
        if 'epochs' in train_signature.parameters:
            result = await bot.train(candles, epochs=epochs)
        else:
            # For bots that don't use epochs (e.g., ensemble_bot)
            result = await bot.train(candles)
        
        if "error" in result:
            raise ValueError(result["error"])
        
        # Calculate training duration
        duration = time.time() - start_time
        
        # Get model file size
        import os
        model_size = 0.0
        if hasattr(bot, 'model_path') and bot.model_path and os.path.exists(bot.model_path):
            model_size = os.path.getsize(bot.model_path) / (1024 * 1024)  # MB
        
        # Extract performance metrics
        test_rmse = result.get("test_rmse") or result.get("final_loss") or None
        test_mae = result.get("test_mae") or result.get("final_mae") or None
        training_loss = result.get("training_loss") or result.get("final_loss") or None
        
        # Create training record
        training_record = ModelTrainingRecord(
            symbol=symbol,
            timeframe=timeframe,
            bot_name=bot.name,
            trained_at=datetime.utcnow(),
            training_duration_seconds=duration,
            data_points_used=len(candles),
            training_period=period,
            epochs=epochs,
            training_loss=training_loss,
            validation_loss=result.get("validation_loss"),
            test_rmse=test_rmse,
            test_mae=test_mae,
            model_path=bot.model_path if hasattr(bot, 'model_path') else None,
            model_size_mb=model_size,
            status='active',
            config={"epochs": epochs, "period": period}
        )
        
        db.add(training_record)
        db.commit()
        
        logger.info(f"Training completed: {bot.name} for {symbol}/{timeframe}")
        
        return {
            "status": "completed",
            "model_id": training_record.id,
            "duration": duration,
            "data_points": len(candles)
        }
        
    except Exception as e:
        logger.error(f"Training failed for {bot.name} {symbol}/{timeframe}: {e}")
        
        # Create failed record
        training_record = ModelTrainingRecord(
            symbol=symbol,
            timeframe=timeframe,
            bot_name=bot.name,
            trained_at=datetime.utcnow(),
            training_duration_seconds=time.time() - start_time,
            status='failed',
            error_message=str(e)
        )
        
        db.add(training_record)
        db.commit()
        
        raise


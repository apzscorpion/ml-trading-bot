"""
AI-Powered Training Endpoints
Uses Freddy AI to generate training labels and targets.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from backend.database import get_db, ModelTrainingRecord
from backend.ml.ai_training_orchestrator import ai_training_orchestrator
from backend.freddy_merger import freddy_merger
from backend.utils.logger import get_logger
from backend.services.prediction_evaluator import prediction_evaluator

router = APIRouter(prefix="/api/ai-training", tags=["ai-training"])
logger = get_logger(__name__)


class AITrainingRequest(BaseModel):
    """Request for AI-powered training"""
    symbol: str
    timeframe: str = "5m"
    lookback_days: int = 30
    sample_points: int = 100
    bot_names: List[str] = ["lstm_bot", "transformer_bot", "ensemble_bot"]
    use_for_training: bool = True  # If True, actually trains models; if False, just generates dataset


class AITrainingResponse(BaseModel):
    """Response from AI training"""
    status: str
    message: str
    metadata: dict
    training_points_generated: int
    models_trained: Optional[List[str]] = None


# Global state for AI training
ai_training_state = {
    "is_running": False,
    "current_task": None,
    "progress": 0.0,
    "message": ""
}


@router.get("/status")
async def get_ai_training_status():
    """Get current AI training status"""
    return ai_training_state


@router.post("/generate-dataset", response_model=AITrainingResponse)
async def generate_ai_training_dataset(
    request: AITrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate AI-labeled training dataset using Freddy API.
    
    This endpoint:
    1. Fetches latest real-time data for the symbol
    2. Calls Freddy AI to generate target/stop-loss for sample points
    3. Optionally trains models with the generated dataset
    
    Returns immediately and runs in background.
    """
    if ai_training_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="AI training is already running. Please wait."
        )
    
    # Set running state
    ai_training_state["is_running"] = True
    ai_training_state["current_task"] = f"{request.symbol}/{request.timeframe}"
    ai_training_state["progress"] = 0.0
    ai_training_state["message"] = "Starting AI training dataset generation..."
    
    # Start background task
    background_tasks.add_task(
        _run_ai_training_background,
        request,
        db
    )
    
    return AITrainingResponse(
        status="started",
        message=f"AI training started for {request.symbol}/{request.timeframe}",
        metadata={
            "lookback_days": request.lookback_days,
            "sample_points": request.sample_points,
            "use_for_training": request.use_for_training
        },
        training_points_generated=0
    )


async def _run_ai_training_background(request: AITrainingRequest, db: Session):
    """
    Background task to run AI training.
    """
    try:
        logger.info(f"🤖 Starting AI training for {request.symbol}/{request.timeframe}")
        
        # Step 1: Generate AI-labeled dataset
        ai_training_state["progress"] = 0.1
        ai_training_state["message"] = "Fetching latest data from APIs..."
        
        training_points, metadata = await ai_training_orchestrator.generate_training_dataset(
            symbol=request.symbol,
            timeframe=request.timeframe,
            lookback_days=request.lookback_days,
            sample_points=request.sample_points
        )
        
        if not training_points:
            logger.error("No training points generated")
            ai_training_state["is_running"] = False
            ai_training_state["message"] = "Failed: No training points generated"
            return
        
        logger.info(f"Generated {len(training_points)} AI-labeled training points")
        
        ai_training_state["progress"] = 0.5
        ai_training_state["message"] = f"Generated {len(training_points)} AI-labeled points"
        
        # Step 2: Convert to training format
        X, y, conversion_metadata = ai_training_orchestrator.convert_to_training_format(
            training_points
        )
        
        logger.info(f"Converted to training format: X shape {X.shape}, y shape {y.shape}")
        
        # Step 3: Train models if requested
        trained_models = []
        if request.use_for_training:
            ai_training_state["progress"] = 0.6
            ai_training_state["message"] = "Training models with AI-generated labels..."
            
            # Get bots from freddy_merger
            for bot_name in request.bot_names:
                try:
                    bot = freddy_merger.get_bot(bot_name)
                    if bot is None:
                        logger.warning(f"Bot {bot_name} not found")
                        continue
                    
                    # Set context for bot
                    bot._current_symbol = request.symbol
                    bot._current_timeframe = request.timeframe
                    
                    # Prepare candles for training (reconstruct from features)
                    candles_for_training = []
                    for point in training_points:
                        candles_for_training.append({
                            'timestamp': point.timestamp.isoformat(),
                            'start_ts': point.timestamp.isoformat(),
                            'open': point.features.get('open', 0),
                            'high': point.features.get('high', 0),
                            'low': point.features.get('low', 0),
                            'close': point.features.get('close', 0),
                            'volume': point.features.get('volume', 0),
                        })
                    
                    logger.info(f"Training {bot_name} with {len(candles_for_training)} AI-labeled candles")
                    
                    # Train the bot
                    result = await bot.train(
                        candles=candles_for_training,
                        test_size=0.2,
                        epochs=50
                    )
                    
                    if result.get("status") == "success" or "error" not in result:
                        trained_models.append(bot_name)
                        logger.info(f"✅ Successfully trained {bot_name}")
                    else:
                        logger.error(f"Failed to train {bot_name}: {result.get('error')}")
                    
                except Exception as e:
                    logger.error(f"Error training {bot_name}: {e}", exc_info=True)
            
            ai_training_state["progress"] = 1.0
            ai_training_state["message"] = f"Training complete! Trained {len(trained_models)} models"
        else:
            ai_training_state["progress"] = 1.0
            ai_training_state["message"] = "Dataset generation complete (training skipped)"
        
        # Store training record
        try:
            training_record = ModelTrainingRecord(
                symbol=request.symbol,
                timeframe=request.timeframe,
                bot_name="ai_orchestrator",
                trained_at=datetime.utcnow(),
                training_duration_seconds=(
                    datetime.fromisoformat(metadata["completed_at"]) -
                    datetime.fromisoformat(metadata["started_at"])
                ).total_seconds(),
                data_points_used=len(training_points),
                training_period=f"{request.lookback_days}d",
                status='completed',
                config={
                    "type": "ai_powered_training",
                    "freddy_calls": metadata.get("freddy_calls", 0),
                    "success_rate": metadata.get("success_rate", 0),
                    "sample_points": request.sample_points,
                    "trained_models": trained_models,
                    "metadata": metadata
                }
            )
            db.add(training_record)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to store training record: {e}")
        
        logger.info(
            f"🎉 AI training completed for {request.symbol}/{request.timeframe}. "
            f"Generated {len(training_points)} points, trained {len(trained_models)} models"
        )
        
    except Exception as e:
        logger.error(f"AI training failed: {e}", exc_info=True)
        ai_training_state["message"] = f"Failed: {str(e)}"
    finally:
        ai_training_state["is_running"] = False


@router.post("/trigger-for-active-symbol")
async def trigger_ai_training_for_active_symbol(
    symbol: str,
    timeframe: str = "5m",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger AI training for the currently active symbol in the chart.
    This is meant to be called when user is viewing a chart.
    
    Use case: User opens INFY chart → system automatically triggers AI training
    to keep models fresh based on latest data and Freddy AI insights.
    """
    logger.info(f"📊 Triggered AI training for active symbol: {symbol}/{timeframe}")
    
    # Check if we recently trained this symbol
    # Check if we recently trained this symbol
    # Run blocking DB query in thread
    import asyncio
    def check_recent_training():
        return db.query(ModelTrainingRecord).filter(
            ModelTrainingRecord.symbol == symbol,
            ModelTrainingRecord.timeframe == timeframe,
            ModelTrainingRecord.bot_name == "ai_orchestrator",
            ModelTrainingRecord.status == 'completed'
        ).order_by(ModelTrainingRecord.trained_at.desc()).first()
        
    recent_training = await asyncio.to_thread(check_recent_training)
    
    if recent_training:
        age_hours = (datetime.utcnow() - recent_training.trained_at).total_seconds() / 3600
        
        # Don't retrain if trained in last 4 hours
        if age_hours < 4:
            logger.info(f"Symbol {symbol} was trained {age_hours:.1f}h ago, skipping")
            return {
                "status": "skipped",
                "message": f"Model trained {age_hours:.1f}h ago, still fresh",
                "last_trained": recent_training.trained_at.isoformat()
            }
    
    # Trigger training
    request = AITrainingRequest(
        symbol=symbol,
        timeframe=timeframe,
        lookback_days=14,  # Shorter lookback for active symbol (faster)
        sample_points=50,   # Fewer samples (faster)
        bot_names=["ensemble_bot", "lstm_bot"],  # Train key models only
        use_for_training=True
    )
    
    if background_tasks:
        return await generate_ai_training_dataset(request, background_tasks, db)
    else:
        # If no background tasks, just return scheduled status
        return {
            "status": "scheduled",
            "message": f"AI training scheduled for {symbol}/{timeframe}",
            "note": "Will run in next background cycle"
        }


@router.post("/learn-from-mistakes")
async def learn_from_mistakes(
    background_tasks: BackgroundTasks,
    min_error_threshold: float = 2.0,
    lookback_hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Trigger the feedback loop:
    1. Evaluate recent predictions against actual data
    2. Identify mistakes (high error)
    3. Retrain models using these mistakes as corrected examples
    """
    if ai_training_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="AI training is already running. Please wait."
        )
        
    ai_training_state["is_running"] = True
    ai_training_state["current_task"] = "Feedback Loop"
    ai_training_state["progress"] = 0.0
    ai_training_state["message"] = "Starting feedback loop..."
    
    background_tasks.add_task(
        _run_feedback_loop_background,
        min_error_threshold,
        lookback_hours,
        db
    )
    
    return {
        "status": "started",
        "message": "Feedback loop started",
        "config": {
            "min_error_threshold": min_error_threshold,
            "lookback_hours": lookback_hours
        }
    }


async def _run_feedback_loop_background(
    min_error_threshold: float,
    lookback_hours: int,
    db: Session
):
    """Background task for feedback loop"""
    try:
        logger.info("🔄 Starting Feedback Loop")
        
        # Step 1: Evaluate pending predictions
        ai_training_state["progress"] = 0.1
        ai_training_state["message"] = "Evaluating past predictions..."
        
        await prediction_evaluator.evaluate_pending_predictions(lookback_hours=lookback_hours)
        
        # Step 2: Generate dataset from mistakes
        ai_training_state["progress"] = 0.3
        ai_training_state["message"] = "Generating correction dataset..."
        
        training_points, metadata = await ai_training_orchestrator.generate_dataset_from_mistakes(
            min_error_threshold=min_error_threshold
        )
        
        if not training_points:
            logger.info("No mistakes found to learn from")
            ai_training_state["is_running"] = False
            ai_training_state["message"] = "Completed: No significant mistakes found"
            return
            
        logger.info(f"Found {len(training_points)} correction points")
        
        # Step 3: Train models
        ai_training_state["progress"] = 0.5
        ai_training_state["message"] = f"Retraining models on {len(training_points)} correction points..."
        
        # Convert to training format
        X, y, _ = ai_training_orchestrator.convert_to_training_format(training_points)
        
        # Train ensemble bot (it's the most important for decision making)
        # We could also train others, but ensemble is the aggregator
        bot_names = ["ensemble_bot", "lstm_bot"]
        trained_models = []
        
        for bot_name in bot_names:
            try:
                bot = freddy_merger.get_bot(bot_name)
                if not bot:
                    continue
                    
                # Prepare candles (reconstructed)
                candles_for_training = []
                for point in training_points:
                    candles_for_training.append({
                        'timestamp': point.timestamp.isoformat(),
                        'start_ts': point.timestamp.isoformat(),
                        'open': point.features.get('open', 0),
                        'high': point.features.get('high', 0),
                        'low': point.features.get('low', 0),
                        'close': point.features.get('close', 0),
                        'volume': point.features.get('volume', 0),
                    })
                
                # Train
                result = await bot.train(
                    candles=candles_for_training,
                    test_size=0.1,
                    epochs=20 # Fewer epochs for fine-tuning
                )
                
                if result.get("status") == "success":
                    trained_models.append(bot_name)
                    
            except Exception as e:
                logger.error(f"Error fine-tuning {bot_name}: {e}")
        
        ai_training_state["progress"] = 1.0
        ai_training_state["message"] = f"Feedback loop complete. Fine-tuned {len(trained_models)} models."
        
        # Log completion
        logger.info(f"✅ Feedback loop completed. Fine-tuned: {trained_models}")
        
    except Exception as e:
        logger.error(f"Feedback loop failed: {e}", exc_info=True)
        ai_training_state["message"] = f"Failed: {str(e)}"
    finally:
        ai_training_state["is_running"] = False

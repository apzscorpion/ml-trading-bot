"""
Training Manager Service
Centralized training state management, queue handling, and cancellation support.
"""
import asyncio
from typing import Dict, Optional, Set
from datetime import datetime
import logging
from backend.database import SessionLocal, ModelTrainingRecord
from backend.websocket_manager import manager

logger = logging.getLogger(__name__)


class TrainingManager:
    """Manages training sessions, queue, and cancellation"""
    
    def __init__(self):
        # Active training sessions: {training_id: task}
        self.active_trainings: Dict[int, asyncio.Task] = {}
        
        # Cancellation flags: {training_id: True}
        self.cancellation_flags: Dict[int, bool] = {}
        
        # Training queue
        self.training_queue: asyncio.Queue = asyncio.Queue()
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Maximum concurrent trainings
        self.max_concurrent_trainings = 3
    
    def is_training_active(self, training_id: int) -> bool:
        """Check if a training session is currently active"""
        return training_id in self.active_trainings
    
    def is_cancellation_requested(self, training_id: int) -> bool:
        """Check if cancellation has been requested for a training session"""
        return self.cancellation_flags.get(training_id, False)
    
    async def register_training(self, training_id: int, task: asyncio.Task):
        """Register a new training session"""
        async with self._lock:
            self.active_trainings[training_id] = task
            self.cancellation_flags[training_id] = False
            logger.info(f"Registered training {training_id}. Active: {len(self.active_trainings)}")
    
    async def unregister_training(self, training_id: int):
        """Unregister a completed/failed training session"""
        async with self._lock:
            if training_id in self.active_trainings:
                del self.active_trainings[training_id]
            if training_id in self.cancellation_flags:
                del self.cancellation_flags[training_id]
            logger.info(f"Unregistered training {training_id}. Active: {len(self.active_trainings)}")
    
    async def request_cancellation(self, training_id: int, reason: str = "user_requested") -> bool:
        """
        Request cancellation of a training session.
        
        Args:
            training_id: ID of the training to cancel
            reason: Reason for cancellation
        
        Returns:
            True if cancellation was requested, False if training not found
        """
        async with self._lock:
            if training_id not in self.active_trainings:
                logger.warning(f"Training {training_id} not found for cancellation")
                return False
            
            # Set cancellation flag
            self.cancellation_flags[training_id] = True
            
            # Update database
            db = SessionLocal()
            try:
                record = db.query(ModelTrainingRecord).filter(
                    ModelTrainingRecord.id == training_id
                ).first()
                
                if record:
                    record.status = 'cancelled'
                    record.cancelled_at = datetime.utcnow()
                    record.cancellation_reason = reason
                    record.progress_message = f"Cancelled: {reason}"
                    db.commit()
                    
                    # Broadcast cancellation
                    await manager.broadcast_training_progress({
                        "training_id": training_id,
                        "bot_name": record.bot_name,
                        "symbol": record.symbol,
                        "timeframe": record.timeframe,
                        "status": "cancelled",
                        "reason": reason,
                        "message": f"Training cancelled: {reason}"
                    })
                    
                    logger.info(f"Cancellation requested for training {training_id}: {reason}")
                    return True
            except Exception as e:
                logger.error(f"Error updating cancellation in DB: {e}")
                db.rollback()
            finally:
                db.close()
            
            return False
    
    async def cancel_all_trainings(self, reason: str = "system_shutdown"):
        """Cancel all active training sessions"""
        training_ids = list(self.active_trainings.keys())
        logger.info(f"Cancelling {len(training_ids)} active trainings: {reason}")
        
        for training_id in training_ids:
            await self.request_cancellation(training_id, reason)
    
    def get_active_trainings(self) -> Dict[int, Dict]:
        """Get information about all active trainings"""
        db = SessionLocal()
        try:
            active_info = {}
            for training_id in self.active_trainings.keys():
                record = db.query(ModelTrainingRecord).filter(
                    ModelTrainingRecord.id == training_id
                ).first()
                
                if record:
                    active_info[training_id] = {
                        "bot_name": record.bot_name,
                        "symbol": record.symbol,
                        "timeframe": record.timeframe,
                        "status": record.status,
                        "progress_percent": record.progress_percent,
                        "current_epoch": record.current_epoch,
                        "total_epochs": record.total_epochs,
                        "current_batch": record.current_batch,
                        "total_batches": record.total_batches,
                        "started_at": record.trained_at.isoformat() if record.trained_at else None
                    }
            
            return active_info
        finally:
            db.close()
    
    async def get_model_status(self, symbol: str, timeframe: str) -> Dict:
        """
        Get status of all models for a given symbol/timeframe.
        
        Returns:
            Dict with model statuses, last training times, and freshness
        """
        db = SessionLocal()
        try:
            bot_names = ['lstm_bot', 'transformer_bot', 'ml_bot', 'ensemble_bot', 
                        'rsi_bot', 'macd_bot', 'ma_bot']
            
            model_statuses = {}
            
            for bot_name in bot_names:
                # Get latest training record
                latest = db.query(ModelTrainingRecord).filter(
                    ModelTrainingRecord.symbol == symbol,
                    ModelTrainingRecord.timeframe == timeframe,
                    ModelTrainingRecord.bot_name == bot_name
                ).order_by(ModelTrainingRecord.trained_at.desc()).first()
                
                # Check if currently training
                is_training = False
                training_progress = None
                for training_id, info in self.get_active_trainings().items():
                    if (info['bot_name'] == bot_name and 
                        info['symbol'] == symbol and 
                        info['timeframe'] == timeframe):
                        is_training = True
                        training_progress = info
                        break
                
                if latest:
                    age_hours = (datetime.utcnow() - latest.trained_at).total_seconds() / 3600
                    
                    model_statuses[bot_name] = {
                        "status": "training" if is_training else latest.status,
                        "last_trained": latest.trained_at.isoformat(),
                        "age_hours": round(age_hours, 1),
                        "is_stale": age_hours > 24,
                        "training_loss": latest.training_loss,
                        "test_rmse": latest.test_rmse,
                        "test_mae": latest.test_mae,
                        "training_progress": training_progress
                    }
                else:
                    model_statuses[bot_name] = {
                        "status": "training" if is_training else "never_trained",
                        "last_trained": None,
                        "age_hours": None,
                        "is_stale": True,
                        "training_progress": training_progress
                    }
            
            return model_statuses
        finally:
            db.close()


# Singleton instance
training_manager = TrainingManager()

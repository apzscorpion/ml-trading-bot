"""
Model Performance Tracker - Tracks recent accuracy for each bot to enable dynamic weighting.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.orm import Session
from backend.database import get_db, Prediction, PredictionEvaluation
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ModelPerformanceTracker:
    """Tracks and calculates performance metrics for prediction bots"""
    
    def __init__(self):
        self.cache = {}  # Cache performance scores: {(symbol, timeframe, bot_name): score}
        self.cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes
        self.cache_timestamps = {}
    
    def get_bot_performance_score(
        self,
        symbol: str,
        timeframe: str,
        bot_name: str,
        lookback_hours: int = 24
    ) -> float:
        """
        Get performance score for a bot (0-1, higher is better).
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe (e.g., '5m')
            bot_name: Bot name (e.g., 'lstm_bot')
            lookback_hours: Hours to look back for performance (default: 24)
        
        Returns:
            Performance score (0-1), where 1.0 = perfect, 0.0 = poor
            Returns 0.5 (neutral) if no data available
        """
        cache_key = (symbol, timeframe, bot_name, lookback_hours)
        
        # Check cache
        if cache_key in self.cache:
            cache_time = self.cache_timestamps.get(cache_key)
            if cache_time and (datetime.utcnow() - cache_time) < self.cache_ttl:
                return self.cache[cache_key]
        
        try:
            db = next(get_db())
            
            # Get recent predictions for this bot
            since = datetime.utcnow() - timedelta(hours=lookback_hours)
            
            # Query predictions with evaluations
            predictions = db.query(Prediction).join(
                PredictionEvaluation,
                Prediction.id == PredictionEvaluation.prediction_id
            ).filter(
                Prediction.symbol == symbol,
                Prediction.timeframe == timeframe,
                Prediction.produced_at >= since
            ).all()
            
            if not predictions:
                # No recent data - return neutral score
                score = 0.5
                self.cache[cache_key] = score
                self.cache_timestamps[cache_key] = datetime.utcnow()
                db.close()
                return score
            
            # Extract bot-specific metrics from bot_contributions
            bot_mape_list = []
            bot_dir_acc_list = []
            bot_rmse_list = []
            
            for pred in predictions:
                # Get evaluation metrics
                eval_data = pred.evaluations[0] if pred.evaluations else None
                if not eval_data:
                    continue
                
                # Check if this bot contributed to this prediction
                contributions = pred.bot_contributions or {}
                if bot_name not in contributions:
                    continue
                
                # Collect metrics
                if eval_data.mape is not None:
                    bot_mape_list.append(eval_data.mape)
                if eval_data.directional_accuracy is not None:
                    bot_dir_acc_list.append(eval_data.directional_accuracy)
                if eval_data.rmse is not None:
                    bot_rmse_list.append(eval_data.rmse)
            
            db.close()
            
            if not bot_mape_list:
                # No evaluations for this bot - return neutral
                score = 0.5
                self.cache[cache_key] = score
                self.cache_timestamps[cache_key] = datetime.utcnow()
                return score
            
            # Calculate performance score
            # Lower MAPE = better (inverse relationship)
            # Higher directional accuracy = better (direct relationship)
            # Lower RMSE = better (inverse relationship)
            
            avg_mape = np.mean(bot_mape_list)
            avg_dir_acc = np.mean(bot_dir_acc_list) if bot_dir_acc_list else 50.0
            avg_rmse = np.mean(bot_rmse_list) if bot_rmse_list else None
            
            # Normalize MAPE: 0% MAPE = 1.0, 10% MAPE = 0.0, linear interpolation
            mape_score = max(0.0, min(1.0, 1.0 - (avg_mape / 10.0)))
            
            # Normalize directional accuracy: 100% = 1.0, 50% = 0.5, 0% = 0.0
            dir_acc_score = avg_dir_acc / 100.0
            
            # Normalize RMSE if available (relative to price level)
            # Assume price ~1500, so RMSE of 30 = 2% error
            rmse_score = 1.0
            if avg_rmse and avg_rmse > 0:
                # Estimate price level from symbol (rough approximation)
                estimated_price = 1500.0  # Default assumption
                rmse_pct = (avg_rmse / estimated_price) * 100
                rmse_score = max(0.0, min(1.0, 1.0 - (rmse_pct / 10.0)))
            
            # Weighted combination: MAPE (40%), Directional (40%), RMSE (20%)
            performance_score = (mape_score * 0.4) + (dir_acc_score * 0.4) + (rmse_score * 0.2)
            
            # Ensure score is between 0.1 and 1.0 (never completely exclude)
            performance_score = max(0.1, min(1.0, performance_score))
            
            # Cache result
            self.cache[cache_key] = performance_score
            self.cache_timestamps[cache_key] = datetime.utcnow()
            
            logger.debug(
                f"Bot {bot_name} performance score: {performance_score:.3f}",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "bot": bot_name,
                    "mape": avg_mape,
                    "dir_acc": avg_dir_acc,
                    "rmse": avg_rmse,
                    "score": performance_score
                }
            )
            
            return float(performance_score)
            
        except Exception as e:
            logger.error(f"Error calculating performance score for {bot_name}: {e}")
            # Return neutral score on error
            return 0.5
    
    def get_all_bot_scores(
        self,
        symbol: str,
        timeframe: str,
        lookback_hours: int = 24
    ) -> Dict[str, float]:
        """
        Get performance scores for all bots.
        
        Returns:
            Dictionary mapping bot_name -> performance_score
        """
        bot_names = [
            "rsi_bot", "macd_bot", "ma_bot",
            "ml_bot", "lstm_bot", "transformer_bot", "ensemble_bot"
        ]
        
        scores = {}
        for bot_name in bot_names:
            scores[bot_name] = self.get_bot_performance_score(
                symbol, timeframe, bot_name, lookback_hours
            )
        
        return scores
    
    def get_recency_factor(
        self,
        symbol: str,
        timeframe: str,
        bot_name: str,
        lookback_hours: int = 24
    ) -> float:
        """
        Calculate recency factor based on how recent the bot's predictions are.
        
        Returns:
            Recency factor (0.5-1.0), where 1.0 = very recent, 0.5 = stale
        """
        try:
            db = next(get_db())
            
            # Get most recent prediction for this bot
            since = datetime.utcnow() - timedelta(hours=lookback_hours)
            
            # Find predictions where this bot contributed
            predictions = db.query(Prediction).filter(
                Prediction.symbol == symbol,
                Prediction.timeframe == timeframe,
                Prediction.produced_at >= since
            ).order_by(Prediction.produced_at.desc()).limit(10).all()
            
            if not predictions:
                db.close()
                return 0.5  # No recent predictions = stale
            
            # Check if bot contributed to recent predictions
            recent_count = 0
            for pred in predictions:
                contributions = pred.bot_contributions or {}
                if bot_name in contributions:
                    recent_count += 1
            
            db.close()
            
            # Recency factor: more recent contributions = higher factor
            recency_factor = 0.5 + (recent_count / len(predictions)) * 0.5
            return float(recency_factor)
            
        except Exception as e:
            logger.error(f"Error calculating recency factor for {bot_name}: {e}")
            return 0.5
    
    def clear_cache(self):
        """Clear performance cache"""
        self.cache.clear()
        self.cache_timestamps.clear()


# Global instance
model_performance_tracker = ModelPerformanceTracker()


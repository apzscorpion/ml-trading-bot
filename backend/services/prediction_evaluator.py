"""
Prediction Evaluator - Automatically evaluates predictions against actual prices.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy.orm import Session
from backend.database import get_db, Prediction, PredictionEvaluation, Candle
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PredictionEvaluator:
    """Automatically evaluates predictions against actual prices as candles arrive"""
    
    def __init__(self):
        self.evaluation_cache = {}  # Cache evaluations to avoid duplicates
    
    def evaluate_prediction(
        self,
        prediction_id: int,
        db: Optional[Session] = None
    ) -> Optional[Dict]:
        """
        Evaluate a prediction against actual prices.
        
        Args:
            prediction_id: ID of the prediction to evaluate
            db: Database session (optional, will create if not provided)
        
        Returns:
            Dictionary with evaluation metrics, or None if evaluation not possible
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            # Get prediction
            prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
            
            if not prediction:
                logger.warning(f"Prediction {prediction_id} not found")
                return None
            
            # Check if already evaluated recently
            cache_key = f"{prediction_id}_{prediction.produced_at}"
            if cache_key in self.evaluation_cache:
                return self.evaluation_cache[cache_key]
            
            # Get predicted series
            predicted_series = prediction.predicted_series
            if not predicted_series:
                logger.warning(f"Prediction {prediction_id} has no predicted series")
                return None
            
            # Extract timestamps and predicted prices
            predicted_prices = []
            actual_prices = []
            matched_points = []
            
            for point in predicted_series:
                try:
                    ts_str = point.get("ts")
                    if not ts_str:
                        continue
                    
                    # Parse timestamp
                    if isinstance(ts_str, str):
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    else:
                        ts = ts_str
                    
                    predicted_price = point.get("price")
                    if predicted_price is None:
                        continue
                    
                    # Find actual candle at this timestamp
                    # Allow tolerance based on timeframe
                    timeframe_minutes = self._timeframe_to_minutes(prediction.timeframe)
                    tolerance = timedelta(minutes=max(5, timeframe_minutes))
                    
                    actual_candle = db.query(Candle).filter(
                        Candle.symbol == prediction.symbol,
                        Candle.timeframe == prediction.timeframe,
                        Candle.start_ts >= ts - tolerance,
                        Candle.start_ts <= ts + tolerance
                    ).order_by(Candle.start_ts).first()
                    
                    if actual_candle:
                        predicted_prices.append(float(predicted_price))
                        actual_prices.append(float(actual_candle.close))
                        matched_points.append({
                            "ts": actual_candle.start_ts.isoformat(),
                            "predicted": float(predicted_price),
                            "actual": float(actual_candle.close)
                        })
                
                except Exception as e:
                    logger.warning(f"Error processing prediction point: {e}")
                    continue
            
            if not actual_prices or len(actual_prices) < 1:
                logger.debug(f"No actual data available yet for prediction {prediction_id}")
                return None
            
            # Calculate metrics
            metrics = self._calculate_metrics(predicted_prices, actual_prices)
            
            # Store evaluation
            evaluation = PredictionEvaluation(
                prediction_id=prediction.id,
                symbol=prediction.symbol,
                timeframe=prediction.timeframe,
                evaluated_at=datetime.utcnow(),
                rmse=metrics.get("rmse"),
                mae=metrics.get("mae"),
                mape=metrics.get("mape"),
                directional_accuracy=metrics.get("directional_accuracy")
            )
            
            db.add(evaluation)
            db.commit()
            
            result = {
                "prediction_id": prediction.id,
                "evaluation_id": evaluation.id,
                "metrics": metrics,
                "matched_points": matched_points,
                "n_samples": len(actual_prices)
            }
            
            # Cache result
            self.evaluation_cache[cache_key] = result
            
            logger.info(
                f"Evaluated prediction {prediction_id}",
                extra={
                    "symbol": prediction.symbol,
                    "timeframe": prediction.timeframe,
                    "mape": metrics.get("mape"),
                    "directional_accuracy": metrics.get("directional_accuracy"),
                    "n_samples": len(actual_prices)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating prediction {prediction_id}: {e}")
            db.rollback()
            return None
        finally:
            if should_close_db:
                db.close()
    
    def _calculate_metrics(
        self,
        predicted: List[float],
        actual: List[float]
    ) -> Dict:
        """Calculate prediction accuracy metrics"""
        if not predicted or not actual or len(predicted) != len(actual):
            return {}
        
        pred_array = np.array(predicted)
        actual_array = np.array(actual)
        
        # RMSE (Root Mean Square Error)
        rmse = float(np.sqrt(np.mean((pred_array - actual_array) ** 2)))
        
        # MAE (Mean Absolute Error)
        mae = float(np.mean(np.abs(pred_array - actual_array)))
        
        # MAPE (Mean Absolute Percentage Error)
        mape = float(np.mean(np.abs((actual_array - pred_array) / np.clip(actual_array, 1e-6, None))) * 100)
        
        # Directional Accuracy
        if len(predicted) > 1:
            pred_direction = np.diff(pred_array) > 0
            actual_direction = np.diff(actual_array) > 0
            directional_accuracy = float(np.mean(pred_direction == actual_direction) * 100)
        else:
            directional_accuracy = 0.0
        
        return {
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
            "directional_accuracy": directional_accuracy
        }
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }
        return mapping.get(timeframe, 5)
    
    def evaluate_recent_predictions(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        hours: int = 24,
        db: Optional[Session] = None
    ) -> Dict:
        """
        Evaluate all recent predictions that haven't been evaluated yet.
        
        Args:
            symbol: Filter by symbol (optional)
            timeframe: Filter by timeframe (optional)
            hours: Look back hours (default: 24)
            db: Database session (optional)
        
        Returns:
            Dictionary with evaluation summary
        """
        should_close_db = False
        if db is None:
            db = next(get_db())
            should_close_db = True
        
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Get predictions that haven't been evaluated yet
            query = db.query(Prediction).filter(
                Prediction.produced_at >= since
            )
            
            if symbol:
                query = query.filter(Prediction.symbol == symbol)
            if timeframe:
                query = query.filter(Prediction.timeframe == timeframe)
            
            predictions = query.all()
            
            evaluated_count = 0
            skipped_count = 0
            error_count = 0
            
            for pred in predictions:
                # Check if already evaluated
                existing_eval = db.query(PredictionEvaluation).filter(
                    PredictionEvaluation.prediction_id == pred.id
                ).first()
                
                if existing_eval:
                    skipped_count += 1
                    continue
                
                # Evaluate
                result = self.evaluate_prediction(pred.id, db)
                if result:
                    evaluated_count += 1
                else:
                    error_count += 1
            
            return {
                "total_predictions": len(predictions),
                "evaluated": evaluated_count,
                "skipped": skipped_count,
                "errors": error_count
            }
            
        except Exception as e:
            logger.error(f"Error evaluating recent predictions: {e}")
            return {"error": str(e)}
        finally:
            if should_close_db:
                db.close()
    
    def clear_cache(self):
        """Clear evaluation cache"""
        self.evaluation_cache.clear()


# Global instance
prediction_evaluator = PredictionEvaluator()


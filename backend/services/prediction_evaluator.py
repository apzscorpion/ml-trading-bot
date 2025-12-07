"""
Prediction Evaluator Service
Evaluates past predictions against actual market data to identify model mistakes.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.database import SessionLocal, Prediction, PredictionEvaluation, Candle
from backend.utils.data_fetcher import data_fetcher
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PredictionEvaluator:
    """
    Evaluates past predictions against actual market data.
    Calculates RMSE, MAE, and Directional Accuracy.
    """
    
    def __init__(self):
        pass
        
    async def evaluate_pending_predictions(self, lookback_hours: int = 24):
        """
        Find predictions that have matured (time has passed) but haven't been evaluated.
        Compare predicted prices with actual prices and store results.
        
        Args:
            lookback_hours: How far back to look for unevaluated predictions
        """
        db = SessionLocal()
        try:
            # 1. Find unevaluated predictions that are old enough to be evaluated
            # We need predictions where produced_at + horizon < now
            cutoff_time = datetime.utcnow()
            start_time = cutoff_time - timedelta(hours=lookback_hours)
            
            # Get IDs of already evaluated predictions to exclude them
            evaluated_ids = db.query(PredictionEvaluation.prediction_id).filter(
                PredictionEvaluation.evaluated_at >= start_time
            ).all()
            evaluated_ids = {r[0] for r in evaluated_ids}
            
            # Query pending predictions
            # Note: We can't easily filter by "produced_at + horizon < now" in SQL directly 
            # without complex expressions, so we'll fetch recent ones and filter in Python
            # or use a safe upper bound for horizon (e.g. 4 hours)
            pending_predictions = db.query(Prediction).filter(
                Prediction.produced_at >= start_time,
                Prediction.produced_at <= cutoff_time,
                Prediction.prediction_type == "ensemble"  # Focus on ensemble for now
            ).all()
            
            # Filter for those that are actually ready and not evaluated
            ready_predictions = []
            for pred in pending_predictions:
                if pred.id in evaluated_ids:
                    continue
                    
                # Check if enough time has passed
                # horizon_minutes is in minutes
                completion_time = pred.produced_at + timedelta(minutes=pred.horizon_minutes)
                if completion_time < datetime.utcnow():
                    ready_predictions.append(pred)
            
            if not ready_predictions:
                logger.info("No pending predictions to evaluate")
                return
            
            logger.info(f"Found {len(ready_predictions)} pending predictions to evaluate")
            
            # Group by symbol/timeframe to optimize data fetching
            grouped_preds = {}
            for pred in ready_predictions:
                key = (pred.symbol, pred.timeframe)
                if key not in grouped_preds:
                    grouped_preds[key] = []
                grouped_preds[key].append(pred)
            
            # Process each group
            evaluations_created = 0
            
            for (symbol, timeframe), preds in grouped_preds.items():
                # Determine time range needed for this batch
                min_ts = min(p.produced_at for p in preds)
                # Max ts is the latest completion time
                max_ts = max(p.produced_at + timedelta(minutes=p.horizon_minutes) for p in preds)
                
                # Fetch actual candles for this range (plus buffer)
                # We need 1m candles for granular comparison, or matching timeframe
                # Using matching timeframe is safer for direct comparison
                actual_candles = await data_fetcher.fetch_candles(
                    symbol=symbol,
                    interval=timeframe,
                    period="5d", # Fetch enough to cover
                    bypass_cache=False
                )
                
                if not actual_candles:
                    logger.warning(f"Could not fetch actual data for {symbol} evaluation")
                    continue
                
                # Convert to lookup dict: timestamp -> close price
                # Ensure timestamps match format
                actual_prices = {}
                for c in actual_candles:
                    # Handle string vs datetime
                    ts_str = c['start_ts']
                    if isinstance(ts_str, datetime):
                        ts_str = ts_str.isoformat()
                    # Normalize to minute precision if needed, but ISO string matching is usually fine
                    # if they come from same source. 
                    # Better: parse to datetime for comparison
                    try:
                        ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        actual_prices[ts_dt] = c['close']
                    except Exception:
                        pass
                
                # Evaluate each prediction
                for pred in preds:
                    try:
                        evaluation = self._evaluate_single_prediction(pred, actual_prices)
                        if evaluation:
                            db.add(evaluation)
                            evaluations_created += 1
                    except Exception as e:
                        logger.error(f"Failed to evaluate prediction {pred.id}: {e}")
            
            db.commit()
            logger.info(f"Successfully evaluated {evaluations_created} predictions")
            
        except Exception as e:
            logger.error(f"Error in evaluate_pending_predictions: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    def _evaluate_single_prediction(
        self, 
        prediction: Prediction, 
        actual_prices: Dict[datetime, float]
    ) -> Optional[PredictionEvaluation]:
        """
        Compare a single prediction series against actual prices.
        """
        if not prediction.predicted_series:
            return None
            
        predicted_points = []
        actual_points = []
        
        # Extract series
        # predicted_series is list of {ts: iso_str, price: float}
        for point in prediction.predicted_series:
            pred_ts_str = point.get('ts')
            pred_price = point.get('price')
            
            if not pred_ts_str or pred_price is None:
                continue
                
            try:
                pred_dt = datetime.fromisoformat(pred_ts_str.replace("Z", "+00:00"))
                
                # Find matching actual price
                # We look for exact match or closest match within tolerance?
                # For now, exact match on timeframe start time
                if pred_dt in actual_prices:
                    predicted_points.append(pred_price)
                    actual_points.append(actual_prices[pred_dt])
            except ValueError:
                continue
                
        if not predicted_points:
            return None
            
        # Calculate metrics
        y_pred = np.array(predicted_points)
        y_true = np.array(actual_points)
        
        # RMSE
        mse = np.mean((y_true - y_pred) ** 2)
        rmse = np.sqrt(mse)
        
        # MAE
        mae = np.mean(np.abs(y_true - y_pred))
        
        # MAPE (Mean Absolute Percentage Error)
        # Avoid division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
            if not np.isfinite(mape):
                mape = 0.0
        
        # Directional Accuracy
        # Did it predict the move direction correctly from the start?
        if len(y_true) > 1:
            # Direction from first point
            true_direction = np.sign(y_true[-1] - y_true[0])
            pred_direction = np.sign(y_pred[-1] - y_pred[0])
            directional_accuracy = 1.0 if true_direction == pred_direction else 0.0
        else:
            directional_accuracy = 0.0
            
        return PredictionEvaluation(
            prediction_id=prediction.id,
            symbol=prediction.symbol,
            timeframe=prediction.timeframe,
            evaluated_at=datetime.utcnow(),
            rmse=float(rmse),
            mae=float(mae),
            mape=float(mape),
            directional_accuracy=float(directional_accuracy)
        )

# Global instance
prediction_evaluator = PredictionEvaluator()

"""Utilities to compute prediction drift and quality metrics with 7-day rolling windows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.database import SessionLocal, ModelTrainingRecord, PredictionEvaluation
from backend.utils.metrics import record_prediction_quality
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DriftMetrics:
    mae: float
    mape: float
    directional_accuracy: float
    drift_score: Optional[float] = None  # New: 0-1 score, higher = more drift


class DriftMonitor:
    """Calculate drift metrics comparing predictions vs actual candles with rolling window tracking."""
    
    def __init__(self):
        self.rolling_window_days = 7
        self.drift_threshold = 0.20  # 20% increase in error = drift alert

    def compute(self, prediction: Dict, actual_candles: List[Dict]) -> DriftMetrics:
        predicted_series = prediction.get('predicted_series', [])
        if not predicted_series or not actual_candles:
            return DriftMetrics(mae=0.0, mape=0.0, directional_accuracy=0.0)

        df_pred = pd.DataFrame(predicted_series)
        df_actual = pd.DataFrame(actual_candles)
        df_actual = df_actual.rename(columns={'close': 'actual_close', 'start_ts': 'ts'})
        df_actual['ts'] = pd.to_datetime(df_actual['ts'])
        df_pred['ts'] = pd.to_datetime(df_pred['ts'])

        merged = pd.merge_asof(
            df_pred.sort_values('ts'),
            df_actual.sort_values('ts'),
            on='ts',
            tolerance=pd.Timedelta('15m'),
            direction='nearest',
        ).dropna(subset=['price', 'actual_close'])

        if merged.empty:
            return DriftMetrics(mae=0.0, mape=0.0, directional_accuracy=0.0)

        predicted = merged['price'].to_numpy()
        actual = merged['actual_close'].to_numpy()
        errors = predicted - actual
        mae = float(np.mean(np.abs(errors)))
        mape = float(np.mean(np.abs(errors / np.clip(actual, 1e-6, None))) * 100)
        if len(predicted) > 1:
            dir_acc = float(
                (np.sign(np.diff(predicted)) == np.sign(np.diff(actual))).mean() * 100
            )
        else:
            dir_acc = 0.0
        return DriftMetrics(mae=mae, mape=mape, directional_accuracy=dir_acc)

    def emit_metrics(self, symbol: str, timeframe: str, drift: DriftMetrics) -> None:
        record_prediction_quality(
            symbol,
            timeframe,
            {
                'mae': drift.mae,
                'mape': drift.mape,
                'directional_accuracy': drift.directional_accuracy,
                'drift_score': drift.drift_score
            },
        )
    
    def compute_drift_score(
        self,
        symbol: str,
        timeframe: str,
        bot_name: str
    ) -> Optional[float]:
        """
        Compute drift score by comparing recent 7-day error vs training baseline.
        
        Returns:
            Drift score (0-1): 0 = no drift, 1 = severe drift
            None if insufficient data
        """
        db = SessionLocal()
        try:
            # Get training baseline error
            training_record = db.query(ModelTrainingRecord).filter(
                ModelTrainingRecord.symbol == symbol,
                ModelTrainingRecord.timeframe == timeframe,
                ModelTrainingRecord.bot_name == bot_name,
                ModelTrainingRecord.status.in_(['active', 'completed'])
            ).order_by(ModelTrainingRecord.trained_at.desc()).first()
            
            if not training_record or not training_record.test_rmse:
                logger.warning(f"No training baseline found for {bot_name} {symbol}/{timeframe}")
                return None
            
            baseline_rmse = training_record.test_rmse
            
            # Get recent 7-day evaluations
            cutoff = datetime.utcnow() - timedelta(days=self.rolling_window_days)
            recent_evals = db.query(PredictionEvaluation).filter(
                PredictionEvaluation.symbol == symbol,
                PredictionEvaluation.timeframe == timeframe,
                PredictionEvaluation.evaluated_at >= cutoff
            ).all()
            
            if not recent_evals:
                logger.warning(f"No recent evaluations for {symbol}/{timeframe}")
                return None
            
            # Compute average recent RMSE
            recent_rmse_values = [e.rmse for e in recent_evals if e.rmse is not None]
            if not recent_rmse_values:
                return None
            
            avg_recent_rmse = np.mean(recent_rmse_values)
            
            # Calculate drift score
            if baseline_rmse > 0:
                drift_ratio = (avg_recent_rmse - baseline_rmse) / baseline_rmse
                drift_score = max(0.0, min(1.0, drift_ratio))  # Clamp to 0-1
            else:
                drift_score = 0.0
            
            logger.info(
                f"Drift score for {bot_name} {symbol}/{timeframe}: {drift_score:.3f} "
                f"(baseline RMSE: {baseline_rmse:.2f}, recent RMSE: {avg_recent_rmse:.2f})"
            )
            
            # Store drift score back to training record
            training_record.config = training_record.config or {}
            training_record.config['drift_score'] = float(drift_score)
            training_record.config['drift_computed_at'] = datetime.utcnow().isoformat()
            db.commit()
            
            return float(drift_score)
            
        finally:
            db.close()
    
    def check_drift_alert(
        self,
        symbol: str,
        timeframe: str,
        bot_name: str
    ) -> bool:
        """
        Check if drift score exceeds alert threshold.
        
        Returns:
            True if retraining is recommended
        """
        drift_score = self.compute_drift_score(symbol, timeframe, bot_name)
        
        if drift_score is None:
            return False
        
        if drift_score > self.drift_threshold:
            logger.warning(
                f"DRIFT ALERT: {bot_name} {symbol}/{timeframe} drift score {drift_score:.2f} "
                f"exceeds threshold {self.drift_threshold}. Retraining recommended."
            )
            return True
        
        return False


def compute_and_emit(symbol: str, timeframe: str, prediction: Dict, actual_candles: List[Dict]) -> DriftMetrics:
    monitor = DriftMonitor()
    drift = monitor.compute(prediction, actual_candles)
    monitor.emit_metrics(symbol, timeframe, drift)
    return drift

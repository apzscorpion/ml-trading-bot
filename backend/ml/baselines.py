"""
Baseline Models for ML Comparison.
Always compare ML models against simple baselines before deployment.
"""
from typing import Dict, List
import numpy as np
import pandas as pd
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BaselineModels:
    """Simple baseline models for comparison with ML models"""
    
    @staticmethod
    def last_value_baseline(
        train_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Last value baseline: predict last known value for all future points.
        
        Returns:
            Dict with RMSE, MAE, directional_accuracy
        """
        if len(train_df) == 0 or len(test_df) == 0:
            return {"error": "empty_data"}
        
        last_value = train_df['close'].iloc[-1]
        predictions = np.full(len(test_df), last_value)
        actuals = test_df['close'].values
        
        rmse = float(np.sqrt(np.mean((predictions - actuals) ** 2)))
        mae = float(np.mean(np.abs(predictions - actuals)))
        
        # Directional accuracy: did we predict the right direction?
        if len(test_df) > 1:
            pred_direction = 0  # flat
            actual_direction = 1 if actuals[-1] > actuals[0] else -1 if actuals[-1] < actuals[0] else 0
            directional_accuracy = 1.0 if pred_direction == actual_direction else 0.0
        else:
            directional_accuracy = 0.5
        
        return {
            "rmse": rmse,
            "mae": mae,
            "directional_accuracy": directional_accuracy,
            "baseline_type": "last_value"
        }
    
    @staticmethod
    def moving_average_baseline(
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        window: int = 20
    ) -> Dict[str, float]:
        """
        Moving average baseline: predict using MA of last N periods.
        
        Returns:
            Dict with RMSE, MAE, directional_accuracy
        """
        if len(train_df) < window or len(test_df) == 0:
            return {"error": "insufficient_data"}
        
        ma_value = train_df['close'].tail(window).mean()
        predictions = np.full(len(test_df), ma_value)
        actuals = test_df['close'].values
        
        rmse = float(np.sqrt(np.mean((predictions - actuals) ** 2)))
        mae = float(np.mean(np.abs(predictions - actuals)))
        
        # Directional accuracy
        if len(test_df) > 1:
            pred_direction = 0  # flat
            actual_direction = 1 if actuals[-1] > actuals[0] else -1 if actuals[-1] < actuals[0] else 0
            directional_accuracy = 1.0 if pred_direction == actual_direction else 0.0
        else:
            directional_accuracy = 0.5
        
        return {
            "rmse": rmse,
            "mae": mae,
            "directional_accuracy": directional_accuracy,
            "baseline_type": f"ma_{window}"
        }
    
    @staticmethod
    def linear_trend_baseline(
        train_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Linear trend baseline: fit simple linear trend to training data.
        
        Returns:
            Dict with RMSE, MAE, directional_accuracy
        """
        if len(train_df) < 10 or len(test_df) == 0:
            return {"error": "insufficient_data"}
        
        # Fit linear trend on training data
        train_indices = np.arange(len(train_df))
        train_prices = train_df['close'].values
        
        # Simple linear regression (y = ax + b)
        A = np.vstack([train_indices, np.ones(len(train_indices))]).T
        slope, intercept = np.linalg.lstsq(A, train_prices, rcond=None)[0]
        
        # Predict for test data
        test_indices = np.arange(len(train_df), len(train_df) + len(test_df))
        predictions = slope * test_indices + intercept
        actuals = test_df['close'].values
        
        rmse = float(np.sqrt(np.mean((predictions - actuals) ** 2)))
        mae = float(np.mean(np.abs(predictions - actuals)))
        
        # Directional accuracy
        if len(predictions) > 1:
            pred_direction = 1 if predictions[-1] > predictions[0] else -1 if predictions[-1] < predictions[0] else 0
            actual_direction = 1 if actuals[-1] > actuals[0] else -1 if actuals[-1] < actuals[0] else 0
            directional_accuracy = 1.0 if pred_direction == actual_direction else 0.0
        else:
            directional_accuracy = 0.5
        
        return {
            "rmse": rmse,
            "mae": mae,
            "directional_accuracy": directional_accuracy,
            "baseline_type": "linear_trend",
            "slope": float(slope)
        }
    
    @staticmethod
    def compare_with_baselines(
        model_metrics: Dict[str, float],
        train_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Dict:
        """
        Compare model metrics with all baseline models.
        
        Args:
            model_metrics: Dict with model's RMSE, MAE, etc
            train_df: Training data
            test_df: Test data
        
        Returns:
            Dict with baseline comparisons and improvement percentages
        """
        baselines = {}
        
        # Compute all baselines
        baselines['last_value'] = BaselineModels.last_value_baseline(train_df, test_df)
        baselines['ma_20'] = BaselineModels.moving_average_baseline(train_df, test_df, window=20)
        baselines['linear_trend'] = BaselineModels.linear_trend_baseline(train_df, test_df)
        
        # Find best baseline
        best_baseline_rmse = min(
            b.get('rmse', float('inf')) for b in baselines.values() if 'error' not in b
        )
        
        # Calculate improvement
        model_rmse = model_metrics.get('rmse', float('inf'))
        improvement_pct = 0.0
        
        if best_baseline_rmse > 0 and model_rmse < float('inf'):
            improvement_pct = ((best_baseline_rmse - model_rmse) / best_baseline_rmse) * 100
        
        return {
            "baselines": baselines,
            "best_baseline_rmse": float(best_baseline_rmse),
            "model_rmse": float(model_rmse),
            "improvement_pct": float(improvement_pct),
            "beats_baseline": model_rmse < best_baseline_rmse
        }


# Global instance
baseline_models = BaselineModels()


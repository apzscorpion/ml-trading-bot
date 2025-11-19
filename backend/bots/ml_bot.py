"""
Machine Learning Bot using linear regression.
Uses historical price patterns and features to predict future prices.
"""
from typing import Dict, List
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from .base_bot import BaseBot
import logging
import warnings

# Suppress sklearn numerical warnings globally for this module
warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')

logger = logging.getLogger(__name__)


class MLBot(BaseBot):
    """ML-based prediction bot using linear regression"""
    
    def __init__(self):
        super().__init__("ml_bot")
        self.min_candles = 100
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """
        Predict future prices using machine learning.
        
        Features:
        - Lagged prices (last 5, 10, 20 periods)
        - Rolling mean and std
        - Price momentum
        - Volume trends
        """
        try:
            if len(candles) < self.min_candles:
                logger.warning(f"{self.name}: Not enough candles for ML prediction (got {len(candles)}, need {self.min_candles})")
                return self._empty_prediction()
            
            df = self._candles_to_dataframe(candles)
            
            # Feature engineering
            df = self._create_features(df)
            
            # Drop NaN rows from feature creation
            df = df.dropna()
            
            # Replace inf values with NaN, then drop
            df = df.replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(df) < 50:
                logger.warning(f"{self.name}: Not enough valid data after feature creation")
                return self._empty_prediction()
            
            # Prepare training data
            feature_cols = [col for col in df.columns if col.startswith('feature_')]
            X = df[feature_cols].values
            y = df['close'].values
            
            # Validate data before scaling
            if not np.isfinite(X).all() or not np.isfinite(y).all():
                logger.warning(f"{self.name}: Found invalid values in data, cleaning...")
                valid_mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
                X = X[valid_mask]
                y = y[valid_mask]
                if len(X) < 50:
                    return self._empty_prediction()
            
            # Scale features
            scaler = StandardScaler()
            
            # Check for zero variance features before scaling
            feature_variance = np.var(X, axis=0)
            zero_variance_mask = feature_variance == 0
            
            if zero_variance_mask.any():
                logger.warning(f"{self.name} found {zero_variance_mask.sum()} features with zero variance, removing them")
                X = X[:, ~zero_variance_mask]
                
                if X.shape[1] == 0:
                    return self._empty_prediction()
            
            X_scaled = scaler.fit_transform(X)
            
            # Handle any NaN/Inf that might occur during scaling
            if not np.isfinite(X_scaled).all():
                # Check for constant features after scaling
                scaled_variance = np.var(X_scaled, axis=0)
                constant_features = scaled_variance == 0
                
                if constant_features.any():
                    logger.warning(f"{self.name} found {constant_features.sum()} constant features after scaling, removing them")
                    X_scaled = X_scaled[:, ~constant_features]
                
                X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
                
                if X_scaled.shape[1] == 0:
                    return self._empty_prediction()
            
            # Train model
            model = LinearRegression()
            
            # Suppress warnings during training
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
                model.fit(X_scaled, y)
            
            # Generate predictions
            latest_close = float(df['close'].iloc[-1])
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            predicted_series = []
            current_features = X_scaled[-1:].copy()
            last_close = latest_close
            clipped_predictions = 0
            # Guard rails for step-wise price movement (per 15m candle)
            max_step_change_base = 0.005  # 0.5% change per step baseline
            max_abs_multiplier = 1.05  # absolute +/-5% bound relative to last close
            reference_close = latest_close
            
            for ts in future_timestamps:
                # Predict next price (suppress warnings)
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
                    pred_price = model.predict(current_features)[0]
                
                if not np.isfinite(pred_price):
                    pred_price = last_close
                    clipped_predictions += 1

                if last_close > 0:
                    # Allow slightly larger swings further into the horizon
                    max_step_change = max_step_change_base * (1 + len(predicted_series) / max(1, len(future_timestamps)))
                    rel_change = (pred_price - last_close) / last_close
                    # Clamp extreme jumps
                    if rel_change > max_step_change:
                        pred_price = last_close * (1 + max_step_change)
                        clipped_predictions += 1
                    elif rel_change < -max_step_change:
                        pred_price = last_close * (1 - max_step_change)
                        clipped_predictions += 1
                    # Absolute guard to avoid runaway values
                    upper_bound = reference_close * max_abs_multiplier
                    lower_bound = max(reference_close / max_abs_multiplier, 0)
                    if pred_price > upper_bound:
                        pred_price = upper_bound
                        clipped_predictions += 1
                    elif pred_price < lower_bound:
                        pred_price = lower_bound
                        clipped_predictions += 1
                else:
                    pred_price = max(pred_price, 0.0)

                pred_price = float(pred_price)

                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": pred_price
                })
                
                # Update features for next prediction (simple approach)
                # In production, you'd update all features properly
                current_features = np.roll(current_features, -1)
                current_features[0, -1] = pred_price
                last_close = pred_price
            
            # Enforce global bounds on the full forecast
            upper_bound_global = reference_close * max_abs_multiplier
            lower_bound_global = max(reference_close / max_abs_multiplier, 0)
            if upper_bound_global <= 0:
                upper_bound_global = reference_close  # fallback
            for point in predicted_series:
                price = point["price"]
                if price > upper_bound_global:
                    point["price"] = upper_bound_global
                    clipped_predictions += 1
                elif price < lower_bound_global:
                    point["price"] = lower_bound_global
                    clipped_predictions += 1

            # Calculate confidence based on model's recent performance
            # Use last 20 predictions vs actuals
            if len(df) > 20:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
                    recent_predictions = model.predict(X_scaled[-20:])
                    recent_actuals = y[-20:]
                    mape = np.mean(np.abs((recent_actuals - recent_predictions) / np.clip(recent_actuals, 1e-6, None)))
                    confidence = max(0.3, 1.0 - mape)
            else:
                confidence = 0.6

            if clipped_predictions:
                # Penalise over-confident forecasts when sanitisation was needed
                confidence = max(0.35, min(confidence, 0.6))

            if not np.isfinite(confidence):
                confidence = 0.45

            confidence = float(confidence)
            
            # Calculate R² score for model quality
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
                r2_score = model.score(X_scaled, y)
            
            # Generate trend metadata
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": float(confidence),
                "bot_name": self.name,
                "meta": {
                    "model_type": "linear_regression",
                    "r2_score": float(r2_score),
                    "n_features": len(feature_cols),
                    "training_samples": len(X),
                    "sanitized_predictions": clipped_predictions,
                    **trend_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return self._empty_prediction()
    
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive features for ML model using unified feature engineering"""
        from backend.utils.feature_engineering import engineer_comprehensive_features
        
        # Use comprehensive feature engineering
        features_df = engineer_comprehensive_features(
            df,
            include_indicators=True,
            include_volume_features=True,
            include_price_features=True,
            include_returns_features=True
        )
        
        # Add lagged features for time series context
        features_df['feature_lag_1'] = features_df['close'].shift(1)
        features_df['feature_lag_5'] = features_df['close'].shift(5)
        features_df['feature_lag_10'] = features_df['close'].shift(10)
        
        # Prefix all feature columns for ML model
        feature_cols = [col for col in features_df.columns 
                       if col not in ['start_ts', 'open', 'high', 'low', 'close', 'volume']]
        
        # Rename to feature_ prefix for consistency
        rename_dict = {col: f'feature_{col}' for col in feature_cols}
        features_df = features_df.rename(columns=rename_dict)
        
        return features_df
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction on error"""
        return {
            "predicted_series": [],
            "confidence": 0.0,
            "bot_name": self.name,
            "meta": {"error": "prediction_failed"}
        }
    
    async def train(self, candles: List[Dict], epochs: int = None, **kwargs):
        """
        MLBot trains on-the-fly during prediction, so this is a no-op.
        However, we implement it for compatibility with the training system.
        """
        logger.info(f"{self.name} does not require separate training - trains on-the-fly during prediction")
        return {
            "status": "success",
            "message": "MLBot trains on-the-fly during prediction, no separate training needed"
        }


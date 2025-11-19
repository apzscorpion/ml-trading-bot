"""
Ensemble ML Bot - Combines Multiple Machine Learning Models
Uses Random Forest, Gradient Boosting, and other classical ML models.
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime, timedelta
import os
import pickle
import warnings

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.multioutput import MultiOutputRegressor
    SKLEARN_AVAILABLE = True
    # Suppress sklearn numerical warnings globally for this module
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
except ImportError:
    SKLEARN_AVAILABLE = False
    from backend.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.warning("scikit-learn not available. Ensemble bot will use fallback.")

from backend.bots.base_bot import BaseBot
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class EnsembleBot(BaseBot):
    """Ensemble ML bot combining multiple models"""
    
    name = "ensemble_bot"
    
    def __init__(self):
        super().__init__("ensemble_bot")  # Use string literal instead of self.name
        self.models = {}
        self.scaler = None
        self.feature_names = []
        self.lookback = 40
        self.model_path = "models/ensemble_models.pkl"
        
        if SKLEARN_AVAILABLE:
            self._load_or_create_models()
    
    def _load_or_create_models(self):
        """Load existing models or create new ones"""
        try:
            model_path = self.get_model_path(self.model_path)
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    saved = pickle.load(f)
                    self.models = saved['models']
                    self.scaler = saved['scaler']
                    self.feature_names = saved['feature_names']
                logger.info(f"{self.name} loaded existing models")
            else:
                self._create_models()
                logger.info(f"{self.name} created new models")
        except Exception as e:
            logger.error(f"{self.name} error loading models: {e}")
            self._create_models()
    
    def _create_models(self):
        """Create ensemble of ML models"""
        if not SKLEARN_AVAILABLE:
            return
        
        # Multiple models for ensemble
        self.models = {
            'random_forest': RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            ),
            'gradient_boosting': GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            ),
            'ridge': Ridge(alpha=1.0)
        }
        
        self.scaler = StandardScaler()
        self.feature_names = []
    
    def _are_models_fitted(self) -> bool:
        """Check if models are fitted and ready for prediction"""
        if not self.models or not self.scaler:
            return False
        
        # Check if scaler is fitted
        if not hasattr(self.scaler, 'mean_'):
            return False
        
        # Check if at least one model is fitted
        for model_name, model in self.models.items():
            if hasattr(model, 'n_features_in_'):
                # Tree-based models (RandomForest, GradientBoosting)
                return True
            elif hasattr(model, 'coef_'):
                # Linear models (Ridge)
                return True
        
        return False
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """Generate ensemble prediction"""
        
        try:
            if not SKLEARN_AVAILABLE or not self.models:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Check if models are fitted before attempting prediction
            if not self._are_models_fitted():
                # Only log once per session to avoid spam
                if not hasattr(self, '_fit_warning_logged'):
                    logger.warning(f"{self.name} models not fitted yet. Use fallback prediction. Train models first via /api/prediction/train")
                    self._fit_warning_logged = True
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            if len(candles) < self.lookback:
                logger.warning(f"{self.name} needs at least {self.lookback} candles")
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Prepare data
            df = pd.DataFrame(candles)
            features_df = self._engineer_features(df)
            
            if len(features_df) < 10:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Get recent features (last lookback periods)
            recent_features = features_df.tail(self.lookback)
            
            # Drop NaN rows (from rolling calculations)
            recent_features = recent_features.dropna()
            
            # Replace inf values
            recent_features = recent_features.replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(recent_features) < self.lookback:
                logger.warning(f"{self.name} not enough valid features after dropna (got {len(recent_features)}, need {self.lookback})")
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Ensure we have exactly lookback periods
            recent_features = recent_features.tail(self.lookback)
            
            # Validate features are finite
            if not np.isfinite(recent_features.values).all():
                logger.warning(f"{self.name} found invalid values in features, using fallback")
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Check if scaler exists and has the right shape
            if hasattr(self.scaler, 'mean_'):
                # Get expected feature count from scaler
                expected_features = self.scaler.mean_.shape[0]
                # We need lookback * features_per_period
                features_per_period = len(recent_features.columns)
                expected_total = self.lookback * features_per_period
                
                if expected_features != expected_total:
                    logger.warning(f"{self.name} scaler mismatch: expected {expected_features} features, but have {expected_total} (lookback={self.lookback}, features_per_period={features_per_period})")
                    # Model/scaler mismatch - use fallback instead of crashing
                    logger.info(f"{self.name} using fallback prediction due to feature mismatch. Retrain models to fix.")
                    return self._fallback_prediction(candles, horizon_minutes, timeframe)
                else:
                    # Flatten BEFORE scaling (scaler expects flattened input)
                    features_flat = recent_features.values.flatten().reshape(1, -1)
                    
                    # Validate features before scaling
                    if not np.isfinite(features_flat).all():
                        logger.warning(f"{self.name} invalid values in features before scaling, using fallback")
                        return self._fallback_prediction(candles, horizon_minutes, timeframe)
                    
                    features_scaled = self.scaler.transform(features_flat)
                    
                    # Validate after scaling
                    if not np.isfinite(features_scaled).all():
                        features_scaled = np.nan_to_num(features_scaled, nan=0.0, posinf=0.0, neginf=0.0)
            else:
                # No scaler, just flatten
                features_scaled = recent_features.values.flatten().reshape(1, -1)
            
            # X is already in the right shape (1, num_features)
            X = features_scaled
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            last_close = float(df['close'].iloc[-1])
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            # Make predictions with each model
            model_predictions = {}
            model_weights = {
                'random_forest': 0.40,
                'gradient_boosting': 0.35,
                'ridge': 0.25
            }
            
            predicted_series = []
            
            for i, ts in enumerate(future_timestamps):
                predictions = []
                weights = []
                
                for model_name, model in self.models.items():
                    try:
                        # Check if model is fitted before predicting
                        is_fitted = False
                        if hasattr(model, 'n_features_in_'):
                            is_fitted = True  # Tree-based models
                        elif hasattr(model, 'coef_'):
                            is_fitted = True  # Linear models
                        
                        if not is_fitted:
                            # Skip unfitted models silently (already checked at start)
                            continue
                        
                        if hasattr(model, 'predict'):
                            # Suppress warnings during prediction
                            with warnings.catch_warnings():
                                warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
                                pred = model.predict(X)[0]
                            predictions.append(pred)
                            weights.append(model_weights.get(model_name, 0.33))
                    except Exception as e:
                        # Only log once per model to avoid spam
                        if not hasattr(self, f'_model_error_logged_{model_name}'):
                            logger.warning(f"{self.name} model {model_name} prediction failed: {e}")
                            setattr(self, f'_model_error_logged_{model_name}', True)
                        continue
                
                if predictions:
                    # Weighted ensemble
                    ensemble_pred = np.average(predictions, weights=weights)
                    
                    # Apply constraints
                    max_change = 0.012 * (1 + i / len(future_timestamps))
                    change = (ensemble_pred - last_close) / last_close
                    change = np.clip(change, -max_change, max_change)
                    predicted_price = last_close * (1 + change)
                else:
                    # Fallback to last close
                    predicted_price = last_close
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
                
                # Update for next iteration
                last_close = predicted_price
            
            # Calculate confidence
            returns = df['close'].pct_change().dropna()
            volatility = float(returns.std())
            
            # Higher confidence for ensemble
            confidence_base = 0.82
            confidence = confidence_base * (1 - min(volatility * 7, 0.35))
            
            # Generate trend metadata
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": confidence,
                "bot_name": self.name,
                "meta": {
                    "model_type": "Ensemble",
                    "models_used": list(self.models.keys()),
                    "lookback_periods": self.lookback,
                    "volatility": volatility,
                    "features_count": len(self.feature_names) if self.feature_names else 0,
                    **trend_metadata
                }
            }
            
        except Exception as e:
            logger.error(
                f"{self.name} prediction error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return self._fallback_prediction(candles, horizon_minutes, timeframe)
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer comprehensive features for ML models using unified feature engineering"""
        from backend.utils.feature_engineering import engineer_comprehensive_features
        
        # Use comprehensive feature engineering
        features_df = engineer_comprehensive_features(
            df,
            include_indicators=True,
            include_volume_features=True,
            include_price_features=True,
            include_returns_features=True
        )
        
        # Ensure we have the core columns for ensemble models
        core_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in core_cols:
            if col not in features_df.columns:
                features_df[col] = df.get(col, 0)
        
        # Fill NaN values
        features_df = features_df.ffill().bfill().fillna(0)
        
        # Replace infinite values
        features_df = features_df.replace([np.inf, -np.inf], 0)
        
        return features_df
    
    def _fallback_prediction(self, candles: List[Dict], horizon_minutes: int, timeframe: str) -> Dict:
        """Fallback prediction using statistical analysis"""
        try:
            df = pd.DataFrame(candles)
            last_close = float(df['close'].iloc[-1])
            
            # Multiple trend indicators
            short_ma = df['close'].tail(5).mean()
            medium_ma = df['close'].tail(10).mean()
            long_ma = df['close'].tail(20).mean()
            
            trend = (short_ma / long_ma - 1) * 0.5 + (medium_ma / long_ma - 1) * 0.3
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            predicted_series = []
            for i, ts in enumerate(future_timestamps):
                damping = 1.0 - (i / len(future_timestamps)) * 0.55
                predicted_price = last_close * (1 + trend * damping * 0.45)
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
            
            return {
                "predicted_series": predicted_series,
                "confidence": 0.42,
                "bot_name": self.name,
                "meta": {
                    "model_type": "fallback",
                    "trend": float(trend)
                }
            }
        except Exception as e:
            logger.error(f"{self.name} fallback error: {e}")
            return self._empty_prediction()
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction on error"""
        return {
            "predicted_series": [],
            "confidence": 0.0,
            "bot_name": self.name,
            "meta": {"error": "prediction_failed"}
        }
    
    async def train(self, candles: List[Dict], test_size: float = 0.2, epochs: int = None, **kwargs):
        """Train all ensemble models
        
        Args:
            candles: Historical candle data
            test_size: Fraction of data to use for testing (default 0.2)
            epochs: Ignored (for compatibility with deep learning bots)
            **kwargs: Additional arguments (ignored)
        """
        if not SKLEARN_AVAILABLE or not self.models:
            logger.error(f"{self.name} cannot train without scikit-learn")
            return {"error": "scikit-learn not available"}
        
        try:
            from backend.ml.data_loader import ml_data_loader
            
            # Use unified data loader if symbol/timeframe context is available
            if hasattr(self, '_current_symbol') and hasattr(self, '_current_timeframe'):
                df_loaded, metadata = await ml_data_loader.get_training_window(
                    self._current_symbol,
                    self._current_timeframe,
                    days=90
                )
                
                if df_loaded is None:
                    logger.error(f"{self.name} data loader failed: {metadata}")
                    return {"error": metadata.get("message", "Data loading failed")}
                
                df = df_loaded
                logger.info(f"{self.name} loaded {len(df)} candles via data_loader", extra=metadata)
            else:
                # Fallback to legacy candle list
                df = pd.DataFrame(candles)
                logger.warning(f"{self.name} using legacy candle list (no context set)")
            
            features_df = self._engineer_features(df)
            
            if len(features_df) < self.lookback + 20:
                return {"error": f"Not enough data for training: {len(features_df)} < {self.lookback + 20}"}
            
            # Prepare training data
            X, y = [], []
            for i in range(self.lookback, len(features_df) - 1):
                X.append(features_df.iloc[i-self.lookback:i].values.flatten())
                y.append(features_df['close'].iloc[i + 1])
            
            X = np.array(X)
            y = np.array(y)
            
            # Remove rows with NaN, Inf, or extreme values
            valid_mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
            X = X[valid_mask]
            y = y[valid_mask]
            
            if len(X) < self.lookback + 10:
                return {"error": "Not enough valid data after cleaning"}
            
            # Scale features
            # Check for zero variance features before scaling (causes divide by zero in StandardScaler)
            feature_variance = np.var(X, axis=0)
            zero_variance_mask = feature_variance == 0
            
            if zero_variance_mask.any():
                logger.warning(f"{self.name} found {zero_variance_mask.sum()} features with zero variance, removing them")
                # Remove zero variance features
                X = X[:, ~zero_variance_mask]
                
                if X.shape[1] == 0:
                    return {"error": "All features have zero variance"}
            
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            # Validate scaling results
            if not np.isfinite(X_scaled).all():
                # Find problematic features
                invalid_mask = ~np.isfinite(X_scaled)
                invalid_cols = np.any(invalid_mask, axis=0)
                
                if invalid_cols.any():
                    logger.warning(f"{self.name} found {invalid_cols.sum()} features with invalid values after scaling, removing them")
                    X_scaled = X_scaled[:, ~invalid_cols]
                    
                    if X_scaled.shape[1] == 0:
                        return {"error": "All features invalid after scaling"}
                
                # Replace any remaining NaN/Inf with 0
                X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Additional check: ensure no extreme values that could cause overflow
            max_val = np.abs(X_scaled).max()
            if max_val > 1e6:
                logger.warning(f"{self.name} found extreme values in scaled features (max={max_val:.2e}), clipping")
                X_scaled = np.clip(X_scaled, -1e6, 1e6)
            
            # Store feature names
            self.feature_names = list(features_df.columns)
            
            # Split train/test
            split_idx = int(len(X_scaled) * (1 - test_size))
            X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Final validation - ensure no invalid values before training
            if not np.isfinite(X_train).all() or not np.isfinite(y_train).all():
                logger.warning(f"{self.name} found invalid values in training data, cleaning...")
                train_mask = np.isfinite(X_train).all(axis=1) & np.isfinite(y_train)
                X_train = X_train[train_mask]
                y_train = y_train[train_mask]
                
                if len(X_train) < 10:
                    return {"error": "Not enough valid training data after cleaning"}
                
                # Recalculate split for test set
                test_mask = np.isfinite(X_test).all(axis=1) & np.isfinite(y_test)
                X_test = X_test[test_mask]
                y_test = y_test[test_mask]
            
            # Train each model in thread pool to avoid blocking event loop
            # model.fit() and model.score() are CPU-bound operations
            import asyncio
            
            async def _train_model_async(model_name, model):
                """Train a single model in thread pool"""
                def _train_and_score():
                    # Suppress sklearn warnings for this specific training
                    with warnings.catch_warnings():
                        warnings.filterwarnings('ignore', category=RuntimeWarning, module='sklearn')
                        try:
                            model.fit(X_train, y_train)
                            train_score = model.score(X_train, y_train)
                            test_score = model.score(X_test, y_test)
                            return train_score, test_score
                        except Exception as e:
                            logger.error(f"{self.name} error training {model_name}: {e}")
                            raise
                
                loop = asyncio.get_event_loop()
                train_score, test_score = await loop.run_in_executor(None, _train_and_score)
                return train_score, test_score
            
            # Train all models concurrently (each in its own thread)
            results = {}
            training_tasks = {
                model_name: _train_model_async(model_name, model)
                for model_name, model in self.models.items()
            }
            
            # Track training start time before training
            from datetime import datetime
            training_start_time = datetime.utcnow()
            
            # Wait for all training to complete concurrently
            training_results = await asyncio.gather(*training_tasks.values(), return_exceptions=True)
            
            # Process results
            for (model_name, _), result in zip(training_tasks.items(), training_results):
                if isinstance(result, Exception):
                    logger.error(f"{self.name} error training {model_name}: {result}")
                    results[model_name] = {"error": str(result)}
                else:
                    train_score, test_score = result
                    results[model_name] = {
                        "train_score": float(train_score),
                        "test_score": float(test_score)
                    }
                    logger.info(f"{self.name} trained {model_name}: test R²={test_score:.4f}")
            
            # Generate model version
            from datetime import datetime
            import hashlib
            
            data_hash = hashlib.md5(str(len(candles)).encode()).hexdigest()[:8]
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            model_version = f"v1.0.{timestamp}"
            dataset_version = f"dataset_v1_{data_hash}"
            training_start = candles[0].get("start_ts") if candles else None
            training_end = candles[-1].get("start_ts") if candles else None
            training_window = f"{training_start}_{training_end}"
            
            hyperparams = {
                "lookback": self.lookback,
                "models": list(self.models.keys()),
                "feature_count": len(self.feature_names)
            }
            
            # Save models
            model_path = self.get_model_path(self.model_path)
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'models': self.models,
                    'scaler': self.scaler,
                    'feature_names': self.feature_names,
                    'model_version': model_version,
                    'dataset_version': dataset_version,
                    'hyperparams': hyperparams,
                    'training_window': training_window
                }, f)
            
            training_duration = (datetime.utcnow() - training_start_time).total_seconds()
            
            # Store training record in database
            try:
                from backend.database import SessionLocal, ModelTrainingRecord
                db = SessionLocal()
                training_record = ModelTrainingRecord(
                    symbol=self._current_symbol or "unknown",
                    timeframe=self._current_timeframe or "unknown",
                    bot_name=self.name,
                    trained_at=datetime.utcnow(),
                    training_duration_seconds=training_duration,
                    data_points_used=len(candles),
                    training_period=training_window,
                    epochs=0,  # Ensemble doesn't use epochs
                    status='active',
                    config={
                        "model_version": model_version,
                        "dataset_version": dataset_version,
                        "hyperparams": hyperparams,
                        "training_window": training_window,
                        "training_results": results
                    }
                )
                db.add(training_record)
                db.commit()
                db.close()
            except Exception as e:
                logger.warning(f"Failed to store training record: {e}")
            
            logger.info(
                f"{self.name} training completed",
                model_version=model_version,
                dataset_version=dataset_version
            )
            
            # Reset warning flags after successful training
            if hasattr(self, '_fit_warning_logged'):
                delattr(self, '_fit_warning_logged')
            for model_name in self.models.keys():
                attr_name = f'_model_error_logged_{model_name}'
                if hasattr(self, attr_name):
                    delattr(self, attr_name)
            
            return {
                "status": "success",
                "model_version": model_version,
                "dataset_version": dataset_version,
                "results": results,
                "features_count": len(self.feature_names),
                "training_duration_seconds": training_duration,
                "hyperparams": hyperparams
            }
            
        except Exception as e:
            logger.error(
                f"{self.name} training error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return {"error": str(e)}


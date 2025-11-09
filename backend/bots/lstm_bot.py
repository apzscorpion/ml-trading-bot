"""
LSTM Neural Network Bot for Time Series Prediction
Uses TensorFlow/Keras to build a deep learning model for stock price prediction.
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime, timedelta
import os
import pickle

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    import warnings
    
    # Suppress TensorFlow data function warnings (harmless)
    warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow.python.data.ops.structured_function')
    
    # Enable eager execution (should be default in TF 2.x, but ensure it's on)
    tf.config.run_functions_eagerly(True)
    
    # Set TensorFlow to use eager execution
    if not tf.executing_eagerly():
        tf.config.run_functions_eagerly(True)
    
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    from backend.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.warning("TensorFlow not available. LSTM bot will use fallback predictions.")

from backend.bots.base_bot import BaseBot
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class LSTMBot(BaseBot):
    """LSTM-based prediction bot using deep learning"""
    
    name = "lstm_bot"
    
    def __init__(self):
        super().__init__("lstm_bot")  # Use string literal instead of self.name
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.sequence_length = 60  # Use last 60 candles for prediction
        self.model_path = "models/lstm_model.keras"
        self.scaler_path = "models/lstm_scalers.pkl"
        
        if TENSORFLOW_AVAILABLE:
            self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new one"""
        try:
            # Use dynamic path based on current context
            model_path = self.get_model_path(self.model_path)
            scaler_path = self.get_model_path(self.scaler_path)
            
            # Also check for old .h5 format for backward compatibility
            old_model_path = model_path.replace('.keras', '.h5')
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = keras.models.load_model(model_path)
                # CRITICAL: Recompile immediately after loading to reset optimizer state
                # This prevents "Unknown variable" errors when training loaded models
                self.model.compile(
                    optimizer=keras.optimizers.Adam(learning_rate=0.001),
                    loss='huber',
                    metrics=['mae']
                )
                with open(scaler_path, 'rb') as f:
                    scalers = pickle.load(f)
                    self.scaler_X = scalers['scaler_X']
                    self.scaler_y = scalers['scaler_y']
                logger.info(f"{self.name} loaded existing model and recompiled optimizer")
            elif os.path.exists(old_model_path) and os.path.exists(scaler_path):
                # Load old .h5 format and migrate to .keras
                logger.info(f"{self.name} loading legacy .h5 model, will migrate to .keras format")
                self.model = keras.models.load_model(old_model_path)
                # CRITICAL: Recompile immediately after loading to reset optimizer state
                self.model.compile(
                    optimizer=keras.optimizers.Adam(learning_rate=0.001),
                    loss='huber',
                    metrics=['mae']
                )
                # Load scalers
                with open(scaler_path, 'rb') as f:
                    scalers = pickle.load(f)
                    self.scaler_X = scalers['scaler_X']
                    self.scaler_y = scalers['scaler_y']
                # Save in new format and remove old file
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                # Explicitly save in Keras format (not HDF5)
                if model_path.endswith('.keras'):
                    self.model.save(model_path, save_format='keras')
                else:
                    self.model.save(model_path)
                try:
                    os.remove(old_model_path)
                    logger.info(f"{self.name} migrated model from .h5 to .keras format")
                except Exception as e:
                    logger.warning(f"{self.name} could not remove old .h5 file: {e}")
                logger.info(f"{self.name} loaded and migrated legacy model")
            else:
                self._create_model()
                logger.info(f"{self.name} created new model")
        except Exception as e:
            logger.error(f"{self.name} error loading model: {e}")
            self._create_model()
    
    def _create_model(self):
        """Create a new LSTM model"""
        if not TENSORFLOW_AVAILABLE:
            return
        
        # Model architecture - use Input layer instead of input_shape parameter
        inputs = layers.Input(shape=(self.sequence_length, 5))
        x = layers.LSTM(128, return_sequences=True)(inputs)
        x = layers.Dropout(0.2)(x)
        x = layers.LSTM(64, return_sequences=True)(x)
        x = layers.Dropout(0.2)(x)
        x = layers.LSTM(32, return_sequences=False)(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(32, activation='relu')(x)
        x = layers.Dense(16, activation='relu')(x)
        outputs = layers.Dense(1)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='huber',
            metrics=['mae']
        )
        
        self.model = model
        
        # Initialize scalers
        from sklearn.preprocessing import StandardScaler
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """Generate LSTM-based prediction"""
        
        try:
            if not TENSORFLOW_AVAILABLE or self.model is None:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            if len(candles) < self.sequence_length:
                logger.warning(f"{self.name} needs at least {self.sequence_length} candles")
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Prepare data
            df = pd.DataFrame(candles)
            
            # Feature engineering
            features = self._prepare_features(df)
            
            if len(features) < self.sequence_length:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Get last sequence
            last_sequence = features[-self.sequence_length:].values
            
            # Normalize
            last_sequence_scaled = last_sequence.copy()
            if hasattr(self.scaler_X, 'mean_'):
                last_sequence_scaled = self.scaler_X.transform(last_sequence)
            
            # Make prediction
            last_sequence_scaled = last_sequence_scaled.reshape(1, self.sequence_length, -1)
            
            # Generate future predictions minute by minute
            predicted_series = []
            current_sequence = last_sequence_scaled.copy()
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            last_close = float(df['close'].iloc[-1])
            
            # Generate predictions for each minute
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            confidence_base = 0.75
            
            for i, ts in enumerate(future_timestamps):
                # Predict next price
                prediction_scaled = self.model.predict(current_sequence, verbose=0)
                
                # Denormalize if scaler is fitted
                if hasattr(self.scaler_y, 'mean_'):
                    prediction = self.scaler_y.inverse_transform(prediction_scaled)[0][0]
                else:
                    prediction = prediction_scaled[0][0]
                
                # Apply realistic constraints
                max_change = 0.02 * (1 + i / len(future_timestamps))  # Max 2% change per step, increasing
                predicted_price = last_close * (1 + np.clip(prediction / last_close - 1, -max_change, max_change))
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
                
                # Update sequence for next prediction
                # Add the predicted value to the sequence
                new_features = np.array([[predicted_price, predicted_price, predicted_price, predicted_price, 0]])
                if hasattr(self.scaler_X, 'mean_'):
                    new_features = self.scaler_X.transform(new_features)
                
                current_sequence = np.concatenate([
                    current_sequence[:, 1:, :],
                    new_features.reshape(1, 1, -1)
                ], axis=1)
                
                last_close = predicted_price
            
            # Calculate confidence based on recent volatility
            returns = df['close'].pct_change().dropna()
            volatility = float(returns.std())
            confidence = confidence_base * (1 - min(volatility * 10, 0.4))
            
            # Generate trend metadata
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": confidence,
                "bot_name": self.name,
                "meta": {
                    "model_type": "LSTM",
                    "sequence_length": self.sequence_length,
                    "volatility": volatility,
                    "data_points_used": len(df),
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
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for LSTM model"""
        features = pd.DataFrame()
        features['open'] = df['open']
        features['high'] = df['high']
        features['low'] = df['low']
        features['close'] = df['close']
        features['volume'] = df['volume']
        
        return features.dropna()
    
    def _fallback_prediction(self, candles: List[Dict], horizon_minutes: int, timeframe: str) -> Dict:
        """Fallback prediction using simple trend analysis"""
        try:
            df = pd.DataFrame(candles)
            last_close = float(df['close'].iloc[-1])
            
            # Calculate trend
            recent_prices = df['close'].tail(20)
            trend = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            
            # Generate predictions
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            predicted_series = []
            for i, ts in enumerate(future_timestamps):
                damping = 1.0 - (i / len(future_timestamps)) * 0.5
                predicted_price = last_close * (1 + trend * damping * 0.5)
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
            
            return {
                "predicted_series": predicted_series,
                "confidence": 0.35,
                "bot_name": self.name,
                "meta": {
                    "model_type": "fallback",
                    "trend": float(trend)
                }
            }
        except Exception as e:
            logger.error(f"{self.name} fallback prediction error: {e}")
            return self._empty_prediction()
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction on error"""
        return {
            "predicted_series": [],
            "confidence": 0.0,
            "bot_name": self.name,
            "meta": {"error": "prediction_failed"}
        }
    
    async def train(self, candles: List[Dict], epochs: int = 50):
        """Train the LSTM model on historical data"""
        if not TENSORFLOW_AVAILABLE or self.model is None:
            logger.error(f"{self.name} cannot train without TensorFlow")
            return {"error": "TensorFlow not available"}
        
        try:
            from datetime import datetime
            import hashlib
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
            
            features = self._prepare_features(df)
            
            if len(features) < self.sequence_length + 10:
                return {"error": f"Not enough data for training: {len(features)} < {self.sequence_length + 10}"}
            
            # Generate model version
            # Version format: v1.0.0, v1.1.0, etc.
            # Use timestamp and data hash to create unique version
            data_hash = hashlib.md5(str(len(candles)).encode()).hexdigest()[:8]
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            model_version = f"v1.0.{timestamp}"
            
            # Dataset version (based on data range)
            dataset_version = f"dataset_v1_{data_hash}"
            
            # Training window
            training_start = candles[0].get("start_ts") if candles else None
            training_end = candles[-1].get("start_ts") if candles else None
            training_window = f"{training_start}_{training_end}"
            
            # Hyperparameters
            hyperparams = {
                "epochs": epochs,
                "batch_size": 32,
                "sequence_length": self.sequence_length,
                "learning_rate": 0.001,
                "loss": "huber",
                "optimizer": "Adam"
            }
            
            # CRITICAL: Recompile model before training to fix optimizer state
            # This fixes "Unknown variable" errors when loading saved models
            self.model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='huber',
                metrics=['mae']
            )
            
            # Prepare sequences
            X, y = [], []
            for i in range(self.sequence_length, len(features)):
                X.append(features.iloc[i-self.sequence_length:i].values)
                y.append(features['close'].iloc[i])
            
            X = np.array(X)
            y = np.array(y).reshape(-1, 1)
            
            # Ensure scalers are initialized
            if self.scaler_X is None or self.scaler_y is None:
                from sklearn.preprocessing import StandardScaler
                logger.warning(f"{self.name} scalers missing before training – reinitializing")
                self.scaler_X = StandardScaler()
                self.scaler_y = StandardScaler()
            
            # Normalize
            X_reshaped = X.reshape(-1, X.shape[-1])
            self.scaler_X.fit(X_reshaped)
            X_scaled = self.scaler_X.transform(X_reshaped).reshape(X.shape)
            
            self.scaler_y.fit(y)
            y_scaled = self.scaler_y.transform(y)
            
            # Ensure arrays are numpy arrays (not TensorFlow tensors)
            X_scaled = np.array(X_scaled)
            y_scaled = np.array(y_scaled)
            
            # Train in thread pool to avoid blocking event loop
            # model.fit() is CPU-bound and blocks the async event loop
            import asyncio
            
            training_start_time = datetime.utcnow()
            
            def _train_model():
                """CPU-bound training function to run in thread pool"""
                return self.model.fit(
                    X_scaled, y_scaled,
                    epochs=epochs,
                    batch_size=32,
                    validation_split=0.2,
                    verbose=0
                )
            
            # Run training in thread pool executor (non-blocking for event loop)
            loop = asyncio.get_event_loop()
            history = await loop.run_in_executor(None, _train_model)
            
            training_duration = (datetime.utcnow() - training_start_time).total_seconds()
            
            # Save model (also CPU-bound, run in thread pool)
            def _save_model():
                model_path = self.get_model_path(self.model_path)
                scaler_path = self.get_model_path(self.scaler_path)
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                # Explicitly save in Keras format (not HDF5)
                if model_path.endswith('.keras'):
                    self.model.save(model_path, save_format='keras')
                else:
                    self.model.save(model_path)
                with open(scaler_path, 'wb') as f:
                    pickle.dump({
                        'scaler_X': self.scaler_X,
                        'scaler_y': self.scaler_y,
                        'model_version': model_version,
                        'dataset_version': dataset_version,
                        'hyperparams': hyperparams,
                        'training_window': training_window
                    }, f)
            
            await loop.run_in_executor(None, _save_model)
            
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
                    epochs=epochs,
                    training_loss=float(history.history['loss'][-1]),
                    validation_loss=float(history.history.get('val_loss', [0])[-1]),
                    status='active',
                    config={
                        "model_version": model_version,
                        "dataset_version": dataset_version,
                        "hyperparams": hyperparams,
                        "training_window": training_window
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
            
            return {
                "status": "success",
                "model_version": model_version,
                "dataset_version": dataset_version,
                "final_loss": float(history.history['loss'][-1]),
                "final_mae": float(history.history['mae'][-1]),
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


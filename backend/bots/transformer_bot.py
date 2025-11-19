"""
Transformer-based Bot for Time Series Prediction
Uses attention mechanisms for advanced pattern recognition.
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
    logger.warning("TensorFlow not available. Transformer bot will use fallback.")

from backend.bots.base_bot import BaseBot
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TransformerBlock(layers.Layer):
    """Transformer block with multi-head attention"""
    
    def __init__(self, *args, **kwargs):
        # Completely flexible signature to handle Keras model loading
        # Keras may pass arguments in various formats during model reconstruction
        
        # Extract parameters from kwargs first
        embed_dim = kwargs.pop('embed_dim', None)
        num_heads = kwargs.pop('num_heads', None)
        ff_dim = kwargs.pop('ff_dim', None)
        rate = kwargs.pop('rate', 0.1)
        
        # Handle positional arguments (for backward compatibility)
        # Original calls: TransformerBlock(embed_dim, num_heads, ff_dim, rate)
        if len(args) >= 1 and embed_dim is None:
            embed_dim = args[0]
        if len(args) >= 2 and num_heads is None:
            num_heads = args[1]
        if len(args) >= 3 and ff_dim is None:
            ff_dim = args[2]
        if len(args) >= 4:
            rate = args[3]
        
        # Validate required parameters
        if embed_dim is None or num_heads is None or ff_dim is None:
            # Try to get from config if it's in kwargs
            config = kwargs.get('config', {})
            if isinstance(config, dict):
                embed_dim = embed_dim or config.get('embed_dim')
                num_heads = num_heads or config.get('num_heads')
                ff_dim = ff_dim or config.get('ff_dim')
                rate = config.get('rate', rate)
        
        # Final validation
        if embed_dim is None or num_heads is None or ff_dim is None:
            raise ValueError(f"TransformerBlock requires embed_dim, num_heads, and ff_dim. Got args={args}, kwargs_keys={list(kwargs.keys())}")
        
        # Filter out Keras internal kwargs that shouldn't be passed to parent
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ['trainable', 'name', 'dtype', 'batch_input_shape', 'input_shape']}
        super().__init__(**filtered_kwargs)
        
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.ff_dim = ff_dim
        self.rate = rate
        self.att = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)
        self.ffn = keras.Sequential([
            layers.Dense(ff_dim, activation="relu"),
            layers.Dense(embed_dim),
        ])
        self.layernorm1 = layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = layers.Dropout(rate)
        self.dropout2 = layers.Dropout(rate)

    def get_config(self):
        """Get config for serialization"""
        config = super().get_config()
        config.update({
            'embed_dim': self.embed_dim,
            'num_heads': self.num_heads,
            'ff_dim': self.ff_dim,
            'rate': self.rate,
        })
        return config

    @classmethod
    def from_config(cls, config):
        """Create instance from config (handles both old and new formats)"""
        # Make a copy to avoid mutating the original
        config = config.copy() if isinstance(config, dict) else dict(config)
        
        # Extract our custom parameters
        embed_dim = config.pop('embed_dim', None)
        num_heads = config.pop('num_heads', None)
        ff_dim = config.pop('ff_dim', None)
        rate = config.pop('rate', 0.1)
        
        # If any required params are missing, raise error
        if embed_dim is None or num_heads is None or ff_dim is None:
            raise ValueError(f"Missing required parameters in config: embed_dim={embed_dim}, num_heads={num_heads}, ff_dim={ff_dim}")
        
        # Remove Keras internal params that shouldn't be passed to __init__
        # These are handled by the parent Layer class
        for key in ['trainable', 'name', 'dtype', 'batch_input_shape', 'input_shape']:
            config.pop(key, None)
        
        # Create instance with keyword arguments only
        return cls(embed_dim=embed_dim, num_heads=num_heads, ff_dim=ff_dim, rate=rate, **config)

    def call(self, inputs, training=None):
        attn_output = self.att(inputs, inputs)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(inputs + attn_output)
        ffn_output = self.ffn(out1)
        ffn_output = self.dropout2(ffn_output, training=training)
        return self.layernorm2(out1 + ffn_output)


class TransformerBot(BaseBot):
    """Transformer-based prediction bot with attention mechanism"""
    
    name = "transformer_bot"
    
    def __init__(self):
        super().__init__("transformer_bot")  # Use string literal instead of self.name
        self.model = None
        self.scaler = None
        self.sequence_length = 50
        self.model_path = "models/transformer_model.keras"
        self.scaler_path = "models/transformer_scaler.pkl"
        
        if TENSORFLOW_AVAILABLE:
            self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one"""
        try:
            # Use dynamic path based on current context
            model_path = self.get_model_path(self.model_path)
            scaler_path = self.get_model_path(self.scaler_path)
            
            # Also check for old .h5 format for backward compatibility
            old_model_path = model_path.replace('.keras', '.h5')
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                # Custom objects needed for loading
                custom_objects = {'TransformerBlock': TransformerBlock}
                self.model = keras.models.load_model(model_path, custom_objects=custom_objects)
            elif os.path.exists(old_model_path) and os.path.exists(scaler_path):
                # Load old .h5 format and migrate to .keras
                logger.info(f"{self.name} loading legacy .h5 model, will migrate to .keras format")
                custom_objects = {'TransformerBlock': TransformerBlock}
                self.model = keras.models.load_model(old_model_path, custom_objects=custom_objects)
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
                # CRITICAL: Recompile immediately after loading to reset optimizer state
                # This prevents "Unknown variable" errors when training loaded models
                try:
                    # Always recompile to reset optimizer state
                    self.model.compile(
                        optimizer=keras.optimizers.Adam(learning_rate=0.001),
                        loss='huber',
                        metrics=['mae']
                    )
                except Exception as compile_error:
                    # If compilation fails, log warning but continue
                    # The model will be recompiled during training anyway
                    logger.warning(f"{self.name} recompilation warning: {compile_error}, will recompile during training")
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info(f"{self.name} loaded existing model and recompiled optimizer")
            else:
                self._create_model()
                logger.info(f"{self.name} created new model")
        except (TypeError, ValueError) as e:
            # Model file is incompatible (likely from old code version)
            # Delete it and create a new one
            logger.warning(f"{self.name} model file incompatible (likely from old version): {e}")
            try:
                model_path = self.get_model_path(self.model_path)
                old_model_path = model_path.replace('.keras', '.h5')
                scaler_path = self.get_model_path(self.scaler_path)
                if os.path.exists(model_path):
                    os.remove(model_path)
                    logger.info(f"{self.name} deleted incompatible model file")
                if os.path.exists(old_model_path):
                    os.remove(old_model_path)
                    logger.info(f"{self.name} deleted incompatible legacy .h5 model file")
                if os.path.exists(scaler_path):
                    os.remove(scaler_path)
                    logger.info(f"{self.name} deleted incompatible scaler file")
            except Exception as cleanup_error:
                logger.warning(f"{self.name} error cleaning up old files: {cleanup_error}")
            self._create_model()
            logger.info(f"{self.name} created new model after removing incompatible files")
        except Exception as e:
            logger.error(
                f"{self.name} error loading model",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            logger.warning(f"{self.name} creating new model due to load error")
            self._create_model()
    
    def _create_model(self):
        """Create a new Transformer model"""
        if not TENSORFLOW_AVAILABLE:
            return
        
        embed_dim = 32
        num_heads = 4
        ff_dim = 64
        
        # Updated to handle more features (will be determined dynamically during training)
        # Default to 20 features (OHLCV + 15 key indicators)
        inputs = layers.Input(shape=(self.sequence_length, 20))
        
        # Position encoding
        positions = tf.range(start=0, limit=self.sequence_length, delta=1)
        position_embedding = layers.Embedding(
            input_dim=self.sequence_length, output_dim=embed_dim
        )(positions)
        
        # Project input features
        x = layers.Dense(embed_dim)(inputs)
        x = x + position_embedding
        
        # Transformer blocks
        x = TransformerBlock(embed_dim, num_heads, ff_dim)(x)
        x = TransformerBlock(embed_dim, num_heads, ff_dim)(x)
        
        # Global pooling
        x = layers.GlobalAveragePooling1D()(x)
        
        # Dense layers
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(0.3)(x)
        x = layers.Dense(32, activation="relu")(x)
        x = layers.Dropout(0.2)(x)
        outputs = layers.Dense(1)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0005),
            loss='huber',
            metrics=['mae']
        )
        
        self.model = model
        
        # Initialize scaler
        from sklearn.preprocessing import RobustScaler
        self.scaler = RobustScaler()
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """Generate Transformer-based prediction"""
        
        try:
            if not TENSORFLOW_AVAILABLE or self.model is None:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            if len(candles) < self.sequence_length:
                logger.warning(f"{self.name} needs at least {self.sequence_length} candles")
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Prepare data
            df = pd.DataFrame(candles)
            features = self._prepare_features(df)
            
            if len(features) < self.sequence_length:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Get last sequence
            last_sequence = features[-self.sequence_length:].values
            
            # Normalize
            last_sequence_scaled = last_sequence.copy()
            if hasattr(self.scaler, 'center_'):
                last_sequence_scaled = self.scaler.transform(last_sequence)
            
            # Generate predictions
            predicted_series = []
            current_sequence = last_sequence_scaled.copy()
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            last_close = float(df['close'].iloc[-1])
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            confidence_base = 0.78
            
            for i, ts in enumerate(future_timestamps):
                # Predict next price
                input_seq = current_sequence.reshape(1, self.sequence_length, -1)
                prediction_scaled = self.model.predict(input_seq, verbose=0)[0][0]
                
                # Denormalize
                if hasattr(self.scaler, 'center_'):
                    # Inverse transform for close price (assuming it's the 4th feature)
                    dummy = np.zeros((1, features.shape[1]))
                    dummy[0, 3] = prediction_scaled
                    prediction = self.scaler.inverse_transform(dummy)[0, 3]
                else:
                    prediction = prediction_scaled
                
                # Apply constraints
                max_change = 0.015 * (1 + i / len(future_timestamps))
                change_ratio = (prediction - last_close) / last_close
                change_ratio = np.clip(change_ratio, -max_change, max_change)
                predicted_price = last_close * (1 + change_ratio)
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
                
                # Update sequence
                new_features = np.array([[
                    predicted_price, predicted_price, predicted_price, 
                    predicted_price, 0, 0, 0
                ]])
                if hasattr(self.scaler, 'center_'):
                    new_features = self.scaler.transform(new_features)
                
                current_sequence = np.vstack([current_sequence[1:], new_features[0]])
                last_close = predicted_price
            
            # Calculate confidence
            returns = df['close'].pct_change().dropna()
            volatility = float(returns.std())
            confidence = confidence_base * (1 - min(volatility * 8, 0.3))
            
            # Generate trend metadata
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": confidence,
                "bot_name": self.name,
                "meta": {
                    "model_type": "Transformer",
                    "attention_heads": 4,
                    "sequence_length": self.sequence_length,
                    "volatility": volatility,
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
        """Prepare comprehensive features including technical indicators and volume"""
        from backend.utils.feature_engineering import engineer_comprehensive_features
        
        # Use comprehensive feature engineering
        features_df = engineer_comprehensive_features(
            df,
            include_indicators=True,
            include_volume_features=True,
            include_price_features=True,
            include_returns_features=True
        )
        
        # Select key features for Transformer (attention mechanism benefits from rich features)
        key_features = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi_14', 'macd', 'macd_signal',
            'stoch_rsi_k', 'stoch_rsi_d',
            'bb_position', 'atr_14',
            'volume_ratio_20', 'obv_ratio', 'mfi_14',
            'momentum_10', 'volatility_10', 'returns_5',
            'sma_20', 'ema_21'
        ]
        
        # Only include columns that exist
        available_features = [col for col in key_features if col in features_df.columns]
        
        if len(available_features) < 5:
            # Fallback to basic OHLCV + returns + volatility
            features = pd.DataFrame()
            features['open'] = df['open']
            features['high'] = df['high']
            features['low'] = df['low']
            features['close'] = df['close']
            features['volume'] = df['volume']
            features['returns'] = df['close'].pct_change()
            features['volatility'] = features['returns'].rolling(window=10).std()
            return features.bfill().fillna(0)
        
        return features_df[available_features].bfill().fillna(0)
    
    def _fallback_prediction(self, candles: List[Dict], horizon_minutes: int, timeframe: str) -> Dict:
        """Fallback prediction using momentum analysis"""
        try:
            df = pd.DataFrame(candles)
            last_close = float(df['close'].iloc[-1])
            
            # Calculate momentum
            short_ma = df['close'].tail(10).mean()
            long_ma = df['close'].tail(30).mean()
            momentum = (short_ma - long_ma) / long_ma
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            predicted_series = []
            for i, ts in enumerate(future_timestamps):
                damping = 1.0 - (i / len(future_timestamps)) * 0.6
                predicted_price = last_close * (1 + momentum * damping * 0.4)
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
            
            return {
                "predicted_series": predicted_series,
                "confidence": 0.40,
                "bot_name": self.name,
                "meta": {
                    "model_type": "fallback",
                    "momentum": float(momentum)
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
    
    async def train(self, candles: List[Dict], epochs: int = 30):
        """Train the Transformer model"""
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
            data_hash = hashlib.md5(str(len(candles)).encode()).hexdigest()[:8]
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            model_version = f"v1.0.{timestamp}"
            dataset_version = f"dataset_v1_{data_hash}"
            training_start = candles[0].get("start_ts") if candles else None
            training_end = candles[-1].get("start_ts") if candles else None
            training_window = f"{training_start}_{training_end}"
            
            hyperparams = {
                "epochs": epochs,
                "batch_size": 16,
                "sequence_length": self.sequence_length,
                "learning_rate": 0.0005,
                "loss": "huber",
                "optimizer": "Adam",
                "attention_heads": 4
            }
            
            # Prepare sequences
            X, y = [], []
            for i in range(self.sequence_length, len(features)):
                X.append(features.iloc[i-self.sequence_length:i].values)
                y.append(features['close'].iloc[i])
            
            X = np.array(X)
            y = np.array(y).reshape(-1, 1)

            # Ensure scaler is initialised (legacy models may not have scaler persisted)
            if self.scaler is None:
                from sklearn.preprocessing import RobustScaler
                logger.warning(f"{self.name} scaler missing before training – reinitialising RobustScaler()")
                self.scaler = RobustScaler()
            
            # Normalize
            X_reshaped = X.reshape(-1, X.shape[-1])
            self.scaler.fit(X_reshaped)
            X_scaled = self.scaler.transform(X_reshaped).reshape(X.shape)
            
            # Scale targets
            y_scaled = (y - np.mean(y)) / np.std(y)
            
            # CRITICAL: Recompile model before training to fix optimizer state
            self.model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.0005),
                loss='huber',
                metrics=['mae']
            )
            
            # Ensure arrays are numpy arrays (not TensorFlow tensors)
            X_scaled = np.array(X_scaled)
            y_scaled = np.array(y_scaled)
            
            # Train in thread pool to avoid blocking event loop
            import asyncio
            
            training_start_time = datetime.utcnow()
            
            def _train_model():
                """CPU-bound training function to run in thread pool"""
                return self.model.fit(
                    X_scaled, y_scaled,
                    epochs=epochs,
                    batch_size=16,
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
                        'scaler': self.scaler,
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


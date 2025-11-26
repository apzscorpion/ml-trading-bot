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



if TENSORFLOW_AVAILABLE:
    class TransformerBlock(layers.Layer):
        """
        Transformer Block with Multi-Head Attention and Feed Forward Network
        """
        def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1, **kwargs):
            super(TransformerBlock, self).__init__(**kwargs)
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

        def call(self, inputs, training=False):
            attn_output = self.att(inputs, inputs)
            attn_output = self.dropout1(attn_output, training=training)
            out1 = self.layernorm1(inputs + attn_output)
            
            ffn_output = self.ffn(out1)
            ffn_output = self.dropout2(ffn_output, training=training)
            return self.layernorm2(out1 + ffn_output)
        
        def get_config(self):
            config = super(TransformerBlock, self).get_config()
            config.update({
                "embed_dim": self.embed_dim,
                "num_heads": self.num_heads,
                "ff_dim": self.ff_dim,
                "rate": self.rate,
            })
            return config
else:
    class TransformerBlock:
        pass


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
                custom_objects = {"TransformerBlock": TransformerBlock}
                self.model = keras.models.load_model(model_path, custom_objects=custom_objects)
                
                self.model.compile(
                    optimizer=keras.optimizers.Adam(learning_rate=0.0005),
                    loss='huber',
                    metrics=['mae']
                )
                
                with open(scaler_path, 'rb') as f:
                    scalers = pickle.load(f)
                    self.scaler_X = scalers['scaler_X']
                    self.scaler_y = scalers['scaler_y']
                logger.info(f"{self.name} loaded existing model")
            else:
                self._create_model()
                logger.info(f"{self.name} created new model")
        except Exception as e:
            logger.error(f"{self.name} error loading model: {e}")
            self._create_model()
    
    def _create_model(self, n_features: int = 25):
        """Create a new Deep Transformer model"""
        if not TENSORFLOW_AVAILABLE:
            return
        
        inputs = layers.Input(shape=(self.sequence_length, n_features))
        
        # Embedding projection
        x = layers.Dense(64)(inputs)
        
        # 4 Transformer Blocks (Deeper architecture)
        for _ in range(4):
            x = TransformerBlock(embed_dim=64, num_heads=8, ff_dim=128)(x)
        
        # Global Average Pooling
        x = layers.GlobalAveragePooling1D()(x)
        
        # Regularization and Output
        x = layers.LayerNormalization(epsilon=1e-6)(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(0.2)(x)
        x = layers.Dense(32, activation="relu")(x)
        
        outputs = layers.Dense(1)(x)
        
        model = keras.Model(inputs=inputs, outputs=outputs)
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0005),
            loss='huber',
            metrics=['mae']
        )
        
        self.model = model
        
        # Initialize scalers (RobustScaler is better for outliers)
        from sklearn.preprocessing import RobustScaler
        self.scaler_X = RobustScaler()
        self.scaler_y = RobustScaler()
    
    def _create_model_with_features(self, n_features: int):
        """Create a new model with specified feature count"""
        self._create_model(n_features)
    
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
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            df = pd.DataFrame(candles)
            features = self._prepare_features(df)
            
            if len(features) < self.sequence_length:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            last_sequence = features[-self.sequence_length:].values
            actual_n_features = last_sequence.shape[1]
            
            try:
                model_input_shape = self.model.input_shape
                expected_features = model_input_shape[2] if len(model_input_shape) == 3 else model_input_shape[1]
                
                if expected_features != actual_n_features:
                    logger.warning(f"{self.name} feature mismatch: expected {expected_features}, got {actual_n_features}. Recreating model.")
                    self._create_model_with_features(actual_n_features)
                    return self._fallback_prediction(candles, horizon_minutes, timeframe)
            except Exception:
                pass
            
            # Normalize
            last_sequence_scaled = last_sequence.copy()
            if hasattr(self.scaler_X, 'center_'):
                last_sequence_scaled = self.scaler_X.transform(last_sequence)
            
            # Predict
            last_sequence_scaled = last_sequence_scaled.reshape(1, self.sequence_length, -1)
            
            predicted_series = []
            current_sequence = last_sequence_scaled.copy()
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            last_close = float(df['close'].iloc[-1])
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            confidence_base = 0.80
            
            for i, ts in enumerate(future_timestamps):
                prediction_scaled = self.model.predict(current_sequence, verbose=0)
                
                if hasattr(self.scaler_y, 'center_'):
                    prediction = self.scaler_y.inverse_transform(prediction_scaled)[0][0]
                else:
                    prediction = prediction_scaled[0][0]
                
                # Dynamic constraints
                max_change = 0.025 * (1 + i / len(future_timestamps))
                predicted_price = last_close * (1 + np.clip(prediction / last_close - 1, -max_change, max_change))
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
                
                # Update sequence
                new_features = np.zeros((1, 1, actual_n_features))
                new_features[0, 0, :] = current_sequence[0, -1, :]
                # Update price (approximate)
                # Assuming first 4 are OHLC
                if hasattr(self.scaler_X, 'center_'):
                    # RobustScaler uses center_ and scale_
                    new_features[0, 0, 3] = (predicted_price - self.scaler_X.center_[3]) / self.scaler_X.scale_[3]
                
                current_sequence = np.concatenate([
                    current_sequence[:, 1:, :],
                    new_features
                ], axis=1)
                
                last_close = predicted_price
            
            # Calculate confidence
            returns = df['close'].pct_change().dropna()
            volatility = float(returns.std())
            confidence = confidence_base * (1 - min(volatility * 8, 0.4))
            
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": confidence,
                "bot_name": self.name,
                "meta": {
                    "model_type": "DeepTransformer",
                    "sequence_length": self.sequence_length,
                    "volatility": volatility,
                    **trend_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}", exc_info=True)
            return self._fallback_prediction(candles, horizon_minutes, timeframe)
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare comprehensive features for Transformer model"""
        from backend.utils.feature_engineering import engineer_comprehensive_features
        
        features_df = engineer_comprehensive_features(
            df,
            include_indicators=True,
            include_volume_features=True,
            include_price_features=True,
            include_returns_features=True
        )
        
        # Expanded feature set for Transformer
        # Transformer handles high dimensionality well
        key_features = [
            'open', 'high', 'low', 'close', 'volume',
            'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'stoch_rsi_k', 'stoch_rsi_d',
            'bb_upper', 'bb_lower', 'bb_position', 'bb_squeeze',
            'atr_14', 'adx',
            'ichimoku_conversion_line', 'ichimoku_base_line',
            'ichimoku_leading_span_a', 'ichimoku_leading_span_b',
            'cci', 'williams_r', 'psar',
            'kc_upper', 'kc_lower',
            'volume_ratio_20', 'obv', 'mfi_14',
            'momentum_10', 'volatility_10', 'returns_5',
            'sma_20', 'ema_21'
        ]
        
        available_features = [col for col in key_features if col in features_df.columns]
        
        if len(available_features) < 5:
            return df[['open', 'high', 'low', 'close', 'volume']].dropna()
        
        return features_df[available_features].dropna()
    
    def _fallback_prediction(self, candles: List[Dict], horizon_minutes: int, timeframe: str) -> Dict:
        """Fallback prediction using recent trend analysis"""
        try:
            df = pd.DataFrame(candles)
            last_close = float(df['close'].iloc[-1])
            
            if len(df) < 10:
                trend = 0.0
            else:
                trend = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10]
                trend = np.clip(trend * 0.2, -0.01, 0.01)
            
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            predicted_series = []
            for i, ts in enumerate(future_timestamps):
                predicted_price = last_close * (1 + trend * (i + 1) / len(future_timestamps))
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
            
            return {
                "predicted_series": predicted_series,
                "confidence": 0.30,
                "bot_name": self.name,
                "meta": {"model_type": "fallback", "warning": "Using fallback"}
            }
        except Exception:
            return self._empty_prediction()

    def _empty_prediction(self) -> Dict:
        return {
            "predicted_series": [],
            "confidence": 0.0,
            "bot_name": self.name,
            "meta": {"error": "prediction_failed"}
        }

    async def train(self, candles: List[Dict], epochs: int = 50):
        """Train the Transformer model"""
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return {"error": "TensorFlow not available"}
        
        try:
            df = pd.DataFrame(candles)
            features = self._prepare_features(df)
            
            if len(features) < self.sequence_length + 10:
                return {"error": "Not enough data"}
            
            n_features = features.shape[1]
            
            try:
                model_input_shape = self.model.input_shape
                expected_features = model_input_shape[2] if len(model_input_shape) == 3 else model_input_shape[1]
                if expected_features != n_features:
                    self._create_model_with_features(n_features)
            except Exception:
                self._create_model_with_features(n_features)
            
            X, y = [], []
            for i in range(self.sequence_length, len(features)):
                X.append(features.iloc[i-self.sequence_length:i].values)
                y.append(float(features['close'].iloc[i]))
            
            X = np.array(X, dtype=np.float32)
            y = np.array(y, dtype=np.float32).reshape(-1, 1)
            
            if self.scaler_X is None:
                from sklearn.preprocessing import RobustScaler
                self.scaler_X = RobustScaler()
                self.scaler_y = RobustScaler()
            
            X_reshaped = X.reshape(-1, X.shape[-1])
            self.scaler_X.fit(X_reshaped)
            X_scaled = self.scaler_X.transform(X_reshaped).reshape(X.shape)
            
            self.scaler_y.fit(y)
            y_scaled = self.scaler_y.transform(y)
            
            self.model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.0005),
                loss='huber',
                metrics=['mae']
            )
            
            history = self.model.fit(
                X_scaled, y_scaled,
                epochs=epochs,
                batch_size=32,
                validation_split=0.2,
                verbose=0
            )
            
            model_path = self.get_model_path(self.model_path)
            scaler_path = self.get_model_path(self.scaler_path)
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            if model_path.endswith('.keras'):
                self.model.save(model_path, save_format='keras')
            else:
                self.model.save(model_path)
                
            with open(scaler_path, 'wb') as f:
                pickle.dump({
                    'scaler_X': self.scaler_X,
                    'scaler_y': self.scaler_y,
                    'model_version': 'v2.0-deep-transformer'
                }, f)
            
            return {
                "status": "success",
                "final_loss": float(history.history['loss'][-1]),
                "model_version": "v2.0-deep-transformer"
            }
        except Exception as e:
            logger.error(
                f"{self.name} training error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return {"error": str(e)}


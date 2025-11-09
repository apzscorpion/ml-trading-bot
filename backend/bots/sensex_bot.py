"""
Sensex Index Prediction Bot
Uses LSTM models to predict Sensex index movements.
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from datetime import datetime
import logging
import os
import pickle

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow.python.data.ops.structured_function')
    tf.config.run_functions_eagerly(True)
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logging.warning("TensorFlow not available. Sensex bot will use fallback predictions.")

from backend.bots.base_bot import BaseBot
from backend.utils.data_fetcher import data_fetcher

logger = logging.getLogger(__name__)


class SensexBot(BaseBot):
    """Sensex index prediction bot using LSTM"""
    
    name = "sensex_bot"
    
    def __init__(self):
        super().__init__("sensex_bot")  # Use string literal instead of self.name
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.sequence_length = 60
        self.symbol = "^BSESN"  # Yahoo Finance symbol for Sensex
        self.model_path = "models/sensex_lstm_model.keras"
        self.scaler_path = "models/sensex_lstm_scalers.pkl"
        
        if TENSORFLOW_AVAILABLE:
            self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create a new one"""
        try:
            model_path = self.get_model_path(self.model_path)
            scaler_path = self.get_model_path(self.scaler_path)
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = keras.models.load_model(model_path)
                self.model.compile(
                    optimizer=keras.optimizers.Adam(learning_rate=0.001),
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
    
    def _create_model(self):
        """Create a new LSTM model for index prediction"""
        if not TENSORFLOW_AVAILABLE:
            return
        
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
        
        from sklearn.preprocessing import StandardScaler
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """Generate Sensex prediction"""
        
        try:
            # If candles are empty or not for Sensex, fetch fresh data
            if not candles or len(candles) < self.sequence_length:
                logger.info(f"{self.name} fetching fresh Sensex data")
                candles = await data_fetcher.fetch_candles(
                    symbol=self.symbol,
                    interval=timeframe,
                    period="60d" if timeframe in ["1d", "1wk", "1mo"] else "5d"
                )
            
            if not candles or len(candles) < self.sequence_length:
                logger.warning(f"{self.name} needs at least {self.sequence_length} candles")
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            df = pd.DataFrame(candles)
            features = self._prepare_features(df)
            
            if len(features) < self.sequence_length:
                return self._fallback_prediction(candles, horizon_minutes, timeframe)
            
            # Get last sequence
            last_sequence = features[-self.sequence_length:].values
            
            # Normalize
            last_sequence_scaled = last_sequence.copy()
            if hasattr(self.scaler_X, 'mean_'):
                last_sequence_scaled = self.scaler_X.transform(last_sequence)
            
            last_sequence_scaled = last_sequence_scaled.reshape(1, self.sequence_length, -1)
            
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
            
            confidence_base = 0.73
            
            for i, ts in enumerate(future_timestamps):
                if not TENSORFLOW_AVAILABLE or self.model is None:
                    # Fallback: simple trend continuation
                    predicted_price = last_close * (1 + 0.001 * (i / len(future_timestamps)))
                else:
                    prediction_scaled = self.model.predict(current_sequence, verbose=0)
                    
                    if hasattr(self.scaler_y, 'mean_'):
                        prediction = self.scaler_y.inverse_transform(prediction_scaled)[0][0]
                    else:
                        prediction = prediction_scaled[0][0]
                    
                    max_change = 0.015 * (1 + i / len(future_timestamps))
                    predicted_price = last_close * (1 + np.clip(prediction / last_close - 1, -max_change, max_change))
                    
                    # Update sequence
                    new_features = np.array([[predicted_price, predicted_price, predicted_price, predicted_price, 0]])
                    if hasattr(self.scaler_X, 'mean_'):
                        new_features = self.scaler_X.transform(new_features)
                    
                    current_sequence = np.concatenate([
                        current_sequence[:, 1:, :],
                        new_features.reshape(1, 1, -1)
                    ], axis=1)
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(predicted_price)
                })
                
                last_close = predicted_price
            
            # Calculate confidence
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
                    "index_symbol": self.symbol,
                    "sequence_length": self.sequence_length,
                    "volatility": volatility,
                    "data_points_used": len(df),
                    **trend_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}", exc_info=True)
            return self._fallback_prediction(candles if candles else [], horizon_minutes, timeframe)
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for LSTM model"""
        features = pd.DataFrame()
        features['open'] = df['open']
        features['high'] = df['high']
        features['low'] = df['low']
        features['close'] = df['close']
        features['volume'] = df['volume']
        return features.dropna()
    
    async def _fallback_prediction(self, candles: List[Dict], horizon_minutes: int, timeframe: str) -> Dict:
        """Fallback prediction using simple trend"""
        try:
            if not candles:
                candles = await data_fetcher.fetch_candles(
                    symbol=self.symbol,
                    interval=timeframe,
                    period="5d"
                )
            
            if not candles:
                return self._empty_prediction()
            
            df = pd.DataFrame(candles)
            last_close = float(df['close'].iloc[-1])
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            # Simple trend continuation
            recent_change = (df['close'].iloc[-1] - df['close'].iloc[-10]) / df['close'].iloc[-10] if len(df) >= 10 else 0
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            predicted_series = []
            current_price = last_close
            
            for i, ts in enumerate(future_timestamps):
                # Dampening trend over time
                dampen = 1.0 - (i / len(future_timestamps)) * 0.5
                price_change_pct = recent_change * dampen * 0.3
                current_price = current_price * (1 + price_change_pct)
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(current_price)
                })
            
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": 0.5,
                "bot_name": self.name,
                "meta": {
                    "model_type": "fallback",
                    "index_symbol": self.symbol,
                    **trend_metadata
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
            "meta": {"error": "prediction_failed", "index_symbol": self.symbol}
        }


"""
RSI (Relative Strength Index) Momentum Bot.
Predicts price movements based on RSI overbought/oversold conditions.
"""
from typing import Dict, List
import numpy as np
from datetime import datetime
from .base_bot import BaseBot
from backend.utils.indicators import calculate_rsi
import logging

logger = logging.getLogger(__name__)


class RSIBot(BaseBot):
    """RSI-based prediction bot"""
    
    def __init__(self):
        super().__init__("rsi_bot")
        self.period = 14
        self.oversold_threshold = 30
        self.overbought_threshold = 70
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        timeframe_map = {
            "1m": 1, "5m": 5, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "1d": 1440, "1wk": 10080, "1mo": 43200
        }
        return timeframe_map.get(timeframe, 5)
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """
        Predict future prices based on RSI momentum.
        
        Strategy:
        - RSI < 30 (oversold): Expect upward reversal
        - RSI > 70 (overbought): Expect downward reversal
        - RSI 30-70: Trend continuation with dampening
        """
        try:
            if len(candles) < self.period + 5:
                logger.warning(f"{self.name}: Not enough candles for prediction")
                return self._empty_prediction()
            
            df = self._candles_to_dataframe(candles)
            
            # Calculate RSI
            df['rsi'] = calculate_rsi(df, period=self.period)
            
            # Get latest values
            latest_close = float(df['close'].iloc[-1])
            latest_rsi = float(df['rsi'].iloc[-1])
            
            if np.isnan(latest_rsi):
                logger.warning(f"{self.name}: RSI calculation failed")
                return self._empty_prediction()
            
            # Generate future timestamps
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            # Calculate prediction direction and magnitude
            if latest_rsi < self.oversold_threshold:
                # Oversold - expect upward movement
                direction = 1
                strength = (self.oversold_threshold - latest_rsi) / self.oversold_threshold
                confidence = 0.6 + (strength * 0.3)  # 0.6 to 0.9
            elif latest_rsi > self.overbought_threshold:
                # Overbought - expect downward movement
                direction = -1
                strength = (latest_rsi - self.overbought_threshold) / (100 - self.overbought_threshold)
                confidence = 0.6 + (strength * 0.3)  # 0.6 to 0.9
            else:
                # Neutral - weak trend continuation
                direction = 1 if latest_rsi > 50 else -1
                strength = abs(latest_rsi - 50) / 50
                confidence = 0.3 + (strength * 0.2)  # 0.3 to 0.5
            
            # Calculate recent volatility for price movement magnitude
            returns = df['close'].pct_change().dropna()
            volatility = float(returns.std())
            
            # Ensure minimum volatility to prevent flat predictions
            timeframe_minutes = self._timeframe_to_minutes(timeframe)
            min_volatility = 0.005 * np.sqrt(timeframe_minutes / (24 * 60))
            volatility = max(volatility, min_volatility)
            
            # Generate predictions
            predicted_series = []
            current_price = latest_close
            
            for i, ts in enumerate(future_timestamps):
                # Dampening factor - predictions become less certain over time
                dampen = 1.0 - (i / len(future_timestamps)) * 0.5
                
                # Price change based on RSI signal, volatility, and time decay
                # Increase multiplier for more visible predictions
                price_change_pct = direction * strength * volatility * dampen * 1.0
                current_price = current_price * (1 + price_change_pct)
                
                predicted_series.append({
                    "ts": ts.isoformat(),
                    "price": float(current_price)
                })
            
            # Generate trend metadata
            trend_metadata = self._generate_trend_metadata(predicted_series, timeframe)
            
            return {
                "predicted_series": predicted_series,
                "confidence": float(confidence),
                "bot_name": self.name,
                "meta": {
                    "rsi": float(latest_rsi),
                    "direction": "bullish" if direction > 0 else "bearish",
                    "signal_strength": float(strength),
                    **trend_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return self._empty_prediction()
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction on error"""
        return {
            "predicted_series": [],
            "confidence": 0.0,
            "bot_name": self.name,
            "meta": {"error": "prediction_failed"}
        }


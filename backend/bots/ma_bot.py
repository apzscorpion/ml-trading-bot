"""
Moving Average Crossover Bot.
Predicts price movements based on MA crossovers and trend direction.
"""
from typing import Dict, List
import numpy as np
from datetime import datetime
from .base_bot import BaseBot
from backend.utils.indicators import calculate_moving_averages
import logging

logger = logging.getLogger(__name__)


class MABot(BaseBot):
    """Moving Average crossover prediction bot"""
    
    def __init__(self):
        super().__init__("ma_bot")
    
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
        Predict future prices based on Moving Average crossovers.
        
        Strategy:
        - Golden Cross (SMA20 > SMA50): Strong bullish
        - Death Cross (SMA20 < SMA50): Strong bearish
        - EMA trends for short-term momentum
        """
        try:
            if len(candles) < 55:  # Need at least 50 + buffer for MA calculations
                logger.warning(f"{self.name}: Not enough candles for prediction")
                return self._empty_prediction()
            
            df = self._candles_to_dataframe(candles)
            
            # Calculate moving averages
            mas = calculate_moving_averages(df)
            df['sma_20'] = mas['sma_20']
            df['sma_50'] = mas['sma_50']
            df['ema_21'] = mas['ema_21']
            df['ema_9'] = mas['ema_9']
            
            # Get latest values
            latest_close = float(df['close'].iloc[-1])
            latest_sma_20 = float(df['sma_20'].iloc[-1])
            latest_sma_50 = float(df['sma_50'].iloc[-1])
            latest_ema_21 = float(df['ema_21'].iloc[-1])
            latest_ema_9 = float(df['ema_9'].iloc[-1])
            
            if np.isnan(latest_sma_20) or np.isnan(latest_sma_50):
                logger.warning(f"{self.name}: MA calculation failed")
                return self._empty_prediction()
            
            # Detect crossovers
            prev_sma_20 = float(df['sma_20'].iloc[-2])
            prev_sma_50 = float(df['sma_50'].iloc[-2])
            
            golden_cross = (prev_sma_20 <= prev_sma_50) and (latest_sma_20 > latest_sma_50)
            death_cross = (prev_sma_20 >= prev_sma_50) and (latest_sma_20 < latest_sma_50)
            
            # Calculate MA separation (trend strength)
            ma_separation = abs(latest_sma_20 - latest_sma_50) / latest_sma_50
            ma_separation_normalized = min(ma_separation * 100, 1.0)
            
            # Price position relative to MAs
            price_above_sma20 = latest_close > latest_sma_20
            price_above_ema21 = latest_close > latest_ema_21
            ema_bullish = latest_ema_9 > latest_ema_21
            
            # Determine direction and confidence
            if golden_cross:
                direction = 1
                confidence = 0.85
                signal_type = "golden_cross"
            elif death_cross:
                direction = -1
                confidence = 0.85
                signal_type = "death_cross"
            elif latest_sma_20 > latest_sma_50:
                # Bullish trend
                direction = 1
                confidence = 0.5 + (ma_separation_normalized * 0.3)
                signal_type = "bullish_trend"
            else:
                # Bearish trend
                direction = -1
                confidence = 0.5 + (ma_separation_normalized * 0.3)
                signal_type = "bearish_trend"
            
            # Adjust confidence based on price position and EMA
            if direction > 0 and price_above_sma20 and price_above_ema21 and ema_bullish:
                confidence = min(confidence * 1.2, 0.95)
            elif direction < 0 and not price_above_sma20 and not price_above_ema21 and not ema_bullish:
                confidence = min(confidence * 1.2, 0.95)
            else:
                confidence = confidence * 0.9
            
            # Generate future timestamps
            last_ts = df['start_ts'].iloc[-1]
            if isinstance(last_ts, str):
                last_ts = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            
            future_timestamps = self._generate_future_timestamps(
                last_ts, timeframe, horizon_minutes
            )
            
            # Calculate recent volatility
            returns = df['close'].pct_change().dropna()
            volatility = float(returns.std())
            
            # Ensure minimum volatility to prevent flat predictions
            # Use a floor of 0.5% daily volatility (scaled to timeframe)
            timeframe_minutes = self._timeframe_to_minutes(timeframe)
            min_volatility = 0.005 * np.sqrt(timeframe_minutes / (24 * 60))  # Scale to timeframe
            volatility = max(volatility, min_volatility)
            
            # Generate predictions
            predicted_series = []
            current_price = latest_close
            
            for i, ts in enumerate(future_timestamps):
                # Dampening factor
                dampen = 1.0 - (i / len(future_timestamps)) * 0.35
                
                # Price change based on MA trend
                trend_strength = ma_separation_normalized
                # Increase multiplier for more visible predictions
                price_change_pct = direction * trend_strength * volatility * dampen * 1.2
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
                    "sma_20": float(latest_sma_20),
                    "sma_50": float(latest_sma_50),
                    "ema_21": float(latest_ema_21),
                    "signal_type": signal_type,
                    "trend_strength": float(ma_separation_normalized),
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


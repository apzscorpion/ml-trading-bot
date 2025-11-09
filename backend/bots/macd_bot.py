"""
MACD (Moving Average Convergence Divergence) Trend Bot.
Predicts price movements based on MACD crossovers and histogram.
"""
from typing import Dict, List
import numpy as np
from datetime import datetime
from .base_bot import BaseBot
from backend.utils.indicators import calculate_macd
import logging

logger = logging.getLogger(__name__)


class MACDBot(BaseBot):
    """MACD-based prediction bot"""
    
    def __init__(self):
        super().__init__("macd_bot")
    
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
        Predict future prices based on MACD signals.
        
        Strategy:
        - MACD crosses above signal: Bullish
        - MACD crosses below signal: Bearish
        - Histogram magnitude indicates strength
        """
        try:
            if len(candles) < 50:  # Need enough data for MACD
                logger.warning(f"{self.name}: Not enough candles for prediction")
                return self._empty_prediction()
            
            df = self._candles_to_dataframe(candles)
            
            # Calculate MACD
            macd_data = calculate_macd(df)
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']
            
            # Get latest values
            latest_close = float(df['close'].iloc[-1])
            latest_macd = float(df['macd'].iloc[-1])
            latest_signal = float(df['macd_signal'].iloc[-1])
            latest_histogram = float(df['macd_histogram'].iloc[-1])
            
            if np.isnan(latest_macd) or np.isnan(latest_signal):
                logger.warning(f"{self.name}: MACD calculation failed")
                return self._empty_prediction()
            
            # Detect crossover
            prev_macd = float(df['macd'].iloc[-2])
            prev_signal = float(df['macd_signal'].iloc[-2])
            
            bullish_crossover = (prev_macd <= prev_signal) and (latest_macd > latest_signal)
            bearish_crossover = (prev_macd >= prev_signal) and (latest_macd < latest_signal)
            
            # Determine direction and confidence
            if bullish_crossover:
                direction = 1
                confidence = 0.75
                signal_type = "bullish_crossover"
            elif bearish_crossover:
                direction = -1
                confidence = 0.75
                signal_type = "bearish_crossover"
            elif latest_macd > latest_signal:
                direction = 1
                confidence = 0.5 + min(abs(latest_histogram) * 0.1, 0.3)
                signal_type = "bullish_trend"
            else:
                direction = -1
                confidence = 0.5 + min(abs(latest_histogram) * 0.1, 0.3)
                signal_type = "bearish_trend"
            
            # Histogram strength
            histogram_strength = min(abs(latest_histogram) / (abs(latest_macd) + 0.001), 1.0)
            
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
            timeframe_minutes = self._timeframe_to_minutes(timeframe)
            min_volatility = 0.005 * np.sqrt(timeframe_minutes / (24 * 60))
            volatility = max(volatility, min_volatility)
            
            # Generate predictions
            predicted_series = []
            current_price = latest_close
            
            for i, ts in enumerate(future_timestamps):
                # Dampening factor
                dampen = 1.0 - (i / len(future_timestamps)) * 0.4
                
                # Price change based on MACD signal
                # Increase multiplier for more visible predictions
                price_change_pct = direction * histogram_strength * volatility * dampen * 1.1
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
                    "macd": float(latest_macd),
                    "signal": float(latest_signal),
                    "histogram": float(latest_histogram),
                    "signal_type": signal_type,
                    "histogram_strength": float(histogram_strength),
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


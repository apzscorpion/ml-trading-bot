"""
Base class for all prediction bots.
"""
from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import os


class BaseBot(ABC):
    """Abstract base class for prediction bots"""
    
    def __init__(self, name: str):
        self.name = name
        self._current_symbol = None
        self._current_timeframe = None
    
    def set_model_context(self, symbol: str, timeframe: str):
        """
        Set the current symbol and timeframe context for model loading/saving.
        This allows models to be stored per symbol/timeframe combination.
        
        Args:
            symbol: Stock symbol (e.g., 'TCS.NS')
            timeframe: Timeframe (e.g., '5m', '1h')
        """
        self._current_symbol = symbol
        self._current_timeframe = timeframe
    
    def get_model_path(self, base_path: str) -> str:
        """
        Generate model path with symbol and timeframe suffix.
        
        Args:
            base_path: Base model path (e.g., 'models/lstm_model.keras')
        
        Returns:
            Path with symbol and timeframe (e.g., 'models/lstm_model_TCS_NS_5m.keras')
        """
        if self._current_symbol and self._current_timeframe:
            # Sanitize symbol for filename (replace . with _)
            safe_symbol = self._current_symbol.replace('.', '_')
            # Get directory and filename
            directory = os.path.dirname(base_path)
            filename = os.path.basename(base_path)
            # Split filename and extension
            name, ext = os.path.splitext(filename)
            # Create new path
            new_filename = f"{name}_{safe_symbol}_{self._current_timeframe}{ext}"
            return os.path.join(directory, new_filename) if directory else new_filename
        return base_path
    
    @abstractmethod
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """
        Generate predictions based on candle data.
        
        Args:
            candles: List of candle dictionaries with OHLCV data
            horizon_minutes: How far ahead to predict (in minutes)
            timeframe: Candle timeframe (e.g., '5m', '15m')
        
        Returns:
            Dictionary with:
            - predicted_series: List of {ts, price} predictions
            - confidence: Confidence score (0-1)
            - bot_name: Name of the bot
            - meta: Additional metadata
        """
        pass
    
    def _is_trading_hour(self, ts: datetime) -> bool:
        """
        Check if timestamp is within Indian stock market trading hours.
        
        Args:
            ts: Timestamp to check
        
        Returns:
            True if timestamp is within trading hours (9:00 AM - 3:30 PM IST, Mon-Fri)
        """
        # Ensure timestamp is in IST timezone
        if ts.tzinfo is None:
            ist = pytz.timezone('Asia/Kolkata')
            ts = ist.localize(ts)
        else:
            ts = ts.astimezone(pytz.timezone('Asia/Kolkata'))
        
        # Check if weekday (Monday=0, Sunday=6)
        weekday = ts.weekday()
        if weekday >= 5:  # Saturday=5, Sunday=6
            return False
        
        # Check if within trading hours (9:00 AM - 3:30 PM IST)
        hour = ts.hour
        minute = ts.minute
        
        # Before 9:00 AM
        if hour < 9:
            return False
        
        # At or after 3:30 PM (market closes at 3:30 PM, so 3:30 PM is included as last trading minute)
        if hour > 15 or (hour == 15 and minute >= 30):
            return False
        
        return True
    
    def _get_next_trading_day(self, ts: datetime) -> datetime:
        """
        Get the next trading day at 9:00 AM IST.
        
        Args:
            ts: Current timestamp
        
        Returns:
            Next trading day at 9:00 AM IST (skips weekends)
        """
        # Ensure timestamp is in IST timezone
        if ts.tzinfo is None:
            ist = pytz.timezone('Asia/Kolkata')
            ts = ist.localize(ts)
        else:
            ts = ts.astimezone(pytz.timezone('Asia/Kolkata'))
        
        # Move to next day at 9:00 AM
        next_day = ts.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # Skip weekends
        weekday = next_day.weekday()
        while weekday >= 5:  # Saturday=5, Sunday=6
            next_day = next_day + timedelta(days=1)
            weekday = next_day.weekday()
        
        return next_day
    
    def _generate_future_timestamps(
        self, 
        last_candle_ts: datetime,
        timeframe: str,
        horizon_minutes: int
    ) -> List[datetime]:
        """
        Generate future timestamps for predictions within Indian stock market trading hours.
        
        Args:
            last_candle_ts: Timestamp of the last candle
            timeframe: Candle timeframe (e.g., '5m')
            horizon_minutes: Prediction horizon (in trading minutes)
        
        Returns:
            List of future timestamps within trading hours only
        """
        # Ensure timestamp is in IST timezone
        if last_candle_ts.tzinfo is None:
            ist = pytz.timezone('Asia/Kolkata')
            current_ts = ist.localize(last_candle_ts)
        else:
            current_ts = last_candle_ts.astimezone(pytz.timezone('Asia/Kolkata'))
        
        # Parse timeframe to get interval in minutes
        interval_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '5d': 1440,     # Daily candles
            '1wk': 10080,   # 7 days
            '1mo': 43200,   # ~30 days
            '3mo': 129600   # ~90 days
        }
        
        interval_minutes = interval_map.get(timeframe, 5)
        
        # Calculate how many trading minutes we need to cover
        # Each trading day has 6.5 hours = 390 minutes of trading (9:00 AM - 3:30 PM)
        trading_minutes_per_day = 390
        num_trading_days_needed = (horizon_minutes // trading_minutes_per_day) + 1
        max_iterations = num_trading_days_needed * trading_minutes_per_day // interval_minutes + 100  # Safety buffer
        
        timestamps = []
        iterations = 0
        
        # Check if we're at or after market close (3:30 PM) - if so, start from next trading day
        hour = current_ts.hour
        minute = current_ts.minute
        weekday = current_ts.weekday()
        
        # If it's a weekday and we're at or after 3:30 PM, start from next trading day
        if weekday < 5 and (hour > 15 or (hour == 15 and minute >= 30)):
            # Market has closed, start predictions from next trading day
            current_ts = self._get_next_trading_day(current_ts)
        else:
            # Start from the next interval after last candle
            current_ts = current_ts + timedelta(minutes=interval_minutes)
            
            # If current timestamp is outside trading hours, move to next trading time
            if not self._is_trading_hour(current_ts):
                hour = current_ts.hour
                minute = current_ts.minute
                weekday = current_ts.weekday()
                
                if weekday >= 5:  # Weekend
                    current_ts = self._get_next_trading_day(current_ts)
                elif hour < 9:
                    # Before 9:00 AM, move to 9:00 AM same day
                    current_ts = current_ts.replace(hour=9, minute=0, second=0, microsecond=0)
                else:
                    # After 3:30 PM, move to next trading day
                    current_ts = self._get_next_trading_day(current_ts)
        
        # Generate timestamps until we have enough trading minutes
        trading_minutes_covered = 0
        
        while trading_minutes_covered < horizon_minutes and iterations < max_iterations:
            iterations += 1
            
            # Check if current timestamp is within trading hours
            if self._is_trading_hour(current_ts):
                timestamps.append(current_ts)
                trading_minutes_covered += interval_minutes
            
            # Move to next interval
            current_ts = current_ts + timedelta(minutes=interval_minutes)
            
            # If we've moved past trading hours, skip to next trading day
            if not self._is_trading_hour(current_ts):
                # Check if we're past market close on a weekday
                weekday = current_ts.weekday()
                hour = current_ts.hour
                minute = current_ts.minute
                
                if weekday >= 5:  # Weekend
                    current_ts = self._get_next_trading_day(current_ts)
                elif hour > 15 or (hour == 15 and minute >= 30):
                    # At or after 3:30 PM, move to next trading day
                    current_ts = self._get_next_trading_day(current_ts)
                elif hour < 9:
                    # Before 9:00 AM, move to 9:00 AM same day
                    current_ts = current_ts.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return timestamps
    
    def _candles_to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """Convert candle list to pandas DataFrame"""
        df = pd.DataFrame(candles)
        if not df.empty and 'start_ts' in df.columns:
            if isinstance(df['start_ts'].iloc[0], str):
                df['start_ts'] = pd.to_datetime(df['start_ts'])
        return df
    
    def _calculate_trend_direction(self, predicted_series: List[Dict]) -> int:
        """
        Calculate trend direction from predicted series.
        
        Args:
            predicted_series: List of {ts, price} predictions
        
        Returns:
            -1 for downtrend, 0 for neutral, 1 for uptrend
        """
        if len(predicted_series) < 2:
            return 0
        
        prices = [p.get("price", 0) for p in predicted_series]
        if len(prices) < 2:
            return 0
        
        start_price = prices[0]
        end_price = prices[-1]
        price_change = (end_price - start_price) / start_price if start_price > 0 else 0
        
        # Threshold: 0.5% change to consider it a trend
        if price_change > 0.005:
            return 1  # Uptrend
        elif price_change < -0.005:
            return -1  # Downtrend
        else:
            return 0  # Neutral
    
    def _calculate_trend_strength(self, predicted_series: List[Dict]) -> float:
        """
        Calculate trend strength from predicted series.
        
        Args:
            predicted_series: List of {ts, price} predictions
        
        Returns:
            Trend strength (0-1): 0 = weak, 0.5 = moderate, 1.0 = strong
        """
        if len(predicted_series) < 3:
            return 0.0
        
        prices = [p.get("price", 0) for p in predicted_series]
        if len(prices) < 3:
            return 0.0
        
        # Calculate linear regression slope
        x = np.arange(len(prices))
        y = np.array(prices)
        
        # Handle invalid prices
        if np.any(y <= 0) or np.isnan(y).any():
            return 0.0
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalize slope relative to price level
        avg_price = np.mean(y)
        normalized_slope = abs(slope / avg_price) if avg_price > 0 else 0
        
        # Convert to 0-1 scale (strong trend if >2% change per unit)
        strength = min(normalized_slope * 50, 1.0)
        
        return float(strength)
    
    def _calculate_trend_duration(self, predicted_series: List[Dict], timeframe: str) -> int:
        """
        Estimate trend duration in minutes based on prediction stability.
        
        Args:
            predicted_series: List of {ts, price} predictions
            timeframe: Candle timeframe
        
        Returns:
            Estimated trend duration in minutes
        """
        if len(predicted_series) < 2:
            return 0
        
        prices = [p.get("price", 0) for p in predicted_series]
        if len(prices) < 2:
            return 0
        
        # Parse timeframe to get interval in minutes
        interval_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440,
            '5d': 1440, '1wk': 10080, '1mo': 43200, '3mo': 129600
        }
        interval_minutes = interval_map.get(timeframe, 5)
        
        # Calculate price changes
        price_changes = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                change = (prices[i] - prices[i-1]) / prices[i-1]
                price_changes.append(change)
        
        if not price_changes:
            return 0
        
        # Find where trend changes direction
        direction = 1 if price_changes[0] > 0 else (-1 if price_changes[0] < 0 else 0)
        trend_duration_points = 1
        
        for change in price_changes[1:]:
            if direction == 0:
                direction = 1 if change > 0 else (-1 if change < 0 else 0)
                trend_duration_points = 1
            elif (direction > 0 and change < 0) or (direction < 0 and change > 0):
                # Trend reversal detected
                break
            else:
                trend_duration_points += 1
        
        # Convert to minutes
        duration_minutes = trend_duration_points * interval_minutes
        
        return duration_minutes
    
    def _generate_trend_metadata(
        self, 
        predicted_series: List[Dict], 
        timeframe: str
    ) -> Dict:
        """
        Generate comprehensive trend metadata from predictions.
        
        Args:
            predicted_series: List of {ts, price} predictions
            timeframe: Candle timeframe
        
        Returns:
            Dictionary with trend_direction, trend_strength, trend_duration_minutes
        """
        direction = self._calculate_trend_direction(predicted_series)
        strength = self._calculate_trend_strength(predicted_series)
        duration = self._calculate_trend_duration(predicted_series, timeframe)
        
        # Map direction to string
        direction_str = "up" if direction > 0 else ("down" if direction < 0 else "neutral")
        
        # Map strength to category
        if strength < 0.3:
            strength_category = "weak"
        elif strength < 0.6:
            strength_category = "moderate"
        else:
            strength_category = "strong"
        
        return {
            "trend_direction": direction,
            "trend_direction_str": direction_str,
            "trend_strength": strength,
            "trend_strength_category": strength_category,
            "trend_duration_minutes": duration
        }


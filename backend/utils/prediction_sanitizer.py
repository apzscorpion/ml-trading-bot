"""
Prediction Sanitizer - Prevents unrealistic predictions from reaching production

This module provides sanity checks and clipping for model predictions to prevent
absurd outputs like "200% gain in 2 hours".
"""

from typing import List, Dict, Optional
import numpy as np
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PredictionSanitizer:
    """Sanitize and validate model predictions"""
    
    def __init__(self):
        # Maximum allowed price moves per timeframe (as percentage)
        self.max_moves = {
            '1m': 0.5,    # 0.5% per minute is already extreme
            '5m': 1.0,    # 1% per 5 minutes
            '15m': 2.0,   # 2% per 15 minutes
            '1h': 5.0,    # 5% per hour
            '4h': 10.0,   # 10% per 4 hours
            '1d': 20.0,   # 20% per day (very extreme)
        }
        
        # Maximum total move for any horizon
        self.max_total_move = 30.0  # 30% total move is extreme
    
    def sanitize_prediction(
        self,
        predicted_series: List[Dict],
        reference_price: float,
        timeframe: str,
        horizon_minutes: int
    ) -> tuple[List[Dict], List[str]]:
        """
        Sanitize prediction series to prevent unrealistic values.
        
        Args:
            predicted_series: List of predicted candles
            reference_price: Current/reference price
            timeframe: Candle timeframe
            horizon_minutes: Prediction horizon in minutes
        
        Returns:
            (sanitized_series, list_of_warnings)
        """
        if not predicted_series:
            return predicted_series, []
        
        warnings = []
        sanitized = []
        
        # Get max allowed move per step
        max_step_pct = self.max_moves.get(timeframe, 5.0)
        
        # Track cumulative move
        prev_price = reference_price
        
        for i, candle in enumerate(predicted_series):
            sanitized_candle = candle.copy()
            
            # Check each price field
            for price_field in ['open', 'high', 'low', 'close']:
                if price_field not in candle:
                    continue
                
                predicted_price = candle[price_field]
                
                # Calculate move from previous
                move_pct = abs((predicted_price / prev_price - 1) * 100)
                
                # Check if move is too large
                if move_pct > max_step_pct:
                    # Clip to max allowed
                    direction = 1 if predicted_price > prev_price else -1
                    clipped_price = prev_price * (1 + direction * max_step_pct / 100)
                    
                    warnings.append(
                        f"Step {i} {price_field}: Clipped {move_pct:.2f}% move to {max_step_pct}% "
                        f"({predicted_price:.2f} -> {clipped_price:.2f})"
                    )
                    
                    sanitized_candle[price_field] = clipped_price
            
            # Update prev_price for next iteration
            prev_price = sanitized_candle.get('close', prev_price)
            sanitized.append(sanitized_candle)
        
        # Check total move
        if sanitized:
            final_price = sanitized[-1].get('close', reference_price)
            total_move_pct = abs((final_price / reference_price - 1) * 100)
            
            if total_move_pct > self.max_total_move:
                warnings.append(
                    f"Total move {total_move_pct:.2f}% exceeds maximum {self.max_total_move}% "
                    f"- prediction may be unrealistic"
                )
                
                # Scale down entire series
                scale_factor = self.max_total_move / total_move_pct
                for candle in sanitized:
                    for price_field in ['open', 'high', 'low', 'close']:
                        if price_field in candle:
                            # Scale relative to reference
                            rel_move = (candle[price_field] / reference_price - 1)
                            candle[price_field] = reference_price * (1 + rel_move * scale_factor)
        
        if warnings:
            logger.warning(
                f"Sanitized prediction for {timeframe}/{horizon_minutes}min: {len(warnings)} adjustments made"
            )
        
        return sanitized, warnings
    
    def validate_prediction(
        self,
        predicted_series: List[Dict],
        reference_price: float,
        timeframe: str,
        horizon_minutes: int
    ) -> tuple[bool, List[str]]:
        """
        Validate prediction without modifying it.
        
        Returns:
            (is_valid, list_of_issues)
        """
        if not predicted_series:
            return False, ["Empty prediction series"]
        
        issues = []
        
        # Check series length matches horizon
        timeframe_mins = self._timeframe_to_minutes(timeframe)
        expected_length = horizon_minutes / timeframe_mins
        
        if abs(len(predicted_series) - expected_length) > 2:
            issues.append(
                f"Series length {len(predicted_series)} doesn't match horizon "
                f"({horizon_minutes}min / {timeframe_mins}min = {expected_length:.1f} expected)"
            )
        
        # Check for NaN or invalid values
        for i, candle in enumerate(predicted_series):
            for field in ['open', 'high', 'low', 'close']:
                if field in candle:
                    value = candle[field]
                    if not isinstance(value, (int, float)) or np.isnan(value) or value <= 0:
                        issues.append(f"Invalid {field} at step {i}: {value}")
        
        # Check for extreme moves
        max_step_pct = self.max_moves.get(timeframe, 5.0)
        prev_price = reference_price
        
        for i, candle in enumerate(predicted_series):
            close_price = candle.get('close', prev_price)
            move_pct = abs((close_price / prev_price - 1) * 100)
            
            if move_pct > max_step_pct * 2:  # 2x threshold for validation
                issues.append(
                    f"Extreme move at step {i}: {move_pct:.2f}% "
                    f"(max expected: {max_step_pct}%)"
                )
            
            prev_price = close_price
        
        # Check total move
        if predicted_series:
            final_price = predicted_series[-1].get('close', reference_price)
            total_move_pct = abs((final_price / reference_price - 1) * 100)
            
            if total_move_pct > self.max_total_move:
                issues.append(
                    f"Total move {total_move_pct:.2f}% exceeds maximum {self.max_total_move}%"
                )
        
        return len(issues) == 0, issues
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        mapping = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        return mapping.get(timeframe, 5)


# Global instance
prediction_sanitizer = PredictionSanitizer()


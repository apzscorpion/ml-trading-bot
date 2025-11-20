"""
ML Prediction Validators - Sanity checks to reject extreme/invalid predictions.
Enhanced with volatility-aware validation and directional consistency checks.
"""
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PredictionValidator:
    """Validates ML predictions before they reach the ensemble or frontend"""
    
    def __init__(self):
        # Validation thresholds
        self.max_total_drift_pct = 10.0  # Max ±10% total change over horizon
        self.max_step_change_pct = 3.0   # Max 3% change per step
        self.max_price_multiplier = 1.15  # Max 15% above reference price
        self.min_price_multiplier = 0.85  # Max 15% below reference price
        
        # Volatility validation thresholds
        self.volatility_tolerance_factor = 2.0  # Predicted volatility can be up to 2x actual
        self.min_volatility_factor = 0.2  # Predicted volatility should be at least 20% of actual
        self.smoothness_threshold = 0.001  # Max allowed smoothness (std of price changes)
        
        # Directional consistency
        self.directional_consistency_threshold = 0.6  # 60% of steps should follow trend
    
    def validate_prediction(
        self,
        predicted_series: List[Dict],
        latest_close: float,
        bot_name: str,
        recent_candles: Optional[List[Dict]] = None
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        Validate a prediction series with volatility-aware and directional checks.
        
        Args:
            predicted_series: List of {ts, price} points
            latest_close: Latest actual close price (reference)
            bot_name: Name of bot for logging
            recent_candles: Recent candles for volatility comparison (optional)
        
        Returns:
            (is_valid, rejection_reason, validation_stats)
        """
        if not predicted_series:
            return False, "empty_series", {"error": "No predictions"}
        
        if latest_close <= 0:
            return False, "invalid_reference_price", {"latest_close": latest_close}
        
        stats = {
            "bot_name": bot_name,
            "num_points": len(predicted_series),
            "reference_price": latest_close
        }
        
        # Extract prices
        try:
            prices = [point["price"] for point in predicted_series]
        except (KeyError, TypeError) as e:
            return False, f"invalid_format: {e}", stats
        
        # Check for NaN or Inf
        if not all(np.isfinite(prices)):
            nan_count = sum(1 for p in prices if not np.isfinite(p))
            stats["nan_or_inf_count"] = nan_count
            return False, f"nan_or_inf_values: {nan_count} invalid", stats
        
        # Check for negative prices
        if any(p < 0 for p in prices):
            negative_count = sum(1 for p in prices if p < 0)
            stats["negative_count"] = negative_count
            return False, f"negative_prices: {negative_count} found", stats
        
        # Check total drift from reference
        max_price = max(prices)
        min_price = min(prices)
        
        max_drift_up_pct = ((max_price - latest_close) / latest_close) * 100
        max_drift_down_pct = ((latest_close - min_price) / latest_close) * 100
        
        stats["max_drift_up_pct"] = float(max_drift_up_pct)
        stats["max_drift_down_pct"] = float(max_drift_down_pct)
        
        if max_drift_up_pct > self.max_total_drift_pct:
            return False, f"excessive_upward_drift: {max_drift_up_pct:.1f}%", stats
        
        if max_drift_down_pct > self.max_total_drift_pct:
            return False, f"excessive_downward_drift: {max_drift_down_pct:.1f}%", stats
        
        # Check step-wise changes
        max_step_change = 0.0
        step_changes = []
        for i in range(1, len(prices)):
            step_change_pct = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
            step_changes.append(step_change_pct)
            max_step_change = max(max_step_change, step_change_pct)
        
        stats["max_step_change_pct"] = float(max_step_change)
        
        if max_step_change > self.max_step_change_pct:
            return False, f"excessive_step_change: {max_step_change:.1f}%", stats
        
        # Check absolute bounds
        upper_bound = latest_close * self.max_price_multiplier
        lower_bound = latest_close * self.min_price_multiplier
        
        if max_price > upper_bound:
            return False, f"exceeds_upper_bound: {max_price:.2f} > {upper_bound:.2f}", stats
        
        if min_price < lower_bound:
            return False, f"below_lower_bound: {min_price:.2f} < {lower_bound:.2f}", stats
        
        # Volatility-aware validation
        if recent_candles and len(recent_candles) >= 10:
            volatility_check = self._validate_volatility_alignment(
                prices, recent_candles, latest_close
            )
            if not volatility_check[0]:
                stats.update(volatility_check[2])
                return False, f"volatility_mismatch: {volatility_check[1]}", stats
            stats.update(volatility_check[2])
        
        # Check for smoothness (straight lines)
        smoothness_check = self._validate_smoothness(prices)
        if not smoothness_check[0]:
            stats.update(smoothness_check[2])
            return False, f"too_smooth: {smoothness_check[1]}", stats
        stats.update(smoothness_check[2])
        
        # Directional consistency check (if recent candles available)
        if recent_candles and len(recent_candles) >= 5:
            directional_check = self._validate_directional_consistency(
                prices, recent_candles, latest_close
            )
            if not directional_check[0]:
                stats.update(directional_check[2])
                # Warning but not rejection - allow if confidence is high
                logger.warning(
                    f"Bot {bot_name} prediction has directional inconsistency: {directional_check[1]}",
                    extra=directional_check[2]
                )
            stats.update(directional_check[2])
        
        # All checks passed
        stats["validation_passed"] = True
        return True, None, stats
    
    def _validate_volatility_alignment(
        self,
        predicted_prices: List[float],
        recent_candles: List[Dict],
        reference_price: float
    ) -> Tuple[bool, Optional[str], Dict]:
        """Check if predicted volatility aligns with actual market volatility"""
        try:
            # Calculate actual volatility from recent candles
            df_actual = pd.DataFrame(recent_candles)
            if 'close' not in df_actual.columns:
                return True, None, {}  # Skip if no close column
            
            actual_returns = df_actual['close'].pct_change().dropna()
            actual_volatility = float(actual_returns.std())
            
            # Calculate predicted volatility
            predicted_returns = np.diff(predicted_prices) / np.array(predicted_prices[:-1])
            predicted_volatility = float(np.std(predicted_returns))
            
            # Compare volatilities
            if actual_volatility == 0:
                actual_volatility = 0.001  # Avoid division by zero
            
            volatility_ratio = predicted_volatility / actual_volatility
            
            stats = {
                "actual_volatility": actual_volatility,
                "predicted_volatility": predicted_volatility,
                "volatility_ratio": volatility_ratio
            }
            
            # Check if predicted volatility is within acceptable range
            if volatility_ratio > self.volatility_tolerance_factor:
                return False, f"predicted_volatility_too_high: {volatility_ratio:.2f}x", stats
            
            if volatility_ratio < self.min_volatility_factor:
                return False, f"predicted_volatility_too_low: {volatility_ratio:.2f}x", stats
            
            return True, None, stats
            
        except Exception as e:
            logger.warning(f"Error in volatility validation: {e}")
            return True, None, {}  # Don't reject on validation error
    
    def _validate_smoothness(
        self,
        predicted_prices: List[float]
    ) -> Tuple[bool, Optional[str], Dict]:
        """Check if prediction is too smooth (straight line)"""
        try:
            if len(predicted_prices) < 2:
                return True, None, {}
            
            # Calculate standard deviation of price changes
            price_changes = np.diff(predicted_prices)
            price_changes_std = float(np.std(price_changes))
            
            # Normalize by average price
            avg_price = np.mean(predicted_prices)
            normalized_smoothness = price_changes_std / avg_price if avg_price > 0 else 0
            
            stats = {
                "smoothness_std": price_changes_std,
                "normalized_smoothness": normalized_smoothness
            }
            
            # Check if too smooth (straight line)
            if normalized_smoothness < self.smoothness_threshold:
                return False, f"prediction_too_smooth: {normalized_smoothness:.6f}", stats
            
            return True, None, stats
            
        except Exception as e:
            logger.warning(f"Error in smoothness validation: {e}")
            return True, None, {}
    
    def _validate_directional_consistency(
        self,
        predicted_prices: List[float],
        recent_candles: List[Dict],
        reference_price: float
    ) -> Tuple[bool, Optional[str], Dict]:
        """Check if prediction direction is consistent with recent trend"""
        try:
            if len(predicted_prices) < 2 or len(recent_candles) < 5:
                return True, None, {}
            
            # Determine recent trend direction
            df_recent = pd.DataFrame(recent_candles)
            if 'close' not in df_recent.columns:
                return True, None, {}
            
            recent_closes = df_recent['close'].values
            recent_trend = 1 if recent_closes[-1] > recent_closes[0] else -1
            
            # Determine predicted trend direction
            predicted_trend = 1 if predicted_prices[-1] > predicted_prices[0] else -1
            
            # Check step-by-step consistency
            consistent_steps = 0
            total_steps = len(predicted_prices) - 1
            
            for i in range(1, len(predicted_prices)):
                pred_step_direction = 1 if predicted_prices[i] > predicted_prices[i-1] else -1
                # Compare with recent trend (allow some flexibility)
                if pred_step_direction == recent_trend:
                    consistent_steps += 1
            
            consistency_ratio = consistent_steps / total_steps if total_steps > 0 else 0
            
            stats = {
                "recent_trend": recent_trend,
                "predicted_trend": predicted_trend,
                "consistency_ratio": consistency_ratio,
                "consistent_steps": consistent_steps,
                "total_steps": total_steps
            }
            
            # Check if direction is consistent enough
            if consistency_ratio < self.directional_consistency_threshold:
                return False, f"low_directional_consistency: {consistency_ratio:.2f}", stats
            
            return True, None, stats
            
        except Exception as e:
            logger.warning(f"Error in directional validation: {e}")
            return True, None, {}
    
    def sanitize_prediction(
        self,
        predicted_series: List[Dict],
        latest_close: float,
        bot_name: str
    ) -> Tuple[List[Dict], Dict]:
        """
        Attempt to sanitize/clamp prediction to make it valid.
        
        Returns:
            (sanitized_series, sanitization_stats)
        """
        if not predicted_series or latest_close <= 0:
            return predicted_series, {"error": "cannot_sanitize"}
        
        sanitized = []
        clipped_count = 0
        upper_bound = latest_close * self.max_price_multiplier
        lower_bound = latest_close * self.min_price_multiplier
        
        last_valid_price = latest_close
        
        for point in predicted_series:
            price = point.get("price")
            
            # Replace NaN/Inf
            if not np.isfinite(price):
                price = last_valid_price
                clipped_count += 1
            
            # Clamp to bounds
            if price > upper_bound:
                price = upper_bound
                clipped_count += 1
            elif price < lower_bound:
                price = lower_bound
                clipped_count += 1
            
            # Step-wise clamp
            max_step = last_valid_price * (self.max_step_change_pct / 100)
            if abs(price - last_valid_price) > max_step:
                if price > last_valid_price:
                    price = last_valid_price + max_step
                else:
                    price = last_valid_price - max_step
                clipped_count += 1
            
            sanitized.append({
                "ts": point["ts"],
                "price": float(price)
            })
            
            last_valid_price = price
        
        stats = {
            "bot_name": bot_name,
            "original_points": len(predicted_series),
            "sanitized_points": len(sanitized),
            "clipped_count": clipped_count,
            "clipped_pct": (clipped_count / len(predicted_series)) * 100 if predicted_series else 0
        }
        
        return sanitized, stats


# Global instance
prediction_validator = PredictionValidator()


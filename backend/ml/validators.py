"""
ML Prediction Validators - Sanity checks to reject extreme/invalid predictions.
"""
from typing import Dict, List, Tuple, Optional
import numpy as np
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
    
    def validate_prediction(
        self,
        predicted_series: List[Dict],
        latest_close: float,
        bot_name: str
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        Validate a prediction series.
        
        Args:
            predicted_series: List of {ts, price} points
            latest_close: Latest actual close price (reference)
            bot_name: Name of bot for logging
        
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
        for i in range(1, len(prices)):
            step_change_pct = abs((prices[i] - prices[i-1]) / prices[i-1]) * 100
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
        
        # All checks passed
        stats["validation_passed"] = True
        return True, None, stats
    
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


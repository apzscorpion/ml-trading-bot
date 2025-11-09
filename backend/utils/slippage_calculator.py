"""
Slippage calculator for realistic order execution.
Simulates price difference between expected and actual fill prices.
"""
from typing import Dict, Optional
import math


class SlippageCalculator:
    """
    Calculate realistic slippage based on:
    - Order size vs. daily volume (market impact)
    - Volatility (wider spreads in volatile markets)
    - Order type (market vs. limit)
    - Time of day (pre-market, opening, closing)
    """
    
    def __init__(
        self,
        base_slippage_bps: float = 5.0,  # 5 basis points (0.05%) base slippage
        impact_factor: float = 0.5,  # Market impact multiplier
        volatility_factor: float = 1.0,  # Volatility multiplier
    ):
        self.base_slippage_bps = base_slippage_bps
        self.impact_factor = impact_factor
        self.volatility_factor = volatility_factor
    
    def calculate_volatility(
        self,
        prices: list[float],
        period: int = 20
    ) -> float:
        """
        Calculate price volatility (standard deviation of returns).
        
        Args:
            prices: List of prices
            period: Period for volatility calculation
        
        Returns:
            Volatility as percentage
        """
        if len(prices) < 2:
            return 0.0
        
        # Use last N prices
        recent_prices = prices[-period:] if len(prices) > period else prices
        
        # Calculate returns
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] > 0:
                ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # Convert to percentage
        return std_dev * 100
    
    def calculate_market_impact(
        self,
        order_size: int,
        daily_volume: float,
        price: float
    ) -> float:
        """
        Calculate market impact based on order size relative to liquidity.
        
        Args:
            order_size: Number of shares in order
            daily_volume: Average daily volume
            price: Current price
        
        Returns:
            Market impact in basis points
        """
        if daily_volume <= 0:
            return 50.0  # High impact if no volume data
        
        # Percentage of daily volume
        volume_percentage = (order_size / daily_volume) * 100
        
        # Market impact increases exponentially with order size
        # Small orders (< 1% of volume): minimal impact
        # Large orders (> 10% of volume): significant impact
        if volume_percentage < 0.1:
            impact = 0.0
        elif volume_percentage < 1.0:
            impact = volume_percentage * 2  # 0-2 bps
        elif volume_percentage < 5.0:
            impact = 2 + (volume_percentage - 1) * 5  # 2-22 bps
        elif volume_percentage < 10.0:
            impact = 22 + (volume_percentage - 5) * 10  # 22-72 bps
        else:
            impact = 72 + (volume_percentage - 10) * 20  # 72+ bps
        
        return min(impact, 200.0)  # Cap at 200 bps (2%)
    
    def calculate_slippage(
        self,
        order_type: str,  # "market" or "limit"
        order_size: int,
        price: float,
        daily_volume: float = None,
        prices: list[float] = None,
        is_sell: bool = False,
        limit_price: float = None
    ) -> Dict[str, float]:
        """
        Calculate realistic slippage for an order.
        
        Args:
            order_type: "market" or "limit"
            order_size: Number of shares
            price: Expected/current price
            daily_volume: Daily trading volume (for market impact)
            prices: Historical prices (for volatility calculation)
            is_sell: True if sell order
            limit_price: Limit price if limit order
        
        Returns:
            Dictionary with slippage details
        """
        # Base slippage
        slippage_bps = self.base_slippage_bps
        
        # Market impact
        if daily_volume:
            market_impact = self.calculate_market_impact(order_size, daily_volume, price)
            slippage_bps += market_impact * self.impact_factor
        
        # Volatility impact
        if prices:
            volatility = self.calculate_volatility(prices)
            volatility_impact = volatility * 0.5  # Scale volatility impact
            slippage_bps += volatility_impact
        
        # Order type adjustment
        if order_type == "limit":
            # Limit orders have less slippage but may not fill
            slippage_bps *= 0.3  # 30% of market order slippage
            
            # Check if limit price is favorable
            if limit_price:
                if is_sell and limit_price > price:
                    # Limit sell above market = may not fill
                    slippage_bps *= 0.5
                elif not is_sell and limit_price < price:
                    # Limit buy below market = may not fill
                    slippage_bps *= 0.5
        elif order_type == "market":
            # Market orders have full slippage
            pass
        
        # Direction adjustment (sells often have slightly more slippage)
        if is_sell:
            slippage_bps *= 1.1
        
        # Convert basis points to percentage
        slippage_pct = slippage_bps / 100.0
        
        # Calculate actual fill price
        if is_sell:
            # Sell: price goes down (less favorable)
            fill_price = price * (1 - slippage_pct)
        else:
            # Buy: price goes up (less favorable)
            fill_price = price * (1 + slippage_pct)
        
        return {
            "slippage_bps": round(slippage_bps, 2),
            "slippage_pct": round(slippage_pct, 4),
            "expected_price": round(price, 2),
            "fill_price": round(fill_price, 2),
            "price_difference": round(abs(fill_price - price), 2),
            "order_type": order_type,
            "is_sell": is_sell,
            "order_size": order_size
        }


# Singleton instance
slippage_calculator = SlippageCalculator()


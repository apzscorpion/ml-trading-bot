"""
Order simulator for realistic trade execution.
Simulates market and limit orders with slippage and fill probability.
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from backend.utils.slippage_calculator import slippage_calculator
from backend.utils.cost_calculator import cost_calculator
import random


class OrderSimulator:
    """
    Simulates order execution with realistic market conditions.
    """
    
    def __init__(self):
        self.pending_orders: List[Dict] = []
    
    def simulate_market_order(
        self,
        symbol: str,
        quantity: int,
        price: float,
        is_sell: bool,
        daily_volume: float = None,
        prices: List[float] = None,
        timestamp: datetime = None
    ) -> Dict:
        """
        Simulate a market order execution.
        Market orders execute immediately at current price + slippage.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            price: Expected price
            is_sell: True if sell order
            daily_volume: Daily trading volume
            prices: Historical prices for volatility
            timestamp: Order timestamp
        
        Returns:
            Order execution result
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Calculate slippage
        slippage_result = slippage_calculator.calculate_slippage(
            order_type="market",
            order_size=quantity,
            price=price,
            daily_volume=daily_volume,
            prices=prices,
            is_sell=is_sell
        )
        
        fill_price = slippage_result["fill_price"]
        trade_value = fill_price * quantity
        
        # Calculate transaction costs
        costs = cost_calculator.calculate_total_cost(
            trade_value=trade_value,
            is_sell=is_sell,
            quantity=quantity
        )
        
        return {
            "order_id": f"MO_{timestamp.timestamp()}",
            "order_type": "market",
            "symbol": symbol,
            "quantity": quantity,
            "side": "sell" if is_sell else "buy",
            "expected_price": price,
            "fill_price": fill_price,
            "slippage": slippage_result,
            "trade_value": trade_value,
            "costs": costs,
            "net_value": trade_value - costs["total_cost"] if is_sell else trade_value + costs["total_cost"],
            "timestamp": timestamp.isoformat(),
            "status": "filled",
            "fill_time": timestamp.isoformat()
        }
    
    def simulate_limit_order(
        self,
        symbol: str,
        quantity: int,
        limit_price: float,
        current_price: float,
        is_sell: bool,
        daily_volume: float = None,
        prices: List[float] = None,
        timestamp: datetime = None,
        expiry_minutes: int = 60
    ) -> Dict:
        """
        Simulate a limit order execution.
        Limit orders only fill if price moves favorably.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares
            limit_price: Limit price
            current_price: Current market price
            is_sell: True if sell order
            daily_volume: Daily trading volume
            prices: Historical prices for volatility
            timestamp: Order timestamp
            expiry_minutes: Order expiry in minutes
        
        Returns:
            Order execution result (may be partially filled or unfilled)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        order_id = f"LO_{timestamp.timestamp()}"
        
        # Check if limit order can fill immediately
        can_fill = False
        if is_sell:
            # Sell limit: fills if limit_price <= current_price
            can_fill = limit_price <= current_price
        else:
            # Buy limit: fills if limit_price >= current_price
            can_fill = limit_price >= current_price
        
        if can_fill:
            # Immediate fill
            fill_price = limit_price
            
            # Still apply some slippage (though less than market order)
            slippage_result = slippage_calculator.calculate_slippage(
                order_type="limit",
                order_size=quantity,
                price=fill_price,
                daily_volume=daily_volume,
                prices=prices,
                is_sell=is_sell,
                limit_price=limit_price
            )
            
            # Actual fill may be slightly worse than limit
            fill_price = slippage_result["fill_price"]
            
            trade_value = fill_price * quantity
            costs = cost_calculator.calculate_total_cost(
                trade_value=trade_value,
                is_sell=is_sell,
                quantity=quantity
            )
            
            return {
                "order_id": order_id,
                "order_type": "limit",
                "symbol": symbol,
                "quantity": quantity,
                "side": "sell" if is_sell else "buy",
                "limit_price": limit_price,
                "current_price": current_price,
                "fill_price": fill_price,
                "slippage": slippage_result,
                "trade_value": trade_value,
                "costs": costs,
                "net_value": trade_value - costs["total_cost"] if is_sell else trade_value + costs["total_cost"],
                "timestamp": timestamp.isoformat(),
                "status": "filled",
                "fill_time": timestamp.isoformat(),
                "fill_quantity": quantity
            }
        else:
            # Order cannot fill immediately
            # In real backtesting, we'd check if price reaches limit_price later
            # For now, mark as pending/unfilled
            
            return {
                "order_id": order_id,
                "order_type": "limit",
                "symbol": symbol,
                "quantity": quantity,
                "side": "sell" if is_sell else "buy",
                "limit_price": limit_price,
                "current_price": current_price,
                "timestamp": timestamp.isoformat(),
                "status": "pending",
                "expiry_time": (timestamp + timedelta(minutes=expiry_minutes)).isoformat(),
                "fill_quantity": 0,
                "fill_price": None
            }
    
    def check_limit_order_fill(
        self,
        order: Dict,
        current_price: float,
        timestamp: datetime = None
    ) -> Optional[Dict]:
        """
        Check if a pending limit order can now be filled.
        
        Args:
            order: Pending order dictionary
            current_price: Current market price
            timestamp: Current timestamp
        
        Returns:
            Filled order result or None if still pending
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Check expiry
        if "expiry_time" in order:
            expiry = datetime.fromisoformat(order["expiry_time"])
            if timestamp > expiry:
                return {
                    **order,
                    "status": "expired",
                    "fill_time": timestamp.isoformat()
                }
        
        is_sell = order["side"] == "sell"
        limit_price = order["limit_price"]
        
        # Check if price reached limit
        can_fill = False
        if is_sell:
            can_fill = current_price >= limit_price  # Sell: price went up
        else:
            can_fill = current_price <= limit_price  # Buy: price went down
        
        if can_fill:
            # Fill the order
            fill_price = limit_price
            
            slippage_result = slippage_calculator.calculate_slippage(
                order_type="limit",
                order_size=order["quantity"],
                price=fill_price,
                is_sell=is_sell,
                limit_price=limit_price
            )
            
            fill_price = slippage_result["fill_price"]
            trade_value = fill_price * order["quantity"]
            
            costs = cost_calculator.calculate_total_cost(
                trade_value=trade_value,
                is_sell=is_sell,
                quantity=order["quantity"]
            )
            
            return {
                **order,
                "status": "filled",
                "fill_price": fill_price,
                "fill_time": timestamp.isoformat(),
                "fill_quantity": order["quantity"],
                "slippage": slippage_result,
                "trade_value": trade_value,
                "costs": costs,
                "net_value": trade_value - costs["total_cost"] if is_sell else trade_value + costs["total_cost"]
            }
        
        return None


# Singleton instance
order_simulator = OrderSimulator()


"""
Transaction cost calculator for Indian stock market.
Handles brokerage, STT, GST, exchange charges, and other fees.
"""
from typing import Dict
from decimal import Decimal, ROUND_HALF_UP


class TransactionCostCalculator:
    """
    Calculate transaction costs for Indian equity trading.
    
    Typical costs in India (2024):
    - Brokerage: 0.03% of trade value or ₹20 minimum
    - STT (Securities Transaction Tax): 0.0125% on sell orders
    - GST: 18% on brokerage
    - Exchange charges: ~₹0.0003% per trade
    - SEBI charges: ₹10 per crore
    - Stamp duty: State-specific (typically ₹0.003%)
    """
    
    def __init__(
        self,
        brokerage_rate: float = 0.0003,  # 0.03%
        min_brokerage: float = 20.0,  # ₹20 minimum
        stt_rate: float = 0.000125,  # 0.0125% on sell
        gst_rate: float = 0.18,  # 18% on brokerage
        exchange_rate: float = 0.000003,  # 0.0003%
        sebi_rate: float = 0.000001,  # ₹10 per crore = 0.0001%
        stamp_duty_rate: float = 0.00003,  # 0.003% (varies by state)
    ):
        self.brokerage_rate = brokerage_rate
        self.min_brokerage = min_brokerage
        self.stt_rate = stt_rate
        self.gst_rate = gst_rate
        self.exchange_rate = exchange_rate
        self.sebi_rate = sebi_rate
        self.stamp_duty_rate = stamp_duty_rate
    
    def calculate_brokerage(self, trade_value: float) -> float:
        """
        Calculate brokerage charges.
        
        Args:
            trade_value: Total value of trade (price * quantity)
        
        Returns:
            Brokerage amount
        """
        brokerage = trade_value * self.brokerage_rate
        return max(brokerage, self.min_brokerage)
    
    def calculate_stt(self, trade_value: float, is_sell: bool) -> float:
        """
        Calculate Securities Transaction Tax (STT).
        Only applicable on sell orders.
        
        Args:
            trade_value: Total value of trade
            is_sell: True if sell order
        
        Returns:
            STT amount
        """
        if not is_sell:
            return 0.0
        return trade_value * self.stt_rate
    
    def calculate_gst(self, brokerage: float) -> float:
        """
        Calculate GST on brokerage.
        
        Args:
            brokerage: Brokerage amount
        
        Returns:
            GST amount
        """
        return brokerage * self.gst_rate
    
    def calculate_exchange_charges(self, trade_value: float) -> float:
        """
        Calculate exchange charges.
        
        Args:
            trade_value: Total value of trade
        
        Returns:
            Exchange charges
        """
        return trade_value * self.exchange_rate
    
    def calculate_sebi_charges(self, trade_value: float) -> float:
        """
        Calculate SEBI charges.
        
        Args:
            trade_value: Total value of trade
        
        Returns:
            SEBI charges
        """
        return trade_value * self.sebi_rate
    
    def calculate_stamp_duty(self, trade_value: float, is_sell: bool) -> float:
        """
        Calculate stamp duty (typically on buy orders).
        
        Args:
            trade_value: Total value of trade
            is_sell: True if sell order
        
        Returns:
            Stamp duty amount
        """
        if is_sell:
            return 0.0
        return trade_value * self.stamp_duty_rate
    
    def calculate_total_cost(
        self,
        trade_value: float,
        is_sell: bool,
        quantity: int = None
    ) -> Dict[str, float]:
        """
        Calculate total transaction cost for a trade.
        
        Args:
            trade_value: Total value of trade (price * quantity)
            is_sell: True if sell order, False if buy order
            quantity: Number of shares (optional, for detailed breakdown)
        
        Returns:
            Dictionary with cost breakdown
        """
        brokerage = self.calculate_brokerage(trade_value)
        stt = self.calculate_stt(trade_value, is_sell)
        gst = self.calculate_gst(brokerage)
        exchange_charges = self.calculate_exchange_charges(trade_value)
        sebi_charges = self.calculate_sebi_charges(trade_value)
        stamp_duty = self.calculate_stamp_duty(trade_value, is_sell)
        
        total_cost = brokerage + stt + gst + exchange_charges + sebi_charges + stamp_duty
        
        return {
            "brokerage": round(brokerage, 2),
            "stt": round(stt, 2),
            "gst": round(gst, 2),
            "exchange_charges": round(exchange_charges, 2),
            "sebi_charges": round(sebi_charges, 2),
            "stamp_duty": round(stamp_duty, 2),
            "total_cost": round(total_cost, 2),
            "trade_value": round(trade_value, 2),
            "is_sell": is_sell,
            "cost_percentage": round((total_cost / trade_value) * 100, 4) if trade_value > 0 else 0.0
        }
    
    def calculate_round_trip_cost(self, buy_value: float, sell_value: float) -> Dict[str, float]:
        """
        Calculate total cost for a round-trip trade (buy + sell).
        
        Args:
            buy_value: Value of buy order
            sell_value: Value of sell order
        
        Returns:
            Dictionary with total round-trip costs
        """
        buy_costs = self.calculate_total_cost(buy_value, is_sell=False)
        sell_costs = self.calculate_total_cost(sell_value, is_sell=True)
        
        total_round_trip_cost = buy_costs["total_cost"] + sell_costs["total_cost"]
        
        return {
            "buy_costs": buy_costs,
            "sell_costs": sell_costs,
            "total_round_trip_cost": round(total_round_trip_cost, 2),
            "net_trade_value": round(sell_value - buy_value, 2),
            "net_profit_after_costs": round(sell_value - buy_value - total_round_trip_cost, 2),
            "cost_percentage": round((total_round_trip_cost / buy_value) * 100, 4) if buy_value > 0 else 0.0
        }


# Singleton instance with default Indian market rates
cost_calculator = TransactionCostCalculator()


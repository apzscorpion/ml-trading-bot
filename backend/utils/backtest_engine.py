"""
Backtesting engine for realistic strategy evaluation.
Simulates trading strategies using historical data with realistic execution.
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import logging
from backend.utils.order_simulator import order_simulator
from backend.utils.position_manager import PositionManager
from backend.utils.performance_metrics import PerformanceMetrics
from backend.utils.cost_calculator import cost_calculator
from backend.utils.exchange_calendar import exchange_calendar
from backend.utils.signal_strategies import generate_signal_from_indicators, MultiIndicatorStrategy, SignalStrategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Main backtesting engine that simulates trading strategies.
    """
    
    def __init__(self):
        self.position_manager = PositionManager()
        self.equity_curve: List[float] = []
        self.returns: List[float] = []
        self.trades: List[Dict] = []
    
    def run_backtest(
        self,
        symbol: str,
        candles: List[Dict],
        initial_capital: float,
        strategy: Optional[SignalStrategy] = None,  # SignalStrategy instance or None for default
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        order_type: str = "market",  # "market" or "limit"
        position_size_pct: float = 0.1,  # 10% of capital per trade
        max_positions: int = 1,  # Maximum concurrent positions
        stop_loss_pct: float = 0.0,  # 0 = no stop loss
        take_profit_pct: float = 0.0,  # 0 = no take profit
    ) -> Dict:
        """
        Run a backtest on historical data.
        
        Args:
            symbol: Stock symbol
            candles: Historical candle data
            initial_capital: Starting capital
            strategy: Function that takes (candle, index, predictions) and returns signal dict
            start_date: Start date for backtest
            end_date: End date for backtest
            order_type: "market" or "limit"
            position_size_pct: Percentage of capital to use per trade
            max_positions: Maximum concurrent positions
            stop_loss_pct: Stop loss percentage (0 = disabled)
            take_profit_pct: Take profit percentage (0 = disabled)
        
        Returns:
            Backtest results dictionary
        """
        if not candles:
            raise ValueError("No candles provided for backtest")
        
        # Initialize position manager
        self.position_manager.initialize(initial_capital)
        self.equity_curve = [initial_capital]
        self.returns = []
        self.trades = []
        
        # Filter candles by date range
        if start_date or end_date:
            filtered_candles = []
            for candle in candles:
                candle_time = self._parse_candle_time(candle["start_ts"])
                if start_date and candle_time < start_date:
                    continue
                if end_date and candle_time > end_date:
                    continue
                filtered_candles.append(candle)
            candles = filtered_candles
        
        if not candles:
            raise ValueError("No candles in date range")
        
        # Use default strategy if none provided
        if strategy is None:
            strategy = MultiIndicatorStrategy()
        
        # Simulate trading day by day
        for i, candle in enumerate(candles):
            candle_time = self._parse_candle_time(candle["start_ts"])
            current_price = candle["close"]
            
            # Check if market is open
            if not exchange_calendar.is_market_open(candle_time):
                continue
            
            # Get current prices for all positions
            current_prices = {symbol: current_price}
            
            # Check stop loss / take profit for open positions
            position = self.position_manager.get_position(symbol)
            if position:
                # Check stop loss
                if stop_loss_pct > 0:
                    stop_loss_price = position.entry_price * (1 - stop_loss_pct)
                    if current_price <= stop_loss_price:
                        # Trigger stop loss
                        self._close_position(
                            symbol=symbol,
                            exit_price=stop_loss_price,
                            exit_time=candle_time,
                            candle=candle,
                            reason="stop_loss"
                        )
                        continue
                
                # Check take profit
                if take_profit_pct > 0:
                    take_profit_price = position.entry_price * (1 + take_profit_pct)
                    if current_price >= take_profit_price:
                        # Trigger take profit
                        self._close_position(
                            symbol=symbol,
                            exit_price=take_profit_price,
                            exit_time=candle_time,
                            candle=candle,
                            reason="take_profit"
                        )
                        continue
            
            # Generate trading signal from indicators
            signal = generate_signal_from_indicators(
                candle=candle,
                candles=candles[:i+1],  # Use all candles up to current
                strategy=strategy,
                index=i
            )
            
            if not signal:
                continue
            
            signal_type = signal.get("action")  # "buy", "sell", or None
            
            if signal_type == "buy":
                # Check if we can open new position
                if len(self.position_manager.positions) >= max_positions:
                    continue
                
                if self.position_manager.get_position(symbol):
                    continue  # Already have position
                
                # Calculate position size
                portfolio_value = self.position_manager.get_portfolio_value(current_prices)
                position_value = portfolio_value * position_size_pct
                quantity = int(position_value / current_price)
                
                if quantity <= 0:
                    continue
                
                # Execute buy order
                order_result = order_simulator.simulate_market_order(
                    symbol=symbol,
                    quantity=quantity,
                    price=current_price,
                    is_sell=False,
                    daily_volume=candle.get("volume", 0),
                    prices=[c["close"] for c in candles[max(0, i-20):i+1]],
                    timestamp=candle_time
                )
                
                # Open position
                try:
                    position = self.position_manager.open_position(
                        symbol=symbol,
                        quantity=quantity,
                        entry_price=order_result["fill_price"],
                        entry_time=candle_time,
                        entry_costs=order_result["costs"]["total_cost"]
                    )
                    
                    self.trades.append({
                        "type": "entry",
                        "symbol": symbol,
                        "time": candle_time.isoformat(),
                        "price": order_result["fill_price"],
                        "quantity": quantity,
                        "value": order_result["trade_value"],
                        "costs": order_result["costs"]["total_cost"],
                        "signal": signal
                    })
                except ValueError as e:
                    logger.warning(f"Insufficient capital for trade: {e}")
                    continue
            
            elif signal_type == "sell":
                # Close existing position
                if self.position_manager.get_position(symbol):
                    self._close_position(
                        symbol=symbol,
                        exit_price=current_price,
                        exit_time=candle_time,
                        candle=candle,
                        reason="signal"
                    )
            
            # Update equity curve
            portfolio_value = self.position_manager.get_portfolio_value(current_prices)
            self.equity_curve.append(portfolio_value)
            
            # Calculate daily return
            if len(self.equity_curve) > 1:
                daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
                self.returns.append(daily_return)
        
        # Calculate final metrics
        final_value = self.equity_curve[-1] if self.equity_curve else initial_capital
        start_time = self._parse_candle_time(candles[0]["start_ts"])
        end_time = self._parse_candle_time(candles[-1]["start_ts"])
        days = (end_time - start_time).days
        
        metrics = PerformanceMetrics.calculate_metrics(
            returns=self.returns,
            equity_curve=self.equity_curve,
            initial_capital=initial_capital,
            final_value=final_value,
            days=days
        )
        
        stats = self.position_manager.get_statistics()
        pnl = self.position_manager.get_total_pnl({symbol: candles[-1]["close"]})
        
        return {
            "symbol": symbol,
            "start_date": start_time.isoformat(),
            "end_date": end_time.isoformat(),
            "initial_capital": initial_capital,
            "final_value": final_value,
            "metrics": metrics,
            "statistics": stats,
            "pnl": pnl,
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "returns": self.returns,
            "total_trades": len(self.trades),
            "closed_positions": [p.to_dict() for p in self.position_manager.closed_positions],
            "open_positions": [p.to_dict() for p in self.position_manager.positions]
        }
    
    def _close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time: datetime,
        candle: Dict,
        reason: str = "signal"
    ):
        """Helper to close a position"""
        position = self.position_manager.get_position(symbol)
        if not position:
            return
        
        # Get daily volume for slippage calculation
        daily_volume = candle.get("volume", 0)
        
        # Execute sell order
        order_result = order_simulator.simulate_market_order(
            symbol=symbol,
            quantity=position.quantity,
            price=exit_price,
            is_sell=True,
            daily_volume=daily_volume,
            prices=[candle["close"]],  # Simplified
            timestamp=exit_time
        )
        
        # Close position
        closed_position = self.position_manager.close_position(
            symbol=symbol,
            exit_price=order_result["fill_price"],
            exit_time=exit_time,
            exit_costs=order_result["costs"]["total_cost"]
        )
        
        if closed_position:
            self.trades.append({
                "type": "exit",
                "symbol": symbol,
                "time": exit_time.isoformat(),
                "price": order_result["fill_price"],
                "quantity": position.quantity,
                "value": order_result["trade_value"],
                "costs": order_result["costs"]["total_cost"],
                "pnl": closed_position.get_realized_pnl(),
                "reason": reason
            })
    
    def _parse_candle_time(self, timestamp) -> datetime:
        """Parse candle timestamp"""
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, datetime):
            return timestamp
        else:
            raise ValueError(f"Invalid timestamp type: {type(timestamp)}")
    


# Singleton instance
backtest_engine = BacktestEngine()


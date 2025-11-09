"""
Position manager for tracking open positions and trades.
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class Position:
    """Represents a single position (long or short)"""
    
    def __init__(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        entry_time: datetime,
        entry_costs: float = 0.0
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.entry_costs = entry_costs
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.exit_costs: float = 0.0
        self.is_closed = False
    
    def close(
        self,
        exit_price: float,
        exit_time: datetime,
        exit_costs: float = 0.0
    ):
        """Close the position"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_costs = exit_costs
        self.is_closed = True
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.is_closed:
            return 0.0
        return (current_price - self.entry_price) * self.quantity
    
    def get_realized_pnl(self) -> Optional[float]:
        """Calculate realized P&L"""
        if not self.is_closed:
            return None
        gross_pnl = (self.exit_price - self.entry_price) * self.quantity
        net_pnl = gross_pnl - self.entry_costs - self.exit_costs
        return net_pnl
    
    def get_holding_period(self) -> Optional[float]:
        """Get holding period in days"""
        if not self.is_closed:
            return None
        delta = self.exit_time - self.entry_time
        return delta.total_seconds() / 86400  # Convert to days
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat(),
            "entry_costs": self.entry_costs,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_costs": self.exit_costs,
            "is_closed": self.is_closed,
            "realized_pnl": self.get_realized_pnl(),
            "holding_period_days": self.get_holding_period()
        }


class PositionManager:
    """Manages positions and trades"""
    
    def __init__(self):
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []
        self.cash: float = 0.0
        self.initial_capital: float = 0.0
    
    def initialize(self, initial_capital: float):
        """Initialize with starting capital"""
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = []
        self.closed_positions = []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get open position for a symbol"""
        for pos in self.positions:
            if pos.symbol == symbol and not pos.is_closed:
                return pos
        return None
    
    def open_position(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        entry_time: datetime,
        entry_costs: float = 0.0
    ) -> Position:
        """Open a new position"""
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=entry_time,
            entry_costs=entry_costs
        )
        
        # Deduct cash (buy)
        total_cost = (entry_price * quantity) + entry_costs
        if total_cost > self.cash:
            raise ValueError(f"Insufficient cash. Need {total_cost}, have {self.cash}")
        
        self.cash -= total_cost
        self.positions.append(position)
        
        return position
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_time: datetime,
        exit_costs: float = 0.0,
        quantity: Optional[int] = None
    ) -> Optional[Position]:
        """Close a position (or partial close)"""
        position = self.get_position(symbol)
        if not position:
            return None
        
        # Partial close support
        close_quantity = quantity if quantity else position.quantity
        
        if close_quantity == position.quantity:
            # Full close
            position.close(exit_price, exit_time, exit_costs)
            self.positions.remove(position)
            self.closed_positions.append(position)
            
            # Add cash (sell proceeds)
            proceeds = (exit_price * close_quantity) - exit_costs
            self.cash += proceeds
            
            return position
        else:
            # Partial close - create new position for remaining quantity
            # For simplicity, we'll close full position
            # In production, you'd split positions
            position.close(exit_price, exit_time, exit_costs)
            self.positions.remove(position)
            self.closed_positions.append(position)
            
            proceeds = (exit_price * close_quantity) - exit_costs
            self.cash += proceeds
            
            return position
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Get total portfolio value"""
        positions_value = 0.0
        
        for position in self.positions:
            if position.symbol in current_prices:
                positions_value += current_prices[position.symbol] * position.quantity
        
        return self.cash + positions_value
    
    def get_total_pnl(self, current_prices: Dict[str, float]) -> Dict:
        """Get total P&L breakdown"""
        realized_pnl = sum(
            pos.get_realized_pnl() or 0.0
            for pos in self.closed_positions
        )
        
        unrealized_pnl = sum(
            pos.get_unrealized_pnl(current_prices.get(pos.symbol, pos.entry_price))
            for pos in self.positions
        )
        
        total_pnl = realized_pnl + unrealized_pnl
        
        portfolio_value = self.get_portfolio_value(current_prices)
        
        return {
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "cash": round(self.cash, 2),
            "positions_value": round(portfolio_value - self.cash, 2),
            "portfolio_value": round(portfolio_value, 2),
            "total_return": round((portfolio_value - self.initial_capital) / self.initial_capital * 100, 2),
            "initial_capital": self.initial_capital
        }
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        if not self.closed_positions:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "avg_holding_period": 0.0
            }
        
        winning_trades = [p for p in self.closed_positions if p.get_realized_pnl() and p.get_realized_pnl() > 0]
        losing_trades = [p for p in self.closed_positions if p.get_realized_pnl() and p.get_realized_pnl() <= 0]
        
        avg_win = sum(p.get_realized_pnl() for p in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(p.get_realized_pnl() for p in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        holding_periods = [p.get_holding_period() for p in self.closed_positions if p.get_holding_period()]
        avg_holding = sum(holding_periods) / len(holding_periods) if holding_periods else 0.0
        
        return {
            "total_trades": len(self.closed_positions),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": round(len(winning_trades) / len(self.closed_positions) * 100, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else float('inf'),
            "avg_holding_period_days": round(avg_holding, 2)
        }


"""
Performance metrics calculator for backtesting results.
Calculates Sharpe ratio, Sortino ratio, max drawdown, etc.
"""
from typing import List, Dict, Optional
import math
from datetime import datetime


class PerformanceMetrics:
    """Calculate performance metrics from trade history"""
    
    @staticmethod
    def calculate_sharpe_ratio(
        returns: List[float],
        risk_free_rate: float = 0.06  # 6% annual risk-free rate
    ) -> float:
        """
        Calculate Sharpe ratio.
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Annual risk-free rate (default 6%)
        
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        # Convert to daily risk-free rate (assuming 252 trading days)
        daily_rf = risk_free_rate / 252
        
        # Calculate excess returns
        excess_returns = [r - daily_rf for r in returns]
        
        if not excess_returns:
            return 0.0
        
        # Mean excess return
        mean_excess = sum(excess_returns) / len(excess_returns)
        
        # Standard deviation
        variance = sum((r - mean_excess) ** 2 for r in excess_returns) / len(excess_returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualize
        sharpe = (mean_excess / std_dev) * math.sqrt(252)
        
        return round(sharpe, 4)
    
    @staticmethod
    def calculate_sortino_ratio(
        returns: List[float],
        risk_free_rate: float = 0.06
    ) -> float:
        """
        Calculate Sortino ratio (downside deviation only).
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Annual risk-free rate
        
        Returns:
            Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        daily_rf = risk_free_rate / 252
        excess_returns = [r - daily_rf for r in returns]
        
        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in excess_returns if r < 0]
        
        if not downside_returns:
            return float('inf') if sum(excess_returns) > 0 else 0.0
        
        downside_variance = sum(r ** 2 for r in downside_returns) / len(excess_returns)
        downside_std = math.sqrt(downside_variance)
        
        if downside_std == 0:
            return 0.0
        
        mean_excess = sum(excess_returns) / len(excess_returns)
        sortino = (mean_excess / downside_std) * math.sqrt(252)
        
        return round(sortino, 4)
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> Dict:
        """
        Calculate maximum drawdown.
        
        Args:
            equity_curve: List of portfolio values over time
        
        Returns:
            Dictionary with max drawdown details
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "peak": equity_curve[0] if equity_curve else 0.0,
                "trough": equity_curve[0] if equity_curve else 0.0
            }
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        peak_val = peak
        trough_val = peak
        
        for value in equity_curve:
            if value > peak:
                peak = value
                peak_val = value
            
            drawdown = peak - value
            drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0.0
            
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_pct = drawdown_pct
                trough_val = value
        
        return {
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "peak": round(peak_val, 2),
            "trough": round(trough_val, 2)
        }
    
    @staticmethod
    def calculate_cagr(
        initial_value: float,
        final_value: float,
        days: int
    ) -> float:
        """
        Calculate Compound Annual Growth Rate (CAGR).
        
        Args:
            initial_value: Starting value
            final_value: Ending value
            days: Number of days
        
        Returns:
            CAGR as percentage
        """
        if initial_value <= 0 or days <= 0:
            return 0.0
        
        years = days / 365.25
        if years <= 0:
            return 0.0
        
        cagr = ((final_value / initial_value) ** (1 / years) - 1) * 100
        
        return round(cagr, 2)
    
    @staticmethod
    def calculate_metrics(
        returns: List[float],
        equity_curve: List[float],
        initial_capital: float,
        final_value: float,
        days: int,
        risk_free_rate: float = 0.06
    ) -> Dict:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            returns: List of periodic returns
            equity_curve: Portfolio values over time
            initial_capital: Starting capital
            final_value: Final portfolio value
            days: Number of trading days
            risk_free_rate: Annual risk-free rate
        
        Returns:
            Dictionary with all metrics
        """
        total_return = ((final_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0
        
        sharpe = PerformanceMetrics.calculate_sharpe_ratio(returns, risk_free_rate)
        sortino = PerformanceMetrics.calculate_sortino_ratio(returns, risk_free_rate)
        max_dd = PerformanceMetrics.calculate_max_drawdown(equity_curve)
        cagr = PerformanceMetrics.calculate_cagr(initial_capital, final_value, days)
        
        # Volatility (annualized)
        if returns and len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance) * math.sqrt(252) * 100  # Annualized %
        else:
            volatility = 0.0
        
        return {
            "total_return_pct": round(total_return, 2),
            "cagr_pct": cagr,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "volatility_pct": round(volatility, 2),
            "max_drawdown": max_dd,
            "initial_capital": round(initial_capital, 2),
            "final_value": round(final_value, 2),
            "total_days": days
        }


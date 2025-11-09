"""
Backtesting API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal, BacktestResult
from backend.utils.backtest_engine import backtest_engine
from backend.utils.signal_strategies import (
    MultiIndicatorStrategy,
    RSIStrategy,
    MACDCrossoverStrategy,
    BollingerBandsStrategy,
    ADXTrendStrategy,
    VWAPStrategy
)
from backend.utils.data_fetcher import data_fetcher
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BacktestRequest(BaseModel):
    """Backtest request model"""
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0
    strategy: str = "multi_indicator"  # multi_indicator, rsi, macd, bollinger, adx, vwap
    position_size_pct: float = 0.1  # 10% per trade
    max_positions: int = 1
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    order_type: str = "market"
    timeframe: str = "5m"


def get_strategy(strategy_name: str):
    """Get strategy instance by name"""
    strategies = {
        "multi_indicator": MultiIndicatorStrategy(),
        "rsi": RSIStrategy(),
        "macd": MACDCrossoverStrategy(),
        "bollinger": BollingerBandsStrategy(),
        "adx": ADXTrendStrategy(),
        "vwap": VWAPStrategy()
    }
    return strategies.get(strategy_name, MultiIndicatorStrategy())


@router.post("/run")
async def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    """
    Run a backtest with specified parameters.
    
    Args:
        request: Backtest configuration
        db: Database session
    
    Returns:
        Backtest results
    """
    try:
        # Fetch historical data
        period = "1mo" if not request.start_date else "max"
        candles = await data_fetcher.fetch_candles(
            symbol=request.symbol,
            interval=request.timeframe,
            period=period,
            bypass_cache=False
        )
        
        if not candles:
            raise HTTPException(status_code=404, detail=f"No data found for {request.symbol}")
        
        # Parse dates
        start_date = None
        end_date = None
        if request.start_date:
            start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
        if request.end_date:
            end_date = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
        
        # Get strategy
        strategy = get_strategy(request.strategy)
        
        # Run backtest
        logger.info(f"Running backtest for {request.symbol} with {request.strategy} strategy")
        results = backtest_engine.run_backtest(
            symbol=request.symbol,
            candles=candles,
            initial_capital=request.initial_capital,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            order_type=request.order_type,
            position_size_pct=request.position_size_pct,
            max_positions=request.max_positions,
            stop_loss_pct=request.stop_loss_pct,
            take_profit_pct=request.take_profit_pct
        )
        
        # Save to database
        backtest_record = BacktestResult(
            symbol=request.symbol,
            strategy_name=request.strategy,
            start_date=datetime.fromisoformat(results["start_date"].replace('Z', '+00:00')),
            end_date=datetime.fromisoformat(results["end_date"].replace('Z', '+00:00')),
            initial_capital=results["initial_capital"],
            final_value=results["final_value"],
            total_return_pct=results["metrics"]["total_return_pct"],
            cagr_pct=results["metrics"]["cagr_pct"],
            sharpe_ratio=results["metrics"]["sharpe_ratio"],
            sortino_ratio=results["metrics"]["sortino_ratio"],
            max_drawdown_pct=results["metrics"]["max_drawdown"]["max_drawdown_pct"],
            volatility_pct=results["metrics"]["volatility_pct"],
            total_trades=results["statistics"]["total_trades"],
            winning_trades=results["statistics"]["winning_trades"],
            losing_trades=results["statistics"]["losing_trades"],
            win_rate=results["statistics"]["win_rate"],
            profit_factor=results["statistics"]["profit_factor"],
            results_json=results,
            equity_curve=results["equity_curve"],
            trades=results["trades"]
        )
        
        db.add(backtest_record)
        db.commit()
        db.refresh(backtest_record)
        
        return {
            "backtest_id": backtest_record.id,
            "results": results,
            "summary": {
                "total_return": f"{results['metrics']['total_return_pct']:.2f}%",
                "sharpe_ratio": results['metrics']['sharpe_ratio'],
                "max_drawdown": f"{results['metrics']['max_drawdown']['max_drawdown_pct']:.2f}%",
                "win_rate": f"{results['statistics']['win_rate']:.2f}%",
                "total_trades": results['statistics']['total_trades']
            }
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results")
async def get_backtest_results(
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    limit: int = Query(10, le=100),
    db: Session = Depends(get_db)
):
    """Get backtest results"""
    query = db.query(BacktestResult)
    
    if symbol:
        query = query.filter(BacktestResult.symbol == symbol)
    if strategy:
        query = query.filter(BacktestResult.strategy_name == strategy)
    
    results = query.order_by(BacktestResult.created_at.desc()).limit(limit).all()
    
    return {
        "results": [r.to_dict() for r in results],
        "count": len(results)
    }


@router.get("/results/{backtest_id}")
async def get_backtest_result(backtest_id: int, db: Session = Depends(get_db)):
    """Get specific backtest result"""
    result = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    return result.to_dict()


@router.get("/strategies")
async def get_available_strategies():
    """Get list of available trading strategies"""
    return {
        "strategies": [
            {
                "name": "multi_indicator",
                "description": "Multi-indicator strategy combining RSI, MACD, Bollinger Bands, ADX, MFI",
                "indicators": ["RSI", "MACD", "Bollinger Bands", "ADX", "MFI", "Moving Averages"]
            },
            {
                "name": "rsi",
                "description": "RSI-based momentum strategy",
                "indicators": ["RSI"]
            },
            {
                "name": "macd",
                "description": "MACD crossover strategy",
                "indicators": ["MACD"]
            },
            {
                "name": "bollinger",
                "description": "Bollinger Bands mean reversion strategy",
                "indicators": ["Bollinger Bands"]
            },
            {
                "name": "adx",
                "description": "ADX trend following strategy",
                "indicators": ["ADX", "+DI", "-DI"]
            },
            {
                "name": "vwap",
                "description": "VWAP-based strategy",
                "indicators": ["VWAP"]
            }
        ]
    }


@router.get("/indicators")
async def get_available_indicators():
    """Get list of all available indicators"""
    return {
        "indicators": [
            {"name": "RSI", "type": "momentum", "description": "Relative Strength Index (0-100)"},
            {"name": "MACD", "type": "trend", "description": "Moving Average Convergence Divergence"},
            {"name": "SMA", "type": "trend", "description": "Simple Moving Average (20, 50)"},
            {"name": "EMA", "type": "trend", "description": "Exponential Moving Average (9, 21)"},
            {"name": "Bollinger Bands", "type": "volatility", "description": "Upper, Middle, Lower bands"},
            {"name": "Stochastic", "type": "momentum", "description": "Stochastic Oscillator (%K, %D)"},
            {"name": "ADX", "type": "trend", "description": "Average Directional Index (+DI, -DI)"},
            {"name": "MFI", "type": "momentum", "description": "Money Flow Index (volume-weighted RSI)"},
            {"name": "ATR", "type": "volatility", "description": "Average True Range"},
            {"name": "OBV", "type": "volume", "description": "On-Balance Volume"},
            {"name": "VWAP", "type": "volume", "description": "Volume-Weighted Average Price"}
        ]
    }


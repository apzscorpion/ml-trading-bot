"""
Debug endpoints for troubleshooting data sync issues
"""
from fastapi import APIRouter, Query
from datetime import datetime
import logging

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)


@router.post("/clear-cache")
async def clear_cache():
    """Clear the data fetcher cache (both Redis and in-memory)"""
    try:
        from backend.utils.data_fetcher import data_fetcher
        from backend.utils.redis_cache import redis_cache
        
        # Clear in-memory cache
        data_fetcher.cache.clear()
        logger.info("In-memory cache cleared")
        
        # Clear Redis cache if available
        try:
            redis_cache.clear_all()
            logger.info("Redis cache cleared")
        except Exception as e:
            logger.warning(f"Could not clear Redis cache: {e}")
        
        return {
            "message": "Cache cleared successfully",
            "status": "success",
            "cleared": {
                "in_memory": True,
                "redis": True
            }
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {"error": str(e), "status": "error"}


@router.get("/latest-data")
async def get_latest_data(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query(..., description="Timeframe")
):
    """Get the latest data from backend to debug sync issues"""
    try:
        from backend.utils.data_fetcher import data_fetcher
        
        # Map timeframe to period
        period_map = {
            "1m": "1d", "5m": "5d", "15m": "5d", 
            "1h": "1mo", "4h": "3mo", "1d": "2y",
            "5d": "2y", "1wk": "5y", "1mo": "10y", "3mo": "10y"
        }
        period = period_map.get(timeframe, "1d")
        
        # Fetch latest candles
        candles = await data_fetcher.fetch_candles(symbol, timeframe, period)
        
        if not candles:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "error": "No data returned from Yahoo Finance",
                "status": "error"
            }
        
        latest_candle = candles[-1]
        
        # Handle start_ts - it's already an ISO string from fetch_candles
        start_ts_str = latest_candle["start_ts"]
        if isinstance(start_ts_str, str):
            time_str = start_ts_str
        else:
            time_str = start_ts_str.isoformat()
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_candles": len(candles),
            "latest_candle": {
                "time": time_str,
                "open": latest_candle["open"],
                "high": latest_candle["high"],
                "low": latest_candle["low"],
                "close": latest_candle["close"],
                "volume": latest_candle["volume"]
            },
            "backend_time": datetime.now().isoformat(),
            "cache_key": f"{symbol}_{timeframe}_{period}",
            "cache_size": len(data_fetcher.cache),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching debug data: {e}")
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "error": str(e),
            "status": "error"
        }


@router.get("/verify-symbol")
async def verify_symbol(symbol: str = Query(..., description="Stock symbol")):
    """Verify what Yahoo Finance returns for a symbol"""
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        data = ticker.history(period="1d", interval="5m")
        
        if data.empty:
            return {
                "symbol": symbol,
                "error": "No data returned",
                "status": "error"
            }
        
        latest = data.iloc[-1]
        
        return {
            "requested_symbol": symbol,
            "yahoo_symbol": info.get("symbol", "N/A"),
            "company_name": info.get("longName", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "N/A"),
            "latest_price": float(latest["Close"]),
            "latest_time": data.index[-1].isoformat(),
            "data_points": len(data),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error verifying symbol: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "status": "error"
        }

"""
Data fetcher for Indian stocks using Yahoo Finance API and Twelve Data as fallback.
Handles NSE (.NS) and BSE (.BO) symbols.
Uses Redis hot cache + in-memory LRU warm cache.
Validates trading days and filters out non-trading days (holidays, weekends).
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import OrderedDict
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytz
from backend.utils.redis_cache import redis_cache
from backend.data_pipeline import DataPipeline
from backend.utils.exchange_calendar import exchange_calendar
from backend.config import settings

logger = logging.getLogger(__name__)

# Thread pool executor for blocking Yahoo Finance calls
_executor = ThreadPoolExecutor(max_workers=5)
_data_pipeline = DataPipeline()


class DataFetcher:
    """Fetches stock data from Yahoo Finance"""
    
    def __init__(self, max_cache_size: int = 100):
        self.cache: OrderedDict[str, tuple] = OrderedDict()
        self.cache_duration = timedelta(seconds=30)  # Reduced cache time for fresher data
        self.max_cache_size = max_cache_size
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """
        Get from cache with LRU eviction.
        
        Args:
            cache_key: Cache key
        
        Returns:
            Cached data or None if not found or expired
        """
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                # Move to end (most recently used)
                self.cache.move_to_end(cache_key)
                self.cache_hits += 1
                logger.debug(f"Cache hit for {cache_key}")
                return cached_data
            else:
                # Expired, remove it
                del self.cache[cache_key]
                self.cache_misses += 1
                logger.debug(f"Cache expired for {cache_key}")
                return None
        self.cache_misses += 1
        return None
    
    def _set_cache(self, cache_key: str, data: List[Dict]):
        """
        Set cache with LRU eviction.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        # Remove oldest entries if cache is full
        while len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False)  # Remove oldest
        
        self.cache[cache_key] = (data, datetime.now())
        logger.debug(f"Cached data for {cache_key}, cache size: {len(self.cache)}")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics including Redis stats.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            "warm_cache": {
                "cache_size": len(self.cache),
                "max_cache_size": self.max_cache_size,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "hit_rate_percent": round(hit_rate, 2)
            },
            "hot_cache": redis_cache.get_stats()
        }
        
        return stats
    
    def _fetch_candles_sync(
        self, 
        symbol: str, 
        interval: str = "5m", 
        period: str = "1d",
        bypass_cache: bool = False
    ) -> List[Dict]:
        """
        Synchronous implementation of fetch_candles (runs in thread pool).
        Uses Redis hot cache first, then in-memory warm cache.
        CRITICAL: Respects bypass_cache parameter - skips ALL caching when True.
        """
        # CRITICAL: Check caches ONLY if bypass_cache is False
        if not bypass_cache:
            # Try Redis hot cache first
            redis_data = redis_cache.get(symbol, interval, period)
            if redis_data is not None:
                self.cache_hits += 1
                logger.debug(f"✅ Redis cache HIT: {symbol}:{interval}:{period}")
                # Also update warm cache for faster subsequent access
                cache_key = f"{symbol}_{interval}_{period}"
                self._set_cache(cache_key, redis_data)
                return redis_data
            
            # Fallback to in-memory warm cache (LRU)
            cache_key = f"{symbol}_{interval}_{period}"
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                self.cache_hits += 1
                logger.debug(f"✅ Warm cache HIT: {cache_key}")
                return cached_data
            
            # Cache miss
            self.cache_misses += 1
            logger.debug(f"❌ Cache MISS: {cache_key} (will fetch fresh)")
        else:
            logger.info(f"🚫 Bypassing ALL caches for {symbol}:{interval}:{period}")
        
        # Run async fetch in a new event loop for this thread
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                candles = loop.run_until_complete(
                    self._fetch_candles_async(symbol, interval, period, bypass_cache)
                )
                
                # Cache the result if we got data and not bypassing cache
                if candles and not bypass_cache:
                    cache_key = f"{symbol}_{interval}_{period}"
                    self._set_cache(cache_key, candles)
                    redis_cache.set(symbol, interval, candles, period)
                    logger.debug(f"💾 Cached fresh data: {cache_key}")
                
                return candles
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Error in async fetch wrapper: {e}", exc_info=True)
            return []
    
    async def _fetch_candles_async(
        self,
        symbol: str,
        interval: str = "5m",
        period: str = "1d",
        bypass_cache: bool = False
    ) -> List[Dict]:
        """
        Async implementation that handles provider selection and fallback.
        """
        try:
            logger.info(f"Fetching data for {symbol}, interval={interval}, period={period}")
            
            # Try primary provider first
            candles = None
            provider_used = None
            
            # Check if we should use Twelve Data as primary
            if settings.primary_data_provider == "twelvedata" and settings.twelvedata_enabled:
                try:
                    from backend.services.twelvedata_service import twelvedata_service
                    if twelvedata_service.client:
                        logger.info(f"Using Twelve Data as primary provider for {symbol}")
                        candles = await twelvedata_service.fetch_candles(
                            symbol=symbol,
                            interval=interval,
                            period=period,
                            use_cache=not bypass_cache
                        )
                        provider_used = "twelvedata"
                        if candles:
                            logger.info(f"Successfully fetched {len(candles)} candles from Twelve Data")
                except Exception as e:
                    logger.warning(f"Twelve Data fetch failed: {e}")
                    candles = None
            
            # If primary provider failed or not configured, try Yahoo Finance
            if not candles:
                try:
                    logger.info(f"Using Yahoo Finance for {symbol}")
                    # Run Yahoo Finance in thread pool since it's blocking
                    loop = asyncio.get_event_loop()
                    
                    def fetch_yahoo():
                        ticker = yf.Ticker(symbol)
                        return ticker.history(period=period, interval=interval)
                    
                    df = await loop.run_in_executor(_executor, fetch_yahoo)
                    
                    if df.empty:
                        logger.debug(f"No data returned for {symbol} (may be market closed or symbol unavailable)")
                        # Try Twelve Data as fallback if enabled
                        if settings.use_twelvedata_as_fallback and settings.twelvedata_enabled:
                            try:
                                from backend.services.twelvedata_service import twelvedata_service
                                if twelvedata_service.client:
                                    logger.info(f"Yahoo Finance returned no data, trying Twelve Data as fallback for {symbol}")
                                    candles = await twelvedata_service.fetch_candles(
                                        symbol=symbol,
                                        interval=interval,
                                        period=period,
                                        use_cache=not bypass_cache
                                    )
                                    provider_used = "twelvedata_fallback"
                                    if candles:
                                        logger.info(f"Successfully fetched {len(candles)} candles from Twelve Data (fallback)")
                            except Exception as e:
                                logger.debug(f"Twelve Data fallback also failed: {e}")
                        
                        if not candles:
                            return []
                    else:
                        # Process Yahoo Finance data
                        candles = []
                        ist = pytz.timezone('Asia/Kolkata')
                        current_time = datetime.now(ist)
                        
                        for index, row in df.iterrows():
                            # Handle timezone properly - Yahoo Finance returns in stock's local timezone
                            ts = index.to_pydatetime()
                            
                            # Yahoo Finance data for NSE/BSE stocks is in IST (Asia/Kolkata)
                            # Keep timezone info to preserve correct IST times
                            # The frontend chart is configured for Asia/Kolkata timezone
                            if ts.tzinfo is None:
                                # If naive (no timezone), assume it's IST
                                ts = ist.localize(ts)
                            
                            # CRITICAL: Filter out future dates - never allow data from the future
                            # Add 1 hour buffer to account for timezone differences and API delays
                            if ts > current_time + timedelta(hours=1):
                                logger.warning(f"Skipping future-dated candle: {ts.isoformat()} (current time: {current_time.isoformat()})")
                                continue
                            
                            # CRITICAL: Filter out non-trading days (holidays, weekends)
                            candle_date = ts.date()
                            if not exchange_calendar.is_trading_day(candle_date):
                                logger.debug(f"Skipping non-trading day candle: {ts.isoformat()} (date: {candle_date.isoformat()})")
                                continue
                            
                            # CRITICAL: Filter out data outside trading hours (for intraday timeframes)
                            # For daily/weekly/monthly timeframes, allow any time on trading day
                            # For intraday (1m, 5m, 15m, 1h), filter by trading hours
                            if interval in ['1m', '5m', '15m', '1h', '4h']:
                                if not exchange_calendar.is_market_open(ts):
                                    # For intraday, skip if outside trading hours
                                    logger.debug(f"Skipping candle outside trading hours: {ts.isoformat()}")
                                    continue
                            
                            # Convert to ISO format string with timezone info
                            # This ensures JavaScript Date() interprets it correctly
                            candle = {
                                "start_ts": ts.isoformat(),  # ISO format with timezone
                                "open": float(row["Open"]),
                                "high": float(row["High"]),
                                "low": float(row["Low"]),
                                "close": float(row["Close"]),
                                "volume": float(row["Volume"]) if "Volume" in row else 0.0
                            }
                            candles.append(candle)
                        
                        provider_used = "yahoo"
                        
                except Exception as e:
                    error_msg = str(e).lower()
                    # Try Twelve Data as fallback if Yahoo Finance fails
                    if settings.use_twelvedata_as_fallback and settings.twelvedata_enabled:
                        try:
                            from backend.services.twelvedata_service import twelvedata_service
                            if twelvedata_service.client:
                                logger.info(f"Yahoo Finance failed ({e}), trying Twelve Data as fallback for {symbol}")
                                candles = await twelvedata_service.fetch_candles(
                                    symbol=symbol,
                                    interval=interval,
                                    period=period,
                                    use_cache=not bypass_cache
                                )
                                provider_used = "twelvedata_fallback"
                                if candles:
                                    logger.info(f"Successfully fetched {len(candles)} candles from Twelve Data (fallback)")
                        except Exception as fallback_error:
                            logger.debug(f"Twelve Data fallback also failed: {fallback_error}")
                    
                    # If all providers failed, handle error
                    if not candles:
                        if "delisted" in error_msg or "no price data" in error_msg or "no data" in error_msg:
                            # This is expected for unavailable symbols or market closed, don't spam logs
                            logger.debug(f"No data available for {symbol} (may be delisted or market closed)")
                        else:
                            logger.warning(f"Error fetching data for {symbol}: {e}")
                        return []
            
            if not candles:
                return []
            
            # Sort candles by start_ts ascending (oldest first) for chronological order
            candles.sort(key=lambda x: datetime.fromisoformat(x.get('start_ts', '').replace('Z', '+00:00')) if isinstance(x.get('start_ts'), str) else x.get('start_ts', datetime.min))
            
            # CRITICAL: Validate chronological order - ensure no gaps or out-of-order dates
            if len(candles) > 1:
                prev_ts = None
                filtered_candles = []
                for candle in candles:
                    candle_ts_str = candle.get('start_ts')
                    if not candle_ts_str:
                        logger.warning(f"Skipping candle without timestamp: {candle}")
                        continue
                    
                    try:
                        candle_ts = datetime.fromisoformat(candle_ts_str.replace('Z', '+00:00'))
                        
                        # Skip if this candle is before the previous one (out of order)
                        if prev_ts and candle_ts < prev_ts:
                            logger.warning(f"Skipping out-of-order candle: {candle_ts.isoformat()} (previous: {prev_ts.isoformat()})")
                            continue
                        
                        filtered_candles.append(candle)
                        prev_ts = candle_ts
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Skipping candle with invalid timestamp {candle_ts_str}: {e}")
                        continue
                
                candles = filtered_candles
                
                if len(candles) > 0:
                    first_ts = datetime.fromisoformat(candles[0]['start_ts'].replace('Z', '+00:00'))
                    last_ts = datetime.fromisoformat(candles[-1]['start_ts'].replace('Z', '+00:00'))
                    logger.info(f"Validated {len(candles)} candles from {provider_used}: {first_ts.isoformat()} to {last_ts.isoformat()}")
            
            # Persist to data pipeline for auditability
            try:
                artifacts = _data_pipeline.ingest(
                    symbol=symbol,
                    timeframe=interval,
                    candles=candles,
                    provider=provider_used or "unknown",
                    dataset_version=settings.dataset_version,
                )
                redis_cache.register_dataset_metadata(
                    symbol=symbol,
                    interval=interval,
                    dataset_version=artifacts.dataset_version,
                    run_id=artifacts.run_id,
                    provider=provider_used or "unknown",
                )
                logger.debug(
                    "Data pipeline persisted dataset %s %s version=%s run=%s records=%s",
                    symbol,
                    interval,
                    artifacts.dataset_version,
                    artifacts.run_id,
                    artifacts.record_count,
                )
            except Exception as pipeline_error:
                logger.warning(
                    "Data pipeline ingest failed for %s %s: %s",
                    symbol,
                    interval,
                    pipeline_error,
                )
            
            # Cache the results (only if not bypassing cache)
            if not bypass_cache:
                # Store in Redis hot cache first
                redis_cache.set(symbol, interval, candles, period)
                # Also store in warm cache (in-memory LRU)
                cache_key = f"{symbol}_{interval}_{period}"
                self._set_cache(cache_key, candles)
            
            logger.info(f"Fetched {len(candles)} candles for {symbol} using {provider_used or 'yahoo'}")
            return candles
            
        except Exception as e:
            logger.error(f"Unexpected error in data fetcher: {e}", exc_info=True)
            return []
    
    async def fetch_candles(
        self, 
        symbol: str, 
        interval: str = "5m", 
        period: str = "1d",
        bypass_cache: bool = False
    ) -> List[Dict]:
        """
        Fetch candle data for a symbol (async version).
        
        Args:
            symbol: Stock symbol (e.g., 'TCS.NS', 'RELIANCE.BO')
            interval: Candle interval ('1m', '5m', '15m', '1h', '1d')
            period: Time period ('1d', '5d', '1mo', 'max')
            bypass_cache: If True, skip cache and always fetch fresh data
        
        Returns:
            List of candle dictionaries with OHLCV data (sorted by start_ts ascending)
        """
        # Run the blocking Yahoo Finance call in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._fetch_candles_sync,
            symbol,
            interval,
            period,
            bypass_cache
        )
    
    def fetch_latest_price(self, symbol: str) -> Optional[float]:
        """
        Fetch the latest price for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Latest price or None if unavailable
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if data.empty:
                return None
            
            return float(data["Close"].iloc[-1])
            
        except Exception as e:
            logger.error(f"Error fetching latest price for {symbol}: {e}")
            return None
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol is valid and tradeable.
        
        Args:
            symbol: Stock symbol to validate
        
        Returns:
            True if valid, False otherwise
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data
            if not info or "symbol" not in info:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    def get_indian_stock_symbols(self) -> List[str]:
        """
        Returns a list of popular Indian stock symbols for autocomplete.
        
        Returns:
            List of stock symbols
        """
        # Popular Indian stocks (NSE)
        nse_stocks = [
            "TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
            "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "HCLTECH.NS",
            "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS", "ULTRACEMCO.NS", "WIPRO.NS"
        ]
        
        return nse_stocks


# Singleton instance
data_fetcher = DataFetcher()


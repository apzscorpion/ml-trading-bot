"""
Twelve Data Service Manager
Handles API calls to Twelve Data for financial market data.
Provides time series data, technical indicators, and WebSocket support.
Follows service manager pattern with proper error handling and caching.
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
from twelvedata import TDClient
from backend.config import settings
from backend.utils.logger import get_logger
from backend.utils.redis_cache import redis_cache
import json
import pytz

logger = get_logger(__name__)


class TwelveDataServiceManager:
    """
    Service manager for Twelve Data API calls.
    Handles time series data, technical indicators, and WebSocket connections.
    Provides caching, error handling, and rate limiting.
    """
    
    def __init__(self):
        # Don't cache API key - read from settings each time to allow dynamic updates
        self.timeout = settings.twelvedata_timeout
        self.cache_ttl = settings.twelvedata_cache_ttl
        self.enabled = settings.twelvedata_enabled
        self.rate_limit = settings.twelvedata_rate_limit
        self._client = None  # Will be created lazily
        self._cached_api_key = None  # Track API key used for client
        
        if not self.enabled:
            logger.warning("Twelve Data is disabled in configuration")
    
    @property
    def api_key(self):
        """Get API key from settings dynamically"""
        return settings.twelvedata_api_key
    
    @property
    def client(self):
        """Get or create TDClient instance"""
        if not self.enabled:
            return None
        
        api_key = self.api_key
        if not api_key:
            return None
        
        # Recreate client if API key changed
        if self._client is None or self._cached_api_key != api_key:
            try:
                self._client = TDClient(apikey=api_key)
                self._cached_api_key = api_key
                logger.info(f"Twelve Data client initialized successfully (API key length: {len(api_key)})")
            except Exception as e:
                logger.error(f"Failed to initialize Twelve Data client: {e}")
                self._client = None
                self._cached_api_key = None
        
        return self._client
    
    def reset_client(self):
        """Reset the client to force recreation with current API key"""
        self._client = None
        self._cached_api_key = None
        logger.info("Twelve Data client reset - will be recreated on next access")
    
    def _get_cache_key(self, symbol: str, interval: str, period: str = None) -> str:
        """Generate cache key for Twelve Data responses"""
        cache_key = f"twelvedata:{symbol}:{interval}"
        if period:
            cache_key += f":{period}"
        return cache_key
    
    async def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Get cached response from Redis"""
        if not settings.redis_enabled or not redis_cache.client:
            return None
        
        try:
            cached = redis_cache.client.get(cache_key)
            if cached:
                # Try msgpack first, fallback to JSON
                try:
                    import msgpack
                    return msgpack.unpackb(cached, raw=False)
                except:
                    return json.loads(cached.decode('utf-8'))
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None
    
    async def _set_cache(self, cache_key: str, data: List[Dict]):
        """Cache response in Redis"""
        if not settings.redis_enabled or not redis_cache.client:
            return
        
        try:
            # Use msgpack for efficient serialization
            import msgpack
            serialized = msgpack.packb(data, use_bin_type=True)
            redis_cache.client.setex(cache_key, self.cache_ttl, serialized)
        except Exception as e:
            logger.debug(f"Cache write error: {e}")
    
    def _convert_twelvedata_symbol(self, symbol: str) -> str:
        """
        Convert Yahoo Finance symbol format to Twelve Data format.
        
        Args:
            symbol: Symbol in Yahoo Finance format (e.g., 'TCS.NS', 'RELIANCE.BO')
        
        Returns:
            Symbol in Twelve Data format (e.g., 'TCS', 'BSE:RELIANCE')
        """
        if not symbol:
            return symbol
        
        # Remove .NS suffix for NSE stocks (Twelve Data uses symbol directly)
        if symbol.endswith('.NS'):
            return symbol.replace('.NS', '')
        
        # Convert .BO to BSE: prefix
        if symbol.endswith('.BO'):
            return f"BSE:{symbol.replace('.BO', '')}"
        
        # Return as-is if no suffix
        return symbol
    
    def _convert_yahoo_interval(self, interval: str) -> str:
        """
        Convert Yahoo Finance interval to Twelve Data interval format.
        
        Args:
            interval: Yahoo Finance interval (e.g., '1m', '5m', '1h', '1d')
        
        Returns:
            Twelve Data interval format (e.g., '1min', '5min', '1hour', '1day')
        """
        interval_map = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '1hour',
            '4h': '4hour',
            '1d': '1day',
            '5d': '5day',
            '1wk': '1week',
            '1mo': '1month',
            '3mo': '3month'
        }
        return interval_map.get(interval, interval)
    
    def _convert_period_to_outputsize(self, period: str) -> int:
        """
        Convert Yahoo Finance period to Twelve Data outputsize.
        
        Args:
            period: Yahoo Finance period (e.g., '1d', '5d', '1mo', 'max')
        
        Returns:
            Number of candles to fetch
        """
        period_map = {
            '1d': 288,      # 1 day of 5-min candles
            '5d': 1440,     # 5 days of 5-min candles
            '1mo': 8640,    # ~1 month of 5-min candles
            '3mo': 25920,   # ~3 months of 5-min candles
            'max': 5000     # Maximum allowed by free tier
        }
        return period_map.get(period, 100)
    
    def _normalize_candle_data(self, candle_data: Dict, interval: str) -> Dict:
        """
        Normalize Twelve Data candle format to match Yahoo Finance format.
        
        Args:
            candle_data: Raw candle data from Twelve Data
            interval: Interval string
        
        Returns:
            Normalized candle dictionary
        """
        ist = pytz.timezone('Asia/Kolkata')
        
        # Parse datetime - Twelve Data can return different formats
        datetime_str = candle_data.get('datetime', '')
        dt = None
        
        if datetime_str:
            try:
                # Try different datetime formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',      # '2024-01-01 09:15:00'
                    '%Y-%m-%dT%H:%M:%S',      # '2024-01-01T09:15:00'
                    '%Y-%m-%d %H:%M:%S%z',    # With timezone
                    '%Y-%m-%dT%H:%M:%S%z',   # ISO format with timezone
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(datetime_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt is None:
                    # Fallback: try parsing as ISO format
                    try:
                        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    except:
                        # Last resort: parse as string
                        dt = datetime.strptime(datetime_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                
                # Assume IST timezone for Indian stocks if no timezone info
                if dt.tzinfo is None:
                    dt = ist.localize(dt)
                else:
                    # Convert to IST if needed
                    dt = dt.astimezone(ist)
                    
            except Exception as e:
                logger.warning(f"Failed to parse datetime {datetime_str}: {e}")
                dt = datetime.now(ist)
        else:
            dt = datetime.now(ist)
        
        return {
            'start_ts': dt.isoformat(),
            'open': float(candle_data.get('open', 0)),
            'high': float(candle_data.get('high', 0)),
            'low': float(candle_data.get('low', 0)),
            'close': float(candle_data.get('close', 0)),
            'volume': float(candle_data.get('volume', 0))
        }
    
    async def fetch_time_series(
        self,
        symbol: str,
        interval: str = "5m",
        outputsize: int = 100,
        use_cache: bool = True
    ) -> Optional[List[Dict]]:
        """
        Fetch time series data from Twelve Data.
        
        Args:
            symbol: Stock symbol (e.g., 'TCS.NS', 'RELIANCE.BO')
            interval: Candle interval ('1m', '5m', '15m', '1h', '1d')
            outputsize: Number of candles to fetch
            use_cache: Whether to use cached responses
        
        Returns:
            List of candle dictionaries with OHLCV data or None if failed
        """
        if not self.enabled:
            logger.debug("Twelve Data is disabled")
            return None
        
        if not self.client:
            logger.warning("Twelve Data client not initialized")
            return None
        
        # Convert symbol and interval formats
        td_symbol = self._convert_twelvedata_symbol(symbol)
        td_interval = self._convert_yahoo_interval(interval)
        
        cache_key = self._get_cache_key(symbol, interval, str(outputsize))
        
        # Check cache first
        if use_cache:
            cached = await self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Using cached Twelve Data response for {symbol}")
                return cached
        
        try:
            # Fetch time series data
            # Run in thread pool since TDClient might be blocking
            loop = asyncio.get_event_loop()
            
            def fetch_sync():
                try:
                    # Capture API key in closure to ensure it's available in thread
                    api_key_to_use = str(self.api_key) if self.api_key else None
                    if not api_key_to_use or len(api_key_to_use) < 20:
                        logger.error(f"Invalid API key in executor thread: length={len(api_key_to_use) if api_key_to_use else 0}")
                        return None
                    
                    logger.debug(f"Using API key: {api_key_to_use[:8]}... (length: {len(api_key_to_use)})")
                    client = TDClient(apikey=api_key_to_use)
                    ts = client.time_series(
                        symbol=td_symbol,
                        interval=td_interval,
                        outputsize=outputsize,
                        timezone="Asia/Kolkata"
                    )
                    return ts.as_json()
                except Exception as e:
                    logger.error(f"Twelve Data API error: {e}")
                    import traceback
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                    return None
            
            data = await loop.run_in_executor(None, fetch_sync)
            
            if not data:
                return None
            
            # Normalize candle data
            candles = []
            if isinstance(data, dict):
                # Single symbol response with 'values' key
                values = data.get('values', [])
                for candle_data in values:
                    normalized = self._normalize_candle_data(candle_data, interval)
                    candles.append(normalized)
            elif isinstance(data, (list, tuple)):
                # Multiple symbols response or tuple of candles
                for item in data:
                    if isinstance(item, dict):
                        # Check if it's a candle dict (has 'datetime', 'open', etc.) or a wrapper
                        if 'datetime' in item or 'open' in item:
                            # It's a candle dictionary directly
                            normalized = self._normalize_candle_data(item, interval)
                            candles.append(normalized)
                        elif 'values' in item:
                            # It's a wrapper with 'values' key
                            values = item.get('values', [])
                            for candle_data in values:
                                normalized = self._normalize_candle_data(candle_data, interval)
                                candles.append(normalized)
            else:
                logger.warning(f"Unexpected data type from Twelve Data: {type(data)}")
                return None
            
            # Sort by timestamp ascending
            candles.sort(key=lambda x: x.get('start_ts', ''))
            
            # Cache the results
            if use_cache and candles:
                await self._set_cache(cache_key, candles)
            
            logger.info(f"Fetched {len(candles)} candles from Twelve Data for {symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching time series from Twelve Data: {e}", exc_info=True)
            return None
    
    async def fetch_candles(
        self,
        symbol: str,
        interval: str = "5m",
        period: str = "1d",
        use_cache: bool = True
    ) -> Optional[List[Dict]]:
        """
        Fetch candle data matching DataFetcher interface.
        
        Args:
            symbol: Stock symbol (e.g., 'TCS.NS', 'RELIANCE.BO')
            interval: Candle interval ('1m', '5m', '15m', '1h', '1d')
            period: Time period ('1d', '5d', '1mo', 'max')
            use_cache: Whether to use cached responses
        
        Returns:
            List of candle dictionaries with OHLCV data (sorted by start_ts ascending)
        """
        # Convert period to outputsize
        outputsize = self._convert_period_to_outputsize(period)
        
        # Fetch from Twelve Data
        candles = await self.fetch_time_series(
            symbol=symbol,
            interval=interval,
            outputsize=outputsize,
            use_cache=use_cache
        )
        
        if not candles:
            return None
        
        # Apply same filtering as DataFetcher:
        # - Filter out future dates
        # - Filter out non-trading days
        # - Filter out outside trading hours for intraday
        
        from backend.utils.exchange_calendar import exchange_calendar
        
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)
        filtered_candles = []
        
        for candle in candles:
            try:
                # Parse timestamp
                candle_ts_str = candle.get('start_ts', '')
                if not candle_ts_str:
                    continue
                
                candle_ts = datetime.fromisoformat(candle_ts_str.replace('Z', '+00:00'))
                if candle_ts.tzinfo is None:
                    candle_ts = ist.localize(candle_ts)
                
                # Filter out future dates
                if candle_ts > current_time + timedelta(hours=1):
                    logger.debug(f"Skipping future-dated candle: {candle_ts.isoformat()}")
                    continue
                
                # Filter out non-trading days
                candle_date = candle_ts.date()
                if not exchange_calendar.is_trading_day(candle_date):
                    logger.debug(f"Skipping non-trading day candle: {candle_ts.isoformat()}")
                    continue
                
                # Filter out data outside trading hours for intraday timeframes
                if interval in ['1m', '5m', '15m', '1h', '4h']:
                    if not exchange_calendar.is_market_open(candle_ts):
                        logger.debug(f"Skipping candle outside trading hours: {candle_ts.isoformat()}")
                        continue
                
                filtered_candles.append(candle)
                
            except Exception as e:
                logger.warning(f"Error filtering candle: {e}")
                continue
        
        # Sort by timestamp ascending
        filtered_candles.sort(key=lambda x: datetime.fromisoformat(x.get('start_ts', '').replace('Z', '+00:00')) if isinstance(x.get('start_ts'), str) else datetime.min)
        
        logger.info(f"Filtered {len(filtered_candles)} valid candles from {len(candles)} total for {symbol}")
        return filtered_candles
    
    async def fetch_with_indicators(
        self,
        symbol: str,
        interval: str = "5m",
        outputsize: int = 100,
        indicators: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Fetch time series data with technical indicators.
        
        Args:
            symbol: Stock symbol
            interval: Candle interval
            outputsize: Number of candles to fetch
            indicators: List of indicators to compute (e.g., ['macd', 'rsi', 'bbands'])
        
        Returns:
            Dictionary with candles and indicator data
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            td_symbol = self._convert_twelvedata_symbol(symbol)
            td_interval = self._convert_yahoo_interval(interval)
            
            # Build time series query
            ts = self.client.time_series(
                symbol=td_symbol,
                interval=td_interval,
                outputsize=outputsize,
                timezone="Asia/Kolkata"
            )
            
            # Add indicators
            if indicators:
                if 'macd' in indicators:
                    ts = ts.with_macd()
                if 'rsi' in indicators:
                    ts = ts.with_rsi()
                if 'bbands' in indicators:
                    ts = ts.with_bbands()
                if 'stoch' in indicators:
                    ts = ts.with_stoch()
                if 'ema' in indicators:
                    ts = ts.with_ema()
            
            # Fetch data
            loop = asyncio.get_event_loop()
            
            def fetch_sync():
                try:
                    return ts.as_json()
                except Exception as e:
                    logger.error(f"Twelve Data indicators API error: {e}")
                    return None
            
            data = await loop.run_in_executor(None, fetch_sync)
            
            if not data:
                return None
            
            # Normalize and return
            result = {
                'symbol': symbol,
                'interval': interval,
                'data': data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching indicators from Twelve Data: {e}", exc_info=True)
            return None
    
    def get_websocket_client(
        self,
        symbols: List[str],
        on_event: callable,
        logger_instance: Optional[logging.Logger] = None
    ):
        """
        Create a WebSocket client for real-time data streaming.
        
        Args:
            symbols: List of symbols to subscribe to
            on_event: Callback function for incoming events
            logger_instance: Optional logger instance
        
        Returns:
            WebSocket client object or None if failed
        """
        if not self.enabled or not self.client:
            logger.warning("Twelve Data WebSocket not available (disabled or not initialized)")
            return None
        
        try:
            # Convert symbols to Twelve Data format
            td_symbols = [self._convert_twelvedata_symbol(s) for s in symbols]
            
            ws = self.client.websocket(
                symbols=td_symbols,
                on_event=on_event,
                logger=logger_instance
            )
            
            return ws
            
        except Exception as e:
            logger.error(f"Error creating Twelve Data WebSocket client: {e}", exc_info=True)
            return None
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol is valid and accessible via Twelve Data.
        
        Args:
            symbol: Stock symbol to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            td_symbol = self._convert_twelvedata_symbol(symbol)
            ts = self.client.time_series(
                symbol=td_symbol,
                interval="1day",
                outputsize=1
            )
            data = ts.as_json()
            return data is not None and len(data.get('values', [])) > 0
            
        except Exception as e:
            logger.debug(f"Symbol validation failed for {symbol}: {e}")
            return False


# Singleton instance
twelvedata_service = TwelveDataServiceManager()


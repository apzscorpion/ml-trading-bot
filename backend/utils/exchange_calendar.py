"""
NSE/BSE Exchange Calendar for Indian Markets.
Handles holidays, early closures, and trading hours validation.
Fetches holidays from NSE/BSE APIs in real-time with fallback to static calendar.
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Set
import pytz
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Cache TTL for holiday data (24 hours)
HOLIDAY_CACHE_TTL = 86400  # 24 hours in seconds


class ExchangeCalendar:
    """NSE/BSE Exchange Calendar for Indian Markets"""
    
    def __init__(self):
        # NSE/BSE trading hours (IST)
        self.market_open = datetime.strptime("09:15", "%H:%M").time()
        self.market_close = datetime.strptime("15:30", "%H:%M").time()
        self.pre_open_start = datetime.strptime("09:00", "%H:%M").time()
        self.pre_open_end = datetime.strptime("09:15", "%H:%M").time()
        self.post_close_end = datetime.strptime("15:40", "%H:%M").time()
        
        # Static holidays (fallback when API is unavailable)
        self._static_holidays: Set[date] = {
            # 2024 Holidays
            date(2024, 1, 26),   # Republic Day
            date(2024, 3, 8),    # Holi
            date(2024, 3, 29),   # Good Friday
            date(2024, 4, 11),   # Eid ul-Fitr
            date(2024, 4, 17),   # Ram Navami
            date(2024, 5, 1),    # Maharashtra Day
            date(2024, 6, 17),   # Eid ul-Adha
            date(2024, 8, 15),   # Independence Day
            date(2024, 8, 26),   # Janmashtami
            date(2024, 10, 2),   # Gandhi Jayanti
            date(2024, 10, 31),  # Diwali Balipratipada
            date(2024, 11, 1),   # Diwali
            date(2024, 11, 15),  # Guru Nanak Jayanti
            date(2024, 12, 25),  # Christmas
            
            # 2025 Holidays
            date(2025, 1, 26),   # Republic Day
            date(2025, 3, 14),   # Holi
            date(2025, 4, 18),   # Good Friday
            date(2025, 5, 1),    # Maharashtra Day
            date(2025, 8, 15),   # Independence Day
            date(2025, 10, 2),   # Gandhi Jayanti
            date(2025, 10, 5),   # CRITICAL: October 5, 2025 - Market Holiday (Dussehra/Vijayadashami)
            date(2025, 10, 20),  # Dussehra
            date(2025, 10, 21),  # Diwali Balipratipada
            date(2025, 10, 22),  # Diwali
            date(2025, 11, 5),   # Diwali Balipratipada
            date(2025, 11, 14),  # Diwali
            date(2025, 12, 25),  # Christmas
        }
        
        # Dynamic holidays fetched from API (merged with static)
        self._dynamic_holidays: Set[date] = set()
        
        # Combined holidays (static + dynamic)
        self.holidays: Set[date] = self._static_holidays.copy()
        
        # Early closure days (half-day trading)
        self.early_closures: Dict[date, datetime.time] = {
            date(2024, 10, 31): datetime.strptime("13:30", "%H:%M").time(),  # Diwali eve
            date(2025, 10, 21): datetime.strptime("13:30", "%H:%M").time(),  # Diwali eve
        }
        
        # Last fetch time for holidays
        self._last_holiday_fetch: Optional[datetime] = None
        
        # Initialize: Try to load from cache, otherwise use static
        self._init_holidays()
    
    def _init_holidays(self):
        """Initialize holidays - try to load from cache, otherwise use static"""
        try:
            from backend.utils.redis_cache import redis_cache
            cache_key = "exchange_calendar:holidays"
            cached_data = redis_cache._redis_client.get(cache_key) if redis_cache._redis_client else None
            
            if cached_data:
                try:
                    cached_holidays = eval(cached_data)
                    if isinstance(cached_holidays, set):
                        holiday_dates = {date.fromisoformat(d) if isinstance(d, str) else d for d in cached_holidays}
                        self._dynamic_holidays = holiday_dates
                        self.holidays = self._static_holidays | self._dynamic_holidays
                        self._last_holiday_fetch = datetime.now()
                        logger.info(f"Loaded {len(self._dynamic_holidays)} holidays from cache")
                        return
                except Exception as e:
                    logger.debug(f"Error loading cached holidays: {e}")
        except Exception as e:
            logger.debug(f"Error initializing holidays from cache: {e}")
        
        # Use static calendar as fallback
        logger.debug("Using static holiday calendar (cache unavailable)")
    
    def is_trading_day(self, check_date: date) -> bool:
        """
        Check if given date is a trading day.
        
        Args:
            check_date: Date to check
        
        Returns:
            True if trading day, False otherwise
        """
        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if holiday
        if check_date in self.holidays:
            return False
        
        return True
    
    def get_market_close_time(self, check_date: date) -> datetime.time:
        """
        Get market close time for given date.
        Returns early closure time if applicable, otherwise regular close time.
        
        Args:
            check_date: Date to check
        
        Returns:
            Market close time
        """
        if check_date in self.early_closures:
            return self.early_closures[check_date]
        return self.market_close
    
    def is_market_open(self, check_datetime: datetime) -> bool:
        """
        Check if market is currently open at given datetime.
        
        Args:
            check_datetime: Datetime to check (must be in IST or naive)
        
        Returns:
            True if market is open, False otherwise
        """
        # Convert to IST if needed
        if check_datetime.tzinfo is None:
            check_datetime = IST.localize(check_datetime)
        else:
            check_datetime = check_datetime.astimezone(IST)
        
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        # Check if trading day
        if not self.is_trading_day(check_date):
            return False
        
        # Check if within trading hours
        market_close_time = self.get_market_close_time(check_date)
        
        if self.market_open <= check_time <= market_close_time:
            return True
        
        return False
    
    def get_next_trading_day(self, from_date: date, days_ahead: int = 1) -> date:
        """
        Get the next trading day N days ahead.
        
        Args:
            from_date: Starting date
            days_ahead: Number of trading days ahead (default: 1)
        
        Returns:
            Next trading day
        """
        current_date = from_date
        trading_days_found = 0
        
        while trading_days_found < days_ahead:
            current_date += timedelta(days=1)
            if self.is_trading_day(current_date):
                trading_days_found += 1
        
        return current_date
    
    def get_trading_calendar(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get trading calendar for date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            List of trading day information dictionaries
        """
        calendar = []
        current_date = start_date
        
        while current_date <= end_date:
            is_trading = self.is_trading_day(current_date)
            close_time = self.get_market_close_time(current_date)
            
            calendar.append({
                "date": current_date.isoformat(),
                "is_trading_day": is_trading,
                "market_open": self.market_open.isoformat(),
                "market_close": close_time.isoformat(),
                "is_early_closure": current_date in self.early_closures,
                "day_of_week": current_date.strftime("%A")
            })
            
            current_date += timedelta(days=1)
        
        return calendar
    
    def add_holiday(self, holiday_date: date):
        """Add a custom holiday"""
        self.holidays.add(holiday_date)
        logger.info(f"Added holiday: {holiday_date}")
    
    def remove_holiday(self, holiday_date: date):
        """Remove a holiday"""
        self.holidays.discard(holiday_date)
        logger.info(f"Removed holiday: {holiday_date}")
    
    async def _fetch_nse_holidays(self) -> Optional[Set[date]]:
        """
        Fetch holidays from NSE website/API.
        
        NOTE: NSE/BSE don't have official public APIs for holidays.
        You can integrate with:
        - Web scraping from NSE's holiday calendar page
        - Third-party APIs (Alpha Vantage, TradingView, etc.)
        - Custom API endpoints if you have access
        
        Returns:
            Set of holiday dates or None if fetch fails
        """
        try:
            # Example: Try NSE's holiday calendar page
            async with httpx.AsyncClient(timeout=10.0) as client:
                # NSE publishes holidays annually, but doesn't have a public API
                # You can implement web scraping here or use third-party services
                # For now, return None to use static calendar
                return None
                    
        except Exception as e:
            logger.debug(f"Error fetching NSE holidays: {e}")
            return None
    
    async def _fetch_holidays_from_third_party(self) -> Optional[Set[date]]:
        """
        Fetch holidays from third-party APIs (Alpha Vantage, TradingView, etc.)
        
        Returns:
            Set of holiday dates or None if fetch fails
        """
        try:
            # Example: Using Alpha Vantage Economic Calendar API
            # api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            # if not api_key:
            #     return None
            
            # You can integrate with:
            # 1. Alpha Vantage: https://www.alphavantage.co/documentation/#economic-calendar
            # 2. TradingView: They have calendar APIs
            # 3. Direct scraping from NSE website
            
            # Since we don't have API keys configured, return None to use static calendar
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching holidays from third-party: {e}")
            return None
    
    async def _refresh_holidays_from_api(self) -> bool:
        """
        Refresh holidays from API sources.
        Falls back to static calendar if API fails.
        
        Returns:
            True if holidays were refreshed, False otherwise
        """
        # Check cache first
        cache_key = "exchange_calendar:holidays"
        try:
            from backend.utils.redis_cache import redis_cache
            cached_data = redis_cache._redis_client.get(cache_key) if redis_cache._redis_client else None
            
            if cached_data:
                try:
                    cached_holidays = eval(cached_data)  # Simple deserialization
                    if isinstance(cached_holidays, set):
                        holiday_dates = {date.fromisoformat(d) if isinstance(d, str) else d for d in cached_holidays}
                        self._dynamic_holidays = holiday_dates
                        self.holidays = self._static_holidays | self._dynamic_holidays
                        self._last_holiday_fetch = datetime.now()
                        logger.info(f"Loaded {len(self._dynamic_holidays)} holidays from cache")
                        return True
                except Exception as e:
                    logger.debug(f"Error loading cached holidays: {e}")
        except Exception:
            pass
        
        # Try to fetch from API
        try:
            # Try NSE holidays first
            nse_holidays = await self._fetch_nse_holidays()
            
            if nse_holidays:
                self._dynamic_holidays = nse_holidays
                self.holidays = self._static_holidays | self._dynamic_holidays
                self._last_holiday_fetch = datetime.now()
                
                # Cache the holidays
                try:
                    from backend.utils.redis_cache import redis_cache
                    if redis_cache._redis_client:
                        holiday_strings = {d.isoformat() for d in nse_holidays}
                        redis_cache._redis_client.setex(cache_key, HOLIDAY_CACHE_TTL, str(holiday_strings))
                except Exception:
                    pass
                
                logger.info(f"✅ Refreshed {len(self._dynamic_holidays)} holidays from API")
                return True
            
            # Fallback to third-party API
            third_party_holidays = await self._fetch_holidays_from_third_party()
            if third_party_holidays:
                self._dynamic_holidays = third_party_holidays
                self.holidays = self._static_holidays | self._dynamic_holidays
                self._last_holiday_fetch = datetime.now()
                
                # Cache the holidays
                try:
                    from backend.utils.redis_cache import redis_cache
                    if redis_cache._redis_client:
                        holiday_strings = {d.isoformat() for d in third_party_holidays}
                        redis_cache._redis_client.setex(cache_key, HOLIDAY_CACHE_TTL, str(holiday_strings))
                except Exception:
                    pass
                
                logger.info(f"✅ Refreshed {len(self._dynamic_holidays)} holidays from third-party API")
                return True
                
        except Exception as e:
            logger.warning(f"Failed to refresh holidays from API: {e}")
            # Fallback to static calendar (already initialized)
        
        # Use static calendar as fallback
        logger.debug("Using static holiday calendar (API unavailable)")
        return False
    
    async def refresh_holidays(self) -> bool:
        """
        Public method to refresh holidays from API.
        Can be called periodically or on-demand.
        
        Returns:
            True if holidays were refreshed, False otherwise
        """
        return await self._refresh_holidays_from_api()
    
    def should_refresh_holidays(self) -> bool:
        """
        Check if holidays should be refreshed from API.
        
        Returns:
            True if refresh is needed (24 hours passed or never fetched)
        """
        if self._last_holiday_fetch is None:
            return True
        
        time_since_fetch = datetime.now() - self._last_holiday_fetch
        return time_since_fetch.total_seconds() >= HOLIDAY_CACHE_TTL
    
    def validate_trading_session(self, check_datetime: datetime) -> Dict:
        """
        Validate trading session and return detailed status.
        
        Args:
            check_datetime: Datetime to check
        
        Returns:
            Dictionary with session status
        """
        # Convert to IST if needed
        if check_datetime.tzinfo is None:
            check_datetime = IST.localize(check_datetime)
        else:
            check_datetime = check_datetime.astimezone(IST)
        
        check_date = check_datetime.date()
        check_time = check_datetime.time()
        
        is_trading_day = self.is_trading_day(check_date)
        market_close_time = self.get_market_close_time(check_date)
        
        if not is_trading_day:
            return {
                "is_market_open": False,
                "reason": "non_trading_day",
                "date": check_date.isoformat(),
                "time": check_time.isoformat(),
                "market_open": self.market_open.isoformat(),
                "market_close": market_close_time.isoformat(),
                "next_trading_day": self.get_next_trading_day(check_date).isoformat()
            }
        
        if check_time < self.market_open:
            return {
                "is_market_open": False,
                "reason": "before_market_open",
                "date": check_date.isoformat(),
                "time": check_time.isoformat(),
                "market_open": self.market_open.isoformat(),
                "market_close": market_close_time.isoformat(),
                "opens_in_minutes": int((datetime.combine(check_date, self.market_open) - 
                                       datetime.combine(check_date, check_time)).total_seconds() / 60)
            }
        
        if check_time > market_close_time:
            return {
                "is_market_open": False,
                "reason": "after_market_close",
                "date": check_date.isoformat(),
                "time": check_time.isoformat(),
                "market_open": self.market_open.isoformat(),
                "market_close": market_close_time.isoformat(),
                "next_trading_day": self.get_next_trading_day(check_date).isoformat()
            }
        
        return {
            "is_market_open": True,
            "reason": "market_open",
            "date": check_date.isoformat(),
            "time": check_time.isoformat(),
            "market_open": self.market_open.isoformat(),
            "market_close": market_close_time.isoformat(),
            "session_type": "early_closure" if check_date in self.early_closures else "regular"
        }


# Singleton instance
exchange_calendar = ExchangeCalendar()

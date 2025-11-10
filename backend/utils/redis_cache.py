"""
Redis hot cache for recent candles with TTL.
Implements versioned cache keys: symbol:interval:dataset-vX
"""
import redis
import json
import msgpack
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis hot cache for most-recent N candles per symbol"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.enabled = settings.redis_enabled
        self.ttl = settings.redis_ttl_seconds
        self.dataset_version = settings.dataset_version
        
        if self.enabled:
            try:
                # Railway/Render provides REDIS_URL, use it if available
                if settings.redis_url:
                    self.client = redis.from_url(
                        settings.redis_url,
                        decode_responses=False,  # Keep binary for msgpack
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        retry_on_timeout=True
                    )
                    logger.info("Redis cache connected via REDIS_URL")
                else:
                    # Fallback to individual connection parameters
                    self.client = redis.Redis(
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_db,
                        password=settings.redis_password if settings.redis_password else None,
                        decode_responses=False,  # Keep binary for msgpack
                        socket_connect_timeout=2,
                        socket_timeout=2,
                        retry_on_timeout=True
                    )
                    logger.info("Redis cache connected", redis_host=settings.redis_host, redis_port=settings.redis_port)
                
                # Test connection
                self.client.ping()
            except Exception as e:
                logger.warning(
                    "Redis connection failed, falling back to in-memory cache",
                    error=str(e)
                )
                self.client = None
                self.enabled = False
    
    def _make_cache_key(self, symbol: str, interval: str, period: str = None) -> str:
        """
        Create versioned cache key: symbol:interval:dataset-vX
        
        Args:
            symbol: Stock symbol
            interval: Timeframe (1m, 5m, etc.)
            period: Optional period (1d, 5d, etc.)
        
        Returns:
            Cache key string
        """
        if period:
            return f"{symbol}:{interval}:{period}:dataset-{self.dataset_version}"
        return f"{symbol}:{interval}:dataset-{self.dataset_version}"
    
    def get(self, symbol: str, interval: str, period: str = None) -> Optional[List[Dict]]:
        """
        Get candles from Redis cache.
        
        Args:
            symbol: Stock symbol
            interval: Timeframe
            period: Optional period
        
        Returns:
            List of candles or None if not found
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            cache_key = self._make_cache_key(symbol, interval, period)
            data = self.client.get(cache_key)
            
            if data:
                # Try msgpack first (more efficient), fallback to JSON
                try:
                    candles = msgpack.unpackb(data, raw=False)
                except:
                    candles = json.loads(data.decode('utf-8'))
                
                logger.debug("Redis cache hit", cache_key=cache_key)
                return candles
            else:
                logger.debug("Redis cache miss", cache_key=cache_key)
                return None
                
        except Exception as e:
            logger.error("Redis get error", error=str(e), error_type=type(e).__name__)
            return None
    
    def set(self, symbol: str, interval: str, candles: List[Dict], period: str = None):
        """
        Store candles in Redis cache with TTL.
        
        Args:
            symbol: Stock symbol
            interval: Timeframe
            candles: List of candle dictionaries
            period: Optional period
        """
        if not self.enabled or not self.client:
            return
        
        try:
            cache_key = self._make_cache_key(symbol, interval, period)
            
            # Use msgpack for compact binary serialization
            data = msgpack.packb(candles, use_bin_type=True)
            
            # Set with TTL
            self.client.setex(cache_key, self.ttl, data)
            logger.debug("Redis cache set", cache_key=cache_key, ttl=self.ttl, candles_count=len(candles))
            
        except Exception as e:
            logger.error("Redis set error", error=str(e), error_type=type(e).__name__)

    def register_dataset_metadata(
        self,
        symbol: str,
        interval: str,
        dataset_version: str,
        run_id: str,
        provider: str,
    ) -> None:
        """Persist metadata about the latest dataset version per symbol/timeframe."""

        if not self.enabled or not self.client:
            return

        try:
            meta_key = f"{symbol}:{interval}:dataset-meta"
            payload = {
                "dataset_version": dataset_version,
                "last_run_id": run_id,
                "provider": provider,
                "updated_at": datetime.utcnow().isoformat(),
            }
            self.client.hset(meta_key, mapping=payload)
            self.client.expire(meta_key, self.ttl)
        except Exception as exc:
            logger.debug("Redis metadata registration error", error=str(exc))
    
    def delete(self, symbol: str, interval: str, period: str = None):
        """
        Delete cache entry.
        
        Args:
            symbol: Stock symbol
            interval: Timeframe
            period: Optional period
        """
        if not self.enabled or not self.client:
            return
        
        try:
            cache_key = self._make_cache_key(symbol, interval, period)
            self.client.delete(cache_key)
            logger.debug("Redis cache deleted", cache_key=cache_key)
        except Exception as e:
            logger.error("Redis delete error", error=str(e), error_type=type(e).__name__)
    
    def clear_all(self):
        """
        Clear all cached data from Redis.
        Uses pattern matching to find all cache keys.
        
        Returns:
            Number of keys cleared
        """
        if not self.enabled or not self.client:
            return 0
        
        try:
            # Get all keys matching our cache pattern (*:dataset-*)
            keys = self.client.keys("*")
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cleared {deleted} keys from Redis cache")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Error clearing Redis cache: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """
        Get Redis cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = self.client.info('stats')
            return {
                "enabled": True,
                "keyspace_keys": info.get('keyspace_keys', 0),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "connected_clients": info.get('connected_clients', 0),
                "used_memory_human": info.get('used_memory_human', '0B')
            }
        except Exception as e:
            logger.error("Redis stats error", error=str(e), error_type=type(e).__name__)
            return {"enabled": False, "error": str(e)}
    
    def ping(self) -> bool:
        """Check if Redis is available"""
        if not self.enabled or not self.client:
            return False
        try:
            return self.client.ping()
        except:
            return False


# Singleton instance
redis_cache = RedisCache()


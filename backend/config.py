"""
Configuration settings for the trading prediction app.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    database_url: str = "sqlite:///./trading_predictions.db"
    default_symbol: str = "TCS.NS"
    prediction_interval: int = 300  # seconds
    yahoo_finance_interval: str = "5m"
    log_level: str = "WARNING"  # Changed from INFO to WARNING to reduce log verbosity
    
    # WebSocket settings
    ws_heartbeat_interval: int = 30
    
    # CORS settings - Railway/Vercel deployment support
    allowed_origins: str = "http://localhost:5155,http://localhost:3000,http://192.168.167.178:5155,https://*.railway.app,https://*.vercel.app"
    
    # Market index symbols
    nifty_symbol: str = "^NSEI"
    sensex_symbol: str = "^BSESN"
    
    # Feature flags
    trend_prediction_enabled: bool = True
    market_prediction_enabled: bool = True
    
    # Redis settings (Railway provides REDIS_URL automatically)
    redis_url: str = ""  # Railway/Render will set this automatically
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_enabled: bool = True  # Set to False to use in-memory cache only
    redis_ttl_seconds: int = 300  # 5 minutes TTL for hot cache
    
    # Cache settings
    dataset_version: str = "v1"  # Version for cache keys
    data_root: str = "data"  # Base directory for data pipeline artifacts (can be absolute path for external storage)
    model_storage_path: str = "models"  # Directory for storing trained models (can be absolute path for external storage)
    
    # Prediction settings
    default_horizon_minutes: int = 180  # 3 hours
    min_candles_for_prediction: int = 50
    
    # Supported timeframes
    supported_timeframes: List[str] = ["1m", "5m", "15m", "1h", "4h", "1d", "5d", "1wk", "1mo", "3mo"]
    
    # Freddy AI API settings
    freddy_api_key: str = ""
    freddy_organization_id: str = ""
    freddy_assistant_id: str = ""
    freddy_api_base_url: str = "https://freddy-api.aitronos.ch/v1"
    freddy_model: str = "gpt-4o"  # Model to use for Freddy AI
    freddy_temperature: float = 0.7  # Temperature for responses
    freddy_timeout: int = 30  # Request timeout in seconds
    freddy_cache_ttl: int = 300  # Cache TTL in seconds (5 minutes)
    freddy_enabled: bool = True  # Enable/disable Freddy AI integration
    
    # Twelve Data API settings
    twelvedata_api_key: str = ""  # API key should be 32 characters
    twelvedata_timeout: int = 30  # Request timeout in seconds
    twelvedata_cache_ttl: int = 300  # Cache TTL in seconds (5 minutes)
    twelvedata_enabled: bool = True  # Enable/disable Twelve Data integration
    twelvedata_rate_limit: int = 800  # Requests per day (free tier: 800, paid tiers: higher)
    
    # Data provider settings
    primary_data_provider: str = "yahoo"  # "yahoo" or "twelvedata"
    use_twelvedata_as_fallback: bool = True  # Use Twelve Data as fallback if Yahoo Finance fails
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        # Ensure no truncation
        extra = 'ignore'


settings = Settings()


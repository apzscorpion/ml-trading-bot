"""
Production-specific configuration and utilities for Railway/Render deployment.
"""
import os
from typing import Optional


def get_production_settings() -> dict:
    """
    Get production-specific settings from environment variables.
    Railway and Render automatically provide these.
    """
    return {
        "database_url": os.getenv("DATABASE_URL"),
        "redis_url": os.getenv("REDIS_URL"),
        "port": int(os.getenv("PORT", 8000)),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", os.getenv("RENDER", "production")),
        "is_production": os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RENDER") is not None,
    }


def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RENDER") is not None


def get_frontend_url() -> str:
    """Get frontend URL for CORS"""
    # Railway provides this automatically
    railway_url = os.getenv("RAILWAY_STATIC_URL")
    if railway_url:
        return f"https://{railway_url}"
    
    # Vercel frontend
    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        return f"https://{vercel_url}"
    
    # Custom domain
    custom_domain = os.getenv("FRONTEND_URL")
    if custom_domain:
        return custom_domain
    
    # Fallback to localhost
    return "http://localhost:5155"


def should_skip_model_loading() -> bool:
    """
    Determine if we should skip loading ML models on startup.
    Useful for first deployment or when models are too large.
    """
    return os.getenv("SKIP_MODEL_LOADING", "false").lower() == "true"


def get_log_level() -> str:
    """Get appropriate log level for environment"""
    if is_production():
        return os.getenv("LOG_LEVEL", "WARNING")
    return os.getenv("LOG_LEVEL", "INFO")


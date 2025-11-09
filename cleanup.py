#!/usr/bin/env python3
"""
Complete cleanup script - removes all cached data, models, and database records.
This will force the system to start fresh with new data.
"""
import os
import sys
import shutil
import redis
import sqlite3
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def clear_redis_cache():
    """Clear all Redis cache entries"""
    if not settings.redis_enabled:
        logger.info("Redis is disabled, skipping Redis cleanup")
        return
    
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password if settings.redis_password else None,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        client.ping()
        
        # Get all keys matching our pattern
        pattern = f"*:dataset-{settings.dataset_version}"
        keys = client.keys(pattern)
        
        if keys:
            deleted = client.delete(*keys)
            logger.info(f"✅ Deleted {deleted} Redis cache entries")
        else:
            logger.info("✅ No Redis cache entries found")
            
        # Also try to clear all keys (in case pattern doesn't match)
        all_keys = client.keys("*")
        if all_keys:
            deleted = client.delete(*all_keys)
            logger.info(f"✅ Deleted {deleted} additional Redis keys")
            
    except redis.ConnectionError:
        logger.warning("❌ Could not connect to Redis - it may not be running")
    except Exception as e:
        logger.error(f"❌ Error clearing Redis: {e}")


def delete_model_files():
    """Delete all trained model files"""
    models_dir = Path(__file__).parent / "backend" / "models"
    
    if not models_dir.exists():
        logger.info("✅ No models directory found")
        return
    
    deleted_count = 0
    for file in models_dir.iterdir():
        if file.is_file() and file.name != ".gitkeep":
            try:
                file.unlink()
                deleted_count += 1
                logger.info(f"🗑️  Deleted: {file.name}")
            except Exception as e:
                logger.error(f"❌ Error deleting {file.name}: {e}")
    
    logger.info(f"✅ Deleted {deleted_count} model files")


def clear_database_tables():
    """Clear all data from SQLite database tables"""
    db_files = [
        Path(__file__).parent / "backend" / "trading_predictions.db",
        Path(__file__).parent / "backend" / "trading_bot.db",
        Path(__file__).parent / "trading_predictions.db",
        Path(__file__).parent / "trading_bot.db",
    ]
    
    for db_path in db_files:
        if not db_path.exists():
            continue
            
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # Clear each table
            for (table_name,) in tables:
                if table_name != "sqlite_sequence":
                    cursor.execute(f"DELETE FROM {table_name}")
                    deleted = cursor.rowcount
                    logger.info(f"🗑️  Cleared {deleted} rows from {table_name} in {db_path.name}")
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Cleared database: {db_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Error clearing database {db_path.name}: {e}")


def clear_pycache():
    """Remove all __pycache__ directories"""
    backend_dir = Path(__file__).parent / "backend"
    deleted_count = 0
    
    for pycache_dir in backend_dir.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache_dir)
            deleted_count += 1
        except Exception as e:
            logger.error(f"❌ Error deleting {pycache_dir}: {e}")
    
    if deleted_count > 0:
        logger.info(f"✅ Deleted {deleted_count} __pycache__ directories")


def main():
    """Run complete cleanup"""
    logger.info("=" * 60)
    logger.info("🧹 STARTING COMPLETE CLEANUP")
    logger.info("=" * 60)
    
    # 1. Clear Redis cache
    logger.info("\n📦 Step 1: Clearing Redis cache...")
    clear_redis_cache()
    
    # 2. Delete model files
    logger.info("\n🤖 Step 2: Deleting model files...")
    delete_model_files()
    
    # 3. Clear database tables
    logger.info("\n💾 Step 3: Clearing database tables...")
    clear_database_tables()
    
    # 4. Clear Python cache
    logger.info("\n🐍 Step 4: Clearing Python cache...")
    clear_pycache()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ CLEANUP COMPLETE!")
    logger.info("=" * 60)
    logger.info("\n📝 Next steps:")
    logger.info("  1. Restart the backend: ./stop.sh && ./start.sh")
    logger.info("  2. Refresh your browser")
    logger.info("  3. The system will fetch fresh data from the last 60 days")
    logger.info("")


if __name__ == "__main__":
    main()


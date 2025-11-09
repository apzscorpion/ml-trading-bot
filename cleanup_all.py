#!/usr/bin/env python3
"""
Complete cleanup script to clear all caches, databases, models, and start fresh.
"""
import os
import sys
import shutil
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    print("🧹 Starting comprehensive cleanup...")
    print(f"📁 Project root: {project_root}")
    
    # 1. Clear Redis cache (if running)
    print("\n1️⃣ Clearing Redis cache...")
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
        client.ping()
        keys = client.keys("*")
        if keys:
            deleted = client.delete(*keys)
            print(f"   ✅ Cleared {deleted} keys from Redis")
        else:
            print(f"   ✅ Redis cache already empty")
    except Exception as e:
        print(f"   ⚠️  Redis not available or already empty: {e}")
    
    # 2. Delete database files
    print("\n2️⃣ Deleting database files...")
    db_files = [
        project_root / "trading_bot.db",
        project_root / "trading_predictions.db",
        project_root / "backend" / "trading_bot.db",
        project_root / "backend" / "trading_predictions.db"
    ]
    
    for db_file in db_files:
        if db_file.exists():
            try:
                db_file.unlink()
                print(f"   ✅ Deleted: {db_file.name}")
            except Exception as e:
                print(f"   ❌ Failed to delete {db_file.name}: {e}")
        else:
            print(f"   ℹ️  Not found: {db_file.name}")
    
    # 3. Clear models directory
    print("\n3️⃣ Clearing models directory...")
    models_dir = project_root / "backend" / "models"
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    print(f"   ✅ Deleted model: {item.name}")
                except Exception as e:
                    print(f"   ❌ Failed to delete {item.name}: {e}")
            elif item.is_dir() and item.name != "__pycache__":
                try:
                    shutil.rmtree(item)
                    print(f"   ✅ Deleted model directory: {item.name}")
                except Exception as e:
                    print(f"   ❌ Failed to delete {item.name}: {e}")
        print(f"   ✅ Models directory cleared")
    else:
        print(f"   ℹ️  Models directory not found or empty")
    
    # 4. Clear log files
    print("\n4️⃣ Clearing log files...")
    log_files = [
        project_root / "logs" / "backend.log",
        project_root / "logs" / "frontend.log",
        project_root / "logs" / "combined.log",
        project_root / "backend" / "backend.log"
    ]
    
    for log_file in log_files:
        if log_file.exists():
            try:
                # Clear content but keep file
                log_file.write_text("")
                print(f"   ✅ Cleared: {log_file.name}")
            except Exception as e:
                print(f"   ❌ Failed to clear {log_file.name}: {e}")
    
    # 5. Clear __pycache__ directories
    print("\n5️⃣ Clearing Python cache...")
    pycache_count = 0
    for pycache_dir in project_root.rglob("__pycache__"):
        if "venv" not in str(pycache_dir):  # Skip virtual environment
            try:
                shutil.rmtree(pycache_dir)
                pycache_count += 1
            except Exception as e:
                print(f"   ⚠️  Failed to delete {pycache_dir}: {e}")
    
    if pycache_count > 0:
        print(f"   ✅ Cleared {pycache_count} __pycache__ directories")
    else:
        print(f"   ℹ️  No __pycache__ directories found")
    
    # 6. Clear PID files
    print("\n6️⃣ Clearing PID files...")
    pid_files = [
        project_root / "logs" / "backend.pid",
        project_root / "logs" / "frontend.pid"
    ]
    
    for pid_file in pid_files:
        if pid_file.exists():
            try:
                pid_file.unlink()
                print(f"   ✅ Deleted: {pid_file.name}")
            except Exception as e:
                print(f"   ❌ Failed to delete {pid_file.name}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Cleanup completed successfully!")
    print("=" * 60)
    print("\n📌 Next steps:")
    print("   1. Run: ./start.sh")
    print("   2. Wait for services to start (databases will be recreated)")
    print("   3. Fresh data will be fetched from API\n")

if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Fix duplicate candles in the database by:
1. Creating a new table with UNIQUE constraint
2. Copying only unique records
3. Replacing the old table
"""
import sqlite3
from pathlib import Path

db_files = [
    Path(__file__).parent / "trading_predictions.db",
    Path(__file__).parent / "backend" / "trading_predictions.db",
]

for db_path in db_files:
    if not db_path.exists():
        continue
    
    print(f"\nProcessing: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if candles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='candles'")
        if not cursor.fetchone():
            print("  ⚠️  No candles table found")
            conn.close()
            continue
        
        # Count duplicates before
        cursor.execute("""
            SELECT COUNT(*) FROM candles
        """)
        total_before = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol || timeframe || start_ts) FROM candles
        """)
        unique_count = cursor.fetchone()[0]
        
        duplicates = total_before - unique_count
        print(f"  📊 Total records: {total_before}")
        print(f"  📊 Unique records: {unique_count}")
        print(f"  📊 Duplicates: {duplicates}")
        
        if duplicates == 0:
            print("  ✅ No duplicates found!")
            conn.close()
            continue
        
        print(f"  🔧 Removing {duplicates} duplicate records...")
        
        # Create new table with unique constraint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candles_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                start_ts TIMESTAMP NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, timeframe, start_ts)
            )
        """)
        
        # Copy unique records (take the first occurrence of each duplicate)
        cursor.execute("""
            INSERT INTO candles_new (symbol, timeframe, start_ts, open, high, low, close, volume)
            SELECT symbol, timeframe, start_ts, open, high, low, close, volume
            FROM candles
            GROUP BY symbol, timeframe, start_ts
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE candles")
        
        # Rename new table
        cursor.execute("ALTER TABLE candles_new RENAME TO candles")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM candles")
        total_after = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ Fixed! Records: {total_before} → {total_after}")
        print(f"  ✅ Removed {total_before - total_after} duplicates")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        if 'conn' in locals():
            conn.close()

print("\n✅ Duplicate cleanup complete!")


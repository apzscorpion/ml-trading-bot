#!/usr/bin/env python3
"""
Remove duplicate candles from database and verify recent data
"""
import sqlite3
from datetime import datetime

def remove_duplicates():
    print("\n🔧 Removing duplicate candles from database...")
    
    db_path = "trading_predictions.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current state
        cursor.execute("SELECT COUNT(*) FROM candles")
        total_before = cursor.fetchone()[0]
        print(f"   Total candles before cleanup: {total_before}")
        
        # Find duplicates
        cursor.execute("""
            SELECT symbol, timeframe, start_ts, COUNT(*) as count
            FROM candles
            GROUP BY symbol, timeframe, start_ts
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        print(f"   Found {len(duplicates)} duplicate groups")
        
        if duplicates:
            # Show some examples
            for symbol, timeframe, start_ts, count in duplicates[:5]:
                print(f"      - {symbol} {timeframe} {start_ts}: {count} copies")
        
        # Remove duplicates - keep the one with the lowest ID (oldest entry)
        cursor.execute("""
            DELETE FROM candles
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM candles
                GROUP BY symbol, timeframe, start_ts
            )
        """)
        deleted = cursor.rowcount
        print(f"   ✅ Deleted {deleted} duplicate candles")
        
        # Check after cleanup
        cursor.execute("SELECT COUNT(*) FROM candles")
        total_after = cursor.fetchone()[0]
        print(f"   Total candles after cleanup: {total_after}")
        
        # Show recent data for TCS
        print(f"\n📊 Recent TCS.NS 5m data:")
        cursor.execute("""
            SELECT start_ts, open, high, low, close, volume
            FROM candles
            WHERE symbol = 'TCS.NS' AND timeframe = '5m'
            ORDER BY start_ts DESC
            LIMIT 10
        """)
        recent = cursor.fetchall()
        for row in recent:
            print(f"      {row[0]}: O={row[1]:.2f} H={row[2]:.2f} L={row[3]:.2f} C={row[4]:.2f}")
        
        conn.commit()
        print("\n✅ Database cleanup completed successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    remove_duplicates()


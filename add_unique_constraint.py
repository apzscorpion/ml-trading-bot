#!/usr/bin/env python3
"""
Add unique constraint to candles table to prevent duplicates
"""
import sqlite3

def add_unique_constraint():
    print("\n🔧 Adding unique constraint to candles table...")
    
    db_path = "trading_predictions.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if unique index already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_candles_unique'
        """)
        
        if cursor.fetchone():
            print("   ℹ️  Unique index already exists")
        else:
            # Create unique index on (symbol, timeframe, start_ts)
            cursor.execute("""
                CREATE UNIQUE INDEX idx_candles_unique 
                ON candles(symbol, timeframe, start_ts)
            """)
            print("   ✅ Created unique index on (symbol, timeframe, start_ts)")
        
        conn.commit()
        print("\n✅ Database constraint added successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_unique_constraint()


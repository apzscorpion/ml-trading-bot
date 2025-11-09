#!/usr/bin/env python3
"""
Test Yahoo Finance data fetching to diagnose date issues
"""
import yfinance as yf
from datetime import datetime
import pandas as pd

# Test fetching data for TCS
symbol = "TCS.NS"
print(f"\n{'='*60}")
print(f"Testing Yahoo Finance data for {symbol}")
print(f"Current time: {datetime.now()}")
print(f"{'='*60}\n")

# Test different periods
test_cases = [
    ("5m", "60d"),
    ("5m", "1d"),
    ("1d", "60d"),
    ("1h", "60d"),
]

for interval, period in test_cases:
    print(f"\n--- Testing: interval={interval}, period={period} ---")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            print(f"❌ No data returned")
        else:
            print(f"✅ Got {len(df)} candles")
            print(f"   First candle: {df.index[0]}")
            print(f"   Last candle:  {df.index[-1]}")
            print(f"   Date range: {(df.index[-1] - df.index[0]).days} days")
            
            # Show first and last few rows
            print(f"\n   First 3 candles:")
            print(df.head(3))
            print(f"\n   Last 3 candles:")
            print(df.tail(3))
            
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*60}\n")


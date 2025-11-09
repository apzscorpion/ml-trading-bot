#!/usr/bin/env python3
"""
Direct test of Yahoo Finance to diagnose data fetching issues
"""
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# Test symbols
symbols = ["TCS.NS", "RELIANCE.NS", "INFY.NS"]

for symbol in symbols:
    print(f"\n{'='*60}")
    print(f"Testing: {symbol}")
    print('='*60)
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Get info
        print(f"\nTicker Info:")
        try:
            info = ticker.info
            print(f"  Name: {info.get('longName', 'N/A')}")
            print(f"  Exchange: {info.get('exchange', 'N/A')}")
            print(f"  Currency: {info.get('currency', 'N/A')}")
            print(f"  Quote Type: {info.get('quoteType', 'N/A')}")
        except Exception as e:
            print(f"  Error getting info: {e}")
        
        # Test different periods and intervals
        test_cases = [
            ("1d", "5m"),
            ("5d", "5m"),
            ("60d", "5m"),
            ("1d", "1h"),
            ("1mo", "1d"),
        ]
        
        for period, interval in test_cases:
            print(f"\n  Testing period={period}, interval={interval}")
            try:
                df = ticker.history(period=period, interval=interval)
                if df.empty:
                    print(f"    ❌ No data returned")
                else:
                    print(f"    ✅ Got {len(df)} candles")
                    print(f"    First: {df.index[0]}")
                    print(f"    Last:  {df.index[-1]}")
                    
                    # Check if last date is recent
                    last_date = df.index[-1]
                    now = datetime.now(pytz.UTC)
                    days_diff = (now - last_date).days
                    print(f"    Last candle is {days_diff} days ago")
                    
                    if days_diff > 7:
                        print(f"    ⚠️  WARNING: Data is stale! Last candle is {days_diff} days old")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Error with {symbol}: {e}")

print(f"\n{'='*60}")
print("Test complete")
print('='*60)


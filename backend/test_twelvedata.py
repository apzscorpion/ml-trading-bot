"""
Twelve Data Integration Test Script
Tests the Twelve Data service manager integration.
"""
import asyncio
import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.twelvedata_service import twelvedata_service
from backend.config import settings


async def test_twelvedata_integration():
    """Test Twelve Data service integration"""
    print("=" * 60)
    print("Twelve Data Integration Test")
    print("=" * 60)
    
    # Check configuration
    print("\n📋 Configuration Check:")
    print(f"  Twelve Data Enabled: {settings.twelvedata_enabled}")
    print(f"  API Key Set: {'✓ Yes' if settings.twelvedata_api_key else '✗ No'}")
    if settings.twelvedata_api_key:
        print(f"  API Key (first 8 chars): {settings.twelvedata_api_key[:8]}...")
    else:
        print(f"  API Key: Not set")
    print(f"  Timeout: {settings.twelvedata_timeout}s")
    print(f"  Cache TTL: {settings.twelvedata_cache_ttl}s")
    
    if not settings.twelvedata_api_key:
        print("\n⚠️  WARNING: TWELVEDATA_API_KEY not set in .env file")
        print("\nTo fix this:")
        print("1. Create a .env file in the project root")
        print("2. Add: TWELVEDATA_API_KEY=d2b5d7d0f6524b5aad12e3b680e85e60")
        print("3. Restart the backend server")
        return False
    
    if not settings.twelvedata_enabled:
        print("\n⚠️  WARNING: Twelve Data is disabled")
        print("Set TWELVEDATA_ENABLED=true in .env to enable")
        return False
    
    # Test symbol conversion
    print("\n🔄 Symbol Conversion Test:")
    test_symbols = ["TCS.NS", "RELIANCE.BO", "INFY.NS"]
    for symbol in test_symbols:
        converted = twelvedata_service._convert_twelvedata_symbol(symbol)
        print(f"  {symbol} → {converted}")
    
    # Test interval conversion
    print("\n⏱️  Interval Conversion Test:")
    test_intervals = ["1m", "5m", "15m", "1h", "1d"]
    for interval in test_intervals:
        converted = twelvedata_service._convert_yahoo_interval(interval)
        print(f"  {interval} → {converted}")
    
    # Test API call
    print("\n🌐 Testing API Call:")
    print("  Fetching time series data for TCS.NS...")
    
    try:
        candles = await twelvedata_service.fetch_time_series(
            symbol="TCS.NS",
            interval="5m",
            outputsize=10,
            use_cache=False
        )
        
        if candles:
            print(f"  ✅ Success! Retrieved {len(candles)} candles")
            if candles:
                print(f"\n  Sample candle:")
                sample = candles[0]
                print(f"    Timestamp: {sample.get('start_ts')}")
                print(f"    Open: {sample.get('open')}")
                print(f"    High: {sample.get('high')}")
                print(f"    Low: {sample.get('low')}")
                print(f"    Close: {sample.get('close')}")
                print(f"    Volume: {sample.get('volume')}")
            return True
        else:
            print("  ❌ No data returned")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_twelvedata_integration())
    sys.exit(0 if success else 1)


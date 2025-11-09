# Twelve Data Integration

## Overview

Twelve Data has been successfully integrated into the trading bot project. This integration provides an alternative data source for fetching financial market data, technical indicators, and real-time WebSocket streams.

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root with the following configuration:

```env
# Twelve Data API Configuration
TWELVEDATA_API_KEY=d2b5d7d0f6524b5aad12e3b680e60
TWELVEDATA_ENABLED=true
TWELVEDATA_TIMEOUT=30
TWELVEDATA_CACHE_TTL=300
TWELVEDATA_RATE_LIMIT=800
```

**Note**: The API key provided is: `d2b5d7d0f6524b5aad12e3b680e60`

### 2. Installation

Install the required package:

```bash
cd backend
pip install twelvedata>=1.2.25
# Or if using venv:
source venv/bin/activate  # On macOS/Linux
pip install twelvedata>=1.2.25
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Service Manager

The Twelve Data service manager is located at `backend/services/twelvedata_service.py` and follows the same pattern as other service managers (e.g., `freddy_ai_service.py`).

### Features

- **Time Series Data**: Fetch OHLCV candle data
- **Technical Indicators**: Get MACD, RSI, Bollinger Bands, Stochastic, EMA
- **WebSocket Support**: Real-time data streaming
- **Caching**: Redis-based caching with TTL
- **Symbol Conversion**: Automatic conversion between Yahoo Finance format (TCS.NS) and Twelve Data format (TCS)
- **Error Handling**: Comprehensive error handling and logging

## Usage Examples

### Basic Usage

```python
from backend.services.twelvedata_service import twelvedata_service
import asyncio

async def fetch_data():
    # Fetch time series data
    candles = await twelvedata_service.fetch_time_series(
        symbol="TCS.NS",
        interval="5m",
        outputsize=100,
        use_cache=True
    )
    
    if candles:
        print(f"Retrieved {len(candles)} candles")
        print(f"Latest candle: {candles[-1]}")

asyncio.run(fetch_data())
```

### Fetch with Technical Indicators

```python
# Fetch data with indicators
result = await twelvedata_service.fetch_with_indicators(
    symbol="TCS.NS",
    interval="5m",
    outputsize=100,
    indicators=['macd', 'rsi', 'bbands']
)
```

### WebSocket Real-time Streaming

```python
def on_event(event):
    print(f"Received event: {event}")

# Create WebSocket client
ws = twelvedata_service.get_websocket_client(
    symbols=["TCS.NS", "RELIANCE.BO"],
    on_event=on_event
)

if ws:
    ws.connect()
    # Keep connection alive
    while True:
        ws.heartbeat()
        time.sleep(10)
```

## Symbol Format Conversion

The service automatically converts symbols:
- `TCS.NS` → `TCS` (NSE stocks)
- `RELIANCE.BO` → `BSE:RELIANCE` (BSE stocks)

## Interval Format Conversion

Intervals are automatically converted:
- `1m` → `1min`
- `5m` → `5min`
- `15m` → `15min`
- `1h` → `1hour`
- `1d` → `1day`
- `1wk` → `1week`
- `1mo` → `1month`

## Testing

Run the test script to verify the integration:

```bash
cd backend
python test_twelvedata.py
```

This will:
1. Check configuration
2. Test symbol conversion
3. Test interval conversion
4. Make an actual API call

## Integration with Existing Data Fetcher

The service can be used alongside or as an alternative to the existing Yahoo Finance data fetcher (`backend/utils/data_fetcher.py`). You can:

1. **Use as fallback**: If Yahoo Finance fails, try Twelve Data
2. **Use for specific features**: Use Twelve Data for technical indicators
3. **Use for real-time**: Use WebSocket for live data streaming

## Rate Limits

- **Free Tier**: 800 requests per day
- **Paid Tiers**: Higher limits available

The service includes rate limiting configuration via `TWELVEDATA_RATE_LIMIT` in the config.

## Caching

- **Hot Cache**: Redis-based caching (5 minutes TTL by default)
- **Cache Keys**: Format: `twelvedata:{symbol}:{interval}:{outputsize}`
- **Cache TTL**: Configurable via `TWELVEDATA_CACHE_TTL`

## API Documentation

For full API documentation, refer to:
- [Twelve Data Python Client](https://github.com/twelvedata/twelvedata-python)
- [Twelve Data API Docs](https://twelvedata.com/docs)

## Files Modified/Created

1. **backend/config.py**: Added Twelve Data configuration settings
2. **backend/services/twelvedata_service.py**: Created service manager
3. **backend/requirements.txt**: Added `twelvedata>=3.0.0`
4. **backend/test_twelvedata.py**: Created test script
5. **.env.example**: Created example environment file

## Next Steps

1. **Create `.env` file**: Copy `.env.example` and add your API key
2. **Install dependencies**: Run `pip install -r requirements.txt`
3. **Test integration**: Run `python backend/test_twelvedata.py`
4. **Integrate with data fetcher**: Optionally add Twelve Data as fallback provider

## Support

For issues or questions:
- Check logs in `logs/backend.log`
- Run the test script to diagnose issues
- Refer to Twelve Data API documentation


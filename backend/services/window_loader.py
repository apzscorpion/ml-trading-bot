"""
Window loader configuration constants.
Legacy file for backward compatibility.
"""

# Timeframe to minutes mapping
TIMEFRAME_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 390,  # Trading day ~6.5 hours
    "1wk": 2730,  # ~7 days
    "1mo": 11700  # ~30 days
}

# Default window days for historical data
WINDOW_DAYS = {
    "1m": 5,
    "5m": 60,
    "15m": 60,
    "30m": 90,
    "1h": 730,
    "4h": 730,
    "1d": 2000,
    "1wk": 3650,
    "1mo": 3650
}


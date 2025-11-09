"""
Historical data endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging

import pandas as pd
import pytz

from backend.database import get_db, Candle
from backend.utils.data_fetcher import data_fetcher
from backend.utils.exchange_calendar import exchange_calendar
from backend.data_pipeline import FeatureStore
from backend.services.window_loader import (
    TIMEFRAME_MINUTES as _TA_TIMEFRAME_MINUTES,
    WINDOW_DAYS as _TA_WINDOW_DAYS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])

_feature_store = FeatureStore()


def normalize_datetime(dt):
    """
    Normalize datetime to timezone-aware (UTC) if it's naive.
    """
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        return dt.replace(tzinfo=pytz.UTC)
    return dt


@router.get("")
async def get_history(
    symbol: str = Query(..., description="Stock symbol (e.g., TCS.NS)"),
    timeframe: str = Query("5m", description="Timeframe (1m, 5m, 15m, 1h)"),
    from_ts: Optional[str] = Query(None, description="Load data BEFORE this timestamp (for pagination)"),
    to_ts: Optional[str] = Query(None, description="Load data AFTER this timestamp (for incremental updates)"),
    limit: int = Query(500, description="Max number of candles to return"),
    bypass_cache: bool = Query(False, description="Bypass cache and fetch fresh data"),
    db: Session = Depends(get_db)
):
    """
    Get historical candle data.
    First checks database, then fetches from Yahoo Finance if needed.
    
    - If from_ts is provided, it loads data BEFORE that timestamp (for loading older data).
    - If to_ts is provided, it loads data AFTER that timestamp (for incremental updates).
    """
    query = db.query(Candle).filter(
        Candle.symbol == symbol,
        Candle.timeframe == timeframe
    )
    
    # CRITICAL: Filter out future dates - never show data from the future
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist)
    query = query.filter(Candle.start_ts <= current_time + timedelta(hours=1))
    
    is_ta_mode = not from_ts and not to_ts

    timeframe_minutes = _TA_TIMEFRAME_MINUTES.get(timeframe, 5)
    target_window_days = _TA_WINDOW_DAYS.get(timeframe, 90)
    target_window_minutes = target_window_days * 24 * 60
    target_records = max(1, target_window_minutes // max(1, timeframe_minutes))

    if is_ta_mode:
        limit = max(limit, target_records)

    if from_ts:
        # Load data BEFORE this timestamp (for pagination/loading older data)
        from_dt = datetime.fromisoformat(from_ts.replace('Z', '+00:00'))
        from_dt = normalize_datetime(from_dt)
        query = query.filter(Candle.start_ts < from_dt)
    
    if to_ts:
        # Load data AFTER this timestamp (for incremental updates/new data)
        to_dt = datetime.fromisoformat(to_ts.replace('Z', '+00:00'))
        to_dt = normalize_datetime(to_dt)
        query = query.filter(Candle.start_ts > to_dt)
    
    # CRITICAL: When no filters provided, get MOST RECENT candles (desc), then reverse
    # When filtering, get in ascending order for proper pagination
    if from_ts or to_ts:
        query = query.order_by(Candle.start_ts.asc()).limit(limit)
    else:
        # Get most recent candles first, then we'll reverse them
        query = query.order_by(Candle.start_ts.desc()).limit(limit)
    
    candles = query.all()
    
    # If we got descending order (no filters), reverse to chronological
    if is_ta_mode:
        candles = list(reversed(candles))
    
    # CRITICAL: Filter out non-trading days (holidays, weekends) from database results
    filtered_candles = []
    for candle in candles:
        candle_date = candle.start_ts.date()
        if exchange_calendar.is_trading_day(candle_date):
            # For intraday timeframes, also check trading hours
            if timeframe in ['1m', '5m', '15m', '1h', '4h']:
                if exchange_calendar.is_market_open(candle.start_ts):
                    filtered_candles.append(candle)
            else:
                # For daily/weekly/monthly, just check trading day
                filtered_candles.append(candle)
        else:
            logger.debug(f"Filtered out non-trading day candle from DB: {candle.start_ts.isoformat()} (date: {candle_date.isoformat()})")
    
    candles = filtered_candles

    if is_ta_mode and candles:
        window_start_utc = (current_time - timedelta(days=target_window_days)).astimezone(pytz.UTC)
        candles = [
            candle
            for candle in candles
            if normalize_datetime(candle.start_ts) >= window_start_utc
        ]
    
    # Check if we need to fetch from Yahoo Finance
    should_fetch_from_yahoo = False
    # Use bypass_cache from query parameter if provided
    if bypass_cache:
        should_fetch_from_yahoo = True
        logger.info(f"bypass_cache=true, forcing fresh fetch from Yahoo Finance")
    
    # Check if to_ts is recent (within last 24 hours) - always bypass cache for recent data
    if to_ts:
        to_dt = datetime.fromisoformat(to_ts.replace('Z', '+00:00'))
        to_dt = normalize_datetime(to_dt)
        now = datetime.now(pytz.UTC)
        time_diff = now - to_dt
        
        # If to_ts is within last 24 hours, bypass cache to get fresh data
        if time_diff < timedelta(hours=24):
            bypass_cache = True
            logger.info(f"to_ts is recent (within 24h), bypassing cache for fresh data")
    
    # Always fetch fresh from Yahoo Finance when from_ts or to_ts is provided (scrolling)
    # This ensures we get the latest data and don't rely on cache
    if from_ts or to_ts:
        should_fetch_from_yahoo = True
    elif not candles:
        # No data in DB, fetch from Yahoo Finance
        should_fetch_from_yahoo = True
    elif len(candles) < limit:
        # We don't have enough candles, fetch from Yahoo Finance
        should_fetch_from_yahoo = True
    
    # Also check if latest candle in DB is stale (older than 1 hour for recent data)
    if not should_fetch_from_yahoo and candles:
        latest_candle = candles[-1]
        now = datetime.now(pytz.UTC)
        latest_ts = normalize_datetime(latest_candle.start_ts)
        time_diff = now - latest_ts
        
        # If latest candle is older than 1 hour, fetch fresh data
        if time_diff > timedelta(hours=1):
            should_fetch_from_yahoo = True
            bypass_cache = True
            logger.info(f"Latest candle is stale (older than 1h), fetching fresh data")
    
    if should_fetch_from_yahoo:
        # SIMPLIFIED: Use fixed, predictable periods based ONLY on timeframe
        # This ensures consistent data on every refresh
        # No dynamic calculation - predictable behavior
        period_map = {
            "1m": "7d",      # Max available for 1m (Yahoo limit)
            "5m": "60d",     # Max available for 5m (Yahoo limit)
            "15m": "60d",    # Max available for 15m (Yahoo limit)
            "1h": "730d",    # Max available for 1h (Yahoo limit: 730 days = 2 years)
            "4h": "730d",    # Max available for 4h
            "1d": "2y",      # 2 years of daily data
            "5d": "2y",      # 2 years 
            "1wk": "5y",     # 5 years
            "1mo": "10y",    # 10 years
            "3mo": "10y"     # 10 years
        }
        
        # Use fixed period for predictable results
        period = period_map.get(timeframe, "60d")
        
        # CRITICAL: Always bypass cache when:
        # 1. Frontend explicitly requests it (bypass_cache=true)
        # 2. Fetching incremental updates (from_ts or to_ts provided)
        should_bypass = bypass_cache or bool(from_ts or to_ts)
        
        logger.info(
            f"Fetching from Yahoo Finance: {symbol}/{timeframe} "
            f"(period={period}, bypass_cache={should_bypass}, "
            f"from_ts={from_ts}, to_ts={to_ts})"
        )
        
        fetched_candles = await data_fetcher.fetch_candles(
            symbol=symbol,
            interval=timeframe,
            period=period,
            bypass_cache=should_bypass
        )
        
        logger.info(
            f"✅ Fetched {len(fetched_candles)} candles from Yahoo Finance "
            f"for {symbol}/{timeframe} (period={period})"
        )
        
        # Filter fetched candles based on parameters
        filtered_candles = []
        for candle_data in fetched_candles:
            candle_ts_str = candle_data.get('start_ts')
            if candle_ts_str:
                if isinstance(candle_ts_str, str):
                    candle_ts = datetime.fromisoformat(candle_ts_str.replace('Z', '+00:00'))
                else:
                    candle_ts = candle_ts_str
                
                # Normalize timezone
                candle_ts = normalize_datetime(candle_ts)
                
                # Filter based on from_ts (load BEFORE) or to_ts (load AFTER)
                if from_ts:
                    from_dt = datetime.fromisoformat(from_ts.replace('Z', '+00:00'))
                    from_dt = normalize_datetime(from_dt)
                    if candle_ts < from_dt:
                        filtered_candles.append(candle_data)
                elif to_ts:
                    to_dt = datetime.fromisoformat(to_ts.replace('Z', '+00:00'))
                    to_dt = normalize_datetime(to_dt)
                    if candle_ts > to_dt:
                        filtered_candles.append(candle_data)
                else:
                    # No filter, include all
                    filtered_candles.append(candle_data)
            else:
                # Include candles without timestamp (shouldn't happen, but be safe)
                filtered_candles.append(candle_data)
        
        fetched_candles = filtered_candles
        
        if is_ta_mode and fetched_candles:
            window_start_iso = (current_time - timedelta(days=target_window_days)).astimezone(pytz.UTC)
            pruned = []
            for candle_data in fetched_candles:
                candle_ts_str = candle_data.get("start_ts")
                if not candle_ts_str:
                    continue
                try:
                    candle_ts = datetime.fromisoformat(candle_ts_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    continue
                if candle_ts >= window_start_iso:
                    pruned.append(candle_data)
            fetched_candles = pruned

        logger.info(f"After filtering: {len(fetched_candles)} candles remain (from_ts={from_ts}, to_ts={to_ts})")
        
        # Store in database (only if not already exists)
        existing_timestamps = set()
        if candles:
            existing_timestamps = {c.start_ts for c in candles}
        
        new_candles_to_store = []
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)
        
        for candle_data in fetched_candles:
            # CRITICAL: Validate timestamp before storing
            candle_ts_str = candle_data.get('start_ts')
            if not candle_ts_str:
                logger.warning(f"Skipping candle without timestamp: {candle_data}")
                continue
            
            try:
                if isinstance(candle_ts_str, str):
                    candle_ts = datetime.fromisoformat(candle_ts_str.replace('Z', '+00:00'))
                else:
                    candle_ts = candle_ts_str
                
                # Normalize timezone
                candle_ts = normalize_datetime(candle_ts)
                
                # CRITICAL: Skip future dates
                if candle_ts > current_time + timedelta(hours=1):
                    logger.warning(f"Skipping future-dated candle from DB storage: {candle_ts.isoformat()}")
                    continue
                
                # CRITICAL: Skip non-trading days (holidays, weekends)
                candle_date = candle_ts.date()
                if not exchange_calendar.is_trading_day(candle_date):
                    logger.debug(f"Skipping non-trading day candle from DB storage: {candle_ts.isoformat()} (date: {candle_date.isoformat()})")
                    continue
                
                # CRITICAL: For intraday timeframes, skip data outside trading hours
                if timeframe in ['1m', '5m', '15m', '1h', '4h']:
                    if not exchange_calendar.is_market_open(candle_ts):
                        logger.debug(f"Skipping candle outside trading hours from DB storage: {candle_ts.isoformat()}")
                        continue
                
                # Skip if already exists
                if candle_ts in existing_timestamps:
                    continue
                
                candle_dict = candle_data.copy()
                candle_dict['start_ts'] = candle_ts
                candle = Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    **candle_dict
                )
                db.add(candle)
                new_candles_to_store.append(candle_data)
                existing_timestamps.add(candle_ts)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Skipping candle with invalid timestamp {candle_ts_str}: {e}")
                continue
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            # Duplicate entries are OK, just continue
        
        # Merge fetched candles with DB candles if we had some
        if candles:
            # Get updated query from DB after storing new candles
            query = db.query(Candle).filter(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe
            )
            
            if from_ts:
                from_dt = datetime.fromisoformat(from_ts.replace('Z', '+00:00'))
                from_dt = normalize_datetime(from_dt)
                query = query.filter(Candle.start_ts < from_dt)
            
            if to_ts:
                to_dt = datetime.fromisoformat(to_ts.replace('Z', '+00:00'))
                to_dt = normalize_datetime(to_dt)
                query = query.filter(Candle.start_ts > to_dt)
            
            # CRITICAL: Get most recent candles, then reverse for chronological order
            if from_ts or to_ts:
                query = query.order_by(Candle.start_ts.asc()).limit(limit)
            else:
                query = query.order_by(Candle.start_ts.desc()).limit(limit)
            candles = query.all()
            
            # Reverse if we got descending order (no filters)
            if not from_ts and not to_ts:
                candles = list(reversed(candles))
            
            # CRITICAL: Filter out non-trading days from merged results
            filtered_candles = []
            for candle in candles:
                candle_date = candle.start_ts.date()
                if exchange_calendar.is_trading_day(candle_date):
                    # For intraday timeframes, also check trading hours
                    if timeframe in ['1m', '5m', '15m', '1h', '4h']:
                        if exchange_calendar.is_market_open(candle.start_ts):
                            filtered_candles.append(candle)
                    else:
                        filtered_candles.append(candle)

            if is_ta_mode and filtered_candles:
                window_start_utc = (current_time - timedelta(days=target_window_days)).astimezone(pytz.UTC)
                filtered_candles = [
                    candle
                    for candle in filtered_candles
                    if normalize_datetime(candle.start_ts) >= window_start_utc
                ]

            candles_list = [c.to_dict() for c in filtered_candles]  # Already sorted ascending
            logger.info(f"Returning {len(candles_list)} candles (merged DB + Yahoo Finance)")
            return candles_list
        else:
            # No candles in DB originally, return fetched candles
            # Sort by start_ts ascending (oldest first)
            fetched_candles.sort(key=lambda x: datetime.fromisoformat(x.get('start_ts', '').replace('Z', '+00:00')) if isinstance(x.get('start_ts'), str) else x.get('start_ts', datetime.min))
            if is_ta_mode:
                window_start_iso = (current_time - timedelta(days=target_window_days)).astimezone(pytz.UTC)
                fetched_candles = [
                    c for c in fetched_candles
                    if 'start_ts' in c and datetime.fromisoformat(c['start_ts'].replace('Z', '+00:00')) >= window_start_iso
                ]
            result = fetched_candles[:limit]
            logger.info(f"Returning {len(result)} candles (from Yahoo Finance, no DB data)")
            return result
    
    # Return from DB (when we have enough data and don't need to fetch from Yahoo)
    # Sort ascending (oldest first) for chronological order
    # CRITICAL: Filter out non-trading days before returning
    filtered_candles = []
    for candle in candles:
        candle_date = candle.start_ts.date()
        if exchange_calendar.is_trading_day(candle_date):
            # For intraday timeframes, also check trading hours
            if timeframe in ['1m', '5m', '15m', '1h', '4h']:
                if exchange_calendar.is_market_open(candle.start_ts):
                    filtered_candles.append(candle)
            else:
                filtered_candles.append(candle)
    
    if is_ta_mode and filtered_candles:
        window_start_utc = (current_time - timedelta(days=target_window_days)).astimezone(pytz.UTC)
        filtered_candles = [
            candle
            for candle in filtered_candles
            if normalize_datetime(candle.start_ts) >= window_start_utc
        ]

    candles_list = [c.to_dict() for c in filtered_candles]  # Already sorted ascending from query

    if is_ta_mode:
        # If DB still lacks enough history, fall back to feature store window
        if len(candles_list) < target_records:
            fs_df = _feature_store.load_time_window(
                symbol=symbol,
                timeframe=timeframe,
                window_minutes=target_window_minutes,
            )
            if fs_df is not None and not fs_df.empty:
                fs_df = fs_df.sort_values("start_ts")
                if not pd.api.types.is_datetime64tz_dtype(fs_df["start_ts"]):
                    fs_df["start_ts"] = pd.to_datetime(fs_df["start_ts"], utc=True)
                    fs_df["start_ts"] = fs_df["start_ts"].dt.tz_convert(ist)
                window_start_ist = current_time - timedelta(days=target_window_days)
                fs_df = fs_df[fs_df["start_ts"] >= window_start_ist]
                if not fs_df.empty:
                    candles_list = fs_df[["start_ts", "open", "high", "low", "close", "volume"]].to_dict("records")
                    logger.info(
                        "Feature store backfill activated for %s/%s: %s rows",
                        symbol,
                        timeframe,
                        len(candles_list),
                    )

    logger.info(f"Returning {len(candles_list)} candles (from DB only)")
    return candles_list


@router.get("/latest")
async def get_latest_candle(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    db: Session = Depends(get_db)
):
    """Get the latest candle for a symbol"""
    candle = db.query(Candle).filter(
        Candle.symbol == symbol,
        Candle.timeframe == timeframe
    ).order_by(Candle.start_ts.desc()).first()
    
    if not candle:
        # Fetch from Yahoo Finance
        fetched = await data_fetcher.fetch_candles(symbol, timeframe, "1d")
        if fetched:
            return fetched[-1]
        return {"error": "No data available"}
    
    return candle.to_dict()


@router.get("/symbols")
async def get_available_symbols():
    """Get list of available Indian stock symbols"""
    return {
        "symbols": data_fetcher.get_indian_stock_symbols()
    }


"""
Market status and exchange calendar endpoints.
"""
from fastapi import APIRouter, Query
from datetime import datetime, date, timedelta
from typing import Optional
import pytz
from backend.utils.exchange_calendar import exchange_calendar

router = APIRouter(prefix="/market-status", tags=["market-status"])


@router.get("/is-open")
async def is_market_open():
    """
    Check if market is currently open.
    
    Returns:
        Market status information
    """
    ist = pytz.timezone('Asia/Kolkata')
    current_ist = datetime.now(ist)
    
    status = exchange_calendar.validate_trading_session(current_ist)
    
    return {
        "is_market_open": status["is_market_open"],
        "reason": status["reason"],
        "current_time_ist": current_ist.isoformat(),
        "market_open": status["market_open"],
        "market_close": status["market_close"],
        "next_trading_day": status.get("next_trading_day"),
        "session_type": status.get("session_type", "regular")
    }


@router.get("/calendar")
async def get_calendar(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    days: int = Query(30, description="Number of days from today if dates not provided")
):
    """
    Get trading calendar for date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        days: Number of days from today if dates not provided
    
    Returns:
        Trading calendar information
    """
    if start_date and end_date:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    else:
        today = date.today()
        start = today
        end = today + timedelta(days=days)
    
    calendar = exchange_calendar.get_trading_calendar(start, end)
    
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "trading_days": calendar,
        "total_days": len(calendar),
        "trading_days_count": sum(1 for d in calendar if d["is_trading_day"])
    }


@router.get("/next-trading-day")
async def get_next_trading_day(
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD), defaults to today"),
    days_ahead: int = Query(1, description="Number of trading days ahead")
):
    """
    Get the next trading day N days ahead.
    
    Args:
        from_date: From date (YYYY-MM-DD)
        days_ahead: Number of trading days ahead
    
    Returns:
        Next trading day information
    """
    if from_date:
        from_dt = date.fromisoformat(from_date)
    else:
        from_dt = date.today()
    
    next_day = exchange_calendar.get_next_trading_day(from_dt, days_ahead)
    
    return {
        "from_date": from_dt.isoformat(),
        "days_ahead": days_ahead,
        "next_trading_day": next_day.isoformat(),
        "day_of_week": next_day.strftime("%A")
    }


@router.get("/validate")
async def validate_trading_session(
    check_datetime: Optional[str] = Query(None, description="Datetime to check (ISO format), defaults to now")
):
    """
    Validate trading session for a specific datetime.
    
    Args:
        check_datetime: Datetime to check (ISO format)
    
    Returns:
        Detailed trading session status
    """
    if check_datetime:
        check_dt = datetime.fromisoformat(check_datetime.replace('Z', '+00:00'))
    else:
        ist = pytz.timezone('Asia/Kolkata')
        check_dt = datetime.now(ist)
    
    status = exchange_calendar.validate_trading_session(check_dt)
    
    return status


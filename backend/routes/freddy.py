"""Freddy AI bridge endpoints."""

from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import Candle, get_db
from backend.services.freddy_ai_service import freddy_ai_service
from backend.utils.data_fetcher import data_fetcher
from backend.utils.indicators import calculate_all_indicators, get_latest_indicators
from backend.utils.logger import get_logger


logger = get_logger(__name__)


router = APIRouter(prefix="/api/freddy", tags=["freddy"])


class FreddyPromptRequest(BaseModel):
    """Request payload for custom Freddy AI prompt."""

    symbol: str = Field(..., description="Stock symbol in NSE/BSE format, e.g. INFY.NS")
    timeframe: str = Field("5m", description="Active timeframe (e.g., 5m, 15m, 1h)")
    prompt: Optional[str] = Field(None, description="Override default Freddy prompt")
    use_cache: bool = Field(True, description="Reuse recent Freddy responses when possible")
    lookback_minutes: int = Field(
        1440,
        ge=60,
        le=7 * 24 * 60,
        description="Window (in minutes) for contextual stats and news focus"
    )


class FreddyPromptResponse(BaseModel):
    """Standard response wrapper for frontend consumption."""

    symbol: str
    timeframe: str
    prompt: str
    context: Dict[str, Optional[float]]
    indicators: Dict[str, Optional[float]]
    analysis: Dict


async def _load_candles(
    db: Session,
    symbol: str,
    timeframe: str,
    limit: int = 500
):
    """Fetch candles from DB or fallback to remote source."""

    candles_query = db.query(Candle).filter(
        Candle.symbol == symbol,
        Candle.timeframe == timeframe
    ).order_by(Candle.start_ts.desc()).limit(limit).all()

    candles = [c.to_dict() for c in candles_query]
    if candles:
        candles.reverse()  # chronological order ascending
        return candles

    logger.info("No cached candles for %s/%s, fetching from data source", symbol, timeframe)
    remote = await data_fetcher.fetch_candles(
        symbol=symbol,
        interval=timeframe,
        period="5d" if timeframe in {"1m", "5m", "15m"} else "60d"
    )
    if remote:
        return remote

    raise HTTPException(status_code=404, detail=f"No candle data available for {symbol}")


def _build_context(
    candles: Dict,
    lookback_minutes: int,
    indicators: Dict[str, Optional[float]]
) -> Dict[str, Optional[float]]:
    """Assemble real-time context dictionary for Freddy prompts."""

    if not candles:
        return {}

    latest = candles[-1]
    latest_time = latest.get("start_ts")
    if isinstance(latest_time, datetime):
        latest_dt = latest_time
    else:
        latest_dt = datetime.fromisoformat(str(latest_time).replace("Z", "+00:00"))

    cutoff = latest_dt - timedelta(minutes=lookback_minutes)

    lookback_candles = [
        c for c in candles
        if datetime.fromisoformat(str(c.get("start_ts")).replace("Z", "+00:00")) >= cutoff
    ] or candles[-min(len(candles), 50):]

    first = lookback_candles[0]

    open_price = float(first.get("open", latest.get("open"))) if first else None
    close_price = float(latest.get("close")) if latest.get("close") is not None else None
    high_price = max(float(c.get("high")) for c in lookback_candles if c.get("high") is not None)
    low_price = min(float(c.get("low")) for c in lookback_candles if c.get("low") is not None)

    price_change = None
    price_change_pct = None
    if open_price is not None and close_price is not None and open_price != 0:
        price_change = close_price - open_price
        price_change_pct = (price_change / open_price) * 100

    total_volume = sum(float(c.get("volume", 0) or 0) for c in lookback_candles)

    context = {
        "generated_at": datetime.utcnow().isoformat(),
        "latest_candle_time": latest_dt.isoformat(),
        "latest_close": close_price,
        "session_open": open_price,
        "session_high": high_price,
        "session_low": low_price,
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "total_volume": total_volume,
        "lookback_minutes": lookback_minutes,
        "indicator_summary": {
            key: indicators.get(key)
            for key in ["rsi_14", "macd", "macd_histogram", "sma_20", "sma_50", "atr_14", "vwap_intraday"]
            if key in indicators
        }
    }

    return context


@router.post("/analysis", response_model=FreddyPromptResponse)
async def run_custom_prompt(
    request: FreddyPromptRequest,
    db: Session = Depends(get_db)
):
    """Invoke Freddy AI with a custom user prompt and live indicator context."""

    if not freddy_ai_service.enabled:
        raise HTTPException(status_code=503, detail="Freddy AI integration is disabled")

    candles = await _load_candles(db, request.symbol, request.timeframe)

    df = calculate_all_indicators(candles)
    indicators = get_latest_indicators(df)

    current_price = None
    if candles:
        current_price = candles[-1].get("close")
        if isinstance(current_price, str):
            try:
                current_price = float(current_price)
            except ValueError:
                current_price = None

    context = _build_context(candles, request.lookback_minutes, indicators)
    prompt_template = request.prompt or (
        "Give me details of the stock using actual values. "
        "Include any impactful news or events from the past day, "
        "state whether the bias is bullish, bearish, or hold, and provide precise targets and stop loss."
    )

    analysis = await freddy_ai_service.analyze_custom_prompt(
        symbol=request.symbol,
        timeframe=request.timeframe,
        prompt=prompt_template,
        current_price=current_price,
        indicator_snapshot=indicators,
        additional_context=context,
        use_cache=request.use_cache,
        enable_web_search=True
    )

    if not analysis:
        raise HTTPException(status_code=502, detail="Freddy AI did not return a response")

    analysis_dict = analysis.dict()

    return FreddyPromptResponse(
        symbol=request.symbol,
        timeframe=request.timeframe,
        prompt=prompt_template,
        context=context,
        indicators=indicators,
        analysis=analysis_dict
    )



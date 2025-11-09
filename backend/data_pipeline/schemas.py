"""Pydantic schemas for candle ingestion."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class CandleRecord(BaseModel):
    start_ts: datetime = Field(..., description="Candle start timestamp (timezone-aware).")
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = 0.0

    @validator("high")
    def _validate_high(cls, v, values):  # pylint: disable=no-self-argument
        low = values.get("low")
        if low is not None and v < low:
            raise ValueError("high must be >= low")
        return v

    @validator("close")
    def _validate_close(cls, v, values):
        low = values.get("low")
        high = values.get("high")
        if low is not None and v < low:
            raise ValueError("close must be >= low")
        if high is not None and v > high:
            raise ValueError("close must be <= high")
        return v

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}

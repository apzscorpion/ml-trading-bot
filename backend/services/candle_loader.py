"""Utility helpers for loading candle windows from feature store or providers."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pytz

from backend.data_pipeline import FeatureStore
from backend.utils.data_fetcher import data_fetcher
from backend.utils.logger import get_logger
from backend.services.version_registry import version_registry

logger = get_logger(__name__)

IST = pytz.timezone("Asia/Kolkata")


def _normalize_timestamp(value) -> Optional[str]:
    """Convert timestamp-like values to ISO format with timezone attached."""

    if value is None:
        return None

    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, str):
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        try:
            ts = datetime.fromisoformat(str(value))
        except ValueError:
            return None

    if ts.tzinfo is None:
        ts = IST.localize(ts)

    return ts.isoformat()


class CandleLoader:
    """Centralized loader that prefers feature store, falls back to live fetch."""

    def __init__(self):
        self._feature_store = FeatureStore()

    def _df_to_candles(self, df) -> List[Dict]:
        if df is None or df.empty:
            return []

        base_cols = ["start_ts", "open", "high", "low", "close", "volume"]
        missing = [col for col in base_cols if col not in df.columns]
        for col in missing:
            df[col] = 0.0

        ordered_df = df[base_cols].sort_values("start_ts").dropna(subset=["start_ts", "close"])

        candles: List[Dict] = []
        for row in ordered_df.itertuples(index=False):
            ts_iso = _normalize_timestamp(row.start_ts)
            if not ts_iso:
                continue

            candles.append(
                {
                    "start_ts": ts_iso,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume) if row.volume is not None else 0.0,
                }
            )

        return candles

    def _sanitize_live_candles(self, candles: Optional[List[Dict]]) -> List[Dict]:
        if not candles:
            return []

        sanitized: List[Dict] = []
        seen_ts = set()
        for candle in candles:
            ts_iso = _normalize_timestamp(candle.get("start_ts"))
            if not ts_iso or ts_iso in seen_ts:
                continue

            try:
                sanitized.append(
                    {
                        "start_ts": ts_iso,
                        "open": float(candle.get("open", 0.0)),
                        "high": float(candle.get("high", 0.0)),
                        "low": float(candle.get("low", 0.0)),
                        "close": float(candle.get("close", 0.0)),
                        "volume": float(candle.get("volume", 0.0)),
                    }
                )
            except (TypeError, ValueError):
                continue

            seen_ts.add(ts_iso)

        sanitized.sort(key=lambda p: p["start_ts"])
        return sanitized

    async def load_time_window(
        self,
        symbol: str,
        timeframe: str,
        window_minutes: int,
        fallback_period: str,
        *,
        min_points: int = 1,
        bypass_cache: bool = False,
    ) -> List[Dict]:
        """Load a window of candles ending now, preferring feature store data."""

        as_of = datetime.now(pytz.UTC)
        override = version_registry.get_dataset_override(symbol, timeframe)
        dataset_version = override.get("dataset_version") if override else None
        run_id = override.get("run_id") if override else None
        df = self._feature_store.load_time_window(
            symbol=symbol,
            timeframe=timeframe,
            window_minutes=window_minutes,
            as_of=as_of,
            dataset_version=dataset_version,
            run_id=run_id,
        )

        candles = self._df_to_candles(df)
        if len(candles) >= min_points:
            return candles

        logger.info(
            "CandleLoader fetching live data",
            extra={"symbol": symbol, "timeframe": timeframe, "period": fallback_period},
        )
        live = await data_fetcher.fetch_candles(
            symbol=symbol,
            interval=timeframe,
            period=fallback_period,
            bypass_cache=bypass_cache,
        )
        return self._sanitize_live_candles(live)

    async def load_recent_rows(
        self,
        symbol: str,
        timeframe: str,
        rows: int,
        fallback_period: str,
        *,
        min_points: int = 1,
        bypass_cache: bool = False,
    ) -> List[Dict]:
        """Load latest N rows for training/predictions."""

        override = version_registry.get_dataset_override(symbol, timeframe)
        dataset_version = override.get("dataset_version") if override else None
        run_id = override.get("run_id") if override else None
        df = self._feature_store.load_features(
            symbol=symbol,
            timeframe=timeframe,
            lookback=rows,
            dataset_version=dataset_version,
            run_id=run_id,
        )
        candles = self._df_to_candles(df)
        if len(candles) >= min_points:
            return candles[-rows:]

        logger.info(
            "CandleLoader fallback to live rows",
            extra={"symbol": symbol, "timeframe": timeframe, "period": fallback_period},
        )
        live = await data_fetcher.fetch_candles(
            symbol=symbol,
            interval=timeframe,
            period=fallback_period,
            bypass_cache=bypass_cache,
        )
        sanitized = self._sanitize_live_candles(live)
        if rows > 0:
            return sanitized[-rows:]
        return sanitized


# Singleton instance
candle_loader = CandleLoader()



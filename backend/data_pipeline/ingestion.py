"""Ingestion logic that promotes raw candle data to bronze/silver datasets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import pytz

from backend.utils.exchange_calendar import exchange_calendar

from .config import DataPipelineConfig, get_config
from .schemas import CandleRecord
from .storage import ParquetStorage
from .versioning import DatasetVersion, VersionManager

_INTERVAL_MINUTES: Dict[str, int] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
    "5d": 1440,
    "1wk": 10080,
    "1mo": 43200,
    "3mo": 129600,
}


@dataclass
class DataArtifacts:
    raw_path: Path
    bronze_path: Path
    silver_path: Path
    dataset_version: str
    run_id: str
    record_count: int
    metadata: Dict[str, str]


class DataPipeline:
    """End-to-end pipeline persisting raw → bronze → silver datasets."""

    def __init__(self, config: Optional[DataPipelineConfig] = None):
        self._config = config or get_config()
        self._storage = ParquetStorage(self._config)
        self._version_mgr = VersionManager(self._config)
        self._tz = pytz.timezone(self._config.timezone)

    def ingest(
        self,
        symbol: str,
        timeframe: str,
        candles: Iterable[Dict],
        provider: Optional[str] = None,
        dataset_version: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> DataArtifacts:
        """Persist candles through raw/bronze/silver layers."""

        candles = list(candles)
        if not candles:
            raise ValueError("No candles supplied for ingestion")

        records = self._validate_records(candles)
        df_raw = self._prepare_raw(records, provider)
        version: DatasetVersion = self._version_mgr.build_version(
            symbol=symbol,
            timeframe=timeframe,
            explicit_version=dataset_version,
            run_id=run_id,
        )

        raw_path = self._storage.write(
            df_raw,
            layer="raw",
            symbol=symbol,
            timeframe=timeframe,
            dataset_version=version.namespace,
            run_id=version.run_id,
            suffix="raw",
        )

        df_bronze = self._bronze_transform(df_raw, timeframe)
        bronze_path = self._storage.write(
            df_bronze,
            layer="bronze",
            symbol=symbol,
            timeframe=timeframe,
            dataset_version=version.namespace,
            run_id=version.run_id,
            suffix="bronze",
        )

        df_silver = self._silver_transform(df_bronze)
        silver_path = self._storage.write(
            df_silver,
            layer="silver",
            symbol=symbol,
            timeframe=timeframe,
            dataset_version=version.namespace,
            run_id=version.run_id,
            suffix="silver",
        )

        metadata = {
            "symbol": symbol,
            "timeframe": timeframe,
            "provider": provider or "unknown",
            "start_ts": df_silver["start_ts"].iloc[0].isoformat() if not df_silver.empty else "",
            "end_ts": df_silver["start_ts"].iloc[-1].isoformat() if not df_silver.empty else "",
        }

        return DataArtifacts(
            raw_path=raw_path,
            bronze_path=bronze_path,
            silver_path=silver_path,
            dataset_version=version.namespace,
            run_id=version.run_id,
            record_count=len(df_silver),
            metadata=metadata,
        )

    def _validate_records(self, candles: List[Dict]) -> List[CandleRecord]:
        records: List[CandleRecord] = []
        for candle in candles:
            record = CandleRecord.parse_obj(candle)
            records.append(record)
        return records

    def _prepare_raw(self, records: List[CandleRecord], provider: Optional[str]) -> pd.DataFrame:
        df = pd.DataFrame([r.dict() for r in records])
        df["start_ts"] = pd.to_datetime(df["start_ts"], utc=True)
        df["start_ts"] = df["start_ts"].dt.tz_convert(self._tz)
        df = df.sort_values("start_ts").reset_index(drop=True)
        df["provider"] = provider or "unknown"
        df["ingested_at"] = datetime.utcnow().replace(tzinfo=pytz.UTC)
        return df

    def _bronze_transform(self, df_raw: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        df = df_raw.copy()
        df = df.drop_duplicates(subset=["start_ts"], keep="last")
        interval = _INTERVAL_MINUTES.get(timeframe, 5)
        df["end_ts"] = df["start_ts"] + pd.to_timedelta(interval, unit="m")
        df["session"] = df["start_ts"].apply(self._session_type)
        df["is_trading_day"] = df["start_ts"].apply(
            lambda ts: exchange_calendar.is_trading_day(ts.date())
        )
        df = df[df["is_trading_day"]].reset_index(drop=True)
        df["volume"] = df["volume"].fillna(0.0)
        df["start_ts"] = df["start_ts"].dt.tz_convert(self._tz)
        df["end_ts"] = df["end_ts"].dt.tz_convert(self._tz)
        return df

    def _silver_transform(self, df_bronze: pd.DataFrame) -> pd.DataFrame:
        df = df_bronze.copy()
        if df.empty:
            return df

        df["return_1"] = df["close"].pct_change()
        df["return_5"] = df["close"].pct_change(5)
        df["rolling_mean_10"] = df["close"].rolling(10, min_periods=1).mean()
        df["rolling_std_10"] = df["close"].rolling(10, min_periods=1).std().fillna(0.0)
        df["volume_ma_10"] = df["volume"].rolling(10, min_periods=1).mean()
        df["high_low_spread"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
        df["momentum_10"] = df["close"] - df["close"].shift(10)
        df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["is_gap_up"] = (df["open"] > df["close"].shift(1)).astype(int)
        df["is_gap_down"] = (df["open"] < df["close"].shift(1)).astype(int)

        # Replace inf/nan
        df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["close"])
        df = df.fillna(0.0)
        return df.reset_index(drop=True)

    def _session_type(self, ts: datetime) -> str:
        status = exchange_calendar.validate_trading_session(ts)
        if status.get("is_market_open"):
            return status.get("session_type", "regular")
        reason = status.get("reason", "closed")
        return reason

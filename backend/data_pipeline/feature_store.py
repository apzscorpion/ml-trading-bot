"""Feature store facade built on top of silver datasets."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from .config import DataPipelineConfig, get_config
from .storage import ParquetStorage


class FeatureStore:
    """Read silver-layer datasets and expose windowed feature retrieval."""

    def __init__(self, config: Optional[DataPipelineConfig] = None):
        self._config = config or get_config()
        self._storage = ParquetStorage(self._config)

    def load_features(
        self,
        symbol: str,
        timeframe: str,
        lookback: Optional[int] = None,
        dataset_version: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Return latest silver dataset, optionally truncated to lookback rows."""

        df = self._storage.read_latest(
            layer="silver",
            symbol=symbol,
            timeframe=timeframe,
            dataset_version=dataset_version,
            run_id=run_id,
        )
        if df is None:
            return None
        df = df.sort_values("start_ts")
        if lookback:
            df = df.tail(lookback)
        return df.reset_index(drop=True)

    def load_time_window(
        self,
        symbol: str,
        timeframe: str,
        window_minutes: int,
        as_of: Optional[datetime] = None,
        dataset_version: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Slice by time window ending at as_of (default now)."""

        df = self.load_features(
            symbol,
            timeframe,
            dataset_version=dataset_version,
            run_id=run_id,
        )
        if df is None:
            return None
        as_of = as_of or datetime.utcnow()
        window_start = as_of - timedelta(minutes=window_minutes)
        mask = (pd.to_datetime(df["start_ts"]) >= window_start) & (
            pd.to_datetime(df["start_ts"]) <= as_of
        )
        sliced = df.loc[mask]
        if sliced.empty:
            return None
        return sliced.reset_index(drop=True)

"""Parquet storage helpers for the data pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import pandas as pd

from .config import DataPipelineConfig


@dataclass(frozen=True)
class StoragePaths:
    base_dir: Path
    dataset_version: str
    symbol: str
    timeframe: str
    run_id: str
    layer: str

    def filepath(self, suffix: str) -> Path:
        filename = f"{self.symbol}_{self.timeframe}_{self.run_id}_{suffix}.parquet"
        return self.base_dir / self.dataset_version / self.symbol / self.timeframe / filename


class ParquetStorage:
    """Persist DataFrames to versioned Parquet paths."""

    def __init__(self, config: DataPipelineConfig):
        self._config = config

    def _ensure_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        df: pd.DataFrame,
        layer: str,
        symbol: str,
        timeframe: str,
        dataset_version: str,
        run_id: Optional[str] = None,
        suffix: str = "data",
    ) -> Path:
        timestamp = run_id or datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        base_dir = self._layer_root(layer)
        paths = StoragePaths(
            base_dir=base_dir,
            dataset_version=dataset_version,
            symbol=symbol.replace(".", "_"),
            timeframe=timeframe,
            run_id=timestamp,
            layer=layer,
        )
        filepath = paths.filepath(suffix)
        self._ensure_dir(filepath)
        df.to_parquet(filepath, index=False)
        return filepath

    def read_latest(
        self,
        layer: str,
        symbol: str,
        timeframe: str,
        dataset_version: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        base_dir = self._layer_root(layer)
        dataset = dataset_version or self._config.dataset_namespace
        target_dir = base_dir / dataset / symbol.replace(".", "_") / timeframe
        if not target_dir.exists():
            return None
        parquet_files = sorted(target_dir.glob("*.parquet"))
        if not parquet_files:
            return None
        if run_id:
            for path in reversed(parquet_files):
                if run_id in path.name:
                    return pd.read_parquet(path)
            return None
        return pd.read_parquet(parquet_files[-1])

    def list_runs(
        self,
        layer: str,
        symbol: str,
        timeframe: str,
        dataset_version: Optional[str] = None,
    ) -> List[str]:
        base_dir = self._layer_root(layer)
        dataset = dataset_version or self._config.dataset_namespace
        target_dir = base_dir / dataset / symbol.replace(".", "_") / timeframe
        if not target_dir.exists():
            return []
        runs: List[str] = []
        for path in sorted(target_dir.glob("*.parquet")):
            stem_parts = path.stem.split("_")
            if len(stem_parts) >= 3:
                runs.append(stem_parts[-2])  # run_id position
        return runs

    def _layer_root(self, layer: str) -> Path:
        layer = layer.lower()
        if layer == "raw":
            return self._config.raw_root
        if layer == "bronze":
            return self._config.bronze_root
        if layer == "silver":
            return self._config.silver_root
        raise ValueError(f"Unsupported layer '{layer}'")

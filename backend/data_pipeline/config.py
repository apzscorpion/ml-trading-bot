"""Configuration helpers for the data pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.config import settings


def _resolve_data_root(data_root: Optional[str]) -> Path:
    base = Path(data_root or settings.data_root or "data")
    return base.expanduser().resolve()


@dataclass(frozen=True)
class DataPipelineConfig:
    """Runtime configuration for the data pipeline."""

    data_root: Path
    timezone: str = "Asia/Kolkata"
    dataset_namespace: str = settings.dataset_version or "v1"

    @property
    def raw_root(self) -> Path:
        return self.data_root / "raw"

    @property
    def bronze_root(self) -> Path:
        return self.data_root / "bronze"

    @property
    def silver_root(self) -> Path:
        return self.data_root / "silver"


def get_config(data_root: Optional[str] = None) -> DataPipelineConfig:
    """Factory returning a configuration object, optionally overriding data root."""

    resolved = _resolve_data_root(data_root)
    return DataPipelineConfig(data_root=resolved)

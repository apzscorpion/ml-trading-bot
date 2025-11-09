"""Dataset version helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .config import DataPipelineConfig


@dataclass
class DatasetVersion:
    namespace: str
    symbol: str
    timeframe: str
    run_id: str

    @property
    def version_string(self) -> str:
        return f"{self.namespace}-{self.symbol}-{self.timeframe}-{self.run_id}"


class VersionManager:
    """Generate version identifiers for dataset artifacts."""

    def __init__(self, config: DataPipelineConfig):
        self._config = config

    def build_version(
        self,
        symbol: str,
        timeframe: str,
        explicit_version: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> DatasetVersion:
        namespace = explicit_version or self._config.dataset_namespace
        run_id = run_id or datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        safe_symbol = symbol.replace(".", "_")
        return DatasetVersion(
            namespace=namespace,
            symbol=safe_symbol,
            timeframe=timeframe,
            run_id=run_id,
        )

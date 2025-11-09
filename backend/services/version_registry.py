"""Simple registry for active dataset/model versions with rollback support."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from backend.data_pipeline.config import get_config, DataPipelineConfig
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class VersionRegistry:
    def __init__(self, config: Optional[DataPipelineConfig] = None) -> None:
        self._config = config or get_config()
        self._registry_path = self._config.data_root / "registry.json"
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict:
        if self._registry_path.exists():
            try:
                return json.loads(self._registry_path.read_text())
            except json.JSONDecodeError:
                logger.warning("Registry file corrupted, recreating", path=str(self._registry_path))
        return {"datasets": {}, "models": {}}

    def _persist(self) -> None:
        self._registry_path.write_text(json.dumps(self._data, indent=2, sort_keys=True))

    def get_dataset_override(self, symbol: str, timeframe: str) -> Optional[Dict[str, str]]:
        key = self._dataset_key(symbol, timeframe)
        return self._data.get("datasets", {}).get(key)

    def set_dataset_override(
        self,
        symbol: str,
        timeframe: str,
        dataset_version: str,
        run_id: str,
    ) -> None:
        key = self._dataset_key(symbol, timeframe)
        self._data.setdefault("datasets", {})[key] = {
            "dataset_version": dataset_version,
            "run_id": run_id,
        }
        self._persist()

    def clear_dataset_override(self, symbol: str, timeframe: str) -> None:
        key = self._dataset_key(symbol, timeframe)
        datasets = self._data.get("datasets", {})
        if key in datasets:
            datasets.pop(key)
            self._persist()

    def list_dataset_overrides(self) -> Dict[str, Dict[str, str]]:
        return self._data.get("datasets", {})

    def _dataset_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}:{timeframe}"


version_registry = VersionRegistry()



"""Experiment registry storing metrics and artifacts on disk."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ExperimentRecord:
    experiment_id: str
    symbol: str
    timeframe: str
    families: List[str]
    metrics: Dict[str, float]
    artifacts: Dict[str, str]
    created_at: datetime

    def to_dict(self) -> Dict:
        return {
            "experiment_id": self.experiment_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "families": self.families,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
            "created_at": self.created_at.isoformat(),
        }


class ExperimentRegistry:
    """Simple JSON-based experiment registry."""

    def __init__(self, root: Path):
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def log(self, record: ExperimentRecord) -> Path:
        path = self._root / f"{record.experiment_id}.json"
        with path.open("w", encoding="utf-8") as fp:
            json.dump(record.to_dict(), fp, indent=2)
        return path

    def list(self) -> List[ExperimentRecord]:
        records: List[ExperimentRecord] = []
        for file in sorted(self._root.glob("*.json")):
            with file.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            records.append(
                ExperimentRecord(
                    experiment_id=data["experiment_id"],
                    symbol=data["symbol"],
                    timeframe=data["timeframe"],
                    families=data["families"],
                    metrics=data["metrics"],
                    artifacts=data.get("artifacts", {}),
                    created_at=datetime.fromisoformat(data["created_at"]),
                )
            )
        return records

    def find_best(self, symbol: str, timeframe: str) -> Optional[ExperimentRecord]:
        best_record: Optional[ExperimentRecord] = None
        best_rmse: float = float("inf")
        for record in self.list():
            if record.symbol != symbol or record.timeframe != timeframe:
                continue
            for metrics in record.metrics.values():
                rmse = metrics.get("rmse")
                if rmse is not None and rmse < best_rmse:
                    best_rmse = rmse
                    best_record = record
        return best_record

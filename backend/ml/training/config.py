"""Configuration for training orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from backend.config import settings
from backend.data_pipeline.config import get_config as get_data_config


@dataclass(frozen=True)
class TrainingConfig:
    data_root: Path
    experiments_root: Path
    models: Dict[str, Dict]
    default_families: List[str] = field(
        default_factory=lambda: [
            "baseline",
            "random_forest",
            "gradient_boosting",
            "quantile",
        ]
    )
    walk_forward_splits: int = 5
    forecast_horizon: int = 12
    min_rows: int = 200


def get_config(
    experiments_root: Optional[str] = None,
    data_root: Optional[str] = None,
) -> TrainingConfig:
    data_cfg = get_data_config(data_root)
    experiments_path = (
        Path(experiments_root).expanduser().resolve()
        if experiments_root
        else (data_cfg.data_root / "experiments")
    )
    experiments_path.mkdir(parents=True, exist_ok=True)
    model_defaults = {
        "baseline": {},
        "random_forest": {"n_estimators": 300, "max_depth": 6},
        "gradient_boosting": {"n_estimators": 250, "learning_rate": 0.05},
        "quantile": {"alpha": 0.85},
    }
    return TrainingConfig(
        data_root=data_cfg.data_root,
        experiments_root=experiments_path,
        models=model_defaults,
        forecast_horizon=settings.default_horizon_minutes // _timeframe_to_minutes(settings.yahoo_finance_interval),
    )


def _timeframe_to_minutes(timeframe: str) -> int:
    mapping = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 390,
    }
    return mapping.get(timeframe, 5)

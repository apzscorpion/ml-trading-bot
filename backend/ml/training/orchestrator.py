"""High-level orchestrator for walk-forward training across model families."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from backend.data_pipeline import FeatureStore
from backend.data_pipeline.config import get_config as get_data_config

from .config import TrainingConfig, get_config
from .models.baseline import BaselineTrainer
from .models.gradient_boosting import GradientBoostingTrainer
from .models.quantile import QuantileTrainer
from .models.random_forest import RandomForestTrainer
from .registry import ExperimentRecord, ExperimentRegistry
from .walk_forward import WalkForwardSplitter

TRAINER_FACTORIES = {
    "baseline": BaselineTrainer,
    "random_forest": RandomForestTrainer,
    "gradient_boosting": GradientBoostingTrainer,
    "quantile": QuantileTrainer,
}


@dataclass
class TrainingResult:
    experiment_id: str
    symbol: str
    timeframe: str
    metrics: Dict[str, Dict[str, float]]
    artifacts: Dict[str, str]


class TrainingOrchestrator:
    """Orchestrates multi-family walk-forward experiments."""

    def __init__(self, config: Optional[TrainingConfig] = None):
        self._config = config or get_config()
        data_cfg = get_data_config(str(self._config.data_root))
        self._feature_store = FeatureStore(config=data_cfg)
        self._registry = ExperimentRegistry(self._config.experiments_root)

    def train(
        self,
        symbol: str,
        timeframe: str,
        families: Optional[List[str]] = None,
        dataset_version: Optional[str] = None,
    ) -> TrainingResult:
        families = families or self._config.default_families
        df = self._feature_store.load_features(
            symbol=symbol,
            timeframe=timeframe,
            dataset_version=dataset_version,
        )
        if df is None or len(df) < self._config.min_rows:
            raise ValueError("Insufficient data for training")

        df = self._prepare_features(df)
        splitter = WalkForwardSplitter(
            n_splits=self._config.walk_forward_splits,
            test_size=self._config.forecast_horizon,
        )

        metrics_summary: Dict[str, Dict[str, float]] = {}
        artifacts_summary: Dict[str, str] = {}

        for family in families:
            trainer_cls = TRAINER_FACTORIES.get(family)
            if not trainer_cls:
                continue
            trainer = trainer_cls(self._config.models.get(family, {}))
            metrics_accum: List[Dict[str, float]] = []

            for split in splitter.split(df):
                train_df = df.iloc[split.train_indices[0] : split.train_indices[1]].copy()
                test_df = df.iloc[split.test_indices[0] : split.test_indices[1]].copy()
                metrics, artifact = trainer.train_and_score(train_df, test_df)
                metrics_accum.append(metrics)
                artifacts_summary[f"{family}_artifact"] = artifact.get("trainer", family)

            metrics_summary[family] = self._aggregate_metrics(metrics_accum)

        experiment_id = self._build_experiment_id(symbol, timeframe)
        record = ExperimentRecord(
            experiment_id=experiment_id,
            symbol=symbol,
            timeframe=timeframe,
            families=families,
            metrics={family: metrics_summary[family] for family in metrics_summary},
            artifacts=artifacts_summary,
            created_at=datetime.utcnow(),
        )
        artifact_path = self._registry.log(record)
        artifacts_summary["registry_path"] = str(artifact_path)

        return TrainingResult(
            experiment_id=experiment_id,
            symbol=symbol,
            timeframe=timeframe,
            metrics=metrics_summary,
            artifacts=artifacts_summary,
        )

    def walk_forward_validate(
        self,
        symbol: str,
        timeframe: str,
        families: Optional[List[str]] = None,
        dataset_version: Optional[str] = None,
        alert_threshold_pct: float = 0.02,
    ) -> Dict[str, Dict]:
        families = families or self._config.default_families
        df = self._feature_store.load_features(
            symbol=symbol,
            timeframe=timeframe,
            dataset_version=dataset_version,
        )
        if df is None or len(df) < self._config.min_rows:
            raise ValueError("Insufficient data for validation")

        df_prepared = self._prepare_features(df)
        splitter = WalkForwardSplitter(
            n_splits=self._config.walk_forward_splits,
            test_size=self._config.forecast_horizon,
        )

        reference_close = float(df_prepared["close"].iloc[-1]) if "close" in df_prepared.columns else None

        split_metrics: Dict[str, List[Dict[str, float]]] = {}
        alerts: List[Dict[str, str]] = []

        for family in families:
            trainer_cls = TRAINER_FACTORIES.get(family)
            if not trainer_cls:
                continue
            trainer = trainer_cls(self._config.models.get(family, {}))
            family_results: List[Dict[str, float]] = []

            for split_id, split in enumerate(splitter.split(df_prepared)):
                train_df = df_prepared.iloc[split.train_indices[0] : split.train_indices[1]].copy()
                test_df = df_prepared.iloc[split.test_indices[0] : split.test_indices[1]].copy()

                metrics, _artifact = trainer.train_and_score(train_df, test_df)

                rmse = metrics.get("rmse")
                rmse_pct = None
                if reference_close and rmse is not None:
                    rmse_pct = float(rmse) / reference_close
                    if rmse_pct > alert_threshold_pct:
                        alerts.append(
                            {
                                "family": family,
                                "split": str(split_id),
                                "metric": "rmse",
                                "value": f"{rmse_pct * 100:.2f}%",
                            }
                        )

                family_results.append(
                    {
                        "split": split_id,
                        "rmse": metrics.get("rmse"),
                        "mae": metrics.get("mae"),
                        "rmse_pct": rmse_pct * 100 if rmse_pct is not None else None,
                        "train_start": train_df["start_ts"].iloc[0] if "start_ts" in train_df.columns else None,
                        "train_end": train_df["start_ts"].iloc[-1] if "start_ts" in train_df.columns else None,
                        "test_start": test_df["start_ts"].iloc[0] if "start_ts" in test_df.columns else None,
                        "test_end": test_df["start_ts"].iloc[-1] if "start_ts" in test_df.columns else None,
                    }
                )

            if family_results:
                split_metrics[family] = family_results

        aggregated = {
            family: self._aggregate_metrics([{
                "rmse": result.get("rmse", 0.0),
                "mae": result.get("mae", 0.0)
            } for result in results])
            for family, results in split_metrics.items()
        }

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "split_metrics": split_metrics,
            "aggregated": aggregated,
            "alerts": alerts,
        }

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.sort_values("start_ts")
        df["close_lag1"] = df["close"].shift(1)
        df = df.fillna(method="ffill").dropna().reset_index(drop=True)
        return df

    def _aggregate_metrics(self, metrics: List[Dict[str, float]]) -> Dict[str, float]:
        keys = metrics[0].keys()
        aggregated = {}
        for key in keys:
            aggregated[key] = float(np.mean([m[key] for m in metrics]))
        return aggregated

    def _build_experiment_id(self, symbol: str, timeframe: str) -> str:
        cleaned_symbol = symbol.replace(".", "_")
        return f"exp-{cleaned_symbol}-{timeframe}-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"

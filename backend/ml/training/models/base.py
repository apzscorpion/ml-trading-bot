"""Base model trainer abstractions."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd


@dataclass
class TrainOutput:
    model_name: str
    metrics: Dict[str, float]
    artifact: Dict[str, str]


class ModelTrainer(ABC):
    name: str

    def __init__(self, params: Dict):
        self.params = params

    @abstractmethod
    def fit(self, train_df: pd.DataFrame) -> None:  # pragma: no cover - abstract
        ...

    @abstractmethod
    def predict(self, test_df: pd.DataFrame) -> np.ndarray:  # pragma: no cover - abstract
        ...

    def evaluate(self, test_df: pd.DataFrame, predictions: np.ndarray) -> Dict[str, float]:
        actuals = test_df["close"].to_numpy()
        errors = predictions - actuals
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        mape = float(np.mean(np.abs(errors / np.clip(actuals, 1e-8, None))) * 100)
        directional = float(
            (np.sign(np.diff(predictions)) == np.sign(np.diff(actuals))).mean() * 100
        )
        return {
            "mae": mae,
            "rmse": rmse,
            "mape": mape,
            "directional_accuracy": directional,
        }

    def train_and_score(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
    ) -> Tuple[Dict[str, float], Dict[str, str]]:
        self.fit(train_df)
        preds = self.predict(test_df)
        metrics = self.evaluate(test_df, preds)
        artifact = self._artifact_metadata()
        return metrics, artifact

    def _artifact_metadata(self) -> Dict[str, str]:
        return {"trainer": self.name}

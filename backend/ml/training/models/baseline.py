"""Baseline trainer that uses persistence and moving averages."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import ModelTrainer


class BaselineTrainer(ModelTrainer):
    name = "baseline"

    def fit(self, train_df: pd.DataFrame) -> None:
        self.window = int(self.params.get("window", 10))

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        close = test_df["close"].to_numpy()
        if len(close) == 0:
            return close
        avg = np.full_like(close, close.mean())
        return avg

"""Gradient boosting regression trainer."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from .base import ModelTrainer


class GradientBoostingTrainer(ModelTrainer):
    name = "gradient_boosting"

    def __init__(self, params):
        super().__init__(params)
        self.model = GradientBoostingRegressor(
            n_estimators=self.params.get("n_estimators", 200),
            learning_rate=self.params.get("learning_rate", 0.05),
            max_depth=self.params.get("max_depth", 3),
            random_state=42,
        )

    def fit(self, train_df: pd.DataFrame) -> None:
        X, y = self._build_xy(train_df)
        self.model.fit(X, y)

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        X, _ = self._build_xy(test_df)
        return self.model.predict(X)

    def _build_xy(self, df: pd.DataFrame):
        feature_cols = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "return_1",
            "return_5",
            "rolling_mean_10",
            "rolling_std_10",
            "volume_ma_10",
            "high_low_spread",
            "momentum_10",
            "ema_20",
            "is_gap_up",
            "is_gap_down",
        ]
        X = df[feature_cols].fillna(0.0).to_numpy()
        y = df["close"].to_numpy()
        return X, y

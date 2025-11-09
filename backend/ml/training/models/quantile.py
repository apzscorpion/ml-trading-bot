"""Quantile regression trainer using gradient boosting."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from .base import ModelTrainer


class QuantileTrainer(ModelTrainer):
    name = "quantile"

    def __init__(self, params):
        super().__init__(params)
        alpha = float(self.params.get("alpha", 0.85))
        self.lower_model = GradientBoostingRegressor(
            loss="quantile",
            alpha=1 - alpha,
            n_estimators=200,
            learning_rate=0.05,
            random_state=42,
        )
        self.upper_model = GradientBoostingRegressor(
            loss="quantile",
            alpha=alpha,
            n_estimators=200,
            learning_rate=0.05,
            random_state=42,
        )
        self.point_model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            random_state=42,
        )

    def fit(self, train_df: pd.DataFrame) -> None:
        X, y = self._build_xy(train_df)
        self.lower_model.fit(X, y)
        self.upper_model.fit(X, y)
        self.point_model.fit(X, y)

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        X, _ = self._build_xy(test_df)
        point = self.point_model.predict(X)
        lower = self.lower_model.predict(X)
        upper = self.upper_model.predict(X)
        self.last_interval = np.vstack([lower, upper]).T
        return point

    def _artifact_metadata(self):
        bounds = (
            self.last_interval.mean(axis=0).tolist()
            if hasattr(self, "last_interval")
            else []
        )
        return {"trainer": self.name, "avg_bounds": str(bounds)}

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

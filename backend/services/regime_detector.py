"""Lightweight regime detection for Indian equities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class RegimeResult:
    name: str
    volatility: float
    momentum: float
    range_ratio: float


class RegimeDetector:
    """Classify market regime based on recent candle statistics."""

    def __init__(self, lookback: int = 120):
        self.lookback = lookback

    def detect(self, candles: List[Dict]) -> RegimeResult:
        if not candles:
            return RegimeResult("unknown", 0.0, 0.0, 0.0)

        df = pd.DataFrame(candles[-self.lookback :])
        df = df.dropna(subset=["close"])
        if df.empty:
            return RegimeResult("unknown", 0.0, 0.0, 0.0)

        returns = df["close"].pct_change().dropna()
        volatility = float(returns.std())
        momentum = float(df["close"].iloc[-1] / df["close"].iloc[0] - 1)
        range_ratio = float((df["high"].max() - df["low"].min()) / df["close"].iloc[-1])

        regime = self._classify(volatility, momentum, range_ratio)
        return RegimeResult(regime, volatility, momentum, range_ratio)

    def _classify(self, volatility: float, momentum: float, range_ratio: float) -> str:
        if volatility < 0.004 and abs(momentum) < 0.01:
            return "range_bound"
        if momentum > 0.015:
            return "trending_up"
        if momentum < -0.015:
            return "trending_down"
        if volatility >= 0.01 or range_ratio > 0.03:
            return "volatile"
        return "neutral"


def detect_regime(candles: List[Dict]) -> RegimeResult:
    detector = RegimeDetector()
    return detector.detect(candles)

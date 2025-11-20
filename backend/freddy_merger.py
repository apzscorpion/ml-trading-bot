"""
Freddy API - Prediction Merger
Re-architected to use regime-aware gating, champion-challenger weighting,
and probabilistic confidence bands.
"""
from typing import Dict, List, Optional
import asyncio
from datetime import datetime
import numpy as np
import pandas as pd

from backend.bots.rsi_bot import RSIBot
from backend.bots.macd_bot import MACDBot
from backend.bots.ma_bot import MABot
from backend.bots.ml_bot import MLBot
from backend.bots.lstm_bot import LSTMBot
from backend.bots.transformer_bot import TransformerBot
from backend.bots.ensemble_bot import EnsembleBot
from backend.ml.training.config import get_config as get_training_config
from backend.ml.training.registry import ExperimentRegistry
from backend.ml.validators import prediction_validator
from backend.services.regime_detector import detect_regime
from backend.services.model_performance_tracker import model_performance_tracker
from backend.utils.logger import get_logger

logger = get_logger(__name__)


REGIME_DEFAULT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "trending_up": {"lstm_bot": 0.28, "transformer_bot": 0.28, "ml_bot": 0.18, "ensemble_bot": 0.16, "ma_bot": 0.10},
    "trending_down": {"lstm_bot": 0.26, "transformer_bot": 0.26, "ml_bot": 0.20, "ensemble_bot": 0.18, "ma_bot": 0.10},
    "range_bound": {"ensemble_bot": 0.32, "ml_bot": 0.24, "ma_bot": 0.20, "rsi_bot": 0.14, "macd_bot": 0.10},
    "volatile": {"ensemble_bot": 0.28, "transformer_bot": 0.24, "lstm_bot": 0.18, "ml_bot": 0.18, "ma_bot": 0.12},
    "neutral": {"ensemble_bot": 0.25, "ml_bot": 0.20, "lstm_bot": 0.20, "transformer_bot": 0.20, "ma_bot": 0.15},
    "unknown": {"ensemble_bot": 0.25, "ml_bot": 0.25, "ma_bot": 0.20, "rsi_bot": 0.15, "macd_bot": 0.15},
}

FAMILY_TO_BOTS: Dict[str, List[str]] = {
    "baseline": ["ma_bot", "rsi_bot", "macd_bot"],
    "random_forest": ["ml_bot", "ensemble_bot"],
    "gradient_boosting": ["ensemble_bot"],
    "quantile": ["ensemble_bot"],
}


class FreddyMerger:
    """Aggregates bot predictions using regime-aware gating and monitoring."""

    MAX_RELATIVE_MOVE = 0.12  # 12% envelope relative to latest close
    MAX_STEP_MOVE = 0.06      # 6% between consecutive points
    MIN_SERIES_POINTS = 1

    def __init__(self):
        self.bots = [
            RSIBot(),
            MACDBot(),
            MABot(),
            MLBot(),
            LSTMBot(),
            TransformerBot(),
            EnsembleBot(),
        ]
        self.available_bots = {bot.name: bot for bot in self.bots}
        training_cfg = get_training_config()
        self.registry = ExperimentRegistry(training_cfg.experiments_root)

    def _extract_reference_close(self, candles: List[Dict]) -> Optional[float]:
        if not candles:
            return None
        price = candles[-1].get("close")
        try:
            price = float(price)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(price) or price <= 0:
            return None
        return price

    def _sanitize_bot_prediction(
        self, 
        prediction: Dict, 
        reference_close: Optional[float],
        recent_candles: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """Sanitize prediction using ML validator first, then legacy checks"""
        series = prediction.get("predicted_series")
        bot_name = prediction.get("bot_name", "unknown")
        
        if not series:
            return None
        
        if not reference_close or reference_close <= 0:
            logger.warning(f"Bot {bot_name}: invalid reference price")
            return None
        
        # First: use ML validator with volatility-aware checks
        is_valid, rejection_reason, val_stats = prediction_validator.validate_prediction(
            series, reference_close, bot_name, recent_candles=recent_candles
        )
        
        if not is_valid:
            logger.warning(
                f"Bot {bot_name} rejected by validator: {rejection_reason}",
                extra=val_stats
            )
            # Attempt sanitization
            series, sanitize_stats = prediction_validator.sanitize_prediction(
                series, reference_close, bot_name
            )
            logger.info(f"Bot {bot_name} sanitized: {sanitize_stats}")
        
        # Legacy validation + deduplication
        sanitized: List[Dict] = []
        seen_ts = set()
        prev_price: Optional[float] = reference_close

        for point in series:
            ts = point.get("ts")
            price = point.get("price")

            try:
                price = float(price)
            except (TypeError, ValueError):
                logger.warning("Dropping bot prediction with non-numeric price", bot=bot_name)
                return None

            if not np.isfinite(price) or price <= 0:
                logger.warning("Dropping bot prediction with invalid price", bot=bot_name, price=price)
                return None

            if reference_close and reference_close > 0:
                change_pct = abs(price - reference_close) / reference_close
                if change_pct > self.MAX_RELATIVE_MOVE:
                    logger.warning(
                        "Bot prediction exceeds max allowed move",
                        extra={
                            "bot": bot_name,
                            "price": price,
                            "reference_close": reference_close,
                            "change_pct": round(change_pct * 100, 2),
                        },
                    )
                    return None

            if prev_price and prev_price > 0:
                step_change = abs(price - prev_price) / prev_price
                if step_change > self.MAX_STEP_MOVE:
                    logger.warning(
                        "Bot prediction exceeds max step change",
                        extra={
                            "bot": prediction.get("bot_name"),
                            "price": price,
                            "previous_price": prev_price,
                            "step_change_pct": round(step_change * 100, 2),
                        },
                    )
                    return None

            if ts in seen_ts or ts is None:
                continue

            sanitized.append({"ts": ts, "price": float(price)})
            seen_ts.add(ts)
            prev_price = price

        if len(sanitized) < self.MIN_SERIES_POINTS:
            return None

        sanitized.sort(key=lambda p: p["ts"])
        prediction.setdefault("meta", {})["sanitizer"] = {
            "reference_close": reference_close,
            "points_in": len(series),
            "points_out": len(sanitized),
        }
        prediction["predicted_series"] = sanitized
        return prediction

    def _sanitize_series(self, series: List[Dict], reference_close: Optional[float]) -> List[Dict]:
        sanitized: List[Dict] = []
        seen_ts = set()
        prev_price: Optional[float] = reference_close

        for point in series:
            ts = point.get("ts")
            price = point.get("price")

            try:
                price = float(price)
            except (TypeError, ValueError):
                continue

            if not np.isfinite(price) or price <= 0 or ts in seen_ts or ts is None:
                continue

            if reference_close and reference_close > 0:
                change_pct = abs(price - reference_close) / reference_close
                if change_pct > self.MAX_RELATIVE_MOVE:
                    logger.warning(
                        "Merged series point exceeds bounds",
                        extra={"price": price, "reference_close": reference_close, "change_pct": round(change_pct * 100, 2)},
                    )
                    continue

            if prev_price and prev_price > 0:
                step_change = abs(price - prev_price) / prev_price
                if step_change > self.MAX_STEP_MOVE:
                    logger.warning(
                        "Merged series step change exceeds bounds",
                        extra={
                            "price": price,
                            "previous_price": prev_price,
                            "step_change_pct": round(step_change * 100, 2),
                        },
                    )
                    continue

            sanitized.append({"ts": ts, "price": float(price)})
            seen_ts.add(ts)
            prev_price = price

        sanitized.sort(key=lambda p: p["ts"])
        return sanitized

    async def predict(
        self,
        symbol: str,
        candles: List[Dict],
        horizon_minutes: int = 180,
        timeframe: str = "5m",
        selected_bots: Optional[List[str]] = None,
    ) -> Dict:
        logger.info("Freddy predicting for %s horizon=%sm", symbol, horizon_minutes)

        reference_close = self._extract_reference_close(candles)
        if reference_close is None:
            logger.warning("Unable to derive reference close; falling back to baseline prediction")
            regime_result = detect_regime(candles)
            return self._baseline_prediction(symbol, candles, horizon_minutes, timeframe, regime_result)

        regime_result = detect_regime(candles)
        gating_weights = self._compute_bot_weights(symbol, timeframe, regime_result.name)

        if selected_bots:
            logger.info("Using selected bots: %s", selected_bots)
            gating_weights = {
                bot: gating_weights.get(bot, 0.1) for bot in selected_bots
            }

        bots_to_use = [
            bot for bot in self.bots if bot.name in gating_weights and gating_weights[bot.name] > 0
        ]
        if not bots_to_use:
            bots_to_use = self.bots
            gating_weights = {bot.name: 1.0 / len(self.bots) for bot in self.bots}

        for bot in bots_to_use:
            bot.set_model_context(symbol, timeframe)
            if hasattr(bot, "_load_or_create_model"):
                bot._load_or_create_model()
            elif hasattr(bot, "_load_or_create_models"):
                bot._load_or_create_models()

        bot_tasks = [bot.predict(candles, horizon_minutes, timeframe) for bot in bots_to_use]
        bot_predictions = await asyncio.gather(*bot_tasks, return_exceptions=True)

        sanitization_summary = {"retained": [], "dropped": [], "sanitized": []}
        valid_predictions = []
        bot_raw_outputs = {}  # Store raw outputs for audit
        validation_flags = {}  # Store validation results
        
        for bot, pred in zip(bots_to_use, bot_predictions):
            # Store raw output
            if not isinstance(pred, Exception):
                bot_raw_outputs[bot.name] = pred
            
            if isinstance(pred, Exception):
                logger.error("Bot %s prediction failed: %s", bot.name, pred)
                validation_flags[bot.name] = {"status": "exception", "error": str(pred)}
                continue
            
            if pred and pred.get("predicted_series") and pred.get("confidence", 0) > 0:
                # Pass recent candles for volatility-aware validation
                sanitized = self._sanitize_bot_prediction(pred, reference_close, recent_candles=candles[-50:])
                if sanitized:
                    valid_predictions.append(sanitized)
                    sanitization_summary["retained"].append(bot.name)
                    # Check if it was modified during sanitization
                    if sanitized != pred:
                        sanitization_summary["sanitized"].append(bot.name)
                        validation_flags[bot.name] = {"status": "sanitized"}
                    else:
                        validation_flags[bot.name] = {"status": "valid"}
                else:
                    logger.warning("Bot %s prediction rejected after sanitization", bot.name)
                    sanitization_summary["dropped"].append(bot.name)
                    validation_flags[bot.name] = {"status": "rejected"}
            else:
                logger.warning("Bot %s returned empty prediction", bot.name)
                sanitization_summary["dropped"].append(bot.name)
                validation_flags[bot.name] = {"status": "empty"}

        if not valid_predictions:
            logger.warning("Falling back to baseline prediction")
            return self._baseline_prediction(symbol, candles, horizon_minutes, timeframe, regime_result)

        merged_series = self._merge_predictions(valid_predictions, gating_weights)
        merged_series = self._sanitize_series(merged_series, reference_close)
        if not merged_series:
            logger.warning("Merged series invalid after sanitization; using baseline prediction")
            return self._baseline_prediction(symbol, candles, horizon_minutes, timeframe, regime_result)
        merged_trend = self._merge_trend_predictions(valid_predictions, merged_series, timeframe)
        overall_confidence = self._compute_confidence(valid_predictions, gating_weights)
        confidence_band = self._confidence_band(merged_series)

        bot_contributions = {}
        for pred in valid_predictions:
            bot_name = pred["bot_name"]
            weight = gating_weights.get(bot_name, pred.get("confidence", 0.1))
            bot_contributions[bot_name] = {
                "weight": float(weight),
                "confidence": float(pred.get("confidence", 0.0)),
                "meta": pred.get("meta", {}),
            }

        # Capture feature snapshot for audit trail
        feature_snapshot = {}
        if candles:
            df = pd.DataFrame(candles)
            if len(df) > 20:
                feature_snapshot = {
                    "latest_close": float(df['close'].iloc[-1]),
                    "sma_20": float(df['close'].tail(20).mean()),
                    "volatility_20": float(df['close'].pct_change().tail(20).std()),
                    "volume_avg": float(df['volume'].tail(20).mean()) if 'volume' in df.columns else None
                }
        
        return {
            "symbol": symbol,
            "produced_at": datetime.utcnow().isoformat(),
            "horizon_minutes": horizon_minutes,
            "timeframe": timeframe,
            "predicted_series": merged_series,
            "overall_confidence": float(overall_confidence),
            "confidence_interval": confidence_band,
            "bot_contributions": bot_contributions,
            "trend": {**merged_trend, "regime": regime_result.name},
            "model_version": "freddy_v2.0",
            "sanitization": sanitization_summary,
            # Enhanced logging fields
            "bot_raw_outputs": bot_raw_outputs,
            "validation_flags": validation_flags,
            "feature_snapshot": feature_snapshot
        }

    def _compute_bot_weights(self, symbol: str, timeframe: str, regime: str) -> Dict[str, float]:
        """
        Compute bot weights using performance-based dynamic weighting.
        
        Formula: weight = base_weight * performance_score * recency_factor
        """
        base_weights = REGIME_DEFAULT_WEIGHTS.get(regime, REGIME_DEFAULT_WEIGHTS["unknown"]).copy()
        
        # Get performance scores for all bots
        performance_scores = model_performance_tracker.get_all_bot_scores(
            symbol, timeframe, lookback_hours=24
        )
        
        # Get recency factors
        recency_factors = {}
        for bot_name in base_weights.keys():
            recency_factors[bot_name] = model_performance_tracker.get_recency_factor(
                symbol, timeframe, bot_name, lookback_hours=24
            )
        
        # Apply performance-based adjustments
        adjusted_weights = {}
        for bot_name, base_weight in base_weights.items():
            performance_score = performance_scores.get(bot_name, 0.5)
            recency_factor = recency_factors.get(bot_name, 0.5)
            
            # Calculate adjusted weight
            # Formula: base_weight * performance_score * recency_factor
            adjusted_weight = base_weight * performance_score * recency_factor
            
            # Ensure minimum weight (never completely exclude)
            adjusted_weight = max(0.05, adjusted_weight)
            
            adjusted_weights[bot_name] = adjusted_weight
        
        # Also check registry for historical performance (legacy support)
        record = self.registry.find_best(symbol, timeframe)
        if record:
            for family, metrics in record.metrics.items():
                rmse = metrics.get("rmse")
                if rmse is None:
                    continue
                bonus = max(0.05, min(0.25, 1.0 / (rmse + 1e-3)))
                for bot_name in FAMILY_TO_BOTS.get(family, []):
                    if bot_name in adjusted_weights:
                        adjusted_weights[bot_name] += bonus * 0.3  # Smaller bonus from registry
        
        # Normalize weights
        total = sum(adjusted_weights.values())
        if total == 0:
            return {bot: 1.0 / len(base_weights) for bot in base_weights}
        
        normalized_weights = {bot: weight / total for bot, weight in adjusted_weights.items()}
        
        # Log weight distribution for debugging
        logger.debug(
            f"Bot weights for {symbol}/{timeframe}",
            extra={
                "regime": regime,
                "weights": normalized_weights,
                "performance_scores": performance_scores,
                "recency_factors": recency_factors
            }
        )
        
        return normalized_weights

    def _merge_predictions(self, predictions: List[Dict], weights: Dict[str, float]) -> List[Dict]:
        timestamp_prices: Dict[str, List[Dict[str, float]]] = {}
        for pred in predictions:
            bot_name = pred["bot_name"]
            weight = weights.get(bot_name, pred.get("confidence", 0.1))
            for point in pred["predicted_series"]:
                timestamp_prices.setdefault(point["ts"], []).append({
                    "price": point["price"],
                    "weight": weight,
                })

        merged_series = []
        for ts in sorted(timestamp_prices.keys()):
            entries = timestamp_prices[ts]
            total_weight = sum(e["weight"] for e in entries)
            if total_weight > 0:
                price = sum(e["price"] * e["weight"] for e in entries) / total_weight
            else:
                price = float(np.mean([e["price"] for e in entries]))
            merged_series.append({"ts": ts, "price": float(price)})
        return merged_series

    def _compute_confidence(self, predictions: List[Dict], weights: Dict[str, float]) -> float:
        weighted_conf = 0.0
        total_weight = 0.0
        for pred in predictions:
            bot_name = pred["bot_name"]
            weight = weights.get(bot_name, 0.1)
            weighted_conf += pred.get("confidence", 0.0) * weight
            total_weight += weight
        return weighted_conf / total_weight if total_weight else 0.0

    def _confidence_band(self, series: List[Dict]) -> Dict[str, float]:
        prices = np.array([point["price"] for point in series])
        if len(prices) == 0:
            return {"lower": 0.0, "upper": 0.0}
        mean = float(np.mean(prices))
        std = float(np.std(prices))
        multiplier = 1.5
        return {
            "lower": max(0.0, mean - multiplier * std),
            "upper": mean + multiplier * std,
        }

    def _merge_trend_predictions(
        self,
        predictions: List[Dict],
        merged_series: List[Dict],
        timeframe: str,
    ) -> Dict:
        trend_directions = []
        trend_strengths = []
        trend_durations = []
        trend_weights = []

        for pred in predictions:
            meta = pred.get("meta", {})
            if "trend_direction" not in meta:
                continue
            trend_directions.append(meta.get("trend_direction", 0))
            trend_strengths.append(meta.get("trend_strength", 0.0))
            trend_durations.append(meta.get("trend_duration_minutes", 0))
            trend_weights.append(pred.get("confidence", 0.0))

        if merged_series:
            helper_bot = RSIBot()
            merged_trend_meta = helper_bot._generate_trend_metadata(merged_series, timeframe)
        else:
            merged_trend_meta = {
                "trend_direction": 0,
                "trend_direction_str": "neutral",
                "trend_strength": 0.0,
                "trend_strength_category": "weak",
                "trend_duration_minutes": 0,
            }

        if trend_weights and sum(trend_weights) > 0:
            total_weight = sum(trend_weights)
            weighted_direction = sum(d * w for d, w in zip(trend_directions, trend_weights)) / total_weight
            weighted_strength = sum(s * w for s, w in zip(trend_strengths, trend_weights)) / total_weight
            avg_duration = sum(trend_durations) / len(trend_durations)

            final_direction = merged_trend_meta["trend_direction"]
            final_direction_str = merged_trend_meta["trend_direction_str"]
            if weighted_direction > 0.3:
                final_direction = 1
                final_direction_str = "up"
            elif weighted_direction < -0.3:
                final_direction = -1
                final_direction_str = "down"

            final_strength = merged_trend_meta["trend_strength"] * 0.6 + weighted_strength * 0.4
            final_duration = max(merged_trend_meta["trend_duration_minutes"], int(avg_duration))
        else:
            final_direction = merged_trend_meta["trend_direction"]
            final_direction_str = merged_trend_meta["trend_direction_str"]
            final_strength = merged_trend_meta["trend_strength"]
            final_duration = merged_trend_meta["trend_duration_minutes"]

        if final_strength < 0.3:
            strength_category = "weak"
        elif final_strength < 0.6:
            strength_category = "moderate"
        else:
            strength_category = "strong"

        return {
            "trend_direction": final_direction,
            "trend_direction_str": final_direction_str,
            "trend_strength": round(final_strength, 3),
            "trend_strength_category": strength_category,
            "trend_duration_minutes": final_duration,
        }

    def _baseline_prediction(
        self,
        symbol: str,
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str,
        regime_result,
    ) -> Dict:
        if not candles:
            return self._empty_prediction(symbol)
        last_candle = candles[-1]
        last_close = last_candle["close"]
        reference_idx = -min(20, len(candles))
        reference_close = candles[reference_idx]["close"]
        momentum = (last_close - reference_close) / reference_close if reference_close else 0.0
        interval_minutes = self._interval_minutes(timeframe)
        horizon_steps = max(1, horizon_minutes // interval_minutes)
        drift = momentum / max(1, horizon_steps)

        ma_bot = self.available_bots.get("ma_bot")
        last_ts = last_candle.get("start_ts")
        if isinstance(last_ts, str):
            last_ts = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))

        future_timestamps = (
            ma_bot._generate_future_timestamps(last_ts, timeframe, horizon_minutes)
            if ma_bot and last_ts
            else []
        )

        predicted_series = []
        for idx, ts in enumerate(future_timestamps or []):
            price = last_close * (1 + drift * (idx + 1))
            predicted_series.append({"ts": ts.isoformat(), "price": float(price)})
        if not predicted_series:
            predicted_series.append({
                "ts": last_ts.isoformat() if last_ts else datetime.utcnow().isoformat(),
                "price": float(last_close),
            })
        return {
            "symbol": symbol,
            "produced_at": datetime.utcnow().isoformat(),
            "horizon_minutes": horizon_minutes,
            "timeframe": timeframe,
            "predicted_series": predicted_series,
            "overall_confidence": 0.25,
            "confidence_interval": self._confidence_band(predicted_series),
            "bot_contributions": {"baseline": {"weight": 1.0, "confidence": 0.25, "meta": {"regime": regime_result.name}}},
            "trend": {"trend_direction": 0, "trend_direction_str": "neutral", "trend_strength": 0.0, "trend_strength_category": "weak", "trend_duration_minutes": 0, "regime": regime_result.name},
            "model_version": "freddy_v2.0",
        }

    def _interval_minutes(self, timeframe: str) -> int:
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

    def _empty_prediction(self, symbol: str) -> Dict:
        return {
            "symbol": symbol,
            "produced_at": datetime.utcnow().isoformat(),
            "horizon_minutes": 0,
            "timeframe": "",
            "predicted_series": [],
            "overall_confidence": 0.0,
            "bot_contributions": {},
            "model_version": "freddy_v2.0",
            "error": "all_bots_failed",
        }


freddy_merger = FreddyMerger()


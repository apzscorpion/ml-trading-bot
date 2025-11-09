"""
Prometheus metrics for monitoring predictions and performance.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict
import time

# Metrics
prediction_counter = Counter(
    'predictions_total',
    'Total number of predictions generated',
    ['bot_name', 'symbol', 'timeframe']
)

prediction_latency = Histogram(
    'prediction_latency_seconds',
    'Prediction generation latency in seconds',
    ['bot_name'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

websocket_connections = Gauge(
    'websocket_connections_total',
    'Current number of WebSocket connections'
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits'
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses'
)

cache_size = Gauge(
    'cache_size',
    'Current cache size'
)

REGIME_LABELS = [
    'trending_up',
    'trending_down',
    'range_bound',
    'volatile',
    'neutral',
    'unknown'
]

regime_state = Gauge(
    'market_regime_state',
    'Active detected regime',
    ['symbol', 'timeframe', 'regime']
)

prediction_quality = Gauge(
    'prediction_quality_metric',
    'Latest prediction error metrics',
    ['symbol', 'timeframe', 'metric']
)

def record_prediction(bot_name: str, symbol: str, timeframe: str, latency: float):
    """Record a prediction metric"""
    prediction_counter.labels(
        bot_name=bot_name,
        symbol=symbol,
        timeframe=timeframe
    ).inc()
    prediction_latency.labels(bot_name=bot_name).observe(latency)

def update_websocket_connections(count: int):
    """Update WebSocket connection gauge"""
    websocket_connections.set(count)

def record_cache_hit():
    """Record a cache hit"""
    cache_hits.inc()

def record_cache_miss():
    """Record a cache miss"""
    cache_misses.inc()

def update_cache_size(size: int):
    """Update cache size gauge"""
    cache_size.set(size)


def record_regime(symbol: str, timeframe: str, regime: str):
    """Publish the current regime classification."""
    for label in REGIME_LABELS:
        regime_state.labels(symbol=symbol, timeframe=timeframe, regime=label).set(1 if label == regime else 0)


def record_prediction_quality(symbol: str, timeframe: str, metrics: Dict[str, float]):
    """Record latest prediction accuracy metrics."""
    for key, value in metrics.items():
        prediction_quality.labels(symbol=symbol, timeframe=timeframe, metric=key).set(value)

def get_metrics() -> bytes:
    """Get Prometheus metrics in text format"""
    return generate_latest()


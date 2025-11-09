"""
Candlestick pattern detection for intraday trading.
Detects various reversal and continuation patterns.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def detect_doji(candle: Dict, body_threshold: float = 0.1) -> bool:
    """
    Detect Doji pattern - open and close are very close.
    Indicates indecision/uncertainty.
    """
    open_price = candle.get('open', 0)
    close_price = candle.get('close', 0)
    high_price = candle.get('high', 0)
    low_price = candle.get('low', 0)
    
    if not all([open_price, close_price, high_price, low_price]):
        return False
    
    body_size = abs(close_price - open_price)
    total_range = high_price - low_price
    
    if total_range == 0:
        return False
    
    body_ratio = body_size / total_range
    return body_ratio <= body_threshold


def detect_hammer(candle: Dict, lower_shadow_ratio: float = 2.0) -> bool:
    """
    Detect Hammer pattern - small body, long lower shadow.
    Bullish reversal signal.
    """
    open_price = candle.get('open', 0)
    close_price = candle.get('close', 0)
    high_price = candle.get('high', 0)
    low_price = candle.get('low', 0)
    
    if not all([open_price, close_price, high_price, low_price]):
        return False
    
    body_size = abs(close_price - open_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    total_range = high_price - low_price
    
    if total_range == 0 or lower_shadow == 0:
        return False
    
    # Hammer: small body, long lower shadow, minimal upper shadow
    body_ratio = body_size / total_range
    shadow_ratio = lower_shadow / (body_size + 0.001)  # Avoid division by zero
    
    return (body_ratio < 0.3 and 
            shadow_ratio >= lower_shadow_ratio and 
            upper_shadow < body_size * 0.5)


def detect_hanging_man(candle: Dict, lower_shadow_ratio: float = 2.0) -> bool:
    """
    Detect Hanging Man pattern - similar to hammer but at top of uptrend.
    Bearish reversal signal.
    """
    open_price = candle.get('open', 0)
    close_price = candle.get('close', 0)
    high_price = candle.get('high', 0)
    low_price = candle.get('low', 0)
    
    if not all([open_price, close_price, high_price, low_price]):
        return False
    
    body_size = abs(close_price - open_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    total_range = high_price - low_price
    
    if total_range == 0 or lower_shadow == 0:
        return False
    
    # Hanging Man: small body, long lower shadow, minimal upper shadow
    body_ratio = body_size / total_range
    shadow_ratio = lower_shadow / (body_size + 0.001)
    
    return (body_ratio < 0.3 and 
            shadow_ratio >= lower_shadow_ratio and 
            upper_shadow < body_size * 0.5)


def detect_shooting_star(candle: Dict, upper_shadow_ratio: float = 2.0) -> bool:
    """
    Detect Shooting Star pattern - small body, long upper shadow.
    Bearish reversal signal.
    """
    open_price = candle.get('open', 0)
    close_price = candle.get('close', 0)
    high_price = candle.get('high', 0)
    low_price = candle.get('low', 0)
    
    if not all([open_price, close_price, high_price, low_price]):
        return False
    
    body_size = abs(close_price - open_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    total_range = high_price - low_price
    
    if total_range == 0 or upper_shadow == 0:
        return False
    
    # Shooting Star: small body, long upper shadow, minimal lower shadow
    body_ratio = body_size / total_range
    shadow_ratio = upper_shadow / (body_size + 0.001)
    
    return (body_ratio < 0.3 and 
            shadow_ratio >= upper_shadow_ratio and 
            lower_shadow < body_size * 0.5)


def detect_bullish_engulfing(current: Dict, previous: Dict) -> bool:
    """
    Detect Bullish Engulfing pattern - current candle engulfs previous bearish candle.
    Bullish reversal signal.
    """
    prev_open = previous.get('open', 0)
    prev_close = previous.get('close', 0)
    curr_open = current.get('open', 0)
    curr_close = current.get('close', 0)
    
    if not all([prev_open, prev_close, curr_open, curr_close]):
        return False
    
    # Previous candle should be bearish (red)
    prev_bearish = prev_close < prev_open
    # Current candle should be bullish (green)
    curr_bullish = curr_close > curr_open
    
    # Current candle should engulf previous (open lower, close higher)
    engulfs = curr_open < prev_close and curr_close > prev_open
    
    return prev_bearish and curr_bullish and engulfs


def detect_bearish_engulfing(current: Dict, previous: Dict) -> bool:
    """
    Detect Bearish Engulfing pattern - current candle engulfs previous bullish candle.
    Bearish reversal signal.
    """
    prev_open = previous.get('open', 0)
    prev_close = previous.get('close', 0)
    curr_open = current.get('open', 0)
    curr_close = current.get('close', 0)
    
    if not all([prev_open, prev_close, curr_open, curr_close]):
        return False
    
    # Previous candle should be bullish (green)
    prev_bullish = prev_close > prev_open
    # Current candle should be bearish (red)
    curr_bearish = curr_close < curr_open
    
    # Current candle should engulf previous (open higher, close lower)
    engulfs = curr_open > prev_close and curr_close < prev_open
    
    return prev_bullish and curr_bearish and engulfs


def detect_bullish_harami(current: Dict, previous: Dict) -> bool:
    """
    Detect Bullish Harami pattern - small bullish candle inside previous bearish candle.
    Bullish reversal signal.
    """
    prev_open = previous.get('open', 0)
    prev_close = previous.get('close', 0)
    curr_open = current.get('open', 0)
    curr_close = current.get('close', 0)
    
    if not all([prev_open, prev_close, curr_open, curr_close]):
        return False
    
    # Previous candle should be bearish
    prev_bearish = prev_close < prev_open
    # Current candle should be bullish
    curr_bullish = curr_close > curr_open
    
    # Current candle should be inside previous candle
    inside = (curr_open > prev_close and curr_open < prev_open and
              curr_close > prev_close and curr_close < prev_open)
    
    return prev_bearish and curr_bullish and inside


def detect_bearish_harami(current: Dict, previous: Dict) -> bool:
    """
    Detect Bearish Harami pattern - small bearish candle inside previous bullish candle.
    Bearish reversal signal.
    """
    prev_open = previous.get('open', 0)
    prev_close = previous.get('close', 0)
    curr_open = current.get('open', 0)
    curr_close = current.get('close', 0)
    
    if not all([prev_open, prev_close, curr_open, curr_close]):
        return False
    
    # Previous candle should be bullish
    prev_bullish = prev_close > prev_open
    # Current candle should be bearish
    curr_bearish = curr_close < curr_open
    
    # Current candle should be inside previous candle
    inside = (curr_open < prev_close and curr_open > prev_open and
              curr_close < prev_close and curr_close > prev_open)
    
    return prev_bullish and curr_bearish and inside


def detect_marubozu(candle: Dict, body_threshold: float = 0.95) -> bool:
    """
    Detect Marubozu pattern - strong body with no shadows.
    Continuation signal - bullish or bearish.
    """
    open_price = candle.get('open', 0)
    close_price = candle.get('close', 0)
    high_price = candle.get('high', 0)
    low_price = candle.get('low', 0)
    
    if not all([open_price, close_price, high_price, low_price]):
        return False
    
    body_size = abs(close_price - open_price)
    total_range = high_price - low_price
    
    if total_range == 0:
        return False
    
    body_ratio = body_size / total_range
    return body_ratio >= body_threshold


def detect_spinning_top(candle: Dict) -> bool:
    """
    Detect Spinning Top pattern - small body with long shadows on both sides.
    Indicates indecision.
    """
    open_price = candle.get('open', 0)
    close_price = candle.get('close', 0)
    high_price = candle.get('high', 0)
    low_price = candle.get('low', 0)
    
    if not all([open_price, close_price, high_price, low_price]):
        return False
    
    body_size = abs(close_price - open_price)
    upper_shadow = high_price - max(open_price, close_price)
    lower_shadow = min(open_price, close_price) - low_price
    total_range = high_price - low_price
    
    if total_range == 0:
        return False
    
    body_ratio = body_size / total_range
    
    # Small body with significant shadows on both sides
    return (body_ratio < 0.3 and 
            upper_shadow > body_size * 1.5 and 
            lower_shadow > body_size * 1.5)


def detect_all_patterns(candles: List[Dict]) -> Dict:
    """
    Detect all candlestick patterns for the latest candles.
    
    Args:
        candles: List of candle dictionaries (should be sorted chronologically)
    
    Returns:
        Dictionary with detected patterns for each candle
    """
    if not candles or len(candles) < 2:
        return {}
    
    patterns = {}
    
    # Analyze latest candle (most recent)
    latest_candle = candles[-1]
    latest_patterns = []
    
    # Single candle patterns
    if detect_doji(latest_candle):
        latest_patterns.append("doji")
    
    if detect_hammer(latest_candle):
        latest_patterns.append("hammer")
    
    if detect_hanging_man(latest_candle):
        latest_patterns.append("hanging_man")
    
    if detect_shooting_star(latest_candle):
        latest_patterns.append("shooting_star")
    
    if detect_marubozu(latest_candle):
        latest_patterns.append("marubozu")
    
    if detect_spinning_top(latest_candle):
        latest_patterns.append("spinning_top")
    
    # Two-candle patterns (need previous candle)
    if len(candles) >= 2:
        previous_candle = candles[-2]
        
        if detect_bullish_engulfing(latest_candle, previous_candle):
            latest_patterns.append("bullish_engulfing")
        
        if detect_bearish_engulfing(latest_candle, previous_candle):
            latest_patterns.append("bearish_engulfing")
        
        if detect_bullish_harami(latest_candle, previous_candle):
            latest_patterns.append("bullish_harami")
        
        if detect_bearish_harami(latest_candle, previous_candle):
            latest_patterns.append("bearish_harami")
    
    patterns['latest'] = latest_patterns
    
    # Analyze previous candles for context
    if len(candles) >= 3:
        prev_patterns = []
        prev_candle = candles[-2]
        
        if detect_doji(prev_candle):
            prev_patterns.append("doji")
        if detect_hammer(prev_candle):
            prev_patterns.append("hammer")
        if detect_hanging_man(prev_candle):
            prev_patterns.append("hanging_man")
        if detect_shooting_star(prev_candle):
            prev_patterns.append("shooting_star")
        
        patterns['previous'] = prev_patterns
    
    return patterns


def get_pattern_sentiment(patterns: Dict) -> Tuple[str, float]:
    """
    Determine overall sentiment from detected patterns.
    
    Returns:
        Tuple of (sentiment, confidence) where sentiment is 'bullish', 'bearish', or 'neutral'
    """
    if not patterns or not patterns.get('latest'):
        return ('neutral', 0.0)
    
    latest_patterns = patterns['latest']
    
    bullish_patterns = ['hammer', 'bullish_engulfing', 'bullish_harami']
    bearish_patterns = ['hanging_man', 'shooting_star', 'bearish_engulfing', 'bearish_harami']
    neutral_patterns = ['doji', 'spinning_top']
    
    bullish_count = sum(1 for p in latest_patterns if p in bullish_patterns)
    bearish_count = sum(1 for p in latest_patterns if p in bearish_patterns)
    neutral_count = sum(1 for p in latest_patterns if p in neutral_patterns)
    
    if bullish_count > bearish_count:
        confidence = min(0.5 + (bullish_count * 0.15), 0.9)
        return ('bullish', confidence)
    elif bearish_count > bullish_count:
        confidence = min(0.5 + (bearish_count * 0.15), 0.9)
        return ('bearish', confidence)
    else:
        confidence = 0.3 if neutral_count > 0 else 0.5
        return ('neutral', confidence)


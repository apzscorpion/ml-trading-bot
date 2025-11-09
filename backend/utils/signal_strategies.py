"""
Signal generation strategies using multiple technical indicators.
Provides various trading strategies based on indicator combinations.
"""
from typing import Dict, Optional, List
import pandas as pd
import logging
from backend.utils.indicators import calculate_all_indicators

logger = logging.getLogger(__name__)


class SignalStrategy:
    """Base class for signal generation strategies"""
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None) -> Optional[Dict]:
        """
        Generate trading signal based on indicators.
        
        Args:
            candle: Current candle data
            indicators: Dictionary of indicator values
            index: Current candle index
        
        Returns:
            Signal dictionary with 'action' ('buy', 'sell', None) and metadata
        """
        raise NotImplementedError


class MultiIndicatorStrategy(SignalStrategy):
    """
    Multi-indicator strategy combining RSI, MACD, MA, Bollinger Bands, ADX, MFI.
    Uses multiple confirmations before generating signals.
    """
    
    def __init__(
        self,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        adx_threshold: float = 25,
        mfi_overbought: float = 80,
        mfi_oversold: float = 20,
        require_confirmation: bool = True
    ):
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.adx_threshold = adx_threshold
        self.mfi_overbought = mfi_overbought
        self.mfi_oversold = mfi_oversold
        self.require_confirmation = require_confirmation
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None) -> Optional[Dict]:
        """
        Generate signal using multiple indicators.
        
        BUY signals when:
        - RSI oversold (< 30) AND
        - MACD bullish crossover AND
        - Price below lower Bollinger Band AND
        - ADX > 25 (strong trend) AND
        - MFI oversold (< 20)
        
        SELL signals when:
        - RSI overbought (> 70) AND
        - MACD bearish crossover AND
        - Price above upper Bollinger Band AND
        - ADX > 25 AND
        - MFI overbought (> 80)
        """
        if not indicators:
            return None
        
        rsi = indicators.get('rsi_14')
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        macd_hist = indicators.get('macd_histogram')
        price = candle.get('close')
        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        adx = indicators.get('adx')
        mfi = indicators.get('mfi_14')
        sma_20 = indicators.get('sma_20')
        sma_50 = indicators.get('sma_50')
        
        # Check if we have enough data
        if any(x is None for x in [rsi, macd, macd_signal, price, bb_upper, bb_lower, adx, mfi]):
            return None
        
        buy_signals = 0
        sell_signals = 0
        reasons = []
        
        # RSI signals
        if rsi < 30:
            buy_signals += 1
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:
            sell_signals += 1
            reasons.append(f"RSI overbought ({rsi:.1f})")
        
        # MACD signals
        if macd_hist and macd_hist > 0 and macd > macd_signal:
            buy_signals += 1
            reasons.append("MACD bullish")
        elif macd_hist and macd_hist < 0 and macd < macd_signal:
            sell_signals += 1
            reasons.append("MACD bearish")
        
        # Bollinger Bands
        if price < bb_lower:
            buy_signals += 1
            reasons.append("Price below BB lower")
        elif price > bb_upper:
            sell_signals += 1
            reasons.append("Price above BB upper")
        
        # ADX (trend strength)
        if adx > 25:
            buy_signals += 0.5  # Half signal for trend strength
            sell_signals += 0.5
            reasons.append(f"Strong trend (ADX: {adx:.1f})")
        
        # MFI signals
        if mfi < 20:
            buy_signals += 1
            reasons.append(f"MFI oversold ({mfi:.1f})")
        elif mfi > 80:
            sell_signals += 1
            reasons.append(f"MFI overbought ({mfi:.1f})")
        
        # Moving Average crossover
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                buy_signals += 0.5
                reasons.append("Golden cross (SMA20 > SMA50)")
            elif sma_20 < sma_50:
                sell_signals += 0.5
                reasons.append("Death cross (SMA20 < SMA50)")
        
        # Require at least 3 confirmations for strong signal
        if buy_signals >= 3:
            return {
                "action": "buy",
                "confidence": min(buy_signals / 5.0, 1.0),  # Normalize to 0-1
                "signals_count": buy_signals,
                "reasons": reasons
            }
        elif sell_signals >= 3:
            return {
                "action": "sell",
                "confidence": min(sell_signals / 5.0, 1.0),
                "signals_count": sell_signals,
                "reasons": reasons
            }
        
        return None


class RSIStrategy(SignalStrategy):
    """Simple RSI-based strategy"""
    
    def __init__(self, overbought: float = 70, oversold: float = 30):
        self.overbought = overbought
        self.oversold = oversold
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None) -> Optional[Dict]:
        rsi = indicators.get('rsi_14')
        if rsi is None:
            return None
        
        if rsi < 30:
            return {
                "action": "buy",
                "confidence": (30 - rsi) / 30.0,  # More oversold = higher confidence
                "reasons": [f"RSI oversold ({rsi:.1f})"]
            }
        elif rsi > 70:
            return {
                "action": "sell",
                "confidence": (rsi - 70) / 30.0,
                "reasons": [f"RSI overbought ({rsi:.1f})"]
            }
        
        return None


class MACDCrossoverStrategy(SignalStrategy):
    """MACD crossover strategy"""
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None) -> Optional[Dict]:
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')
        macd_hist = indicators.get('macd_histogram')
        
        if any(x is None for x in [macd, macd_signal, macd_hist]):
            return None
        
        # Bullish crossover: MACD crosses above signal
        if macd_hist > 0 and macd > macd_signal:
            return {
                "action": "buy",
                "confidence": min(abs(macd_hist) / 10.0, 1.0),
                "reasons": ["MACD bullish crossover"]
            }
        # Bearish crossover: MACD crosses below signal
        elif macd_hist < 0 and macd < macd_signal:
            return {
                "action": "sell",
                "confidence": min(abs(macd_hist) / 10.0, 1.0),
                "reasons": ["MACD bearish crossover"]
            }
        
        return None


class BollingerBandsStrategy(SignalStrategy):
    """Bollinger Bands mean reversion strategy"""
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None) -> Optional[Dict]:
        price = candle.get('close')
        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        bb_middle = indicators.get('bb_middle')
        
        if any(x is None for x in [price, bb_upper, bb_lower, bb_middle]):
            return None
        
        # Buy when price touches lower band
        if price <= bb_lower:
            return {
                "action": "buy",
                "confidence": 0.7,
                "reasons": [f"Price at lower BB ({price:.2f} <= {bb_lower:.2f})"]
            }
        # Sell when price touches upper band
        elif price >= bb_upper:
            return {
                "action": "sell",
                "confidence": 0.7,
                "reasons": [f"Price at upper BB ({price:.2f} >= {bb_upper:.2f})"]
            }
        
        return None


class ADXTrendStrategy(SignalStrategy):
    """ADX-based trend following strategy"""
    
    def __init__(self, adx_threshold: float = 25):
        self.adx_threshold = adx_threshold
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None, adx_threshold: float = 25) -> Optional[Dict]:
        adx = indicators.get('adx')
        plus_di = indicators.get('adx_plus_di')
        minus_di = indicators.get('adx_minus_di')
        
        if any(x is None for x in [adx, plus_di, minus_di]):
            return None
        
        # Only trade when trend is strong (ADX > threshold)
        if adx < adx_threshold:
            return None
        
        # Buy when +DI > -DI (uptrend)
        if plus_di > minus_di:
            return {
                "action": "buy",
                "confidence": min(adx / 50.0, 1.0),  # Stronger trend = higher confidence
                "reasons": [f"Strong uptrend (ADX: {adx:.1f}, +DI: {plus_di:.1f} > -DI: {minus_di:.1f})"]
            }
        # Sell when -DI > +DI (downtrend)
        elif minus_di > plus_di:
            return {
                "action": "sell",
                "confidence": min(adx / 50.0, 1.0),
                "reasons": [f"Strong downtrend (ADX: {adx:.1f}, -DI: {minus_di:.1f} > +DI: {plus_di:.1f})"]
            }
        
        return None


class VWAPStrategy(SignalStrategy):
    """VWAP-based strategy - buy below VWAP, sell above"""
    
    @staticmethod
    def generate_signal(candle: Dict, indicators: Dict, index: int = None) -> Optional[Dict]:
        price = candle.get('close')
        vwap = indicators.get('vwap_intraday') or indicators.get('vwap')
        
        if price is None or vwap is None:
            return None
        
        # Buy when price is significantly below VWAP
        if price < vwap * 0.98:  # 2% below VWAP
            return {
                "action": "buy",
                "confidence": min((vwap - price) / vwap * 10, 1.0),
                "reasons": [f"Price below VWAP ({price:.2f} < {vwap:.2f})"]
            }
        # Sell when price is significantly above VWAP
        elif price > vwap * 1.02:  # 2% above VWAP
            return {
                "action": "sell",
                "confidence": min((price - vwap) / vwap * 10, 1.0),
                "reasons": [f"Price above VWAP ({price:.2f} > {vwap:.2f})"]
            }
        
        return None


def generate_signal_from_indicators(
    candle: Dict,
    candles: List[Dict],
    strategy: SignalStrategy = None,
    index: int = None
) -> Optional[Dict]:
    """
    Generate trading signal using all indicators.
    
    Args:
        candle: Current candle
        candles: List of all candles (for indicator calculation)
        strategy: Signal strategy to use (default: MultiIndicatorStrategy)
        index: Current candle index
    
    Returns:
        Signal dictionary or None
    """
    if not candles:
        return None
    
    # Calculate all indicators
    df = calculate_all_indicators(candles)
    
    if df.empty:
        return None
    
    # Get latest indicator values
    latest_idx = len(df) - 1 if index is None else min(index, len(df) - 1)
    latest = df.iloc[latest_idx]
    
    indicators = {}
    for col in df.columns:
        if col not in ['start_ts', 'open', 'high', 'low', 'close', 'volume']:
            value = latest[col]
            indicators[col] = float(value) if pd.notna(value) else None
    
    # Use default strategy if none provided
    if strategy is None:
        strategy = MultiIndicatorStrategy()
    
    # Generate signal
    return strategy.generate_signal(candle, indicators, index)


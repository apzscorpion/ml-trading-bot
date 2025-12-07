"""
Technical indicator calculations using pandas-ta.
"""
import pandas as pd
import sys
from unittest.mock import MagicMock

# Mock numba for Python 3.14 compatibility (pandas_ta requires it)
try:
    import numba
except ImportError:
    numba = MagicMock()
    
    def njit(arg=None, **kwargs):
        if callable(arg):
            return arg
        def wrapper(func):
            return func
        return wrapper
        
    numba.njit = njit
    numba.jit = njit
    sys.modules['numba'] = numba

import pandas_ta as ta
import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index)"""
    return ta.rsi(df['close'], length=period)


def calculate_macd(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Returns:
        Dictionary with 'macd', 'signal', and 'histogram' series
    """
    macd_result = ta.macd(df['close'], fast=12, slow=26, signal=9)
    
    if macd_result is None or macd_result.empty:
        return {
            'macd': pd.Series(dtype=float),
            'signal': pd.Series(dtype=float),
            'histogram': pd.Series(dtype=float)
        }
    
    return {
        'macd': macd_result[f'MACD_12_26_9'],
        'signal': macd_result[f'MACDs_12_26_9'],
        'histogram': macd_result[f'MACDh_12_26_9']
    }


def calculate_moving_averages(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate various moving averages.
    
    Returns:
        Dictionary with SMA and EMA series
    """
    return {
        'sma_20': ta.sma(df['close'], length=20),
        'sma_50': ta.sma(df['close'], length=50),
        'ema_21': ta.ema(df['close'], length=21),
        'ema_9': ta.ema(df['close'], length=9)
    }


def calculate_bollinger_bands(df: pd.DataFrame, length: int = 20, std: float = 2) -> Dict[str, pd.Series]:
    """
    Calculate Bollinger Bands.
    
    Returns:
        Dictionary with 'upper', 'middle', and 'lower' bands
    """
    bb = ta.bbands(df['close'], length=length, std=std)
    
    if bb is None or bb.empty:
        return {
            'upper': pd.Series(dtype=float),
            'middle': pd.Series(dtype=float),
            'lower': pd.Series(dtype=float)
        }
    
    # Try different possible column names from pandas-ta
    # pandas-ta may return different column names based on version
    possible_upper_names = [
        f'BBU_{length}_{std}.0',
        f'BBU_{length}_{std}',
        f'BBU_{length}_{int(std)}',
        'BBU_20_2.0'
    ]
    possible_middle_names = [
        f'BBM_{length}_{std}.0',
        f'BBM_{length}_{std}',
        f'BBM_{length}_{int(std)}',
        'BBM_20_2.0'
    ]
    possible_lower_names = [
        f'BBL_{length}_{std}.0',
        f'BBL_{length}_{std}',
        f'BBL_{length}_{int(std)}',
        'BBL_20_2.0'
    ]
    
    # Find the actual column names
    upper_col = None
    middle_col = None
    lower_col = None
    
    for name in possible_upper_names:
        if name in bb.columns:
            upper_col = name
            break
    
    for name in possible_middle_names:
        if name in bb.columns:
            middle_col = name
            break
    
    for name in possible_lower_names:
        if name in bb.columns:
            lower_col = name
            break
    
    # If we still can't find, try to find any column starting with BBU, BBM, BBL
    if not upper_col:
        for col in bb.columns:
            if col.startswith('BBU'):
                upper_col = col
                break
    if not middle_col:
        for col in bb.columns:
            if col.startswith('BBM'):
                middle_col = col
                break
    if not lower_col:
        for col in bb.columns:
            if col.startswith('BBL'):
                lower_col = col
                break
    
    # If still not found, return empty series to avoid KeyError
    if not upper_col or not middle_col or not lower_col:
        logger.warning(f"Could not find Bollinger Band columns. Available columns: {list(bb.columns)}")
        return {
            'upper': pd.Series(dtype=float),
            'middle': pd.Series(dtype=float),
            'lower': pd.Series(dtype=float)
        }
    
    return {
        'upper': bb[upper_col] if upper_col else pd.Series(dtype=float),
        'middle': bb[middle_col] if middle_col else pd.Series(dtype=float),
        'lower': bb[lower_col] if lower_col else pd.Series(dtype=float)
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR (Average True Range)"""
    return ta.atr(df['high'], df['low'], df['close'], length=period)


def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
    """
    Calculate Stochastic Oscillator.
    
    Returns:
        Dictionary with '%K' and '%D' series
    """
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=k_period, d=d_period)
    
    if stoch is None or stoch.empty:
        return {
            'k': pd.Series(dtype=float),
            'd': pd.Series(dtype=float)
        }
    
    return {
        'k': stoch[f'STOCHk_{k_period}_{d_period}_3'],
        'd': stoch[f'STOCHd_{k_period}_{d_period}_3']
    }


def calculate_stochastic_rsi(df: pd.DataFrame, rsi_period: int = 14, stoch_period: int = 14, k_period: int = 3, d_period: int = 3) -> Dict[str, pd.Series]:
    """
    Calculate Stochastic RSI (StochRSI).
    
    Stochastic RSI applies Stochastic Oscillator formula to RSI values instead of price.
    This makes it more sensitive to overbought/oversold conditions.
    
    Args:
        df: DataFrame with OHLCV data
        rsi_period: Period for RSI calculation (default: 14)
        stoch_period: Period for Stochastic calculation on RSI (default: 14)
        k_period: Period for %K smoothing (default: 3)
        d_period: Period for %D smoothing (default: 3)
    
    Returns:
        Dictionary with 'stoch_rsi_k' and 'stoch_rsi_d' series (0-100 range)
    """
    try:
        # First calculate RSI
        rsi = calculate_rsi(df, period=rsi_period)
        
        # Remove NaN values for calculation
        rsi_clean = rsi.dropna()
        
        if len(rsi_clean) < stoch_period + k_period:
            return {
                'stoch_rsi_k': pd.Series(dtype=float, index=rsi.index),
                'stoch_rsi_d': pd.Series(dtype=float, index=rsi.index)
            }
        
        # Apply Stochastic formula to RSI values
        # %K = (RSI - Lowest RSI in period) / (Highest RSI in period - Lowest RSI in period) * 100
        stoch_rsi_k = pd.Series(index=rsi.index, dtype=float)
        stoch_rsi_d = pd.Series(index=rsi.index, dtype=float)
        
        for i in range(stoch_period - 1, len(rsi)):
            rsi_window = rsi.iloc[i - stoch_period + 1:i + 1]
            rsi_window_clean = rsi_window.dropna()
            
            if len(rsi_window_clean) < 2:
                continue
            
            lowest_rsi = rsi_window_clean.min()
            highest_rsi = rsi_window_clean.max()
            current_rsi = rsi.iloc[i]
            
            if pd.notna(current_rsi) and (highest_rsi - lowest_rsi) > 0:
                stoch_rsi_k.iloc[i] = ((current_rsi - lowest_rsi) / (highest_rsi - lowest_rsi)) * 100
            else:
                stoch_rsi_k.iloc[i] = 50.0  # Neutral value
        
        # Smooth %K to get %D (moving average of %K)
        stoch_rsi_d = stoch_rsi_k.rolling(window=k_period).mean()
        
        # Smooth %D further if d_period > 1
        if d_period > 1:
            stoch_rsi_d = stoch_rsi_d.rolling(window=d_period).mean()
        
        return {
            'stoch_rsi_k': stoch_rsi_k,
            'stoch_rsi_d': stoch_rsi_d
        }
    except Exception as e:
        logger.error(f"Error calculating Stochastic RSI: {e}")
        return {
            'stoch_rsi_k': pd.Series(dtype=float, index=df.index if hasattr(df, 'index') else pd.RangeIndex(len(df))),
            'stoch_rsi_d': pd.Series(dtype=float, index=df.index if hasattr(df, 'index') else pd.RangeIndex(len(df)))
        }


def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
    """
    Calculate ADX (Average Directional Index) and related indicators.
    
    Returns:
        Dictionary with 'adx', '+di', and '-di' series
    """
    adx_result = ta.adx(df['high'], df['low'], df['close'], length=period)
    
    if adx_result is None or adx_result.empty:
        return {
            'adx': pd.Series(dtype=float),
            'plus_di': pd.Series(dtype=float),
            'minus_di': pd.Series(dtype=float)
        }
    
    return {
        'adx': adx_result[f'ADX_{period}'],
        'plus_di': adx_result[f'DMP_{period}'],
        'minus_di': adx_result[f'DMN_{period}']
    }


def calculate_mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate MFI (Money Flow Index) - volume-weighted RSI.
    
    Returns:
        MFI series (0-100)
    """
    return ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=period)


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """
    Calculate OBV (On-Balance Volume).
    
    Returns:
        OBV series
    """
    return ta.obv(df['close'], df['volume'])


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate VWAP (Volume-Weighted Average Price).
    Typically calculated per day, but can be rolling.
    
    Returns:
        VWAP series
    """
    # pandas-ta doesn't have VWAP, so we'll calculate it manually
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return vwap


def calculate_vwap_intraday(df: pd.DataFrame, time_column: str = 'start_ts') -> pd.Series:
    """
    Calculate VWAP resetting daily (true intraday VWAP).
    
    Args:
        df: DataFrame with OHLCV data
        time_column: Column name for timestamp
    
    Returns:
        Intraday VWAP series
    """
    if time_column not in df.columns:
        # Fallback to rolling VWAP
        return calculate_vwap(df)
    
    df = df.copy()
    df['date'] = pd.to_datetime(df[time_column]).dt.date
    
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = typical_price * df['volume']
    
    # Group by date and calculate cumulative VWAP per day
    df['vwap'] = df.groupby('date')['pv'].cumsum() / df.groupby('date')['volume'].cumsum()
    
    return df['vwap']


def calculate_all_indicators(candles: List[Dict]) -> pd.DataFrame:
    """
    Calculate all indicators for a list of candles.
    
    Args:
        candles: List of candle dictionaries with OHLCV data
    
    Returns:
        DataFrame with all indicators added
    """
    if not candles:
        return pd.DataFrame()
    
    # Convert to DataFrame
    df = pd.DataFrame(candles)
    
    # Ensure proper column names
    df.columns = [col.lower() for col in df.columns]
    
    # Calculate indicators
    try:
        df['rsi_14'] = calculate_rsi(df, period=14)
        
        macd = calculate_macd(df)
        df['macd'] = macd['macd']
        df['macd_signal'] = macd['signal']
        df['macd_histogram'] = macd['histogram']
        
        mas = calculate_moving_averages(df)
        df['sma_20'] = mas['sma_20']
        df['sma_50'] = mas['sma_50']
        df['ema_21'] = mas['ema_21']
        df['ema_9'] = mas['ema_9']
        
        bb = calculate_bollinger_bands(df)
        df['bb_upper'] = bb['upper']
        df['bb_middle'] = bb['middle']
        df['bb_lower'] = bb['lower']
        
        df['atr_14'] = calculate_atr(df, period=14)
        
        stoch = calculate_stochastic(df)
        df['stoch_k'] = stoch['k']
        df['stoch_d'] = stoch['d']
        
        # Stochastic RSI
        stoch_rsi = calculate_stochastic_rsi(df, rsi_period=14, stoch_period=14, k_period=3, d_period=3)
        df['stoch_rsi_k'] = stoch_rsi['stoch_rsi_k']
        df['stoch_rsi_d'] = stoch_rsi['stoch_rsi_d']
        
        # ADX (Average Directional Index)
        adx = calculate_adx(df)
        df['adx'] = adx['adx']
        df['adx_plus_di'] = adx['plus_di']
        df['adx_minus_di'] = adx['minus_di']
        
        # MFI (Money Flow Index)
        df['mfi_14'] = calculate_mfi(df, period=14)
        
        # OBV (On-Balance Volume)
        df['obv'] = calculate_obv(df)
        
        # VWAP (Volume-Weighted Average Price)
        df['vwap'] = calculate_vwap(df)
        
        # Intraday VWAP (resets daily)
        if 'start_ts' in df.columns:
            df['vwap_intraday'] = calculate_vwap_intraday(df)
        else:
            df['vwap_intraday'] = df['vwap']
        
        logger.debug(f"Calculated indicators for {len(df)} candles")
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
    
    return df



def get_latest_indicators(df: pd.DataFrame) -> Dict:
    """
    Get the latest values of all indicators.
    
    Args:
        df: DataFrame with calculated indicators
    
    Returns:
        Dictionary with latest indicator values
    """
    if df.empty:
        return {}
    
    latest = df.iloc[-1]
    
    indicators = {}
    for col in df.columns:
        if col not in ['start_ts', 'open', 'high', 'low', 'close', 'volume']:
            value = latest[col]
            indicators[col] = float(value) if pd.notna(value) else None
    
    return indicators


def calculate_ichimoku(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate Ichimoku Cloud components.
    
    Returns:
        Dictionary with Tenkan, Kijun, Span A, Span B, Chikou
    """
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
    high_9 = df['high'].rolling(window=9).max()
    low_9 = df['low'].rolling(window=9).min()
    tenkan_sen = (high_9 + low_9) / 2

    # Kijun-sen (Base Line): (26-period high + 26-period low)/2
    high_26 = df['high'].rolling(window=26).max()
    low_26 = df['low'].rolling(window=26).min()
    kijun_sen = (high_26 + low_26) / 2

    # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

    # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
    high_52 = df['high'].rolling(window=52).max()
    low_52 = df['low'].rolling(window=52).min()
    senkou_span_b = ((high_52 + low_52) / 2).shift(26)

    # Chikou Span (Lagging Span): Close shifted back 26 periods
    chikou_span = df['close'].shift(-26)

    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


def calculate_cci(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Calculate Commodity Channel Index (CCI)"""
    return ta.cci(df['high'], df['low'], df['close'], length=length)


def calculate_williams_r(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Calculate Williams %R"""
    return ta.willr(df['high'], df['low'], df['close'], length=length)


def calculate_psar(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Calculate Parabolic SAR.
    
    Returns:
        Dictionary with 'psar' (value) and 'psar_direction' (1 for long, -1 for short)
    """
    # pandas-ta psar returns columns like PSARl_0.02_0.2, PSARs_0.02_0.2, PSARaf_0.02_0.2, PSARr_0.02_0.2
    psar = ta.psar(df['high'], df['low'], df['close'])
    
    if psar is None or psar.empty:
        return {
            'psar': pd.Series(dtype=float),
            'psar_direction': pd.Series(dtype=float)
        }
        
    # Find the columns (names can vary)
    # Usually: PSARl (long), PSARs (short), PSARaf (acceleration), PSARr (reversal)
    # We want a combined series
    
    # Combine long and short into one series
    # If PSARl is NaN, use PSARs, and vice versa
    long_col = [c for c in psar.columns if c.startswith('PSARl')][0]
    short_col = [c for c in psar.columns if c.startswith('PSARs')][0]
    
    combined_psar = psar[long_col].fillna(psar[short_col])
    
    # Direction: 1 if close > psar, -1 if close < psar
    direction = np.where(df['close'] > combined_psar, 1.0, -1.0)
    
    return {
        'psar': combined_psar,
        'psar_direction': pd.Series(direction, index=df.index)
    }


def calculate_keltner_channels(df: pd.DataFrame, length: int = 20, mult: float = 2.0) -> Dict[str, pd.Series]:
    """
    Calculate Keltner Channels.
    
    Returns:
        Dictionary with 'upper', 'middle', 'lower'
    """
    kc = ta.kc(df['high'], df['low'], df['close'], length=length, scalar=mult)
    
    if kc is None or kc.empty:
        return {
            'upper': pd.Series(dtype=float),
            'middle': pd.Series(dtype=float),
            'lower': pd.Series(dtype=float)
        }
        
    # Column names usually: KCLe_20_2, KCBe_20_2, KCUe_20_2 (Lower, Basis, Upper)
    lower_col = [c for c in kc.columns if c.startswith('KCL')][0]
    basis_col = [c for c in kc.columns if c.startswith('KCB')][0]
    upper_col = [c for c in kc.columns if c.startswith('KCU')][0]
    
    return {
        'upper': kc[upper_col],
        'middle': kc[basis_col],
        'lower': kc[lower_col]
    }



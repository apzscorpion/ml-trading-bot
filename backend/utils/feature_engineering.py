"""
Comprehensive feature engineering module for ML models.
All bots should use this module to ensure consistent feature sets including:
- Technical indicators (RSI, MACD, Stochastic RSI, Bollinger Bands, etc.)
- Volume-based indicators (OBV, MFI, Volume Profile, etc.)
- Price features (OHLC, returns, volatility, momentum)
- Volume features (volume MA, volume ratios, volume trends)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

from backend.utils.indicators import (
    calculate_all_indicators,
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_stochastic,
    calculate_stochastic_rsi,
    calculate_adx,
    calculate_mfi,
    calculate_obv,
    calculate_obv,
    calculate_vwap_intraday,
    calculate_ichimoku,
    calculate_cci,
    calculate_williams_r,
    calculate_psar,
    calculate_keltner_channels
)

logger = logging.getLogger(__name__)


def engineer_comprehensive_features(
    df: pd.DataFrame,
    include_indicators: bool = True,
    include_volume_features: bool = True,
    include_price_features: bool = True,
    include_returns_features: bool = True
) -> pd.DataFrame:
    """
    Engineer comprehensive features for ML models.
    
    This function creates a complete feature set including:
    1. Technical indicators (RSI, MACD, Stochastic RSI, Bollinger Bands, ADX, ATR)
    2. Volume-based indicators (OBV, MFI, VWAP, Volume MA ratios)
    3. Price features (OHLC, moving averages, momentum)
    4. Returns and volatility features
    
    Args:
        df: DataFrame with OHLCV data (must have columns: open, high, low, close, volume)
        include_indicators: Whether to include technical indicators
        include_volume_features: Whether to include volume-based features
        include_price_features: Whether to include price-based features
        include_returns_features: Whether to include returns and volatility features
    
    Returns:
        DataFrame with all engineered features
    """
    if df.empty:
        return df
    
    # Ensure we have required columns
    required_cols = ['open', 'high', 'low', 'close']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.warning(f"Missing required columns: {missing_cols}. Using defaults.")
        for col in missing_cols:
            df[col] = df.get('close', 0) if col != 'close' else 0
    
    # Ensure volume column exists
    if 'volume' not in df.columns:
        logger.warning("Volume column missing. Using zeros.")
        df['volume'] = 0
    
    features_df = df.copy()
    
    # 1. Technical Indicators
    if include_indicators:
        try:
            # Calculate all indicators at once (most efficient)
            indicators_df = calculate_all_indicators(df.to_dict('records'))
            
            # Merge indicators into features
            indicator_cols = [
                'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
                'sma_20', 'sma_50', 'ema_21', 'ema_9',
                'bb_upper', 'bb_middle', 'bb_lower',
                'atr_14', 'stoch_k', 'stoch_d',
                'stoch_rsi_k', 'stoch_rsi_d',
                'adx', 'adx_plus_di', 'adx_minus_di',
                'mfi_14', 'obv', 'vwap', 'vwap_intraday'
            ]
            
            for col in indicator_cols:
                if col in indicators_df.columns:
                    features_df[col] = indicators_df[col]
                else:
                    features_df[col] = np.nan
            
            # Add indicator-based features
            # RSI position relative to overbought/oversold
            features_df['rsi_overbought'] = (features_df['rsi_14'] > 70).astype(float)
            features_df['rsi_oversold'] = (features_df['rsi_14'] < 30).astype(float)
            
            # MACD signal crossovers
            features_df['macd_bullish'] = (features_df['macd'] > features_df['macd_signal']).astype(float)
            features_df['macd_bearish'] = (features_df['macd'] < features_df['macd_signal']).astype(float)
            
            # Bollinger Band position
            if 'bb_upper' in features_df.columns and 'bb_lower' in features_df.columns:
                bb_width = features_df['bb_upper'] - features_df['bb_lower']
                features_df['bb_position'] = (features_df['close'] - features_df['bb_lower']) / (bb_width + 1e-10)
                features_df['bb_squeeze'] = (bb_width < bb_width.rolling(20).mean() * 0.8).astype(float)
            
            # Stochastic RSI signals
            if 'stoch_rsi_k' in features_df.columns:
                features_df['stoch_rsi_overbought'] = (features_df['stoch_rsi_k'] > 80).astype(float)
                features_df['stoch_rsi_oversold'] = (features_df['stoch_rsi_k'] < 20).astype(float)
            
            # Ichimoku Cloud
            ichimoku = calculate_ichimoku(df)
            features_df['ichimoku_conversion_line'] = ichimoku['tenkan_sen']
            features_df['ichimoku_base_line'] = ichimoku['kijun_sen']
            features_df['ichimoku_leading_span_a'] = ichimoku['senkou_span_a']
            features_df['ichimoku_leading_span_b'] = ichimoku['senkou_span_b']
            
            # CCI
            features_df['cci'] = calculate_cci(df)
            
            # Williams %R
            features_df['williams_r'] = calculate_williams_r(df)
            
            # Parabolic SAR
            psar = calculate_psar(df)
            features_df['psar'] = psar['psar']
            features_df['psar_direction'] = psar['psar_direction']
            
            # Keltner Channels
            kc = calculate_keltner_channels(df)
            features_df['kc_upper'] = kc['upper']
            features_df['kc_lower'] = kc['lower']
            features_df['kc_middle'] = kc['middle']
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
    
    # 2. Volume Features
    if include_volume_features and 'volume' in df.columns:
        try:
            # Volume moving averages
            features_df['volume_ma_5'] = df['volume'].rolling(5).mean()
            features_df['volume_ma_10'] = df['volume'].rolling(10).mean()
            features_df['volume_ma_20'] = df['volume'].rolling(20).mean()
            
            # Volume ratios
            features_df['volume_ratio_5'] = df['volume'] / (features_df['volume_ma_5'] + 1e-10)
            features_df['volume_ratio_20'] = df['volume'] / (features_df['volume_ma_20'] + 1e-10)
            
            # Volume trend
            features_df['volume_trend'] = (features_df['volume_ma_5'] > features_df['volume_ma_20']).astype(float)
            
            # Volume-weighted features (if VWAP available)
            if 'vwap' in features_df.columns:
                features_df['price_vwap_diff'] = (df['close'] - features_df['vwap']) / (features_df['vwap'] + 1e-10)
                features_df['price_vwap_ratio'] = df['close'] / (features_df['vwap'] + 1e-10)
            
            # OBV trend (if OBV available)
            if 'obv' in features_df.columns:
                features_df['obv_trend'] = (features_df['obv'] > features_df['obv'].shift(1)).astype(float)
                features_df['obv_ma_10'] = features_df['obv'].rolling(10).mean()
                features_df['obv_ratio'] = features_df['obv'] / (features_df['obv_ma_10'] + 1e-10)
            
            # MFI signals (if MFI available)
            if 'mfi_14' in features_df.columns:
                features_df['mfi_overbought'] = (features_df['mfi_14'] > 80).astype(float)
                features_df['mfi_oversold'] = (features_df['mfi_14'] < 20).astype(float)
            
        except Exception as e:
            logger.error(f"Error calculating volume features: {e}")
    
    # 3. Price Features
    if include_price_features:
        try:
            # Moving averages
            features_df['sma_5'] = df['close'].rolling(5).mean()
            features_df['sma_10'] = df['close'].rolling(10).mean()
            features_df['ema_5'] = df['close'].ewm(span=5).mean()
            features_df['ema_10'] = df['close'].ewm(span=10).mean()
            
            # Price position relative to MAs
            features_df['price_sma5_ratio'] = df['close'] / (features_df['sma_5'] + 1e-10)
            features_df['price_sma20_ratio'] = df['close'] / (features_df.get('sma_20', df['close']) + 1e-10)
            
            # High-Low range
            features_df['hl_range'] = (df['high'] - df['low']) / (df['close'] + 1e-10)
            features_df['hl_range_ma'] = features_df['hl_range'].rolling(10).mean()
            
            # Body size (open-close)
            features_df['body_size'] = abs(df['close'] - df['open']) / (df['close'] + 1e-10)
            features_df['body_size_ma'] = features_df['body_size'].rolling(10).mean()
            
            # Upper/Lower wick ratios
            features_df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / (df['close'] + 1e-10)
            features_df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / (df['close'] + 1e-10)
            
            # Momentum
            features_df['momentum_5'] = df['close'] - df['close'].shift(5)
            features_df['momentum_10'] = df['close'] - df['close'].shift(10)
            features_df['momentum_20'] = df['close'] - df['close'].shift(20)
            
            # Rate of change
            features_df['roc_5'] = ((df['close'] - df['close'].shift(5)) / df['close'].shift(5)) * 100
            features_df['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
            
        except Exception as e:
            logger.error(f"Error calculating price features: {e}")
    
    # 4. Returns and Volatility Features
    if include_returns_features:
        try:
            # Returns
            features_df['returns_1'] = df['close'].pct_change(1)
            features_df['returns_5'] = df['close'].pct_change(5)
            features_df['returns_10'] = df['close'].pct_change(10)
            
            # Volatility (rolling std of returns)
            features_df['volatility_5'] = features_df['returns_1'].rolling(5).std()
            features_df['volatility_10'] = features_df['returns_1'].rolling(10).std()
            features_df['volatility_20'] = features_df['returns_1'].rolling(20).std()
            
            # Volatility ratio (current vs historical)
            features_df['volatility_ratio'] = features_df['volatility_5'] / (features_df['volatility_20'] + 1e-10)
            
            # ATR-based volatility (if ATR available)
            if 'atr_14' in features_df.columns:
                features_df['atr_ratio'] = features_df['atr_14'] / (df['close'] + 1e-10)
                features_df['atr_trend'] = (features_df['atr_14'] > features_df['atr_14'].shift(1)).astype(float)
            
        except Exception as e:
            logger.error(f"Error calculating returns/volatility features: {e}")
    
    # Fill NaN values with forward fill, then backward fill, then 0
    features_df = features_df.ffill().bfill().fillna(0)
    
    # Replace infinite values
    features_df = features_df.replace([np.inf, -np.inf], 0)
    
    return features_df


def get_feature_columns(
    include_indicators: bool = True,
    include_volume_features: bool = True,
    include_price_features: bool = True,
    include_returns_features: bool = True
) -> List[str]:
    """
    Get list of feature column names that will be generated.
    
    Useful for:
    - Model initialization (knowing input dimensions)
    - Feature selection
    - Debugging
    
    Returns:
        List of feature column names
    """
    base_cols = ['open', 'high', 'low', 'close', 'volume']
    feature_cols = []
    
    if include_indicators:
        feature_cols.extend([
            'rsi_14', 'macd', 'macd_signal', 'macd_histogram',
            'sma_20', 'sma_50', 'ema_21', 'ema_9',
            'bb_upper', 'bb_middle', 'bb_lower',
            'atr_14', 'stoch_k', 'stoch_d',
            'stoch_rsi_k', 'stoch_rsi_d',
            'adx', 'adx_plus_di', 'adx_minus_di',
            'mfi_14', 'obv', 'vwap', 'vwap_intraday',
            'rsi_overbought', 'rsi_oversold',
            'macd_bullish', 'macd_bearish',
            'bb_position', 'bb_squeeze',
            'stoch_rsi_overbought', 'stoch_rsi_oversold',
            'ichimoku_conversion_line', 'ichimoku_base_line',
            'ichimoku_leading_span_a', 'ichimoku_leading_span_b',
            'cci', 'williams_r', 'psar', 'psar_direction',
            'kc_upper', 'kc_lower', 'kc_middle'
        ])
    
    if include_volume_features:
        feature_cols.extend([
            'volume_ma_5', 'volume_ma_10', 'volume_ma_20',
            'volume_ratio_5', 'volume_ratio_20',
            'volume_trend', 'price_vwap_diff', 'price_vwap_ratio',
            'obv_trend', 'obv_ma_10', 'obv_ratio',
            'mfi_overbought', 'mfi_oversold'
        ])
    
    if include_price_features:
        feature_cols.extend([
            'sma_5', 'sma_10', 'ema_5', 'ema_10',
            'price_sma5_ratio', 'price_sma20_ratio',
            'hl_range', 'hl_range_ma',
            'body_size', 'body_size_ma',
            'upper_wick', 'lower_wick',
            'momentum_5', 'momentum_10', 'momentum_20',
            'roc_5', 'roc_10'
        ])
    
    if include_returns_features:
        feature_cols.extend([
            'returns_1', 'returns_5', 'returns_10',
            'volatility_5', 'volatility_10', 'volatility_20',
            'volatility_ratio', 'atr_ratio', 'atr_trend'
        ])
    
    return base_cols + feature_cols


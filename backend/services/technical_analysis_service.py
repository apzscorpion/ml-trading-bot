"""
Technical Analysis Service - Pure TA computation on raw candles only.
Completely isolated from ML predictions and caches.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from backend.database import SessionLocal, Candle
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalAnalysisService:
    """Pure technical analysis service - never uses ML predictions"""
    
    def __init__(self):
        self.min_days_required = 60
        self.default_window_days = 90
    
    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        window_days: Optional[int] = None
    ) -> Dict:
        """
        Run pure technical analysis on raw candles.
        
        Args:
            symbol: Stock symbol
            timeframe: Candle timeframe (5m, 15m, 1h, 1d, etc)
            window_days: Days of historical data to analyze (default: 90)
        
        Returns:
            Dict with TA indicators, signals, and metadata
        """
        window_days = window_days or self.default_window_days
        
        # Fetch raw candles directly from database
        candles = self._fetch_raw_candles(symbol, timeframe, window_days)
        
        if len(candles) < self.min_days_required:
            logger.error(
                f"Insufficient data for TA analysis: {len(candles)} candles, need ≥{self.min_days_required} days"
            )
            return {
                "error": "insufficient_data",
                "message": f"Need at least {self.min_days_required} days of data for technical analysis",
                "candles_found": len(candles)
            }
        
        df = pd.DataFrame(candles)
        
        # Compute all TA indicators
        indicators = self._compute_indicators(df)
        
        # Generate signals
        signals = self._generate_signals(indicators)
        
        # Calculate overall recommendation
        recommendation = self._compute_recommendation(signals, indicators)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "analyzed_at": datetime.utcnow().isoformat(),
            "data_window_days": window_days,
            "candles_analyzed": len(df),
            "indicators": indicators,
            "signals": signals,
            "recommendation": recommendation,
            "mode": "technical_analysis_only"
        }
    
    def _fetch_raw_candles(self, symbol: str, timeframe: str, days: int) -> List[Dict]:
        """Fetch raw candles from database, fallback to data fetcher if needed"""
        db = SessionLocal()
        try:
            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Query database
            candles = db.query(Candle).filter(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe,
                Candle.start_ts >= cutoff
            ).order_by(Candle.start_ts.asc()).all()
            
            if not candles:
                logger.warning(f"No candles found in DB for {symbol}/{timeframe}, fetching from Yahoo")
                # Fallback to Yahoo Finance
                from backend.utils.data_fetcher import data_fetcher
                import asyncio
                
                # Map timeframe to period
                period_map = {
                    "1m": "5d", "5m": "60d", "15m": "60d", "1h": "730d",
                    "4h": "730d", "1d": "2000d", "1wk": "max", "1mo": "max"
                }
                period = period_map.get(timeframe, "60d")
                
                # Fetch asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                fetched = loop.run_until_complete(
                    data_fetcher.fetch_candles(symbol, timeframe, period)
                )
                loop.close()
                
                return fetched if fetched else []
            
            return [c.to_dict() for c in candles]
            
        finally:
            db.close()
    
    def _compute_indicators(self, df: pd.DataFrame) -> Dict:
        """Compute all technical indicators"""
        indicators = {}
        
        # Price data
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        # Moving Averages
        indicators['sma_20'] = float(close.rolling(20).mean().iloc[-1])
        indicators['sma_50'] = float(close.rolling(50).mean().iloc[-1])
        indicators['ema_12'] = float(close.ewm(span=12).mean().iloc[-1])
        indicators['ema_26'] = float(close.ewm(span=26).mean().iloc[-1])
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        indicators['rsi'] = float(rsi.iloc[-1])
        
        # MACD
        macd_line = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line
        indicators['macd'] = float(macd_line.iloc[-1])
        indicators['macd_signal'] = float(signal_line.iloc[-1])
        indicators['macd_histogram'] = float(histogram.iloc[-1])
        
        # Bollinger Bands
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        indicators['bb_upper'] = float((sma_20 + 2 * std_20).iloc[-1])
        indicators['bb_middle'] = float(sma_20.iloc[-1])
        indicators['bb_lower'] = float((sma_20 - 2 * std_20).iloc[-1])
        indicators['bb_width'] = float((indicators['bb_upper'] - indicators['bb_lower']) / indicators['bb_middle'])
        
        # ATR (Average True Range)
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        indicators['atr'] = float(true_range.rolling(14).mean().iloc[-1])
        
        # Volume indicators
        indicators['volume_sma_20'] = float(volume.rolling(20).mean().iloc[-1])
        indicators['volume_ratio'] = float(volume.iloc[-1] / indicators['volume_sma_20'])
        
        # Current price
        indicators['current_price'] = float(close.iloc[-1])
        
        # Price change
        indicators['price_change_pct'] = float(((close.iloc[-1] - close.iloc[0]) / close.iloc[0]) * 100)
        
        return indicators
    
    def _generate_signals(self, indicators: Dict) -> Dict:
        """Generate trading signals from indicators"""
        signals = {}
        
        # RSI signals
        rsi = indicators['rsi']
        if rsi > 70:
            signals['rsi'] = {"signal": "overbought", "strength": min((rsi - 70) / 30, 1.0)}
        elif rsi < 30:
            signals['rsi'] = {"signal": "oversold", "strength": min((30 - rsi) / 30, 1.0)}
        else:
            signals['rsi'] = {"signal": "neutral", "strength": 0.0}
        
        # MACD signals
        macd = indicators['macd']
        macd_signal = indicators['macd_signal']
        macd_hist = indicators['macd_histogram']
        
        if macd > macd_signal and macd_hist > 0:
            signals['macd'] = {"signal": "bullish", "strength": min(abs(macd_hist) / abs(macd_signal + 0.01), 1.0)}
        elif macd < macd_signal and macd_hist < 0:
            signals['macd'] = {"signal": "bearish", "strength": min(abs(macd_hist) / abs(macd_signal + 0.01), 1.0)}
        else:
            signals['macd'] = {"signal": "neutral", "strength": 0.0}
        
        # MA signals
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        current_price = indicators['current_price']
        
        if sma_20 > sma_50 and current_price > sma_20:
            signals['ma'] = {"signal": "bullish", "strength": 0.7}
        elif sma_20 < sma_50 and current_price < sma_20:
            signals['ma'] = {"signal": "bearish", "strength": 0.7}
        else:
            signals['ma'] = {"signal": "neutral", "strength": 0.3}
        
        # Bollinger Band signals
        bb_upper = indicators['bb_upper']
        bb_lower = indicators['bb_lower']
        bb_middle = indicators['bb_middle']
        
        if current_price >= bb_upper:
            signals['bollinger'] = {"signal": "overbought", "strength": 0.8}
        elif current_price <= bb_lower:
            signals['bollinger'] = {"signal": "oversold", "strength": 0.8}
        elif current_price > bb_middle:
            signals['bollinger'] = {"signal": "bullish", "strength": 0.4}
        else:
            signals['bollinger'] = {"signal": "bearish", "strength": 0.4}
        
        # Volume signal
        if indicators['volume_ratio'] > 1.5:
            signals['volume'] = {"signal": "high_volume", "strength": min((indicators['volume_ratio'] - 1.0) / 2.0, 1.0)}
        elif indicators['volume_ratio'] < 0.5:
            signals['volume'] = {"signal": "low_volume", "strength": min((1.0 - indicators['volume_ratio']) / 0.5, 1.0)}
        else:
            signals['volume'] = {"signal": "normal", "strength": 0.0}
        
        return signals
    
    def _compute_recommendation(self, signals: Dict, indicators: Dict) -> Dict:
        """Compute overall recommendation from signals"""
        # Score signals
        bullish_score = 0.0
        bearish_score = 0.0
        
        # RSI
        if signals['rsi']['signal'] == 'oversold':
            bullish_score += signals['rsi']['strength'] * 0.2
        elif signals['rsi']['signal'] == 'overbought':
            bearish_score += signals['rsi']['strength'] * 0.2
        
        # MACD
        if signals['macd']['signal'] == 'bullish':
            bullish_score += signals['macd']['strength'] * 0.3
        elif signals['macd']['signal'] == 'bearish':
            bearish_score += signals['macd']['strength'] * 0.3
        
        # MA
        if signals['ma']['signal'] == 'bullish':
            bullish_score += signals['ma']['strength'] * 0.25
        elif signals['ma']['signal'] == 'bearish':
            bearish_score += signals['ma']['strength'] * 0.25
        
        # Bollinger
        if signals['bollinger']['signal'] == 'oversold':
            bullish_score += signals['bollinger']['strength'] * 0.15
        elif signals['bollinger']['signal'] == 'overbought':
            bearish_score += signals['bollinger']['strength'] * 0.15
        
        # Volume (amplifies existing trend)
        if signals['volume']['signal'] == 'high_volume':
            volume_amp = signals['volume']['strength'] * 0.1
            if bullish_score > bearish_score:
                bullish_score += volume_amp
            else:
                bearish_score += volume_amp
        
        # Determine recommendation
        total_score = bullish_score + bearish_score
        if total_score == 0:
            recommendation = "HOLD"
            confidence = 0.3
        elif bullish_score > bearish_score:
            if bullish_score > 0.6:
                recommendation = "STRONG BUY"
                confidence = min(bullish_score, 0.9)
            else:
                recommendation = "BUY"
                confidence = min(bullish_score, 0.7)
        else:
            if bearish_score > 0.6:
                recommendation = "STRONG SELL"
                confidence = min(bearish_score, 0.9)
            else:
                recommendation = "SELL"
                confidence = min(bearish_score, 0.7)
        
        return {
            "action": recommendation,
            "confidence": float(confidence),
            "bullish_score": float(bullish_score),
            "bearish_score": float(bearish_score),
            "current_price": indicators['current_price'],
            "support_level": indicators['bb_lower'],
            "resistance_level": indicators['bb_upper'],
            "stop_loss_suggestion": float(indicators['current_price'] - 2 * indicators['atr']),
            "take_profit_suggestion": float(indicators['current_price'] + 3 * indicators['atr'])
        }


# Global instance
ta_service = TechnicalAnalysisService()


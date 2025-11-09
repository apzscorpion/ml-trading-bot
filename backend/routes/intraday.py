"""
Comprehensive intraday prediction endpoint using all models, indicators, and patterns.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import logging

from backend.database import get_db
from backend.freddy_merger import freddy_merger
from backend.utils.indicators import calculate_all_indicators, get_latest_indicators
from backend.utils.candlestick_patterns import detect_all_patterns, get_pattern_sentiment
from backend.bots.rsi_bot import RSIBot
from backend.bots.macd_bot import MACDBot
from backend.bots.ma_bot import MABot
from backend.bots.ml_bot import MLBot
from backend.bots.lstm_bot import LSTMBot
from backend.bots.transformer_bot import TransformerBot
from backend.bots.ensemble_bot import EnsembleBot
from backend.services.candle_loader import candle_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intraday", tags=["intraday"])

# Initialize all bots
rsi_bot = RSIBot()
macd_bot = MACDBot()
ma_bot = MABot()
ml_bot = MLBot()
lstm_bot = LSTMBot()
transformer_bot = TransformerBot()
ensemble_bot = EnsembleBot()

all_bots = [
    rsi_bot, macd_bot, ma_bot, ml_bot, 
    lstm_bot, transformer_bot, ensemble_bot
]

TA_WINDOW_MINUTES = {
    "1m": 60 * 24 * 60,
    "5m": 75 * 24 * 60,
    "15m": 90 * 24 * 60,
    "30m": 120 * 24 * 60,
    "1h": 180 * 24 * 60,
    "4h": 365 * 24 * 60,
    "1d": 365 * 24 * 60,
}

TA_FALLBACK_PERIOD = {
    "1m": "60d",
    "5m": "60d",
    "15m": "60d",
    "30m": "730d",
    "1h": "730d",
    "4h": "730d",
    "1d": "2y",
    "1wk": "5y",
    "1mo": "10y",
    "3mo": "10y",
}

DEFAULT_TA_WINDOW_MINUTES = 90 * 24 * 60
PREDICTION_CANDLE_LIMIT = 600

def calculate_targets_and_stop_loss(
    current_price: float,
    predicted_series: List[Dict],
    pattern_sentiment: str,
    indicators: Dict,
    atr: Optional[float] = None
) -> Dict:
    """
    Calculate target prices and stop loss for intraday trading.
    
    Args:
        current_price: Current stock price
        predicted_series: List of predicted prices with timestamps
        pattern_sentiment: 'bullish', 'bearish', or 'neutral'
        indicators: Dictionary of latest indicator values
        atr: Average True Range for volatility-based stops
    
    Returns:
        Dictionary with targets and stop loss
    """
    if not predicted_series:
        return {
            "target_1": None,
            "target_2": None,
            "stop_loss": None,
            "risk_reward_ratio": None
        }
    
    # Get highest and lowest predicted prices
    predicted_prices = [p.get('price', 0) for p in predicted_series if p.get('price')]
    if not predicted_prices:
        return {
            "target_1": None,
            "target_2": None,
            "stop_loss": None,
            "risk_reward_ratio": None
        }
    
    max_predicted = max(predicted_prices)
    min_predicted = min(predicted_prices)
    avg_predicted = sum(predicted_prices) / len(predicted_prices)
    
    # Use ATR for stop loss if available, otherwise use percentage
    if atr and atr > 0:
        atr_multiplier = 1.5  # 1.5x ATR for intraday stop loss
        stop_loss_distance = atr * atr_multiplier
    else:
        # Default: 1% stop loss for intraday
        stop_loss_distance = current_price * 0.01
    
    # Determine targets based on sentiment and predictions
    if pattern_sentiment == 'bullish' or avg_predicted > current_price:
        # Bullish scenario
        target_1 = min(max_predicted, current_price * 1.02)  # Conservative target: 2%
        target_2 = min(max_predicted, current_price * 1.05)  # Aggressive target: 5%
        stop_loss = current_price - stop_loss_distance
        
        # Ensure targets are realistic (not too far from current)
        if target_1 > current_price * 1.10:
            target_1 = current_price * 1.05
        if target_2 > current_price * 1.15:
            target_2 = current_price * 1.10
            
    elif pattern_sentiment == 'bearish' or avg_predicted < current_price:
        # Bearish scenario - for short positions
        target_1 = max(min_predicted, current_price * 0.98)  # Conservative target: 2% down
        target_2 = max(min_predicted, current_price * 0.95)  # Aggressive target: 5% down
        stop_loss = current_price + stop_loss_distance
        
        # Ensure targets are realistic
        if target_1 < current_price * 0.90:
            target_1 = current_price * 0.95
        if target_2 < current_price * 0.85:
            target_2 = current_price * 0.90
    else:
        # Neutral - use prediction range
        price_range = max_predicted - min_predicted
        target_1 = current_price + (price_range * 0.3)
        target_2 = current_price + (price_range * 0.6)
        stop_loss = current_price - stop_loss_distance
    
    # Calculate risk-reward ratio
    risk = abs(stop_loss - current_price)
    reward_1 = abs(target_1 - current_price)
    reward_2 = abs(target_2 - current_price)
    
    risk_reward_1 = reward_1 / risk if risk > 0 else None
    risk_reward_2 = reward_2 / risk if risk > 0 else None
    
    return {
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "stop_loss": round(stop_loss, 2),
        "risk_reward_ratio_1": round(risk_reward_1, 2) if risk_reward_1 else None,
        "risk_reward_ratio_2": round(risk_reward_2, 2) if risk_reward_2 else None,
        "risk_amount": round(risk, 2),
        "reward_1": round(reward_1, 2),
        "reward_2": round(reward_2, 2)
    }


@router.get("/comprehensive-prediction")
async def get_comprehensive_intraday_prediction(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe (intraday: 1m, 5m, 15m)"),
    horizon_minutes: int = Query(180, description="Prediction horizon in minutes"),
    _db: Session = Depends(get_db)
):
    """
    Generate comprehensive intraday prediction using:
    - All ML models (RSI, MACD, MA, ML, LSTM, Transformer, Ensemble)
    - All technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands, ATR, etc.)
    - All candlestick patterns (doji, hammer, hanging man, star, etc.)
    
    Returns:
        Comprehensive prediction with targets and stop loss
    """
    try:
        logger.info(f"Generating comprehensive prediction for {symbol} {timeframe}")
        
        window_minutes = TA_WINDOW_MINUTES.get(timeframe, DEFAULT_TA_WINDOW_MINUTES)
        fallback_period = TA_FALLBACK_PERIOD.get(timeframe, "60d")
        ta_candles = await candle_loader.load_time_window(
            symbol=symbol,
            timeframe=timeframe,
            window_minutes=window_minutes,
            fallback_period=fallback_period,
            min_points=120,
            bypass_cache=True,
        )

        if not ta_candles:
            raise HTTPException(status_code=404, detail=f"No data available for {symbol}")

        ta_candles = sorted(
            ta_candles,
            key=lambda candle: candle.get("start_ts") or "",
        )

        last_candle = ta_candles[-1]
        current_price = float(last_candle.get("close", 0.0))
        current_time_raw = last_candle.get("start_ts")

        if hasattr(current_time_raw, "to_pydatetime"):
            current_time_dt = current_time_raw.to_pydatetime()
        elif isinstance(current_time_raw, datetime):
            current_time_dt = current_time_raw
        elif isinstance(current_time_raw, str):
            try:
                current_time_dt = datetime.fromisoformat(current_time_raw.replace("Z", "+00:00"))
            except ValueError:
                current_time_dt = None
        else:
            current_time_dt = None

        current_time_iso = current_time_dt.isoformat() if current_time_dt else str(current_time_raw)

        # Ensure we have a manageable window for ML models
        prediction_candles = ta_candles[-PREDICTION_CANDLE_LIMIT:]

        # 1. Calculate all technical indicators on the full TA window
        df = calculate_all_indicators(ta_candles)
        latest_indicators = get_latest_indicators(df)
        
        # 2. Detect candlestick patterns
        patterns = detect_all_patterns(ta_candles)
        pattern_sentiment, pattern_confidence = get_pattern_sentiment(patterns)
        
        # 3. Get predictions from all bots
        all_bot_predictions = []
        bot_results = {}
        
        for bot in all_bots:
            try:
                bot_pred = await bot.predict(prediction_candles, horizon_minutes, timeframe)
                if bot_pred and bot_pred.get('predicted_series'):
                    all_bot_predictions.append(bot_pred)
                    bot_results[bot.name] = {
                        "confidence": bot_pred.get('confidence', 0.0),
                        "predicted_series": bot_pred.get('predicted_series', []),
                        "direction": bot_pred.get('meta', {}).get('direction', 0)
                    }
            except Exception as e:
                logger.warning(f"Bot {bot.name} prediction failed: {e}")
                continue
        
        # 4. Merge all predictions using Freddy merger
        merged_prediction = None
        if all_bot_predictions:
            try:
                # Use freddy_merger.predict() method instead of merge_predictions
                merged_prediction = await freddy_merger.predict(
                    symbol=symbol,
                    candles=prediction_candles,
                    horizon_minutes=horizon_minutes,
                    timeframe=timeframe,
                    selected_bots=None  # Use all bots
                )
            except Exception as e:
                logger.error(f"Failed to merge predictions: {e}")
        
        # Use merged prediction or fallback to average
        if merged_prediction and merged_prediction.get('predicted_series'):
            final_predicted_series = merged_prediction.get('predicted_series', [])
            overall_confidence = merged_prediction.get('overall_confidence', 0.0)
            bot_contributions = merged_prediction.get('bot_contributions', {})
        else:
            # Fallback: average all predictions
            all_prices = []
            for pred in all_bot_predictions:
                series = pred.get('predicted_series', [])
                for point in series:
                    if point.get('price'):
                        all_prices.append(point.get('price'))
            
            if all_prices:
                avg_price = sum(all_prices) / len(all_prices)
                final_predicted_series = [{"price": avg_price, "ts": current_time_iso}]
                overall_confidence = sum(b.get('confidence', 0.0) for b in bot_results.values()) / len(bot_results) if bot_results else 0.5
                bot_contributions = {}
            else:
                raise HTTPException(status_code=500, detail="Failed to generate predictions")
        
        # 5. Calculate targets and stop loss
        atr_value = latest_indicators.get('atr_14')
        targets_sl = calculate_targets_and_stop_loss(
            current_price=current_price,
            predicted_series=final_predicted_series,
            pattern_sentiment=pattern_sentiment,
            indicators=latest_indicators,
            atr=atr_value
        )
        
        # 6. Format response
        response = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "current_time": current_time_iso,
            "prediction_timestamp": datetime.utcnow().isoformat(),
            "horizon_minutes": horizon_minutes,
            
            # Pattern analysis
            "candlestick_patterns": {
                "detected_patterns": patterns.get('latest', []),
                "sentiment": pattern_sentiment,
                "confidence": round(pattern_confidence, 3)
            },
            
            # Technical indicators summary
            "indicators": {
                "rsi": latest_indicators.get('rsi_14'),
                "macd": latest_indicators.get('macd'),
                "macd_signal": latest_indicators.get('macd_signal'),
                "macd_histogram": latest_indicators.get('macd_histogram'),
                "sma_20": latest_indicators.get('sma_20'),
                "sma_50": latest_indicators.get('sma_50'),
                "ema_21": latest_indicators.get('ema_21'),
                "bb_upper": latest_indicators.get('bb_upper'),
                "bb_lower": latest_indicators.get('bb_lower'),
                "atr": latest_indicators.get('atr_14'),
                "volume": float(last_candle.get('volume', 0.0)),
                "vwap": latest_indicators.get('vwap_intraday')
            },
            
            # Prediction results
            "prediction": {
                "predicted_series": final_predicted_series,
                "overall_confidence": round(overall_confidence, 3),
                "bot_contributions": bot_contributions
            },
            
            # Trading targets
            "targets": {
                "target_1": targets_sl.get('target_1'),
                "target_2": targets_sl.get('target_2'),
                "stop_loss": targets_sl.get('stop_loss'),
                "risk_reward_ratio_1": targets_sl.get('risk_reward_ratio_1'),
                "risk_reward_ratio_2": targets_sl.get('risk_reward_ratio_2'),
                "risk_amount": targets_sl.get('risk_amount'),
                "reward_1": targets_sl.get('reward_1'),
                "reward_2": targets_sl.get('reward_2')
            },
            
            # Model summary
            "models_used": {
                "total_bots": len(all_bots),
                "successful_bots": len(bot_results),
                "bot_results": bot_results
            }
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating comprehensive prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate prediction: {str(e)}")


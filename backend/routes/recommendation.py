"""
Trading recommendation endpoints based on prediction evaluations.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime, timedelta
import numpy as np

from backend.database import get_db, Prediction, PredictionEvaluation, Candle
from backend.services.comprehensive_analysis import comprehensive_analysis
from backend.services.technical_analysis_service import ta_service
from backend.utils.data_fetcher import data_fetcher
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


def calculate_trend(predictions: list) -> str:
    """Calculate trend direction from predictions"""
    if len(predictions) < 2:
        return "neutral"
    
    prices = [p["price"] for p in predictions]
    start_price = prices[0]
    end_price = prices[-1]
    
    change_pct = ((end_price - start_price) / start_price) * 100
    
    if change_pct > 1.5:
        return "strong_bullish"
    elif change_pct > 0.5:
        return "bullish"
    elif change_pct < -1.5:
        return "strong_bearish"
    elif change_pct < -0.5:
        return "bearish"
    else:
        return "neutral"


def calculate_volatility(predictions: list) -> float:
    """Calculate volatility from predictions"""
    if len(predictions) < 2:
        return 0.0
    
    prices = [p["price"] for p in predictions]
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns) * 100
    return float(volatility)


def get_signal_strength(confidence: float, accuracy: Optional[float]) -> str:
    """Determine signal strength based on confidence and historical accuracy"""
    if accuracy is None:
        score = confidence
    else:
        score = (confidence * 0.6) + (accuracy * 0.4)
    
    if score >= 0.8:
        return "very_strong"
    elif score >= 0.65:
        return "strong"
    elif score >= 0.5:
        return "moderate"
    else:
        return "weak"


@router.get("/analysis")
async def get_trading_recommendation(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    mode: str = Query("combined", description="Mode: 'ta_only', 'ml_only', or 'combined'"),
    db: Session = Depends(get_db)
):
    """
    Get trading recommendation based on mode:
    - ta_only: Pure technical analysis on raw candles (60-90 days)
    - ml_only: ML predictions only
    - combined: TA + ML hybrid (default)
    """
    # TA-only mode: return pure technical analysis
    if mode == "ta_only":
        ta_result = await ta_service.analyze(symbol, timeframe)
        if "error" in ta_result:
            raise HTTPException(status_code=400, detail=ta_result["message"])
        return ta_result
    
    # ML-only or combined mode
    # Get latest prediction
    prediction = db.query(Prediction).filter(
        Prediction.symbol == symbol,
        Prediction.timeframe == timeframe
    ).order_by(Prediction.produced_at.desc()).first()
    
    if not prediction:
        # Fallback to TA-only if no ML predictions available
        if mode == "combined":
            logger.warning(f"No ML predictions for {symbol}, falling back to TA-only")
            return await ta_service.analyze(symbol, timeframe)
        return {
            "error": "No predictions available",
            "symbol": symbol,
            "recommendation": "hold",
            "signal_strength": "none"
        }
    
    # Get latest candle for current price
    latest_candle = db.query(Candle).filter(
        Candle.symbol == symbol,
        Candle.timeframe == timeframe
    ).order_by(Candle.start_ts.desc()).first()
    
    current_price = latest_candle.close if latest_candle else None
    
    # Calculate trend and volatility
    predicted_series = prediction.predicted_series
    trend = calculate_trend(predicted_series)
    volatility = calculate_volatility(predicted_series)
    
    # Get historical accuracy from recent evaluations (optimized query)
    recent_evaluations = db.query(PredictionEvaluation).join(
        Prediction, PredictionEvaluation.prediction_id == Prediction.id
    ).filter(
        Prediction.symbol == symbol,
        Prediction.timeframe == timeframe
    ).order_by(PredictionEvaluation.evaluated_at.desc()).limit(10).all()
    
    avg_directional_accuracy = None
    avg_mape = None
    success_rate = None
    
    if recent_evaluations:
        accuracies = []
        mapes = []
        for eval in recent_evaluations:
            metrics = eval.metrics
            if metrics:
                if "directional_accuracy" in metrics:
                    accuracies.append(metrics["directional_accuracy"])
                if "mape" in metrics:
                    mapes.append(metrics["mape"])
        
        if accuracies:
            avg_directional_accuracy = np.mean(accuracies) / 100  # Convert to 0-1 scale
            success_rate = float(np.mean(accuracies))
        
        if mapes:
            avg_mape = float(np.mean(mapes))
    
    # Determine recommendation
    confidence = prediction.confidence or 0.5
    signal_strength = get_signal_strength(confidence, avg_directional_accuracy)
    
    if trend in ["strong_bullish", "bullish"]:
        recommendation = "buy"
    elif trend in ["strong_bearish", "bearish"]:
        recommendation = "sell"
    else:
        recommendation = "hold"
    
    # Calculate price targets
    # Use the LAST predicted price (end of horizon) as the target price
    predicted_price = predicted_series[-1]["price"] if predicted_series else current_price
    
    # Calculate change from CURRENT price to PREDICTED price (not first-to-last prediction)
    if current_price and predicted_price:
        price_change = predicted_price - current_price
        price_change_pct = (price_change / current_price) * 100
    else:
        price_change = 0
        price_change_pct = 0
    
    # Calculate risk/reward
    if volatility > 2.5:
        risk_level = "high"
    elif volatility > 1.5:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # Generate insights
    insights = []
    
    if trend in ["strong_bullish", "strong_bearish"]:
        insights.append(f"Strong {trend.replace('strong_', '')} trend detected")
    
    if signal_strength in ["very_strong", "strong"]:
        insights.append(f"High confidence signal ({signal_strength})")
    elif signal_strength == "weak":
        insights.append("Low confidence - consider waiting for stronger signal")
    
    if volatility > 2.5:
        insights.append("High volatility - higher risk")
    elif volatility < 1.0:
        insights.append("Low volatility - stable movement expected")
    
    if success_rate and success_rate >= 70:
        insights.append(f"Model has {success_rate:.1f}% historical accuracy")
    elif success_rate and success_rate < 50:
        insights.append("Model accuracy below 50% - use with caution")
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "recommendation": recommendation,
        "signal_strength": signal_strength,
        "trend": trend,
        "confidence": float(confidence * 100),
        "current_price": float(current_price) if current_price else None,
        "predicted_price": float(predicted_price) if predicted_price else None,
        "price_change": float(price_change),
        "price_change_pct": float(price_change_pct),
        "volatility": float(volatility),
        "risk_level": risk_level,
        "success_rate": float(success_rate) if success_rate else None,
        "avg_mape": float(avg_mape) if avg_mape else None,
        "horizon_minutes": prediction.horizon_minutes,
        "prediction_time": prediction.produced_at.isoformat(),
        "insights": insights,
        "bot_contributions": prediction.bot_contributions
    }


@router.get("/signals")
async def get_multiple_signals(
    symbols: str = Query(..., description="Comma-separated symbols"),
    timeframe: str = Query("5m", description="Timeframe"),
    db: Session = Depends(get_db)
):
    """Get trading signals for multiple symbols"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    results = []
    
    for symbol in symbol_list:
        try:
            result = await get_trading_recommendation(symbol=symbol, timeframe=timeframe, db=db)
            results.append(result)
        except Exception as e:
            results.append({
                "symbol": symbol,
                "error": str(e),
                "recommendation": "hold"
            })
    
    return {"signals": results}


@router.get("/comprehensive")
async def get_comprehensive_analysis(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("5m", description="Timeframe"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analysis combining:
    - Internal ML predictions (RSI, MACD, MA, LSTM, Transformer, Ensemble)
    - Freddy AI market intelligence (technical analysis, news, fundamentals)
    - Risk-adjusted recommendations
    
    This endpoint provides the most holistic view by combining:
    1. Our internal models' predictions
    2. Freddy AI's market intelligence and technical analysis
    3. Combined confidence scoring and recommendation normalization
    """
    try:
        logger.info(f"Generating comprehensive analysis for {symbol} {timeframe}")
        
        # Get latest prediction
        prediction = db.query(Prediction).filter(
            Prediction.symbol == symbol,
            Prediction.timeframe == timeframe
        ).order_by(Prediction.produced_at.desc()).first()
        
        # Get latest candle
        latest_candle = db.query(Candle).filter(
            Candle.symbol == symbol,
            Candle.timeframe == timeframe
        ).order_by(Candle.start_ts.desc()).first()
        
        # Fetch recent candles if needed
        candles = None
        if not latest_candle or not prediction:
            # Fetch candles from data source
            try:
                candles_data = await data_fetcher.fetch_candles(
                    symbol=symbol,
                    interval=timeframe,
                    period="5d" if timeframe in ["1m", "5m", "15m"] else "60d"
                )
                if candles_data:
                    candles = candles_data
                    logger.info(f"Fetched {len(candles)} candles for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to fetch candles: {e}")
        
        # Generate comprehensive analysis
        analysis_result = await comprehensive_analysis.analyze(
            symbol=symbol,
            timeframe=timeframe,
            prediction=prediction,
            latest_candle=latest_candle,
            candles=candles
        )
        
        return analysis_result
    
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Comprehensive analysis failed: {str(e)}"
        )


@router.get("/comprehensive/batch")
async def get_comprehensive_analysis_batch(
    symbols: str = Query(..., description="Comma-separated stock symbols"),
    timeframe: str = Query("5m", description="Timeframe"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analysis for multiple symbols in batch.
    Useful for watchlist analysis.
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    results = []
    
    for symbol in symbol_list:
        try:
            result = await get_comprehensive_analysis(
                symbol=symbol,
                timeframe=timeframe,
                db=db
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Failed analysis for {symbol}: {e}")
            results.append({
                "symbol": symbol,
                "error": str(e),
                "recommendation": "hold",
                "confidence": 0.0
            })
    
    return {
        "symbols": symbol_list,
        "timeframe": timeframe,
        "analyses": results,
        "timestamp": datetime.utcnow().isoformat()
    }


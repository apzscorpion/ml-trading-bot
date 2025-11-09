"""
Market prediction routes for Nifty50, Sensex, and Market Sentiment.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from backend.database import get_db, MarketPrediction, MarketSentiment
from backend.bots.nifty_bot import NiftyBot
from backend.bots.sensex_bot import SensexBot
from backend.bots.sentiment_bot import SentimentBot
from backend.utils.data_fetcher import data_fetcher
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])

nifty_bot = NiftyBot()
sensex_bot = SensexBot()
sentiment_bot = SentimentBot()


class MarketPredictionRequest(BaseModel):
    timeframe: Optional[str] = "5m"
    horizon_minutes: Optional[int] = 180


@router.get("/nifty/predict")
async def predict_nifty(
    timeframe: str = "5m",
    horizon_minutes: int = 180,
    db: Session = Depends(get_db)
):
    """
    Get Nifty50 index prediction.
    
    Args:
        timeframe: Candle timeframe (default: 5m)
        horizon_minutes: Prediction horizon in minutes (default: 180)
    
    Returns:
        Nifty50 prediction with trend analysis
    """
    try:
        logger.info("Generating Nifty50 prediction", timeframe=timeframe, horizon_minutes=horizon_minutes)
        
        # Fetch Nifty data
        candles = await data_fetcher.fetch_candles(
            symbol="^NSEI",
            interval=timeframe,
            period="60d" if timeframe in ["1d", "1wk", "1mo"] else "5d"
        )
        
        if not candles:
            raise HTTPException(status_code=404, detail="Could not fetch Nifty50 data")
        
        # Generate prediction
        prediction = await nifty_bot.predict(candles, horizon_minutes, timeframe)
        
        # Store in database
        trend_meta = prediction.get("meta", {})
        market_pred = MarketPrediction(
            index_symbol="^NSEI",
            index_name="Nifty50",
            timeframe=timeframe,
            produced_at=datetime.utcnow(),
            horizon_minutes=horizon_minutes,
            predicted_series=prediction.get("predicted_series", []),
            confidence=prediction.get("confidence", 0.0),
            trend_direction=trend_meta.get("trend_direction", 0),
            trend_direction_str=trend_meta.get("trend_direction_str", "neutral"),
            trend_strength=trend_meta.get("trend_strength", 0.0),
            trend_strength_category=trend_meta.get("trend_strength_category", "weak"),
            trend_duration_minutes=trend_meta.get("trend_duration_minutes", 0),
            current_value=candles[-1].get("close", 0) if candles else 0
        )
        db.add(market_pred)
        db.commit()
        
        return {
            "success": True,
            "prediction": prediction,
            "prediction_id": market_pred.id
        }
        
    except Exception as e:
        logger.error("Nifty50 prediction error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/sensex/predict")
async def predict_sensex(
    timeframe: str = "5m",
    horizon_minutes: int = 180,
    db: Session = Depends(get_db)
):
    """
    Get Sensex index prediction.
    
    Args:
        timeframe: Candle timeframe (default: 5m)
        horizon_minutes: Prediction horizon in minutes (default: 180)
    
    Returns:
        Sensex prediction with trend analysis
    """
    try:
        logger.info("Generating Sensex prediction", timeframe=timeframe, horizon_minutes=horizon_minutes)
        
        # Fetch Sensex data
        candles = await data_fetcher.fetch_candles(
            symbol="^BSESN",
            interval=timeframe,
            period="60d" if timeframe in ["1d", "1wk", "1mo"] else "5d"
        )
        
        if not candles:
            raise HTTPException(status_code=404, detail="Could not fetch Sensex data")
        
        # Generate prediction
        prediction = await sensex_bot.predict(candles, horizon_minutes, timeframe)
        
        # Store in database
        trend_meta = prediction.get("meta", {})
        market_pred = MarketPrediction(
            index_symbol="^BSESN",
            index_name="Sensex",
            timeframe=timeframe,
            produced_at=datetime.utcnow(),
            horizon_minutes=horizon_minutes,
            predicted_series=prediction.get("predicted_series", []),
            confidence=prediction.get("confidence", 0.0),
            trend_direction=trend_meta.get("trend_direction", 0),
            trend_direction_str=trend_meta.get("trend_direction_str", "neutral"),
            trend_strength=trend_meta.get("trend_strength", 0.0),
            trend_strength_category=trend_meta.get("trend_strength_category", "weak"),
            trend_duration_minutes=trend_meta.get("trend_duration_minutes", 0),
            current_value=candles[-1].get("close", 0) if candles else 0
        )
        db.add(market_pred)
        db.commit()
        
        return {
            "success": True,
            "prediction": prediction,
            "prediction_id": market_pred.id
        }
        
    except Exception as e:
        logger.error("Sensex prediction error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/sentiment")
async def get_market_sentiment(
    timeframe: str = "5m",
    horizon_minutes: int = 180,
    db: Session = Depends(get_db)
):
    """
    Get overall market sentiment (bullish/bearish/neutral).
    
    Args:
        timeframe: Candle timeframe (default: 5m)
        horizon_minutes: Prediction horizon in minutes (default: 180)
    
    Returns:
        Market sentiment prediction
    """
    try:
        logger.info("Generating market sentiment", timeframe=timeframe, horizon_minutes=horizon_minutes)
        
        # Generate sentiment prediction
        sentiment_pred = await sentiment_bot.predict([], horizon_minutes, timeframe)
        
        # Store in database
        meta = sentiment_pred.get("meta", {})
        sentiment_record = MarketSentiment(
            produced_at=datetime.utcnow(),
            sentiment=meta.get("sentiment", "neutral"),
            sentiment_value=meta.get("sentiment_value", 0),
            sentiment_strength=meta.get("sentiment_strength", 0.0),
            confidence=sentiment_pred.get("confidence", 0.0),
            nifty_trend=meta.get("nifty_trend", 0),
            sensex_trend=meta.get("sensex_trend", 0),
            nifty_price=meta.get("nifty_price", 0),
            sensex_price=meta.get("sensex_price", 0),
            indices_agreement=meta.get("indices_agreement", False),
            nifty_confidence=meta.get("nifty_confidence", 0.0),
            sensex_confidence=meta.get("sensex_confidence", 0.0)
        )
        db.add(sentiment_record)
        db.commit()
        
        return {
            "success": True,
            "sentiment": sentiment_pred,
            "sentiment_id": sentiment_record.id
        }
        
    except Exception as e:
        logger.error("Market sentiment error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sentiment prediction failed: {str(e)}")


@router.get("/nifty/latest")
async def get_latest_nifty(db: Session = Depends(get_db)):
    """Get latest Nifty50 prediction"""
    latest = db.query(MarketPrediction).filter(
        MarketPrediction.index_symbol == "^NSEI"
    ).order_by(MarketPrediction.produced_at.desc()).first()
    
    if not latest:
        raise HTTPException(status_code=404, detail="No Nifty50 predictions found")
    
    return latest.to_dict()


@router.get("/sensex/latest")
async def get_latest_sensex(db: Session = Depends(get_db)):
    """Get latest Sensex prediction"""
    latest = db.query(MarketPrediction).filter(
        MarketPrediction.index_symbol == "^BSESN"
    ).order_by(MarketPrediction.produced_at.desc()).first()
    
    if not latest:
        raise HTTPException(status_code=404, detail="No Sensex predictions found")
    
    return latest.to_dict()


@router.get("/sentiment/latest")
async def get_latest_sentiment(db: Session = Depends(get_db)):
    """Get latest market sentiment"""
    latest = db.query(MarketSentiment).order_by(
        MarketSentiment.produced_at.desc()
    ).first()
    
    if not latest:
        raise HTTPException(status_code=404, detail="No sentiment predictions found")
    
    return latest.to_dict()


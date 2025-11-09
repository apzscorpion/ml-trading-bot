"""
Market Sentiment Bot
Predicts overall market sentiment (bullish/bearish/neutral) based on multiple indicators.
"""
from typing import Dict, List
import numpy as np
import pandas as pd
from datetime import datetime
import logging

from backend.bots.base_bot import BaseBot
from backend.utils.data_fetcher import data_fetcher
from backend.bots.nifty_bot import NiftyBot
from backend.bots.sensex_bot import SensexBot

logger = logging.getLogger(__name__)


class SentimentBot(BaseBot):
    """Market sentiment classification bot"""
    
    name = "sentiment_bot"
    
    def __init__(self):
        super().__init__("sentiment_bot")  # Use string literal instead of self.name
        self.nifty_bot = NiftyBot()
        self.sensex_bot = SensexBot()
    
    async def predict(
        self, 
        candles: List[Dict],
        horizon_minutes: int,
        timeframe: str
    ) -> Dict:
        """
        Predict market sentiment based on:
        - Nifty50 and Sensex trend
        - Market breadth (if available)
        - Aggregate indicators
        """
        try:
            # Get index predictions
            nifty_pred = await self.nifty_bot.predict([], horizon_minutes, timeframe)
            sensex_pred = await self.sensex_bot.predict([], horizon_minutes, timeframe)
            
            # Extract trend directions
            nifty_trend = nifty_pred.get("meta", {}).get("trend_direction", 0)
            sensex_trend = sensex_pred.get("meta", {}).get("trend_direction", 0)
            
            nifty_strength = nifty_pred.get("meta", {}).get("trend_strength", 0.0)
            sensex_strength = sensex_pred.get("meta", {}).get("trend_strength", 0.0)
            
            # Calculate sentiment score
            # Average of both indices
            avg_direction = (nifty_trend + sensex_trend) / 2.0
            avg_strength = (nifty_strength + sensex_strength) / 2.0
            
            # Classify sentiment
            if avg_direction > 0.3:
                sentiment = "bullish"
                sentiment_value = 1
            elif avg_direction < -0.3:
                sentiment = "bearish"
                sentiment_value = -1
            else:
                sentiment = "neutral"
                sentiment_value = 0
            
            # Calculate confidence based on agreement and strength
            # Agreement: both indices agree on direction
            agreement = 1.0 if (nifty_trend * sensex_trend) > 0 else 0.5
            confidence = min(0.7 + (avg_strength * 0.2) + (agreement * 0.1), 0.95)
            
            # Get index values
            nifty_price = nifty_pred.get("predicted_series", [{}])[-1].get("price", 0) if nifty_pred.get("predicted_series") else 0
            sensex_price = sensex_pred.get("predicted_series", [{}])[-1].get("price", 0) if sensex_pred.get("predicted_series") else 0
            
            return {
                "predicted_series": [],  # Sentiment doesn't have price series
                "confidence": float(confidence),
                "bot_name": self.name,
                "meta": {
                    "sentiment": sentiment,
                    "sentiment_value": sentiment_value,
                    "sentiment_strength": round(avg_strength, 3),
                    "nifty_trend": nifty_trend,
                    "sensex_trend": sensex_trend,
                    "nifty_price": nifty_price,
                    "sensex_price": sensex_price,
                    "indices_agreement": agreement > 0.5,
                    "nifty_confidence": nifty_pred.get("confidence", 0.0),
                    "sensex_confidence": sensex_pred.get("confidence", 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}", exc_info=True)
            return self._empty_prediction()
    
    def _empty_prediction(self) -> Dict:
        """Return empty prediction on error"""
        return {
            "predicted_series": [],
            "confidence": 0.0,
            "bot_name": self.name,
            "meta": {
                "sentiment": "neutral",
                "sentiment_value": 0,
                "error": "prediction_failed"
            }
        }


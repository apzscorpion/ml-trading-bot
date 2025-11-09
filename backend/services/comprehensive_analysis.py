"""
Comprehensive Analysis Service
Combines internal ML predictions with Freddy AI market intelligence
to provide holistic trading recommendations.
"""
from typing import Dict, Optional, List
from datetime import datetime
import numpy as np
import math

from backend.services.freddy_ai_service import freddy_ai_service, FreddyAIResponse
from backend.database import Prediction, Candle
from backend.utils.logger import get_logger
from backend.utils.data_fetcher import data_fetcher

logger = get_logger(__name__)


class ComprehensiveAnalysis:
    """
    Comprehensive analysis combining:
    1. Internal ML predictions (RSI, MACD, MA, LSTM, Transformer, Ensemble)
    2. Freddy AI market intelligence (technical, fundamental, news)
    3. Risk-adjusted recommendations
    """
    
    @staticmethod
    def _normalize_recommendation(internal_rec: str, freddy_rec: Optional[str]) -> str:
        """
        Normalize and combine recommendations from internal and Freddy AI.
        
        Args:
            internal_rec: Internal recommendation (buy/sell/hold)
            freddy_rec: Freddy AI recommendation (Buy/Sell/Hold/Buy on Dip)
        
        Returns:
            Normalized combined recommendation
        """
        # Normalize Freddy recommendation
        freddy_normalized = None
        if freddy_rec:
            freddy_lower = freddy_rec.lower()
            if "buy" in freddy_lower and "dip" in freddy_lower:
                freddy_normalized = "buy_on_dip"
            elif "buy" in freddy_lower:
                freddy_normalized = "buy"
            elif "sell" in freddy_lower:
                freddy_normalized = "sell"
            else:
                freddy_normalized = "hold"
        
        # Combine logic
        if not freddy_normalized:
            return internal_rec
        
        # Both agree
        if internal_rec == freddy_normalized:
            return internal_rec
        
        # One says buy, other says hold -> cautious buy
        if internal_rec == "buy" and freddy_normalized == "hold":
            return "buy"
        if internal_rec == "hold" and freddy_normalized == "buy":
            return "buy_on_dip"
        
        # One says sell, other says hold -> cautious sell
        if internal_rec == "sell" and freddy_normalized == "hold":
            return "sell"
        if internal_rec == "hold" and freddy_normalized == "sell":
            return "hold"  # Be conservative
        
        # Direct conflict (buy vs sell) -> hold (safest)
        if (internal_rec == "buy" and freddy_normalized == "sell") or \
           (internal_rec == "sell" and freddy_normalized == "buy"):
            return "hold"
        
        return internal_rec
    
    @staticmethod
    def _calculate_combined_confidence(
        internal_confidence: float,
        freddy_confidence: Optional[float],
        agreement: bool
    ) -> float:
        """
        Calculate combined confidence score.
        
        Args:
            internal_confidence: Internal model confidence (0-1)
            freddy_confidence: Freddy AI confidence (0-1)
            agreement: Whether recommendations agree
        
        Returns:
            Combined confidence (0-1)
        """
        if not freddy_confidence:
            return internal_confidence
        
        # If they agree, boost confidence
        if agreement:
            combined = (internal_confidence * 0.5) + (freddy_confidence * 0.5)
            # Boost by 10% for agreement
            combined = min(1.0, combined * 1.1)
        else:
            # If they disagree, reduce confidence
            combined = (internal_confidence * 0.6) + (freddy_confidence * 0.4)
            # Reduce by 20% for disagreement
            combined = max(0.0, combined * 0.8)
        
        return combined
    
    @staticmethod
    async def analyze(
        symbol: str,
        timeframe: str = "5m",
        prediction: Optional[Prediction] = None,
        latest_candle: Optional[Candle] = None,
        candles: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Perform comprehensive analysis combining internal predictions and Freddy AI.
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            prediction: Internal prediction object (optional)
            latest_candle: Latest candle data (optional)
            candles: List of candle dictionaries (optional)
        
        Returns:
            Comprehensive analysis dictionary
        """
        logger.info(f"Generating comprehensive analysis for {symbol} {timeframe}")
        
        # Get current price
        current_price = None
        if latest_candle:
            current_price = latest_candle.close
        elif candles and len(candles) > 0:
            current_price = candles[-1].get('close')
        
        # Fetch Freddy AI analysis
        freddy_response: Optional[FreddyAIResponse] = None
        try:
            logger.info(f"Attempting to fetch Freddy AI analysis for {symbol}")
            freddy_response = await freddy_ai_service.analyze_stock(
                symbol=symbol,
                current_price=current_price
            )
            if freddy_response:
                logger.info(f"Freddy AI analysis received for {symbol}")
            else:
                logger.warning(f"Freddy AI returned no response for {symbol}")
        except Exception as e:
            logger.error(f"Freddy AI analysis failed for {symbol}: {e}", exc_info=True)
        
        # Get internal prediction data
        internal_rec = "hold"
        internal_confidence = 0.5
        predicted_price = current_price
        trend = "neutral"
        volatility = 0.0
        
        if prediction:
            predicted_series = prediction.predicted_series
            if predicted_series:
                predicted_price = predicted_series[-1].get("price", current_price)
                # Calculate trend
                if len(predicted_series) >= 2:
                    start_price = predicted_series[0].get("price", current_price)
                    end_price = predicted_series[-1].get("price", current_price)
                    change_pct = ((end_price - start_price) / start_price) * 100 if start_price else 0
                    
                    if change_pct > 1.5:
                        trend = "strong_bullish"
                        internal_rec = "buy"
                    elif change_pct > 0.5:
                        trend = "bullish"
                        internal_rec = "buy"
                    elif change_pct < -1.5:
                        trend = "strong_bearish"
                        internal_rec = "sell"
                    elif change_pct < -0.5:
                        trend = "bearish"
                        internal_rec = "sell"
                
                # Calculate volatility
                prices = [p.get("price", current_price) for p in predicted_series]
                if len(prices) > 1:
                    returns = np.diff(prices) / prices[:-1]
                    volatility = float(np.std(returns) * 100) if len(returns) > 0 else 0.0
            
            internal_confidence = prediction.confidence or 0.5
        
        # Combine recommendations
        freddy_rec = freddy_response.recommendation if freddy_response else None
        combined_rec = ComprehensiveAnalysis._normalize_recommendation(internal_rec, freddy_rec)
        
        # Check agreement
        freddy_normalized = None
        if freddy_rec:
            freddy_lower = freddy_rec.lower()
            if "buy" in freddy_lower:
                freddy_normalized = "buy"
            elif "sell" in freddy_lower:
                freddy_normalized = "sell"
            else:
                freddy_normalized = "hold"
        
        agreement = (internal_rec == freddy_normalized) if freddy_normalized else False
        
        # Calculate combined confidence
        freddy_conf = freddy_response.confidence if freddy_response else None
        combined_confidence = ComprehensiveAnalysis._calculate_combined_confidence(
            internal_confidence,
            freddy_conf,
            agreement
        )
        
        # Determine target and stop loss
        target_price = predicted_price
        stop_loss = None
        
        if freddy_response:
            if freddy_response.target_price:
                # Validate target_price is not NaN/Inf
                freddy_target = freddy_response.target_price
                if isinstance(freddy_target, (int, float)) and not (math.isnan(freddy_target) or math.isinf(freddy_target)):
                    # Average between internal prediction and Freddy target
                    if predicted_price and predicted_price != current_price and not (math.isnan(predicted_price) or math.isinf(predicted_price)):
                        target_price = (predicted_price * 0.6) + (freddy_target * 0.4)
                    else:
                        target_price = freddy_target
                else:
                    logger.warning(f"Freddy AI returned invalid target_price: {freddy_target}")
                    # Use internal prediction if Freddy target is invalid
                    if predicted_price and not (math.isnan(predicted_price) or math.isinf(predicted_price)):
                        target_price = predicted_price
                    else:
                        target_price = current_price
            
            if freddy_response.stop_loss:
                freddy_sl = freddy_response.stop_loss
                if isinstance(freddy_sl, (int, float)) and not (math.isnan(freddy_sl) or math.isinf(freddy_sl)):
                    stop_loss = freddy_sl
                else:
                    logger.warning(f"Freddy AI returned invalid stop_loss: {freddy_sl}")
        
        # Final validation - ensure target_price is valid
        if target_price and isinstance(target_price, (int, float)):
            if math.isnan(target_price) or math.isinf(target_price):
                logger.warning(f"Invalid target_price after combination: {target_price}, using current_price")
                target_price = current_price if current_price else predicted_price
        
        # Calculate price change
        if current_price and target_price:
            price_change = target_price - current_price
            price_change_pct = (price_change / current_price) * 100
        else:
            price_change = 0
            price_change_pct = 0
        
        # Build insights
        insights = []
        
        # Internal model insights
        if trend in ["strong_bullish", "strong_bearish"]:
            insights.append(f"Strong {trend.replace('strong_', '')} trend from ML models")
        
        if internal_confidence >= 0.7:
            insights.append(f"High confidence from internal models ({internal_confidence:.0%})")
        elif internal_confidence < 0.4:
            insights.append("Low confidence from internal models - use caution")
        
        # Freddy AI insights
        if freddy_response:
            if freddy_response.technical_indicators:
                ti = freddy_response.technical_indicators
                if ti.technical_bias:
                    insights.append(f"Technical bias: {ti.technical_bias}")
                
                if ti.rsi_level:
                    insights.append(f"RSI: {ti.rsi_level}")
            
            if freddy_response.news_events:
                positive_news = [n for n in freddy_response.news_events if n.impact == "positive"]
                negative_news = [n for n in freddy_response.news_events if n.impact == "negative"]
                
                if positive_news:
                    insights.append(f"{len(positive_news)} positive news event(s)")
                if negative_news:
                    insights.append(f"{len(negative_news)} negative news event(s)")
            
            if freddy_response.summary:
                insights.append(f"Market intelligence: {freddy_response.summary[:150]}...")
        
        # Agreement/disagreement insight
        if agreement:
            insights.append("✓ Internal models and market intelligence agree")
        elif freddy_normalized:
            insights.append("⚠ Internal models and market intelligence differ - exercise caution")
        
        # Risk assessment
        risk_level = "medium"
        if freddy_response and freddy_response.risk_metrics:
            risk_level = freddy_response.risk_metrics.risk_level or risk_level
        elif volatility > 2.5:
            risk_level = "high"
        elif volatility < 1.0:
            risk_level = "low"
        
        # Build response
        response = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat(),
            "current_price": float(current_price) if current_price else None,
            
            # Recommendations
            "recommendation": combined_rec,
            "recommendation_details": {
                "internal": internal_rec,
                "freddy_ai": freddy_rec,
                "agreement": agreement
            },
            "confidence": float(combined_confidence),
            "confidence_breakdown": {
                "internal": float(internal_confidence),
                "freddy_ai": float(freddy_conf) if freddy_conf else None,
                "combined": float(combined_confidence)
            },
            
            # Price targets
            "target_price": float(target_price) if target_price else None,
            "stop_loss": float(stop_loss) if stop_loss else None,
            "price_change": float(price_change),
            "price_change_pct": float(price_change_pct),
            
            # Market data
            "trend": trend,
            "volatility": float(volatility),
            "risk_level": risk_level,
            
            # Internal prediction data
            "internal_prediction": {
                "predicted_price": float(predicted_price) if predicted_price else None,
                "trend": trend,
                "confidence": float(internal_confidence)
            },
            
            # Freddy AI data
            "freddy_ai": {
                "available": freddy_response is not None,
                "recommendation": freddy_rec,
                "target_price": float(freddy_response.target_price) if freddy_response and freddy_response.target_price else None,
                "stop_loss": float(freddy_response.stop_loss) if freddy_response and freddy_response.stop_loss else None,
                "confidence": float(freddy_conf) if freddy_conf else None,
                "technical_indicators": freddy_response.technical_indicators.dict() if freddy_response and freddy_response.technical_indicators else None,
                "news_count": len(freddy_response.news_events) if freddy_response else 0,
                "summary": freddy_response.summary if freddy_response else None
            },
            
            # Insights
            "insights": insights,
            
            # Metadata
            "analysis_version": "v1.0",
            "data_sources": {
                "internal_ml": True,
                "freddy_ai": freddy_response is not None
            }
        }
        
        return response


# Singleton instance
comprehensive_analysis = ComprehensiveAnalysis()


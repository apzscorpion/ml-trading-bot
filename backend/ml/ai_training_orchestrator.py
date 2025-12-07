"""
AI-Powered Training Orchestrator
Uses Freddy AI to generate training targets, stop-losses, and market insights.
Learns from real-time data and technical analysis reports.
"""
import asyncio
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import logging

from backend.services.freddy_ai_service import freddy_ai_service, FreddyAIResponse
from backend.utils.data_fetcher import data_fetcher
from backend.database import SessionLocal, Candle, ModelTrainingRecord, Prediction, PredictionEvaluation
from backend.utils.logger import get_logger
from backend.services.technical_analysis_service import TechnicalAnalysisService
from sqlalchemy import desc

logger = get_logger(__name__)


class AITrainingDataPoint:
    """Single training data point with AI-generated labels"""
    def __init__(
        self,
        timestamp: datetime,
        features: Dict,
        target_price: float,
        stop_loss: float,
        confidence: float,
        recommendation: str,
        technical_bias: str,
        support_levels: List[float],
        resistance_levels: List[float],
        news_sentiment: Optional[str] = None
    ):
        self.timestamp = timestamp
        self.features = features
        self.target_price = target_price
        self.stop_loss = stop_loss
        self.confidence = confidence
        self.recommendation = recommendation
        self.technical_bias = technical_bias
        self.support_levels = support_levels
        self.resistance_levels = resistance_levels
        self.news_sentiment = news_sentiment


class AITrainingOrchestrator:
    """
    Orchestrates AI-powered model training using Freddy API for labels.
    
    Features:
    - Fetches latest real-time data for training
    - Uses Freddy AI to generate target/stop-loss for each training point
    - Learns from historical technical analysis reports
    - Incorporates news sentiment and market context
    - Generates high-quality training labels automatically
    """
    
    def __init__(self):
        self.technical_service = TechnicalAnalysisService()
        self.training_history = []
        
    async def fetch_latest_training_data(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """
        Fetch latest data from APIs for training.
        Always gets fresh data, never uses stale cached data.
        
        Args:
            symbol: Stock symbol (e.g., INFY.NS)
            timeframe: Timeframe (5m, 15m, 1h)
            lookback_days: How many days of data to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching latest training data for {symbol}/{timeframe} ({lookback_days} days)")
        
        # Map days to period
        period_map = {
            "1m": "7d",
            "5m": "60d",
            "15m": "60d",
            "1h": "730d",
            "1d": "730d"
        }
        
        period = period_map.get(timeframe, "60d")
        
        # ALWAYS bypass cache for training data
        candles = await data_fetcher.fetch_candles(
            symbol=symbol,
            interval=timeframe,
            period=period,
            bypass_cache=True  # CRITICAL: Always get fresh data
        )
        
        if not candles:
            logger.error(f"No data fetched for {symbol}/{timeframe}")
            return pd.DataFrame()
        
        df = pd.DataFrame(candles)
        
        # Filter to lookback window
        if not df.empty and 'start_ts' in df.columns:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            # Ensure start_ts is datetime
            df['start_ts'] = pd.to_datetime(df['start_ts'])
            
            # Handle timezone comparison
            if df['start_ts'].dt.tz is not None and cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)
            elif df['start_ts'].dt.tz is None and cutoff.tzinfo is not None:
                df['start_ts'] = df['start_ts'].dt.tz_localize('UTC')
            
            # If df has different timezone than cutoff, convert cutoff to match
            if df['start_ts'].dt.tz is not None and cutoff.tzinfo is not None:
                 cutoff = cutoff.astimezone(df['start_ts'].dt.tz)

            df = df[df['start_ts'] >= cutoff]
        
        logger.info(f"Fetched {len(df)} candles for training")
        return df
    
    async def generate_ai_labels_for_point(
        self,
        symbol: str,
        current_price: float,
        candles_context: List[Dict],
        technical_indicators: Optional[Dict] = None
    ) -> Optional[AITrainingDataPoint]:
        """
        Use Freddy AI to generate training labels (target, stop-loss) for a single point.
        
        Args:
            symbol: Stock symbol
            current_price: Current price at this training point
            candles_context: Recent candles for context
            technical_indicators: Pre-calculated technical indicators
            
        Returns:
            AITrainingDataPoint with AI-generated labels, or None if failed
        """
        try:
            # Call Freddy AI for analysis
            freddy_response: Optional[FreddyAIResponse] = await freddy_ai_service.analyze_stock(
                symbol=symbol,
                current_price=current_price,
                use_cache=False  # Don't use cache for training labels
            )
            
            if not freddy_response:
                logger.warning(f"Freddy AI returned no response for {symbol} at price {current_price}")
                return None
            
            # Extract labels from Freddy response
            target_price = freddy_response.target_price or current_price * 1.02
            stop_loss = freddy_response.stop_loss or current_price * 0.98
            confidence = freddy_response.confidence or 0.5
            recommendation = freddy_response.recommendation or "Hold"
            
            # Technical bias
            technical_bias = "neutral"
            if freddy_response.technical_indicators:
                technical_bias = freddy_response.technical_indicators.technical_bias or "neutral"
            
            # Support/Resistance
            support_levels = []
            resistance_levels = []
            if freddy_response.support_resistance:
                support_levels = freddy_response.support_resistance.support_levels
                resistance_levels = freddy_response.support_resistance.resistance_levels
            
            # News sentiment
            news_sentiment = None
            if freddy_response.news_events:
                positive_count = sum(1 for n in freddy_response.news_events if n.impact == "positive")
                negative_count = sum(1 for n in freddy_response.news_events if n.impact == "negative")
                if positive_count > negative_count:
                    news_sentiment = "positive"
                elif negative_count > positive_count:
                    news_sentiment = "negative"
                else:
                    news_sentiment = "neutral"
            
            # Calculate features
            features = self._calculate_features(candles_context, technical_indicators)
            
            return AITrainingDataPoint(
                timestamp=datetime.utcnow(),
                features=features,
                target_price=target_price,
                stop_loss=stop_loss,
                confidence=confidence,
                recommendation=recommendation,
                technical_bias=technical_bias,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                news_sentiment=news_sentiment
            )
            
        except Exception as e:
            logger.error(f"Error generating AI labels for {symbol}: {e}", exc_info=True)
            return None
    
    def _calculate_features(
        self,
        candles: List[Dict],
        technical_indicators: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate features from candles and indicators.
        
        Args:
            candles: Recent candle data
            technical_indicators: Pre-calculated indicators
            
        Returns:
            Dictionary of features
        """
        if not candles:
            return {}
        
        df = pd.DataFrame(candles)
        
        features = {
            # Price features
            'close': float(df['close'].iloc[-1]),
            'open': float(df['open'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'low': float(df['low'].iloc[-1]),
            'volume': float(df['volume'].iloc[-1]) if 'volume' in df else 0,
            
            # Returns
            'returns_1': float(df['close'].pct_change(1).iloc[-1]) if len(df) > 1 else 0,
            'returns_5': float(df['close'].pct_change(5).iloc[-1]) if len(df) > 5 else 0,
            'returns_10': float(df['close'].pct_change(10).iloc[-1]) if len(df) > 10 else 0,
            
            # Volatility
            'volatility_5': float(df['close'].pct_change().rolling(5).std().iloc[-1]) if len(df) > 5 else 0,
            'volatility_10': float(df['close'].pct_change().rolling(10).std().iloc[-1]) if len(df) > 10 else 0,
        }
        
        # Add technical indicators if available
        if technical_indicators:
            features.update({
                'rsi': technical_indicators.get('rsi', 50),
                'macd': technical_indicators.get('macd', 0),
                'macd_signal': technical_indicators.get('macd_signal', 0),
                'bollinger_upper': technical_indicators.get('bollinger_upper', 0),
                'bollinger_lower': technical_indicators.get('bollinger_lower', 0),
                'sma_20': technical_indicators.get('sma_20', 0),
                'ema_12': technical_indicators.get('ema_12', 0),
                'ema_12': technical_indicators.get('ema_12', 0),
                'ema_26': technical_indicators.get('ema_26', 0),
                'ichimoku_conversion': technical_indicators.get('ichimoku_conversion_line', 0),
                'ichimoku_base': technical_indicators.get('ichimoku_base_line', 0),
                'cci': technical_indicators.get('cci', 0),
                'williams_r': technical_indicators.get('williams_r', 0),
                'psar_direction': technical_indicators.get('psar_direction', 0),
            })
        
        # Replace NaN and Inf
        for key in features:
            if features[key] is None or np.isnan(features[key]) or np.isinf(features[key]):
                features[key] = 0.0
        
        return features
    
    async def generate_training_dataset(
        self,
        symbol: str,
        timeframe: str = "5m",
        lookback_days: int = 30,
        sample_points: int = 100,
        batch_size: int = 5
    ) -> Tuple[List[AITrainingDataPoint], Dict]:
        """
        Generate complete training dataset with AI-generated labels.
        
        This is the MAIN method that:
        1. Fetches latest data from API
        2. Samples strategic points for labeling
        3. Calls Freddy AI to generate target/stop-loss for each point
        4. Returns structured training data
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            lookback_days: How many days of history to use
            sample_points: How many points to label (more = better but slower)
            batch_size: How many concurrent Freddy API calls
            
        Returns:
            (training_points, metadata)
        """
        logger.info(
            f"🚀 Starting AI-powered training dataset generation for {symbol}/{timeframe}"
        )
        logger.info(f"Parameters: lookback={lookback_days}d, sample_points={sample_points}")
        
        metadata = {
            "symbol": symbol,
            "timeframe": timeframe,
            "lookback_days": lookback_days,
            "sample_points": sample_points,
            "started_at": datetime.utcnow().isoformat(),
            "freddy_calls": 0,
            "success_rate": 0.0
        }
        
        # Step 1: Fetch latest data
        df = await self.fetch_latest_training_data(symbol, timeframe, lookback_days)
        
        if df.empty:
            logger.error("No data fetched, cannot generate training dataset")
            metadata["error"] = "no_data"
            return [], metadata
        
        metadata["total_candles"] = len(df)
        
        # Step 2: Sample strategic points
        # Use both uniform sampling and volatility-based sampling
        sample_indices = self._sample_strategic_points(df, sample_points)
        
        logger.info(f"Sampled {len(sample_indices)} strategic points for labeling")
        
        # Step 3: Generate AI labels for each point (in batches)
        training_points = []
        failed_count = 0
        
        for i in range(0, len(sample_indices), batch_size):
            batch_indices = sample_indices[i:i+batch_size]
            
            # Process batch concurrently
            tasks = []
            for idx in batch_indices:
                if idx >= len(df):
                    continue
                
                current_price = float(df.iloc[idx]['close'])
                # Get context window (last 50 candles up to this point)
                context_start = max(0, idx - 50)
                candles_context = df.iloc[context_start:idx+1].to_dict('records')
                
                tasks.append(
                    self.generate_ai_labels_for_point(
                        symbol=symbol,
                        current_price=current_price,
                        candles_context=candles_context
                    )
                )
            
            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Failed to generate label: {result}")
                    failed_count += 1
                elif result is not None:
                    training_points.append(result)
                    metadata["freddy_calls"] += 1
                else:
                    failed_count += 1
            
            # Rate limiting: small delay between batches
            if i + batch_size < len(sample_indices):
                await asyncio.sleep(1)  # 1 second between batches
        
        # Calculate success rate
        total_attempts = len(sample_indices)
        metadata["success_rate"] = len(training_points) / total_attempts if total_attempts > 0 else 0
        metadata["successful_labels"] = len(training_points)
        metadata["failed_labels"] = failed_count
        metadata["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(
            f"✅ Generated {len(training_points)} AI-labeled training points "
            f"(success rate: {metadata['success_rate']*100:.1f}%)"
        )
        
        return training_points, metadata
    
    def _sample_strategic_points(self, df: pd.DataFrame, n_samples: int) -> List[int]:
        """
        Sample strategic points for labeling.
        Combines uniform sampling with volatility-based sampling.
        
        Args:
            df: DataFrame with OHLCV data
            n_samples: Number of samples to take
            
        Returns:
            List of indices to sample
        """
        if len(df) < n_samples:
            return list(range(len(df)))
        
        # 50% uniform sampling across time
        uniform_samples = np.linspace(0, len(df)-1, n_samples//2, dtype=int).tolist()
        
        # 50% volatility-based sampling (sample more from volatile periods)
        if 'close' in df.columns:
            returns = df['close'].pct_change().abs()
            # Replace NaN with 0
            returns = returns.fillna(0)
            
            # Normalize to probabilities
            if returns.sum() > 0:
                probs = returns / returns.sum()
                volatile_samples = np.random.choice(
                    len(df),
                    size=n_samples - len(uniform_samples),
                    replace=False,
                    p=probs.values
                ).tolist()
            else:
                volatile_samples = []
        else:
            volatile_samples = []
        
        # Combine and deduplicate
        all_samples = list(set(uniform_samples + volatile_samples))
        all_samples.sort()
        
        return all_samples[:n_samples]
    
    def convert_to_training_format(
        self,
        training_points: List[AITrainingDataPoint]
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Convert AI training points to X, y format for model training.
        
        Args:
            training_points: List of AITrainingDataPoint
            
        Returns:
            (X, y, metadata) where:
            - X: feature matrix (n_samples, n_features)
            - y: target values (n_samples,) - can be target_price, or returns, or classification
            - metadata: additional info about the conversion
        """
        if not training_points:
            return np.array([]), np.array([]), {"error": "no_points"}
        
        X_list = []
        y_list = []
        
        for point in training_points:
            # Convert features dict to array
            feature_values = [
                point.features.get('close', 0),
                point.features.get('open', 0),
                point.features.get('high', 0),
                point.features.get('low', 0),
                point.features.get('volume', 0),
                point.features.get('returns_1', 0),
                point.features.get('returns_5', 0),
                point.features.get('returns_10', 0),
                point.features.get('volatility_5', 0),
                point.features.get('volatility_10', 0),
                point.features.get('rsi', 50),
                point.features.get('macd', 0),
                point.features.get('ichimoku_conversion', 0),
                point.features.get('ichimoku_base', 0),
                point.features.get('cci', 0),
                point.features.get('williams_r', 0),
                point.features.get('psar_direction', 0),
                point.confidence,
                # Add target/stop-loss as features (helps model learn risk/reward)
                (point.target_price - point.features.get('close', 0)) / point.features.get('close', 1),
                (point.features.get('close', 0) - point.stop_loss) / point.features.get('close', 1),
            ]
            
            X_list.append(feature_values)
            
            # Target: use Freddy's target price
            y_list.append(point.target_price)
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        metadata = {
            "n_samples": len(training_points),
            "n_features": X.shape[1] if len(X) > 0 else 0,
            "feature_names": [
                'close', 'open', 'high', 'low', 'volume',
                'returns_1', 'returns_5', 'returns_10',
                'volatility_5', 'volatility_10', 'rsi', 'macd',
                'ichimoku_conversion', 'ichimoku_base', 'cci', 'williams_r', 'psar_direction',
                'freddy_confidence', 'target_return', 'stop_loss_distance'
            ]
        }
        
        return X, y, metadata

    async def generate_dataset_from_mistakes(
        self,
        min_error_threshold: float = 2.0,  # MAPE threshold (2%)
        max_mistakes: int = 100
    ) -> Tuple[List[AITrainingDataPoint], Dict]:
        """
        Generate training dataset specifically from past prediction mistakes.
        
        Args:
            min_error_threshold: Minimum MAPE to consider a mistake
            max_mistakes: Maximum number of mistakes to process
            
        Returns:
            (training_points, metadata)
        """
        logger.info(f"Generating training dataset from mistakes (MAPE > {min_error_threshold}%)")
        
        db = SessionLocal()
        try:
            # Find high-error evaluations
            mistakes = db.query(PredictionEvaluation).filter(
                PredictionEvaluation.mape >= min_error_threshold
            ).order_by(desc(PredictionEvaluation.evaluated_at)).limit(max_mistakes).all()
            
            if not mistakes:
                logger.info("No significant mistakes found to learn from")
                return [], {"status": "no_mistakes"}
            
            logger.info(f"Found {len(mistakes)} mistakes to analyze")
            
            training_points = []
            processed_count = 0
            
            for evaluation in mistakes:
                # Get original prediction to find timestamp and symbol
                prediction = db.query(Prediction).filter(Prediction.id == evaluation.prediction_id).first()
                if not prediction:
                    continue
                    
                # We need to reconstruct the state AT THE TIME of prediction
                # Fetch candles leading up to produced_at
                end_time = prediction.produced_at
                start_time = end_time - timedelta(days=60) # Sufficient lookback
                
                # Fetch historical context
                candles = db.query(Candle).filter(
                    Candle.symbol == prediction.symbol,
                    Candle.timeframe == prediction.timeframe,
                    Candle.start_ts <= end_time,
                    Candle.start_ts >= start_time
                ).order_by(Candle.start_ts).all()
                
                if not candles or len(candles) < 50:
                    continue
                    
                # Convert to dict format
                candles_data = [c.to_dict() for c in candles]
                
                # Get the ACTUAL outcome that happened
                # We want the price at horizon
                horizon_time = prediction.produced_at + timedelta(minutes=prediction.horizon_minutes)
                
                actual_outcome_candle = db.query(Candle).filter(
                    Candle.symbol == prediction.symbol,
                    Candle.timeframe == prediction.timeframe,
                    Candle.start_ts >= horizon_time
                ).order_by(Candle.start_ts).first()
                
                if not actual_outcome_candle:
                    continue
                    
                actual_price = actual_outcome_candle.close
                current_price = candles[-1].close
                
                # Calculate what the correct target should have been
                # For simplicity, we assume target is the actual price at horizon
                # In reality, we might want the max/min within the horizon for optimal trading
                
                # Re-calculate features based on PAST data
                features = self._calculate_features(candles_data)
                
                # Create corrected training point
                # We use the ACTUAL outcome as the target
                point = AITrainingDataPoint(
                    timestamp=prediction.produced_at,
                    features=features,
                    target_price=actual_price,
                    stop_loss=current_price * 0.98, # Default/Estimated
                    confidence=1.0, # High confidence because this is ground truth
                    recommendation="Buy" if actual_price > current_price else "Sell",
                    technical_bias="neutral", # We don't have this historical state easily
                    support_levels=[],
                    resistance_levels=[],
                    news_sentiment=None
                )
                
                training_points.append(point)
                processed_count += 1
                
            logger.info(f"Generated {len(training_points)} correction points from mistakes")
            
            return training_points, {
                "source": "mistakes",
                "mistakes_found": len(mistakes),
                "points_generated": len(training_points)
            }
            
        except Exception as e:
            logger.error(f"Error generating dataset from mistakes: {e}", exc_info=True)
            return [], {"error": str(e)}
        finally:
            db.close()


# Global instance
ai_training_orchestrator = AITrainingOrchestrator()


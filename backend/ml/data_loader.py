"""
ML Data Loader - Unified data loading with consistent windowing for all ML bots.
Ensures all models train on the same 60-90 day rolling windows with validated schemas.
"""
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from backend.database import SessionLocal, Candle
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class MLDataLoader:
    """Unified data loader for ML training with consistent windowing"""
    
    def __init__(self):
        self.default_window_days = 90
        self.min_candles_required = 200
        self.required_columns = ['start_ts', 'open', 'high', 'low', 'close', 'volume']
    
    async def get_training_window(
        self,
        symbol: str,
        timeframe: str,
        days: Optional[int] = None
    ) -> Tuple[Optional[pd.DataFrame], Dict]:
        """
        Fetch consistent training window for ML models.
        
        Args:
            symbol: Stock symbol
            timeframe: Candle timeframe
            days: Number of days to fetch (default: 90)
        
        Returns:
            (DataFrame with validated schema, metadata dict)
            Returns (None, error_dict) if data is insufficient
        """
        days = days or self.default_window_days
        
        # Fetch raw candles
        candles, metadata = await self._fetch_candles(symbol, timeframe, days)
        
        if not candles:
            return None, {
                "error": "no_data",
                "message": f"No candles found for {symbol}/{timeframe}",
                "days_requested": days
            }
        
        # Convert to DataFrame
        df = pd.DataFrame(candles)
        
        # Validate schema
        is_valid, validation_error = self._validate_schema(df)
        if not is_valid:
            return None, {
                "error": "schema_validation_failed",
                "message": validation_error,
                "columns_found": list(df.columns)
            }
        
        # Validate data quality
        is_clean, quality_error = self._validate_data_quality(df)
        if not is_clean:
            logger.warning(f"Data quality issues for {symbol}/{timeframe}: {quality_error}")
            # Don't fail, but log the issue
        
        # Sort by timestamp
        df = df.sort_values('start_ts', ascending=True).reset_index(drop=True)
        
        # Check minimum rows
        if len(df) < self.min_candles_required:
            return None, {
                "error": "insufficient_rows",
                "message": f"Need at least {self.min_candles_required} candles, got {len(df)}",
                "candles_found": len(df)
            }
        
        # Update metadata with actual data stats
        metadata.update({
            "rows": len(df),
            "start_date": df['start_ts'].iloc[0] if len(df) > 0 else None,
            "end_date": df['start_ts'].iloc[-1] if len(df) > 0 else None,
            "has_gaps": self._check_for_gaps(df, timeframe),
            "price_range": {
                "min": float(df['low'].min()),
                "max": float(df['high'].max()),
                "current": float(df['close'].iloc[-1])
            }
        })
        
        logger.info(
            f"Loaded training window for {symbol}/{timeframe}: {len(df)} candles "
            f"from {metadata['start_date']} to {metadata['end_date']}"
        )
        
        return df, metadata
    
    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        days: int
    ) -> Tuple[List[Dict], Dict]:
        """Fetch candles from database or fallback to data fetcher"""
        db = SessionLocal()
        metadata = {
            "source": "database",
            "symbol": symbol,
            "timeframe": timeframe,
            "days_requested": days
        }
        
        try:
            # Calculate cutoff date
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Query database
            candles = db.query(Candle).filter(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe,
                Candle.start_ts >= cutoff
            ).order_by(Candle.start_ts.asc()).all()
            
            if candles:
                metadata["candles_from_db"] = len(candles)
                return [c.to_dict() for c in candles], metadata
            
            # Fallback to Yahoo Finance
            logger.info(f"No DB data for {symbol}/{timeframe}, fetching from Yahoo Finance")
            metadata["source"] = "yahoo_finance"
            
            from backend.utils.data_fetcher import data_fetcher
            
            # Map days to period
            period_map = {
                "1m": "5d", "5m": "60d", "15m": "60d", "1h": "730d",
                "4h": "730d", "1d": "2000d", "1wk": "max", "1mo": "max"
            }
            period = period_map.get(timeframe, "60d")
            
            fetched_candles = await data_fetcher.fetch_candles(
                symbol=symbol,
                interval=timeframe,
                period=period
            )
            
            if fetched_candles:
                metadata["candles_from_yahoo"] = len(fetched_candles)
                # Store in DB for future use
                self._store_candles_to_db(symbol, timeframe, fetched_candles, db)
            
            return fetched_candles if fetched_candles else [], metadata
            
        finally:
            db.close()
    
    def _store_candles_to_db(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Dict],
        db
    ):
        """Store fetched candles to database"""
        try:
            for candle_data in candles:
                candle_dict = candle_data.copy()
                # Convert start_ts if needed
                if isinstance(candle_dict.get('start_ts'), str):
                    candle_dict['start_ts'] = datetime.fromisoformat(
                        candle_dict['start_ts'].replace('Z', '+00:00')
                    )
                
                # Check if candle already exists
                existing = db.query(Candle).filter(
                    Candle.symbol == symbol,
                    Candle.timeframe == timeframe,
                    Candle.start_ts == candle_dict['start_ts']
                ).first()
                
                if not existing:
                    candle = Candle(
                        symbol=symbol,
                        timeframe=timeframe,
                        **candle_dict
                    )
                    db.add(candle)
            
            db.commit()
            logger.info(f"Stored {len(candles)} candles to DB for {symbol}/{timeframe}")
        except Exception as e:
            logger.error(f"Failed to store candles to DB: {e}")
            db.rollback()
    
    def _validate_schema(self, df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """Validate that DataFrame has all required columns"""
        missing = set(self.required_columns) - set(df.columns)
        if missing:
            return False, f"Missing required columns: {missing}"
        return True, None
    
    def _validate_data_quality(self, df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """Validate data quality (NaN, Inf, negative prices, etc)"""
        issues = []
        
        # Check for NaN values
        nan_counts = df[self.required_columns].isna().sum()
        if nan_counts.any():
            issues.append(f"NaN values found: {nan_counts[nan_counts > 0].to_dict()}")
        
        # Check for infinite values
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if not np.isfinite(df[col]).all():
                issues.append(f"Infinite values in {col}")
        
        # Check for negative prices
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if (df[col] < 0).any():
                issues.append(f"Negative prices in {col}")
        
        # Check for OHLC relationships
        invalid_ohlc = (
            (df['high'] < df['low']) |
            (df['close'] < df['low']) |
            (df['close'] > df['high']) |
            (df['open'] < df['low']) |
            (df['open'] > df['high'])
        ).sum()
        
        if invalid_ohlc > 0:
            issues.append(f"{invalid_ohlc} candles with invalid OHLC relationships")
        
        if issues:
            return False, "; ".join(issues)
        
        return True, None
    
    def _check_for_gaps(self, df: pd.DataFrame, timeframe: str) -> bool:
        """Check if there are significant gaps in the time series"""
        if len(df) < 2:
            return False
        
        # Map timeframe to expected delta
        timeframe_deltas = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1),
            "1wk": timedelta(weeks=1),
            "1mo": timedelta(days=30)
        }
        
        expected_delta = timeframe_deltas.get(timeframe)
        if not expected_delta:
            return False
        
        # Convert to datetime if string
        timestamps = pd.to_datetime(df['start_ts'])
        diffs = timestamps.diff()[1:]  # Skip first NaT
        
        # Allow 2x the expected delta as tolerance (for weekends, holidays)
        max_gap = expected_delta * 2
        gaps = (diffs > max_gap).sum()
        
        return gaps > 0


# Global instance
ml_data_loader = MLDataLoader()


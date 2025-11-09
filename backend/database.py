"""
Database models and connection.
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, Text, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL - use config if available, otherwise default
try:
    from backend.config import settings
    DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
except ImportError:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")

# For SQLite, resolve relative paths to absolute paths to ensure consistency
# This ensures migration script and SQLAlchemy use the same database file
if "sqlite" in DATABASE_URL:
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("./"):
        # Resolve relative to project root (same as migrate_db.py)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, db_path[2:])
        DATABASE_URL = f"sqlite:///{db_path}"
    elif not os.path.isabs(db_path):
        # Resolve relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(project_root, db_path)
        DATABASE_URL = f"sqlite:///{db_path}"

# Create engine with proper connection pooling
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,  # Set to True for SQL query debugging
    pool_size=20,  # Increased from default 5
    max_overflow=40,  # Increased from default 10
    pool_timeout=60,  # Increased from default 30
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True  # Verify connections before using them
)

# Store the resolved database path for debugging
RESOLVED_DB_PATH = DATABASE_URL.replace("sqlite:///", "") if "sqlite" in DATABASE_URL else None

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()


class Candle(Base):
    """Candle/OHLCV data"""
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'start_ts', name='uq_candles_symbol_timeframe_start_ts'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    start_ts = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "start_ts": self.start_ts.isoformat() if self.start_ts else None,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class Prediction(Base):
    """Prediction results"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    produced_at = Column(DateTime, index=True)
    horizon_minutes = Column(Integer)
    predicted_series = Column(JSON)  # List of {ts, price}
    confidence = Column(Float)
    bot_contributions = Column(JSON)  # Bot weights/contributions
    trend = Column(JSON)  # Trend metadata from Freddy merger
    
    # Enhanced logging for audit trail
    bot_raw_outputs = Column(JSON)  # Per-bot predictions before ensemble merge
    validation_flags = Column(JSON)  # Was sanitized? clipped? rejected?
    feature_snapshot = Column(JSON)  # Key indicator values at prediction time
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "produced_at": self.produced_at.isoformat() if self.produced_at else None,
            "horizon_minutes": self.horizon_minutes,
            "predicted_series": self.predicted_series,
            "confidence": self.confidence,
            "bot_contributions": self.bot_contributions,
            "trend": self.trend if hasattr(self, 'trend') else None,
            "bot_raw_outputs": self.bot_raw_outputs if hasattr(self, 'bot_raw_outputs') else None,
            "validation_flags": self.validation_flags if hasattr(self, 'validation_flags') else None,
            "feature_snapshot": self.feature_snapshot if hasattr(self, 'feature_snapshot') else None
        }


class PredictionEvaluation(Base):
    """Evaluation of prediction accuracy"""
    __tablename__ = "prediction_evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    evaluated_at = Column(DateTime, index=True)
    rmse = Column(Float)
    mae = Column(Float)
    mape = Column(Float)
    directional_accuracy = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "rmse": self.rmse,
            "mae": self.mae,
            "mape": self.mape,
            "directional_accuracy": self.directional_accuracy
        }


class ModelTrainingRecord(Base):
    """Track model training history and metadata"""
    __tablename__ = "model_training_records"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    timeframe = Column(String, index=True, nullable=False)
    bot_name = Column(String, index=True, nullable=False)  # 'lstm_bot', 'transformer_bot', etc.
    
    # Training metadata
    trained_at = Column(DateTime, default=datetime.utcnow, index=True)
    training_duration_seconds = Column(Float)
    data_points_used = Column(Integer)
    training_period = Column(String)  # '60d', '730d', etc.
    epochs = Column(Integer)
    
    # Model performance
    training_loss = Column(Float)
    validation_loss = Column(Float)
    test_rmse = Column(Float)
    test_mae = Column(Float)
    
    # Model file path
    model_path = Column(String)
    model_size_mb = Column(Float)
    
    # Status
    status = Column(String, default='queued')  # 'queued', 'running', 'completed', 'failed', 'active', 'archived'
    error_message = Column(Text, nullable=True)
    
    # Progress tracking (for incremental training)
    progress_percent = Column(Float, default=0.0)
    current_batch = Column(Integer, default=0)
    total_batches = Column(Integer, default=1)
    progress_message = Column(Text, nullable=True)
    
    # Configuration
    config = Column(JSON)  # Store hyperparameters, settings
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "bot_name": self.bot_name,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "training_duration_seconds": self.training_duration_seconds,
            "data_points_used": self.data_points_used,
            "training_period": self.training_period,
            "epochs": self.epochs,
            "training_loss": self.training_loss,
            "validation_loss": self.validation_loss,
            "test_rmse": self.test_rmse,
            "test_mae": self.test_mae,
            "model_path": self.model_path,
            "model_size_mb": self.model_size_mb,
            "status": self.status,
            "error_message": self.error_message,
            "progress_percent": self.progress_percent,
            "current_batch": self.current_batch,
            "total_batches": self.total_batches,
            "progress_message": self.progress_message,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TrendPrediction(Base):
    """Store trend predictions for individual stock predictions"""
    __tablename__ = "trend_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, index=True)  # Links to Prediction.id
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    produced_at = Column(DateTime, index=True)
    
    # Trend metadata
    trend_direction = Column(Integer)  # -1, 0, 1
    trend_direction_str = Column(String)  # "up", "down", "neutral"
    trend_strength = Column(Float)  # 0-1
    trend_strength_category = Column(String)  # "weak", "moderate", "strong"
    trend_duration_minutes = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "prediction_id": self.prediction_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "produced_at": self.produced_at.isoformat() if self.produced_at else None,
            "trend_direction": self.trend_direction,
            "trend_direction_str": self.trend_direction_str,
            "trend_strength": self.trend_strength,
            "trend_strength_category": self.trend_strength_category,
            "trend_duration_minutes": self.trend_duration_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class MarketPrediction(Base):
    """Store market index predictions (Nifty50, Sensex)"""
    __tablename__ = "market_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    index_symbol = Column(String, index=True)  # "^NSEI" or "^BSESN"
    index_name = Column(String)  # "Nifty50" or "Sensex"
    timeframe = Column(String, index=True)
    produced_at = Column(DateTime, index=True)
    horizon_minutes = Column(Integer)
    
    # Prediction data
    predicted_series = Column(JSON)  # List of {ts, price}
    confidence = Column(Float)
    
    # Trend metadata
    trend_direction = Column(Integer)
    trend_direction_str = Column(String)
    trend_strength = Column(Float)
    trend_strength_category = Column(String)
    trend_duration_minutes = Column(Integer)
    
    # Current index value
    current_value = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "index_symbol": self.index_symbol,
            "index_name": self.index_name,
            "timeframe": self.timeframe,
            "produced_at": self.produced_at.isoformat() if self.produced_at else None,
            "horizon_minutes": self.horizon_minutes,
            "predicted_series": self.predicted_series,
            "confidence": self.confidence,
            "trend_direction": self.trend_direction,
            "trend_direction_str": self.trend_direction_str,
            "trend_strength": self.trend_strength,
            "trend_strength_category": self.trend_strength_category,
            "trend_duration_minutes": self.trend_duration_minutes,
            "current_value": self.current_value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class MarketSentiment(Base):
    """Store market sentiment predictions"""
    __tablename__ = "market_sentiment"
    
    id = Column(Integer, primary_key=True, index=True)
    produced_at = Column(DateTime, index=True)
    
    # Sentiment classification
    sentiment = Column(String)  # "bullish", "bearish", "neutral"
    sentiment_value = Column(Integer)  # 1, -1, 0
    sentiment_strength = Column(Float)  # 0-1
    confidence = Column(Float)
    
    # Supporting data
    nifty_trend = Column(Integer)
    sensex_trend = Column(Integer)
    nifty_price = Column(Float)
    sensex_price = Column(Float)
    indices_agreement = Column(Boolean)
    nifty_confidence = Column(Float)
    sensex_confidence = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "produced_at": self.produced_at.isoformat() if self.produced_at else None,
            "sentiment": self.sentiment,
            "sentiment_value": self.sentiment_value,
            "sentiment_strength": self.sentiment_strength,
            "confidence": self.confidence,
            "nifty_trend": self.nifty_trend,
            "sensex_trend": self.sensex_trend,
            "nifty_price": self.nifty_price,
            "sensex_price": self.sensex_price,
            "indices_agreement": self.indices_agreement,
            "nifty_confidence": self.nifty_confidence,
            "sensex_confidence": self.sensex_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class BacktestResult(Base):
    """Backtest execution results"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    strategy_name = Column(String)
    start_date = Column(DateTime, index=True)
    end_date = Column(DateTime, index=True)
    initial_capital = Column(Float)
    final_value = Column(Float)
    
    # Performance metrics
    total_return_pct = Column(Float)
    cagr_pct = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown_pct = Column(Float)
    volatility_pct = Column(Float)
    
    # Trading statistics
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    
    # Full results stored as JSON
    results_json = Column(JSON)  # Full backtest results
    equity_curve = Column(JSON)  # Portfolio value over time
    trades = Column(JSON)  # List of all trades
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": self.initial_capital,
            "final_value": self.final_value,
            "total_return_pct": self.total_return_pct,
            "cagr_pct": self.cagr_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown_pct": self.max_drawdown_pct,
            "volatility_pct": self.volatility_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "results_json": self.results_json,
            "equity_curve": self.equity_curve,
            "trades": self.trades,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables
def init_db():
    """Initialize database tables"""
    # Print database path for debugging
    print(f"📁 Database file: {DATABASE_URL}")
    if RESOLVED_DB_PATH:
        print(f"📁 Resolved database path: {RESOLVED_DB_PATH}")
        import os
        if os.path.exists(RESOLVED_DB_PATH):
            print(f"✅ Database file exists")
        else:
            print(f"❌ Database file does NOT exist at resolved path!")
    
    # Run migration FIRST to ensure schema is up to date
    try:
        from backend.migrate_db import migrate_database
        migrate_database()
    except Exception as e:
        # Migration errors are non-fatal - table might already exist or migration might fail
        # But we still want to continue
        print(f"Note: Migration check failed (non-fatal): {e}")
    
    # Create tables - this ensures SQLAlchemy metadata matches database schema
    # Note: create_all() won't modify existing tables, but it will create missing ones
    Base.metadata.create_all(bind=engine)
    
    # Verify SQLAlchemy can see the columns by testing a connection
    try:
        with engine.connect() as conn:
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            
            # Check if table exists and what columns it has
            if 'prediction_evaluations' in inspector.get_table_names():
                db_columns = {col['name'] for col in inspector.get_columns('prediction_evaluations')}
                model_columns = {col.name for col in Base.metadata.tables['prediction_evaluations'].columns}
                
                print(f"✅ Database columns: {sorted(db_columns)}")
                print(f"✅ Model columns: {sorted(model_columns)}")
                
                # Verify symbol and timeframe exist
                if 'symbol' not in db_columns or 'timeframe' not in db_columns:
                    print(f"❌ ERROR: Database is missing symbol or timeframe columns!")
                    print(f"   Missing: {({'symbol', 'timeframe'} - db_columns)}")
                else:
                    print(f"✅ Database has symbol and timeframe columns")
                    
                # Test a simple query to verify columns are accessible
                result = conn.execute(text("SELECT COUNT(*) FROM prediction_evaluations"))
                count = result.scalar()
                print(f"✅ Test query successful - {count} evaluation records found")
                
                # Test querying symbol column directly
                try:
                    result = conn.execute(text("SELECT symbol FROM prediction_evaluations LIMIT 1"))
                    result.fetchone()
                    print(f"✅ Direct symbol column query successful")
                except Exception as e:
                    print(f"❌ Direct symbol column query failed: {e}")
    except Exception as e:
        print(f"⚠️  Database verification failed: {e}")
        import traceback
        traceback.print_exc()
    
    # After migration, clear connection pool to force fresh connections
    # This ensures SQLAlchemy connections see the updated schema
    engine.dispose(close=True)
    
    print("✅ Database tables created successfully")


if __name__ == "__main__":
    init_db()

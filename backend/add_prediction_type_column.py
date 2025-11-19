"""
Migration script to add prediction_type column to predictions table
and backfill existing predictions with inferred types.
"""
import sqlite3
import json
import os
from pathlib import Path

# Get database URL from config (same as database.py)
try:
    from backend.config import settings
    DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
except ImportError:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_predictions.db")

# Extract path from SQLite URL - handle both relative and absolute paths
db_path = DATABASE_URL.replace("sqlite:///", "")
if db_path.startswith("./"):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path[2:])
elif not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)

DB_PATH = Path(db_path)

def determine_prediction_type_from_bot_contributions(bot_contributions):
    """
    Infer prediction type from bot_contributions JSON.
    Similar logic to backend/routes/prediction.py
    """
    if not bot_contributions:
        return "ensemble"
    
    try:
        if isinstance(bot_contributions, str):
            bot_contributions = json.loads(bot_contributions)
        
        if not isinstance(bot_contributions, dict):
            return "ensemble"
        
        bot_names = set(bot_contributions.keys())
        
        # Technical analysis bots
        technical_bots = {"rsi_bot", "macd_bot", "ma_bot"}
        # ML bots
        ml_bots = {"ml_bot", "ensemble_bot"}
        # Deep learning bots
        dl_bots = {"lstm_bot", "transformer_bot"}
        
        # Check if only technical bots
        if bot_names.issubset(technical_bots) and len(bot_names) > 0:
            return "technical"
        
        # Check if only ML bots
        if bot_names.issubset(ml_bots) and not bot_names.intersection(dl_bots) and not bot_names.intersection(technical_bots):
            return "ml"
        
        # Check if only LSTM
        if bot_names == {"lstm_bot"}:
            return "lstm"
        
        # Check if only Transformer
        if bot_names == {"transformer_bot"}:
            return "transformer"
        
        # Check if both LSTM and Transformer
        if bot_names.issubset(dl_bots) and len(bot_names) == 2:
            return "deep_learning"
        
        # If all bots or mixed selection
        all_bots = technical_bots | ml_bots | dl_bots
        if bot_names == all_bots or len(bot_names) >= 5:
            return "all"
        
        return "ensemble"
    except Exception as e:
        print(f"Error determining prediction type: {e}")
        return "ensemble"


def migrate():
    """Add prediction_type column and backfill data"""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(predictions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "prediction_type" in columns:
            print("Column 'prediction_type' already exists. Skipping migration.")
            return
        
        print("Adding prediction_type column...")
        cursor.execute("ALTER TABLE predictions ADD COLUMN prediction_type VARCHAR(50) DEFAULT 'ensemble'")
        
        # Create index
        print("Creating index on prediction_type...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_prediction_type ON predictions(prediction_type)")
        
        # Backfill existing predictions
        print("Backfilling existing predictions...")
        cursor.execute("SELECT id, bot_contributions FROM predictions WHERE prediction_type IS NULL OR prediction_type = 'ensemble'")
        rows = cursor.fetchall()
        
        updated_count = 0
        for row_id, bot_contributions_json in rows:
            pred_type = determine_prediction_type_from_bot_contributions(bot_contributions_json)
            cursor.execute(
                "UPDATE predictions SET prediction_type = ? WHERE id = ?",
                (pred_type, row_id)
            )
            updated_count += 1
        
        conn.commit()
        print(f"✅ Migration complete! Updated {updated_count} predictions.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()


"""
Database migration script to add progress tracking columns to model_training_records.
"""
import sqlite3
import os
from pathlib import Path

# Get database URL from config (same as database.py)
try:
    from backend.config import settings
    DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
except ImportError:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")

# Extract path from SQLite URL - handle both relative and absolute paths
db_path = DATABASE_URL.replace("sqlite:///", "")
if db_path.startswith("./"):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path[2:])
elif not os.path.isabs(db_path):
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)

def migrate_database():
    """Add missing columns to database tables if they don't exist"""
    if not os.path.exists(db_path):
        print(f"Database file {db_path} doesn't exist yet. It will be created with new schema.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Migrate model_training_records table
        try:
            cursor.execute("PRAGMA table_info(model_training_records)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'progress_percent' not in columns:
                print("Adding progress_percent column to model_training_records...")
                cursor.execute("ALTER TABLE model_training_records ADD COLUMN progress_percent REAL DEFAULT 0.0")
            
            if 'current_batch' not in columns:
                print("Adding current_batch column to model_training_records...")
                cursor.execute("ALTER TABLE model_training_records ADD COLUMN current_batch INTEGER DEFAULT 0")
            
            if 'total_batches' not in columns:
                print("Adding total_batches column to model_training_records...")
                cursor.execute("ALTER TABLE model_training_records ADD COLUMN total_batches INTEGER DEFAULT 1")
            
            if 'progress_message' not in columns:
                print("Adding progress_message column to model_training_records...")
                cursor.execute("ALTER TABLE model_training_records ADD COLUMN progress_message TEXT")
        except Exception as e:
            print(f"Note: model_training_records migration skipped: {e}")
        
        # Migrate predictions table - add trend column
        try:
            cursor.execute("PRAGMA table_info(predictions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'trend' not in columns:
                print("Adding trend column to predictions table...")
                cursor.execute("ALTER TABLE predictions ADD COLUMN trend TEXT")
                print("✅ Added trend column to predictions table")
            else:
                print("✅ trend column already exists in predictions table")
            
            # Add prediction_type column
            if 'prediction_type' not in columns:
                print("Adding prediction_type column to predictions table...")
                cursor.execute("ALTER TABLE predictions ADD COLUMN prediction_type VARCHAR(50) DEFAULT 'ensemble'")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_prediction_type ON predictions(prediction_type)")
                print("✅ Added prediction_type column to predictions table")
                
                # Backfill existing predictions with inferred types
                print("Backfilling prediction_type for existing predictions...")
                try:
                    import json
                    def determine_prediction_type_from_bot_contributions(bot_contributions):
                        """Infer prediction type from bot_contributions JSON"""
                        if not bot_contributions:
                            return "ensemble"
                        try:
                            if isinstance(bot_contributions, str):
                                bot_contributions = json.loads(bot_contributions)
                            if not isinstance(bot_contributions, dict):
                                return "ensemble"
                            bot_names = set(bot_contributions.keys())
                            technical_bots = {"rsi_bot", "macd_bot", "ma_bot"}
                            ml_bots = {"ml_bot", "ensemble_bot"}
                            dl_bots = {"lstm_bot", "transformer_bot"}
                            if bot_names.issubset(technical_bots) and len(bot_names) > 0:
                                return "technical"
                            if bot_names.issubset(ml_bots) and not bot_names.intersection(dl_bots) and not bot_names.intersection(technical_bots):
                                return "ml"
                            if bot_names == {"lstm_bot"}:
                                return "lstm"
                            if bot_names == {"transformer_bot"}:
                                return "transformer"
                            if bot_names.issubset(dl_bots) and len(bot_names) == 2:
                                return "deep_learning"
                            all_bots = technical_bots | ml_bots | dl_bots
                            if bot_names == all_bots or len(bot_names) >= 5:
                                return "all"
                            return "ensemble"
                        except Exception:
                            return "ensemble"
                    
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
                    print(f"✅ Backfilled {updated_count} existing predictions with prediction_type")
                except Exception as e:
                    print(f"⚠️  Error backfilling prediction_type: {e} (non-fatal)")
            else:
                print("✅ prediction_type column already exists in predictions table")
        except Exception as e:
            print(f"Note: predictions table migration skipped (table might not exist yet): {e}")
        
        # Migrate backtest_results table - check if it exists and create if needed
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_results'")
            if not cursor.fetchone():
                print("Note: backtest_results table will be created on next startup")
        except Exception as e:
            print(f"Note: Could not check backtest_results table: {e}")
        
        # Migrate prediction_evaluations table - add symbol and timeframe columns if missing
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_evaluations'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(prediction_evaluations)")
                columns = [row[1] for row in cursor.fetchall()]
                
                columns_added = False
                if 'symbol' not in columns:
                    print("Adding symbol column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN symbol TEXT")
                    columns_added = True
                
                if 'timeframe' not in columns:
                    print("Adding timeframe column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN timeframe TEXT")
                    columns_added = True
                
                if 'evaluated_at' not in columns:
                    print("Adding evaluated_at column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN evaluated_at TIMESTAMP")
                    columns_added = True
                
                # Add created_at if missing (it should exist per model but might be missing from old tables)
                if 'created_at' not in columns:
                    print("Adding created_at column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    columns_added = True
                
                # Add metric columns if missing (rmse, mae, mape, directional_accuracy)
                # These are REQUIRED columns that must exist for the model to work
                if 'rmse' not in columns:
                    print("Adding rmse column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN rmse REAL")
                    columns_added = True
                    print("✅ Added rmse column")
                
                if 'mae' not in columns:
                    print("Adding mae column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN mae REAL")
                    columns_added = True
                    print("✅ Added mae column")
                
                if 'mape' not in columns:
                    print("Adding mape column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN mape REAL")
                    columns_added = True
                    print("✅ Added mape column")
                
                if 'directional_accuracy' not in columns:
                    print("Adding directional_accuracy column to prediction_evaluations...")
                    cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN directional_accuracy REAL")
                    columns_added = True
                    print("✅ Added directional_accuracy column")
                
                # Migrate data from old metrics JSON column to new individual columns if they exist
                # This handles the case where old records have metrics in JSON format
                if 'metrics' in columns:
                    print("Migrating data from metrics JSON column to individual columns...")
                    try:
                        # First, re-fetch columns to ensure we have the new columns
                        cursor.execute("PRAGMA table_info(prediction_evaluations)")
                        updated_columns = [row[1] for row in cursor.fetchall()]
                        
                        # Only migrate if the target columns exist
                        if 'rmse' in updated_columns and 'mae' in updated_columns:
                            cursor.execute("""
                                UPDATE prediction_evaluations 
                                SET rmse = CASE 
                                    WHEN json_extract(metrics, '$.rmse') IS NOT NULL 
                                    THEN CAST(json_extract(metrics, '$.rmse') AS REAL)
                                    ELSE rmse END,
                                mae = CASE 
                                    WHEN json_extract(metrics, '$.mae') IS NOT NULL 
                                    THEN CAST(json_extract(metrics, '$.mae') AS REAL)
                                    ELSE mae END,
                                mape = CASE 
                                    WHEN json_extract(metrics, '$.mape') IS NOT NULL 
                                    THEN CAST(json_extract(metrics, '$.mape') AS REAL)
                                    ELSE mape END,
                                directional_accuracy = CASE 
                                    WHEN json_extract(metrics, '$.directional_accuracy') IS NOT NULL 
                                    THEN CAST(json_extract(metrics, '$.directional_accuracy') AS REAL)
                                    ELSE directional_accuracy END
                                WHERE metrics IS NOT NULL AND metrics != 'null' AND metrics != ''
                            """)
                            rows_updated = cursor.rowcount
                            print(f"✅ Migrated {rows_updated} records from metrics JSON to individual columns")
                        else:
                            print("⚠️  Metric columns not found, skipping data migration")
                    except Exception as e:
                        print(f"⚠️  Error migrating metrics data: {e}. Continuing anyway.")
                
                # Re-fetch columns after any additions to get accurate column list
                cursor.execute("PRAGMA table_info(prediction_evaluations)")
                final_columns = [row[1] for row in cursor.fetchall()]
                final_column_names = {col for col in final_columns}
                
                if columns_added:
                    print(f"✅ Columns after migration: {sorted(final_column_names)}")
                
                # Verify required columns exist
                required_columns = {'rmse', 'mae', 'mape', 'directional_accuracy', 'symbol', 'timeframe', 'evaluated_at'}
                missing_columns = required_columns - final_column_names
                if missing_columns:
                    print(f"❌ WARNING: Missing required columns after migration: {missing_columns}")
                    print(f"   Attempting to add missing columns...")
                    for col_name in missing_columns:
                        if col_name == 'rmse':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN rmse REAL")
                        elif col_name == 'mae':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN mae REAL")
                        elif col_name == 'mape':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN mape REAL")
                        elif col_name == 'directional_accuracy':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN directional_accuracy REAL")
                        elif col_name == 'symbol':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN symbol TEXT")
                        elif col_name == 'timeframe':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN timeframe TEXT")
                        elif col_name == 'evaluated_at':
                            cursor.execute("ALTER TABLE prediction_evaluations ADD COLUMN evaluated_at TIMESTAMP")
                    conn.commit()
                    print(f"✅ Added missing columns: {missing_columns}")
                else:
                    print(f"✅ All required columns exist: {sorted(required_columns)}")
                
                # Check if created_at exists before using it in UPDATE
                has_created_at = 'created_at' in final_column_names
                
                # Update existing records to populate symbol and timeframe from predictions table
                # Only update if columns were just added or if values are NULL
                if has_created_at:
                    cursor.execute("""
                        UPDATE prediction_evaluations 
                        SET symbol = (SELECT symbol FROM predictions WHERE predictions.id = prediction_evaluations.prediction_id),
                            timeframe = (SELECT timeframe FROM predictions WHERE predictions.id = prediction_evaluations.prediction_id),
                            evaluated_at = COALESCE(evaluated_at, created_at)
                        WHERE symbol IS NULL OR timeframe IS NULL
                    """)
                else:
                    cursor.execute("""
                        UPDATE prediction_evaluations 
                        SET symbol = (SELECT symbol FROM predictions WHERE predictions.id = prediction_evaluations.prediction_id),
                            timeframe = (SELECT timeframe FROM predictions WHERE predictions.id = prediction_evaluations.prediction_id),
                            evaluated_at = datetime('now')
                        WHERE symbol IS NULL OR timeframe IS NULL
                    """)
                print("✅ Updated existing prediction_evaluations records with symbol and timeframe")
        except Exception as e:
            print(f"Note: prediction_evaluations migration skipped: {e}")
        
        conn.commit()
        print("✅ Database migration completed successfully")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()


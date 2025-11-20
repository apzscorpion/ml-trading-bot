"""
Script to clear old models with feature shape mismatches.
Run this before retraining models to ensure clean slate.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config import settings

def main():
    print("=" * 80)
    print("CLEAR OLD MODELS WITH FEATURE MISMATCH")
    print("=" * 80)
    
    # Get model storage path (relative to backend directory)
    backend_dir = Path(__file__).parent
    model_base_relative = Path(settings.model_storage_path)
    if model_base_relative.is_absolute():
        model_base = model_base_relative
    else:
        model_base = (backend_dir / model_base_relative).resolve()
    print(f"\nModel storage path: {model_base}")
    
    if not model_base.exists():
        print(f"❌ Model directory does not exist: {model_base}")
        return
    
    # Models to clear (those with shape mismatches)
    model_patterns = [
        "lstm_model*.keras",
        "lstm_scalers*.pkl",
        "transformer_model*.keras",
        "transformer_scaler*.pkl",
        "ensemble_models*.pkl"
    ]
    
    files_to_delete = []
    for pattern in model_patterns:
        files_to_delete.extend(model_base.glob(pattern))
    
    if not files_to_delete:
        print("\n✅ No model files found to delete")
        return
    
    print(f"\n📋 Found {len(files_to_delete)} model files:")
    for f in files_to_delete:
        print(f"   - {f.name}")
    
    # Ask for confirmation
    response = input("\n⚠️  Delete all these model files? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    # Delete files
    deleted_count = 0
    for f in files_to_delete:
        try:
            f.unlink()
            print(f"✅ Deleted: {f.name}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Error deleting {f.name}: {e}")
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully deleted {deleted_count} model files")
    print(f"{'='*80}")
    print("\nNext steps:")
    print("1. Start the backend server: cd backend && source venv/bin/activate && python main.py")
    print("2. Open frontend and select a symbol (e.g., TCS.NS)")
    print("3. Click 'Train DL Models' button to retrain LSTM and Transformer")
    print("4. Click 'Retrain All Models' to retrain Ensemble as well")
    print("\nOr use the API:")
    print("  curl -X POST http://localhost:8000/api/prediction/train \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"symbol\": \"TCS.NS\", \"timeframe\": \"5m\", \"bot_name\": \"lstm_bot\", \"epochs\": 50}'")

if __name__ == "__main__":
    main()


"""
Test script for AI-powered training system.
Run this to test the new AI training capabilities.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ml.ai_training_orchestrator import ai_training_orchestrator
from backend.services.freddy_ai_service import freddy_ai_service
from backend.config import settings


async def test_ai_training():
    """Test AI training system"""
    
    print("=" * 80)
    print("🤖 AI-POWERED TRAINING TEST")
    print("=" * 80)
    
    # Check if Freddy AI is enabled
    print(f"\n1. Checking Freddy AI configuration...")
    if not settings.freddy_enabled:
        print("❌ Freddy AI is DISABLED in config")
        print("   Set FREDDY_ENABLED=true in .env")
        return
    
    if not settings.freddy_api_key:
        print("❌ Freddy API key is NOT set")
        print("   Set FREDDY_API_KEY in .env")
        return
    
    print(f"✅ Freddy AI is enabled")
    print(f"   API Key: {settings.freddy_api_key[:10]}...")
    print(f"   Org ID: {settings.freddy_organization_id}")
    print(f"   Assistant ID: {settings.freddy_assistant_id}")
    
    # Test data fetching
    print(f"\n2. Testing latest data fetching...")
    symbol = "INFY.NS"
    timeframe = "5m"
    
    df = await ai_training_orchestrator.fetch_latest_training_data(
        symbol=symbol,
        timeframe=timeframe,
        lookback_days=7  # Small for testing
    )
    
    if df.empty:
        print(f"❌ Failed to fetch data for {symbol}")
        return
    
    print(f"✅ Fetched {len(df)} candles for {symbol}/{timeframe}")
    print(f"   Date range: {df['start_ts'].min()} to {df['start_ts'].max()}")
    
    # Test Freddy AI label generation
    print(f"\n3. Testing Freddy AI label generation...")
    
    if len(df) < 50:
        print("❌ Not enough data for testing")
        return
    
    # Get a sample point
    sample_idx = len(df) // 2
    current_price = float(df.iloc[sample_idx]['close'])
    context_candles = df.iloc[max(0, sample_idx-50):sample_idx+1].to_dict('records')
    
    print(f"   Testing with price: ₹{current_price:.2f}")
    
    ai_label = await ai_training_orchestrator.generate_ai_labels_for_point(
        symbol=symbol,
        current_price=current_price,
        candles_context=context_candles
    )
    
    if ai_label is None:
        print("❌ Failed to generate AI labels")
        print("   This might be due to:")
        print("   - Invalid Freddy API credentials")
        print("   - Network issues")
        print("   - Freddy API rate limits")
        return
    
    print(f"✅ Generated AI labels:")
    print(f"   Current Price: ₹{current_price:.2f}")
    print(f"   Target Price: ₹{ai_label.target_price:.2f} ({((ai_label.target_price/current_price - 1)*100):.2f}%)")
    print(f"   Stop Loss: ₹{ai_label.stop_loss:.2f} ({((ai_label.stop_loss/current_price - 1)*100):.2f}%)")
    print(f"   Confidence: {ai_label.confidence:.2%}")
    print(f"   Recommendation: {ai_label.recommendation}")
    print(f"   Technical Bias: {ai_label.technical_bias}")
    if ai_label.news_sentiment:
        print(f"   News Sentiment: {ai_label.news_sentiment}")
    
    # Test full dataset generation (small)
    print(f"\n4. Testing full AI dataset generation (small test)...")
    print(f"   Generating 5 AI-labeled training points...")
    
    training_points, metadata = await ai_training_orchestrator.generate_training_dataset(
        symbol=symbol,
        timeframe=timeframe,
        lookback_days=7,
        sample_points=5,  # Small for testing
        batch_size=2
    )
    
    if not training_points:
        print("❌ Failed to generate training dataset")
        return
    
    print(f"✅ Generated {len(training_points)} training points")
    print(f"   Success rate: {metadata['success_rate']*100:.1f}%")
    print(f"   Freddy API calls: {metadata['freddy_calls']}")
    print(f"   Duration: {metadata['completed_at']}")
    
    # Show sample training points
    print(f"\n5. Sample training points:")
    for i, point in enumerate(training_points[:3]):
        print(f"\n   Point {i+1}:")
        print(f"   ├─ Price: ₹{point.features.get('close', 0):.2f}")
        print(f"   ├─ Target: ₹{point.target_price:.2f}")
        print(f"   ├─ Stop Loss: ₹{point.stop_loss:.2f}")
        print(f"   ├─ Confidence: {point.confidence:.2%}")
        print(f"   └─ Recommendation: {point.recommendation}")
    
    # Convert to training format
    print(f"\n6. Converting to model training format...")
    X, y, conversion_metadata = ai_training_orchestrator.convert_to_training_format(
        training_points
    )
    
    print(f"✅ Converted to training arrays:")
    print(f"   X shape: {X.shape}")
    print(f"   y shape: {y.shape}")
    print(f"   Features: {conversion_metadata['n_features']}")
    print(f"   Feature names: {conversion_metadata['feature_names'][:5]}... (showing first 5)")
    
    # Summary
    print("\n" + "=" * 80)
    print("🎉 AI TRAINING TEST COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("\nWhat was tested:")
    print("✅ Freddy AI configuration")
    print("✅ Real-time data fetching")
    print("✅ AI label generation (targets, stop-losses)")
    print("✅ Full training dataset generation")
    print("✅ Conversion to model training format")
    
    print("\nNext steps:")
    print("1. Use /api/ai-training/generate-dataset to train models")
    print("2. Or trigger automatically by opening charts in the UI")
    print("3. Monitor with: tail -f logs/backend.log | grep 'AI training'")
    
    print("\nExample API call:")
    print("""
    curl -X POST http://localhost:5000/api/ai-training/generate-dataset \\
      -H "Content-Type: application/json" \\
      -d '{
        "symbol": "INFY.NS",
        "timeframe": "5m",
        "lookback_days": 30,
        "sample_points": 100,
        "bot_names": ["lstm_bot", "transformer_bot", "ensemble_bot"],
        "use_for_training": true
      }'
    """)


if __name__ == "__main__":
    try:
        asyncio.run(test_ai_training())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


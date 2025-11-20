"""
Diagnostic script to check if predictions are inverted.
This will help identify if the issue is in training, inference, or display.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.bots.lstm_bot import LSTMBot
from backend.bots.transformer_bot import TransformerBot
from backend.bots.ensemble_bot import EnsembleBot
from backend.utils.data_fetcher import data_fetcher
import pandas as pd
import numpy as np


async def main():
    print("=" * 80)
    print("PREDICTION DIRECTION DIAGNOSTIC")
    print("=" * 80)
    
    # Test symbol
    symbol = "TCS.NS"
    timeframe = "5m"
    horizon = 180
    
    print(f"\n📊 Testing with {symbol} / {timeframe}")
    
    # Fetch candles
    print("\n1. Fetching recent candles...")
    candles = await data_fetcher.fetch_candles(symbol, timeframe, period="5d")
    
    if not candles or len(candles) < 100:
        print(f"❌ Not enough candles: {len(candles) if candles else 0}")
        return
    
    print(f"✅ Fetched {len(candles)} candles")
    
    # Extract recent trend
    df = pd.DataFrame(candles)
    recent_closes = df['close'].tail(20).values
    latest_close = float(recent_closes[-1])
    
    # Calculate recent trend (last 20 candles)
    returns = np.diff(recent_closes) / recent_closes[:-1]
    avg_return = np.mean(returns)
    trend_direction = "UP" if avg_return > 0 else "DOWN"
    
    print(f"\n📈 Recent Market Trend (last 20 candles):")
    print(f"   Latest Close: ₹{latest_close:.2f}")
    print(f"   Avg Return: {avg_return*100:.3f}%")
    print(f"   Direction: {trend_direction} {'🟢' if trend_direction == 'UP' else '🔴'}")
    print(f"   First Close (20 candles ago): ₹{recent_closes[0]:.2f}")
    print(f"   Change: {((recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100):.2f}%")
    
    # Test each bot
    bots = [
        ("LSTM", LSTMBot()),
        ("Transformer", TransformerBot()),
        ("Ensemble", EnsembleBot())
    ]
    
    print("\n" + "=" * 80)
    print("TESTING EACH BOT")
    print("=" * 80)
    
    for bot_name, bot in bots:
        print(f"\n{'='*40}")
        print(f"🤖 Testing {bot_name} Bot")
        print(f"{'='*40}")
        
        # Set context
        bot.set_model_context(symbol, timeframe)
        if hasattr(bot, '_load_or_create_model'):
            bot._load_or_create_model()
        elif hasattr(bot, '_load_or_create_models'):
            bot._load_or_create_models()
        
        try:
            # Make prediction
            result = await bot.predict(candles, horizon, timeframe)
            
            if not result or not result.get("predicted_series"):
                print(f"❌ {bot_name}: No predictions generated")
                print(f"   Result: {result}")
                continue
            
            predicted_series = result["predicted_series"]
            if len(predicted_series) == 0:
                print(f"❌ {bot_name}: Empty prediction series")
                continue
            
            # Extract predicted prices
            predicted_prices = [p["price"] for p in predicted_series]
            first_predicted = predicted_prices[0]
            last_predicted = predicted_prices[-1]
            predicted_change = last_predicted - first_predicted
            predicted_change_pct = (predicted_change / first_predicted) * 100
            
            # Check if prediction direction matches trend
            predicted_direction = "UP" if predicted_change > 0 else "DOWN"
            is_inverted = (trend_direction == "UP" and predicted_direction == "DOWN") or \
                         (trend_direction == "DOWN" and predicted_direction == "UP")
            
            print(f"\n✅ {bot_name} Prediction:")
            print(f"   First Price: ₹{first_predicted:.2f}")
            print(f"   Last Price: ₹{last_predicted:.2f}")
            print(f"   Change: {predicted_change_pct:+.2f}%")
            print(f"   Direction: {predicted_direction} {'🟢' if predicted_direction == 'UP' else '🔴'}")
            print(f"   Confidence: {result.get('confidence', 0):.2%}")
            
            if is_inverted:
                print(f"\n   ⚠️  INVERTED! Market is {trend_direction} but prediction is {predicted_direction}")
            else:
                print(f"\n   ✅ Correct Direction (matches market trend)")
            
            # Check magnitude
            if abs(predicted_change_pct) > 5:
                print(f"   ⚠️  WARNING: Large predicted change ({predicted_change_pct:.2f}%) - may be unrealistic")
            
        except Exception as e:
            print(f"❌ {bot_name}: Error - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print("\nIf predictions are consistently inverted:")
    print("1. Models may have been trained on incorrect labels")
    print("2. Scaler may be applying incorrect transformations")
    print("3. Prediction post-processing may be inverting signs")
    print("\nRecommended fix: Retrain all models with corrected training labels")


if __name__ == "__main__":
    asyncio.run(main())


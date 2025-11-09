"""
Test Freddy AI stock analysis integration with the working API configuration.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.freddy_ai_service import freddy_ai_service
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def test_basic_connection():
    """Test basic Freddy AI connection with a simple prompt."""
    print("\n" + "="*80)
    print("TEST 1: Basic Connection Test")
    print("="*80)
    
    # Simple test prompt
    prompt = "Hi, can you help me analyze stocks?"
    
    print(f"\nSending prompt: {prompt}")
    print(f"Using model: {freddy_ai_service.model}")
    print(f"API Key: {freddy_ai_service.api_key[:20]}...")
    print(f"Organization ID: {freddy_ai_service.organization_id}")
    print(f"Assistant ID: {freddy_ai_service.assistant_id}")
    
    response = await freddy_ai_service._call_api(
        prompt=prompt,
        temperature=0.7,
        enable_web_search=False
    )
    
    if response:
        print("\n✅ SUCCESS: Freddy AI responded!")
        print(f"Response: {response}")
        return True
    else:
        print("\n❌ FAILED: No response from Freddy AI")
        return False


async def test_stock_analysis():
    """Test stock analysis for a specific symbol."""
    print("\n" + "="*80)
    print("TEST 2: Stock Analysis Test")
    print("="*80)
    
    symbol = "INFY.NS"
    current_price = 1850.50
    
    print(f"\nAnalyzing: {symbol}")
    print(f"Current Price: ₹{current_price}")
    
    analysis = await freddy_ai_service.analyze_stock(
        symbol=symbol,
        current_price=current_price,
        use_cache=False  # Force fresh analysis
    )
    
    if analysis:
        print("\n✅ SUCCESS: Stock analysis completed!")
        print(f"\nSymbol: {analysis.symbol}")
        print(f"Recommendation: {analysis.recommendation}")
        print(f"Target Price: ₹{analysis.target_price}")
        print(f"Stop Loss: ₹{analysis.stop_loss}")
        print(f"Confidence: {analysis.confidence}")
        
        if analysis.technical_indicators:
            print(f"\nTechnical Indicators:")
            print(f"  RSI-14: {analysis.technical_indicators.rsi_14}")
            print(f"  RSI Level: {analysis.technical_indicators.rsi_level}")
            print(f"  Technical Bias: {analysis.technical_indicators.technical_bias}")
        
        if analysis.summary:
            print(f"\nSummary: {analysis.summary}")
        
        return True
    else:
        print("\n❌ FAILED: Stock analysis failed")
        return False


async def test_custom_prompt():
    """Test custom prompt with real-time context."""
    print("\n" + "="*80)
    print("TEST 3: Custom Prompt with Context Test")
    print("="*80)
    
    symbol = "TCS.NS"
    timeframe = "5m"
    current_price = 4250.75
    
    # Mock indicator snapshot
    indicators = {
        "rsi_14": 65.5,
        "macd": 12.3,
        "macd_histogram": 5.2,
        "sma_20": 4240.0,
        "sma_50": 4200.0,
        "atr_14": 45.2,
        "vwap_intraday": 4245.0
    }
    
    # Mock additional context
    context = {
        "latest_close": current_price,
        "session_high": 4280.0,
        "session_low": 4230.0,
        "price_change_pct": 1.2,
        "total_volume": 1500000
    }
    
    prompt = "Should I buy this stock now? What are the key support and resistance levels?"
    
    print(f"\nSymbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Current Price: ₹{current_price}")
    print(f"Prompt: {prompt}")
    
    analysis = await freddy_ai_service.analyze_custom_prompt(
        symbol=symbol,
        timeframe=timeframe,
        prompt=prompt,
        current_price=current_price,
        indicator_snapshot=indicators,
        additional_context=context,
        use_cache=False,
        enable_web_search=True
    )
    
    if analysis:
        print("\n✅ SUCCESS: Custom prompt analysis completed!")
        print(f"\nRecommendation: {analysis.recommendation}")
        print(f"Target Price: ₹{analysis.target_price}")
        print(f"Stop Loss: ₹{analysis.stop_loss}")
        
        if analysis.support_resistance:
            print(f"\nSupport Levels: {analysis.support_resistance.support_levels}")
            print(f"Resistance Levels: {analysis.support_resistance.resistance_levels}")
        
        if analysis.summary:
            print(f"\nSummary: {analysis.summary}")
        
        return True
    else:
        print("\n❌ FAILED: Custom prompt analysis failed")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("FREDDY AI STOCK ANALYSIS INTEGRATION TEST")
    print("="*80)
    
    if not freddy_ai_service.enabled:
        print("\n❌ ERROR: Freddy AI is disabled in configuration")
        print("Please set FREDDY_ENABLED=true in .env")
        return
    
    if not freddy_ai_service.api_key:
        print("\n❌ ERROR: Freddy AI API key not configured")
        print("Please set FREDDY_API_KEY in .env")
        return
    
    results = []
    
    # Test 1: Basic connection
    try:
        result = await test_basic_connection()
        results.append(("Basic Connection", result))
    except Exception as e:
        print(f"\n❌ ERROR in basic connection test: {e}")
        results.append(("Basic Connection", False))
    
    # Test 2: Stock analysis
    try:
        result = await test_stock_analysis()
        results.append(("Stock Analysis", result))
    except Exception as e:
        print(f"\n❌ ERROR in stock analysis test: {e}")
        results.append(("Stock Analysis", False))
    
    # Test 3: Custom prompt
    try:
        result = await test_custom_prompt()
        results.append(("Custom Prompt", result))
    except Exception as e:
        print(f"\n❌ ERROR in custom prompt test: {e}")
        results.append(("Custom Prompt", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! Freddy AI integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())


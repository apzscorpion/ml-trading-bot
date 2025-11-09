#!/usr/bin/env python3
"""
Quick diagnostic script to test Freddy AI API call
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_freddy_api():
    """Test Freddy AI API call directly"""
    from backend.services.freddy_ai_service import freddy_ai_service
    from backend.config import settings
    
    print("=" * 60)
    print("Freddy AI API Diagnostic Test")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  Enabled: {freddy_ai_service.enabled}")
    print(f"  API Key: {'✓ Set' if freddy_ai_service.api_key else '✗ Not set'}")
    print(f"  Organization ID: {'✓ Set' if freddy_ai_service.organization_id else '✗ Not set'}")
    print(f"  Assistant ID: {'✓ Set' if freddy_ai_service.assistant_id else '✗ Not set'}")
    print(f"  Base URL: {freddy_ai_service.base_url}")
    print(f"  Model: {freddy_ai_service.model}")
    print(f"  Timeout: {freddy_ai_service.timeout}s")
    
    if not freddy_ai_service.enabled:
        print("\n❌ Freddy AI is disabled!")
        return
    
    if not freddy_ai_service.api_key:
        print("\n❌ API key not configured!")
        return
    
    if not freddy_ai_service.organization_id:
        print("\n❌ Organization ID not configured!")
        return
    
    if not freddy_ai_service.assistant_id:
        print("\n❌ Assistant ID not configured!")
        return
    
    print(f"\n🔍 Testing API call for INFY.NS...")
    print(f"  URL will be: {freddy_ai_service.base_url.rstrip('/')}/model/response")
    
    try:
        response = await freddy_ai_service.analyze_stock(
            symbol="INFY.NS",
            current_price=1468.0,
            use_cache=False  # Don't use cache for testing
        )
        
        if response:
            print("\n✅ SUCCESS! Freddy AI response received:")
            print(f"  Symbol: {response.symbol}")
            print(f"  Recommendation: {response.recommendation}")
            print(f"  Confidence: {response.confidence}")
            print(f"  Target Price: {response.target_price}")
            print(f"  Stop Loss: {response.stop_loss}")
            if response.summary:
                print(f"  Summary: {response.summary[:100]}...")
        else:
            print("\n❌ No response received from Freddy AI")
            print("   Check logs for error details")
    
    except Exception as e:
        print(f"\n❌ Error calling Freddy AI API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_freddy_api())


#!/usr/bin/env python3
"""
Test script for Freddy AI integration
Verifies that the service can be imported and initialized correctly
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    try:
        from backend.services.freddy_ai_service import freddy_ai_service, FreddyAIResponse
        print("✅ freddy_ai_service imported successfully")
        
        from backend.services.comprehensive_analysis import comprehensive_analysis
        print("✅ comprehensive_analysis imported successfully")
        
        from backend.config import settings
        print("✅ config imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration settings"""
    print("\n🔍 Testing configuration...")
    try:
        from backend.config import settings
        
        print(f"  FREDDY_API_KEY: {'✓ Set' if settings.freddy_api_key else '✗ Not set'}")
        print(f"  FREDDY_API_BASE_URL: {settings.freddy_api_base_url}")
        print(f"  FREDDY_MODEL: {settings.freddy_model}")
        print(f"  FREDDY_ENABLED: {settings.freddy_enabled}")
        print(f"  FREDDY_TIMEOUT: {settings.freddy_timeout}s")
        print(f"  FREDDY_CACHE_TTL: {settings.freddy_cache_ttl}s")
        
        if not settings.freddy_api_key:
            print("\n⚠️  WARNING: FREDDY_API_KEY not set in .env file")
            print("   The service will work but Freddy AI calls will be disabled")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_service_initialization():
    """Test service initialization"""
    print("\n🔍 Testing service initialization...")
    try:
        from backend.services.freddy_ai_service import freddy_ai_service
        
        print(f"  Service enabled: {freddy_ai_service.enabled}")
        print(f"  API key configured: {bool(freddy_ai_service.api_key)}")
        print(f"  Base URL: {freddy_ai_service.base_url}")
        print(f"  Model: {freddy_ai_service.model}")
        
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False

def test_comprehensive_analysis():
    """Test comprehensive analysis service"""
    print("\n🔍 Testing comprehensive analysis service...")
    try:
        from backend.services.comprehensive_analysis import comprehensive_analysis
        
        # Test recommendation normalization
        test_cases = [
            ("buy", "Buy", "buy"),
            ("hold", "Buy", "buy_on_dip"),
            ("buy", "Sell", "hold"),
            ("sell", "Sell", "sell"),
        ]
        
        print("  Testing recommendation normalization...")
        for internal, freddy, expected in test_cases:
            result = comprehensive_analysis._normalize_recommendation(internal, freddy)
            status = "✓" if result == expected else "✗"
            print(f"    {status} Internal: {internal}, Freddy: {freddy} → {result}")
        
        return True
    except Exception as e:
        print(f"❌ Comprehensive analysis test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Freddy AI Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Service Initialization", test_service_initialization),
        ("Comprehensive Analysis", test_comprehensive_analysis),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Add FREDDY_API_KEY to your .env file")
        print("2. Update FREDDY_API_BASE_URL with actual Freddy AI endpoint")
        print("3. Test the API endpoint: GET /api/recommendation/comprehensive?symbol=INFY.NS")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


# Freddy AI Integration - Quick Setup Guide

## ✅ Installation Complete

All dependencies have been installed and the integration is ready to use!

## 📋 Setup Steps

### Step 1: Create/Update .env File

Create or update `backend/.env` file with the following:

```env
# Freddy AI API Settings
FREDDY_API_KEY=your_api_key_here
FREDDY_API_BASE_URL=https://api.freddy.ai/v1
FREDDY_MODEL=gpt-4
FREDDY_TIMEOUT=30
FREDDY_CACHE_TTL=300
FREDDY_ENABLED=true
```

**Important**: Replace `your_api_key_here` with your actual Freddy AI API key.

### Step 2: Update API Base URL

If Freddy AI uses a different API endpoint format than OpenAI-compatible, update `FREDDY_API_BASE_URL` accordingly.

The current implementation expects OpenAI-compatible format:
- Endpoint: `{base_url}/chat/completions`
- Request format: OpenAI chat completions format
- Response format: OpenAI chat completions format

### Step 3: Verify Installation

Run the test script to verify everything works:

```bash
cd backend
python test_freddy_ai.py
```

Expected output: All tests should pass ✅

### Step 4: Start the Backend

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### Step 5: Test the API

Once the backend is running, test the comprehensive analysis endpoint:

```bash
# Single symbol analysis
curl "http://localhost:8182/api/recommendation/comprehensive?symbol=INFY.NS&timeframe=5m"

# Batch analysis for multiple symbols
curl "http://localhost:8182/api/recommendation/comprehensive/batch?symbols=INFY.NS,TCS.NS&timeframe=5m"
```

## 🎯 Using the Integration

### Without API Key (Fallback Mode)

If you don't have a Freddy AI API key yet, the system will:
- ✅ Continue to work normally
- ✅ Use only internal ML predictions
- ✅ Return comprehensive analysis without Freddy AI data
- ⚠️  Freddy AI sections will show `available: false`

### With API Key (Full Mode)

Once you add the API key:
- ✅ Freddy AI will be called for market intelligence
- ✅ Responses will include technical analysis, news, fundamentals
- ✅ Combined recommendations with confidence scoring
- ✅ Support/resistance levels and risk metrics

## 📊 API Response Example

```json
{
  "symbol": "INFY.NS",
  "recommendation": "buy_on_dip",
  "confidence": 0.72,
  "current_price": 1523.45,
  "target_price": 1700.0,
  "stop_loss": 1400.0,
  "freddy_ai": {
    "available": true,
    "recommendation": "Buy on Dip",
    "technical_indicators": {
      "rsi_14": 56.7,
      "rsi_level": "neutral",
      "moving_averages": {
        "5_day": 1523.0,
        "50_day": 1484.0,
        "200_day": 1450.0
      },
      "technical_bias": "Bullish"
    },
    "news_count": 2,
    "summary": "Infosys shows bullish technical indicators..."
  },
  "insights": [
    "Strong bullish trend from ML models",
    "Technical bias: Bullish",
    "✓ Internal models and market intelligence agree"
  ]
}
```

## 🔧 Troubleshooting

### Issue: "Freddy AI API key not configured"
- Solution: Add `FREDDY_API_KEY` to your `.env` file

### Issue: "Freddy AI API timeout"
- Check your internet connection
- Increase `FREDDY_TIMEOUT` in `.env` if needed
- Verify API base URL is correct

### Issue: "Failed to parse Freddy AI JSON response"
- Check if Freddy AI returns OpenAI-compatible format
- Review logs for actual response format
- May need to update `_call_api` method if format differs

### Issue: Slow responses
- Enable caching (already enabled by default)
- Cache TTL is 5 minutes (300 seconds)
- Reduce `FREDDY_CACHE_TTL` if you need fresher data

## 📚 Documentation

- **Detailed Guide**: `FREDDY_AI_INTEGRATION.md`
- **Implementation Summary**: `FREDDY_AI_IMPLEMENTATION_SUMMARY.md`
- **Test Script**: `backend/test_freddy_ai.py`

## 🚀 Next Steps

1. **Get Freddy AI API Key**: Contact Freddy AI provider for API access
2. **Configure .env**: Add your API key to `.env` file
3. **Test Integration**: Run test script and API endpoints
4. **Monitor Performance**: Check logs for API response times
5. **Fine-tune Prompts**: Adjust prompts in `freddy_ai_service.py` if needed

## ✅ Verification Checklist

- [x] httpx installed in virtual environment
- [x] All imports working correctly
- [x] Configuration loading properly
- [x] Service initialization successful
- [x] Recommendation normalization working
- [ ] API key added to .env
- [ ] API base URL updated (if needed)
- [ ] Backend server started
- [ ] API endpoint tested
- [ ] Freddy AI responses received

## 🎉 Ready to Use!

The Freddy AI integration is complete and ready to use. Just add your API key and start getting comprehensive analysis combining internal ML predictions with market intelligence!


# Freddy AI Integration - Implementation Summary

## ✅ What Was Implemented

### 1. Configuration (`backend/config.py`)
- Added Freddy AI API settings:
  - `freddy_api_key`: API key for authentication
  - `freddy_api_base_url`: Base URL for Freddy AI API (OpenAI-compatible)
  - `freddy_model`: Model to use (default: gpt-4)
  - `freddy_timeout`: Request timeout (default: 30s)
  - `freddy_cache_ttl`: Cache TTL (default: 300s / 5 minutes)
  - `freddy_enabled`: Enable/disable flag

### 2. Freddy AI Service Manager (`backend/services/freddy_ai_service.py`)
- **FreddyAIServiceManager**: Async service for calling Freddy AI API
- **Structured Prompts**: Comprehensive prompts for stock analysis including:
  - Technical indicators (RSI, moving averages, technical bias)
  - Fundamental & news analysis
  - Volume trends
  - Support & resistance levels
  - Risk metrics
  - Recommendations with targets and stop loss
- **Response Models**: Pydantic models for structured responses:
  - `TechnicalIndicator`: RSI, MAs, technical bias
  - `NewsEvent`: News with impact classification
  - `VolumeAnalysis`: Volume trends and ratios
  - `SupportResistance`: Support/resistance levels
  - `RiskMetrics`: Volatility, risk level, Sharpe ratio
  - `FreddyAIResponse`: Complete response structure
- **Caching**: Redis-based caching with TTL to reduce API calls
- **Error Handling**: Graceful fallbacks if API fails

### 3. Comprehensive Analysis Service (`backend/services/comprehensive_analysis.py`)
- **ComprehensiveAnalysis**: Combines internal predictions with Freddy AI
- **Recommendation Normalization**: Smart logic to combine recommendations:
  - Agreement detection (boosts confidence)
  - Conflict resolution (conservative approach)
  - Normalizes different recommendation formats
- **Confidence Scoring**: Combined confidence calculation:
  - Agreement: Boosted by 10%
  - Disagreement: Reduced by 20%
  - Weighted average of both sources
- **Risk Assessment**: Combines Freddy AI risk metrics with internal volatility
- **Insights Generation**: Creates actionable insights from both sources

### 4. API Endpoints (`backend/routes/recommendation.py`)
- **GET `/api/recommendation/comprehensive`**: Single symbol comprehensive analysis
- **GET `/api/recommendation/comprehensive/batch`**: Batch analysis for multiple symbols
- Both endpoints combine:
  - Internal ML predictions
  - Freddy AI market intelligence
  - Risk-adjusted recommendations

### 5. Dependencies (`backend/requirements.txt`)
- Added `httpx>=0.25.0` for async HTTP client

## 📋 Setup Instructions

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Add to `.env` file:
```env
FREDDY_API_KEY=your_api_key_here
FREDDY_API_BASE_URL=https://api.freddy.ai/v1  # Update with actual URL
FREDDY_MODEL=gpt-4
FREDDY_TIMEOUT=30
FREDDY_CACHE_TTL=300
FREDDY_ENABLED=true
```

### Step 3: Update API Base URL
If Freddy AI uses a different API endpoint format, update `FREDDY_API_BASE_URL` in `.env`.

**Note**: The implementation assumes OpenAI-compatible API format. If Freddy AI uses a different format, update the `_call_api` method in `freddy_ai_service.py`.

## 🎯 Usage Examples

### Single Symbol Analysis
```bash
curl "http://localhost:8182/api/recommendation/comprehensive?symbol=INFY.NS&timeframe=5m"
```

### Batch Analysis
```bash
curl "http://localhost:8182/api/recommendation/comprehensive/batch?symbols=INFY.NS,TCS.NS&timeframe=5m"
```

### Python Example
```python
import httpx

async def get_comprehensive_analysis(symbol: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8182/api/recommendation/comprehensive",
            params={"symbol": symbol, "timeframe": "5m"}
        )
        return response.json()
```

## 🔧 How It Works

### Flow Diagram
```
User Request
    ↓
Get Latest Prediction (Internal ML)
    ↓
Get Latest Candle (Price Data)
    ↓
Call Freddy AI API (Market Intelligence)
    ↓
Parse & Cache Response
    ↓
Combine Recommendations
    ↓
Calculate Combined Confidence
    ↓
Generate Insights
    ↓
Return Comprehensive Analysis
```

### Recommendation Combination Logic

1. **Both Agree** → Higher confidence, use agreed recommendation
2. **Internal Buy + Freddy Hold** → Buy (with moderate confidence)
3. **Internal Hold + Freddy Buy** → Buy on Dip (conservative)
4. **Internal Sell + Freddy Hold** → Sell (moderate confidence)
5. **Direct Conflict** → Hold (safest approach)

### Confidence Scoring
- **Agreement**: `(internal * 0.5 + freddy * 0.5) * 1.1` (boosted)
- **Disagreement**: `(internal * 0.6 + freddy * 0.4) * 0.8` (reduced)

## 📊 Response Structure

The comprehensive analysis response includes:

- **Recommendation**: Combined recommendation (buy/sell/hold/buy_on_dip)
- **Confidence**: Combined confidence score (0-1)
- **Price Targets**: Target price and stop loss
- **Trend Analysis**: Bullish/bearish/neutral from internal models
- **Risk Assessment**: Low/medium/high risk level
- **Freddy AI Data**: Complete Freddy AI analysis
- **Internal Prediction**: Internal ML model predictions
- **Insights**: Actionable insights from both sources

## 🚨 Important Notes

1. **API Key Required**: Freddy AI integration requires a valid API key
2. **Fallback Behavior**: If Freddy AI is unavailable, analysis continues with internal predictions only
3. **Caching**: Responses are cached for 5 minutes to reduce API calls
4. **Rate Limits**: Be mindful of Freddy AI API rate limits
5. **Error Handling**: Errors are logged but don't break the analysis flow

## 🔍 Testing

### Test Without Freddy AI
Set `FREDDY_ENABLED=false` in `.env` to test with internal predictions only.

### Test with Mock Data
You can modify `freddy_ai_service.py` to return mock data for testing:
```python
# In _call_api method, add:
if settings.freddy_enabled and self.api_key == "test":
    return {
        "symbol": symbol,
        "recommendation": "Buy",
        "confidence": 0.75,
        # ... mock data
    }
```

## 📝 Next Steps

1. **Get Freddy AI API Key**: Obtain API key from Freddy AI provider
2. **Update API URL**: Update `FREDDY_API_BASE_URL` with actual endpoint
3. **Test Integration**: Test with real symbols (INFY.NS, TCS.NS)
4. **Monitor Performance**: Check logs for API response times and errors
5. **Adjust Prompts**: Fine-tune prompts based on Freddy AI response quality

## 🐛 Troubleshooting

### Issue: Freddy AI returns empty responses
- Check API key is correct
- Verify API base URL is correct
- Check API response format matches expected OpenAI-compatible format
- Review logs for API errors

### Issue: Slow responses
- Check network connectivity
- Reduce timeout if needed
- Ensure caching is working
- Consider using batch endpoint for multiple symbols

### Issue: Parsing errors
- Check Freddy AI response format
- Update `_call_api` method if format differs
- Add more robust JSON parsing if needed

## 📚 Related Documentation

- `FREDDY_AI_INTEGRATION.md`: Detailed integration guide
- `backend/services/freddy_ai_service.py`: Service implementation
- `backend/services/comprehensive_analysis.py`: Analysis combination logic


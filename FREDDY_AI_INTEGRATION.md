# Freddy AI Integration Guide

## Overview

The Freddy AI integration combines our internal ML predictions with external market intelligence from Freddy AI. This provides a holistic view that combines:

1. **Internal ML Models**: RSI, MACD, MA, LSTM, Transformer, Ensemble predictions
2. **Freddy AI Intelligence**: Technical analysis, news, fundamentals, volume trends, support/resistance
3. **Combined Recommendations**: Risk-adjusted, confidence-weighted recommendations

## Configuration

Add the following to your `.env` file:

```env
# Freddy AI Settings
FREDDY_API_KEY=your_api_key_here
FREDDY_API_BASE_URL=https://api.freddy.ai/v1  # Update with actual URL
FREDDY_MODEL=gpt-4  # Model to use
FREDDY_TIMEOUT=30  # Request timeout in seconds
FREDDY_CACHE_TTL=300  # Cache TTL in seconds (5 minutes)
FREDDY_ENABLED=true  # Enable/disable Freddy AI
```

## API Endpoints

### 1. Comprehensive Analysis (Single Symbol)

**Endpoint**: `GET /api/recommendation/comprehensive`

**Parameters**:
- `symbol` (required): Stock symbol (e.g., `INFY.NS`, `TCS.NS`)
- `timeframe` (optional): Timeframe, default `5m`

**Example**:
```bash
curl "http://localhost:8182/api/recommendation/comprehensive?symbol=INFY.NS&timeframe=5m"
```

**Response**:
```json
{
  "symbol": "INFY.NS",
  "timeframe": "5m",
  "timestamp": "2025-11-05T10:00:00",
  "current_price": 1523.45,
  "recommendation": "buy_on_dip",
  "recommendation_details": {
    "internal": "buy",
    "freddy_ai": "Buy on Dip",
    "agreement": false
  },
  "confidence": 0.72,
  "confidence_breakdown": {
    "internal": 0.65,
    "freddy_ai": 0.75,
    "combined": 0.72
  },
  "target_price": 1700.0,
  "stop_loss": 1400.0,
  "price_change": 176.55,
  "price_change_pct": 11.59,
  "trend": "bullish",
  "volatility": 1.8,
  "risk_level": "medium",
  "internal_prediction": {
    "predicted_price": 1700.0,
    "trend": "bullish",
    "confidence": 0.65
  },
  "freddy_ai": {
    "available": true,
    "recommendation": "Buy on Dip",
    "target_price": 1700.0,
    "stop_loss": 1400.0,
    "confidence": 0.75,
    "technical_indicators": {
      "rsi_14": 56.7,
      "rsi_level": "neutral",
      "moving_averages": {
        "5_day": 1523.0,
        "50_day": 1484.0,
        "200_day": 1450.0
      },
      "price_vs_ma": "above",
      "technical_bias": "Bullish"
    },
    "news_count": 2,
    "summary": "Infosys shows bullish technical indicators with positive news..."
  },
  "insights": [
    "Strong bullish trend from ML models",
    "Technical bias: Bullish",
    "RSI: neutral",
    "2 positive news event(s)",
    "⚠ Internal models and market intelligence differ - exercise caution"
  ],
  "analysis_version": "v1.0",
  "data_sources": {
    "internal_ml": true,
    "freddy_ai": true
  }
}
```

### 2. Comprehensive Analysis (Batch)

**Endpoint**: `GET /api/recommendation/comprehensive/batch`

**Parameters**:
- `symbols` (required): Comma-separated stock symbols
- `timeframe` (optional): Timeframe, default `5m`

**Example**:
```bash
curl "http://localhost:8182/api/recommendation/comprehensive/batch?symbols=INFY.NS,TCS.NS&timeframe=5m"
```

## How It Works

### 1. Data Collection
- Fetches latest internal prediction from database
- Calls Freddy AI API with structured prompt
- Retrieves current price and historical candles

### 2. Analysis Combination
- **Recommendation Normalization**: Converts both recommendations to common format and combines them
- **Confidence Scoring**: Calculates combined confidence (boosted if they agree, reduced if they disagree)
- **Risk Assessment**: Uses Freddy AI risk metrics combined with internal volatility

### 3. Recommendation Logic

| Internal | Freddy AI | Combined Result |
|----------|-----------|-----------------|
| Buy | Buy | Buy (high confidence) |
| Buy | Hold | Buy |
| Hold | Buy | Buy on Dip |
| Hold | Sell | Hold (conservative) |
| Sell | Buy | Hold (conflict) |
| Sell | Sell | Sell (high confidence) |

### 4. Caching
- Responses are cached for 5 minutes (configurable)
- Reduces API calls and improves response time
- Cache keys: `freddy_ai:analysis:{symbol}` and `freddy_ai:volume_levels:{symbol}`

## Response Structure

### Technical Indicators
- RSI (14-day) and level (oversold/neutral/overbought)
- Moving averages (5-day, 50-day, 200-day)
- Price position relative to MAs
- Overall technical bias

### News Events
- Recent news affecting the stock
- Impact classification (positive/negative/neutral)
- Corporate actions (buybacks, dividends, splits)
- Regulatory developments

### Volume Analysis
- Volume trend (increasing/decreasing/stable)
- Average vs current volume
- Volume ratio

### Support & Resistance
- Key support levels
- Key resistance levels
- Nearest support/resistance from current price

### Risk Metrics
- Volatility assessment
- Risk level (low/medium/high)
- Max drawdown
- Sharpe ratio

## Error Handling

- If Freddy AI is unavailable, falls back to internal predictions only
- If API key is missing, Freddy AI data will be `null` but analysis continues
- Errors are logged but don't break the analysis flow

## Best Practices

1. **API Key Management**: Store API key in `.env` file, never commit to git
2. **Rate Limiting**: Be mindful of API rate limits; caching helps reduce calls
3. **Fallback**: Always design to work without Freddy AI if service is unavailable
4. **Monitoring**: Monitor API response times and error rates
5. **Testing**: Test with various symbols and timeframes to ensure stability

## Troubleshooting

### Freddy AI not returning data
- Check API key is set correctly
- Verify `FREDDY_ENABLED=true` in `.env`
- Check API base URL is correct
- Review logs for API errors

### Low confidence scores
- Normal if internal and Freddy AI disagree
- Check if market conditions are uncertain
- Consider using longer timeframes for more stable signals

### Slow responses
- Check network connectivity
- Reduce `FREDDY_TIMEOUT` if needed
- Ensure caching is enabled
- Consider using batch endpoint for multiple symbols

## Future Enhancements

- [ ] Add webhook support for real-time Freddy AI updates
- [ ] Implement A/B testing between with/without Freddy AI
- [ ] Add historical accuracy tracking for Freddy AI recommendations
- [ ] Support for multiple Freddy AI models
- [ ] Custom prompt templates per symbol/sector


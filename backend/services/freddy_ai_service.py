"""
Freddy AI Service Manager
Handles API calls to Freddy AI for stock analysis and market intelligence.
Provides structured prompts and parses responses similar to OpenAI API.
"""
import httpx
import json
import math
import re
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from backend.config import settings
from backend.utils.logger import get_logger
from backend.utils.redis_cache import redis_cache

logger = get_logger(__name__)


class TechnicalIndicator(BaseModel):
    """Technical indicator data from Freddy AI"""
    rsi_14: Optional[float] = Field(None, description="14-day RSI value")
    rsi_level: Optional[str] = Field(None, description="RSI level: oversold, neutral, overbought")
    moving_averages: Optional[Dict[str, float]] = Field(None, description="Moving averages (5-day, 50-day, 200-day)")
    price_vs_ma: Optional[str] = Field(None, description="Price position relative to MAs: above, below, mixed")
    technical_bias: Optional[str] = Field(None, description="Technical bias: Bullish, Bearish, Neutral, Strong Sell")


class NewsEvent(BaseModel):
    """News event or fundamental data"""
    title: str
    impact: str = Field(description="Impact: positive, negative, neutral")
    description: Optional[str] = None
    date: Optional[str] = None


class VolumeAnalysis(BaseModel):
    """Volume trend analysis"""
    trend: Optional[str] = Field(None, description="Volume trend: increasing, decreasing, stable")
    avg_volume: Optional[float] = None
    current_volume: Optional[float] = None
    volume_ratio: Optional[float] = Field(None, description="Current volume / Average volume")


class SupportResistance(BaseModel):
    """Support and resistance levels"""
    support_levels: List[float] = Field(default_factory=list)
    resistance_levels: List[float] = Field(default_factory=list)
    current_price: Optional[float] = None
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None


class RiskMetrics(BaseModel):
    """Risk metrics analysis"""
    volatility: Optional[float] = None
    risk_level: Optional[str] = Field(None, description="Risk level: low, medium, high")
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None


class FreddyAIResponse(BaseModel):
    """Structured response from Freddy AI"""
    symbol: str
    current_price: Optional[float] = None
    recommendation: Optional[str] = Field(None, description="Recommendation: Buy, Sell, Hold, Buy on Dip")
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    technical_indicators: Optional[TechnicalIndicator] = None
    news_events: List[NewsEvent] = Field(default_factory=list)
    volume_analysis: Optional[VolumeAnalysis] = None
    support_resistance: Optional[SupportResistance] = None
    risk_metrics: Optional[RiskMetrics] = None
    summary: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score 0-1")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FreddyAIServiceManager:
    """
    Service manager for Freddy AI API calls.
    Handles prompt construction, API communication, response parsing, and caching.
    """
    
    def __init__(self):
        self.api_key = settings.freddy_api_key
        self.organization_id = settings.freddy_organization_id
        self.assistant_id = settings.freddy_assistant_id
        self.base_url = settings.freddy_api_base_url
        self.model = settings.freddy_model
        self.temperature = settings.freddy_temperature
        self.timeout = settings.freddy_timeout
        self.cache_ttl = settings.freddy_cache_ttl
        self.enabled = settings.freddy_enabled
        
        if not self.enabled:
            logger.warning("Freddy AI is disabled in configuration")
        
        if self.enabled:
            if not self.api_key:
                logger.warning("Freddy AI API key not configured")
            if not self.organization_id:
                logger.warning("Freddy AI organization_id not configured")
            if not self.assistant_id:
                logger.warning("Freddy AI assistant_id not configured")
    
    def _get_cache_key(self, symbol: str, analysis_type: str) -> str:
        """Generate cache key for Freddy AI responses"""
        return f"freddy_ai:{analysis_type}:{symbol}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get cached response from Redis"""
        if not settings.redis_enabled:
            return None
        
        try:
            cached = redis_cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None
    
    async def _set_cache(self, cache_key: str, data: Dict):
        """Cache response in Redis"""
        if not settings.redis_enabled:
            return
        
        try:
            redis_cache.set(cache_key, json.dumps(data), ttl=self.cache_ttl)
        except Exception as e:
            logger.debug(f"Cache write error: {e}")
    
    def _build_stock_analysis_prompt(self, symbol: str, current_price: Optional[float] = None) -> str:
        """
        Build a comprehensive prompt for stock analysis.
        
        Args:
            symbol: Stock symbol (e.g., INFY.NS, TCS.NS)
            current_price: Current stock price (optional)
        
        Returns:
            Formatted prompt string
        """
        # Add system instruction at the start
        system_instruction = "You are a professional financial analyst specializing in Indian stock market (NSE/BSE) analysis. Provide accurate, data-driven insights with specific numbers and actionable recommendations. **IMPORTANT: Always format your response as valid JSON only, no additional text or explanations outside the JSON structure.**"
        
        symbol_clean = symbol.replace('.NS', '').replace('.BO', '')
        
        prompt = f"""{system_instruction}

Analyze {symbol_clean} (NSE/BSE: {symbol}) comprehensively. Provide a structured analysis with the following:

1. **Technical Indicators:**
   - Current 14-day RSI value and level (oversold/neutral/overbought)
   - Moving averages: 5-day, 50-day, 200-day with actual values
   - Price position relative to MAs (above/below/mixed)
   - Overall technical bias (Bullish/Bearish/Neutral/Strong Sell)

2. **Fundamental & News:**
   - Recent news events affecting the stock
   - Major corporate actions (buybacks, dividends, splits)
   - Regulatory developments or disputes
   - Sector-specific headwinds or tailwinds

3. **Volume Analysis:**
   - Volume trend (increasing/decreasing/stable)
   - Average volume vs current volume
   - Volume ratio (current/avg)

4. **Support & Resistance:**
   - Key support levels
   - Key resistance levels
   - Nearest support and resistance from current price

5. **Risk Metrics:**
   - Volatility assessment
   - Risk level (low/medium/high)
   - Max drawdown if available
   - Sharpe ratio if available

6. **Recommendation:**
   - Clear recommendation: Buy / Sell / Hold / Buy on Dip
   - Target price range
   - Stop loss level
   - Confidence score (0-1)

7. **Summary:**
   - 2-3 sentence executive summary

Format your response as JSON with this structure:
{{
    "symbol": "{symbol}",
    "current_price": {current_price if current_price else "null"},
    "recommendation": "Buy/Sell/Hold/Buy on Dip",
    "target_price": <target_price>,
    "stop_loss": <stop_loss>,
    "technical_indicators": {{
        "rsi_14": <rsi_value>,
        "rsi_level": "oversold/neutral/overbought",
        "moving_averages": {{"5_day": <value>, "50_day": <value>, "200_day": <value>}},
        "price_vs_ma": "above/below/mixed",
        "technical_bias": "Bullish/Bearish/Neutral/Strong Sell"
    }},
    "news_events": [
        {{"title": "<title>", "impact": "positive/negative/neutral", "description": "<desc>"}}
    ],
    "volume_analysis": {{
        "trend": "increasing/decreasing/stable",
        "avg_volume": <value>,
        "current_volume": <value>,
        "volume_ratio": <ratio>
    }},
    "support_resistance": {{
        "support_levels": [<levels>],
        "resistance_levels": [<levels>],
        "current_price": <price>,
        "nearest_support": <support>,
        "nearest_resistance": <resistance>
    }},
    "risk_metrics": {{
        "volatility": <value>,
        "risk_level": "low/medium/high",
        "max_drawdown": <value>,
        "sharpe_ratio": <value>
    }},
    "summary": "<2-3 sentence summary>",
    "confidence": <0.0-1.0>
}}

Be specific with numbers. Use web search to get the latest data. Focus on actionable insights."""
        
        return prompt
    
    def _build_volume_analysis_prompt(self, symbol: str) -> str:
        """Build prompt specifically for volume trends and support/resistance"""
        symbol_clean = symbol.replace('.NS', '').replace('.BO', '')
        
        return f"""Analyze volume trends, support/resistance levels, and detailed risk metrics for {symbol_clean} ({symbol}).

Provide:
1. Volume trend over last 20 trading sessions (increasing/decreasing/stable)
2. Average volume vs current volume
3. Support levels (at least 3 key levels)
4. Resistance levels (at least 3 key levels)
5. Detailed risk metrics including volatility, Sharpe ratio, max drawdown

Format as JSON matching the volume_analysis, support_resistance, and risk_metrics structures from the main analysis prompt."""
    
    async def _call_api(
        self,
        prompt: str,
        temperature: float = 0.7,
        enable_web_search: bool = False,
        thread_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Call Freddy AI API (OpenAI-compatible format).
        
        Args:
            prompt: The prompt to send
            temperature: Temperature for response (0-1)
            enable_web_search: Enable web search tool
            thread_id: Optional thread ID for conversation continuity
        
        Returns:
            Parsed JSON response or None
        """
        if not self.enabled:
            logger.debug("Freddy AI is disabled in configuration")
            return None
        
        if not self.api_key:
            logger.warning("Freddy AI API key not configured - skipping API call")
            return None
        
        if not self.organization_id:
            logger.warning("Freddy AI organization_id not configured - skipping API call")
            return None
        
        if not self.assistant_id:
            logger.warning("Freddy AI assistant_id not configured - skipping API call")
            return None
        
        try:
            # Freddy AI uses /model/response endpoint
            base_url = self.base_url.rstrip('/')
            url = f"{base_url}/model/response"
            logger.debug(f"Calling Freddy AI API: {url}")
            
            headers = {
                'Content-Type': 'application/json',
                'Api-Key': self.api_key
            }
            
            # Generate a simple thread_id if not provided (6-digit random number to stay within Int32 range)
            if not thread_id:
                import random
                thread_id = str(random.randint(100000, 999999))  # 6-digit number
            
            request_body = {
                "organization_id": self.organization_id,
                "assistant_id": self.assistant_id,
                "thread_id": thread_id,
                "inputs": [
                    {
                        "role": "user",
                        "texts": [
                            {
                                "text": prompt
                            }
                        ],
                        "files": []
                    }
                ],
                "message_type_id": 1,
                "smart_document": False,
                "model": self.model,
                "tools": {
                    "web_search": {
                        "is_enabled": enable_web_search
                    },
                    "file_search": {
                        "is_enabled": False
                    }
                },
                "tool_choice": "web_search" if enable_web_search else ""
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=request_body)
                response.raise_for_status()
                
                result = response.json()
                
                # Parse Freddy API response format
                # Response can be streaming events array or a single response object
                events = []
                if isinstance(result, list):
                    # Streaming events format: [{"event": "...", "response": "...", ...}, ...]
                    events = result
                elif isinstance(result, dict):
                    if 'success' in result and result.get('success'):
                        events = result.get('data', [])
                    elif 'data' in result:
                        events = result['data']
                    else:
                        events = [result]
                else:
                    events = [result]
                
                # Extract content from events
                # Look for completed event or text deltas
                content = ""
                completed_response = None
                
                for event in events:
                    if isinstance(event, dict):
                        # Check for completed event with full response
                        if event.get('event') == 'response.completed':
                            completed_response = event.get('response', '')
                            break
                        # Check for text delta events
                        elif event.get('event') == 'response.output_text.delta':
                            content += str(event.get('response', ''))
                        # Check for direct text/content fields
                        elif 'text' in event:
                            content += str(event['text'])
                        elif 'content' in event:
                            content += str(event['content'])
                        elif 'response' in event and isinstance(event['response'], str):
                            content += str(event['response'])
                        elif 'message' in event and isinstance(event['message'], dict):
                            if 'text' in event['message']:
                                content += str(event['message']['text'])
                            elif 'content' in event['message']:
                                content += str(event['message']['content'])
                        elif 'role' in event and 'content' in event:
                            content += str(event['content'])
                
                # Use completed response if available, otherwise use accumulated content
                final_content = completed_response if completed_response else content
                
                if not final_content:
                    logger.error("No content found in Freddy AI response")
                    logger.debug(f"Response structure: {result}")
                    return None
                
                # Try to parse as JSON
                try:
                    # Try to extract JSON if wrapped in markdown code blocks
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', final_content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(1))
                    else:
                        # Try parsing the entire content as JSON
                        parsed = json.loads(final_content)
                    
                    # If response has a "data" or "result" wrapper, extract it
                    if isinstance(parsed, dict):
                        if "data" in parsed:
                            parsed = parsed["data"]
                        elif "result" in parsed:
                            parsed = parsed["result"]
                    
                    # Validate and clean NaN/Inf values
                    parsed = self._validate_and_clean_response(parsed)
                    
                    return parsed
                except json.JSONDecodeError:
                    # If response is not JSON, it might be plain text
                    # This can happen if the API returns a text response instead of JSON
                    logger.debug(f"Response is not JSON, treating as plain text: {final_content[:200]}")
                    # Return None - the caller should handle plain text responses differently
                    # or we could return a dict with the text content
                    return {
                        "error": "Non-JSON response",
                        "text": final_content,
                        "note": "Freddy AI returned plain text instead of JSON. Prompt may need to explicitly request JSON format."
                    }
        
        except httpx.TimeoutException:
            logger.error(f"Freddy AI API timeout after {self.timeout}s")
            return None
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500] if e.response.text else "No error message"
            logger.error(f"Freddy AI API error {e.response.status_code}: {error_text}")
            
            if e.response.status_code == 404:
                logger.error(f"Endpoint not found: {url}")
                logger.error("Please verify FREDDY_API_BASE_URL is correct")
            
            return None
        except Exception as e:
            logger.error(f"Freddy AI API call failed: {e}", exc_info=True)
            return None
    
    def _validate_and_clean_response(self, data: Any) -> Any:
        """
        Recursively validate and clean NaN/Inf values from API response.
        
        Args:
            data: Response data (dict, list, or primitive)
        
        Returns:
            Cleaned data with NaN/Inf replaced or removed
        """
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                cleaned_value = self._validate_and_clean_response(value)
                if cleaned_value is not None:
                    cleaned[key] = cleaned_value
            return cleaned
        elif isinstance(data, list):
            cleaned = []
            for item in data:
                cleaned_item = self._validate_and_clean_response(item)
                if cleaned_item is not None:
                    cleaned.append(cleaned_item)
            return cleaned
        elif isinstance(data, (int, float)):
            # Validate numeric values
            if math.isnan(data) or math.isinf(data):
                logger.warning(f"Found NaN/Inf value in response: {data}")
                return None  # Return None for invalid values
            return data
        else:
            return data
    
    async def analyze_stock(
        self, 
        symbol: str, 
        current_price: Optional[float] = None,
        use_cache: bool = True
    ) -> Optional[FreddyAIResponse]:
        """
        Get comprehensive stock analysis from Freddy AI.
        
        Args:
            symbol: Stock symbol (e.g., INFY.NS, TCS.NS)
            current_price: Current stock price (optional, helps with analysis)
            use_cache: Whether to use cached responses
        
        Returns:
            FreddyAIResponse object or None if failed
        """
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(symbol, "analysis")
        
        # Check cache first
        if use_cache:
            cached = await self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Using cached Freddy AI response for {symbol}")
                try:
                    return FreddyAIResponse(**cached)
                except Exception as e:
                    logger.warning(f"Failed to parse cached response: {e}")
        
        # Build prompt
        prompt = self._build_stock_analysis_prompt(symbol, current_price)
        
        # Call API
        logger.info(f"Calling Freddy AI for {symbol} analysis")
        response_data = await self._call_api(prompt)
        
        if not response_data:
            return None
        
        # Add symbol and timestamp if missing
        if "symbol" not in response_data:
            response_data["symbol"] = symbol
        if "timestamp" not in response_data:
            response_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Cache the response
        await self._set_cache(cache_key, response_data)
        
        # Parse and return
        try:
            # Validate numeric fields before creating response
            response_data = self._validate_freddy_response(response_data, current_price)
            
            return FreddyAIResponse(**response_data)
        except Exception as e:
            logger.error(f"Failed to parse Freddy AI response: {e}")
            logger.debug(f"Response data: {response_data}")
            return None
    
    async def analyze_custom_prompt(
        self,
        symbol: str,
        timeframe: str,
        prompt: str,
        current_price: Optional[float] = None,
        indicator_snapshot: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        enable_web_search: bool = True
    ) -> Optional[FreddyAIResponse]:
        """
        Call Freddy AI with a custom user prompt enriched with real-time context.

        Args:
            symbol: Stock symbol (e.g., INFY.NS)
            timeframe: Active timeframe (e.g., 5m, 15m)
            prompt: User supplied natural language prompt
            current_price: Latest traded price (if available)
            indicator_snapshot: Latest calculated indicator values
            additional_context: Extra context (e.g., candle stats, sentiment)
            use_cache: Whether to reuse cached responses
            enable_web_search: Allow Freddy AI to perform web search for headlines

        Returns:
            FreddyAIResponse instance or None on failure
        """
        if not self.enabled:
            return None

        prompt = prompt.strip() if prompt else "Provide actionable intraday analysis."  # Fallback safety

        context_payload: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "generated_at": datetime.utcnow().isoformat(),
            "indicators": indicator_snapshot or {}
        }

        if additional_context:
            # Merge shallowly while keeping indicator snapshot nested
            for key, value in additional_context.items():
                if key == "indicators":
                    context_payload["indicators"].update(value or {})
                else:
                    context_payload[key] = value

        # Use prompt+context signature for caching uniqueness
        signature_input = {
            "symbol": symbol,
            "timeframe": timeframe,
            "prompt": prompt,
            "context": context_payload
        }
        signature_hash = hashlib.sha256(
            json.dumps(signature_input, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        cache_key = f"freddy_ai:custom:{symbol}:{signature_hash}"

        if use_cache:
            cached = await self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Using cached Freddy AI custom response for {symbol} ({timeframe})")
                try:
                    return FreddyAIResponse(**cached)
                except Exception as exc:
                    logger.warning(f"Failed to hydrate cached custom response: {exc}")

        # Build base structured prompt and append user request
        base_prompt = self._build_stock_analysis_prompt(symbol, current_price)

        context_json = json.dumps(context_payload, indent=2, sort_keys=True, default=str)
        final_prompt = (
            f"{base_prompt}\n\n"
            f"Real-time context (JSON):\n{context_json}\n\n"
            "Instructions: Focus on real market data from the supplied context. "
            "If you reference news, prioritise events within the last 24 hours. "
            "All numeric outputs (targets, stop loss, indicators) must be explicit numbers. "
            "Return valid JSON only.\n\n"
            f"User request: {prompt}"
        )

        logger.info(
            "Calling Freddy AI custom prompt for %s (%s) with web_search=%s",
            symbol,
            timeframe,
            enable_web_search
        )

        response_data = await self._call_api(
            final_prompt,
            temperature=self.temperature,
            enable_web_search=enable_web_search
        )

        if not response_data:
            return None

        response_data.setdefault("symbol", symbol)
        if "timestamp" not in response_data:
            response_data["timestamp"] = datetime.utcnow().isoformat()
        if "current_price" not in response_data and current_price is not None:
            response_data["current_price"] = current_price

        await self._set_cache(cache_key, response_data)

        try:
            response_data = self._validate_freddy_response(response_data, current_price)
            return FreddyAIResponse(**response_data)
        except Exception as exc:
            logger.error(f"Failed to parse Freddy AI custom response: {exc}")
            logger.debug(f"Custom response payload: {response_data}")
            return None

    def _validate_freddy_response(self, data: Dict, fallback_price: Optional[float] = None) -> Dict:
        """
        Validate and clean Freddy AI response, ensuring numeric fields are valid.
        
        Args:
            data: Response data dictionary
            fallback_price: Fallback price if target_price is invalid
        
        Returns:
            Cleaned response data
        """
        # Validate target_price
        if "target_price" in data and data["target_price"] is not None:
            target_price = data["target_price"]
            if isinstance(target_price, (int, float)):
                if math.isnan(target_price) or math.isinf(target_price):
                    logger.warning(f"Invalid target_price (NaN/Inf): {target_price}, using fallback")
                    data["target_price"] = fallback_price if fallback_price else None
        
        # Validate stop_loss
        if "stop_loss" in data and data["stop_loss"] is not None:
            stop_loss = data["stop_loss"]
            if isinstance(stop_loss, (int, float)):
                if math.isnan(stop_loss) or math.isinf(stop_loss):
                    logger.warning(f"Invalid stop_loss (NaN/Inf): {stop_loss}")
                    data["stop_loss"] = None
        
        # Validate confidence
        if "confidence" in data and data["confidence"] is not None:
            confidence = data["confidence"]
            if isinstance(confidence, (int, float)):
                if math.isnan(confidence) or math.isinf(confidence):
                    logger.warning(f"Invalid confidence (NaN/Inf): {confidence}, using 0.5")
                    data["confidence"] = 0.5
                # Clamp confidence to 0-1 range
                data["confidence"] = max(0.0, min(1.0, float(confidence)))
        
        # Validate current_price
        if "current_price" in data and data["current_price"] is not None:
            current_price = data["current_price"]
            if isinstance(current_price, (int, float)):
                if math.isnan(current_price) or math.isinf(current_price):
                    logger.warning(f"Invalid current_price (NaN/Inf): {current_price}")
                    data["current_price"] = fallback_price if fallback_price else None
        
        # Validate technical indicators
        if "technical_indicators" in data and isinstance(data["technical_indicators"], dict):
            ti = data["technical_indicators"]
            for key in ["rsi_14"]:
                if key in ti and ti[key] is not None:
                    value = ti[key]
                    if isinstance(value, (int, float)):
                        if math.isnan(value) or math.isinf(value):
                            logger.debug(f"Invalid {key} (NaN/Inf): {value}")
                            ti[key] = None
            
            # Validate moving_averages
            if "moving_averages" in ti and isinstance(ti["moving_averages"], dict):
                ma = ti["moving_averages"]
                for key, value in list(ma.items()):
                    if isinstance(value, (int, float)):
                        if math.isnan(value) or math.isinf(value):
                            logger.debug(f"Invalid moving_averages.{key} (NaN/Inf): {value}")
                            ma.pop(key, None)
        
        # Validate support/resistance levels
        for key in ["support_levels", "resistance_levels"]:
            if key in data and isinstance(data[key], list):
                cleaned_levels = []
                for level in data[key]:
                    if isinstance(level, (int, float)):
                        if not (math.isnan(level) or math.isinf(level)):
                            cleaned_levels.append(float(level))
                    elif isinstance(level, str):
                        try:
                            level_float = float(level)
                            if not (math.isnan(level_float) or math.isinf(level_float)):
                                cleaned_levels.append(level_float)
                        except ValueError:
                            pass
                data[key] = cleaned_levels
        
        return data
    
    async def get_volume_and_levels(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Get detailed volume trends and support/resistance levels.
        
        Args:
            symbol: Stock symbol
            use_cache: Whether to use cached responses
        
        Returns:
            Dictionary with volume_analysis, support_resistance, risk_metrics
        """
        if not self.enabled:
            return None
        
        cache_key = self._get_cache_key(symbol, "volume_levels")
        
        # Check cache
        if use_cache:
            cached = await self._get_from_cache(cache_key)
            if cached:
                return cached
        
        # Build prompt
        prompt = self._build_volume_analysis_prompt(symbol)
        
        # Call API
        response_data = await self._call_api(prompt, temperature=0.5)
        
        if not response_data:
            return None
        
        # Cache and return
        await self._set_cache(cache_key, response_data)
        return response_data


# Singleton instance
freddy_ai_service = FreddyAIServiceManager()


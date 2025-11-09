# Freddy AI Integration Status

## ✅ Working Configuration

### API Credentials
```bash
FREDDY_API_KEY=sk-frdy-b8215320-3c72-45d2-aafc-ca9f75e86709
FREDDY_ORGANIZATION_ID=ORG_2310c95ccfb44aa49a5d3f43ea1ab835
FREDDY_ASSISTANT_ID=ASS_b22fa944a85d436cb04d06c3c0ab6839
FREDDY_API_BASE_URL=https://freddy-api.aitronos.ch/v1/
FREDDY_MODEL=gpt-4o
FREDDY_ENABLED=True
```

### ✅ Working cURL Command

Basic query:
```bash
curl -X POST "https://freddy-api.aitronos.ch/v1/model/response" \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk-frdy-b8215320-3c72-45d2-aafc-ca9f75e86709" \
  -d '{
    "organization_id": "ORG_2310c95ccfb44aa49a5d3f43ea1ab835",
    "assistant_id": "ASS_b22fa944a85d436cb04d06c3c0ab6839",
    "thread_id": "356082",
    "inputs": [
        {
            "role": "user",
            "texts": [{"text": "Hi"}],
            "files": []
        }
    ],
    "message_type_id": 1,
    "smart_document": false,
    "model": "gpt-4o",
    "tools": {
        "web_search": {"is_enabled": false},
        "file_search": {"is_enabled": false}
    },
    "tool_choice": ""
}'
```

With web search enabled (for stock news):
```bash
curl -X POST "https://freddy-api.aitronos.ch/v1/model/response" \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk-frdy-b8215320-3c72-45d2-aafc-ca9f75e86709" \
  -d '{
    "organization_id": "ORG_2310c95ccfb44aa49a5d3f43ea1ab835",
    "assistant_id": "ASS_b22fa944a85d436cb04d06c3c0ab6839",
    "thread_id": "356082",
    "inputs": [
        {
            "role": "user",
            "texts": [{"text": "What is the latest news about Infosys stock?"}],
            "files": []
        }
    ],
    "message_type_id": 1,
    "smart_document": false,
    "model": "gpt-4o",
    "tools": {
        "web_search": {"is_enabled": true},
        "file_search": {"is_enabled": false}
    },
    "tool_choice": "web_search"
}'
```

## Response Format

The API returns **streaming events** in JSON array format:

```json
[
  {"event": "response.created", "status": "in_progress", "isDocument": false},
  {"event": "response.in_progress", "status": "in_progress", "isDocument": false},
  {"event": "response.output_text.delta", "response": "Hi", "type": "text", "isDocument": false},
  {"event": "response.output_text.delta", "response": " there", "type": "text", "isDocument": false},
  ...
  {
    "event": "response.completed",
    "status": "completed",
    "response": "Hi there! How can I help you today?",
    "type": "text",
    "time": "1650 ms",
    "threadId": 356082,
    "isDocument": false,
    "userMessageId": 385056,
    "responseMessageId": 385057,
    "annotations": []
  }
]
```

## Key Findings

1. **Model**: Must use `gpt-4o` (not `gpt-4`)
2. **Thread ID**: Must be a valid integer (6-digit number works well, e.g., "356082")
3. **Web Search**: 
   - Set `tools.web_search.is_enabled: true`
   - Set `tool_choice: "web_search"` to force web search
4. **Streaming**: API returns streaming Server-Sent Events format
5. **Response Parsing**: Need to handle streaming delta events and extract final `response.completed` event

## Implementation Status

### ✅ Completed
- Environment configuration updated
- API credentials validated
- cURL commands tested and working
- Web search functionality verified
- Service code updated with correct payload structure

### ⚠️  Known Issues
- Python `httpx` client has issues with the streaming response format
- Need to implement proper SSE (Server-Sent Events) handling
- Current implementation tries to read entire response at once, causing `ReadError`

### 🔄 Next Steps
1. Implement proper streaming response handler
2. Parse SSE format correctly
3. Extract final response from `response.completed` event
4. Add retry logic for network errors
5. Implement proper timeout handling for long-running web searches

## Usage Example (Python - To Be Fixed)

```python
from backend.services.freddy_ai_service import freddy_ai_service

# Analyze stock with web search
analysis = await freddy_ai_service.analyze_custom_prompt(
    symbol="INFY.NS",
    timeframe="5m",
    prompt="What is the latest news about Infosys? Should I buy now?",
    current_price=1850.50,
    enable_web_search=True
)
```

## Files Modified
- `/Users/pits/Projects/new-bot-trading/.env` - Updated API credentials and model
- `/Users/pits/Projects/new-bot-trading/backend/config.py` - Changed default model to gpt-4o
- `/Users/pits/Projects/new-bot-trading/backend/services/freddy_ai_service.py` - Updated payload structure, added thread_id generation, tool_choice logic
- `/Users/pits/Projects/new-bot-trading/backend/test_freddy_stock_analysis.py` - Created integration test script

## API Documentation
- Endpoint: `https://freddy-api.aitronos.ch/v1/model/response`
- Method: POST
- Headers: `Content-Type: application/json`, `Api-Key: <your-key>`
- Response: Streaming JSON array with delta events

## Testing
Run curl test:
```bash
curl -X POST "https://freddy-api.aitronos.ch/v1/model/response" \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk-frdy-b8215320-3c72-45d2-aafc-ca9f75e86709" \
  -d '{"organization_id":"ORG_2310c95ccfb44aa49a5d3f43ea1ab835","assistant_id":"ASS_b22fa944a85d436cb04d06c3c0ab6839","thread_id":"356082","inputs":[{"role":"user","texts":[{"text":"Hi"}],"files":[]}],"message_type_id":1,"smart_document":false,"model":"gpt-4o","tools":{"web_search":{"is_enabled":false},"file_search":{"is_enabled":false}},"tool_choice":""}'
```

Expected: 200 OK with streaming JSON response containing "Hi there! How can I help you today?"


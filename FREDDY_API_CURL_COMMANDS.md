# 🔧 Freddy API cURL Commands

## Basic Test Command

```bash
curl -X POST "https://freddy-api.aitronos.ch/v1/model/response" \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk-frdy-5017ffa6-0f1a-445b-8ab2-04df27b75f54" \
  -d '{
    "organization_id": "ORG_0b1348c014f14dbbb89a64a454a0bd3a",
    "assistant_id": "ASS_2af1c42b90e4445b8571005394f8a0fe",
    "inputs": [
      {
        "role": "user",
        "texts": [
          {
            "text": "Hello, analyze INFY stock"
          }
        ]
      }
    ],
    "model": "gpt-4",
    "temperature": 0.7,
    "stream": false
  }'
```

## Pretty Print JSON Response

```bash
curl -X POST "https://freddy-api.aitronos.ch/v1/model/response" \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk-frdy-5017ffa6-0f1a-445b-8ab2-04df27b75f54" \
  -d '{
    "organization_id": "ORG_0b1348c014f14dbbb89a64a454a0bd3a",
    "assistant_id": "ASS_2af1c42b90e4445b8571005394f8a0fe",
    "inputs": [{"role": "user", "texts": [{"text": "Hello"}]}],
    "model": "gpt-4",
    "temperature": 0.7,
    "stream": false
  }' | python3 -m json.tool
```

## One-Liner (Compact)

```bash
curl -X POST "https://freddy-api.aitronos.ch/v1/model/response" -H "Content-Type: application/json" -H "Api-Key: sk-frdy-5017ffa6-0f1a-445b-8ab2-04df27b75f54" -d '{"organization_id":"ORG_0b1348c014f14dbbb89a64a454a0bd3a","assistant_id":"ASS_2af1c42b90e4445b8571005394f8a0fe","inputs":[{"role":"user","texts":[{"text":"Hello"}]}],"model":"gpt-4","temperature":0.7,"stream":false}'
```

## With Verbose Output (Debug)

```bash
curl -v -X POST "https://freddy-api.aitronos.ch/v1/model/response" \
  -H "Content-Type: application/json" \
  -H "Api-Key: sk-frdy-5017ffa6-0f1a-445b-8ab2-04df27b75f54" \
  -d '{
    "organization_id": "ORG_0b1348c014f14dbbb89a64a454a0bd3a",
    "assistant_id": "ASS_2af1c42b90e4445b8571005394f8a0fe",
    "inputs": [{"role": "user", "texts": [{"text": "Hello"}]}],
    "model": "gpt-4",
    "temperature": 0.7,
    "stream": false
  }'
```

## Current Configuration

```bash
# From .env file:
FREDDY_API_KEY=sk-frdy-5017ffa6-0f1a-445b-8ab2-04df27b75f54
FREDDY_ORGANIZATION_ID=ORG_0b1348c014f14dbbb89a64a454a0bd3a
FREDDY_ASSISTANT_ID=ASS_2af1c42b90e4445b8571005394f8a0fe
FREDDY_API_BASE_URL=https://freddy-api.aitronos.ch/v1/
FREDDY_MODEL=gpt-4
FREDDY_TEMPERATURE=0.7
```

## Expected Response Format

If successful, you should get a response like:
```json
{
  "success": true,
  "data": [
    {
      "text": "...",
      "content": "..."
    }
  ]
}
```

Or:
```json
{
  "data": [
    {
      "text": "...",
      "content": "..."
    }
  ]
}
```

## Current Error (401 Unauthorized)

```json
{
  "title": "Unauthorized",
  "message": "Invalid headerApiKey: sk-frdy-5017ffa6-0f1a-445b-8ab2-04df27b75f54."
}
```

This indicates the API key is invalid or expired. Update the API key in the curl command above to test with a valid key.


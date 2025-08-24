# API Changes and Migration Guide

## Overview

This document outlines the changes made to support multiple TTS services while maintaining full backward compatibility.

## Backward Compatibility

✅ **All existing code continues to work unchanged**
- Default behavior uses Edge TTS (same as before)
- All existing endpoints remain functional
- Environment variables remain the same
- Request/response formats unchanged

## New Features

### 1. Service Selection Parameter

Add `tts_service` to your requests to specify which TTS service to use:

```json
{
  "input": "Hello world",
  "voice": "alloy",
  "tts_service": "azuretts"
}
```

**Supported values:**
- `edgetts`, `edge` - Microsoft Edge TTS (default)
- `azuretts`, `azure` - Azure Cognitive Services TTS
- `googlecloudtts`, `google`, `gcp` - Google Cloud TTS
- `apipietts`, `apipie`, `openai` - OpenAI-compatible APIs
- `amazonpolly`, `polly`, `aws` - Amazon Polly

### 2. New Endpoints

#### Service Information
```bash
GET /v1/services
```
Returns available services and their configuration status.

#### Service-Specific Voices
```bash
GET /v1/services/{service_name}/voices
GET /v1/services/{service_name}/voices?language=en-US
```
Get voices for a specific service, optionally filtered by language.

### 3. Enhanced Existing Endpoints

All existing endpoints now support an optional `service` parameter:

```bash
# Get models for a specific service
GET /v1/models?service=azuretts

# Get voices for a specific service
GET /v1/voices?service=googlecloudtts&language=en-US
```

## Environment Variables

### Existing (unchanged)
```env
API_KEY=your_api_key_here
PORT=5050
DEFAULT_VOICE=en-US-AvaNeural
DEFAULT_RESPONSE_FORMAT=mp3
DEFAULT_SPEED=1.0
DEFAULT_LANGUAGE=en-US
REQUIRE_API_KEY=True
REMOVE_FILTER=False
EXPAND_API=True
DETAILED_ERROR_LOGGING=True
```

### New Configuration
```env
# Default service (optional, defaults to edgetts for compatibility)
DEFAULT_TTS_SERVICE=edgetts

# Azure Cognitive Services TTS
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=eastus

# Google Cloud Text-to-Speech
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT=your-project-id

# APIpie (OpenAI-compatible) TTS
APIPIE_API_KEY=your_apipie_api_key_here
APIPIE_BASE_URL=https://api.openai.com
APIPIE_TIMEOUT=30

# Amazon Polly
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
```

## Migration Examples

### Before (Edge TTS only)
```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello world",
    "voice": "alloy"
  }'
```

### After (same request, same behavior)
```bash
# Identical request - no changes needed
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello world",
    "voice": "alloy"
  }'

# Optional: explicitly specify Edge TTS
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello world",
    "voice": "alloy",
    "tts_service": "edgetts"
  }'

# New: use a different service
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello world",
    "voice": "alloy",
    "tts_service": "azuretts"
  }'
```

## Voice Mapping

OpenAI voice names are automatically mapped to equivalent voices in each service:

```javascript
// Example voice mappings
{
  "alloy": {
    "edgetts": "en-US-JennyNeural",
    "azuretts": "en-US-JennyNeural", 
    "googlecloudtts": "en-US-Journey-F",
    "apipietts": "alloy",  // No mapping needed
    "amazonpolly": "Joanna"
  }
}
```

You can also use service-specific voice names directly:
```json
{
  "input": "Hello world",
  "voice": "en-US-AriaNeural",  // Direct Azure voice name
  "tts_service": "azuretts"
}
```

## Error Handling and Fallbacks

### Service Availability
- If a requested service is not configured, falls back to default service
- If default service is unavailable, returns an error
- Service availability checked in real-time

### Example Fallback Flow
1. Request: `"tts_service": "azuretts"`
2. Azure TTS not configured → falls back to Edge TTS
3. Edge TTS available → request succeeds
4. Log warning about fallback

## Dependencies

### Core (existing)
```
flask
gevent
python-dotenv
edge-tts
emoji
```

### Optional (new)
```
aiohttp              # For APIpie TTS
azure-cognitiveservices-speech    # For Azure TTS
google-cloud-texttospeech         # For Google Cloud TTS
boto3                # For Amazon Polly
```

Install only what you need:
```bash
# For Azure TTS
pip install azure-cognitiveservices-speech

# For Google Cloud TTS  
pip install google-cloud-texttospeech

# For Amazon Polly
pip install boto3
```

## Testing

Use the included test script to verify functionality:
```bash
# Start the server
python app/server.py

# In another terminal, run tests
./test_multi_tts_api.sh
```

## Troubleshooting

### Service Not Available
Check the `/v1/services` endpoint to see service status:
```bash
curl -X GET http://localhost:5050/v1/services \
  -H "Authorization: Bearer your_api_key_here"
```

### Missing Dependencies
Install required packages for the services you want to use. The server will start even if optional dependencies are missing.

### Configuration Issues
- Check environment variables are set correctly
- Verify API keys and credentials have proper permissions
- Review service-specific documentation for setup requirements
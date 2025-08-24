# Multi-TTS Service Documentation

## Overview

The OpenAI-compatible TTS API now supports multiple Text-to-Speech services alongside the original Edge TTS. You can use Azure Cognitive Services TTS, Google Cloud Text-to-Speech, APIpie (OpenAI-compatible APIs), and Amazon Polly.

## Supported Services

### 1. Edge TTS (Microsoft) - `edgetts` or `edge`
- **Free** Microsoft Edge text-to-speech service
- **No API key required**
- **Default service** for backward compatibility
- Uses Microsoft's neural voices

### 2. Azure Cognitive Services TTS - `azuretts` or `azure`
- Microsoft's premium TTS service
- Requires Azure subscription and API key
- High-quality neural voices
- SSML support

### 3. Google Cloud Text-to-Speech - `googlecloudtts`, `google`, or `gcp`
- Google's cloud-based TTS service
- Requires Google Cloud project and credentials
- WaveNet and Neural2 voices available
- Multiple languages and voices

### 4. APIpie TTS - `apipietts`, `apipie`, or `openai`
- For OpenAI-compatible TTS APIs
- Requires API key and base URL configuration
- Perfect for using OpenAI's actual TTS API or other compatible services
- Supports all OpenAI voice names natively

### 5. Amazon Polly - `amazonpolly`, `polly`, or `aws`
- Amazon's neural text-to-speech service
- Requires AWS credentials
- Neural and standard voices available
- SSML support

## Configuration

Add the following environment variables to your `.env` file to configure each service:

```env
# Default TTS service (optional, defaults to edgetts)
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

## Usage

### Basic Usage (Default Service)

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello, world!",
    "voice": "alloy"
  }' \
  --output speech.mp3
```

### Using a Specific Service

Add the `tts_service` parameter to specify which service to use:

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Azure TTS!",
    "voice": "alloy",
    "tts_service": "azuretts"
  }' \
  --output speech.mp3
```

### Service Examples

#### Edge TTS (Free)
```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Edge TTS!",
    "voice": "alloy",
    "tts_service": "edgetts"
  }' \
  --output speech.mp3
```

#### Azure TTS
```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Azure TTS!",
    "voice": "nova",
    "tts_service": "azuretts",
    "speed": 1.2
  }' \
  --output speech.mp3
```

#### Google Cloud TTS
```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Google Cloud TTS!",
    "voice": "shimmer",
    "tts_service": "googlecloudtts",
    "response_format": "wav"
  }' \
  --output speech.wav
```

#### APIpie (OpenAI) TTS
```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from OpenAI TTS!",
    "voice": "echo",
    "tts_service": "apipietts"
  }' \
  --output speech.mp3
```

#### Amazon Polly
```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Amazon Polly!",
    "voice": "onyx",
    "tts_service": "amazonpolly"
  }' \
  --output speech.mp3
```

## New API Endpoints

### Service Information
Get information about all available services:

```bash
curl -X GET http://localhost:5050/v1/services \
  -H "Authorization: Bearer your_api_key_here"
```

Response includes service availability, voice mappings, and supported formats.

### Service-Specific Voices
Get voices for a specific service:

```bash
curl -X GET http://localhost:5050/v1/services/azuretts/voices \
  -H "Authorization: Bearer your_api_key_here"
```

Add language filtering:
```bash
curl -X GET "http://localhost:5050/v1/services/googlecloudtts/voices?language=en-US" \
  -H "Authorization: Bearer your_api_key_here"
```

## Voice Mapping

Each service maps OpenAI voice names to their own voice systems:

| OpenAI Voice | Edge TTS | Azure TTS | Google Cloud | Amazon Polly |
|--------------|----------|-----------|--------------|--------------|
| alloy        | en-US-JennyNeural | en-US-JennyNeural | en-US-Journey-F | Joanna |
| echo         | en-US-GuyNeural | en-US-GuyNeural | en-US-Journey-D | Justin |
| fable        | en-GB-SoniaNeural | en-GB-SoniaNeural | en-GB-Standard-A | Amy |
| nova         | en-US-AriaNeural | en-US-AriaNeural | en-US-Journey-F | Emma |
| onyx         | en-US-EricNeural | en-US-EricNeural | en-US-Journey-D | Matthew |
| shimmer      | en-US-EmmaNeural | en-US-EmmaNeural | en-US-Journey-F | Kendra |

## Fallback Behavior

- If a requested service is not available or not configured, the system automatically falls back to the default service (Edge TTS)
- If the default service is also unavailable, an error is returned
- Service availability is checked in real-time

## Streaming Support

All services support streaming with the `stream_format: "sse"` parameter:

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "This will stream as Server-Sent Events",
    "voice": "alloy",
    "stream_format": "sse",
    "tts_service": "azuretts"
  }'
```

## Installation

Install additional dependencies for the services you want to use:

```bash
# For Azure TTS
pip install azure-cognitiveservices-speech

# For Google Cloud TTS
pip install google-cloud-texttospeech

# For Amazon Polly
pip install boto3

# aiohttp is included for APIpie TTS
```

## Error Handling

- Services that are not properly configured will show as "unavailable" in the `/v1/services` endpoint
- Failed TTS requests automatically fall back to the default service if possible
- Detailed error logging can be enabled with `DETAILED_ERROR_LOGGING=True`

## Backward Compatibility

- All existing requests continue to work unchanged
- The original Edge TTS behavior is preserved as the default
- No breaking changes to existing API endpoints
- Original environment variables remain supported
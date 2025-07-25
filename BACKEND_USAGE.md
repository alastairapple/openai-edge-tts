# Multi-Backend TTS Usage Guide

This project now supports three TTS backends:

1. **EdgeTTS** - Microsoft Edge TTS (default, free)
2. **AzureTTS** - Azure Cognitive Services Speech
3. **Gemini** - Google Gemini Audio Generation

## Configuration

Set your backend in the `.env` file:

```env
# Default backend (edgetts, azuretts, gemini)
DEFAULT_BACKEND=edgetts

# Azure TTS settings (required for azuretts backend)
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=eastus

# Gemini settings (required for gemini backend)
GEMINI_API_KEY=your_gemini_api_key_here
```

## API Usage

### 1. EdgeTTS Backend (Default)

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Microsoft Edge TTS!",
    "voice": "alloy",
    "backend": "edgetts"
  }' \
  --output speech_edge.mp3
```

### 2. Azure TTS Backend

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Azure Cognitive Services!",
    "voice": "alloy",
    "backend": "azuretts",
    "response_format": "wav"
  }' \
  --output speech_azure.wav
```

### 3. Gemini TTS Backend

```bash
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "input": "Hello from Google Gemini!",
    "voice": "nova",
    "backend": "gemini"
  }' \
  --output speech_gemini.mp3
```

## Voice Mapping

The system maps OpenAI voice names to backend-specific voices:

### EdgeTTS Voices
- `alloy` → `en-US-JennyNeural`
- `echo` → `en-US-GuyNeural`
- `fable` → `en-GB-SoniaNeural`
- `nova` → `en-US-AriaNeural`
- `onyx` → `en-US-EricNeural`
- `shimmer` → `en-US-EmmaNeural`

### Azure TTS Voices
Uses the same mapping as EdgeTTS (both use Azure Neural voices)

### Gemini Voices
- `alloy` → `Kore`
- `echo` → `Kore`
- `fable` → `Aoede`
- `nova` → `Kore`
- `onyx` → `Charon`
- `shimmer` → `Kore`

## Backend-Specific Features

### EdgeTTS
- ✅ Supports all audio formats (mp3, wav, opus, aac, flac)
- ✅ Supports speed adjustment (0.25x to 4.0x)
- ✅ Supports SSE streaming
- ✅ Free to use

### Azure TTS
- ✅ Supports all audio formats
- ✅ Supports speed adjustment
- ❌ No SSE streaming support yet
- 💰 Requires Azure subscription

### Gemini
- ✅ Supports all audio formats
- ❌ No speed adjustment support
- ❌ No SSE streaming support yet  
- 💰 Requires Google Cloud/Gemini API key

## Installation

Install the required dependencies:

```bash
pip install azure-cognitiveservices-speech google-genai
```

Or use the updated requirements.txt:

```bash
pip install -r requirements.txt
```

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```env
   DEFAULT_BACKEND=edgetts
   AZURE_SPEECH_KEY=your_key_here
   AZURE_SPEECH_REGION=eastus
   GEMINI_API_KEY=your_key_here
   ```

## Python Usage Example

```python
import requests

# Test different backends
backends = ['edgetts', 'azuretts', 'gemini']

for backend in backends:
    response = requests.post('http://localhost:5050/v1/audio/speech', 
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer your_api_key_here'
        },
        json={
            'input': f'Hello from {backend}!',
            'voice': 'alloy',
            'backend': backend
        })
    
    if response.status_code == 200:
        with open(f'speech_{backend}.mp3', 'wb') as f:
            f.write(response.content)
        print(f'✅ {backend} audio saved')
    else:
        print(f'❌ {backend} failed: {response.text}')
```

## Troubleshooting

### Azure TTS Issues
- Verify your `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` are correct
- Check your Azure subscription has speech services enabled

### Gemini Issues  
- Verify your `GEMINI_API_KEY` is valid
- Ensure you have access to the `gemini-2.5-flash-preview-tts` model

### General Issues
- Check the server logs for detailed error messages
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file configuration
# config.py

DEFAULT_CONFIGS = {
    # Server settings
    "PORT": 5050,
    "API_KEY": 'your_api_key_here',  # Fallback API key

    # TTS settings
    "DEFAULT_VOICE": 'en-US-AvaNeural',
    "DEFAULT_RESPONSE_FORMAT": 'mp3',
    "DEFAULT_SPEED": 1.0,
    "DEFAULT_LANGUAGE": 'en-US',
    "DEFAULT_BACKEND": 'edgetts',  # Options: 'edgetts', 'azuretts', 'gemini'

    # Feature flags
    "REQUIRE_API_KEY": True,
    "REMOVE_FILTER": False,
    "EXPAND_API": True,
    "DETAILED_ERROR_LOGGING": True,
    
    # Backend-specific settings
    "AZURE_SPEECH_KEY": '',  # Azure Speech Service subscription key
    "AZURE_SPEECH_REGION": 'eastus',  # Azure Speech Service region
    "GEMINI_API_KEY": '',  # Gemini API key
} 
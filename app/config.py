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
    "DEFAULT_TTS_SERVICE": 'edgetts',  # Default service for backward compatibility

    # Feature flags
    "REQUIRE_API_KEY": True,
    "REMOVE_FILTER": False,
    "EXPAND_API": True,
    "DETAILED_ERROR_LOGGING": True,
    
    # Service-specific defaults
    "AZURE_SPEECH_REGION": 'eastus',
    "AWS_REGION": 'us-east-1',
    "APIPIE_TIMEOUT": 30,
} 
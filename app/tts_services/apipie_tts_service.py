# apipie_tts_service.py

import os
import tempfile
import aiohttp
import asyncio
from typing import List, Dict, Any, AsyncGenerator

from .base_service import BaseTTSService


class APIpieTTSService(BaseTTSService):
    """APIpie (OpenAI-compatible) TTS service implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Configuration for APIpie service
        self.api_key = self.config.get('APIPIE_API_KEY') or os.getenv('APIPIE_API_KEY')
        self.base_url = self.config.get('APIPIE_BASE_URL') or os.getenv('APIPIE_BASE_URL', 'https://api.openai.com')
        self.timeout = self.config.get('APIPIE_TIMEOUT', 30)
        
        # Since this is OpenAI-compatible, we can use the same voice names
        self.voice_mapping = {
            'alloy': 'alloy',
            'ash': 'ash', 
            'ballad': 'ballad',
            'coral': 'coral',
            'echo': 'echo',
            'fable': 'fable',
            'nova': 'nova',
            'onyx': 'onyx',
            'sage': 'sage',
            'shimmer': 'shimmer',
            'verse': 'verse',
        }
        
        # Default voice if none specified
        self.default_voice = 'alloy'
    
    def get_voice_mapping(self) -> Dict[str, str]:
        """Get OpenAI voice mapping (no mapping needed for OpenAI-compatible API)."""
        return self.voice_mapping
    
    def is_available(self) -> bool:
        """Check if APIpie TTS is available and configured."""
        return bool(self.api_key and self.base_url)
    
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """Generate speech using APIpie (OpenAI-compatible) API."""
        if not self.is_available():
            raise RuntimeError("APIpie TTS is not properly configured. Please set APIPIE_API_KEY and APIPIE_BASE_URL.")
        
        # Map voice name (should be the same for OpenAI-compatible API)
        apipie_voice = self.map_voice(voice)
        
        # Prepare the request payload
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": apipie_voice,
            "response_format": response_format,
            "speed": speed
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Make API request
        url = f"{self.base_url.rstrip('/')}/v1/audio/speech"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    # Create temporary file and write audio content
                    temp_path = self.create_temp_file(f".{response_format}")
                    
                    with open(temp_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    return temp_path
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"APIpie TTS API error (status {response.status}): {error_text}")
    
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0) -> AsyncGenerator[bytes, None]:
        """Generate streaming speech using APIpie API."""
        if not self.is_available():
            raise RuntimeError("APIpie TTS is not properly configured.")
        
        # Map voice name
        apipie_voice = self.map_voice(voice)
        
        # Prepare the request payload for streaming
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": apipie_voice,
            "response_format": "mp3",
            "speed": speed,
            "stream_format": "audio"  # Request raw audio streaming
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url.rstrip('/')}/v1/audio/speech"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    # Stream the audio chunks
                    async for chunk in response.content.iter_chunked(4096):
                        if chunk:
                            yield chunk
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"APIpie TTS streaming error (status {response.status}): {error_text}")
    
    async def get_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get available voices from APIpie API."""
        if not self.is_available():
            return []
        
        # Try to get voices from the API if it supports the voices endpoint
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url.rstrip('/')}/v1/audio/voices"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        voices = data.get('voices', [])
                        
                        # Filter by language if specified
                        if language and language != 'all':
                            voices = [v for v in voices if v.get('language', '').startswith(language)]
                        
                        return voices
        except Exception as e:
            print(f"Could not fetch voices from APIpie API: {e}")
        
        # Fallback to standard OpenAI voices
        openai_voices = [
            {"name": "alloy", "gender": "Female", "language": "en-US"},
            {"name": "echo", "gender": "Male", "language": "en-US"},
            {"name": "fable", "gender": "Female", "language": "en-GB"},
            {"name": "onyx", "gender": "Male", "language": "en-US"},
            {"name": "nova", "gender": "Female", "language": "en-US"},
            {"name": "shimmer", "gender": "Female", "language": "en-US"},
            {"name": "ash", "gender": "Male", "language": "en-US"},
            {"name": "ballad", "gender": "Male", "language": "en-GB"},
            {"name": "coral", "gender": "Female", "language": "en-AU"},
            {"name": "sage", "gender": "Female", "language": "en-US"},
            {"name": "verse", "gender": "Male", "language": "en-US"},
        ]
        
        # Filter by language if specified
        if language and language != 'all':
            openai_voices = [v for v in openai_voices if v['language'].startswith(language)]
        
        return openai_voices
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """Get available models from APIpie API."""
        if not self.is_available():
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url.rstrip('/')}/v1/models"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get('data', [])
                        
                        # Filter for TTS models
                        tts_models = [m for m in models if 'tts' in m.get('id', '').lower()]
                        return tts_models
        except Exception as e:
            print(f"Could not fetch models from APIpie API: {e}")
        
        # Fallback to standard OpenAI TTS models
        return [
            {"id": "tts-1", "name": "Text-to-speech v1"},
            {"id": "tts-1-hd", "name": "Text-to-speech v1 HD"},
        ]
    
    def get_supported_formats(self) -> List[str]:
        """Get supported audio formats."""
        return ["mp3", "opus", "aac", "flac", "wav", "pcm"]
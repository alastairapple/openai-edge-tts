# base_service.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Union
import tempfile
import os


class BaseTTSService(ABC):
    """Abstract base class for TTS services."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the TTS service with configuration."""
        self.config = config or {}
        self.service_name = self.__class__.__name__.replace('TTSService', '').lower()
    
    @abstractmethod
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """
        Generate speech from text and return the path to the audio file.
        
        Args:
            text: The text to convert to speech
            voice: The voice to use (service-specific or OpenAI-compatible name)
            response_format: Audio format (mp3, wav, etc.)
            speed: Speech speed (0.25 to 4.0)
            
        Returns:
            Path to the generated audio file
        """
        pass
    
    @abstractmethod
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0) -> AsyncGenerator[bytes, None]:
        """
        Generate streaming speech from text.
        
        Args:
            text: The text to convert to speech
            voice: The voice to use
            speed: Speech speed
            
        Yields:
            Audio chunks as bytes
        """
        pass
    
    @abstractmethod
    async def get_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """
        Get available voices for this service.
        
        Args:
            language: Filter by language/locale (optional)
            
        Returns:
            List of voice dictionaries with name, gender, language
        """
        pass
    
    @abstractmethod
    def get_voice_mapping(self) -> Dict[str, str]:
        """
        Get mapping from OpenAI voice names to service-specific voice names.
        
        Returns:
            Dictionary mapping OpenAI voice names to service voice names
        """
        pass
    
    def map_voice(self, voice: str) -> str:
        """
        Map OpenAI voice name to service-specific voice name.
        
        Args:
            voice: OpenAI voice name or service-specific voice name
            
        Returns:
            Service-specific voice name
        """
        voice_mapping = self.get_voice_mapping()
        return voice_mapping.get(voice, voice)
    
    def is_available(self) -> bool:
        """
        Check if the service is available and properly configured.
        
        Returns:
            True if service is available
        """
        return True
    
    def get_supported_formats(self) -> List[str]:
        """
        Get supported audio formats for this service.
        
        Returns:
            List of supported format strings
        """
        return ["mp3", "wav", "ogg", "aac"]
    
    def validate_speed(self, speed: float) -> float:
        """
        Validate and normalize speed parameter.
        
        Args:
            speed: Speech speed value
            
        Returns:
            Validated speed value
        """
        return max(0.25, min(4.0, speed))
    
    def create_temp_file(self, suffix: str = ".mp3") -> str:
        """
        Create a temporary file for audio output.
        
        Args:
            suffix: File suffix including dot (e.g., ".mp3")
            
        Returns:
            Path to temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()
        return temp_file.name
    
    def cleanup_temp_file(self, file_path: str) -> None:
        """
        Clean up a temporary file.
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except OSError:
            pass  # File might already be cleaned up
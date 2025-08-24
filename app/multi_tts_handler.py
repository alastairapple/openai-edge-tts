# multi_tts_handler.py

import asyncio
import os
from typing import List, Dict, Any, AsyncGenerator, Union

from tts_services import TTSServiceFactory, BaseTTSService
from config import DEFAULT_CONFIGS


class MultiTTSHandler:
    """Handler for managing multiple TTS services."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.factory = TTSServiceFactory()
        self.default_service_name = self.config.get('DEFAULT_TTS_SERVICE', DEFAULT_CONFIGS['DEFAULT_TTS_SERVICE'])
        
        # Cache for service instances
        self._service_cache = {}
    
    def get_service(self, service_name: str = None) -> BaseTTSService:
        """
        Get a TTS service instance.
        
        Args:
            service_name: Name of the service to get (defaults to default service)
            
        Returns:
            TTS service instance
        """
        service_name = service_name or self.default_service_name
        service_name = service_name.lower()
        
        # Check cache first
        if service_name in self._service_cache:
            return self._service_cache[service_name]
        
        # Create new service instance
        try:
            service = self.factory.create_service(service_name, self.config)
            self._service_cache[service_name] = service
            return service
        except ValueError as e:
            # Fall back to default service if requested service is not available
            if service_name != self.default_service_name:
                print(f"Warning: {e}. Falling back to default service: {self.default_service_name}")
                return self.get_service(self.default_service_name)
            raise
    
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", 
                            speed: float = 1.0, service_name: str = None) -> str:
        """
        Generate speech using the specified service.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            response_format: Audio format
            speed: Speech speed
            service_name: TTS service to use
            
        Returns:
            Path to generated audio file
        """
        service = self.get_service(service_name)
        
        if not service.is_available():
            # Try to fall back to default service
            if service_name and service_name != self.default_service_name:
                print(f"Warning: {service_name} service is not available. Falling back to {self.default_service_name}")
                service = self.get_service(self.default_service_name)
                if not service.is_available():
                    raise RuntimeError(f"Default TTS service {self.default_service_name} is not available")
            else:
                raise RuntimeError(f"TTS service {service_name or self.default_service_name} is not available")
        
        return await service.generate_speech(text, voice, response_format, speed)
    
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0, 
                                   service_name: str = None) -> AsyncGenerator[bytes, None]:
        """
        Generate streaming speech using the specified service.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            speed: Speech speed  
            service_name: TTS service to use
            
        Yields:
            Audio chunks as bytes
        """
        service = self.get_service(service_name)
        
        if not service.is_available():
            # Try to fall back to default service
            if service_name and service_name != self.default_service_name:
                print(f"Warning: {service_name} service is not available. Falling back to {self.default_service_name}")
                service = self.get_service(self.default_service_name)
                if not service.is_available():
                    raise RuntimeError(f"Default TTS service {self.default_service_name} is not available")
            else:
                raise RuntimeError(f"TTS service {service_name or self.default_service_name} is not available")
        
        async for chunk in service.generate_speech_stream(text, voice, speed):
            yield chunk
    
    async def get_voices(self, language: str = None, service_name: str = None) -> List[Dict[str, Any]]:
        """
        Get available voices from the specified service.
        
        Args:
            language: Language filter
            service_name: TTS service to query
            
        Returns:
            List of voice dictionaries
        """
        service = self.get_service(service_name)
        return await service.get_voices(language)
    
    def get_models(self, service_name: str = None) -> List[Dict[str, Any]]:
        """
        Get available models.
        
        Args:
            service_name: TTS service to query
            
        Returns:
            List of model dictionaries
        """
        # For now, return standard TTS models
        # Individual services could override this if they have specific models
        return [
            {"id": "tts-1", "name": "Text-to-speech v1"},
            {"id": "tts-1-hd", "name": "Text-to-speech v1 HD"},
            {"id": "gpt-4o-mini-tts", "name": "GPT-4o mini TTS"}
        ]
    
    def get_models_formatted(self, service_name: str = None) -> List[Dict[str, str]]:
        """Get models in OpenAI-compatible format."""
        models = self.get_models(service_name)
        return [{"id": model["id"]} for model in models]
    
    def get_voices_formatted(self, service_name: str = None) -> List[Dict[str, str]]:
        """Get OpenAI voice mappings for the specified service."""
        service = self.get_service(service_name)
        voice_mapping = service.get_voice_mapping()
        return [{"id": k, "name": v} for k, v in voice_mapping.items()]
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get list of available services."""
        return self.factory.get_available_services()
    
    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all services."""
        return self.factory.get_service_info()


# Synchronous wrapper functions for backward compatibility
def generate_speech(text: str, voice: str, response_format: str, speed: float = 1.0, service_name: str = None) -> str:
    """Synchronous wrapper for generate_speech."""
    handler = MultiTTSHandler()
    return asyncio.run(handler.generate_speech(text, voice, response_format, speed, service_name))


def generate_speech_stream(text: str, voice: str, speed: float = 1.0, service_name: str = None) -> AsyncGenerator[bytes, None]:
    """Synchronous wrapper for generate_speech_stream."""
    handler = MultiTTSHandler()
    return handler.generate_speech_stream(text, voice, speed, service_name)


def get_models() -> List[Dict[str, Any]]:
    """Get available models."""
    handler = MultiTTSHandler()
    return handler.get_models()


def get_models_formatted() -> List[Dict[str, str]]:
    """Get models in OpenAI-compatible format."""
    handler = MultiTTSHandler()
    return handler.get_models_formatted()


def get_voices(language: str = None, service_name: str = None) -> List[Dict[str, Any]]:
    """Get available voices."""
    handler = MultiTTSHandler()
    return asyncio.run(handler.get_voices(language, service_name))


def get_voices_formatted(service_name: str = None) -> List[Dict[str, str]]:
    """Get OpenAI voice mappings."""
    handler = MultiTTSHandler()
    return handler.get_voices_formatted(service_name)
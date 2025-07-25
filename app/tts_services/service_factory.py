# service_factory.py

from typing import Dict, Any, Optional
import os

from .base_service import BaseTTSService
from .edge_tts_service import EdgeTTSService
from .azure_tts_service import AzureTTSService
from .google_cloud_tts_service import GoogleCloudTTSService
from .apipie_tts_service import APIpieTTSService
from .amazon_polly_service import AmazonPollyTTSService


class TTSServiceFactory:
    """Factory class for creating TTS service instances."""
    
    # Map service names to service classes
    SERVICE_REGISTRY = {
        'edgetts': EdgeTTSService,
        'edge': EdgeTTSService,
        'azuretts': AzureTTSService,
        'azure': AzureTTSService,
        'googlecloudtts': GoogleCloudTTSService,
        'google': GoogleCloudTTSService,
        'gcp': GoogleCloudTTSService,
        'apipietts': APIpieTTSService,
        'apipie': APIpieTTSService,
        'openai': APIpieTTSService,
        'amazonpolly': AmazonPollyTTSService,
        'polly': AmazonPollyTTSService,
        'aws': AmazonPollyTTSService,
    }
    
    @classmethod
    def create_service(cls, service_name: str, config: Dict[str, Any] = None) -> BaseTTSService:
        """
        Create a TTS service instance by name.
        
        Args:
            service_name: Name of the TTS service (case-insensitive)
            config: Optional configuration dictionary
            
        Returns:
            TTS service instance
            
        Raises:
            ValueError: If service name is not supported
        """
        service_name_lower = service_name.lower()
        
        if service_name_lower not in cls.SERVICE_REGISTRY:
            available_services = list(cls.SERVICE_REGISTRY.keys())
            raise ValueError(f"Unsupported TTS service: {service_name}. Available services: {available_services}")
        
        service_class = cls.SERVICE_REGISTRY[service_name_lower]
        return service_class(config)
    
    @classmethod
    def get_default_service(cls, config: Dict[str, Any] = None) -> BaseTTSService:
        """
        Get the default TTS service.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            Default TTS service instance (EdgeTTS for backward compatibility)
        """
        default_service_name = os.getenv('DEFAULT_TTS_SERVICE', 'edgetts')
        return cls.create_service(default_service_name, config)
    
    @classmethod
    def get_available_services(cls) -> Dict[str, bool]:
        """
        Get a list of all available services and their availability status.
        
        Returns:
            Dictionary mapping service names to availability status
        """
        available_services = {}
        
        # Check each unique service class
        checked_classes = set()
        for service_name, service_class in cls.SERVICE_REGISTRY.items():
            if service_class in checked_classes:
                continue
            checked_classes.add(service_class)
            
            try:
                service_instance = service_class()
                is_available = service_instance.is_available()
                
                # Map all aliases to the same availability status
                for name, cls_type in cls.SERVICE_REGISTRY.items():
                    if cls_type == service_class:
                        available_services[name] = is_available
            except Exception as e:
                # If we can't instantiate the service, mark as unavailable
                for name, cls_type in cls.SERVICE_REGISTRY.items():
                    if cls_type == service_class:
                        available_services[name] = False
        
        return available_services
    
    @classmethod
    def get_service_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available services.
        
        Returns:
            Dictionary with service information
        """
        service_info = {}
        
        # Get unique service classes and their info
        checked_classes = set()
        for service_name, service_class in cls.SERVICE_REGISTRY.items():
            if service_class in checked_classes:
                continue
            checked_classes.add(service_class)
            
            try:
                service_instance = service_class()
                
                # Get aliases for this service class
                aliases = [name for name, cls_type in cls.SERVICE_REGISTRY.items() if cls_type == service_class]
                
                info = {
                    'class_name': service_class.__name__,
                    'service_name': service_instance.service_name,
                    'aliases': aliases,
                    'is_available': service_instance.is_available(),
                    'supported_formats': service_instance.get_supported_formats(),
                    'voice_mapping': service_instance.get_voice_mapping()
                }
                
                # Use the primary alias (first one) as the key
                primary_alias = aliases[0] if aliases else service_name
                service_info[primary_alias] = info
                
            except Exception as e:
                # If we can't instantiate the service, provide basic info
                aliases = [name for name, cls_type in cls.SERVICE_REGISTRY.items() if cls_type == service_class]
                primary_alias = aliases[0] if aliases else service_name
                
                service_info[primary_alias] = {
                    'class_name': service_class.__name__,
                    'service_name': 'unknown',
                    'aliases': aliases,
                    'is_available': False,
                    'supported_formats': [],
                    'voice_mapping': {},
                    'error': str(e)
                }
        
        return service_info
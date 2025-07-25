# edge_tts_service.py

import edge_tts
import asyncio
import tempfile
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator

from .base_service import BaseTTSService
from utils import DETAILED_ERROR_LOGGING
from config import DEFAULT_CONFIGS


class EdgeTTSService(BaseTTSService):
    """Microsoft Edge TTS service implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.default_language = self.config.get('DEFAULT_LANGUAGE', DEFAULT_CONFIGS["DEFAULT_LANGUAGE"])
        
        # OpenAI voice names mapped to edge-tts equivalents
        self.voice_mapping = {
            'alloy': 'en-US-JennyNeural',
            'ash': 'en-US-AndrewNeural',
            'ballad': 'en-GB-ThomasNeural',
            'coral': 'en-AU-NatashaNeural',
            'echo': 'en-US-GuyNeural',
            'fable': 'en-GB-SoniaNeural',
            'nova': 'en-US-AriaNeural',
            'onyx': 'en-US-EricNeural',
            'sage': 'en-US-JennyNeural',
            'shimmer': 'en-US-EmmaNeural',
            'verse': 'en-US-BrianNeural',
        }
    
    def get_voice_mapping(self) -> Dict[str, str]:
        """Get OpenAI to Edge TTS voice mapping."""
        return self.voice_mapping
    
    def is_ffmpeg_installed(self) -> bool:
        """Check if FFmpeg is installed and accessible."""
        try:
            subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def speed_to_rate(self, speed: float) -> str:
        """
        Converts a multiplicative speed value to the edge-tts "rate" format.
        
        Args:
            speed: The multiplicative speed value (e.g., 1.5 for +50%, 0.5 for -50%).
        
        Returns:
            The formatted "rate" string (e.g., "+50%" or "-50%").
        """
        speed = self.validate_speed(speed)
        if speed < 0 or speed > 2:
            raise ValueError("Speed must be between 0 and 2 (inclusive).")

        # Convert speed to percentage change
        percentage_change = (speed - 1) * 100

        # Format with a leading "+" or "-" as required
        return f"{percentage_change:+.0f}%"
    
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """Generate TTS audio and optionally convert to a different format."""
        # Map voice name
        edge_tts_voice = self.map_voice(voice)
        
        # Generate the TTS output in mp3 format first
        temp_mp3_path = self.create_temp_file(".mp3")

        # Convert speed to SSML rate format
        try:
            speed_rate = self.speed_to_rate(speed)
        except Exception as e:
            print(f"Error converting speed: {e}. Defaulting to +0%.")
            speed_rate = "+0%"

        # Generate the MP3 file
        communicator = edge_tts.Communicate(text=text, voice=edge_tts_voice, rate=speed_rate)
        await communicator.save(temp_mp3_path)

        # If the requested format is mp3, return the generated file directly
        if response_format == "mp3":
            return temp_mp3_path

        # Check if FFmpeg is installed
        if not self.is_ffmpeg_installed():
            print("FFmpeg is not available. Returning unmodified mp3 file.")
            return temp_mp3_path

        # Create a new temporary file for the converted output
        converted_path = self.create_temp_file(f".{response_format}")

        # Build the FFmpeg command
        ffmpeg_command = [
            "ffmpeg",
            "-i", temp_mp3_path,  # Input file path
            "-c:a", {
                "aac": "aac",
                "mp3": "libmp3lame",
                "wav": "pcm_s16le",
                "opus": "libopus",
                "flac": "flac"
            }.get(response_format, "aac"),  # Default to AAC if unknown
        ]

        if response_format != "wav":
            ffmpeg_command.extend(["-b:a", "192k"])

        ffmpeg_command.extend([
            "-f", {
                "aac": "mp4",  # AAC in MP4 container
                "mp3": "mp3",
                "wav": "wav",
                "opus": "ogg",
                "flac": "flac"
            }.get(response_format, response_format),  # Default to matching format
            "-y",  # Overwrite without prompt
            converted_path  # Output file path
        ])

        try:
            # Run FFmpeg command and ensure no errors occur
            subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            # Clean up potentially created (but incomplete) converted file
            self.cleanup_temp_file(converted_path)
            # Clean up the original mp3 file as well, since conversion failed
            self.cleanup_temp_file(temp_mp3_path)
            
            if DETAILED_ERROR_LOGGING:
                error_message = f"FFmpeg error during audio conversion. Command: '{' '.join(e.cmd)}'. Stderr: {e.stderr.decode('utf-8', 'ignore')}"
                print(error_message)
            else:
                error_message = f"FFmpeg error during audio conversion: {e}"
                print(error_message)
            raise RuntimeError(f"FFmpeg error during audio conversion: {e}")

        # Clean up the original temporary file (original mp3) as it's now converted
        self.cleanup_temp_file(temp_mp3_path)

        return converted_path
    
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0) -> AsyncGenerator[bytes, None]:
        """Generate streaming TTS audio using edge-tts."""
        # Map voice name
        edge_tts_voice = self.map_voice(voice)
        
        # Convert speed to SSML rate format
        try:
            speed_rate = self.speed_to_rate(speed)
        except Exception as e:
            print(f"Error converting speed: {e}. Defaulting to +0%.")
            speed_rate = "+0%"
        
        # Create the communicator for streaming
        communicator = edge_tts.Communicate(text=text, voice=edge_tts_voice, rate=speed_rate)
        
        # Stream the audio data
        async for chunk in communicator.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    
    async def get_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get available voices from Edge TTS."""
        # List all voices, filter by language if specified
        all_voices = await edge_tts.list_voices()
        language = language or self.default_language
        filtered_voices = [
            {"name": v['ShortName'], "gender": v['Gender'], "language": v['Locale']}
            for v in all_voices if language == 'all' or language is None or v['Locale'] == language
        ]
        return filtered_voices
    
    def get_supported_formats(self) -> List[str]:
        """Get supported audio formats."""
        return ["mp3", "wav", "ogg", "aac", "flac", "opus"]
    
    def is_available(self) -> bool:
        """Check if Edge TTS is available."""
        # Edge TTS doesn't require API keys, just network access
        return True
# google_cloud_tts_service.py

import os
import tempfile
import subprocess
import base64
from typing import List, Dict, Any, AsyncGenerator
import asyncio

from .base_service import BaseTTSService


class GoogleCloudTTSService(BaseTTSService):
    """Google Cloud Text-to-Speech service implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Google Cloud credentials can be set via service account key file or environment variable
        self.credentials_path = self.config.get('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.project_id = self.config.get('GOOGLE_CLOUD_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # OpenAI voice names mapped to Google Cloud TTS equivalents
        self.voice_mapping = {
            'alloy': 'en-US-Journey-F',
            'ash': 'en-US-Journey-D',
            'ballad': 'en-GB-Standard-D',
            'coral': 'en-AU-Standard-A',
            'echo': 'en-US-Journey-D',
            'fable': 'en-GB-Standard-A',
            'nova': 'en-US-Journey-F',
            'onyx': 'en-US-Journey-D',
            'sage': 'en-US-Journey-F',
            'shimmer': 'en-US-Journey-F',
            'verse': 'en-US-Journey-D',
        }
        
        # Default voice if none specified
        self.default_voice = 'en-US-Journey-F'
    
    def get_voice_mapping(self) -> Dict[str, str]:
        """Get OpenAI to Google Cloud TTS voice mapping."""
        return self.voice_mapping
    
    def is_available(self) -> bool:
        """Check if Google Cloud TTS is available and configured."""
        # Check if credentials are available (either file path or service account key)
        has_credentials = bool(
            self.credentials_path or 
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or
            os.getenv('GOOGLE_CLOUD_TTS_API_KEY')
        )
        return has_credentials
    
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """Generate speech using Google Cloud Text-to-Speech."""
        if not self.is_available():
            raise RuntimeError("Google Cloud TTS is not properly configured. Please set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_CLOUD_TTS_API_KEY.")
        
        try:
            from google.cloud import texttospeech
        except ImportError:
            raise RuntimeError("Google Cloud TTS library not installed. Please install: pip install google-cloud-texttospeech")
        
        # Map voice name
        gcp_voice = self.map_voice(voice)
        
        # Parse voice name to get language and voice
        if '-' in gcp_voice and len(gcp_voice.split('-')) >= 3:
            parts = gcp_voice.split('-')
            language_code = f"{parts[0]}-{parts[1]}"
            voice_name = gcp_voice
        else:
            language_code = "en-US"
            voice_name = gcp_voice
        
        # Create client
        client = texttospeech.TextToSpeechClient()
        
        # Set up the synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build the voice request
        voice_config = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        # Select the audio file type and set speaking speed
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speed
        )
        
        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_config,
            audio_config=audio_config
        )
        
        # Create temporary file and write audio content
        temp_path = self.create_temp_file(".mp3")
        with open(temp_path, "wb") as out:
            out.write(response.audio_content)
        
        # Convert format if needed
        if response_format != "mp3":
            return await self._convert_audio_format(temp_path, response_format)
        
        return temp_path
    
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0) -> AsyncGenerator[bytes, None]:
        """Generate streaming speech using Google Cloud TTS."""
        if not self.is_available():
            raise RuntimeError("Google Cloud TTS is not properly configured.")
        
        # Google Cloud TTS doesn't provide true streaming, so we generate and chunk
        temp_path = await self.generate_speech(text, voice, "mp3", speed)
        
        try:
            with open(temp_path, 'rb') as f:
                while True:
                    chunk = f.read(4096)  # 4KB chunks
                    if not chunk:
                        break
                    yield chunk
        finally:
            self.cleanup_temp_file(temp_path)
    
    async def get_voices(self, language: str = None) -> List[Dict[str, Any]]:
        """Get available voices from Google Cloud TTS."""
        if not self.is_available():
            return []
        
        try:
            from google.cloud import texttospeech
        except ImportError:
            return []
        
        try:
            client = texttospeech.TextToSpeechClient()
            voices_response = client.list_voices()
            
            voices = []
            for voice in voices_response.voices:
                for language_code in voice.language_codes:
                    if language and language != 'all' and language_code != language:
                        continue
                    
                    # Determine gender
                    gender_map = {
                        texttospeech.SsmlVoiceGender.MALE: "Male",
                        texttospeech.SsmlVoiceGender.FEMALE: "Female",
                        texttospeech.SsmlVoiceGender.NEUTRAL: "Neutral",
                    }
                    gender = gender_map.get(voice.ssml_gender, "Unknown")
                    
                    voices.append({
                        "name": voice.name,
                        "gender": gender,
                        "language": language_code
                    })
            
            return voices
            
        except Exception as e:
            print(f"Error fetching Google Cloud TTS voices: {e}")
            # Return a basic set of common voices as fallback
            fallback_voices = [
                {"name": "en-US-Journey-F", "gender": "Female", "language": "en-US"},
                {"name": "en-US-Journey-D", "gender": "Male", "language": "en-US"},
                {"name": "en-GB-Standard-A", "gender": "Female", "language": "en-GB"},
                {"name": "en-GB-Standard-D", "gender": "Male", "language": "en-GB"},
                {"name": "en-AU-Standard-A", "gender": "Female", "language": "en-AU"},
            ]
            
            if language and language != 'all':
                fallback_voices = [v for v in fallback_voices if v['language'] == language]
            
            return fallback_voices
    
    async def _convert_audio_format(self, input_path: str, target_format: str) -> str:
        """Convert audio to target format using FFmpeg."""
        output_path = self.create_temp_file(f".{target_format}")
        
        ffmpeg_command = [
            "ffmpeg",
            "-i", input_path,
            "-c:a", {
                "aac": "aac",
                "mp3": "libmp3lame",
                "wav": "pcm_s16le", 
                "opus": "libopus",
                "flac": "flac"
            }.get(target_format, "aac"),
            "-y",
            output_path
        ]
        
        try:
            subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.cleanup_temp_file(input_path)  # Remove original file
            return output_path
        except subprocess.CalledProcessError as e:
            self.cleanup_temp_file(output_path)
            self.cleanup_temp_file(input_path)
            raise RuntimeError(f"Audio format conversion failed: {e}")
    
    def get_supported_formats(self) -> List[str]:
        """Get supported audio formats."""
        return ["mp3", "wav", "ogg", "aac", "flac", "opus"]
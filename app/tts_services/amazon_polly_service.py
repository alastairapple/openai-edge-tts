# amazon_polly_service.py

import os
import tempfile
import subprocess
from typing import List, Dict, Any, AsyncGenerator
import asyncio

from .base_service import BaseTTSService


class AmazonPollyTTSService(BaseTTSService):
    """Amazon Polly TTS service implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # AWS configuration
        self.aws_access_key_id = self.config.get('AWS_ACCESS_KEY_ID') or os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = self.config.get('AWS_SECRET_ACCESS_KEY') or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = self.config.get('AWS_REGION') or os.getenv('AWS_REGION', 'us-east-1')
        
        # OpenAI voice names mapped to Amazon Polly equivalents
        self.voice_mapping = {
            'alloy': 'Joanna',
            'ash': 'Matthew',
            'ballad': 'Brian',
            'coral': 'Nicole',
            'echo': 'Justin',
            'fable': 'Amy',
            'nova': 'Emma',
            'onyx': 'Matthew',
            'sage': 'Joanna',
            'shimmer': 'Kendra',
            'verse': 'Joey',
        }
        
        # Default voice if none specified
        self.default_voice = 'Joanna'
    
    def get_voice_mapping(self) -> Dict[str, str]:
        """Get OpenAI to Amazon Polly voice mapping."""
        return self.voice_mapping
    
    def is_available(self) -> bool:
        """Check if Amazon Polly is available and configured."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)
    
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """Generate speech using Amazon Polly."""
        if not self.is_available():
            raise RuntimeError("Amazon Polly is not properly configured. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
        
        try:
            import boto3
        except ImportError:
            raise RuntimeError("boto3 not installed. Please install: pip install boto3")
        
        # Map voice name
        polly_voice = self.map_voice(voice)
        
        # Create Polly client
        polly_client = boto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        ).client('polly')
        
        # Convert speed to SSML prosody rate
        if speed != 1.0:
            speed_percent = f"{int((speed - 1) * 100):+d}%"
            ssml_text = f'<speak><prosody rate="{speed_percent}">{text}</prosody></speak>'
            text_type = 'ssml'
        else:
            ssml_text = text
            text_type = 'text'
        
        # Determine output format for Polly
        polly_format = "mp3" if response_format in ["mp3", "opus", "aac"] else "pcm"
        
        try:
            # Synthesize speech
            response = polly_client.synthesize_speech(
                Text=ssml_text,
                TextType=text_type,
                OutputFormat=polly_format,
                VoiceId=polly_voice,
                Engine='neural' if self._supports_neural_voice(polly_voice) else 'standard'
            )
            
            # Create temporary file and write audio content
            temp_path = self.create_temp_file(f".{polly_format}")
            
            with open(temp_path, "wb") as f:
                f.write(response['AudioStream'].read())
            
            # Convert format if needed
            if response_format != polly_format:
                return await self._convert_audio_format(temp_path, response_format)
            
            return temp_path
            
        except Exception as e:
            raise RuntimeError(f"Amazon Polly synthesis failed: {str(e)}")
    
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0) -> AsyncGenerator[bytes, None]:
        """Generate streaming speech using Amazon Polly."""
        if not self.is_available():
            raise RuntimeError("Amazon Polly is not properly configured.")
        
        # Amazon Polly doesn't provide true streaming, so we generate and chunk
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
        """Get available voices from Amazon Polly."""
        if not self.is_available():
            return []
        
        try:
            import boto3
        except ImportError:
            return []
        
        try:
            # Create Polly client
            polly_client = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            ).client('polly')
            
            # Get voices from Polly
            response = polly_client.describe_voices()
            voices = []
            
            for voice in response['Voices']:
                voice_language = voice['LanguageCode']
                
                # Filter by language if specified
                if language and language != 'all' and not voice_language.startswith(language):
                    continue
                
                voices.append({
                    "name": voice['Id'],
                    "gender": voice['Gender'].title(),
                    "language": voice_language
                })
            
            return voices
            
        except Exception as e:
            print(f"Error fetching Amazon Polly voices: {e}")
            # Return a basic set of common voices as fallback
            fallback_voices = [
                {"name": "Joanna", "gender": "Female", "language": "en-US"},
                {"name": "Matthew", "gender": "Male", "language": "en-US"},
                {"name": "Kendra", "gender": "Female", "language": "en-US"},
                {"name": "Justin", "gender": "Male", "language": "en-US"},
                {"name": "Joey", "gender": "Male", "language": "en-US"},
                {"name": "Amy", "gender": "Female", "language": "en-GB"},
                {"name": "Brian", "gender": "Male", "language": "en-GB"},
                {"name": "Emma", "gender": "Female", "language": "en-GB"},
                {"name": "Nicole", "gender": "Female", "language": "en-AU"},
            ]
            
            if language and language != 'all':
                fallback_voices = [v for v in fallback_voices if v['language'].startswith(language)]
            
            return fallback_voices
    
    def _supports_neural_voice(self, voice_id: str) -> bool:
        """Check if voice supports neural engine."""
        # Neural voices in Polly (this is a subset - in production you'd query the API)
        neural_voices = {
            'Joanna', 'Matthew', 'Kendra', 'Justin', 'Joey', 'Amy', 'Brian', 'Emma',
            'Olivia', 'Aria', 'Ayanda', 'Ivy', 'Ruth', 'Stephen', 'Kevin', 'Kajal'
        }
        return voice_id in neural_voices
    
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
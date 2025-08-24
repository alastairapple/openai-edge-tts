# azure_tts_service.py

import os
import tempfile
import subprocess
from typing import List, Dict, Any, AsyncGenerator
import asyncio

from .base_service import BaseTTSService


class AzureTTSService(BaseTTSService):
    """Azure Cognitive Services Speech TTS implementation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.subscription_key = self.config.get('AZURE_SPEECH_KEY') or os.getenv('AZURE_SPEECH_KEY')
        self.region = self.config.get('AZURE_SPEECH_REGION') or os.getenv('AZURE_SPEECH_REGION', 'eastus')
        
        # OpenAI voice names mapped to Azure TTS equivalents
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
        
        # Default voice if none specified
        self.default_voice = 'en-US-AriaNeural'
    
    def get_voice_mapping(self) -> Dict[str, str]:
        """Get OpenAI to Azure TTS voice mapping."""
        return self.voice_mapping
    
    def is_available(self) -> bool:
        """Check if Azure TTS is available and configured."""
        return bool(self.subscription_key and self.region)
    
    async def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """Generate speech using Azure Cognitive Services."""
        if not self.is_available():
            raise RuntimeError("Azure TTS is not properly configured. Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION.")
        
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise RuntimeError("Azure Speech SDK not installed. Please install: pip install azure-cognitiveservices-speech")
        
        # Map voice name
        azure_voice = self.map_voice(voice)
        
        # Create Azure Speech config
        speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription_key,
            region=self.region
        )
        speech_config.speech_synthesis_voice_name = azure_voice
        
        # Set output format
        if response_format == "wav":
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)
        else:
            speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
        
        # Create temporary output file
        temp_path = self.create_temp_file(f".{response_format}")
        
        # Configure audio output
        audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_path)
        
        # Create synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        # Create SSML with speed adjustment
        speed_percent = int((speed - 1) * 100)
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{azure_voice}">
                <prosody rate="{speed_percent:+d}%">
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        
        # Synthesize speech
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Convert if needed
            if response_format != "mp3" and response_format != "wav":
                return await self._convert_audio_format(temp_path, response_format)
            return temp_path
        else:
            self.cleanup_temp_file(temp_path)
            error_details = result.error_details if hasattr(result, 'error_details') else "Unknown error"
            raise RuntimeError(f"Azure TTS synthesis failed: {error_details}")
    
    async def generate_speech_stream(self, text: str, voice: str, speed: float = 1.0) -> AsyncGenerator[bytes, None]:
        """Generate streaming speech using Azure TTS."""
        if not self.is_available():
            raise RuntimeError("Azure TTS is not properly configured.")
        
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            raise RuntimeError("Azure Speech SDK not installed.")
        
        # For Azure TTS streaming, we'll generate the full audio and chunk it
        # Azure doesn't provide true streaming like Edge TTS
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
        """Get available voices from Azure TTS."""
        if not self.is_available():
            return []
        
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            return []
        
        # Azure TTS voice list (subset of common voices)
        # In a real implementation, you would use the Azure TTS API to get the full list
        azure_voices = [
            {"name": "en-US-AriaNeural", "gender": "Female", "language": "en-US"},
            {"name": "en-US-JennyNeural", "gender": "Female", "language": "en-US"},
            {"name": "en-US-GuyNeural", "gender": "Male", "language": "en-US"},
            {"name": "en-US-AndrewNeural", "gender": "Male", "language": "en-US"},
            {"name": "en-US-EmmaNeural", "gender": "Female", "language": "en-US"},
            {"name": "en-US-BrianNeural", "gender": "Male", "language": "en-US"},
            {"name": "en-US-EricNeural", "gender": "Male", "language": "en-US"},
            {"name": "en-GB-SoniaNeural", "gender": "Female", "language": "en-GB"},
            {"name": "en-GB-ThomasNeural", "gender": "Male", "language": "en-GB"},
            {"name": "en-AU-NatashaNeural", "gender": "Female", "language": "en-AU"},
        ]
        
        if language and language != 'all':
            azure_voices = [v for v in azure_voices if v['language'] == language]
        
        return azure_voices
    
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
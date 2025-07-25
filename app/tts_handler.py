# tts_handler.py

import edge_tts
import asyncio
import tempfile
import subprocess
import os
import wave
import base64
from pathlib import Path

from utils import DETAILED_ERROR_LOGGING
from config import DEFAULT_CONFIGS

# Backend configuration
DEFAULT_BACKEND = os.getenv('DEFAULT_BACKEND', DEFAULT_CONFIGS["DEFAULT_BACKEND"])
AZURE_SPEECH_KEY = os.getenv('AZURE_SPEECH_KEY', DEFAULT_CONFIGS["AZURE_SPEECH_KEY"])
AZURE_SPEECH_REGION = os.getenv('AZURE_SPEECH_REGION', DEFAULT_CONFIGS["AZURE_SPEECH_REGION"])
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', DEFAULT_CONFIGS["GEMINI_API_KEY"])

# Language default (environment variable)
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', DEFAULT_CONFIGS["DEFAULT_LANGUAGE"])

# Import backend-specific libraries conditionally
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    if DETAILED_ERROR_LOGGING:
        print("Azure Speech SDK not available. Install with: pip install azure-cognitiveservices-speech")

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    if DETAILED_ERROR_LOGGING:
        print("Google GenAI not available. Install with: pip install google-genai")

# OpenAI voice names mapped to edge-tts equivalents
voice_mapping = {
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

# Azure voice mapping (OpenAI -> Azure voice names)
azure_voice_mapping = {
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

# Gemini voice mapping (OpenAI -> Gemini voice names)
gemini_voice_mapping = {
    'alloy': 'Kore',
    'ash': 'Charon',
    'ballad': 'Aoede',
    'coral': 'Fenrir',
    'echo': 'Kore',
    'fable': 'Aoede', 
    'nova': 'Kore',
    'onyx': 'Charon',
    'sage': 'Aoede',
    'shimmer': 'Kore',
    'verse': 'Charon',
}

model_data = [
        {"id": "tts-1", "name": "Text-to-speech v1"},
        {"id": "tts-1-hd", "name": "Text-to-speech v1 HD"},
        {"id": "gpt-4o-mini-tts", "name": "GPT-4o mini TTS"}
    ]

def is_ffmpeg_installed():
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def write_wave_file(filename, pcm_data, channels=1, rate=24000, sample_width=2):
    """Write PCM data to a WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)

# Backend-specific generation functions
async def _generate_audio_stream_edgetts(text, voice, speed):
    """Generate streaming TTS audio using edge-tts."""
    # Determine if the voice is an OpenAI-compatible voice or a direct edge-tts voice
    edge_tts_voice = voice_mapping.get(voice, voice)  # Use mapping if in OpenAI names, otherwise use as-is
    
    # Convert speed to SSML rate format
    try:
        speed_rate = speed_to_rate(speed)  # Convert speed value to "+X%" or "-X%"
    except Exception as e:
        print(f"Error converting speed: {e}. Defaulting to +0%.")
        speed_rate = "+0%"
    
    # Create the communicator for streaming
    communicator = edge_tts.Communicate(text=text, voice=edge_tts_voice, rate=speed_rate)
    
    # Stream the audio data
    async for chunk in communicator.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]

async def _generate_audio_edgetts(text, voice, response_format, speed):
    """Generate TTS audio using edge-tts and optionally convert to a different format."""
    # Determine if the voice is an OpenAI-compatible voice or a direct edge-tts voice
    edge_tts_voice = voice_mapping.get(voice, voice)  # Use mapping if in OpenAI names, otherwise use as-is

    # Generate the TTS output in mp3 format first
    temp_mp3_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_mp3_path = temp_mp3_file_obj.name

    # Convert speed to SSML rate format
    try:
        speed_rate = speed_to_rate(speed)  # Convert speed value to "+X%" or "-X%"
    except Exception as e:
        print(f"Error converting speed: {e}. Defaulting to +0%.")
        speed_rate = "+0%"

    # Generate the MP3 file
    communicator = edge_tts.Communicate(text=text, voice=edge_tts_voice, rate=speed_rate)
    await communicator.save(temp_mp3_path)
    temp_mp3_file_obj.close() # Explicitly close our file object for the initial mp3

    # If the requested format is mp3, return the generated file directly
    if response_format == "mp3":
        return temp_mp3_path

    # Check if FFmpeg is installed
    if not is_ffmpeg_installed():
        print("FFmpeg is not available. Returning unmodified mp3 file.")
        return temp_mp3_path # Return the original mp3 path, it won't be cleaned by this function

    # Create a new temporary file for the converted output
    converted_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=f".{response_format}")
    converted_path = converted_file_obj.name
    converted_file_obj.close() # Close file object, ffmpeg will write to the path

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
        Path(converted_path).unlink(missing_ok=True)
        # Clean up the original mp3 file as well, since conversion failed
        Path(temp_mp3_path).unlink(missing_ok=True)
        
        if DETAILED_ERROR_LOGGING:
            error_message = f"FFmpeg error during audio conversion. Command: '{' '.join(e.cmd)}'. Stderr: {e.stderr.decode('utf-8', 'ignore')}"
            print(error_message) # Log for server-side diagnosis
        else:
            error_message = f"FFmpeg error during audio conversion: {e}"
            print(error_message) # Log a simpler message
        raise RuntimeError(f"FFmpeg error during audio conversion: {e}") # The raised error will still have details via e

    # Clean up the original temporary file (original mp3) as it's now converted
    Path(temp_mp3_path).unlink(missing_ok=True)

    return converted_path

async def _generate_audio_azuretts(text, voice, response_format, speed):
    """Generate TTS audio using Azure Cognitive Services Speech."""
    if not AZURE_AVAILABLE:
        raise RuntimeError("Azure Speech SDK not available. Install with: pip install azure-cognitiveservices-speech")
    
    if not AZURE_SPEECH_KEY:
        raise RuntimeError("Azure Speech Key not configured. Set AZURE_SPEECH_KEY environment variable.")
    
    # Map OpenAI voice to Azure voice
    azure_voice = azure_voice_mapping.get(voice, voice)
    
    # Create speech config
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
    speech_config.speech_synthesis_voice_name = azure_voice
    
    # Adjust speech rate for speed
    rate_percentage = int((speed - 1) * 100)
    ssml_text = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="{azure_voice}">
            <prosody rate="{rate_percentage:+d}%">{text}</prosody>
        </voice>
    </speak>'''
    
    # Create synthesizer
    temp_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_path = temp_file_obj.name
    temp_file_obj.close()
    
    audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    # Synthesize speech
    result = synthesizer.speak_ssml_async(ssml_text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # Convert to requested format if needed
        if response_format == "wav":
            return temp_path
        else:
            # Use FFmpeg to convert
            return await _convert_audio_format(temp_path, response_format)
    else:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise RuntimeError(f"Azure TTS failed: {result.reason}")

async def _generate_audio_gemini(text, voice, response_format, speed):
    """Generate TTS audio using Google Gemini."""
    if not GEMINI_AVAILABLE:
        raise RuntimeError("Google GenAI not available. Install with: pip install google-genai")
    
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API Key not configured. Set GEMINI_API_KEY environment variable.")
    
    # Map OpenAI voice to Gemini voice  
    gemini_voice = gemini_voice_mapping.get(voice, 'Kore')
    
    # Note: Gemini doesn't support speed adjustment in the same way
    # We'll ignore the speed parameter for now
    if speed != 1.0 and DETAILED_ERROR_LOGGING:
        print(f"Warning: Gemini TTS doesn't support speed adjustment. Ignoring speed={speed}")
    
    try:
        # Initialize Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Generate audio
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=gemini_voice,
                        )
                    )
                ),
            )
        )
        
        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        
        # Create temporary WAV file
        temp_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file_obj.name
        temp_file_obj.close()
        
        # Write WAV file (Gemini returns PCM data at 24kHz, 16-bit)
        write_wave_file(temp_path, audio_data, channels=1, rate=24000, sample_width=2)
        
        # Convert to requested format if needed
        if response_format == "wav":
            return temp_path
        else:
            return await _convert_audio_format(temp_path, response_format)
            
    except Exception as e:
        raise RuntimeError(f"Gemini TTS failed: {str(e)}")

async def _convert_audio_format(input_path, target_format):
    """Convert audio file to target format using FFmpeg."""
    if not is_ffmpeg_installed():
        print("FFmpeg is not available. Returning original file.")
        return input_path
    
    # Create output file
    converted_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=f".{target_format}")
    converted_path = converted_file_obj.name
    converted_file_obj.close()
    
    # Build FFmpeg command
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
    ]
    
    if target_format != "wav":
        ffmpeg_command.extend(["-b:a", "192k"])
        
    ffmpeg_command.extend([
        "-f", {
            "aac": "mp4",
            "mp3": "mp3",
            "wav": "wav", 
            "opus": "ogg",
            "flac": "flac"
        }.get(target_format, target_format),
        "-y",
        converted_path
    ])
    
    try:
        subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # Clean up original file
        Path(input_path).unlink(missing_ok=True)
        return converted_path
    except subprocess.CalledProcessError as e:
        # Clean up files on error
        Path(converted_path).unlink(missing_ok=True)
        Path(input_path).unlink(missing_ok=True)
        raise RuntimeError(f"FFmpeg conversion failed: {e}")

# Main interface functions (backwards compatible)
async def _generate_audio_stream(text, voice, speed, backend=None):
    """Generate streaming TTS audio using specified backend."""
    backend = backend or DEFAULT_BACKEND
    
    if backend == 'edgetts':
        async for chunk in _generate_audio_stream_edgetts(text, voice, speed):
            yield chunk
    else:
        # For now, only edge-tts supports streaming
        raise RuntimeError(f"Streaming not supported for backend: {backend}")

def generate_speech_stream(text, voice, speed=1.0, backend=None):
    """Generate streaming speech audio (synchronous wrapper)."""
    return asyncio.run(_generate_audio_stream(text, voice, speed, backend))

async def _generate_audio(text, voice, response_format, speed, backend=None):
    """Generate TTS audio using specified backend."""
    backend = backend or DEFAULT_BACKEND
    
    if backend == 'edgetts':
        return await _generate_audio_edgetts(text, voice, response_format, speed)
    elif backend == 'azuretts':
        return await _generate_audio_azuretts(text, voice, response_format, speed)
    elif backend == 'gemini':
        return await _generate_audio_gemini(text, voice, response_format, speed)
    else:
        raise RuntimeError(f"Unknown TTS backend: {backend}")

def generate_speech(text, voice, response_format, speed=1.0, backend=None):
    """Generate speech audio (synchronous wrapper)."""
    return asyncio.run(_generate_audio(text, voice, response_format, speed, backend))

def get_models():
    return model_data

def get_models_formatted():
    return [{ "id": x["id"] } for x in model_data]

def get_voices_formatted():
    return [{ "id": k, "name": v } for k, v in voice_mapping.items()]

async def _get_voices(language=None):
    # List all voices, filter by language if specified
    all_voices = await edge_tts.list_voices()
    language = language or DEFAULT_LANGUAGE  # Use default if no language specified
    filtered_voices = [
        {"name": v['ShortName'], "gender": v['Gender'], "language": v['Locale']}
        for v in all_voices if language == 'all' or language is None or v['Locale'] == language
    ]
    return filtered_voices

def get_voices(language=None):
    return asyncio.run(_get_voices(language))

def speed_to_rate(speed: float) -> str:
    """
    Converts a multiplicative speed value to the edge-tts "rate" format.
    
    Args:
        speed (float): The multiplicative speed value (e.g., 1.5 for +50%, 0.5 for -50%).
    
    Returns:
        str: The formatted "rate" string (e.g., "+50%" or "-50%").
    """
    if speed < 0 or speed > 2:
        raise ValueError("Speed must be between 0 and 2 (inclusive).")

    # Convert speed to percentage change
    percentage_change = (speed - 1) * 100

    # Format with a leading "+" or "-" as required
    return f"{percentage_change:+.0f}%"

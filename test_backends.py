#!/usr/bin/env python3
"""
Test script for multi-backend TTS functionality.
This script demonstrates how to use different TTS backends.
"""

import requests
import json
import os

def test_backend(backend, text="Hello world!", voice="alloy"):
    """Test a specific TTS backend."""
    url = "http://localhost:5050/v1/audio/speech"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your_api_key_here"
    }
    
    data = {
        "input": text,
        "voice": voice,
        "backend": backend,
        "response_format": "mp3"
    }
    
    print(f"\n🔄 Testing {backend.upper()} backend...")
    print(f"   Text: '{text}'")
    print(f"   Voice: {voice}")
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            filename = f"test_{backend}.mp3"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ Success! Audio saved to {filename}")
            print(f"   📊 File size: {len(response.content)} bytes")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection error - is the server running on {url}?")
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout - {backend} might be slow or misconfigured")
    except Exception as e:
        print(f"   ❌ Unexpected error: {str(e)}")

def check_server_status():
    """Check if the server is running."""
    try:
        response = requests.get("http://localhost:5050/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and responding")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except:
        print("❌ Server is not running or not accessible")
        print("   Start the server with: python3 app/server.py")
        return False

def main():
    print("🎵 Multi-Backend TTS Test Script")
    print("=" * 50)
    
    # Check server status
    if not check_server_status():
        return
    
    # Test each backend
    backends = [
        ("edgetts", "Hello from Microsoft EdgeTTS!"),
        ("azuretts", "Hello from Azure Cognitive Services!"), 
        ("gemini", "Hello from Google Gemini!")
    ]
    
    for backend, text in backends:
        test_backend(backend, text)
    
    print("\n" + "=" * 50)
    print("🎉 Testing complete!")
    print("\nNotes:")
    print("- EdgeTTS should work without additional setup")
    print("- Azure TTS requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION")
    print("- Gemini TTS requires GEMINI_API_KEY")
    print("- Check your .env file for backend-specific configuration")

if __name__ == "__main__":
    main()
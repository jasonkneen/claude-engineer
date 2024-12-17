import base64
import io
from gtts import gTTS
import asyncio
from typing import Optional

class VoiceTool:
    """Tool for handling text-to-speech conversion."""
    
    def __init__(self):
        """Initialize the voice tool."""
        self.language = 'en'
        self.tld = 'com'  # Top level domain for the Google TTS service
        
    async def text_to_speech(self, text: str) -> Optional[str]:
        """
        Convert text to speech and return base64 encoded audio data.
        
        Args:
            text: The text to convert to speech
            
        Returns:
            Base64 encoded audio data or None if conversion fails
        """
        try:
            # Run TTS in a thread pool to avoid blocking
            audio_data = await asyncio.get_event_loop().run_in_executor(
                None, self._generate_audio, text
            )
            return audio_data
        except Exception as e:
            print(f"Error converting text to speech: {str(e)}")
            return None
            
    def _generate_audio(self, text: str) -> str:
        """
        Generate audio data from text.
        
        Args:
            text: Text to convert
            
        Returns:
            Base64 encoded audio data
        """
        # Create an in-memory bytes buffer
        audio_buffer = io.BytesIO()
        
        # Generate TTS audio
        tts = gTTS(text=text, lang=self.language, tld=self.tld)
        tts.write_to_fp(audio_buffer)
        
        # Get the audio data and encode as base64
        audio_buffer.seek(0)
        audio_data = base64.b64encode(audio_buffer.read()).decode('utf-8')
        
        return audio_data
from .base import BaseTool
from enum import Enum
from typing import Dict, Any, Optional
import pyttsx3
import whisper
import sounddevice as sd
import numpy as np
import queue
import threading
import logging
import time
import os

class VoiceRole(Enum):
    TTS = "text_to_speech"
    STT = "speech_to_text"
    VOICE_CONTROL = "voice_control"

class VoiceTool(BaseTool):
    """Tool for handling voice interactions using PyTTSx3 and Whisper."""

    def __init__(self, agent_id: str, role: VoiceRole, name: Optional[str] = None):
        """Initialize voice tool with specified role.

        Args:
            agent_id: Unique identifier for this voice tool instance
            role: Role defining primary function (TTS, STT, or control)
            name: Optional display name for the voice tool
        """
        super().__init__(name=name or f"voice_{agent_id}")
        self.agent_id = agent_id
        self.role = role
        self.tts_engine = None
        self.stt_model = None
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = np.float32
        self.audio_queue = queue.Queue()
        self.recording = False
        self.record_thread = None
        self.logger = logging.getLogger(__name__)

    @property
    def description(self) -> str:
        """Get the tool description."""
        return f"""
        Voice interaction tool supporting:
        - Text-to-Speech using PyTTSx3
        - Speech-to-Text using Whisper
        - Voice control capabilities
        Current role: {self.role.value}
        """

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["speak", "listen", "transcribe", "toggle_listening"],
                    "description": "Voice action to perform"
                },
                "text": {
                    "type": "string",
                    "description": "Text to speak for TTS"
                },
                "duration": {
                    "type": "number",
                    "description": "Recording duration in seconds"
                }
            },
            "required": ["action"]
        }

    async def initialize_tts(self):
        """Initialize TTS engine asynchronously."""
        try:
            if not self.tts_engine:
                self.logger.info("Initializing TTS engine...")
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)  # Set initial volume to 0.8
                self.logger.info("TTS engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS engine: {str(e)}")
            raise RuntimeError(f"TTS initialization failed: {str(e)}")

    async def initialize_stt(self, model_size: str = "base"):
        """Initialize STT model."""
        try:
            if not self.stt_model:
                self.stt_model = whisper.load_model(model_size)
        except Exception as e:
            self.logger.error(f"Failed to initialize STT model: {str(e)}")
            raise RuntimeError(f"STT initialization failed: {str(e)}")

    async def speak(self, text: str) -> str:
        """Speak text using TTS engine and return audio file path."""
        await self.initialize_tts()
        audio_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static', 'audio'))
        os.makedirs(audio_dir, exist_ok=True)
        audio_path = os.path.join(audio_dir, f"{self.agent_id}_{int(time.time())}.wav")
        self.logger.info(f"Saving audio to: {audio_path}")
        self.tts_engine.save_to_file(text, audio_path)
        self.tts_engine.runAndWait()
        if not os.path.exists(audio_path):
            self.logger.error(f"Failed to create audio file at: {audio_path}")
            raise RuntimeError(f"Failed to create audio file at: {audio_path}")
        self.logger.info(f"Successfully created audio file at: {audio_path}")
        return audio_path

    async def transcribe(self, audio_file: str) -> str:
        """Transcribe audio file to text."""
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

        await self.initialize_stt()
        try:
            result = self.stt_model.transcribe(audio_file)
            return result["text"]
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    async def set_voice(self, voice_id: Optional[str] = None):
        """Set voice ID and return list of available voices."""
        await self.initialize_tts()
        voices = self.tts_engine.getProperty('voices')
        if voice_id:
            self.tts_engine.setProperty('voice', voice_id)
        return [voice.id for voice in voices]

    async def set_rate(self, rate: int = 150):
        """Set speech rate."""
        await self.initialize_tts()
        self.tts_engine.setProperty('rate', rate)

    async def set_volume(self, volume: float = 0.9):
        """Set speech volume."""
        await self.initialize_tts()
        self.tts_engine.setProperty('volume', volume)

    async def _speak(self, text: str) -> str:
        """Internal method to speak text."""
        try:
            await self.initialize_tts()
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            return f"Successfully spoke: {text}"
        except Exception as e:
            self.logger.error(f"TTS error: {str(e)}")
            return f"TTS error: {str(e)}"

    async def _listen(self, duration: float) -> str:
        """Internal method to listen and transcribe audio."""
        try:
            await self.initialize_stt()
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype
            )
            sd.wait()
            audio_data = (recording * 32767).astype(np.int16)
            result = self.stt_model.transcribe(audio_data)
            return result["text"].strip()
        except Exception as e:
            self.logger.error(f"STT error: {str(e)}")
            return f"STT error: {str(e)}"

    def _toggle_listening(self) -> str:
        if self.recording:
            self.recording = False
            if self.record_thread:
                self.record_thread.join()
            return "Stopped listening"

        self.recording = True
        self.record_thread = threading.Thread(target=self._continuous_listen)
        self.record_thread.start()
        return "Started listening"

    def _continuous_listen(self):
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback
            ):
                while self.recording:
                    time.sleep(0.1)
        except Exception as e:
            self.logger.error(f"Continuous listening error: {str(e)}")
            self.recording = False

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            self.logger.warning(f"Audio callback status: {status}")
        self.audio_queue.put(indata.copy())

    def close(self):
        self.recording = False
        if self.record_thread:
            self.record_thread.join()
        self.tts_engine.stop()

    async def execute(self, **kwargs) -> str:
        """Execute voice actions."""
        action = kwargs.get("action")

        try:
            if action == "speak":
                text = kwargs.get("text")
                if not text:
                    return "No text provided for speaking"
                return await self._speak(text)

            elif action == "listen":
                duration = kwargs.get("duration", 5.0)  # Default 5 seconds
                return await self._listen(duration)

            elif action == "transcribe":
                audio_file = kwargs.get("audio_file")
                if not audio_file:
                    return "No audio file provided for transcription"
                return await self.transcribe(audio_file)

            elif action == "toggle_listening":
                return self._toggle_listening()

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error executing voice action: {str(e)}")
            return f"Error executing voice action: {str(e)}"

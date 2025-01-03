from tools.base import BaseTool
import asyncio
import json
import logging
import aiowebrtc
from typing import Dict, Optional
import openai

class RealtimeVoiceTool(BaseTool):
    name = "realtimevoicetool"
    description = '''
    Manages real-time voice conversations using OpenAI's API and WebRTC.
    Handles audio streaming, voice session management, and turn-taking.
    Supports both single and multi-agent voice conversations.
    Provides real-time audio processing and agent state management.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Unique identifier for the voice session"},
            "agent_role": {"type": "string", "description": "Role/instructions for the AI agent"},
            "audio_settings": {
                "type": "object",
                "properties": {
                    "sample_rate": {"type": "integer", "default": 16000},
                    "channels": {"type": "integer", "default": 1},
                    "chunk_size": {"type": "integer", "default": 1024}
                }
            },
            "webrtc_config": {
                "type": "object",
                "properties": {
                    "ice_servers": {"type": "array", "items": {"type": "string"}},
                    "connection_timeout": {"type": "integer", "default": 30}
                }
            }
        },
        "required": ["session_id"]
    }

    def __init__(self):
        super().__init__()
        self.active_sessions: Dict[str, dict] = {}
        self.peer_connections = {}
        self.audio_processors = {}
        self.logger = logging.getLogger(__name__)

    async def _init_webrtc(self, session_id: str, config: dict) -> None:
        pc = aiowebrtc.RTCPeerConnection(configuration=config)
        self.peer_connections[session_id] = pc
        
        @pc.on("track")
        async def on_track(track):
            if track.kind == "audio":
                self.audio_processors[session_id] = await self._create_audio_processor(track)

    async def _create_audio_processor(self, track) -> None:
        processor = openai.Audio()
        return processor

    async def start_session(self, session_id: str, config: dict) -> None:
        if session_id in self.active_sessions:
            raise ValueError(f"Session {session_id} already exists")
        
        self.active_sessions[session_id] = {
            "status": "initializing",
            "config": config,
            "start_time": asyncio.get_event_loop().time()
        }
        
        await self._init_webrtc(session_id, config.get("webrtc_config", {}))
        self.active_sessions[session_id]["status"] = "active"

    async def stop_session(self, session_id: str) -> None:
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        if session_id in self.peer_connections:
            await self.peer_connections[session_id].close()
            del self.peer_connections[session_id]
        
        if session_id in self.audio_processors:
            del self.audio_processors[session_id]
        
        del self.active_sessions[session_id]

    async def process_audio(self, session_id: str, audio_data: bytes) -> str:
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        try:
            processor = self.audio_processors.get(session_id)
            if not processor:
                raise ValueError("Audio processor not initialized")
            
            response = await processor.transcribe(audio_data)
            return response.text
        except Exception as e:
            self.logger.error(f"Error processing audio: {str(e)}")
            raise

    def execute(self, **kwargs) -> str:
        session_id = kwargs.get("session_id")
        if not session_id:
            raise ValueError("session_id is required")

        try:
            loop = asyncio.get_event_loop()
            if kwargs.get("action") == "start":
                loop.run_until_complete(self.start_session(session_id, kwargs))
                return json.dumps({"status": "success", "message": "Session started"})
            
            elif kwargs.get("action") == "stop":
                loop.run_until_complete(self.stop_session(session_id))
                return json.dumps({"status": "success", "message": "Session stopped"})
            
            elif kwargs.get("action") == "process":
                audio_data = kwargs.get("audio_data")
                if not audio_data:
                    raise ValueError("audio_data is required for processing")
                result = loop.run_until_complete(self.process_audio(session_id, audio_data))
                return json.dumps({"status": "success", "result": result})
            
            else:
                raise ValueError("Invalid action specified")

        except Exception as e:
            self.logger.error(f"Error in execute: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})

    def get_session_status(self, session_id: str) -> Optional[dict]:
        return self.active_sessions.get(session_id)
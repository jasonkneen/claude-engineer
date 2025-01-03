import asyncio
from typing import Dict, Any, AsyncGenerator, Optional
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from dataclasses import dataclass
import time
import logging
from enum import Enum

class ConnectionState(Enum):
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    RECONNECTING = 'reconnecting'
    FAILED = 'failed'

@dataclass
class ConnectionConfig:
    max_retries: int = 5
    retry_delay: int = 1000  # milliseconds
    health_check_interval: int = 30  # seconds
    connection_timeout: int = 5000  # milliseconds

class EnhancedSSETransport:
    def __init__(self, config: ConnectionConfig = ConnectionConfig()):
        self._connections: Dict[str, AsyncGenerator] = {}
        self._connection_states: Dict[str, ConnectionState] = {}
        self._retry_counts: Dict[str, int] = {}
        self._config = config
        self._message_filters: Dict[str, callable] = {}
        self._logger = logging.getLogger(__name__)
        
    async def connect(self, client_id: str, request: Request) -> EventSourceResponse:
        self._connection_states[client_id] = ConnectionState.CONNECTED
        self._retry_counts[client_id] = 0
        
        async def event_generator():
            try:
                while True:
                    if await request.is_disconnected():
                        self._connection_states[client_id] = ConnectionState.DISCONNECTED
                        await self._handle_disconnection(client_id)
                        break
                        
                    if self._connection_states[client_id] == ConnectionState.RECONNECTING:
                        await self._attempt_reconnection(client_id)
                        
                    message = await self._get_filtered_message(client_id)
                    if message:
                        yield {
                            'event': message.get('event', 'message'),
                            'data': message.get('data'),
                            'id': message.get('id', None)
                        }
                    
                    await asyncio.sleep(0.1)  # Prevent CPU spinning
                    
            finally:
                await self.disconnect(client_id)
        
        return EventSourceResponse(event_generator())
    
    async def _handle_disconnection(self, client_id: str) -> None:
        if self._retry_counts[client_id] < self._config.max_retries:
            self._connection_states[client_id] = ConnectionState.RECONNECTING
            self._retry_counts[client_id] += 1
            await asyncio.sleep(self._config.retry_delay / 1000)  # Convert to seconds
        else:
            self._connection_states[client_id] = ConnectionState.FAILED
            self._logger.error(f'Client {client_id} failed to reconnect after {self._config.max_retries} attempts')
    
    async def _attempt_reconnection(self, client_id: str) -> None:
        try:
            # Implement reconnection logic here
            # For example, re-establish WebSocket connection or recreate SSE stream
            self._connection_states[client_id] = ConnectionState.CONNECTED
            self._logger.info(f'Successfully reconnected client {client_id}')
        except Exception as e:
            self._logger.error(f'Reconnection attempt failed for client {client_id}: {str(e)}')
            await self._handle_disconnection(client_id)
    
    async def disconnect(self, client_id: str) -> None:
        if client_id in self._connections:
            del self._connections[client_id]
        if client_id in self._connection_states:
            del self._connection_states[client_id]
        if client_id in self._retry_counts:
            del self._retry_counts[client_id]
    
    def add_message_filter(self, client_id: str, filter_func: callable) -> None:
        """Add a message filter for a specific client"""
        self._message_filters[client_id] = filter_func
    
    async def _get_filtered_message(self, client_id: str) -> Optional[Dict[str, Any]]:
        message = await self._get_next_message(client_id)
        if message and client_id in self._message_filters:
            return self._message_filters[client_id](message)
        return message
    
    async def _get_next_message(self, client_id: str) -> Optional[Dict[str, Any]]:
        # Implement message queue integration here
        return None  # Placeholder
    
    def get_connection_state(self, client_id: str) -> ConnectionState:
        return self._connection_states.get(client_id, ConnectionState.DISCONNECTED)
    
    def get_retry_count(self, client_id: str) -> int:
        return self._retry_counts.get(client_id, 0)
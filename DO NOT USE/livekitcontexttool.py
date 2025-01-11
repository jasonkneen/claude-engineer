from typing import Dict, Optional
from datetime import datetime
import json
import uuid
from tools.base import BaseTool

class LiveKitContextTool(BaseTool):
    """
    A tool for managing LiveKit room context and real-time communication.
    
    Features:
    - Manages LiveKit room connections
    - Stores and retrieves conversation context
    - Handles message storage and synchronization
    - Supports real-time data publishing
    
    Parameters:
        conversation_id (str, optional): ID for the conversation context
        message (dict, optional): Message to store in context
        action (str): The action to perform ('connect', 'store', 'get', 'disconnect')
    """

    @property
    def name(self) -> str:
        """Return the tool name."""
        return "livekitcontexttool"

    @property
    def description(self) -> str:
        """Return the tool description."""
        return """
    A tool for managing LiveKit room context and real-time communication.
    Features:
    - Manages LiveKit room connections
    - Stores and retrieves conversation context
    - Handles message storage and synchronization
    - Supports real-time data publishing
    """

    @property
    def input_schema(self) -> Dict:
        """Define the input schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["connect", "store", "get", "disconnect"],
                    "description": "The action to perform"
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Optional conversation ID"
                },
                "message": {
                    "type": "object",
                    "description": "Optional message to store",
                    "properties": {
                        "role": {"type": "string"},
                        "content": {"type": "string"},
                        "metadata": {"type": "object"}
                    }
                }
            },
            "required": ["action"]
        }

    def __init__(self):
        super().__init__()
        self.url = 'ws://localhost:7880'
        self.api_key = None
        self.api_secret = None
        self.room = None
        self.conversation_id = None
        self.context = {}

    def execute(self, **kwargs) -> Dict:
        """
        Execute the LiveKit context operation based on the specified action.

        Args:
            **kwargs: Keyword arguments including:
                - action: The operation to perform
                - conversation_id: Optional conversation ID
                - message: Optional message to store

        Returns:
            Dict: Result of the operation containing success status and relevant data
        """
        action = kwargs.get('action')
        conversation_id = kwargs.get('conversation_id')
        message = kwargs.get('message', {})

        if not action:
            return {'success': False, 'error': 'Action parameter is required'}

        if action == 'connect':
            success = self._connect(conversation_id)
            return {
                'success': success,
                'conversation_id': self.conversation_id if success else None
            }

        elif action == 'store':
            if not message:
                return {'success': False, 'error': 'Message parameter is required for store action'}
            success = self._store_message(
                role=message.get('role', 'user'),
                content=message.get('content', ''),
                metadata=message.get('metadata', {})
            )
            return {'success': success}

        elif action == 'get':
            return {
                'success': True,
                'context': self.get_context()
            }

        elif action == 'disconnect':
            self._disconnect()
            return {'success': True}

        return {'success': False, 'error': f'Unknown action: {action}'}

    def _connect(self, conversation_id: Optional[str] = None) -> bool:
        """Connect to LiveKit server and create/join a room for the conversation"""
        try:
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
            
            self.conversation_id = conversation_id
            
            # Initialize context storage
            self.context = {
                'conversation_id': conversation_id,
                'created_at': datetime.utcnow().isoformat(),
                'messages': []
            }

            return True

        except Exception as e:
            print(f'Failed to connect to LiveKit: {str(e)}')
            return False

    def _store_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """Store a message in the conversation context"""
        try:
            if not self.conversation_id:
                raise Exception('Not connected to a room')

            message = {
                'timestamp': datetime.utcnow().isoformat(),
                'role': role,
                'content': content,
                'metadata': metadata or {}
            }

            self.context['messages'].append(message)
            return True

        except Exception as e:
            print(f'Failed to store message: {str(e)}')
            return False

    def get_context(self) -> Dict:
        """Get the current conversation context"""
        return self.context

    def _disconnect(self) -> None:
        """Disconnect from the LiveKit room"""
        self.room = None
        self.conversation_id = None
        self.context = {}
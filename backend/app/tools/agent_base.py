from .base import BaseTool
from typing import Dict, Any, Optional, List, Union
import asyncio
import json
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import time

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    CONTEXT = "context"
    TEST = "test"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    TASK = "task"
    CONVERSATION = "conversation"
    CUSTOM = "custom"

@dataclass
class AgentState:
    agent_id: str = None
    agent_type: str = None
    is_paused: bool = False
    current_task: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)  # Persistent data storage
    progress: float = 0.0  # Track task completion progress (0-100)
    task_history: List[Dict[str, Any]] = field(default_factory=list)  # Track completed tasks
    start_time: Optional[float] = None  # Track when agent started current task

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        return cls(**data)

class AgentBaseTool(BaseTool):
    def __init__(self, agent_id: str, name: Optional[str] = None, role: Optional[AgentRole] = None):
        """Initialize agent tool with ID and optional name."""
        super().__init__(name)
        self._agent_id = agent_id
        self._role = role or AgentRole.CUSTOM
        self._description = "Base agent tool for handling agent operations"
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=self.name,
            is_paused=False
        )
    
    async def initialize(self):
        """Async initialization method."""
        await super().initialize()
        # Additional initialization can be added here

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> AgentRole:
        return self._role

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Schema defining expected input parameters"""
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message or command for the agent"},
                "context": {"type": "object", "description": "Optional context data"},
                "task_id": {"type": "string", "description": "Optional task identifier"},
                "api_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai"],
                    "description": "API provider to use"
                }
            },
            "required": ["message"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute agent operations in a thread-safe manner.

        Args:
            message: Command or message for the agent
            context: Optional context data
            task_id: Optional task identifier
            api_provider: API provider to use (anthropic/openai)

        Returns:
            Execution result as string
        """
        async with self._lock:
            if self.state.is_paused:
                return f"Agent {self.agent_id} is currently paused"

            message = kwargs.get("message")
            context = kwargs.get("context", {})
            task_id = kwargs.get("task_id")
            api_provider = kwargs.get("api_provider", "anthropic")

            # Update state
            self.state.current_task = task_id
            self.state.context = context
            self.state.start_time = time.time() if task_id else None
            self.state.progress = 0.0 if task_id else self.state.progress

            try:
                # Execute message processing asynchronously
                if message:
                    return await self._process_message(
                        message=message,
                        context=context,
                        api_provider=api_provider
                    )
                else:
                    return await self._execute_action(**kwargs)
            except Exception as e:
                self.logger.error(f"Error executing agent {self.agent_id}: {str(e)}")
                return f"Error: {str(e)}"

    async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
        """Process message through central server.

        This method should be overridden by specific agent implementations
        to provide custom processing logic.
        """
        raise NotImplementedError("Agent implementations must override _process_message")

    async def _execute_action(self, **kwargs) -> str:
        """Execute custom agent actions.

        This method should be overridden by specific agent implementations
        to provide custom action handling.
        """
        raise NotImplementedError("Agent implementations must override _execute_action")

    async def pause(self) -> None:
        """Pause agent operations"""
        async with self._lock:
            self.state.is_paused = True

    async def resume(self) -> None:
        """Resume agent operations"""
        async with self._lock:
            self.state.is_paused = False

    async def get_state(self) -> Dict[str, Any]:
        """Get current agent state"""
        async with self._lock:
            return self.state.to_dict()

    async def update_context(self, context: Dict[str, Any]) -> None:
        """Update agent context"""
        async with self._lock:
            self.state.context = context

    async def close(self):
        """Clean up resources"""
        pass
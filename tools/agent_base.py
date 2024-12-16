import asyncio
import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict, field
from concurrent.futures import ThreadPoolExecutor
import time

class AgentRole(Enum):
    TEST = "test"
    CUSTOM = "custom"
    MANAGER = "manager"  # Role for managing other agents
    CONTEXT = "context"  # Role for context management
    VOICE = "voice"
    CHAT = "chat"
    ASSISTANT = "assistant"
    EXECUTOR = "executor"
    COORDINATOR = "coordinator"
    ORCHESTRATOR = "orchestrator"  # Role for orchestrating agent workflows
    TASK = "task"  # Role for task execution

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

class AgentBaseTool(ABC):
    """Base class for agent-based tools that supports:
    1. Predefined and custom roles
    2. State management and persistence
    3. Thread-safe operations
    4. Context management
    5. Communication through central server
    """

    def __init__(self, agent_id: str, role: Union[AgentRole, str] = AgentRole.TEST, name: Optional[str] = None):
        """Initialize agent base tool."""
        self.agent_id = agent_id
        self._paused = False
        self._lock = asyncio.Lock()

        # Set up role first
        if isinstance(role, str):
            try:
                self.role = AgentRole[role.upper()]
                self.custom_role = None
            except KeyError:
                self.role = AgentRole.CUSTOM
                self.custom_role = role.lower()
        else:
            self.role = role
            self.custom_role = None

        # Set up name after role is initialized
        role_str = self.custom_role or self.role.value.lower()
        self.name = name or f"agent_{role_str}_{agent_id}"

        # Initialize state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=self.__class__.__name__,
            is_paused=self._paused
        )

        # Set up logger
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{agent_id}")
        self.logger.setLevel(logging.DEBUG)

    async def initialize(self):
        """Async initialization method."""
        await self._setup()

    @property
    def description(self) -> str:
        """Get agent description."""
        return f"{self.name} - {self.__class__.__name__}"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get input schema for validation."""
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "context": {"type": "object"},
                "api_provider": {"type": "string"}
            },
            "required": ["message"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute agent action."""
        async with self._lock:
            if self._paused:
                return "Agent is currently paused"

            try:
                message = kwargs.get('message', '')
                context = kwargs.get('context', {})
                api_provider = kwargs.get('api_provider', '')
                return await self._process_message(message=message, context=context, api_provider=api_provider)
            except Exception as e:
                self.logger.error(f"Error executing action: {str(e)}")
                return f"Error: {str(e)}"

    async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
        """Process message through central server.

        This method should be overridden by specific agent implementations
        to provide custom processing logic.
        """
        if self.state.is_paused:
            return f"Agent {self.agent_id} is currently paused"
        return f"Processed: {message}"

    async def pause(self) -> None:
        """Pause agent operations"""
        async with self._lock:
            self._paused = True
            self.state.is_paused = True

    async def resume(self) -> None:
        """Resume agent operations"""
        async with self._lock:
            self._paused = False
            self.state.is_paused = False

    async def get_state(self) -> Dict[str, Any]:
        """Get current agent state"""
        async with self._lock:
            return self.state.to_dict()

    async def update_context(self, context: Dict[str, Any]) -> None:
        """Update agent context"""
        async with self._lock:
            self.state.context = context

    async def _setup(self) -> None:
        """Internal setup method called during initialization"""
        pass  # Override in subclasses if needed

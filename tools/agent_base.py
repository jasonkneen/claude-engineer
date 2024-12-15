from tools.base import BaseTool
from typing import Dict, Any, Optional, List
import threading
import json
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    CONTEXT = "context"
    TEST = "test"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    CUSTOM = "custom"

@dataclass
class AgentState:
    agent_id: str = None
    agent_type: str = None
    is_paused: bool = False
    current_task: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)  # Persistent data storage

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        return cls(**data)

class AgentBaseTool(BaseTool):
    """Base class for agent-based tools that supports:
    1. Predefined and custom roles
    2. State management and persistence
    3. Thread-safe operations
    4. Context management
    5. Communication through central server
    """

    def __init__(self, agent_id: str, role: AgentRole, custom_role: Optional[str] = None):
        """Initialize agent tool with ID and role.

        Args:
            agent_id: Unique identifier for the agent
            role: Predefined role from AgentRole enum
            custom_role: Custom role name if role is AgentRole.CUSTOM
        """
        self.agent_id = agent_id
        self.role = role
        self.custom_role = custom_role if role == AgentRole.CUSTOM else None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.state = AgentState(
            agent_id=agent_id,
            agent_type=role.value,
            is_paused=False,
            current_task=None,
            context={},
            data={'tests': {}} if role == AgentRole.TEST else {}  # Initialize tests dict for test agent
        )
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        """Tool name based on agent ID and role"""
        role_name = self.custom_role if self.role == AgentRole.CUSTOM else self.role.value
        return f"agent_{role_name}_{self.agent_id}"

    @property
    def description(self) -> str:
        """Detailed description of the agent's capabilities"""
        role_desc = self.custom_role if self.role == AgentRole.CUSTOM else self.role.value
        return f"""
        Agent-based tool for {role_desc} operations.
        Supports:
        - Task execution and management
        - Context awareness
        - State persistence
        - Thread-safe operations
        - Central server communication
        """

    @property
    def input_schema(self) -> Dict:
        """Schema defining expected input parameters"""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message or command for the agent"
                },
                "context": {
                    "type": "object",
                    "description": "Optional context data"
                },
                "task_id": {
                    "type": "string",
                    "description": "Optional task identifier"
                },
                "api_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai"],
                    "description": "API provider to use"
                }
            },
            "required": ["message"]
        }

    def execute(self, **kwargs) -> str:
        """Execute agent operations in a thread-safe manner.

        Args:
            message: Command or message for the agent
            context: Optional context data
            task_id: Optional task identifier
            api_provider: API provider to use (anthropic/openai)

        Returns:
            Execution result as string
        """
        with self._lock:
            if self.state.is_paused:
                return f"Agent {self.agent_id} is currently paused"

            message = kwargs.get("message")
            context = kwargs.get("context", {})
            task_id = kwargs.get("task_id")
            api_provider = kwargs.get("api_provider", "anthropic")

            # Update state
            self.state.current_task = task_id
            self.state.context = context

            try:
                # Execute directly without thread pool to maintain state
                if message:
                    return self._process_message(
                        message=message,
                        context=context,
                        api_provider=api_provider
                    )
                else:
                    return self._execute_action(**kwargs)
            except Exception as e:
                logging.error(f"Error executing agent {self.agent_id}: {str(e)}")
                return f"Error: {str(e)}"

    def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
        """Process message through central server.

        This method should be overridden by specific agent implementations
        to provide custom processing logic.
        """
        raise NotImplementedError("Agent implementations must override _process_message")

    def pause(self) -> None:
        """Pause agent operations"""
        with self._lock:
            self.state.is_paused = True

    def resume(self) -> None:
        """Resume agent operations"""
        with self._lock:
            self.state.is_paused = False

    def get_state(self) -> Dict[str, Any]:
        """Get current agent state"""
        with self._lock:
            return self.state.to_dict()

    def update_context(self, context: Dict[str, Any]) -> None:
        """Update agent context"""
        with self._lock:
            self.state.context = context

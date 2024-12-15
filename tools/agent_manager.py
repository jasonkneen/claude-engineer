from tools.base import BaseTool
from tools.agent_base import AgentBaseTool, AgentRole
from api_router import APIRouter, APIConfig
from typing import Dict, Any, Optional, List
import asyncio
import logging
import json
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class AgentConfig:
    role: AgentRole
    custom_role: Optional[str] = None
    api_provider: str = "anthropic"
    model_config: Optional[APIConfig] = None

class AgentManagerTool(BaseTool):
    """Manages agent lifecycle and communication through central server.
    Supports creating, pausing, and orchestrating agents as tools.
    """

    description = """
    Manages agent lifecycle and team assembly:
    - Creates new agents with predefined or custom roles
    - Handles agent pausing and resuming
    - Routes communication through central server
    - Maintains agent state and context
    """
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "pause", "resume", "list", "delete"],
                "description": "Action to perform"
            },
            "agent_id": {
                "type": "string",
                "description": "Target agent ID"
            },
            "role": {
                "type": "string",
                "enum": [role.value for role in AgentRole],
                "description": "Agent role"
            },
            "custom_role": {
                "type": "string",
                "description": "Custom role name if role is custom"
            },
            "api_provider": {
                "type": "string",
                "enum": ["anthropic", "openai"],
                "description": "API provider to use"
            }
        },
        "required": ["action"]
    }

    def __init__(self, name: Optional[str] = None):
        """Initialize manager with API router and agent registry"""
        super().__init__(name=name)
        self.api_router = APIRouter()
        self.agents: Dict[str, AgentBaseTool] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)

    def execute(self, **kwargs) -> str:
        """Execute agent management operations.

        Args:
            action: Management action to perform
            agent_id: Target agent ID (if applicable)
            role: Agent role for creation
            custom_role: Custom role name
            api_provider: API provider to use

        Returns:
            Operation result as string
        """
        action = kwargs.get("action")
        agent_id = kwargs.get("agent_id")

        try:
            if action == "create":
                return self._create_agent(**kwargs)
            elif action == "pause":
                return self._pause_agent(agent_id)
            elif action == "resume":
                return self._resume_agent(agent_id)
            elif action == "list":
                return self._list_agents()
            elif action == "delete":
                return self._delete_agent(agent_id)
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error in agent manager: {str(e)}")
            return f"Error: {str(e)}"

    def _create_agent(self, **kwargs) -> str:
        """Create new agent with specified configuration"""
        agent_id = kwargs.get("agent_id")
        if not agent_id:
            agent_id = f"agent_{len(self.agents) + 1}"

        if agent_id in self.agents:
            return f"Agent {agent_id} already exists"

        try:
            role = kwargs.get("role", "custom")
            custom_role = kwargs.get("custom_role")

            # Handle role validation
            if isinstance(role, str):
                # Check if it's a predefined role
                if role.upper() in [r.name for r in AgentRole]:
                    try:
                        role = AgentRole[role.upper()]
                    except (KeyError, AttributeError):
                        return f"Invalid role format: {role}"
                elif role.lower() == "custom" and custom_role:
                    role = AgentRole.CUSTOM
                else:
                    return f"Invalid role: {role}. Must be one of {[r.name for r in AgentRole]} or use role='custom' with custom_role parameter"

            config = AgentConfig(
                role=role,
                custom_role=custom_role,
                api_provider=kwargs.get("api_provider", "anthropic")
            )

            agent = AgentBaseTool(
                agent_id=agent_id,
                role=role,
                name=f"agent_{custom_role or role.name}_{agent_id}"
            )
            self.agents[agent_id] = agent

            display_role = custom_role or agent.role.name
            return f"Created agent {agent_id} with role {display_role}"

        except Exception as e:
            return f"Error creating agent: {str(e)}"

    def _pause_agent(self, agent_id: str) -> str:
        """Pause specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        self.agents[agent_id].pause()
        return f"Paused agent {agent_id}"

    def _resume_agent(self, agent_id: str) -> str:
        """Resume specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        self.agents[agent_id].resume()
        return f"Resumed agent {agent_id}"

    def _list_agents(self) -> str:
        """List all registered agents and their states"""
        if not self.agents:
            return "No agents registered"

        result = []
        for agent_id, agent in self.agents.items():
            state = agent.get_state()
            display_role = agent.custom_role or agent.role.name
            result.append(
                f"Agent: {agent_id}\n"
                f"Role: {display_role}\n"
                f"Status: {'Paused' if state['is_paused'] else 'Active'}\n"
                f"Current task: {state['current_task'] or 'None'}\n"
            )

        return "\n".join(result)

    def _delete_agent(self, agent_id: str) -> str:
        """Delete specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        agent = self.agents.pop(agent_id)
        agent.pause()  # Ensure agent stops any ongoing work
        return f"Deleted agent {agent_id}"

    async def close(self):
        """Clean up resources"""
        await self.api_router.close()
        self._executor.shutdown(wait=True)

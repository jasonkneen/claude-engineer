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

    async def setup(self):
        """Initialize the manager and its dependencies"""
        await self.api_router._setup_clients()

    def __init__(self, name: Optional[str] = None, test_mode: bool = False):
        """Initialize manager with API router and agent registry"""
        super().__init__(name=name)
        self.api_router = APIRouter(test_mode=test_mode)
        self.agents: Dict[str, AgentBaseTool] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)

    async def execute(self, **kwargs) -> str:
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
        role = kwargs.get("role")

        try:
            if action == "create":
                if not agent_id:
                    return "Error: agent_id is required"

                if not role:
                    return "Error: role is required"

                # Validate role before creating agent
                if isinstance(role, str):
                    role_upper = role.upper()
                    if role_upper != "SPECIALIZED" and role_upper not in AgentRole.__members__:
                        return f"Invalid role: {role}"

                try:
                    await self._create_agent(**kwargs)
                    return f"Created agent {agent_id}"
                except ValueError as e:
                    return f"Invalid role: {str(e)}"

            elif action == "pause":
                return await self._pause_agent(agent_id)
            elif action == "resume":
                return await self._resume_agent(agent_id)
            elif action == "list":
                return await self._list_agents()
            elif action == "delete":
                return await self._delete_agent(agent_id)
            else:
                return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error in agent manager: {str(e)}")
            return f"Error: {str(e)}"

    async def _create_agent(self, **kwargs) -> str:
        """Create new agent with specified configuration"""
        agent_id = kwargs.get("agent_id")
        if not agent_id:
            agent_id = f"agent_{len(self.agents) + 1}"

        if agent_id in self.agents:
            return f"Agent {agent_id} already exists"

        try:
            role = kwargs.get("role", "CUSTOM")
            custom_role = kwargs.get("custom_role")

            # Handle role validation and conversion
            if isinstance(role, str):
                role_upper = role.upper()

                # Special handling for specialized role
                if role_upper == "SPECIALIZED":
                    role = AgentRole.CUSTOM
                    custom_role = "specialized"
                elif role_upper in AgentRole.__members__:
                    role = AgentRole[role_upper]
                    custom_role = None
                else:
                    raise ValueError(f"Invalid role: {role}")

            if not isinstance(role, AgentRole):
                raise ValueError(f"Invalid role type: {type(role)}")

            # Create agent instance with proper initialization
            agent = AgentBaseTool(
                agent_id=agent_id,
                role=role,
                custom_role=custom_role,
                name=f"agent_{custom_role or role.name}_{agent_id}"
            )
            await agent.initialize()
            self.agents[agent_id] = agent
            return f"Created agent {agent_id}"

        except Exception as e:
            raise ValueError(str(e))

    async def _pause_agent(self, agent_id: str) -> str:
        """Pause agent operations"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"
        await self.agents[agent_id].pause()
        return f"Paused agent {agent_id}"

    async def _resume_agent(self, agent_id: str) -> str:
        """Resume paused agent"""
        try:
            if agent_id not in self.agents:
                return f"Agent {agent_id} not found"

            agent = self.agents[agent_id]
            await agent.resume()
            return f"Resumed agent {agent_id}"

        except Exception as e:
            self.logger.error(f"Error in agent manager: {str(e)}")
            return f"Error: {str(e)}"

    async def _list_agents(self) -> str:
        """List all registered agents"""
        if not self.agents:
            return "No agents registered"

        result = []
        for agent_id, agent in self.agents.items():
            status = "Active" if not agent.state.is_paused else "Paused"
            if agent.role == AgentRole.CUSTOM:
                role_display = agent.custom_role if agent.custom_role else "custom"
            else:
                role_display = agent.role.name
            result.append(f"Agent {agent_id} (Role: {role_display}): {status}")

        return "\n".join(result)

    async def _delete_agent(self, agent_id: str) -> str:
        """Delete specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        agent = self.agents.pop(agent_id)
        await agent.pause()  # Ensure agent stops any ongoing work
        return f"Deleted agent {agent_id}"

    async def close(self):
        """Clean up resources"""
        await self.api_router.close()
        self._executor.shutdown(wait=True)

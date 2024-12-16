from tools.base import BaseTool
from tools.agent_base import AgentBaseTool, AgentRole
from api_router import APIRouter, APIConfig
from typing import Dict, Any, Optional, List, Union
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

class AgentManagerTool(AgentBaseTool):
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
        super().__init__(agent_id="manager", name=name or "agent_manager", role=AgentRole.MANAGER)
        self.api_router = APIRouter()
        self.agents: Dict[str, AgentBaseTool] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)

    async def setup(self):
        """Async setup for manager components"""
        await self.api_router.setup()
        await self.initialize()

    async def execute(self, **kwargs) -> str:
        """Execute agent management operations."""
        try:
            action = kwargs.get("action")
            if not action:
                return "No action specified"

            if action == "create":
                agent_id = kwargs.get("agent_id")
                role = kwargs.get("role")
                if not agent_id or not role:
                    return "Missing required parameters: agent_id and role"

                # Remove agent_id from kwargs to avoid duplicate
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop("agent_id", None)
                return await self._create_agent(agent_id=agent_id, **kwargs_copy)

            elif action == "pause":
                agent_id = kwargs.get("agent_id")
                if not agent_id:
                    return "Missing required parameter: agent_id"
                return await self._pause_agent(agent_id)

            elif action == "resume":
                agent_id = kwargs.get("agent_id")
                if not agent_id:
                    return "Missing required parameter: agent_id"
                return await self._resume_agent(agent_id)

            elif action == "list":
                return await self._list_agents()

            elif action == "delete":
                agent_id = kwargs.get("agent_id")
                if not agent_id:
                    return "Missing required parameter: agent_id"
                return await self._delete_agent(agent_id)

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error in agent manager: {str(e)}")
            return f"Error: {str(e)}"

    async def _create_agent(self, agent_id: str, role: Union[str, AgentRole], **kwargs) -> str:
        """Create a new agent with specified role and configuration."""
        try:
            # Handle role conversion and validation
            if isinstance(role, str):
                # Validate role string format
                if not role or not role.strip() or not role.replace('_', '').isalnum():
                    return "Invalid role"

                role_upper = role.upper()
                if role_upper in AgentRole.__members__:
                    role = AgentRole[role_upper]
                    custom_role = None
                else:
                    # Create agent with custom role
                    custom_role = role.lower()
                    role = AgentRole.CUSTOM
            else:
                custom_role = None

            # Create agent based on role
            from tools.test_agent import TestAgentTool

            if role == AgentRole.TEST:
                agent = TestAgentTool(agent_id=agent_id)
            else:
                agent = AgentBaseTool(
                    agent_id=agent_id,
                    role=role,
                    name=kwargs.get('name'),
                    custom_role=custom_role
                )

            # Initialize agent
            await agent.initialize()

            # Register agent
            self.agents[agent_id] = agent
            self.logger.info(f"Created agent {agent_id} with role {role}")
            return f"Created agent {agent_id}"

        except Exception as e:
            self.logger.error(f"Error creating agent {agent_id}: {str(e)}")
            return f"Error creating agent: {str(e)}"

    async def _pause_agent(self, agent_id: str) -> str:
        """Pause specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        await self.agents[agent_id].pause()
        return f"Paused agent {agent_id}"

    async def _resume_agent(self, agent_id: str) -> str:
        """Resume specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        await self.agents[agent_id].resume()
        return f"Resumed agent {agent_id}"

    async def _list_agents(self) -> str:
        """List all registered agents and their states"""
        if not self.agents:
            return "No agents registered"

        result = []
        for agent_id, agent in self.agents.items():
            state = await agent.get_state()
            # Use custom_role if available, otherwise use role name
            display_role = agent.custom_role if agent.custom_role else agent.role.name
            result.append(
                f"Agent: {agent_id}\n"
                f"Role: {display_role}\n"
                f"Status: {'Paused' if state['is_paused'] else 'Active'}\n"
                f"Current task: {state['current_task'] or 'None'}\n"
            )

        return "\n".join(result)

    async def _delete_agent(self, agent_id: str) -> str:
        """Delete specified agent"""
        if agent_id not in self.agents:
            return f"Agent {agent_id} not found"

        agent = self.agents.pop(agent_id)
        await agent.pause()
        return f"Deleted agent {agent_id}"

    async def close(self):
        """Clean up resources"""
        await self.api_router.close()
        self._executor.shutdown(wait=True)

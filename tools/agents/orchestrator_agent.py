from ..agent_base import AgentBaseTool
from typing import Dict, Any, List
from enum import Enum

class OrchestratorRole(Enum):
    TASK_MANAGER = "task_manager"
    CONTEXT_COORDINATOR = "context_coordinator"

class OrchestratorAgent(AgentBaseTool):
    def __init__(self, agent_id: str, role: OrchestratorRole):
        super().__init__(
            agent_id=agent_id,
            role=role,
            name="orchestrator_agent",
            description="Manages task list, goals, and context streams between agents"
        )
        self.active_tasks = {}
        self.agent_contexts = {}
        self.paused_agents = set()

    def manage_task(self, task_id: str, status: str, agent_id: str) -> Dict[str, Any]:
        """Update task status and manage task lifecycle"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].update({
                "status": status,
                "agent_id": agent_id,
                "last_updated": "timestamp"
            })
        return self.active_tasks.get(task_id, {})

    def update_context(self, agent_id: str, context: Dict[str, Any]) -> None:
        """Update context for a specific agent"""
        if agent_id not in self.agent_contexts:
            self.agent_contexts[agent_id] = []
        self.agent_contexts[agent_id].append(context)

    def pause_agent(self, agent_id: str, reason: str) -> bool:
        """Pause an agent's execution"""
        self.paused_agents.add(agent_id)
        return True

    def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent"""
        if agent_id in self.paused_agents:
            self.paused_agents.remove(agent_id)
            return True
        return False

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get current status of an agent"""
        return {
            "agent_id": agent_id,
            "is_paused": agent_id in self.paused_agents,
            "active_tasks": [
                task for task_id, task in self.active_tasks.items()
                if task.get("agent_id") == agent_id
            ],
            "context_size": len(self.agent_contexts.get(agent_id, []))
        }

    def manage_context_streams(self) -> None:
        """Manage context streams between agents"""
        for agent_id, contexts in self.agent_contexts.items():
            if len(contexts) > 10:  # Example threshold
                # Compress or clean up old contexts
                self.agent_contexts[agent_id] = contexts[-10:]

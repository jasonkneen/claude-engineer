from tools.base import BaseTool
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class AgentManagerTool(BaseTool):
    name = "agentmanagertool"
    description = '''
    Manages MCP agent configurations, status and lifecycle.
    Supports registering, listing, updating and removing agents.
    Persists agent data across sessions using JSON storage.
    Tracks metadata including creation time, status updates, and health.
    '''
    
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["register", "list", "status", "update", "remove"]
            },
            "agent_id": {"type": "string"},
            "config": {
                "type": "object",
                "properties": {
                    "transport": {"type": "string"},
                    "connection": {"type": "object"},
                    "settings": {"type": "object"}
                }
            },
            "status": {"type": "string"}
        },
        "required": ["operation"]
    }

    def __init__(self):
        super().__init__()
        self.storage_path = Path("contexts/state/agent_data.json")
        # Ensure the state directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.agents = self._load_agents()

    def _load_agents(self) -> Dict:
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_agents(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.agents, f, indent=2)

    def _validate_config(self, config: Dict) -> bool:
        required_fields = ['transport', 'connection']
        return all(field in config for field in required_fields)

    def register_agent(self, agent_id: str, config: Dict) -> Dict:
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already exists")
        
        if not self._validate_config(config):
            raise ValueError("Invalid agent configuration")

        agent_data = {
            "id": agent_id,
            "config": config,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "health": "unknown"
        }
        
        self.agents[agent_id] = agent_data
        self._save_agents()
        return agent_data

    def list_agents(self) -> List[Dict]:
        return list(self.agents.values())

    def get_agent_status(self, agent_id: str) -> Dict:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        return self.agents[agent_id]

    def update_agent_status(self, agent_id: str, status: str) -> Dict:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        self.agents[agent_id]["status"] = status
        self.agents[agent_id]["last_updated"] = datetime.now().isoformat()
        self._save_agents()
        return self.agents[agent_id]

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        del self.agents[agent_id]
        self._save_agents()
        return True

    def execute(self, **kwargs) -> str:
        operation = kwargs.get("operation")
        agent_id = kwargs.get("agent_id")
        config = kwargs.get("config")
        status = kwargs.get("status")

        try:
            if operation == "register":
                result = self.register_agent(agent_id, config)
                return f"Agent {agent_id} registered successfully: {result}"
            
            elif operation == "list":
                agents = self.list_agents()
                return f"Active agents: {json.dumps(agents, indent=2)}"
            
            elif operation == "status":
                status = self.get_agent_status(agent_id)
                return f"Agent {agent_id} status: {status}"
            
            elif operation == "update":
                result = self.update_agent_status(agent_id, status)
                return f"Agent {agent_id} status updated: {result}"
            
            elif operation == "remove":
                self.remove_agent(agent_id)
                return f"Agent {agent_id} removed successfully"
            
            else:
                return "Invalid operation specified"

        except Exception as e:
            return f"Error: {str(e)}"
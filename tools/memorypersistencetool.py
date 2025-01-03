from tools.base import BaseTool
import json
from datetime import datetime
from pathlib import Path
import os

class MemoryPersistenceTool(BaseTool):
    name = "memorypersistencetool"
    description = '''
    Manages persistent memory storage for AI context and processing.
    Stores key-value pairs, processing history, and decision records.
    Supports hierarchical organization and timestamps.
    Can save/load state to/from JSON files.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["store", "retrieve", "save", "load", "update", "track_progress", "log_decision", "log_action"]
            },
            "key": {"type": "string"},
            "value": {"type": "object"},
            "filepath": {"type": "string"},
            "progress_status": {"type": "string"},
            "decision": {"type": "string"},
            "rationale": {"type": "string"},
            "action_details": {"type": "string"}
        },
        "required": ["action"]
    }

    def __init__(self):
        self.memory = {}
        self.progress_tracking = {}
        self.decisions = []
        self.action_history = []
        self.default_filepath = "memory_state.json"

    def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        timestamp = datetime.now().isoformat()

        if action == "store":
            key = kwargs.get("key")
            value = kwargs.get("value")
            if key and value:
                self.memory[key] = {"value": value, "timestamp": timestamp}
                return f"Stored value for key: {key}"

        elif action == "retrieve":
            key = kwargs.get("key")
            if key in self.memory:
                return str(self.memory[key])
            return f"Key not found: {key}"

        elif action == "save":
            filepath = kwargs.get("filepath", self.default_filepath)
            state = {
                "memory": self.memory,
                "progress": self.progress_tracking,
                "decisions": self.decisions,
                "actions": self.action_history,
                "last_saved": timestamp
            }
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            return f"Memory state saved to {filepath}"

        elif action == "load":
            filepath = kwargs.get("filepath", self.default_filepath)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    state = json.load(f)
                self.memory = state.get("memory", {})
                self.progress_tracking = state.get("progress", {})
                self.decisions = state.get("decisions", [])
                self.action_history = state.get("actions", [])
                return f"Memory state loaded from {filepath}"
            return f"File not found: {filepath}"

        elif action == "update":
            key = kwargs.get("key")
            value = kwargs.get("value")
            if key in self.memory and value:
                self.memory[key] = {"value": value, "timestamp": timestamp}
                return f"Updated value for key: {key}"
            return f"Key not found: {key}"

        elif action == "track_progress":
            status = kwargs.get("progress_status")
            if status:
                self.progress_tracking[timestamp] = status
                return f"Progress tracked: {status}"

        elif action == "log_decision":
            decision = kwargs.get("decision")
            rationale = kwargs.get("rationale")
            if decision and rationale:
                self.decisions.append({
                    "decision": decision,
                    "rationale": rationale,
                    "timestamp": timestamp
                })
                return f"Decision logged: {decision}"

        elif action == "log_action":
            action_details = kwargs.get("action_details")
            if action_details:
                self.action_history.append({
                    "action": action_details,
                    "timestamp": timestamp
                })
                return f"Action logged: {action_details}"

        return "Invalid action or missing parameters"
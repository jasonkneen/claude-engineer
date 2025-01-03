import json
import os
from pathlib import Path
from datetime import datetime
import tempfile
import asyncio

# Base paths for context files
CONTEXTS_PATH = "ce3/contexts"
CONTEXT_STATE_PATH = "ce3/contexts/state"

def get_state_path(filename: str) -> str:
    """Get full path for a state file"""
    return os.path.join(CONTEXT_STATE_PATH, filename)

def get_context_path(filename: str) -> str:
    """Get full path for a context file"""
    return os.path.join(CONTEXTS_PATH, filename)

def ensure_directories():
    """Ensure context directories exist"""
    os.makedirs(CONTEXTS_PATH, exist_ok=True) 
    os.makedirs(CONTEXT_STATE_PATH, exist_ok=True)

class ContextManager:
    def __init__(self):
        self.context_baton_path = get_state_path("context_baton.json")
        self.status_path = get_state_path("STATUS.json")
        self.agent_data_path = get_state_path("agent_data.json")
        ensure_directories()

    def save_context(self, context: dict, name: str = None):
        """Save context to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name is None:
            context_path = get_context_path(f"context_full_{timestamp}.json")
        else:
            context_path = get_context_path(f"context_{name}_{timestamp}.json")

        with open(context_path, 'w') as f:
            json.dump(context, f, indent=2)

        return context_path

    def load_context(self, context_path: str = None):
        """Load context from a file"""
        if context_path is None:
            # Find most recent context file
            context_files = sorted(
                Path(CONTEXTS_PATH).glob("context_full_*.json"), 
                key=os.path.getctime,
                reverse=True
            )
            if not context_files:
                return None
            context_path = str(context_files[0])

        with open(context_path) as f:
            return json.load(f)


from tools.base import BaseTool
import json
from enum import Enum
from typing import Dict, List
from datetime import datetime
import os

class TaskStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class TaskTrackerTool(BaseTool):
    name = "tasktrackertool"
    description = '''
    Task tracking and management tool that supports:
    - Creating and managing tasks with status tracking
    - Task dependencies and progress monitoring
    - Persistent storage using JSON
    - Category-based task organization
    - Position/focus tracking in processes
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "list", "load", "save", "get_focus"]
            },
            "task_id": {"type": "string"},
            "description": {"type": "string"},
            "category": {"type": "string"},
            "status": {"type": "string"},
            "progress": {"type": "number"},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "current_focus": {"type": "string"}
        },
        "required": ["action"]
    }

    def __init__(self):
        self.tasks = {}
        self.current_focus = None
        self.storage_file = "tasks.json"

    def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        
        if action == "create":
            return self._create_task(**kwargs)
        elif action == "update":
            return self._update_task(**kwargs)
        elif action == "list":
            return self._list_tasks(kwargs.get("category"))
        elif action == "save":
            return self._save_tasks()
        elif action == "load":
            return self._load_tasks()
        elif action == "get_focus":
            return self._get_focus()
        else:
            return "Invalid action specified"

    def _create_task(self, **kwargs) -> str:
        task_id = kwargs.get("task_id", str(len(self.tasks) + 1))
        task = {
            "description": kwargs.get("description", ""),
            "status": TaskStatus.NOT_STARTED.value,
            "progress": 0,
            "category": kwargs.get("category", "default"),
            "dependencies": kwargs.get("dependencies", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.tasks[task_id] = task
        return f"Task {task_id} created successfully"

    def _update_task(self, **kwargs) -> str:
        task_id = kwargs.get("task_id")
        if not task_id or task_id not in self.tasks:
            return "Invalid task ID"

        task = self.tasks[task_id]
        if "status" in kwargs:
            task["status"] = kwargs["status"]
        if "progress" in kwargs:
            task["progress"] = kwargs["progress"]
        if "description" in kwargs:
            task["description"] = kwargs["description"]
        if "category" in kwargs:
            task["category"] = kwargs["category"]
        if "dependencies" in kwargs:
            task["dependencies"] = kwargs["dependencies"]
        
        task["updated_at"] = datetime.now().isoformat()
        return f"Task {task_id} updated successfully"

    def _list_tasks(self, category=None) -> str:
        output = []
        for task_id, task in self.tasks.items():
            if category and task["category"] != category:
                continue
            output.append(f"Task {task_id}:")
            for key, value in task.items():
                output.append(f"  {key}: {value}")
            output.append("")
        return "\n".join(output) if output else "No tasks found"

    def _save_tasks(self) -> str:
        try:
            with open(self.storage_file, 'w') as f:
                json.dump({
                    "tasks": self.tasks,
                    "current_focus": self.current_focus
                }, f, indent=2)
            return "Tasks saved successfully"
        except Exception as e:
            return f"Error saving tasks: {str(e)}"

    def _load_tasks(self) -> str:
        try:
            if not os.path.exists(self.storage_file):
                return "No saved tasks found"
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                self.tasks = data.get("tasks", {})
                self.current_focus = data.get("current_focus")
            return "Tasks loaded successfully"
        except Exception as e:
            return f"Error loading tasks: {str(e)}"

    def _get_focus(self) -> str:
        return f"Current focus: {self.current_focus}" if self.current_focus else "No current focus set"
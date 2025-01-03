from tools.base import BaseTool
from typing import Dict, List, Optional
import re
import json
from dataclasses import dataclass
from threading import Lock

@dataclass
class ToolContext:
    tool_use_id: str
    tool_name: str
    tool_args: dict
    tool_result: Optional[str] = None
    is_complete: bool = False

class ContextManagerTool(BaseTool):
    name = "contextmanagertool"
    description = '''
    Manages and validates tool usage context in conversations.
    - Validates tool use/result pairing
    - Maintains conversation history integrity
    - Prevents 400 errors related to tool_result blocks
    - Handles history compression
    - Ensures proper tool interaction sequencing
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["validate", "cleanup", "reset", "compress"]
            },
            "conversation_history": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["action", "conversation_history"]
    }

    def __init__(self):
        self.context_lock = Lock()
        self.active_contexts: Dict[str, ToolContext] = {}
        self.tool_pattern = re.compile(r'<tool_use>(.*?)</tool_use>')
        self.result_pattern = re.compile(r'<tool_result>(.*?)</tool_result>')

    def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        history = kwargs.get("conversation_history", [])

        if action == "validate":
            return self._validate_context(history)
        elif action == "cleanup":
            return self._cleanup_history(history)
        elif action == "reset":
            return self._reset_context()
        elif action == "compress":
            return self._compress_history(history)
        
        return "Invalid action specified"

    def _validate_context(self, history: List[str]) -> str:
        with self.context_lock:
            tool_uses = []
            tool_results = []
            
            for message in history:
                tool_matches = self.tool_pattern.findall(message)
                result_matches = self.result_pattern.findall(message)
                
                tool_uses.extend(tool_matches)
                tool_results.extend(result_matches)

            if len(tool_uses) != len(tool_results):
                return "Context validation failed: Mismatched tool use and result pairs"

            for use, result in zip(tool_uses, tool_results):
                try:
                    use_data = json.loads(use)
                    context = ToolContext(
                        tool_use_id=use_data.get("id", ""),
                        tool_name=use_data.get("name", ""),
                        tool_args=use_data.get("args", {}),
                        tool_result=result,
                        is_complete=True
                    )
                    self.active_contexts[context.tool_use_id] = context
                except json.JSONDecodeError:
                    return f"Context validation failed: Invalid tool use format"

            return "Context validation successful"

    def _cleanup_history(self, history: List[str]) -> str:
        cleaned_history = []
        for message in history:
            # Remove any incomplete tool blocks
            message = re.sub(r'<tool_use>(?:(?!</tool_use>).)*$', '', message)
            message = re.sub(r'<tool_result>(?:(?!</tool_result>).)*$', '', message)
            if message.strip():
                cleaned_history.append(message)
        
        return json.dumps(cleaned_history)

    def _reset_context(self) -> str:
        with self.context_lock:
            self.active_contexts.clear()
        return "Context reset successful"

    def _compress_history(self, history: List[str]) -> str:
        compressed = []
        current_length = 0
        max_length = 8000  # Adjust based on requirements

        for message in reversed(history):
            message_length = len(message)
            if current_length + message_length <= max_length:
                compressed.insert(0, message)
                current_length += message_length
            else:
                break

        return json.dumps(compressed)
from tools.base import BaseTool
import traceback
import json
import re
from typing import List, Dict, Any

class ErrorHandlerTool(BaseTool):
    name = "errorhandlertool"
    description = '''
    Utility tool for handling and formatting error messages:
    - Consolidates duplicate error messages
    - Formats errors cleanly without repetitive structures
    - Prevents recursive error propagation
    - Implements maximum message length limits
    - Filters system-level traces
    - Provides human-readable error summaries
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "error_messages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of error messages to process"
            },
            "include_traces": {
                "type": "boolean",
                "description": "Whether to include system traces in output"
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum length for formatted error message"
            }
        },
        "required": ["error_messages"]
    }

    def execute(self, **kwargs) -> str:
        error_messages = kwargs.get("error_messages", [])
        include_traces = kwargs.get("include_traces", False)
        max_length = kwargs.get("max_length", 1000)

        if not error_messages:
            return "No error messages to process"

        # Consolidate duplicate messages
        unique_errors = {}
        for error in error_messages:
            # Clean JSON structures
            cleaned_error = self._clean_json_structure(error)
            if cleaned_error in unique_errors:
                unique_errors[cleaned_error] += 1
            else:
                unique_errors[cleaned_error] = 1

        # Format output
        formatted_errors = []
        for error, count in unique_errors.items():
            if not include_traces and self._is_system_trace(error):
                continue

            if count > 1:
                formatted_errors.append(f"({count}x) {error}")
            else:
                formatted_errors.append(error)

        # Combine and truncate
        result = "\n".join(formatted_errors)
        if len(result) > max_length:
            result = result[:max_length-3] + "..."

        return result

    def _clean_json_structure(self, error_msg: str) -> str:
        try:
            # Remove repeated JSON formatting
            json_pattern = r'{[\s\S]*?}'
            cleaned = re.sub(json_pattern, lambda m: self._simplify_json(m.group(0)), error_msg)
            # Remove multiple spaces and newlines
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned
        except:
            return error_msg

    def _simplify_json(self, json_str: str) -> str:
        try:
            parsed = json.loads(json_str)
            return json.dumps(parsed, sort_keys=True)
        except:
            return json_str

    def _is_system_trace(self, error_msg: str) -> bool:
        system_patterns = [
            r'File ".*?",\s+line\s+\d+',
            r'Traceback \(most recent call last\):',
            r'^\s+at\s+.*?\s+\(.*?\)$'
        ]
        return any(re.search(pattern, error_msg) for pattern in system_patterns)
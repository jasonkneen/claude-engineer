from tools.base import BaseTool
import re
import json
from typing import Dict, Any

class MessageHistoryCompressionTool(BaseTool):
    name = "messagehistorycompressiontool"
    description = '''
    Compresses conversation history when approaching size limits while preserving important context.
    Maintains system context, recent messages, and key markers like goals and tasks.
    Returns compressed history and compression metrics.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "history": {"type": "string", "description": "Full conversation history to compress"},
            "max_size": {"type": "integer", "description": "Maximum allowed size", "default": 200000},
            "threshold": {"type": "integer", "description": "Size threshold to trigger compression", "default": 175000},
            "output_file": {"type": "string", "description": "Optional file to save compressed history"}
        },
        "required": ["history"]
    }

    def execute(self, **kwargs) -> str:
        history = kwargs.get("history")
        max_size = kwargs.get("max_size", 200000)
        threshold = kwargs.get("threshold", 175000)
        output_file = kwargs.get("output_file", None)

        original_size = len(history)
        if original_size <= threshold:
            return json.dumps({
                "compressed_history": history,
                "metrics": {
                    "original_size": original_size,
                    "compressed_size": original_size,
                    "compression_ratio": 1.0
                },
                "preservation_details": "No compression needed"
            })

        # Extract important sections
        system_context = re.search(r"(system:.*?)(?=\n\w+:|$)", history, re.DOTALL | re.IGNORECASE)
        goals = re.findall(r"(goal:.*?)(?=\n\w+:|$)", history, re.DOTALL | re.IGNORECASE)
        tasks = re.findall(r"(task:.*?)(?=\n\w+:|$)", history, re.DOTALL | re.IGNORECASE)
        status = re.findall(r"(status:.*?)(?=\n\w+:|$)", history, re.DOTALL | re.IGNORECASE)

        # Split into messages
        messages = re.split(r"\n(?=human:|assistant:)", history)
        
        # Keep system context, last 5 messages, and important markers
        preserved_sections = []
        if system_context:
            preserved_sections.append(system_context.group(1))
        
        preserved_sections.extend(goals[-2:] if goals else [])
        preserved_sections.extend(tasks[-2:] if tasks else [])
        preserved_sections.extend(status[-1:] if status else [])
        
        # Add recent messages
        preserved_sections.extend(messages[-5:])

        # Combine preserved sections
        compressed_history = "\n".join(preserved_sections)

        # Ensure we're under max_size
        if len(compressed_history) > max_size:
            compressed_history = compressed_history[:max_size-100] + "\n...[truncated]..."

        compression_metrics = {
            "original_size": original_size,
            "compressed_size": len(compressed_history),
            "compression_ratio": len(compressed_history) / original_size
        }

        preservation_details = {
            "preserved_elements": {
                "system_context": bool(system_context),
                "goals": len(goals),
                "tasks": len(tasks),
                "status": len(status),
                "recent_messages": min(5, len(messages))
            }
        }

        result = {
            "compressed_history": compressed_history,
            "metrics": compression_metrics,
            "preservation_details": preservation_details
        }

        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                result["file_save_error"] = str(e)

        return json.dumps(result, indent=2)
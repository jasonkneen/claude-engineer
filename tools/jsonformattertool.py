from tools.base import BaseTool
import json
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter

class JsonFormatterTool(BaseTool):
    name = "jsonformattertool"
    description = '''
    Formats and beautifies JSON strings with color coding and configurable options.
    Features:
    - Configurable indentation (2 or 4 spaces)
    - Optional compact output
    - Optional key sorting
    - Color-coded output
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "json_string": {
                "type": "string",
                "description": "JSON string to format"
            },
            "indent": {
                "type": "integer",
                "enum": [2, 4],
                "description": "Indentation spaces (2 or 4)",
                "default": 2
            },
            "compact": {
                "type": "boolean",
                "description": "Output in compact format",
                "default": False
            },
            "sort_keys": {
                "type": "boolean",
                "description": "Sort dictionary keys",
                "default": False
            }
        },
        "required": ["json_string"]
    }

    def _hide_params_in_call(self, func_name: str, **kwargs) -> str:
        return f"{func_name}(...)"

    def execute(self, **kwargs) -> str:
        try:
            json_data = json.loads(kwargs['json_string'])
            indent = kwargs.get('indent', 2)
            compact = kwargs.get('compact', False)
            sort_keys = kwargs.get('sort_keys', False)

            if compact:
                formatted_json = json.dumps(json_data, separators=(',', ':'), sort_keys=sort_keys)
            else:
                formatted_json = json.dumps(json_data, indent=indent, sort_keys=sort_keys)

            colored_output = highlight(formatted_json, JsonLexer(), TerminalFormatter())
            return colored_output.strip()

        except json.JSONDecodeError as e:
            return f"Invalid JSON: {str(e)}"
        except Exception as e:
            return f"Error formatting JSON: {str(e)}"
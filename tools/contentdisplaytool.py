from tools.base import BaseTool
import pygments
from pygments import formatters, lexers
from pygments.util import ClassNotFound

class ContentDisplayTool(BaseTool):
    name = "contentdisplaytool"
    description = '''
    Displays raw text content with preserved formatting.
    Trims leading/trailing whitespace while maintaining internal spacing.
    Optionally applies syntax highlighting for supported formats.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Raw text content to display"
            },
            "format": {
                "type": "string",
                "description": "Optional format for syntax highlighting (e.g. python, markdown)",
                "default": None
            }
        },
        "required": ["content"]
    }

    def execute(self, **kwargs) -> str:
        content = kwargs.get("content", "").strip()
        format_type = kwargs.get("format")

        if not content:
            return ""

        if not format_type:
            return content

        try:
            lexer = lexers.get_lexer_by_name(format_type)
            formatter = formatters.TerminalFormatter()
            highlighted = pygments.highlight(content, lexer, formatter)
            return highlighted.strip()
        except ClassNotFound:
            return content
from tools.base import BaseTool
import os
import re
import sys

class ColorTool(BaseTool):
    name = "colortool"
    description = '''
    Handles terminal color output with automatic capability detection.
    Converts ANSI color codes to appropriate terminal format.
    Provides fallback formatting when colors aren't supported.
    Sanitizes output to prevent raw escape sequences.
    Supports bold, colors, and underlining.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to format"
            },
            "color": {
                "type": "string",
                "enum": ["red", "green", "blue", "yellow", "magenta", "cyan", "white"],
                "description": "Color to apply"
            },
            "style": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["bold", "underline", "normal"]
                },
                "description": "Styles to apply"
            }
        },
        "required": ["text"]
    }

    def __init__(self):
        super().__init__()
        self.has_color = self._detect_color_support()
        self.color_map = {
            "red": "\033[31m",
            "green": "\033[32m",
            "blue": "\033[34m",
            "yellow": "\033[33m",
            "magenta": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m"
        }
        self.style_map = {
            "bold": "\033[1m",
            "underline": "\033[4m",
            "normal": "\033[0m"
        }

    def _detect_color_support(self) -> bool:
        if not hasattr(sys.stdout, "isatty"):
            return False
        if not sys.stdout.isatty():
            return False
        if "COLORTERM" in os.environ:
            return True
        if "TERM" in os.environ and os.environ["TERM"] in ["xterm", "xterm-256color", "linux"]:
            return True
        return False

    def _sanitize_text(self, text: str) -> str:
        return re.sub(r'\033\[[0-9;]*[mGKH]', '', text)

    def _apply_formatting(self, text: str, color: str = None, style: list = None) -> str:
        if not self.has_color:
            return text

        result = ""
        if style:
            for s in style:
                if s in self.style_map:
                    result += self.style_map[s]
        
        if color and color in self.color_map:
            result += self.color_map[color]
        
        result += text
        result += self.style_map["normal"]
        return result

    def execute(self, **kwargs) -> str:
        text = kwargs.get("text", "")
        color = kwargs.get("color")
        style = kwargs.get("style", [])

        sanitized_text = self._sanitize_text(text)
        formatted_text = self._apply_formatting(sanitized_text, color, style)
        
        return formatted_text
from tools.base import BaseTool
import pygments
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
import json

class CodeFormatter(BaseTool):
    name = "codeformatter"
    description = '''
    Formats and syntax-highlights code blocks with support for multiple languages.
    Handles inline code, block code, and diff formatting.
    Supports line numbers and syntax highlighting.
    Auto-detects language if not specified.
    Returns markdown-compatible formatted code.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The code/text to format"
            },
            "language": {
                "type": "string",
                "description": "Programming language for syntax highlighting (optional)"
            },
            "style": {
                "type": "string",
                "enum": ["inline", "block", "diff"],
                "default": "block",
                "description": "Code block style to use"
            },
            "line_numbers": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include line numbers"
            }
        },
        "required": ["code"]
    }

    def execute(self, **kwargs) -> str:
        code = kwargs.get("code", "").strip()
        language = kwargs.get("language", None)
        style = kwargs.get("style", "block")
        line_numbers = kwargs.get("line_numbers", False)

        if not code:
            return "Error: No code provided"

        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = get_lexer_by_name("text")

        formatter = HtmlFormatter(
            linenos='table' if line_numbers else False,
            cssclass="highlight",
            wrapcode=True
        )

        if style == "diff":
            formatted_lines = []
            for line in code.split('\n'):
                if line.startswith('+'):
                    formatted_lines.append(f'<span class="addition">{line}</span>')
                elif line.startswith('-'):
                    formatted_lines.append(f'<span class="deletion">{line}</span>')
                else:
                    formatted_lines.append(line)
            code = '\n'.join(formatted_lines)

        highlighted = highlight(code, lexer, formatter)

        if style == "inline":
            return f'<code>{highlighted}</code>'
        else:
            copy_button = '<button class="copy-button" onclick="copyCode(this)">Copy</button>'
            return f'''
<div class="code-block">
    {copy_button}
    <pre>{highlighted}</pre>
</div>
'''

    def _validate_syntax(self, code: str, language: str) -> bool:
        try:
            if language == "python":
                compile(code, "<string>", "exec")
            elif language == "json":
                json.loads(code)
            return True
        except Exception as e:
            return False

    def _detect_language(self, code: str) -> str:
        try:
            lexer = guess_lexer(code)
            return lexer.name.lower()
        except ClassNotFound:
            return "text"
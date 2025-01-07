from tools.base import BaseTool
import json
import re
from typing import List, Dict, Optional

class CommandListFormatter(BaseTool):
    name = "commandlistformatter"
    description = '''
    Formats a list of commands or events into a clean, readable structure.
    Features:
    - One command per line with proper indentation
    - Optional grouping by prefix/category
    - Strips common prefixes for cleaner display
    - Supports JSON or plain text input
    - Multiple output formats (plain text, markdown)
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "commands": {
                "type": "string",
                "description": "JSON array or newline-separated list of commands"
            },
            "format": {
                "type": "string",
                "enum": ["plain", "markdown"],
                "default": "plain",
                "description": "Output format style"
            },
            "group_by_prefix": {
                "type": "boolean",
                "default": True,
                "description": "Group commands by common prefixes"
            },
            "strip_prefix": {
                "type": "boolean",
                "default": True,
                "description": "Strip common prefixes from display"
            }
        },
        "required": ["commands"]
    }

    def _parse_input(self, commands: str) -> List[str]:
        try:
            return json.loads(commands)
        except json.JSONDecodeError:
            return [cmd.strip() for cmd in commands.split('\n') if cmd.strip()]

    def _extract_command_name(self, command: str) -> str:
        patterns = [
            r'onCommand:([\w\-\.]+)',
            r'command\.([\w\-\.]+)',
            r'(\w+\.\w+)$'
        ]
        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                return match.group(1)
        return command

    def _group_commands(self, commands: List[str]) -> Dict[str, List[str]]:
        groups = {}
        for cmd in commands:
            clean_cmd = self._extract_command_name(cmd)
            prefix = clean_cmd.split('.')[0] if '.' in clean_cmd else 'other'
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(clean_cmd)
        return groups

    def _format_plain(self, groups: Dict[str, List[str]], strip_prefix: bool) -> str:
        output = []
        for prefix, commands in sorted(groups.items()):
            output.append(f"\n{prefix}:")
            for cmd in sorted(commands):
                display_cmd = cmd.split('.', 1)[1] if strip_prefix and '.' in cmd else cmd
                output.append(f"  - {display_cmd}")
        return '\n'.join(output)

    def _format_markdown(self, groups: Dict[str, List[str]], strip_prefix: bool) -> str:
        output = []
        for prefix, commands in sorted(groups.items()):
            output.append(f"\n### {prefix}")
            for cmd in sorted(commands):
                display_cmd = cmd.split('.', 1)[1] if strip_prefix and '.' in cmd else cmd
                output.append(f"- `{display_cmd}`")
        return '\n'.join(output)

    def execute(self, **kwargs) -> str:
        commands = self._parse_input(kwargs["commands"])
        format_type = kwargs.get("format", "plain")
        group_by_prefix = kwargs.get("group_by_prefix", True)
        strip_prefix = kwargs.get("strip_prefix", True)

        if not commands:
            return "No commands provided"

        if group_by_prefix:
            grouped_commands = self._group_commands(commands)
        else:
            grouped_commands = {"Commands": commands}

        if format_type == "markdown":
            return self._format_markdown(grouped_commands, strip_prefix)
        return self._format_plain(grouped_commands, strip_prefix)
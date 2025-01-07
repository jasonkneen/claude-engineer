# tools/self_evolver.py

import os
from typing import Optional

from rich.console import Console

from tools.base import BaseTool


class SelfEvolverTool(BaseTool):
    """
    A tool that can propose and apply changes to local Python files, subject to user approval.
    The LLM can call this tool to self-modify or create new code, if enabled.
    """
    name = "self_evolver"
    description = (
        "Propose and apply code modifications to local files. "
        "Provide a 'filename' and the full new content or a diff in 'content_diff'. "
        "User must confirm before changes are written."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "content_diff": {"type": "string"}
        },
        "required": ["filename", "content_diff"]
    }

    def __init__(self):
        super().__init__()
        self.console = Console()

    def execute(self, filename: str, content_diff: str) -> str:
        """
        Show the user the proposed content changes, ask for confirmation, and
        if approved, overwrite or patch the file.
        """
        self.console.print(f"\n[bold yellow]Proposed changes to:[/bold yellow] {filename}")
        self.console.print(content_diff)  # Entire new file or a unified diff

        user_input = input("\nApply these changes? (y/n): ").strip().lower()
        if user_input == 'y':
            try:
                # Simple approach: treat 'content_diff' as the full new file content
                # and overwrite 'filename' with it.
                self._apply_changes(filename, content_diff)
                return f"Changes applied to {filename}."
            except Exception as e:
                return f"Error applying changes: {str(e)}"
        else:
            return "Changes not applied."

    def _apply_changes(self, filename: str, new_content: str):
        """
        Overwrite the file with 'new_content'. For a real diff approach,
        you might parse and apply only the patch hunks.
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
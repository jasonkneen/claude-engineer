from tools.base import BaseTool
from tools.filecontentreadertool import FileContentReaderTool
import os
import json
import logging
from typing import Optional, Dict, Any

class OnStartup(BaseTool):
    name = "onstartup"
    description = '''
    Automatically runs during assistant initialization to establish working context.
    Reads and parses status.txt from the working directory to understand current context.
    Makes context information available throughout the session.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "status_file": {
                "type": "string",
                "description": "Optional path to status file. Defaults to status.txt in working directory"
            }
        },
        "required": []
    }

    def __init__(self):
        super().__init__()
        self._context = {}
        self._initialized = False
        self._file_reader = FileContentReaderTool()

    def execute(self, **kwargs) -> str:
        try:
            status_file = kwargs.get('status_file', 'status.txt')
            result = self.read_status(status_file)
            return f"Context initialized: {result}"
        except Exception as e:
            logging.error(f"Error during startup: {str(e)}")
            return f"Failed to initialize context: {str(e)}"

    def read_status(self, status_file: str = 'status.txt') -> Dict[str, Any]:
        try:
            if not os.path.isabs(status_file):
                status_file = os.path.join(os.getcwd(), status_file)

            if not os.path.exists(status_file):
                logging.warning(f"Status file not found: {status_file}")
                self._context = {}
                return self._context

            content = self._file_reader.execute(filepath=status_file)
            
            try:
                self._context = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                self._context = {"raw_content": content.strip()}
            
            self._initialized = True
            return self._context

        except Exception as e:
            logging.error(f"Error reading status file: {str(e)}")
            self._context = {}
            raise

    def get_current_context(self) -> Dict[str, Any]:
        if not self._initialized:
            self.read_status()
        return self._context

    def is_initialized(self) -> bool:
        return self._initialized

    def reset(self) -> None:
        self._context = {}
        self._initialized = False
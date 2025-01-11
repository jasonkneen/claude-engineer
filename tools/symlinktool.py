from tools.base import BaseTool
import os
from pathlib import Path
import shutil

class SymlinkTool(BaseTool):
    name = "symlinktool"
    description = '''
    Creates and manages symbolic links between directories.
    Supports working directory management and symlink operations.
    Handles both absolute and relative paths across platforms.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["create_symlink", "remove_symlink", "set_working_dir", "get_working_dir"],
                "description": "Operation to perform"
            },
            "source_path": {
                "type": "string",
                "description": "Source path for symlink creation"
            },
            "target_path": {
                "type": "string",
                "description": "Target path for symlink creation"
            },
            "path": {
                "type": "string",
                "description": "Path for single-path operations"
            }
        },
        "required": ["operation"]
    }

    def __init__(self):
        super().__init__()
        self.working_dir = os.getcwd()

    def execute(self, **kwargs) -> str:
        operation = kwargs.get("operation")

        try:
            if operation == "create_symlink":
                source = kwargs.get("source_path")
                target = kwargs.get("target_path")
                if not source or not target:
                    return "Source and target paths are required for symlink creation"
                return self.create_symlink(source, target)

            elif operation == "remove_symlink":
                path = kwargs.get("path")
                if not path:
                    return "Path is required for symlink removal"
                return self.remove_symlink(path)

            elif operation == "set_working_dir":
                path = kwargs.get("path")
                if not path:
                    return "Path is required for setting working directory"
                return self.set_working_directory(path)

            elif operation == "get_working_dir":
                return self.get_working_directory()

            else:
                return f"Unknown operation: {operation}"

        except Exception as e:
            return f"Error: {str(e)}"

    def create_symlink(self, source_path: str, target_path: str) -> str:
        source = Path(source_path)
        target = Path(target_path)

        if not source.is_absolute():
            source = Path(self.working_dir) / source
        if not target.is_absolute():
            target = Path(self.working_dir) / target

        if not source.exists():
            return f"Source path does not exist: {source}"

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                target.unlink()
            os.symlink(source, target, target_is_directory=source.is_dir())
            return f"Successfully created symlink from {source} to {target}"
        except Exception as e:
            return f"Failed to create symlink: {str(e)}"

    def remove_symlink(self, path: str) -> str:
        symlink_path = Path(path)
        if not symlink_path.is_absolute():
            symlink_path = Path(self.working_dir) / symlink_path

        if not symlink_path.is_symlink():
            return f"Path is not a symlink: {symlink_path}"

        try:
            symlink_path.unlink()
            return f"Successfully removed symlink: {symlink_path}"
        except Exception as e:
            return f"Failed to remove symlink: {str(e)}"

    def set_working_directory(self, path: str) -> str:
        new_path = Path(path)
        if not new_path.is_absolute():
            new_path = Path(self.working_dir) / new_path

        if not new_path.exists():
            return f"Directory does not exist: {new_path}"
        if not new_path.is_dir():
            return f"Path is not a directory: {new_path}"

        self.working_dir = str(new_path)
        return f"Working directory set to: {self.working_dir}"

    def get_working_directory(self) -> str:
        return f"Current working directory: {self.working_dir}"
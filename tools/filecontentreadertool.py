from tools.base import BaseTool
from typing import Dict, Any, Union
import os
import json
import mimetypes

class FileContentReaderTool(BaseTool):
    name = "filecontentreadertool"
    description = '''
    Reads content from multiple files and returns their contents.
    Accepts a list of file paths and returns a dictionary with file paths as keys
    and their content as values.
    Handles file reading errors gracefully with built-in Python exceptions.
    When given a directory, recursively reads all text files while skipping binaries and common ignore patterns.
    '''
    
    # Files and directories to ignore
    IGNORE_PATTERNS = {
        # Hidden files and directories
        '.git', '.svn', '.hg', '.DS_Store', '.env', '.idea', '.vscode', '.settings',
        # Build directories
        'node_modules', '__pycache__', 'build', 'dist', 'venv', 'env', 'bin', 'obj',
        'target', 'out', 'Debug', 'Release', 'x64', 'x86', 'builds', 'coverage',
        # Binary file extensions
        '.pyc', '.pyo', '.so', '.dll', '.dylib', '.pdb', '.ilk', '.exp', '.map',
        '.exe', '.bin', '.dat', '.db', '.sqlite', '.sqlite3', '.o', '.cache',
        '.lib', '.a', '.sys', '.ko', '.obj', '.iso', '.msi', '.msp', '.msm',
        '.img', '.dmg', '.class', '.jar', '.war', '.ear', '.aar', '.apk',
        # Media files
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.psd', '.ai', '.eps',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.aac', '.m4a', '.wma', '.midi',
        '.flv', '.mkv', '.wmv', '.m4v', '.webm', '.3gp', '.mpg', '.mpeg', '.m2v',
        '.ogg', '.ogv', '.webp', '.heic', '.raw', '.svg', '.ico', '.icns',
        # Archive files
        '.zip', '.tar', '.gz', '.rar', '.7z', '.pkg', '.deb', '.rpm', '.snap',
        '.bz2', '.xz', '.cab', '.iso', '.tgz', '.tbz2', '.lz', '.lzma', '.tlz',
        # IDE and editor files
        '.sln', '.suo', '.user', '.workspace', '.project', '.classpath', '.iml',
        # Log and temp files
        '.log', '.tmp', '.temp', '.swp', '.bak', '.old', '.orig', '.pid'
    }

    input_schema = {
        "type": "object",
        "properties": {
            "file_paths": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of file paths to read"
            }
        },
        "required": ["file_paths"]
    }

    def _should_skip(self, path: str) -> bool:
        """Determine if a file or directory should be skipped."""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()

        # Skip if name or extension matches ignore patterns
        if name in self.IGNORE_PATTERNS or ext in self.IGNORE_PATTERNS:
            return True

        # Skip hidden files/directories (starting with .)
        if name.startswith('.'):
            return True

        # If it's a file, check if it's binary using mimetype
        if os.path.isfile(path):
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type and not mime_type.startswith('text/'):
                return True

        return False

    def _read_file(self, file_path: str) -> str:
        """Safely read a file and handle errors."""
        try:
            if not os.path.exists(file_path):
                return "Error: File not found"

            if self._should_skip(file_path):
                return "Skipped: Binary or ignored file type"

            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()

        except PermissionError:
            return "Error: Permission denied"
        except IsADirectoryError:
            return "Error: Path is a directory"
        except UnicodeDecodeError:
            return "Error: Unable to decode file (likely binary)"
        except Exception as e:
            return f"Error: {str(e)}"

    def _read_directory(self, dir_path: str) -> dict:
        """Recursively read all files in a directory."""
        results = {}

        try:
            for root, dirs, files in os.walk(dir_path):
                # Filter out directories to skip
                dirs[:] = [d for d in dirs if not self._should_skip(os.path.join(root, d))]

                # Process files
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self._should_skip(file_path):
                        content = self._read_file(file_path)
                        results[file_path] = content

        except Exception as e:
            results[dir_path] = f"Error reading directory: {str(e)}"

        return results

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Read file contents and return them as properly formatted code blocks with proper styling."""
        from rich import box
        from rich.panel import Panel
        import json

        file_paths = kwargs.get('file_paths', [])
        
        def detect_language(path: str) -> str:
            """Detect language based on file extension."""
            ext = os.path.splitext(path)[1].lstrip('.')
            return {
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'json': 'json',
                'md': 'markdown',
                'html': 'html',
                'css': 'css',
                'sh': 'bash',
            }.get(ext, 'text')

        def format_content(path: str, content: str) -> str:
            """Format content as a code block with detected language."""
            lang = detect_language(path)
            return f"```{lang}\n{content}\n```"

        try:
            if not file_paths:
                return {"type": "text", "text": "Error: No file paths provided"}
                
            # Convert relative paths to absolute paths
            def make_absolute(path):
                if not os.path.isabs(path):
                    return os.path.abspath(os.path.join(os.getcwd(), path))
                return path

            # For single file, return formatted content directly
            if len(file_paths) == 1:
                path = make_absolute(file_paths[0])
                if os.path.isdir(path):
                    dir_results = self._read_directory(path)
                    formatted = "\n\n".join(
                        f"File: {p}\n{format_content(p, c)}" 
                        for p, c in dir_results.items()
                    )
                    return {"type": "text", "text": formatted}
                else:
                    content = self._read_file(path)
                    formatted = format_content(path, content)
                    return {"type": "text", "text": formatted}

            # For multiple files, return formatted content for each
            results = {}
            for path in file_paths:
                abs_path = make_absolute(path)
                if os.path.isdir(abs_path):
                    dir_results = self._read_directory(abs_path)
                    results.update(dir_results)
                else:
                    content = self._read_file(abs_path)
                    results[abs_path] = content

            # Format each file's content with proper code blocks
            formatted_files = []
            for path, content in results.items():
                formatted = format_content(path, content)
                formatted_files.append(f"File: {path}\n{formatted}")
            
            # Join all formatted files with proper spacing
            from rich.console import Console
            from io import StringIO

            # Format with proper styling
            cleaned_input = file_paths
            cleaned_result = "\n\n".join(formatted_files)
            
            # Format with proper styling
            from rich.syntax import Syntax
            from rich.console import Group

            # Create syntax-highlighted code block
            code = Syntax(cleaned_result, "python", theme="monokai", line_numbers=True)
            
            # Create input section
            input_section = f"[cyan]📥 Input:[/cyan] {json.dumps(cleaned_input, indent=2)}"
            
            # Group the components
            content = Group(
                input_section,
                "[cyan]📤 Result:[/cyan]",
                code
            )

            # Create panel with proper styling
            panel = Panel(
                content,
                title="Tool used: FileContentReader",
                title_align="left",
                border_style="cyan",
                padding=(0, 1)
            )
            
            return {"type": "text", "text": str(panel)}

        except Exception as e:
            return {"type": "text", "text": f"Error: {str(e)}"}

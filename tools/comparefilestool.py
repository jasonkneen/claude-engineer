from tools.base import BaseTool
import os

class CompareFilesTool(BaseTool):
    name = "comparefilestool"
    description = '''
    Compares two text files and identifies lines or sections that are present in the first file
    but missing from the second file.
    Returns a report of the differences found.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "file1_path": {
                "type": "string",
                "description": "Path to the first file"
            },
            "file2_path": {
                "type": "string",
                "description": "Path to the second file"
            }
        },
        "required": ["file1_path", "file2_path"]
    }

    def execute(self, **kwargs) -> str:
        file1_path = kwargs.get("file1_path")
        file2_path = kwargs.get("file2_path")

        if not os.path.exists(file1_path):
            return f"Error: First file '{file1_path}' does not exist."
        if not os.path.exists(file2_path):
            return f"Error: Second file '{file2_path}' does not exist."

        try:
            with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
                file1_lines = set(f1.readlines())
                file2_lines = set(f2.readlines())

            missing_lines = file1_lines - file2_lines

            if not missing_lines:
                return "No differences found. All lines in the first file are present in the second file."

            result = "Lines present in first file but missing from second file:\n\n"
            for line in sorted(missing_lines):
                result += f"- {line.strip()}\n"

            return result

        except Exception as e:
            return f"Error comparing files: {str(e)}"
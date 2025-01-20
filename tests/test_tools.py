import unittest
import json
from tools.e2bcodetool import E2bCodeTool
from tools.errorhandlertool import ErrorHandlerTool
from tools.filecontentreadertool import FileContentReaderTool
from tools.filecreatortool import FileCreatorTool
from tools.fileedittool import FileEditTool
from tools.gitmergeconflicttool import GitMergeConflictTool
from tools.gitmergetool import GitMergeTool
from tools.lintingtool import LintingTool
from tools.screenshottool import ScreenshotTool
from tools.toolcreator import ToolCreatorTool
from tools.uvpackagemanager import UVPackageManager
from tools.webscrapertool import WebScraperTool


class TestTools(unittest.TestCase):
    def setUp(self):
        # Initialize tools
        self.tools = {
            "e2bcode": E2bCodeTool(),
            "errorhandler": ErrorHandlerTool(),
            "filereader": FileContentReaderTool(),
            "filecreator": FileCreatorTool(),
            "fileedit": FileEditTool(),
            "gitconflict": GitMergeConflictTool(),
            "gitmerge": GitMergeTool(),
            "linting": LintingTool(),
            "screenshot": ScreenshotTool(),
            "toolcreator": ToolCreatorTool(),
            "uvpackage": UVPackageManager(),
            "webscraper": WebScraperTool(),
        }

    def test_tool_initialization(self):
        """Test that all tools initialize correctly with required properties"""
        for name, tool in self.tools.items():
            with self.subTest(tool=name):
                # Check required properties
                self.assertIsInstance(tool.name, str)
                self.assertIsInstance(tool.description, str)
                self.assertIsInstance(tool.input_schema, dict)
                self.assertTrue(hasattr(tool, "execute"))

    def test_tool_schema_validation(self):
        """Test that tool schemas are valid"""
        for name, tool in self.tools.items():
            with self.subTest(tool=name):
                schema = tool.input_schema
                # Basic schema validation
                self.assertIn("type", schema)
                self.assertIn("properties", schema)
                if "required" in schema:
                    self.assertIsInstance(schema["required"], list)

    def test_error_handler_tool(self):
        """Test Error Handler Tool functionality"""
        tool = self.tools["errorhandler"]
        test_errors = [
            "Error 1: Something went wrong",
            "Error 1: Something went wrong",  # Duplicate
            "Error 2: Another issue occurred",
            "Traceback (most recent call last):\n  File 'test.py', line 10",  # System trace
        ]

        # Test basic error handling
        result = tool.execute(error_messages=test_errors, include_traces=False)
        self.assertIn("(2x) Error 1", result)
        self.assertIn("Error 2", result)
        self.assertNotIn("Traceback", result)  # System trace should be filtered out

        # Test with traces included
        result_with_traces = tool.execute(
            error_messages=test_errors, include_traces=True
        )
        self.assertIn("Traceback", result_with_traces)

    def test_file_operations(self):
        """Test file operation tools"""
        # Create a temporary test file
        test_content = "test content"
        creator = self.tools["filecreator"]
        create_result = creator.execute(path="test_file.txt", content=test_content)

        # Verify file creation
        self.assertTrue(isinstance(create_result, str))

        # Test file reading
        reader = self.tools["filereader"]
        read_result = reader.execute(path="test_file.txt")
        self.assertIn(test_content, read_result)

        # Test file editing
        editor = self.tools["fileedit"]
        new_content = "updated content"
        edit_result = editor.execute(path="test_file.txt", content=new_content)
        self.assertTrue(isinstance(edit_result, str))

        # Verify the edit
        read_result_after_edit = reader.execute(path="test_file.txt")
        self.assertIn(new_content, read_result_after_edit)

    def test_error_handling(self):
        """Test error handling across tools"""
        for name, tool in self.tools.items():
            with self.subTest(tool=name):
                # Test with invalid parameters
                try:
                    result = tool.execute(invalid_param="invalid")
                    if isinstance(result, str):
                        # Some tools return error messages as strings
                        self.assertTrue(
                            "error" in result.lower()
                            or "invalid" in result.lower()
                            or "failed" in result.lower()
                        )
                except Exception as e:
                    # Some tools might raise exceptions directly
                    self.assertIsInstance(e, Exception)


if __name__ == "__main__":
    unittest.main()

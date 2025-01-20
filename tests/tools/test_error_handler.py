import unittest
from tools.errorhandlertool import ErrorHandlerTool


class TestErrorHandlerTool(unittest.TestCase):
    def setUp(self):
        self.tool = ErrorHandlerTool()

    def test_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "errorhandlertool")
        self.assertIsInstance(self.tool.description, str)
        self.assertIsInstance(self.tool.input_schema, dict)
        self.assertTrue(hasattr(self.tool, "execute"))

    def test_basic_error_handling(self):
        """Test basic error message processing"""
        test_errors = [
            "Error 1: Something went wrong",
            "Error 1: Something went wrong",  # Duplicate
            "Error 2: Another issue occurred",
        ]

        result = self.tool.execute(error_messages=test_errors)

        # Check for duplicate consolidation
        self.assertIn("(2x)", result)
        self.assertIn("Error 1", result)
        self.assertIn("Error 2", result)

    def test_system_trace_filtering(self):
        """Test system trace filtering"""
        test_errors = [
            "Error: Application error",
            "Traceback (most recent call last):\n  File 'test.py', line 10",
        ]

        # Test with traces excluded
        result_no_traces = self.tool.execute(
            error_messages=test_errors, include_traces=False
        )
        self.assertIn("Error: Application error", result_no_traces)
        self.assertNotIn("Traceback", result_no_traces)

        # Test with traces included
        result_with_traces = self.tool.execute(
            error_messages=test_errors, include_traces=True
        )
        self.assertIn("Traceback", result_with_traces)

    def test_max_length_limit(self):
        """Test maximum length limiting"""
        long_error = "Error: " + "x" * 1000
        result = self.tool.execute(error_messages=[long_error], max_length=50)
        self.assertLessEqual(len(result), 50)
        self.assertTrue(result.endswith("..."))

    def test_empty_input(self):
        """Test handling of empty input"""
        result = self.tool.execute(error_messages=[])
        self.assertEqual(result, "No error messages to process")


if __name__ == "__main__":
    unittest.main()

# Tool Testing Framework

This directory contains the test suite for Claude Engineer tools. The tests are designed to verify the functionality, error handling, and edge cases of each tool.

## Directory Structure

```
tests/tools/
├── README.md                 # This documentation
├── run_tool_tests.py        # Test runner script
├── test_error_handler.py    # Tests for ErrorHandlerTool
└── test_file_reader.py      # Tests for FileContentReaderTool
```

## Available Tests

### ErrorHandlerTool Tests
- Tool initialization and properties
- Basic error message processing
- System trace filtering
- Maximum length limiting
- Empty input handling

### FileContentReaderTool Tests
- Tool initialization and properties
- Single file reading
- Multiple files reading
- Binary file handling
- Directory operations
- Non-existent file handling
- Empty file list handling

## Running Tests

### Run All Tests
```bash
# From project root
PYTHONPATH=/path/to/project python3 tests/tools/run_tool_tests.py --verbose
```

### Run Specific Test File
```bash
# From project root
PYTHONPATH=/path/to/project python3 tests/tools/run_tool_tests.py --pattern test_error_handler.py --verbose
```

## Test Runner Options
- `--pattern`: Specify a test file pattern to run specific tests
- `--verbose` or `-v`: Enable verbose output
- `--help` or `-h`: Show help message

## Adding New Tests

1. Create a new test file following the naming convention `test_*.py`
2. Import the tool and BaseTool
3. Create a test class inheriting from `unittest.TestCase`
4. Implement test methods following these categories:
   - Initialization tests
   - Basic functionality tests
   - Edge case tests
   - Error handling tests

Example template:
```python
import unittest
from tools.your_tool import YourTool

class TestYourTool(unittest.TestCase):
    def setUp(self):
        self.tool = YourTool()

    def test_initialization(self):
        """Test tool initialization and properties"""
        self.assertEqual(self.tool.name, "yourtool")
        self.assertIsInstance(self.tool.description, str)
        self.assertIsInstance(self.tool.input_schema, dict)
        self.assertTrue(hasattr(self.tool, 'execute'))

    def test_basic_functionality(self):
        """Test basic tool functionality"""
        # Add your test implementation

    def test_edge_cases(self):
        """Test edge cases"""
        # Add your test implementation

    def test_error_handling(self):
        """Test error handling"""
        # Add your test implementation
```

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on the state from other tests
2. **Resource Cleanup**: Use setUp/tearDown methods to handle resource cleanup
3. **Meaningful Names**: Use descriptive test method names that indicate what is being tested
4. **Error Messages**: Provide clear error messages in assertions
5. **Documentation**: Add docstrings to test methods explaining what they test
6. **Coverage**: Aim to test both success and failure scenarios

## Current Test Coverage

Total tests: 12
- ErrorHandlerTool: 5 tests
- FileContentReaderTool: 7 tests

All tests are currently passing with proper validation of tool functionality and error handling.
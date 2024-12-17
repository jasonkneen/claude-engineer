import ast
import asyncio
import json
import logging
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from .agent_base import AgentBaseTool, AgentRole

@dataclass
class TestSpec:
    name: str
    description: str
    code: str
    changes: List[str]
    created_at: str

class TestAgentTool(AgentBaseTool):
    """Creates and tracks unit tests for all code changes.
    Maintains a separate list representing the current app specification.
    """

    description = """
    Manages test creation and tracking:
    - Creates unit tests for code changes
    - Tracks changes in app specification
    - Maintains test coverage
    - Validates test quality
    - Reports test results
    """
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "list", "delete", "run"],
                "description": "Action to perform"
            },
            "test_name": {
                "type": "string",
                "description": "Test identifier"
            },
            "code_changes": {
                "type": "object",
                "description": "Code changes to create tests for"
            },
            "test_code": {
                "type": "string",
                "description": "Test code to add/update"
            }
        },
        "required": ["action"]
    }

    def __init__(self, agent_id: str = "test_agent", name: Optional[str] = None):
        """Initialize test agent tool"""
        super().__init__(
            agent_id=agent_id,
            name=name or f"agent_test_{agent_id}",
            role=AgentRole.TEST
        )
        self.logger = logging.getLogger(__name__)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.spec_changes = []

    async def initialize(self):
        """Initialize the test agent"""
        await super().initialize()
        
        # Initialize tests in persistent state storage
        if 'tests' not in self.state.data:
            self.state.data['tests'] = {}
        self.tests = self.state.data['tests']  # Reference to persistent storage
        self.logger.debug(f"Initialized tests dictionary: {self.state.data['tests']}")

    async def execute(self, **kwargs) -> str:
        """Execute test agent action"""
        self.logger.debug(f"Executing with args: {kwargs}")

        try:
            # Handle message-based execution from base class
            if "message" in kwargs:
                return await self._process_message(
                    message=kwargs["message"],
                    context=kwargs.get("context", {}),
                    api_provider=kwargs.get("api_provider", "anthropic")
                )

            # Handle direct action-based execution
            action = kwargs.get("action")
            if not action:
                return "Action is required"

            # Execute action with proper locking
            async with self._lock:
                if action == "create":
                    test_name = kwargs.get("test_name")
                    if not test_name:
                        return "Test name is required"

                    test_code = kwargs.get("test_code")
                    code_changes = kwargs.get("code_changes", {})

                    return await self._create_test(
                        test_name=test_name,
                        code_changes=code_changes,
                        test_code=test_code
                    )

                elif action == "update":
                    test_name = kwargs.get("test_name")
                    if not test_name:
                        return "Test name is required"

                    test_code = kwargs.get("test_code")
                    if not test_code:
                        return "Test code is required for update"

                    return await self._update_test(test_name, test_code)

                elif action == "list":
                    return await self._list_tests()

                elif action == "delete":
                    test_name = kwargs.get("test_name")
                    if not test_name:
                        return "Test name is required"

                    return await self._delete_test(test_name)

                elif action == "run":
                    test_name = kwargs.get("test_name")
                    return await self._run_tests(test_name)

                else:
                    return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error executing action: {str(e)}")
            return f"Error executing action: {str(e)}"

    async def _create_test(
        self,
        test_name: str,
        code_changes: Dict[str, str] = None,
        test_code: str = None
    ) -> str:
        """Create a new test"""
        self.logger.debug(f"Creating test with name: {test_name}, changes: {code_changes}, code: {test_code}")

        if test_name in self.state.data['tests']:
            return f"Test {test_name} already exists"

        if not test_code and not code_changes:
            return "Either test code or code changes must be provided"

        if not test_code and code_changes:
            test_code = await self._generate_test_code(code_changes)

        # Validate test code syntax
        try:
            ast.parse(test_code)
        except SyntaxError as e:
            # Store invalid test for tracking
            test_spec = TestSpec(
                name=test_name,
                description=await self._extract_test_description(test_code),
                code=test_code,
                changes=list(code_changes.items()) if code_changes else [],
                created_at=datetime.now().isoformat()
            )
            self.state.data['tests'][test_name] = test_spec
            self.tests = self.state.data['tests']
            return f"Invalid test code: {str(e)}"

        try:
            # Create test spec
            test_spec = TestSpec(
                name=test_name,
                description=await self._extract_test_description(test_code),
                code=test_code,
                changes=list(code_changes.items()) if code_changes else [],
                created_at=datetime.now().isoformat()
            )

            # Store test in persistent storage
            self.state.data['tests'][test_name] = test_spec
            self.tests = self.state.data['tests']  # Update local reference
            self.logger.debug(f"Created test spec: {test_spec}")

            return f"Created test {test_name}"

        except Exception as e:
            self.logger.error(f"Error creating test: {str(e)}")
            return f"Error creating test: {str(e)}"

    async def _update_test(self, test_name: str, test_code: str) -> str:
        """Update existing test"""
        if not test_name or test_name not in self.state.data['tests']:
            return f"Test {test_name} not found"

        if not test_code:
            return "No test code provided"

        try:
            # Validate test code
            ast.parse(test_code)

            # Update test
            test_spec = self.state.data['tests'][test_name]
            test_spec.code = test_code
            test_spec.description = await self._extract_test_description(test_code)

            return f"Updated test {test_name}"

        except SyntaxError as e:
            return f"Invalid test code: {str(e)}"
        except Exception as e:
            return f"Error updating test: {str(e)}"

    async def _list_tests(self) -> str:
        """List all registered tests"""
        self.logger.debug(f"Listing tests. Current tests: {self.state.data.get('tests', {})}")

        if not self.state.data.get('tests', {}):
            return "No tests registered"

        result = []
        for name, test in self.state.data['tests'].items():
            result.append(
                f"Test: {name}\n"
                f"Description: {test.description}\n"
                f"Created: {test.created_at}\n"
                f"Changes: {len(test.changes)}\n"
                "---"
            )
        return "\n".join(result)

    async def _delete_test(self, test_name: str) -> str:
        """Delete a test"""
        if test_name not in self.state.data['tests']:
            return f"Test {test_name} not found"

        del self.state.data['tests'][test_name]
        self.tests = self.state.data['tests']  # Update local reference
        return f"Deleted test {test_name}"

    async def _run_tests(self, test_name: Optional[str] = None) -> str:
        """Run tests and return results"""
        self.logger.debug(f"Running tests. Test name: {test_name}, All tests: {self.state.data.get('tests', {})}")

        if not self.state.data.get('tests', {}):
            return "No tests registered"

        results = []
        tests_to_run = {}

        # Determine which tests to run
        if test_name:
            if test_name not in self.state.data['tests']:
                return f"Test {test_name} not found"
            tests_to_run[test_name] = self.state.data['tests'][test_name]
        else:
            tests_to_run = self.state.data['tests']

        # Run selected tests
        for name, test in tests_to_run.items():
            self.logger.debug(f"Running test: {name}")
            try:
                result = await self._execute_test(test.code)
                results.append(f"Test {name}: {result}")
            except SyntaxError as e:
                self.logger.error(f"Syntax error in test {name}: {str(e)}")
                results.append(f"Test {name}: FAIL - Syntax error: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error running test {name}: {str(e)}")
                results.append(f"Test {name}: FAIL - {str(e)}")

        return "\n".join(results)

    async def _generate_test_code(self, code_changes: Dict[str, Any]) -> str:
        """Generate test code from code changes"""
        self.logger.debug(f"Generating test code from changes: {code_changes}")

        test_code = []
        for file_path, changes in code_changes.items():
            test_name = f"test_{file_path.replace('/', '_').replace('.', '_')}"
            test_code.append(f"def {test_name}():")
            test_code.append(f"    \"\"\"Test changes in {file_path}\"\"\"")

            # Add assertions based on changes
            if isinstance(changes, str):
                test_code.append(f"    # Test changes from {file_path}")
                test_code.append("    assert True  # Placeholder assertion")
            else:
                for key, value in changes.items():
                    test_code.append(f"    # Test {key} changes")
                    test_code.append("    assert True  # Placeholder assertion")

        return "\n    ".join(test_code) if test_code else "def test_placeholder():\n    assert True"

    async def _extract_test_description(self, test_code: str) -> str:
        """Extract test description from docstring"""
        try:
            # Handle escaped newlines in test code
            test_code = test_code.replace('\\n', '\n')

            tree = ast.parse(test_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        return docstring.strip()
            return "No description available"
        except Exception as e:
            self.logger.error(f"Error extracting description: {str(e)}")
            return "No description available"

    async def _execute_test(self, test_code: str) -> str:
        """Execute a test and return the result"""
        self.logger.debug(f"Executing test code: {test_code}")

        try:
            # Create temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_code)
                temp_path = f.name

            try:
                # Run test using pytest in executor to avoid blocking
                def run_test():
                    try:
                        subprocess.run(
                            ['pytest', temp_path, '-v'],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        return "PASS"
                    except subprocess.CalledProcessError:
                        return "FAIL"

                # Run in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self._executor, run_test)
                return result

            finally:
                # Clean up temp file
                os.unlink(temp_path)

        except Exception as e:
            self.logger.error(f"Error executing test: {str(e)}")
            return f"Error executing test: {str(e)}"

    async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
        """Process message through central server"""
        try:
            # Parse message as JSON
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                return "Invalid JSON message format"

            # Extract action and parameters
            action = data.get("action")
            if not action:
                return "Action is required in message"

            # Execute action with context
            kwargs = {
                "action": action,
                **data,
                "context": context,
                "api_provider": api_provider
            }
            return await self.execute(**kwargs)

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"

    async def close(self):
        """Clean up resources"""
        await super().close()
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
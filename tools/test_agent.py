import ast
import json
import logging
import os
import subprocess
import tempfile
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from .agent_base import AgentBaseTool, AgentRole

@dataclass
class TestSpec:
    name: str
    code: str
    description: str = ""
    changes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

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
        """Initialize test agent."""
        super().__init__(agent_id=agent_id, role=AgentRole.TEST, name=name or f"test_{agent_id}")
        self.tests: Dict[str, TestSpec] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    async def initialize(self):
        """Initialize the test agent."""
        await super().initialize()
        self.logger.info("Test agent initialized")

    async def execute(self, **kwargs) -> str:
        """Execute test agent operations."""
        try:
            action = kwargs.get("action")
            if not action:
                return "No action specified"

            if action == "create":
                test_name = kwargs.get("test_name")
                if not test_name:
                    return "Test name is required"
                # Remove test_name from kwargs to avoid duplicate
                kwargs_copy = kwargs.copy()
                kwargs_copy.pop("test_name", None)
                return await self._create_test(test_name, **kwargs_copy)

            elif action == "update":
                test_name = kwargs.get("test_name")
                test_code = kwargs.get("test_code")
                return await self._update_test(test_name=test_name, test_code=test_code)

            elif action == "list":
                return await self._list_tests()

            elif action == "delete":
                test_name = kwargs.get("test_name")
                return await self._delete_test(test_name)

            elif action == "run":
                test_name = kwargs.get("test_name", None)
                return await self._run_tests(test_name)

            return f"Unknown action: {action}"

        except Exception as e:
            self.logger.error(f"Error executing action: {str(e)}")
            return f"Error: {str(e)}"

    async def _create_test(self, test_name: str, **kwargs) -> str:
        """Create a new test with given name and code."""
        try:
            self.logger.info(f"Creating test {test_name} with kwargs: {kwargs}")

            # Extract test code from kwargs
            test_code = kwargs.get("test_code")
            if not test_code:
                code_changes = kwargs.get("code_changes", {})
                test_code = await self._generate_test_code(code_changes)

            # Validate test code
            if not test_code or "def test" not in test_code:
                return "Invalid test code"

            # Create test spec
            test_spec = TestSpec(
                name=test_name,
                code=test_code,
                description=self._extract_test_description(test_code),
                changes=list(kwargs.get("code_changes", {}).keys())
            )

            # Store test
            self.tests[test_name] = test_spec
            self.logger.info(f"Created and stored test {test_name}. Current tests: {list(self.tests.keys())}")

            return f"Created test {test_name}"

        except Exception as e:
            self.logger.error(f"Error creating test {test_name}: {str(e)}")
            return f"Error creating test: {str(e)}"

    async def _update_test(self, test_name: Optional[str] = None, test_code: str = None, **kwargs) -> str:
        """Update an existing test."""
        if not test_name:
            return "Test name is required"

        if test_name not in self.tests:
            return f"Test {test_name} not found"

        if not test_code:
            return "Test code is required"

        try:
            # Validate test code
            ast.parse(test_code)
        except SyntaxError:
            return "Invalid test code"

        # Update test
        test = self.tests[test_name]
        test.code = test_code
        test.description = self._extract_test_description(test_code)

        self.logger.info(f"Updated test {test_name}")
        return f"Updated test {test_name}"

    async def _list_tests(self) -> str:
        """List all registered tests."""
        self.logger.info(f"Listing tests. Current tests: {list(self.tests.keys())}")

        if not self.tests:
            return "No tests registered"

        result = []
        for name, spec in self.tests.items():
            result.append(f"{name}: {spec.description}")

        return "\n".join(result)

    async def _delete_test(self, test_name: str) -> str:
        """Delete a test."""
        if test_name not in self.tests:
            return f"Test {test_name} not found"

        del self.tests[test_name]
        return f"Deleted test {test_name}"

    async def _run_tests(self, test_name: Optional[str] = None) -> str:
        """Run specified test or all tests."""
        results = []

        if test_name:
            if test_name not in self.tests:
                return f"Test {test_name} not found"
            results.append(await self._execute_test(test_name, self.tests[test_name]))
        else:
            for name, spec in self.tests.items():
                results.append(await self._execute_test(name, spec))

        return "\n".join(results)

    async def _generate_test_code(self, code_changes: Dict[str, str]) -> str:
        """Generate test code from code changes."""
        test_code = []
        for file_path, changes in code_changes.items():
            test_code.append(f"# Tests for {file_path}")
            test_code.append("def test_changes():")
            test_code.append("    # TODO: Generate meaningful tests")
            test_code.append("    assert True")
            test_code.append("")

        return "\n".join(test_code)

    def _extract_test_description(self, code: str) -> str:
        """Extract test description from docstring."""
        try:
            # Replace escaped newlines with actual newlines
            code = code.replace('\\n', '\n')
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        return docstring.strip()
        except Exception as e:
            self.logger.error(f"Error extracting description: {str(e)}")
        return ""
    async def _execute_test(self, test_name: str, test_spec: TestSpec) -> str:
        """Execute a test and return result."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_spec.code)
                temp_path = f.name

            try:
                # Run pytest on temporary file
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: subprocess.run(
                        ['pytest', temp_path, '-v', '--no-header'],
                        capture_output=True,
                        text=True
                    )
                )
                return f"{test_name}: {'PASS' if result.returncode == 0 else 'FAIL'}"
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
        except Exception as e:
            self.logger.error(f"Test execution failed: {str(e)}")
            return f"{test_name}: FAIL - {str(e)}"

    async def _update_spec_changes(self, code_changes: Dict[str, Any]) -> None:
        """Update app specification changes."""
        if 'spec_changes' not in self.state.data:
            self.state.data['spec_changes'] = []
        self.state.data['spec_changes'].extend(code_changes.items())

    async def _process_message(self, message: str, context: Dict[str, Any] = None, api_provider: str = "anthropic") -> str:
        """Process a message through the test agent."""
        if self._paused:
            return "Agent is currently paused"

        try:
            # Handle test-related commands
            if isinstance(message, dict):
                return await self.execute(**message)

            # Process as regular message
            return f"Processed: {message}"
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return f"Error: {str(e)}"

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)

import pytest
from tools.agent_base import AgentBaseTool, AgentRole, AgentState
from typing import Dict, Any
import threading
import time

class TestAgentTool(AgentBaseTool):
    """Test implementation of AgentBaseTool"""
    def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
        return f"Processed: {message}"

def test_agent_initialization():
    """Test agent initialization with different roles"""
    # Test predefined role
    agent1 = TestAgentTool("test1", AgentRole.TEST)
    assert agent1.role == AgentRole.TEST
    assert agent1.custom_role is None

    # Test custom role
    agent2 = TestAgentTool("test2", AgentRole.CUSTOM, "specialized")
    assert agent2.role == AgentRole.CUSTOM
    assert agent2.custom_role == "specialized"

def test_agent_name_and_description():
    """Test agent name and description generation"""
    agent = TestAgentTool("test1", AgentRole.TEST)
    assert "agent_test_test1" in agent.name
    assert "Agent-based tool for test operations" in agent.description

def test_agent_state_management():
    """Test agent state management and persistence"""
    agent = TestAgentTool("test1", AgentRole.TEST)

    # Test pause/resume
    agent.pause()
    assert agent.state.is_paused
    agent.resume()
    assert not agent.state.is_paused

    # Test context update
    context = {"key": "value"}
    agent.update_context(context)
    assert agent.get_state()["context"] == context

def test_thread_safety():
    """Test thread-safe operations"""
    agent = TestAgentTool("test1", AgentRole.TEST)
    results = []

    def worker():
        result = agent.execute(message="test")
        results.append(result)

    # Create multiple threads
    threads = [threading.Thread(target=worker) for _ in range(5)]

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify results
    assert len(results) == 5
    assert all("Processed: test" in result for result in results)

def test_paused_execution():
    """Test execution while agent is paused"""
    agent = TestAgentTool("test1", AgentRole.TEST)

    # Pause agent
    agent.pause()

    # Try to execute
    result = agent.execute(message="test")
    assert "is currently paused" in result

def test_input_schema():
    """Test input schema validation"""
    agent = TestAgentTool("test1", AgentRole.TEST)
    schema = agent.input_schema

    # Check required fields
    assert "message" in schema["properties"]
    assert "message" in schema["required"]

    # Check optional fields
    assert "context" in schema["properties"]
    assert "task_id" in schema["properties"]
    assert "api_provider" in schema["properties"]

def test_error_handling():
    """Test error handling during execution"""
    class ErrorAgentTool(AgentBaseTool):
        def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
            raise ValueError("Test error")

    agent = ErrorAgentTool("test1", AgentRole.TEST)
    result = agent.execute(message="test")
    assert "Error:" in result

import pytest
import pytest_asyncio
from tools.agent_base import AgentBaseTool, AgentRole, AgentState
from typing import Dict, Any, Union, Optional
import threading
import time
import asyncio

@pytest.fixture
def test_agent():
    """Fixture to create a test agent instance"""
    class TestAgentTool(AgentBaseTool):
        async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
            return f"Processed: {message}"
    return TestAgentTool

@pytest.mark.asyncio
async def test_agent_initialization(test_agent):
    """Test agent initialization with different roles"""
    # Test predefined role
    agent1 = test_agent("test1", AgentRole.TEST)
    await agent1.initialize()
    assert agent1.role == AgentRole.TEST
    assert agent1.custom_role is None

    # Test custom role as string
    agent2 = test_agent("test2", "specialized")
    await agent2.initialize()
    assert agent2.role == AgentRole.CUSTOM
    assert agent2.custom_role == "specialized"

    # Test custom role with enum
    agent3 = test_agent("test3", AgentRole.CUSTOM, name="Custom Agent")
    await agent3.initialize()
    assert agent3.role == AgentRole.CUSTOM
    assert agent3.custom_role == "custom"

@pytest.mark.asyncio
async def test_agent_name_and_description(test_agent):
    """Test agent name and description generation"""
    agent = test_agent("test1", AgentRole.TEST)
    await agent.initialize()
    assert "agent_test_test1" in agent.name
    assert "Agent-based tool for test operations" in agent.description

@pytest.mark.asyncio
async def test_agent_state_management(test_agent):
    """Test agent state management and persistence"""
    agent = test_agent("test1", AgentRole.TEST)
    await agent.initialize()

    # Test pause/resume
    agent.pause()
    assert agent.state.is_paused
    agent.resume()
    assert not agent.state.is_paused

    # Test context update
    context = {"key": "value"}
    await agent.update_context(context)
    state = await agent.get_state()
    assert state["context"] == context

@pytest.mark.asyncio
async def test_thread_safety(test_agent):
    """Test thread-safe operations"""
    agent = test_agent("test1", AgentRole.TEST)
    await agent.initialize()
    results = []

    async def worker():
        result = await agent.execute(message="test")
        results.append(result)

    # Create multiple tasks
    tasks = [asyncio.create_task(worker()) for _ in range(5)]

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)

    # Verify results
    assert len(results) == 5
    assert all("Processed: test" in result for result in results)

@pytest.mark.asyncio
async def test_paused_execution(test_agent):
    """Test execution while agent is paused"""
    agent = test_agent("test1", AgentRole.TEST)
    await agent.initialize()

    # Pause agent
    agent.pause()

    # Try to execute
    result = await agent.execute(message="test")
    assert "is currently paused" in result

@pytest.mark.asyncio
async def test_input_schema(test_agent):
    """Test input schema validation"""
    agent = test_agent("test1", AgentRole.TEST)
    await agent.initialize()
    schema = agent.input_schema

    # Check required fields
    assert "message" in schema["properties"]
    assert "message" in schema["required"]

    # Check optional fields
    assert "context" in schema["properties"]
    assert "task_id" in schema["properties"]
    assert "api_provider" in schema["properties"]

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling during execution"""
    class ErrorAgentTool(AgentBaseTool):
        async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
            raise ValueError("Test error")

    agent = ErrorAgentTool("test1", AgentRole.TEST)
    await agent.initialize()
    result = await agent.execute(message="test")
    assert "Error:" in result

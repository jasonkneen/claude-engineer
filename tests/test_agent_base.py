import pytest
import pytest_asyncio
from tools.agent_base import AgentBaseTool, AgentRole, AgentState
import logging
from typing import Dict, Any, Optional, Union
import asyncio

class TestAgentTool(AgentBaseTool):
    """Test implementation of AgentBaseTool."""
    def __init__(self, agent_id: str = "test1", role: Union[AgentRole, str] = AgentRole.TEST, name: Optional[str] = None):
        super().__init__(agent_id=agent_id, role=role, name=name)
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize async components."""
        await super().initialize()
        async with self._lock:
            if 'tests' not in self.state.data:
                self.state.data['tests'] = {}
            self.tests = self.state.data['tests']

    async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
        if self._paused:
            return "Agent is currently paused"
        return f"Processed: {message}"

@pytest_asyncio.fixture
async def test_agent():
    """Create test agent fixture."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initialization."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()
    assert agent.role == AgentRole.TEST
    assert agent.agent_id == "test1"
    assert isinstance(agent.state, AgentState)
    assert agent._lock is not None

@pytest.mark.asyncio
async def test_agent_name_and_description():
    """Test agent name and description generation."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()
    assert "agent_test_test1" in agent.name
    assert "TestAgentTool" in agent.description

@pytest.mark.asyncio
async def test_agent_state_management():
    """Test agent state management and persistence."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()

    # Test pause/resume
    await agent.pause()
    assert agent._paused
    result = await agent.execute(message="test", context={}, api_provider="test")
    assert "Agent is currently paused" in result

    await agent.resume()
    assert not agent._paused
    result = await agent.execute(message="test", context={}, api_provider="test")
    assert "Processed: test" in result

    # Test context update
    context = {"key": "value"}
    await agent.update_context(context)
    state = await agent.get_state()
    assert state["context"] == context

@pytest.mark.asyncio
async def test_thread_safety():
    """Test thread-safe operations."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()
    results = []

    async def worker():
        """Test worker function."""
        await agent.update_context({"key": "value"})
        state = await agent.get_state()
        results.append(state["context"]["key"])

    # Run multiple workers concurrently
    tasks = [asyncio.create_task(worker()) for _ in range(5)]
    await asyncio.gather(*tasks)

    # Verify all operations completed successfully
    assert len(results) == 5
    assert all(r == "value" for r in results)

@pytest.mark.asyncio
async def test_paused_execution():
    """Test execution while agent is paused."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()

    # Pause agent
    await agent.pause()

    # Try to execute
    result = await agent.execute(message="test", context={}, api_provider="test")
    assert "Agent is currently paused" in result

@pytest.mark.asyncio
async def test_input_schema():
    """Test input schema validation."""
    agent = TestAgentTool(agent_id="test1", role=AgentRole.TEST)
    await agent.initialize()
    schema = agent.input_schema

    # Check required fields
    assert "message" in schema["properties"]
    assert "message" in schema["required"]

    # Check optional fields
    assert "context" in schema["properties"]
    assert "api_provider" in schema["properties"]

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling during execution."""
    class ErrorAgentTool(AgentBaseTool):
        def __init__(self, agent_id: str = "test1", role: Union[AgentRole, str] = AgentRole.TEST):
            super().__init__(agent_id=agent_id, role=role)
            self.logger = logging.getLogger(__name__)

        async def _process_message(self, message: str, context: Dict[str, Any], api_provider: str) -> str:
            raise ValueError("Test error")

    agent = ErrorAgentTool("test1", AgentRole.TEST)
    await agent.initialize()
    result = await agent.execute(message="test", context={}, api_provider="test")
    assert "Error:" in result

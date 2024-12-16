import pytest
import pytest_asyncio
from tools.agent_manager import AgentManagerTool, AgentConfig
from tools.agent_base import AgentRole
from unittest.mock import Mock, patch, AsyncMock
import anthropic
import openai

@pytest_asyncio.fixture
async def agent_manager():
    """Create agent manager fixture."""
    # Mock API clients
    with patch('anthropic.Anthropic', return_value=AsyncMock()) as mock_anthropic, \
         patch('openai.Client', return_value=AsyncMock()) as mock_openai, \
         patch.dict('os.environ', {
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'OPENAI_API_KEY': 'test_openai_key'
         }):
        manager = AgentManagerTool()
        await manager.setup()  # Initialize the manager
        yield manager
        await manager.close()

@pytest.mark.asyncio
async def test_agent_creation(agent_manager):
    """Test agent creation with various roles"""
    # Test predefined role as string
    result = await agent_manager.execute(
        action="create",
        agent_id="test1",
        role="TEST"
    )
    assert "Created agent test1" in result
    assert "test1" in agent_manager.agents
    assert agent_manager.agents["test1"].role == AgentRole.TEST

    # Test custom role as string
    result = await agent_manager.execute(
        action="create",
        agent_id="test2",
        role="specialized"
    )
    assert "Created agent test2" in result
    assert "test2" in agent_manager.agents
    assert agent_manager.agents["test2"].role == AgentRole.CUSTOM
    assert agent_manager.agents["test2"].custom_role == "specialized"

@pytest.mark.asyncio
async def test_agent_lifecycle(agent_manager):
    """Test agent pause, resume, and deletion"""
    # Create agent
    await agent_manager.execute(
        action="create",
        agent_id="test1",
        role="TEST"
    )

    # Test pause
    result = await agent_manager.execute(
        action="pause",
        agent_id="test1"
    )
    assert "Paused agent test1" in result
    assert agent_manager.agents["test1"].state.is_paused

    # Test resume
    result = await agent_manager.execute(
        action="resume",
        agent_id="test1"
    )
    assert "Resumed agent test1" in result
    assert not agent_manager.agents["test1"].state.is_paused

    # Test delete
    result = await agent_manager.execute(
        action="delete",
        agent_id="test1"
    )
    assert "Deleted agent test1" in result
    assert "test1" not in agent_manager.agents

@pytest.mark.asyncio
async def test_list_agents(agent_manager):
    """Test agent listing"""
    # Test empty list
    result = await agent_manager.execute(action="list")
    assert "No agents registered" in result

    # Create some agents
    await agent_manager.execute(
        action="create",
        agent_id="test1",
        role="TEST"
    )
    await agent_manager.execute(
        action="create",
        agent_id="test2",
        role="specialized"
    )

    # Test list with agents
    result = await agent_manager.execute(action="list")
    assert "test1" in result
    assert "test2" in result
    assert "Role: TEST" in result
    assert "Role: specialized" in result

@pytest.mark.asyncio
async def test_error_handling(agent_manager):
    """Test error handling"""
    # Test invalid action
    result = await agent_manager.execute(action="invalid")
    assert "Unknown action" in result

    # Test invalid role
    result = await agent_manager.execute(
        action="create",
        agent_id="test1",
        role="invalid"
    )
    assert "Invalid role" in result

    # Test missing agent
    result = await agent_manager.execute(
        action="pause",
        agent_id="missing"
    )
    assert "not found" in result

@pytest.mark.asyncio
async def test_cleanup(agent_manager):
    """Test resource cleanup"""
    await agent_manager.close()
    assert agent_manager._executor._shutdown

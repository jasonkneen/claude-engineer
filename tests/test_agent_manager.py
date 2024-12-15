import pytest
from tools.agent_manager import AgentManagerTool, AgentConfig
from tools.agent_base import AgentRole
from unittest.mock import Mock, patch

@pytest.fixture
def agent_manager():
    with patch('openai.Client'), patch('anthropic.Anthropic'):
        yield AgentManagerTool()

def test_agent_creation(agent_manager):
    """Test agent creation with various roles"""
    # Test predefined role
    result = agent_manager.execute(
        action="create",
        agent_id="test1",
        role="test"
    )
    assert "Created agent test1" in result
    assert "test1" in agent_manager.agents

    # Test custom role
    result = agent_manager.execute(
        action="create",
        agent_id="test2",
        role="custom",
        custom_role="specialized"
    )
    assert "Created agent test2" in result
    assert "test2" in agent_manager.agents

def test_agent_lifecycle(agent_manager):
    """Test agent pause, resume, and deletion"""
    # Create agent
    agent_manager.execute(
        action="create",
        agent_id="test1",
        role="test"
    )

    # Test pause
    result = agent_manager.execute(
        action="pause",
        agent_id="test1"
    )
    assert "Paused agent test1" in result
    assert agent_manager.agents["test1"].state.is_paused

    # Test resume
    result = agent_manager.execute(
        action="resume",
        agent_id="test1"
    )
    assert "Resumed agent test1" in result
    assert not agent_manager.agents["test1"].state.is_paused

    # Test delete
    result = agent_manager.execute(
        action="delete",
        agent_id="test1"
    )
    assert "Deleted agent test1" in result
    assert "test1" not in agent_manager.agents

def test_list_agents(agent_manager):
    """Test agent listing"""
    # Test empty list
    result = agent_manager.execute(action="list")
    assert "No agents registered" in result

    # Create some agents
    agent_manager.execute(
        action="create",
        agent_id="test1",
        role="test"
    )
    agent_manager.execute(
        action="create",
        agent_id="test2",
        role="context"
    )

    # Test list with agents
    result = agent_manager.execute(action="list")
    assert "test1" in result
    assert "test2" in result
    assert "Role: test" in result
    assert "Role: context" in result

def test_error_handling(agent_manager):
    """Test error handling"""
    # Test invalid action
    result = agent_manager.execute(action="invalid")
    assert "Unknown action" in result

    # Test invalid role
    result = agent_manager.execute(
        action="create",
        agent_id="test1",
        role="invalid"
    )
    assert "Invalid role" in result

    # Test missing agent
    result = agent_manager.execute(
        action="pause",
        agent_id="missing"
    )
    assert "not found" in result

@pytest.mark.asyncio
async def test_cleanup(agent_manager):
    """Test resource cleanup"""
    await agent_manager.close()
    assert agent_manager._executor._shutdown

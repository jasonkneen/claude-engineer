import pytest
from tools.context_manager import ContextManagerTool, CompressionRule
from unittest.mock import Mock, patch

@pytest.fixture
def context_manager():
    return ContextManagerTool()

def test_context_compression(context_manager):
    """Test context compression with default rules"""
    # Test basic compression
    result = context_manager.execute(
        action="compress",
        context_id="test1",
        context={
            "text": "This is a test message with some redundant words."
        }
    )
    assert "Compressed context test1" in result

    # Verify compression results
    result = context_manager.execute(
        action="get",
        context_id="test1"
    )
    compressed = eval(result)  # Safe since we control the input
    assert "test1" in context_manager.contexts
    assert len(compressed["text"]) < len("This is a test message with some redundant words.")

def test_context_optimization(context_manager):
    """Test context optimization"""
    # Add redundant context
    context_manager.execute(
        action="compress",
        context_id="test1",
        context={
            "msg1": "Hello world",
            "msg2": "Hello world",  # Redundant
            "msg3": "Different message"
        }
    )

    # Test optimization
    result = context_manager.execute(
        action="optimize",
        context_id="test1"
    )
    assert "Optimized context test1" in result

    # Verify optimization
    result = context_manager.execute(
        action="get",
        context_id="test1"
    )
    optimized = eval(result)  # Safe since we control the input
    assert len(optimized) < 3  # Should have removed redundant entry

def test_compression_rules(context_manager):
    """Test adding and using custom compression rules"""
    # Add custom rule
    result = context_manager.execute(
        action="add_rule",
        rule={
            "pattern": r"\b(hello|hi)\b",
            "replacement": "greeting",
            "priority": 1
        }
    )
    assert "Added compression rule" in result

    # Test custom rule
    result = context_manager.execute(
        action="compress",
        context_id="test1",
        context={
            "text": "Hello there! Hi everyone!"
        }
    )
    assert "Compressed context test1" in result

    # Verify custom rule application
    result = context_manager.execute(
        action="get",
        context_id="test1"
    )
    compressed = eval(result)  # Safe since we control the input
    assert "greeting" in compressed["text"].lower()

def test_context_management(context_manager):
    """Test context management operations"""
    # Test missing context
    result = context_manager.execute(
        action="get",
        context_id="missing"
    )
    assert "not found" in result

    # Test clear context
    context_manager.execute(
        action="compress",
        context_id="test1",
        context={"text": "test"}
    )
    result = context_manager.execute(
        action="clear",
        context_id="test1"
    )
    assert "Cleared context test1" in result
    assert "test1" not in context_manager.contexts

def test_error_handling(context_manager):
    """Test error handling"""
    # Test invalid action
    result = context_manager.execute(
        action="invalid"
    )
    assert "Unknown action" in result

    # Test invalid regex pattern
    result = context_manager.execute(
        action="add_rule",
        rule={
            "pattern": "[invalid",
            "replacement": "test"
        }
    )
    assert "Invalid regex pattern" in result

@pytest.mark.asyncio
async def test_cleanup(context_manager):
    """Test resource cleanup"""
    await context_manager.close()
    assert context_manager._executor._shutdown

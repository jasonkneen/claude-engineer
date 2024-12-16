import pytest
from tools.test_agent import TestAgentTool, TestSpec
from unittest.mock import Mock, patch

@pytest.fixture
def test_agent():
    return TestAgentTool()

def test_test_creation(test_agent):
    """Test test creation with code changes"""
    # Test with code changes
    result = test_agent.execute(
        action="create",
        test_name="test1",
        code_changes={
            "file1.py": "def test(): pass"
        }
    )
    assert "Created test test1" in result
    assert "test1" in test_agent.tests

    # Test with explicit test code
    result = test_agent.execute(
        action="create",
        test_name="test2",
        test_code="def test_example(): assert True"
    )
    assert "Created test test2" in result
    assert "test2" in test_agent.tests

def test_test_updates(test_agent):
    """Test test updates"""
    # Create test
    test_agent.execute(
        action="create",
        test_name="test1",
        test_code="def test_example(): assert True"
    )

    # Update test
    result = test_agent.execute(
        action="update",
        test_name="test1",
        test_code="def test_example(): assert 1 == 1"
    )
    assert "Updated test test1" in result
    assert "assert 1 == 1" in test_agent.tests["test1"].code

def test_test_listing(test_agent):
    """Test test listing"""
    # Test empty list
    result = test_agent.execute(action="list")
    assert "No tests registered" in result

    # Create some tests
    test_agent.execute(
        action="create",
        test_name="test1",
        test_code="def test1(): \"\"\"Test 1\"\"\"\\nassert True"
    )
    test_agent.execute(
        action="create",
        test_name="test2",
        test_code="def test2(): \"\"\"Test 2\"\"\"\\nassert True"
    )

    # Test list with tests
    result = test_agent.execute(action="list")
    assert "test1" in result
    assert "test2" in result
    assert "Test 1" in result
    assert "Test 2" in result

def test_test_deletion(test_agent):
    """Test test deletion"""
    # Create test
    test_agent.execute(
        action="create",
        test_name="test1",
        test_code="def test_example(): assert True"
    )

    # Delete test
    result = test_agent.execute(
        action="delete",
        test_name="test1"
    )
    assert "Deleted test test1" in result
    assert "test1" not in test_agent.tests

def test_test_execution(test_agent):
    """Test test execution"""
    # Create valid test
    test_agent.execute(
        action="create",
        test_name="test1",
        test_code="def test_valid(): assert True"
    )

    # Create invalid test
    test_agent.execute(
        action="create",
        test_name="test2",
        test_code="def test_invalid(): invalid syntax"
    )

    # Run specific test
    result = test_agent.execute(
        action="run",
        test_name="test1"
    )
    assert "PASS" in result

    # Run all tests
    result = test_agent.execute(action="run")
    assert "test1" in result
    assert "test2" in result
    assert "PASS" in result
    assert "FAIL" in result

def test_error_handling(test_agent):
    """Test error handling"""
    # Test invalid action
    result = test_agent.execute(action="invalid")
    assert "Unknown action" in result

    # Test missing test
    result = test_agent.execute(
        action="update",
        test_name="missing",
        test_code="def test(): pass"
    )
    assert "not found" in result

    # Test invalid test code
    result = test_agent.execute(
        action="create",
        test_name="test1",
        test_code="invalid syntax"
    )
    assert "Invalid test code" in result

@pytest.mark.asyncio
async def test_cleanup(test_agent):
    """Test resource cleanup"""
    await test_agent.close()
    assert test_agent._executor._shutdown

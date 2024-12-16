import pytest
import pytest_asyncio
from ce3 import Assistant
from config import Config
import asyncio
from unittest.mock import AsyncMock, patch

@pytest_asyncio.fixture
async def assistant():
    """Create test assistant fixture."""
    config = Config()
    config.agent_id = "test_assistant"
    config.role = "TEST"  # Use TEST role for testing
    config.test_mode = True  # Enable test mode

    # Create mock API router with async methods
    mock_router = AsyncMock()
    mock_router.setup = AsyncMock()
    mock_router.route_request = AsyncMock(return_value={
        "content": "Test response",
        "usage": {"total_tokens": 10},
        "model": "test-model",
        "role": "assistant"
    })

    # Mock API router class
    with patch('ce3.APIRouter', return_value=mock_router):
        assistant = Assistant(config)
        await assistant.initialize()  # Ensure proper async initialization
        return assistant

@pytest.mark.asyncio
async def test_assistant_chat_coroutine(assistant):
    """Test that Assistant.chat coroutine is properly awaited."""
    test_input = "Hello, this is a test message"

    # Test direct chat call
    response = await assistant.chat(test_input)
    assert isinstance(response, str)
    assert len(response) > 0

    # Test chat in event loop
    async def chat_in_loop():
        return await assistant.chat(test_input)

    response = await chat_in_loop()
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_assistant_chat_from_app(assistant):
    """Test Assistant.chat when called from app context."""
    from app import app

    # Create mock assistant for app context
    mock_assistant = AsyncMock()
    mock_assistant.chat = AsyncMock(return_value="Test response from app")
    mock_assistant.initialize = AsyncMock()

    # Mock Assistant class in app context
    with patch('app.Assistant', return_value=mock_assistant):
        test_client = app.test_client()
        test_message = {
            "message": "Test message from app context",
            "agent_id": "test_agent"
        }

        response = await test_client.post('/chat', json=test_message)
        assert response.status_code == 200
        data = await response.get_json()
        assert 'response' in data
        assert isinstance(data['response'], str)

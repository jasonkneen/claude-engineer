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
    config.test_mode = True  # Enable test mode to bypass API keys

    # Create mock API router
    mock_router = AsyncMock()
    mock_router.route_request = AsyncMock(return_value={
        "content": [{"text": "Test response"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "claude-3-sonnet-20240229",
        "role": "assistant"
    })
    mock_router._setup_clients = AsyncMock(return_value=True)

    with patch('ce3.APIRouter', return_value=mock_router):
        assistant = Assistant(config)
        await assistant.initialize()  # Ensure proper async initialization
        return assistant

@pytest.mark.asyncio
async def test_assistant_chat_coroutine(assistant):
    """Test that Assistant.chat coroutine is properly awaited."""
    test_input = "Hello, this is a test message"

    # Mock API router response
    mock_router = AsyncMock()
    mock_router.route_request = AsyncMock(return_value={
        "content": [{"text": "Test response"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "claude-3-sonnet-20240229",
        "role": "assistant"
    })
    mock_router._setup_clients = AsyncMock(return_value=True)

    with patch('ce3.APIRouter', return_value=mock_router):
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

    # Create a properly awaitable mock assistant
    mock_assistant = AsyncMock()
    mock_assistant.chat = AsyncMock(return_value="Test response from app")
    mock_assistant.initialize = AsyncMock(return_value=mock_assistant)
    mock_assistant._initialized = True

    # Create an async mock class that returns our mock instance
    async def async_init(config):
        return mock_assistant

    mock_assistant_class = AsyncMock()
    mock_assistant_class.return_value = mock_assistant
    mock_assistant_class.__call__ = AsyncMock(side_effect=async_init)
    mock_assistant_class.__await__ = AsyncMock(side_effect=lambda: async_init(None).__await__())

    with patch('app.Assistant', mock_assistant_class):
        await app.startup()  # Initialize assistant

        # Test chat functionality
        async with app.app_context():
            response = await app.assistant.chat("Test message")
            assert response == "Test response from app"
            mock_assistant.chat.assert_called_once_with("Test message")

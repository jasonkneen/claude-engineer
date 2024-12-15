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

    # Mock API calls
    with patch('ce3.APIRouter') as mock_router:
        mock_router.return_value.route_request = AsyncMock(return_value="Test response")
        assistant = Assistant(config)
        await assistant.initialize()  # Ensure proper async initialization
        await assistant.initialize_tools()  # Initialize tools with proper parameters
        return assistant

@pytest.mark.asyncio
async def test_assistant_chat_coroutine(assistant):
    """Test that Assistant.chat coroutine is properly awaited."""
    test_input = "Hello, this is a test message"

    # Mock API router response
    with patch('ce3.APIRouter') as mock_router:
        mock_router.return_value.route_request = AsyncMock(return_value="Test response")

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

    # Mock API router and assistant in app context
    with patch('app.Assistant') as mock_assistant_class:
        mock_assistant = AsyncMock()
        mock_assistant.chat = AsyncMock(return_value="Test response from app")
        mock_assistant_class.return_value = mock_assistant

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

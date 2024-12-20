import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from api_router import APIRouter, APIConfig, APIProvider
import anthropic
import openai

@pytest_asyncio.fixture
async def api_router():
    """Create API router fixture."""
    router = APIRouter(test_mode=True)  # Enable test mode
    await router._setup_clients()  # Initialize clients
    return router

@pytest.fixture
def mock_anthropic_response():
    return Mock(
        content=[{"text": "Test response"}],
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        model="claude-3-sonnet-20240229"
    )

@pytest.fixture
def mock_openai_response():
    return Mock(
        choices=[Mock(message=Mock(content="Test response"))],
        usage={"prompt_tokens": 10, "completion_tokens": 20},
        model="gpt-4-turbo-preview"
    )

@pytest.mark.asyncio
async def test_anthropic_request(api_router, mock_anthropic_response):
    """Test Anthropic API request routing"""
    messages = [{"role": "user", "content": "Test message"}]
    config = APIConfig(
        model="claude-3-sonnet-20240229",
        max_tokens=100,
        temperature=0.7
    )

    with patch.object(
        api_router.anthropic_client.messages,
        'create',
        return_value=mock_anthropic_response
    ):
        response = await api_router.route_request(
            provider="anthropic",
            messages=messages,
            config=config
        )

        assert response["content"] == mock_anthropic_response.content
        assert response["usage"] == mock_anthropic_response.usage
        assert response["model"] == mock_anthropic_response.model

@pytest.mark.asyncio
async def test_openai_request(api_router, mock_openai_response):
    """Test OpenAI API request routing"""
    messages = [{"role": "user", "content": "Test message"}]
    config = APIConfig(
        model="gpt-4-turbo-preview",
        max_tokens=100,
        temperature=0.7
    )

    # Create event loop
    loop = asyncio.get_event_loop()

    with patch.object(
        api_router.openai_client.chat.completions,
        'create',
        return_value=mock_openai_response
    ):
        response = await api_router.route_request(
            provider="openai",
            messages=messages,
            config=config
        )

        assert response["content"] == mock_openai_response.choices[0].message.content
        assert response["usage"] == mock_openai_response.usage
        assert response["model"] == mock_openai_response.model

@pytest.mark.asyncio
async def test_invalid_provider(api_router):
    """Test invalid provider handling"""
    with pytest.raises(ValueError):
        await api_router.route_request(
            provider="invalid",
            messages=[{"role": "user", "content": "Test"}]
        )

@pytest.mark.asyncio
async def test_default_config(api_router):
    """Test default configuration"""
    messages = [{"role": "user", "content": "Test"}]

    with patch.object(
        api_router.anthropic_client.messages,
        'create',
        return_value=Mock(
            content=[{"text": "Test"}],
            usage={},
            model="claude-3-sonnet-20240229"
        )
    ):
        response = await api_router.route_request(
            provider="anthropic",
            messages=messages
        )
        assert response["model"] == "claude-3-sonnet-20240229"

@pytest.mark.asyncio
async def test_error_handling(api_router):
    """Test error handling"""
    messages = [{"role": "user", "content": "Test"}]

    # Re-initialize clients to ensure clean state
    await api_router._setup_clients()

    with patch.object(
        api_router.anthropic_client.messages,
        'create',
        side_effect=Exception("API Error")
    ):
        with pytest.raises(Exception) as exc_info:
            await api_router.route_request(
                provider="anthropic",
                messages=messages
            )

@pytest.mark.asyncio
async def test_cleanup(api_router):
    """Test resource cleanup"""
    await api_router.close()
    assert api_router._executor._shutdown

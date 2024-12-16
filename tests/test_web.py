import pytest
import pytest_asyncio
from quart import Quart
from quart.testing import QuartClient
import json
from app import app as quart_app
from unittest.mock import AsyncMock, patch, MagicMock
from tools.voice_tool import VoiceRole, VoiceTool
from tools.agent_base import AgentRole, AgentBaseTool
import asyncio
from werkzeug.datastructures import FileStorage
from io import BytesIO

@pytest_asyncio.fixture
async def voice_tool():
    """Create voice tool fixture."""
    tool = VoiceTool(agent_id="test_web_voice", role=VoiceRole.VOICE_CONTROL)
    await tool.initialize()
    return tool

@pytest_asyncio.fixture
async def app():
    """Create test app fixture."""
    app = quart_app
    app.config['TESTING'] = True

    # Mock assistant initialization
    mock_assistant = AsyncMock()
    mock_assistant.chat = AsyncMock(return_value="Test response")
    mock_assistant.tools = []
    mock_assistant.initialize = AsyncMock()

    # Create mock Assistant class with create classmethod
    class MockAssistant:
        @classmethod
        async def create(cls, config=None):
            return mock_assistant

    with patch('app.Assistant', MockAssistant):
        await app.startup()  # Initialize assistant
        return app

@pytest_asyncio.fixture
async def client(app):
    """Create test client fixture."""
    return app.test_client()

@pytest.mark.asyncio
@patch('app.assistant.chat', new_callable=AsyncMock)
async def test_dark_mode_toggle(mock_chat, client: QuartClient):
    """Test dark mode toggle functionality."""
    # Test getting initial dark mode state
    response = await client.get('/dark-mode')
    assert response.status_code == 200
    data = await response.get_json()
    assert 'enabled' in data

    # Test setting dark mode
    response = await client.post('/dark-mode',
                               json={'enabled': True})
    assert response.status_code == 200
    data = await response.get_json()
    assert data['enabled'] is True

    # Test setting light mode
    response = await client.post('/dark-mode',
                               json={'enabled': False})
    assert response.status_code == 200
    data = await response.get_json()
    assert data['enabled'] is False

@pytest.mark.asyncio
@patch('app.VoiceTool')
async def test_agent_status_display(mock_voice, client: QuartClient, voice_tool):
    """Test agent status display functionality."""
    mock_voice.return_value = voice_tool
    mock_voice.return_value.get_state = AsyncMock(return_value={
        'is_paused': False,
        'current_task': "Test task",
        'progress': 50,
        'task_history': ["Task 1", "Task 2"]
    })

    response = await client.get('/agent-status')
    assert response.status_code == 200
    data = await response.get_json()
    assert 'agents' in data
    assert isinstance(data['agents'], list)

    # Verify agent status structure
    if data['agents']:
        agent = data['agents'][0]
        assert 'id' in agent
        assert 'status' in agent
        assert 'current_task' in agent
        assert 'progress' in agent

@pytest.mark.asyncio
@patch('app.assistant.chat', new_callable=AsyncMock)
async def test_flow_creation(mock_chat, client: QuartClient):
    """Test flow creation functionality."""
    test_flow = {
        'name': 'Test Flow',
        'description': 'Test flow creation',
        'steps': [
            {'type': 'chat', 'content': 'Hello'},
            {'type': 'voice', 'content': 'Speak this'}
        ]
    }

    mock_chat.return_value = "Flow created successfully"

    response = await client.post('/create-flow',
                               json=test_flow)
    assert response.status_code == 200
    data = await response.get_json()
    assert 'flow_id' in data
    assert 'status' in data
    assert data['status'] == 'created'

@pytest.mark.asyncio
@patch('app.assistant.chat', new_callable=AsyncMock)
async def test_chat_interface(mock_chat, client: QuartClient):
    """Test chat interface functionality."""
    mock_chat.return_value = "Test response"

    test_message = {
        'message': 'Test chat message',
        'agent_id': 'test_agent'
    }

    response = await client.post('/chat',
                               json=test_message)
    assert response.status_code == 200
    data = await response.get_json()
    assert 'response' in data
    assert isinstance(data['response'], str)

@pytest.mark.asyncio
@patch('app.VoiceTool')
async def test_agent_configuration(mock_voice, client: QuartClient, voice_tool):
    """Test agent configuration interface."""
    mock_voice.return_value = voice_tool
    mock_voice.return_value.get_state = AsyncMock(return_value={
        'is_paused': False,
        'current_task': "Config task",
        'progress': 75,
        'task_history': ["Config 1", "Config 2"]
    })

    # Test getting agent config
    response = await client.get('/agent-config')
    assert response.status_code == 200
    data = await response.get_json()
    assert 'agents' in data

    # Test updating agent config
    test_config = {
        'agent_id': 'test_agent',
        'role': 'TEST_ROLE',
        'settings': {
            'voice_enabled': True,
            'auto_learn': True
        }
    }

    response = await client.post('/update-agent-config',
                               json=test_config)
    assert response.status_code == 200
    data = await response.get_json()
    assert 'status' in data
    assert data['status'] == 'success'

@pytest.mark.asyncio
async def test_voice_integration(client: QuartClient, voice_tool):
    """Test voice integration in web interface."""
    # Ensure testing mode is enabled
    client.app.config['TESTING'] = True

    # Test TTS endpoint
    test_text = "Testing voice output"
    response = await client.post('/speak',
                               json={'text': test_text})
    assert response.status_code == 200
    data = await response.get_json()
    assert 'audio_path' in data

    # Test STT endpoint
    with open('tests/test_audio.wav', 'wb') as f:
        f.write(b'test audio data')

    # Create proper file storage object
    with open('tests/test_audio.wav', 'rb') as f:
        file_data = f.read()

    file = FileStorage(
        stream=BytesIO(file_data),
        filename='test_audio.wav',
        content_type='audio/wav'
    )

    # Send request with proper file storage object
    response = await client.post(
        '/transcribe',
        files={'audio': file}
    )
    assert response.status_code == 200
    data = await response.get_json()
    assert 'text' in data

import pytest
import pytest_asyncio
import os
import tempfile
from unittest.mock import MagicMock
from tools.voice_tool import VoiceTool, VoiceRole

@pytest.fixture
def tts_engine(mocker):
    """Create mocked TTS engine fixture."""
    mock_engine = mocker.MagicMock()
    mock_engine.say = mocker.MagicMock()
    mock_engine.save_to_file = mocker.MagicMock()
    mock_engine.runAndWait = mocker.MagicMock()
    mock_engine.setProperty = mocker.MagicMock()
    mock_engine.getProperty = mocker.MagicMock(return_value=[])
    mocker.patch('pyttsx3.init', return_value=mock_engine)
    return mock_engine

@pytest_asyncio.fixture
async def voice_tool(tts_engine):
    """Create voice tool fixture with mocked TTS engine."""
    def mock_save_to_file(text, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(b'test audio content')
    tts_engine.save_to_file.side_effect = mock_save_to_file
    tool = VoiceTool(agent_id="test_tts", role=VoiceRole.VOICE_CONTROL)
    await tool.initialize_tts()
    yield tool
    # Cleanup any generated files
    audio_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'audio')
    if os.path.exists(audio_dir):
        for file in os.listdir(audio_dir):
            if file.startswith('test_tts_'):
                os.remove(os.path.join(audio_dir, file))

@pytest.fixture
def test_audio_file():
    """Create temporary test audio file."""
    _, temp_path = tempfile.mkstemp(suffix='.wav')
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)

@pytest.mark.asyncio
async def test_tts_basic_functionality(tts_engine, test_audio_file):
    """Test basic TTS engine functionality."""
    test_text = "Testing text to speech"

    # Mock save_to_file to create an empty file
    def mock_save_to_file(text, path):
        with open(path, 'wb') as f:
            f.write(b'test audio content')

    tts_engine.save_to_file.side_effect = mock_save_to_file
    tts_engine.save_to_file(test_text, test_audio_file)
    tts_engine.runAndWait()
    assert os.path.exists(test_audio_file)
    assert os.path.getsize(test_audio_file) > 0

@pytest.mark.asyncio
async def test_voice_tool_tts(voice_tool):
    """Test VoiceTool TTS functionality."""
    test_text = "Testing voice tool TTS"
    audio_path = await voice_tool.speak(test_text)
    assert os.path.exists(audio_path)
    assert os.path.getsize(audio_path) > 0
    if os.path.exists(audio_path):
        os.remove(audio_path)

@pytest.mark.asyncio
async def test_tts_with_different_texts(voice_tool):
    """Test TTS with various text inputs."""
    test_cases = [
        "Hello world",
        "This is a longer sentence to test text to speech capability",
        "Special characters: !@#$%^&*()",
        "Numbers 12345 and symbols @#$"
    ]

    for text in test_cases:
        audio_path = await voice_tool.speak(text)
        assert os.path.exists(audio_path)
        assert os.path.getsize(audio_path) > 0
        if os.path.exists(audio_path):
            os.remove(audio_path)

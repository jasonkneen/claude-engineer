import pytest
import pytest_asyncio
from tools.voice_tool import VoiceTool, VoiceRole
import os

@pytest_asyncio.fixture
async def voice_tool(mocker):
    """Create voice tool fixture with mocked TTS."""
    # Create a properties dict to track TTS engine state
    mock_voice = mocker.MagicMock()
    mock_voice.id = "mock_voice_1"

    properties = {
        'rate': 150,
        'volume': 0.8,
        'voices': [mock_voice]
    }

    # Mock TTS engine
    mock_tts = mocker.MagicMock()
    mock_tts.getProperty = mocker.MagicMock(side_effect=lambda prop: properties[prop])
    mock_tts.setProperty = mocker.MagicMock(side_effect=lambda prop, val: properties.__setitem__(prop, val))
    mock_tts.runAndWait = mocker.MagicMock()  # Add runAndWait mock
    mocker.patch('pyttsx3.init', return_value=mock_tts)

    tool = VoiceTool(agent_id="test_voice", role=VoiceRole.VOICE_CONTROL)
    await tool.initialize_tts()
    return tool

@pytest.mark.asyncio
async def test_voice_tool_initialization(voice_tool):
    assert voice_tool.agent_id == "test_voice"
    assert voice_tool.role == VoiceRole.VOICE_CONTROL
    assert voice_tool.tts_engine is not None
    assert voice_tool.stt_model is None

@pytest.mark.asyncio
async def test_tts_initialization(voice_tool):
    assert voice_tool.tts_engine is not None

@pytest.mark.asyncio
async def test_voice_properties(voice_tool):
    voices = await voice_tool.set_voice()
    assert isinstance(voices, list)

    await voice_tool.set_rate(200)
    await voice_tool.set_volume(0.8)

    assert voice_tool.tts_engine.getProperty('rate') == 200
    assert voice_tool.tts_engine.getProperty('volume') == 0.8

@pytest.mark.skipif(not os.path.exists("test_audio.wav"),
                    reason="Test audio file not found")
@pytest.mark.asyncio
async def test_speech_to_text(voice_tool):
    if os.path.exists("test_audio.wav"):
        voice_tool.initialize_stt()
        text = await voice_tool.transcribe("test_audio.wav")
        assert isinstance(text, str)

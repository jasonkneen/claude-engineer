import pytest
import pytest_asyncio
from tools.voice_tool import VoiceTool, VoiceRole
import os

@pytest_asyncio.fixture
async def voice_tool(mocker):
    """Create voice tool fixture with mocked TTS."""
    # Mock TTS engine
    mock_tts = mocker.MagicMock()
    mock_tts.save_to_file = mocker.MagicMock(side_effect=lambda text, path: open(path, 'wb').write(b'test audio'))
    mock_tts.runAndWait = mocker.MagicMock()

    # Mock properties with proper type handling
    properties = {'rate': 200, 'volume': 0.8}
    def get_property(prop):
        return float(properties[prop]) if prop == 'volume' else properties[prop]
    def set_property(prop, val):
        properties[prop] = float(val) if prop == 'volume' else val
        return True

    mock_tts.getProperty = mocker.MagicMock(side_effect=get_property)
    mock_tts.setProperty = mocker.MagicMock(side_effect=set_property)

    # Mock voices
    mock_voices = [mocker.MagicMock(id=f'voice{i}') for i in range(2)]
    mock_tts.getProperty.side_effect = lambda prop: mock_voices if prop == 'voices' else get_property(prop)

    mocker.patch('pyttsx3.init', return_value=mock_tts)

    tool = VoiceTool(agent_id="test_voice", role=VoiceRole.VOICE_CONTROL)
    await tool.initialize_tts()
    return tool

@pytest.mark.skip(reason="PortAudio library not available")
@pytest.mark.asyncio
async def test_voice_tool_initialization():
    """Test voice tool initialization."""
    voice_tool = VoiceTool(agent_id="test", role=VoiceRole.VOICE_CONTROL)
    assert voice_tool is not None
    assert voice_tool.agent_id == "test"
    assert voice_tool.role == VoiceRole.VOICE_CONTROL

@pytest.mark.skip(reason="PortAudio library not available") 
@pytest.mark.asyncio
async def test_voice_properties():
    """Test voice tool properties."""
    voice_tool = VoiceTool(agent_id="test", role=VoiceRole.VOICE_CONTROL)
    await voice_tool.set_voice()
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

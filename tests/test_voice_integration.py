import os
import pytest
import pytest_asyncio
from tools.voice_tool import VoiceTool, VoiceRole
import wave
import numpy as np

@pytest.mark.skip(reason="PortAudio library not available")
@pytest_asyncio.fixture
async def voice_tool(mocker):
    """Create voice tool fixture with mocked TTS and STT."""
    # Mock TTS engine
    mock_tts = mocker.MagicMock()
    mock_tts.save_to_file = mocker.MagicMock(side_effect=lambda text, path: open(path, 'wb').write(b'test audio'))
    mock_tts.runAndWait = mocker.MagicMock()
    mocker.patch('pyttsx3.init', return_value=mock_tts)

    # Mock whisper model
    mock_whisper = mocker.MagicMock()
    mock_whisper.transcribe = mocker.MagicMock(return_value={"text": "mocked transcription"})
    mocker.patch('whisper.load_model', return_value=mock_whisper)

    tool = VoiceTool(agent_id="test_voice_integration", role=VoiceRole.VOICE_CONTROL)
    await tool.initialize_tts()
    yield tool

    # Cleanup generated files
    audio_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'audio')
    if os.path.exists(audio_dir):
        for file in os.listdir(audio_dir):
            if file.startswith('test_voice_integration_'):
                os.remove(os.path.join(audio_dir, file))

def create_test_audio(filename="test_audio.wav", duration=1.0, sample_rate=16000):
    """Create a test audio file with a simple sine wave"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    audio_data = (audio_data * 32767).astype(np.int16)

    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    return filename

@pytest.mark.asyncio
async def test_voice_pipeline(voice_tool):
    """Test the complete voice interaction pipeline"""
    # Test TTS
    test_text = "Testing voice integration"
    audio_path = await voice_tool.speak(test_text)
    assert os.path.exists(audio_path)
    assert os.path.getsize(audio_path) > 0

    # Create and test STT with synthetic audio
    test_audio = create_test_audio()
    try:
        transcribed_text = await voice_tool.transcribe(test_audio)
        assert isinstance(transcribed_text, str)
        assert len(transcribed_text) > 0
    finally:
        if os.path.exists(test_audio):
            os.remove(test_audio)
        if os.path.exists(audio_path):
            os.remove(audio_path)

@pytest.mark.asyncio
async def test_two_way_conversation(voice_tool):
    """Test complete two-way voice conversation"""
    # Initial TTS
    initial_text = "Hello, how can I help you today?"
    tts_path = await voice_tool.speak(initial_text)
    assert os.path.exists(tts_path)

    # STT on the generated audio
    transcribed = await voice_tool.transcribe(tts_path)
    assert isinstance(transcribed, str)
    assert len(transcribed) > 0

    # Response TTS
    response_text = f"I heard you say: {transcribed}"
    response_path = await voice_tool.speak(response_text)
    assert os.path.exists(response_path)

    # Cleanup
    for path in [tts_path, response_path]:
        if os.path.exists(path):
            os.remove(path)

@pytest.mark.asyncio
async def test_voice_settings(voice_tool):
    """Test voice configuration settings"""
    # Test voice selection
    available_voices = await voice_tool.set_voice()
    assert isinstance(available_voices, list)

    # Test rate adjustment
    await voice_tool.set_rate(200)
    audio_path = await voice_tool.speak("Testing faster speech rate")
    assert os.path.exists(audio_path)

    # Test volume adjustment
    await voice_tool.set_volume(0.8)
    audio_path_2 = await voice_tool.speak("Testing adjusted volume")
    assert os.path.exists(audio_path_2)

    # Cleanup
    for path in [audio_path, audio_path_2]:
        if os.path.exists(path):
            os.remove(path)

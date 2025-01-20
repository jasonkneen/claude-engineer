from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    MODEL = "claude-3-5-sonnet-20241022"
    MAX_TOKENS = 8000
    MAX_CONVERSATION_TOKENS = 200000  # Maximum tokens per conversation

    # Memory Server Configuration
    MEMORY_SERVER_ENABLED = os.getenv('MEMORY_SERVER_ENABLED', 'true').lower() == 'true'
    MEMORY_SERVER_HOST = os.getenv('MEMORY_SERVER_HOST', 'localhost')
    MEMORY_SERVER_PORT = int(os.getenv('MEMORY_SERVER_PORT', '8765'))
    MEMORY_SERVER_RECONNECT_INTERVAL = int(os.getenv('MEMORY_SERVER_RECONNECT_INTERVAL', '5'))

    # Memory Management Thresholds
    WORKING_MEMORY_MAX_TOKENS = int(os.getenv('WORKING_MEMORY_MAX_TOKENS', '200000'))
    ARCHIVE_TRIGGER_THRESHOLD = float(os.getenv('ARCHIVE_TRIGGER_THRESHOLD', '0.9'))  # 90% of max tokens
    MIN_ARCHIVE_BLOCK_SIZE = int(os.getenv('MIN_ARCHIVE_BLOCK_SIZE', '1000'))
    MAX_ARCHIVE_BLOCK_SIZE = int(os.getenv('MAX_ARCHIVE_BLOCK_SIZE', '10000'))

    # Memory Archival Settings
    MEMORY_COMPRESSION_RATIO = float(os.getenv('MEMORY_COMPRESSION_RATIO', '0.5'))
    MEMORY_IMPORTANCE_THRESHOLD = float(os.getenv('MEMORY_IMPORTANCE_THRESHOLD', '0.7'))
    MEMORY_MAX_AGE_HOURS = int(os.getenv('MEMORY_MAX_AGE_HOURS', '24'))

    # W3W Generation Settings
    W3W_MIN_TOKENS = int(os.getenv('W3W_MIN_TOKENS', '50'))
    W3W_MAX_TOKENS = int(os.getenv('W3W_MAX_TOKENS', '200'))
    W3W_OVERLAP_TOKENS = int(os.getenv('W3W_OVERLAP_TOKENS', '10'))
    W3W_VOCABULARY_SIZE = int(os.getenv('W3W_VOCABULARY_SIZE', '1000'))

    # Memory Stats Settings
    STATS_UPDATE_INTERVAL = float(os.getenv('STATS_UPDATE_INTERVAL', '1.0'))  # seconds
    STATS_HISTORY_SIZE = int(os.getenv('STATS_HISTORY_SIZE', '100'))
    STATS_BROADCAST_ENABLED = os.getenv('STATS_BROADCAST_ENABLED', 'true').lower() == 'true'

    # Paths
    BASE_DIR = Path(__file__).parent
    TOOLS_DIR = BASE_DIR / "tools"
    PROMPTS_DIR = BASE_DIR / "prompts"

    # Assistant Configuration
    ENABLE_THINKING = True
    SHOW_TOOL_USAGE = True
    DEFAULT_TEMPERATURE = 0.7

    # Logging Configuration
    DEBUG_MODE = False
    PANEL_MODE = True

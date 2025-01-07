import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    MODEL = "claude-3-5-sonnet-20241022"
    MAX_TOKENS = 8000
    MAX_CONVERSATION_TOKENS = 200000  # Maximum tokens per conversation

    # Paths
    BASE_DIR = Path(__file__).parent
    TOOLS_DIR = BASE_DIR / "tools"
    PROMPTS_DIR = BASE_DIR / "prompts"
    CONTEXT_DIR = BASE_DIR / ".context"

    # Assistant Configuration
    ENABLE_THINKING = True
    SHOW_TOOL_USAGE = True
    DEFAULT_TEMPERATURE = 0.7
    
    # Context Management Configuration
    MAX_CONTEXT_ENTRIES = 100  # Maximum number of context entries to keep
    MIN_CONTEXT_SIZE_FOR_SUMMARY = 1000  # Minimum characters before summarizing
    CONTEXT_SUMMARY_MAX_TOKENS = 500  # Maximum tokens for context summaries
    CONTEXT_SUMMARY_TEMPERATURE = 0.3  # Lower temperature for more focused summaries
    
    # Context Cleanup and Archive
    CONTEXT_CLEANUP_THRESHOLD = 90  # Cleanup when reaching 90% of MAX_CONTEXT_ENTRIES
    CONTEXT_ARCHIVE_ENABLED = True
    CONTEXT_ARCHIVE_DIR = BASE_DIR / ".context_archive"
    
    # Context Summary Configuration
    CONTEXT_SUMMARY_PROMPT = """
    Analyze and summarize the following context information, focusing on:
    1. Key decisions and their rationales
    2. Important relationships between different components/concepts
    3. Critical technical details and configurations
    4. Potential dependencies and implications
    
    Context:
    {context}
    
    Provide a structured summary that:
    - Maintains clear relationships between components
    - Preserves technical accuracy
    - Highlights critical decisions and their impacts
    - Notes any important dependencies
    """

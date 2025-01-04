import os

class Config:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    MODEL = "claude-3-opus-20240229"
    MAX_CONVERSATION_TOKENS = 100000
    MAX_TOKENS = 1024
    
    # Tool settings
    TOOLS_DIR = "tools"
    ENABLE_THINKING = True
    
    # Model parameters 
    DEFAULT_TEMPERATURE = 0.7
    
    def __init__(self):
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

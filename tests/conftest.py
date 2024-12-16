import pytest
from unittest.mock import MagicMock
import os

# Mock sounddevice module before it's imported
mock_sd = MagicMock()
mock_sd.__version__ = '0.4.6'  # Mock version attribute

def pytest_configure(config):
    """Configure test environment."""
    import sys
    sys.modules['sounddevice'] = mock_sd
    os.environ['ANTHROPIC_API_KEY'] = 'test-key-for-testing'

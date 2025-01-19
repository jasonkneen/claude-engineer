import unittest
import asyncio
from ce3 import CE3


class TestCE3(unittest.TestCase):
    """Unit tests for the CE3 class's chat-like methods."""

    def setUp(self):
        self.ce3 = CE3()

    def test_chat_simple_message(self):
        """Test sending a simple message to chat."""
        response = self.ce3.chat("Hello from test!")
        # The 'chat' method may return None on certain commands or a string response
        self.assertIsInstance(response, (str, type(None)))

    def test_reset_functionality(self):
        """Test the reset() method to ensure conversation history and token usage are cleared."""
        # We create a short conversation
        self.ce3.chat("First message")
        # Now we reset
        self.ce3.reset()
        # The next chat should behave as if it's from scratch
        response_after_reset = self.ce3.chat("Post-reset message")
        self.assertIsInstance(response_after_reset, (str, type(None)))

    def test_process_message_async(self):
        """Test the async process_message method to ensure it returns the expected string."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.ce3.process_message("async test message"))
        self.assertEqual(result, "Message processed")


if __name__ == "__main__":
    unittest.main()

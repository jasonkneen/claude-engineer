import unittest
from mcp_memory import MCPMemory

class TestMCPMemory(unittest.TestCase):
    def setUp(self):
        """Initialize the MCP Memory instance before each test."""
        self.memory = MCPMemory()
        self.sample_article = {
            "title": "Test Article",
            "content": "This is a test article content that will be stored in MCP memory.",
            "author": "Test Author",
            "date": "2023-01-01"
        }

    def tearDown(self):
        """Clean up after each test."""
        self.memory = None
        self.sample_article = None

    def test_store_and_retrieve_content(self):
        """Test storing and retrieving content from MCP memory."""
        # Store the content
        self.memory.store_content(self.sample_article)

        # Retrieve the content
        retrieved_content = self.memory.retrieve_content()

        # Verify the retrieved content matches the original
        self.assertEqual(retrieved_content["title"], self.sample_article["title"])
        self.assertEqual(retrieved_content["content"], self.sample_article["content"])
        self.assertEqual(retrieved_content["author"], self.sample_article["author"])
        self.assertEqual(retrieved_content["date"], self.sample_article["date"])

if __name__ == '__main__':
    unittest.main()


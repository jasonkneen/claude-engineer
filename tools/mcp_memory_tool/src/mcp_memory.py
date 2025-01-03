class MCPMemory:
    def __init__(self):
        """Initialize an empty memory storage."""
        self._memory = {}
    
    def store_content(self, key, content):
        """
        Store content in memory with the specified key.
        
        Args:
            key: The key to store the content under
            content: The content to store
            
        Raises:
            ValueError: If key or content is None or empty
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")
        if content is None:
            raise ValueError("Content cannot be None")
            
        self._memory[key] = content
    
    def retrieve_content(self, key):
        """
        Retrieve content from memory using the specified key.
        
        Args:
            key: The key to retrieve content for
            
        Returns:
            The stored content for the given key
            
        Raises:
            KeyError: If the key doesn't exist in memory
            ValueError: If key is None or empty
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")
            
        if key not in self._memory:
            raise KeyError(f"No content found for key: {key}")
            
        return self._memory[key]


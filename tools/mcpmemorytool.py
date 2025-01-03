from typing import Dict, List, Optional, Any
from pathlib import Path
from tools.basetool import BaseTool
import logging
import os

# Import the MCP Memory Service
from tools.mcp_memory.src.mcp_memory_service import MemoryService

class MCPMemoryTool(BaseTool):
    """Tool for interacting with the MCP Memory Service
    
    Provides a wrapper around the MCP Memory Service functionality for storing,
    retrieving and searching memories using semantic similarity and tags.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "MCPMemoryTool"
        self.description = "Tool for interacting with the MCP Memory Service"
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize paths relative to this file
        self.tool_dir = Path(__file__).parent.absolute()
        self.memory_dir = self.tool_dir / "mcp_memory"
        self.config_dir = self.memory_dir / "config"
        self.chroma_dir = self.config_dir / "chroma_db" 
        self.backups_dir = self.config_dir / "backups"
        
        # Ensure directories exist
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        try:
            self._init_memory_service()
        except Exception as e:
            self.logger.error(f"Failed to initialize memory service: {str(e)}")
            raise

    def store_memory(self, content: str, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None) -> str:
        """Store a memory with optional metadata and tags"""
        try:
            memory_id = self.memory_service.store_memory(content, metadata, tags)
            return memory_id
        except Exception as e:
            self.logger.error(f"Error storing memory: {str(e)}")
            raise

    def retrieve_memory(self, query: str, k: int = 5) -> List[Dict]:
        """Retrieve memories semantically similar to the query"""
        try:
            memories = self.memory_service.retrieve_memory(query, k)
            return memories
        except Exception as e:
            self.logger.error(f"Error retrieving memories: {str(e)}")
            raise

    def search_by_tag(self, tags: List[str], require_all: bool = True) -> List[Dict]:
        """Search memories by tags"""
        try:
            memories = self.memory_service.search_by_tag(tags, require_all)
            return memories
        except Exception as e:
            self.logger.error(f"Error searching by tags: {str(e)}")
            raise

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID"""
        try:
            success = self.memory_service.delete_memory(memory_id)
            return success
        except Exception as e:
            self.logger.error(f"Error deleting memory: {str(e)}")
            raise

    def export_memories(self, file_path: Optional[str] = None) -> str:
        """Export all memories to a backup file"""
        if file_path is None:
            file_path = os.path.join(self.data_dir, "backups", "memory_backup.json")
        try:
            self.memory_service.export_memories(file_path)
            return file_path
        except Exception as e:
            self.logger.error(f"Error exporting memories: {str(e)}")
            raise

    def import_memories(self, file_path: str) -> int:
        """Import memories from a backup file"""
        try:
            count = self.memory_service.import_memories(file_path)
            return count
        except Exception as e:
            self.logger.error(f"Error importing memories: {str(e)}")
            raise

    def _init_memory_service(self):
        """Initialize the MCP Memory Service with configuration."""
        os.environ["MCP_MEMORY_CHROMA_PATH"] = str(self.chroma_dir)
        os.environ["MCP_MEMORY_BACKUPS_PATH"] = str(self.backups_dir)
        
        try:
            self.memory_service = MemoryService()
            self.logger.info("MCP Memory Service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize memory service: {str(e)}")
            raise
    
    async def store_memory(self, 
                        content: str, 
                        metadata: Optional[Dict[str, Any]] = None,
                        tags: Optional[List[str]] = None) -> str:
        """Store a new memory with optional metadata and tags.
        
        Args:
            content: The text content to store
            metadata: Optional dictionary of metadata
            tags: Optional list of tags
            
        Returns:
            str: The memory ID of the stored content
        """
        try:
            memory_id = self.memory_service.store_memory(
                content=content,
                metadata=metadata or {},
                tags=tags or []
            )
            self.logger.debug(f"Stored memory with ID: {memory_id}")
            return memory_id
        except Exception as e:
            self.logger.error(f"Failed to store memory: {str(e)}")
            raise
    
    async def retrieve_memory(self,
                            query: str,
                            limit: int = 5,
                            min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """Retrieve memories similar to the query text.
        
        Args:
            query: The search query text
            limit: Maximum number of results to return
            min_similarity: Minimum similarity score (0-1)
            
        Returns:
            List of matching memories with their metadata
        """
        try:
            results = self.memory_service.retrieve_memory(
                query=query,
                limit=limit,
                min_similarity=min_similarity
            )
            self.logger.debug(f"Retrieved {len(results)} memories")
            return results
        except Exception as e:
            self.logger.error(f"Failed to retrieve memories: {str(e)}")
            raise
    
    async def search_by_tag(self, 
                        tags: List[str],
                        match_any: bool = False) -> List[Dict[str, Any]]:
        """Search memories by tags.
        
        Args:
            tags: List of tags to search for
            match_any: If True, match memories with any of the tags
                    If False, match only memories with all tags
            
        Returns:
            List of matching memories with their metadata
        """
        try:
            results = self.memory_service.search_by_tag(
                tags=tags,
                match_any=match_any
            )
            self.logger.debug(f"Found {len(results)} memories with tags: {tags}")
            return results
        except Exception as e:
            self.logger.error(f"Failed to search by tags: {str(e)}")
            raise
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by its ID.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            success = self.memory_service.delete_memory(memory_id)
            if success:
                self.logger.debug(f"Deleted memory: {memory_id}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to delete memory: {str(e)}")
            raise
    
    async def clear_memories(self) -> bool:
        """Clear all stored memories.
        
        Returns:
            bool: True if clearing was successful
        """
        try:
            success = self.memory_service.clear_memories()
            if success:
                self.logger.info("Cleared all memories")
            return success
        except Exception as e:
            self.logger.error(f"Failed to clear memories: {str(e)}")
            raise


import json
from typing import List, Dict, Any

class MemoryMethods:
    """Memory-specific methods for autonomous-mcp."""
    
    def __init__(self, memory_service):
        self.memory_service = memory_service
    
    async def store_memory(self, content: str, tags: List[str] = None) -> Dict[str, Any]:
        """Store a new memory."""
        mem_id = await self.memory_service.store_memory(content, tags or [])
        return {
            "success": True,
            "memory_id": mem_id,
            "content": content,
            "tags": tags
        }
        
    async def retrieve_memory(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Retrieve memories similar to the query."""
        results = await self.memory_service.retrieve_memory(query, n_results)
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "content": r["content"],
                    "similarity": r["similarity"],
                    "tags": r.get("metadata", {}).get("tags", [])
                }
                for r in results
            ]
        }
        
    async def search_by_tag(self, tag: str) -> Dict[str, Any]:
        """Search memories by tag."""
        results = await self.memory_service.search_by_tag(tag)
        return {
            "success": True,
            "tag": tag,
            "results": [
                {
                    "content": r["content"],
                    "tags": r.get("metadata", {}).get("tags", [])
                }
                for r in results
            ]
        }


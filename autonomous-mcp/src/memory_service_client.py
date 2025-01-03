import aiohttp
import json
from typing import Dict, List, Optional, Any

class MemoryServiceClient:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.base_url = f"http://{host}:{port}"
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            
    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("Client session not initialized. Use async context manager.")
        return self._session
        
    async def store_memory(self, content: str, tags: List[str], metadata: Dict[str, Any]) -> str:
        """Store a memory and return its ID."""
        payload = {
            "content": content,
            "tags": tags,
            "metadata": metadata
        }
        async with self.session.post(f"{self.base_url}/memories", json=payload) as response:
            response.raise_for_status()
            result = await response.json()
            return result["memory_id"]
            
    async def retrieve_memory(self, memory_id: str) -> Dict[str, Any]:
        """Retrieve a memory by ID."""
        async with self.session.get(f"{self.base_url}/memories/{memory_id}") as response:
            response.raise_for_status()
            return await response.json()
            
    async def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Search memories by tag."""
        params = {"tag": tag}
        async with self.session.get(f"{self.base_url}/memories/search", params=params) as response:
            response.raise_for_status()
            return await response.json()


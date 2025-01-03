import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional

from server import MCPServer
from methods.memory_methods import MemoryMethods
from protocols.http_handler import HTTPHandler
from protocols.sse_handler import SSEHandler
from protocols.web_handler import WebHandler

class MemoryService:
    def __init__(self):
        self.base_url = "http://localhost:8000/api/v1"
        self.session = None

    async def setup(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    async def store_memory(self, memory_data):
        async with self.session.post(f"{self.base_url}/memory", json=memory_data) as resp:
            return await resp.json()

    async def retrieve_memory(self, memory_id):
        async with self.session.get(f"{self.base_url}/memory/{memory_id}") as resp:
            return await resp.json()

    async def search_by_tag(self, tag):
        async with self.session.get(f"{self.base_url}/memory/search", params={"tag": tag}) as resp:
            return await resp.json()

class MemoryAgent(MCPServer):
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        super().__init__(host, port)
        
        # Initialize memory service and methods
        self.memory_service = MemoryService()
        self.memory_methods = MemoryMethods(self.memory_service)
        
        # Register all available memory methods
        self.register_method("store_memory", self.memory_methods.store_memory)
        self.register_method("retrieve_memory", self.memory_methods.retrieve_memory) 
        self.register_method("search_by_tag", self.memory_methods.search_by_tag)
        
        # Initialize all protocol handlers
        self.http_handler = HTTPHandler(self)
        self.sse_handler = SSEHandler(self)
        self.web_handler = WebHandler(self)

    async def start(self):
        """Start the memory agent with all protocols"""
        await super().start()
        
        # Initialize memory service
        await self.memory_service.setup()
        
        # Start protocol handlers
        await self.http_handler.start()
        await self.sse_handler.start()
        await self.web_handler.start()
        
        print(f"Memory Agent running at http://{self.host}:{self.port}")
        print("Available methods: store_memory, retrieve_memory, search_by_tag")
        
    async def stop(self):
        """Stop all protocol handlers and server"""
        await self.http_handler.stop()
        await self.sse_handler.stop() 
        await self.web_handler.stop()
        if self.memory_service.session:
            await self.memory_service.session.close()
        await super().stop()

def main():
    agent = MemoryAgent()
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("Shutting down Memory Agent...")
        asyncio.run(agent.stop())

if __name__ == "__main__":
    main()


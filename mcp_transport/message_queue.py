from typing import Dict, List, Any
from asyncio import Queue

class MessageQueue:
    def __init__(self):
        self._queues: Dict[str, Queue] = {}
    
    async def create_queue(self, client_id: str) -> None:
        if client_id not in self._queues:
            self._queues[client_id] = Queue()
    
    async def remove_queue(self, client_id: str) -> None:
        if client_id in self._queues:
            del self._queues[client_id]
    
    async def enqueue_message(self, client_id: str, message: Any) -> None:
        if client_id in self._queues:
            await self._queues[client_id].put(message)
    
    async def get_message(self, client_id: str) -> Any:
        if client_id in self._queues:
            return await self._queues[client_id].get()
        return None
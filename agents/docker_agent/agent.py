import json
import asyncio
import aiohttp
from typing import Dict, Any

class DockerAgent:
    def __init__(self, webcontainer_url: str):
        self.webcontainer_url = webcontainer_url
        self.session = None
        self.sse_connection = None

    async def connect(self):
        self.session = aiohttp.ClientSession()
        # Connect to SSE endpoint
        self.sse_connection = await self.session.get(
            f'{self.webcontainer_url}/sse',
            headers={'Accept': 'text/event-stream'}
        )

    async def send_message(self, message: Dict[Any, Any]):
        async with self.session.post(
            f'{self.webcontainer_url}/message',
            json=message
        ) as response:
            return await response.json()

    async def listen_for_messages(self):
        async for msg in self.sse_connection.content:
            if msg:
                # Process SSE message
                message = msg.decode('utf-8')
                if message.startswith('data: '):
                    data = json.loads(message[6:])
                    await self.handle_message(data)

    async def handle_message(self, message: Dict[Any, Any]):
        # Implement message handling logic
        print(f'Received message: {message}')

    async def run(self):
        await self.connect()
        await self.listen_for_messages()

    async def cleanup(self):
        if self.sse_connection:
            await self.sse_connection.close()
        if self.session:
            await self.session.close()

if __name__ == '__main__':
    webcontainer_url = 'http://localhost:8080'
    agent = DockerAgent(webcontainer_url)
    try:
        asyncio.run(agent.run())
    finally:
        asyncio.run(agent.cleanup())
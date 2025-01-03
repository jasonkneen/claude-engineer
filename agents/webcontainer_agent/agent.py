import json
import asyncio
from aiohttp import web
from typing import Dict, Any

class WebContainerAgent:
    def __init__(self):
        self.app = web.Application()
        self.app.router.add_post('/message', self.handle_message)
        self.app.router.add_get('/sse', self.handle_sse)
        self.connections = []

    async def handle_message(self, request):
        data = await request.json()
        # Process incoming message
        response = await self.process_message(data)
        return web.json_response(response)

    async def handle_sse(self, request):
        resp = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        await resp.prepare(request)
        self.connections.append(resp)
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            self.connections.remove(resp)
        return resp

    async def process_message(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        # Implement message processing logic
        return {
            'status': 'processed',
            'original_data': data
        }

    async def broadcast_message(self, message: Dict[Any, Any]):
        data = f'data: {json.dumps(message)}\n\n'
        for conn in self.connections:
            await conn.write(data.encode())

    def run(self, host='0.0.0.0', port=8080):
        web.run_app(self.app, host=host, port=port)

if __name__ == '__main__':
    agent = WebContainerAgent()
    agent.run()
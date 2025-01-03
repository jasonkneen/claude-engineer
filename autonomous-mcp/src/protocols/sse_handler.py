
from aiohttp import web
import json

class SSEHandler:
    def __init__(self, server):
        self.server = server
        self.active_connections = set()
        self._running = False

    async def start(self):
        """Start the SSE handler."""
        self._running = True
        
    async def stop(self):
        """Stop the SSE handler and close all active connections."""
        self._running = False
        for response in self.active_connections:
            await response.write(b"event: close\ndata: Server shutting down\n\n")
        self.active_connections.clear()
    async def handle(self, request):
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        
        try:
            if not self._running:
                return web.Response(status=503, text="Server is shutting down")
                
            self.active_connections.add(response)
            while self._running:
                data = await request.content.read()
                if data:
                    result = await self.server.handle_request(json.loads(data))
                    await response.write(f"data: {json.dumps(result)}\n\n".encode('utf-8'))
        except Exception as e:
            self.server.logger.error(f"SSE Error: {str(e)}")
        finally:
            self.active_connections.discard(response)
            return response

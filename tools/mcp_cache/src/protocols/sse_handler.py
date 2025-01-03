
from aiohttp import web
import json

class SSEHandler:
    def __init__(self, server):
        self.server = server
        
    async def handle(self, request):
        response = web.StreamResponse()
        response.headers['Content-Type'] = 'text/event-stream'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Connection'] = 'keep-alive'
        await response.prepare(request)
        
        try:
            while True:
                data = await request.content.read()
                if data:
                    result = await self.server.handle_request(json.loads(data))
                    await response.write(f"data: {json.dumps(result)}\n\n".encode('utf-8'))
        except Exception as e:
            self.server.logger.error(f"SSE Error: {str(e)}")
        finally:
            return response

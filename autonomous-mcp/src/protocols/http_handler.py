import json
from aiohttp import web
from typing import Optional, Dict, Any

class HTTPHandler:
    def __init__(self, agent):
        self.agent = agent
        self.router = web.RouteTableDef()
        self._setup_routes()

    def _setup_routes(self):
        @self.router.post('/memory/store')
        async def store_memory(request):
            data = await request.json()
            content = data.get('content')
            tags = data.get('tags', [])
            
            if not content:
                raise web.HTTPBadRequest(text="Content is required")

            result = await self.agent.handle_method("store_memory", {"content": content, "tags": tags})
            return web.json_response({"success": True, "memory_id": result})

        @self.router.get('/memory/retrieve')
        async def retrieve_memory(request):
            query = request.query.get('query')
            n_results = int(request.query.get('n_results', 5))
            
            if not query:
                raise web.HTTPBadRequest(text="Query is required")

            result = await self.agent.handle_method("retrieve_memory", {"query": query, "n_results": n_results})
            return web.json_response({"success": True, "results": result})

        @self.router.get('/memory/search')
        async def search_by_tag(request):
            tag = request.query.get('tag')
            if not tag:
                raise web.HTTPBadRequest(text="Tag is required")

            result = await self.agent.handle_method("search_by_tag", {"tag": tag})
            return web.json_response({"success": True, "results": result})

    def get_routes(self):
        return self.router

    async def start(self):
        app = web.Application()
        app.add_routes(self.router)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, host='localhost', port=8080)
        await site.start()
        print(f"HTTP server started on http://localhost:8080")

    async def stop(self):
        if hasattr(self, 'runner'):
            await self.runner.cleanup()
            print("HTTP server stopped")

import json
import aiohttp_jinja2
import jinja2
from pathlib import Path
from aiohttp import web

class WebHandler:
    def __init__(self, agent):
        self.agent = agent
        self.router = web.RouteTableDef()
        self._setup_routes()
        
    def _setup_routes(self):
        @self.router.get('/')
        @aiohttp_jinja2.template('index.html')
        async def index(request):
            return {}

        @self.router.post('/api/memory/store')
        async def store_memory(request):
            data = await request.json()
            content = data.get('content')
            tags = data.get('tags', [])
            
            result = await self.agent.handle_method("store_memory", {"content": content, "tags": tags})
            return web.json_response({"success": True, "memory_id": result})

        @self.router.post('/api/memory/retrieve')
        async def retrieve_memory(request):
            data = await request.json()
            query = data.get('query')
            n_results = int(data.get('n_results', 5))
            
            result = await self.agent.handle_method("retrieve_memory", {"query": query, "n_results": n_results})
            return web.json_response({"success": True, "results": result})

    def setup_static_routes(self, app):
        # Set up Jinja2 templates
        templates_path = Path(__file__).parent / 'templates'
        aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(str(templates_path)))
        
        # Serve static files
        static_path = Path(__file__).parent / 'static'
        app.router.add_static('/static/', path=str(static_path), name='static')
        
    def get_routes(self):
        return self.router
        
    async def start(self) -> dict:
        """Start the web interface handler."""
        return {"status": "success", "message": "Web interface started"}
        
    async def stop(self) -> dict:
        """Stop the web interface handler."""
        return {"status": "success", "message": "Web interface stopped"}

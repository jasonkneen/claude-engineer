
import os
import json
import logging
from method_handler import MethodHandler
from logger import setup_logging

class MCPServer:
    def __init__(self):
        self.logger = setup_logging()
        self.method_handler = MethodHandler()
        
    async def handle_request(self, request):
        try:
            return await self.method_handler.handle(request)
        except Exception as e:
            self.logger.error(f"Error handling request: {str(e)}")
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}

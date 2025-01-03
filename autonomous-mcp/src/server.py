
import os
import json
import logging
from method_handler import MethodHandler
from logger import setup_logging

class MCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.logger = setup_logging()
        self.method_handler = MethodHandler()
        self._registered_methods = {}
        
    def register_method(self, operation: str, handler):
        """Register a handler method for a specific operation"""
        self._registered_methods[operation] = handler
        self.method_handler.add_method(operation, handler)

    async def handle_request(self, request):
        try:
            return await self.method_handler.handle(request)
        except Exception as e:
            self.logger.error(f"Error handling request: {str(e)}")
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None}

    async def start(self):
        """Start the server"""
        self.logger.info(f"Starting server on {self.host}:{self.port}")
        await self.method_handler.setup()

    async def stop(self):
        """Stop the server"""
        self.logger.info("Stopping server")
        await self.method_handler.cleanup()

import json
from typing import Dict, Any, Callable, Awaitable

class MethodHandler:
    def __init__(self):
        self.methods: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {}
        
    def add_method(self, name: str, handler: Callable[[Dict[str, Any]], Awaitable[Any]]) -> None:
        """Register a new method handler."""
        self.methods[name] = handler
        
    async def setup(self) -> None:
        """Perform any necessary setup."""
        pass
        
    async def cleanup(self) -> None:
        """Cleanup any resources."""
        pass
        
    async def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(request, dict):
            return self._error_response(-32600, "Invalid Request")
            
    def _error_response(self, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": None
        }

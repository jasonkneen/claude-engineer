
import json
from typing import Dict, Any

class MethodHandler:
    def __init__(self):
        self.methods = {}
        
    async def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(request, dict):
            return self._error_response(-32600, "Invalid Request")
            
        method = request.get("method")
        if not method in self.methods:
            return self._error_response(-32601, "Method not found")
            
        try:
            result = await self.methods[method](request.get("params", {}))
            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request.get("id")
            }
        except Exception as e:
            return self._error_response(-32603, str(e))
            
    def _error_response(self, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": None
        }

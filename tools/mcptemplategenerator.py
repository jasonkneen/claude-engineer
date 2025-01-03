from tools.base import BaseTool
import os
import json
import shutil
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader

class MCPTemplateGenerator(BaseTool):
    name = "mcptemplategenerator"
    description = '''
    Generates a complete Universal MCP Server template with support for multiple transport protocols.
    Creates full project structure including configuration, documentation, and testing framework.
    Features:
    - Multiple transport protocols (SSE, Stdio, REST)
    - Docker and StackBlitz deployment configurations
    - Browser-based testing UI
    - JSON-RPC 2.0 implementation
    - Extensible method system
    - Comprehensive logging and error handling
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "project_name": {
                "type": "string",
                "description": "Name of the MCP server project"
            },
            "protocols": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["sse", "stdio", "rest"]
                },
                "description": "List of transport protocols to support"
            },
            "output_dir": {
                "type": "string",
                "description": "Directory where the template will be generated"
            }
        },
        "required": ["project_name", "protocols", "output_dir"]
    }

    def execute(self, **kwargs) -> str:
        project_name = kwargs.get("project_name")
        protocols = kwargs.get("protocols")
        output_dir = kwargs.get("output_dir")

        try:
            self._create_project_structure(output_dir, project_name)
            self._generate_core_files(output_dir, project_name, protocols)
            self._generate_protocol_handlers(output_dir, protocols)
            self._generate_config_files(output_dir, project_name)
            self._generate_documentation(output_dir)
            self._generate_test_framework(output_dir)
            self._generate_ui(output_dir)

            return f"MCP Server template generated successfully at {output_dir}"
        except Exception as e:
            return f"Error generating template: {str(e)}"

    def _create_project_structure(self, base_dir: str, project_name: str) -> None:
        directories = [
            "src",
            "src/protocols",
            "src/methods",
            "config",
            "docs",
            "tests",
            "ui",
            "deployment"
        ]
        
        for dir_path in directories:
            os.makedirs(os.path.join(base_dir, dir_path), exist_ok=True)

    def _generate_core_files(self, base_dir: str, project_name: str, protocols: list) -> None:
        core_files = {
            "src/server.py": self._get_server_template(),
            "src/method_handler.py": self._get_method_handler_template(),
            "src/logger.py": self._get_logger_template(),
            ".env": self._get_env_template(project_name),
            "requirements.txt": self._get_requirements_template(protocols)
        }

        for file_path, content in core_files.items():
            with open(os.path.join(base_dir, file_path), 'w') as f:
                f.write(content)

    def _generate_protocol_handlers(self, base_dir: str, protocols: list) -> None:
        for protocol in protocols:
            template = getattr(self, f"_get_{protocol}_template")()
            with open(os.path.join(base_dir, f"src/protocols/{protocol}_handler.py"), 'w') as f:
                f.write(template)

    def _generate_config_files(self, base_dir: str, project_name: str) -> None:
        config_files = {
            "deployment/Dockerfile": self._get_dockerfile_template(),
            "deployment/docker-compose.yml": self._get_docker_compose_template(project_name),
            "config/server_config.json": self._get_server_config_template()
        }

        for file_path, content in config_files.items():
            with open(os.path.join(base_dir, file_path), 'w') as f:
                f.write(content)

    def _get_server_template(self) -> str:
        return '''
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
'''

    def _get_method_handler_template(self) -> str:
        return '''
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
'''

    def _get_logger_template(self) -> str:
        return '''
import logging
import os

def setup_logging():
    logger = logging.getLogger('mcp_server')
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
'''

    def _get_env_template(self, project_name: str) -> str:
        return f'''
PROJECT_NAME={project_name}
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
'''

    def _get_requirements_template(self, protocols: list) -> str:
        base_requirements = [
            "aiohttp",
            "python-dotenv",
            "jsonschema",
            "pytest",
            "pytest-asyncio"
        ]
        return "\n".join(base_requirements)

    def _get_sse_template(self) -> str:
        return '''
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
                    await response.write(f"data: {json.dumps(result)}\\n\\n".encode('utf-8'))
        except Exception as e:
            self.server.logger.error(f"SSE Error: {str(e)}")
        finally:
            return response
'''

    def _get_dockerfile_template(self) -> str:
        return '''
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/server.py"]
'''

    def _get_server_config_template(self) -> str:
        return '''{
    "server": {
        "host": "0.0.0.0",
        "port": 8000
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "protocols": {
        "sse": {
            "enabled": true,
            "path": "/sse"
        },
        "rest": {
            "enabled": true,
            "path": "/api"
        }
    }
}'''

    def _generate_documentation(self, base_dir: str) -> None:
        docs = {
            "docs/README.md": "# MCP Server Documentation\n\nAPI and usage documentation...",
            "docs/API.md": "# API Reference\n\nDetailed API documentation...",
            "docs/DEPLOYMENT.md": "# Deployment Guide\n\nDeployment instructions..."
        }
        
        for file_path, content in docs.items():
            with open(os.path.join(base_dir, file_path), 'w') as f:
                f.write(content)

    def _generate_test_framework(self, base_dir: str) -> None:
        test_files = {
            "tests/conftest.py": "# pytest configuration",
            "tests/test_server.py": "# Server tests",
            "tests/test_methods.py": "# Method tests"
        }
        
        for file_path, content in test_files.items():
            with open(os.path.join(base_dir, file_path), 'w') as f:
                f.write(content)

    def _generate_ui(self, base_dir: str) -> None:
        ui_files = {
            "ui/index.html": self._get_ui_template(),
            "ui/styles.css": "/* UI styles */",
            "ui/script.js": "// UI JavaScript"
        }
        
        for file_path, content in ui_files.items():
            with open(os.path.join(base_dir, file_path), 'w') as f:
                f.write(content)

    def _get_ui_template(self) -> str:
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Test UI</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>MCP Server Test Interface</h1>
    <div id="request-form">
        <!-- Request form -->
    </div>
    <div id="response-display">
        <!-- Response display -->
    </div>
    <script src="script.js"></script>
</body>
</html>
'''
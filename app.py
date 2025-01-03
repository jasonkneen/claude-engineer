from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect, HTTPException,
    File, UploadFile, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import Optional, List, Dict, Any
import datetime
import uuid
import json
import logging
import os
import asyncio
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate required environment variables
if not os.getenv('ANTHROPIC_API_KEY'):
    logger.error('ANTHROPIC_API_KEY environment variable is not set')
    raise ValueError('ANTHROPIC_API_KEY environment variable is not set')

# Configure Anthropic client
try:
    anthropic_client = anthropic.Anthropic(
        api_key=os.getenv('ANTHROPIC_API_KEY')
    )
    logger.info('Successfully initialized Anthropic client')
except Exception as e:
    logger.error(f'Failed to initialize Anthropic client: {str(e)}')
    raise

# Get server configuration from environment variables
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', '8000'))

# Configure CORS origins
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

class ChatMessage(BaseModel):
    message: str
    image: Optional[str] = None
    thinking: bool = False
    tool_name: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None

class AgentParseRequest(BaseModel):
    description: str

class AgentParseResponse(BaseModel):
    name: str
    role: str
    tools: List[str]

class AgentConfig(BaseModel):
    enabled: bool
    agents: Optional[Dict[str, Any]] = None

# Initialize FastAPI app with configuration
app = FastAPI(
    title="Claude Engineer API",
    description="API for managing AI agents and tools",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
# Configure CORS with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Log CORS configuration
logger.info("CORS configured to allow all origins in development")
logger.info("WebSocket endpoint available at ws://localhost:8000/ws")

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("New WebSocket connection accepted")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info("WebSocket connection closed")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logging.error(f"Error broadcasting message: {str(e)}")

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    """Health check endpoint to verify server is running."""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat(),
        "websocket_endpoint": "ws://localhost:8000/ws"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting up server...")
        # Add any additional startup initialization here
        logger.info(f"Server running at http://{HOST}:{PORT}")
        logger.info("WebSocket endpoint available at ws://localhost:8000/ws")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down server...")
        # Add any cleanup code here
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

async def parse_agent_description(description: str) -> Dict[str, Any]:
    """Parse natural language description into agent properties"""
    try:
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.error("ANTHROPIC_API_KEY not set")
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        # Use Claude to parse the description
        response = await anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Parse this agent description and extract name, role, and recommended tools.
                Description: {description}
                
                Return a JSON object with:
                - name: extracted or generated name
                - role: one of [test, context, orchestrator, custom]
                - tools: list of recommended tool names
                
                Base the tool selection on the agent's purpose.
                
                Example response:
                {{
                    "name": "API Tester",
                    "role": "test",
                    "tools": ["http_client", "test_runner", "logger"]
                }}"""
            }]
        )
        
        # Extract the JSON from Claude's response
        content = response.content[0].text
        parsed = json.loads(content)
        
        return {
            "name": parsed.get("name", ""),
            "role": parsed.get("role", "custom"),
            "tools": parsed.get("tools", [])
        }
        
    except Exception as e:
        logging.error(f"Error parsing agent description: {str(e)}")
        return {
            "name": "",
            "role": "custom",
            "tools": []
        }

@app.get("/agents")
async def get_agents():
    """Get list of all agents."""
    try:
        # For now, return empty list as we don't have persistence
        return []
    except Exception as e:
        logging.error(f"Error getting agents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting agents: {str(e)}"
        )

# WebSocket configuration
WS_PING_INTERVAL = int(os.getenv('WS_PING_INTERVAL', '30'))
WS_PING_TIMEOUT = int(os.getenv('WS_PING_TIMEOUT', '10'))
MAX_AGENTS = int(os.getenv('MAX_AGENTS', '10'))
AGENT_TIMEOUT = int(os.getenv('AGENT_TIMEOUT', '300'))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time chat and agent creation."""
    ping_task = None
    try:
        logger.info(f"New WebSocket connection attempt from {websocket.client}")
        await manager.connect(websocket)
        logger.info("WebSocket connection accepted")
        
        # Send initial connection success message
        connection_message = {
            'type': 'connected',
            'content': 'Successfully connected to server',
            'timestamp': datetime.datetime.now().isoformat()
        }
        await websocket.send_json(connection_message)
        logger.info(f"Sent connection success message: {connection_message}")

        # Start ping/pong task
        async def ping_pong():
            while True:
                try:
                    await asyncio.sleep(WS_PING_INTERVAL)
                    await websocket.send_json({
                        'type': 'ping',
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    # Wait for pong response
                    try:
                        await asyncio.wait_for(
                            websocket.receive_text(),
                            timeout=WS_PING_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Ping timeout, closing connection")
                        await websocket.close()
                        break
                except Exception as e:
                    logger.error(f"Error in ping/pong: {str(e)}")
                    break

        # Start ping/pong task
        ping_task = asyncio.create_task(ping_pong())

        # Keep connection alive and handle messages
        connected = True
        while connected:
            try:
                # Wait for messages
                raw_data = await websocket.receive_text()
                logging.info(f"Received raw message: {raw_data}")
                
                try:
                    data = json.loads(raw_data)
                    logger.info(f"Parsed message data: {data}")
                    
                    # Validate message structure
                    if not isinstance(data, dict):
                        raise ValueError("Message must be a JSON object")
                    
                    if 'type' not in data or 'content' not in data:
                        raise ValueError("Message must contain 'type' and 'content' fields")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Invalid message format: {str(e)}")
                    await websocket.send_json({
                        'type': 'error',
                        'content': 'Invalid JSON message',
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    continue

                if not isinstance(data, dict):
                    await websocket.send_json({
                        'type': 'error',
                        'content': 'Message must be a JSON object',
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    continue

                message_type = data.get('type')
                content = data.get('content')

                if not message_type or not content:
                    await websocket.send_json({
                        'type': 'error',
                        'content': 'Message must contain type and content fields',
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    continue

                # Handle pong messages
                if message_type == 'pong':
                    logger.debug("Received pong message")
                    continue

                # Handle regular messages
                if message_type == 'message':
                    # Handle initial connection message
                    if content == 'Agent creation client connected':
                        logger.info("Client connection acknowledged")
                        await websocket.send_json({
                            'type': 'connected',
                            'content': 'Connection acknowledged',
                            'timestamp': datetime.datetime.now().isoformat()
                        })
                        continue

                    try:
                        # Parse agent description
                        parsed = await parse_agent_description(content)
                        await websocket.send_json({
                            'type': 'agent_parsed',
                            'content': parsed,
                            'timestamp': datetime.datetime.now().isoformat()
                        })

                        # Create agent (mock for now)
                        await websocket.send_json({
                            'type': 'agent_created',
                            'content': {
                                'id': str(uuid.uuid4()),
                                'name': parsed['name'],
                                'role': parsed['role'],
                                'tools': parsed['tools']
                            },
                            'timestamp': datetime.datetime.now().isoformat()
                        })
                    except Exception as e:
                        logging.error(f"Error processing agent: {str(e)}")
                        await websocket.send_json({
                            'type': 'error',
                            'content': f"Error processing agent: {str(e)}",
                            'timestamp': datetime.datetime.now().isoformat()
                        })
                else:
                    await websocket.send_json({
                        'type': 'error',
                        'content': f"Unknown message type: {message_type}",
                        'timestamp': datetime.datetime.now().isoformat()
                    })

            except WebSocketDisconnect:
                logging.info("Client disconnected")
                connected = False
            except Exception as e:
                logging.error(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    'type': 'error',
                    'content': f"Error processing message: {str(e)}",
                    'timestamp': datetime.datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error occurred: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        if ping_task:
            logger.info("Cancelling ping task")
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                logger.info("Ping task cancelled successfully")
            except Exception as e:
                logger.error(f"Error cancelling ping task: {str(e)}")
        try:
            manager.disconnect(websocket)
            await websocket.close()
        except:
            pass
        logger.info("WebSocket connection closed")

if __name__ == '__main__':
    try:
        import uvicorn
        logger.info(f"Starting server on {HOST}:{PORT}")
        uvicorn.run(
            app,
            host=HOST,
            port=PORT,
            log_level=os.getenv('LOG_LEVEL', 'info').lower(),
            reload=os.getenv('DEBUG', 'false').lower() == 'true'
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise
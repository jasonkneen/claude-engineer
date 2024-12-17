from fastapi import FastAPI, Request, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import sys
import os
import logging
import datetime
from enum import Enum
from tools.voice_tool import VoiceTool
from tools.agent_manager import AgentManagerTool
from tools.context_manager import ContextManagerTool

class ToolSchema(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]

class AgentRole(str, Enum):
    TEST = "test"
    CONTEXT = "context"
    ORCHESTRATOR = "orchestrator"
    CUSTOM = "custom"

class AgentCreate(BaseModel):
    name: str
    role: AgentRole
    tools: List[str]

class ChatResponse(BaseModel):
    type: str = "message"
    content: str
    role: str = "assistant"
    timestamp: str
    id: str

class ChatRequest(BaseModel):
    content: str

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the backend directory to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ce3 import Assistant

app = FastAPI(title="Claude Engineer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the assistant and create default agents on startup."""
    global assistant
    try:
        # Initialize assistant
        assistant = Assistant()
        await assistant.initialize()
        
        # Initialize agent manager
        assistant.agent_manager = AgentManagerTool()
        
        # Create default agents
        default_agents = [
            {
                "name": "management",
                "role": AgentRole.CUSTOM,
                "tools": ["agent_manager", "context_manager"]
            },
            {
                "name": "context",
                "role": AgentRole.CONTEXT,
                "tools": ["context_manager", "file_reader"]
            },
            {
                "name": "tracker",
                "role": AgentRole.CUSTOM,
                "tools": ["context_manager", "file_reader", "file_writer"]
            }
        ]
        
        for agent in default_agents:
            agent_id = f"{agent['name']}_{datetime.datetime.now().timestamp()}"
            await assistant.agent_manager.execute(
                command="create",
                agent_id=agent_id,
                role=agent["role"],
                tools=agent["tools"]
            )
        
        # Initialize voice tool
        assistant.voice_tool = VoiceTool()
        
        logger.info("Assistant and default agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize assistant: {str(e)}")
        raise

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message
            chat_response = await assistant.chat(message_data['content'])
            
            # Convert response to text if voice is requested
            if message_data.get('voice', False):
                audio_data = await assistant.voice_tool.text_to_speech(str(chat_response))
                # Send both text and audio data
                response_data = {
                    "type": "message",
                    "content": str(chat_response),
                    "audio": audio_data,
                    "role": "assistant",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "id": str(int(datetime.datetime.now().timestamp()))
                }
            else:
                response_data = {
                    "type": "message",
                    "content": str(chat_response),
                    "role": "assistant",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "id": str(int(datetime.datetime.now().timestamp()))
                }
            
            # Send response back to client
            await websocket.send_json(response_data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "content": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        })

@app.post("/chat")
async def chat(request: Request):
    """Handle chat messages."""
    try:
        # Parse request data
        data = await request.json()
        content = data.get('content')
        
        if not content:
            raise HTTPException(status_code=400, detail="Message content is required")
            
        logger.info(f"Processing chat message: {content[:100]}...")  # Log first 100 chars
        
        # Get response from assistant and ensure it's properly awaited
        chat_response = await assistant.chat(content)
        
        # Create response data with primitive types
        timestamp = datetime.datetime.now()
        response_data = {
            "type": "message",
            "content": str(chat_response) if chat_response else "",
            "role": "assistant",
            "timestamp": timestamp.isoformat(),
            "id": str(int(timestamp.timestamp()))
        }
        
        # Convert to JSON-compatible format and return
        return JSONResponse(
            content=jsonable_encoder(response_data),
            status_code=200
        )
            
    except Exception as e:
        # Log the error
        logger.error(f"Error processing chat message: {str(e)}")
        
        # Create error response
        timestamp = datetime.datetime.now()
        error_data = {
            "type": "error",
            "content": str(e),
            "role": "assistant",
            "timestamp": timestamp.isoformat(),
            "id": str(int(timestamp.timestamp()))
        }
        
        # Return error response
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(error_data)
        )

@app.get("/tools")
async def list_tools():
    """List all available tools."""
    try:
        tools = await assistant._load_tools()
        return JSONResponse(content=jsonable_encoder(tools))
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/agents")
async def create_agent(agent: AgentCreate):
    """Create a new agent with specified tools."""
    try:
        # Initialize agent manager if not already done
        if not hasattr(assistant, 'agent_manager'):
            from tools.agent_manager import AgentManagerTool
            assistant.agent_manager = AgentManagerTool()

        # Create agent with specified tools
        agent_id = f"{agent.name.lower()}_{datetime.datetime.now().timestamp()}"
        result = await assistant.agent_manager.execute(
            command="create",
            agent_id=agent_id,
            role=agent.role,
            tools=agent.tools
        )
        
        return JSONResponse(content=jsonable_encoder({
            "agent_id": agent_id,
            "result": result
        }))
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/agents")
async def list_agents():
    """List all available agents."""
    try:
        if not hasattr(assistant, 'agent_manager'):
            return JSONResponse(content=[])
            
        result = await assistant.agent_manager.execute(command="list")
        return JSONResponse(content=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import List, Dict, Any
import json
import sys
import os
import logging
import datetime

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

# Store active connections
connections: Dict[str, WebSocket] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the assistant on startup."""
    global assistant
    try:
        assistant = Assistant()
        await assistant.initialize()
        logger.info("Assistant initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize assistant: {str(e)}")
        raise

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time chat."""
    try:
        # Log headers for debugging
        logger.info("WebSocket connection headers:")
        for header, value in websocket.headers.items():
            logger.info(f"{header}: {value}")

        # Accept all connections for now
        await websocket.accept()
        
        client_id = str(id(websocket))
        connections[client_id] = websocket
        logger.info(f"New WebSocket connection established: {client_id}")
        
        while True:
            try:
                message = await websocket.receive_text()
                logger.debug(f"Received message from {client_id}: {message}")
                
                # Parse the message
                try:
                    data = json.loads(message)
                    content = data.get('content', '')
                except json.JSONDecodeError:
                    content = message

                # Process with Claude Engineer
                response = await assistant.chat(content)

                # Send response back
                await websocket.send_json({
                    "type": "message",
                    "content": response,
                    "role": "assistant",
                    "timestamp": datetime.datetime.now().isoformat()
                })
                logger.debug(f"Sent response to {client_id}")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "content": "An error occurred while processing your message"
                })

    except Exception as e:
        logger.error(f"Error handling WebSocket connection: {str(e)}")
    finally:
        if client_id in connections:
            del connections[client_id]
            logger.info(f"Cleaned up connection: {client_id}")

@app.options("/ws")
async def websocket_options(request: Request):
    """Handle CORS preflight requests for WebSocket."""
    return {
        "headers": {
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
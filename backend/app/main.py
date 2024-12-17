from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from typing import List, Dict, Any
import json
import sys
import os
import logging
import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the backend directory to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ce3 import Assistant

app = FastAPI(title="Claude Engineer API")

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "ws://localhost:3000",
    "ws://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    client_id = None
    try:
        # Log connection attempt
        logger.info("WebSocket connection attempt")
        logger.info("Headers:")
        for k, v in websocket.headers.items():
            logger.info(f"{k}: {v}")

        # Accept connection
        await websocket.accept()
        client_id = str(id(websocket))
        connections[client_id] = websocket
        logger.info(f"New WebSocket connection established: {client_id}")
        
        # Send initial message
        await websocket.send_json({
            "type": "connection",
            "content": "Connected to Claude Engineer",
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        while True:
            try:
                # Receive message
                message = await websocket.receive_text()
                logger.info(f"Received message from {client_id}: {message}")
                
                # Parse message
                try:
                    data = json.loads(message)
                    content = data.get('content', '')
                    logger.info(f"Parsed content: {content}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    content = message

                # Process with Claude Engineer
                logger.info("Processing with Claude Engineer")
                response = await assistant.chat(content)
                logger.info(f"Got response: {response[:100]}...")  # Log first 100 chars

                # Send response
                await websocket.send_json({
                    "type": "message",
                    "content": response,
                    "role": "assistant",
                    "timestamp": datetime.datetime.now().isoformat()
                })
                logger.info(f"Sent response to {client_id}")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {client_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"An error occurred while processing your message: {str(e)}"
                    })
                except Exception as send_error:
                    logger.error(f"Failed to send error message: {str(send_error)}")

    except Exception as e:
        logger.error(f"Error handling WebSocket connection: {str(e)}")
    finally:
        if client_id and client_id in connections:
            del connections[client_id]
            logger.info(f"Cleaned up connection: {client_id}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
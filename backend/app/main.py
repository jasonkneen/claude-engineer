from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import List, Dict, Any
import json
import sys
import os

# Add the backend directory to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ce3 import Assistant

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
    assistant = await Assistant.create()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time chat."""
    await websocket.accept()
    client_id = str(id(websocket))
    connections[client_id] = websocket
    
    try:
        while True:
            message = await websocket.receive_text()
            
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
                "timestamp": None  # You can add timestamp if needed
            })

    except Exception as e:
        print(f"Error handling WebSocket: {str(e)}")
    finally:
        # Clean up connection
        if client_id in connections:
            del connections[client_id]

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import sys
import os
import logging
import datetime

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
    """Initialize the assistant on startup."""
    global assistant
    try:
        assistant = Assistant()
        await assistant.initialize()
        logger.info("Assistant initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize assistant: {str(e)}")
        raise

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
        
        try:
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
            json_compatible = jsonable_encoder(response_data)
            return JSONResponse(content=json_compatible, status_code=200)
            
        except Exception as chat_error:
            logger.error(f"Chat error: {str(chat_error)}")
            timestamp = datetime.datetime.now()
            error_data = {
                "type": "error",
                "content": str(chat_error),
                "role": "assistant",
                "timestamp": timestamp.isoformat(),
                "id": str(int(timestamp.timestamp()))
            }
            return JSONResponse(
                status_code=500,
                content=jsonable_encoder(error_data)
            )
            
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        timestamp = datetime.datetime.now()
        error_data = {
            "type": "error",
            "content": str(e),
            "role": "assistant",
            "timestamp": timestamp.isoformat(),
            "id": str(int(timestamp.timestamp()))
        }
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(error_data)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
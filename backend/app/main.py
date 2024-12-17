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

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages."""
    try:
        if not request.content:
            raise HTTPException(status_code=400, detail="Message content is required")
            
        logger.info(f"Processing chat message: {request.content[:100]}...")  # Log first 100 chars
        
        try:
            # Get response from assistant
            response = await assistant.chat(request.content)
            
            # Create response using Pydantic model
            timestamp = datetime.datetime.now()
            return ChatResponse(
                content=str(response) if response else "",
                timestamp=timestamp.isoformat(),
                id=str(int(timestamp.timestamp()))
            )
            
        except Exception as chat_error:
            logger.error(f"Chat error: {str(chat_error)}")
            error_response = ChatResponse(
                type="error",
                content=str(chat_error),
                timestamp=datetime.datetime.now().isoformat(),
                id=str(int(datetime.datetime.now().timestamp()))
            )
            return JSONResponse(
                status_code=500,
                content=jsonable_encoder(error_response)
            )
            
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        error_response = ChatResponse(
            type="error",
            content=str(e),
            timestamp=datetime.datetime.now().isoformat(),
            id=str(int(datetime.datetime.now().timestamp()))
        )
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(error_response)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
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
        data = await request.json()
        content = data.get('content')
        
        if not content:
            raise HTTPException(status_code=400, detail="Message content is required")
            
        logger.info(f"Processing chat message: {content[:100]}...")  # Log first 100 chars
        response = await assistant.chat(content)
        
        return {
            "type": "message",
            "content": response,
            "role": "assistant",
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
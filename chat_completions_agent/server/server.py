import json
import sys
import os
from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import asyncio
from queue import Queue
from threading import Thread
from openai import AsyncOpenAI

app = FastAPI()

# Configure OpenAI - you'll need to set OPENAI_API_KEY environment variable
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = "gpt-4-0125-preview"  # GPT-4 Turbo

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    model: Optional[str] = DEFAULT_MODEL

async def handle_chat_completion(messages, temperature=0.7, model=DEFAULT_MODEL):
    try:
        # Convert messages to the format OpenAI expects
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        # Call OpenAI API with new client
        response = await client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            temperature=temperature
        )
        
        return {
            "role": response.choices[0].message.role,
            "content": response.choices[0].message.content
        }
    except Exception as e:
        print(f"Error in chat completion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# HTTP endpoint
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    response = await handle_chat_completion(
        request.messages, 
        request.temperature,
        request.model
    )
    return {"choices": [{"message": response}]}

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_json()
            response = await handle_chat_completion(
                data["messages"], 
                data.get("temperature", 0.7),
                data.get("model", DEFAULT_MODEL)
            )
            await websocket.send_json({"choices": [{"message": response}]})
        except Exception as e:
            await websocket.send_json({"error": str(e)})

# STDIO handler
def handle_stdio():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            request = json.loads(line)
            loop = asyncio.new_event_loop()
            response = loop.run_until_complete(handle_chat_completion(
                request["messages"],
                request.get("temperature", 0.7),
                request.get("model", DEFAULT_MODEL)
            ))
            print(json.dumps({"choices": [{"message": response}]}))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        handle_stdio()
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
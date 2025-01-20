import os
import json
import time
import logging
import threading
import websocket
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum

class MemoryServerConfig:
    HOST = os.getenv("MEMORY_SERVER_HOST", "localhost")
    PORT = int(os.getenv("MEMORY_SERVER_PORT", "8000"))
    ENABLED = os.getenv("MEMORY_SERVER_ENABLED", "true").lower() == "true"
    RETRY_INTERVAL = int(os.getenv("MEMORY_SERVER_RETRY_INTERVAL", "5"))
    MAX_RETRIES = int(os.getenv("MEMORY_SERVER_MAX_RETRIES", "5"))

class MemoryType(Enum):
    ARCHIVED = "archived"  # Long-term archived memories

@dataclass
class Memory:
    content: str
    embedding: Optional[List[float]]  # Semantic embedding for search
    timestamp: float
    context: str  # Surrounding conversation context
    source: str  # Where this memory came from
    importance: float  # Importance score
    tags: List[str]  # Searchable tags
    metadata: Dict[str, Any]  # Additional flexible metadata
    
class MemoryServerClient:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ws: Optional[websocket.WebSocketApp] = None
        self.connected = False
        self.local_storage: List[Memory] = []
        self.local_path = os.path.join(os.path.expanduser("~"), ".ce3_memories.json")
        self._load_local_storage()
        self.retry_count = 0
        self.lock = threading.Lock()
        
        if MemoryServerConfig.ENABLED:
            self.connect()
            
    def connect(self):
        """Establish WebSocket connection to memory server"""
        if self.connected:
            return
            
        try:
            self.ws = websocket.WebSocketApp(
                f"ws://{MemoryServerConfig.HOST}:{MemoryServerConfig.PORT}",
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to memory server: {str(e)}")
            self._handle_connection_failure()
            
    def _on_open(self, ws):
        self.logger.info("Connected to memory server")
        self.connected = True
        self.retry_count = 0
        
        # Sync local memories to server
        self._sync_local_to_server()
        
    def _on_message(self, ws, message):
        """Handle incoming messages from server"""
        try:
            data = json.loads(message)
            if data.get("type") == "sync":
                self._handle_sync_message(data)
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            
    def _on_error(self, ws, error):
        self.logger.error(f"WebSocket error: {str(error)}")
        
    def _on_close(self, ws, close_status_code, close_msg):
        self.logger.warning("Disconnected from memory server")
        self.connected = False
        self._handle_connection_failure()
        
    def _handle_connection_failure(self):
        """Handle connection failures with retry logic"""
        if self.retry_count < MemoryServerConfig.MAX_RETRIES:
            self.retry_count += 1
            self.logger.info(f"Retrying connection in {MemoryServerConfig.RETRY_INTERVAL} seconds...")
            time.sleep(MemoryServerConfig.RETRY_INTERVAL)
            self.connect()
        else:
            self.logger.warning("Max retries reached, falling back to local storage only")
            
    def _sync_local_to_server(self):
        """Sync local memories to server after reconnection"""
        if not self.connected:
            return
            
        with self.lock:
            for memory_type in MemoryType:
                memories = self.local_storage[memory_type]
                for memory in memories:
                    self._send_to_server({
                        "type": "store",
                        "memory_type": memory_type.value,
                        "memory": asdict(memory)
                    })
                    
    def archive(self, content: str, context: str = "", source: str = "", tags: List[str] = None, **metadata) -> Memory:
        """Archive a memory with metadata"""
        memory = Memory(
            content=content,
            embedding=self._generate_embedding(content),
            timestamp=time.time(),
            context=context,
            source=source,
            importance=metadata.pop("importance", 0.5),
            tags=tags or [],
            metadata=metadata
        )
        
        if self.connected:
            self._send_to_server({
                "type": "archive",
                "memory": asdict(memory)
            })
        
        # Always keep local copy
        with self.lock:
            self.local_storage.append(memory)
            self._save_local_storage()
            
        return memory
            
    def recall(self, query: str = None, tags: List[str] = None, limit: int = 10) -> List[Memory]:
        """Recall memories using semantic search and/or tags"""
        if not query and not tags:
            return []
            
        query_embedding = self._generate_embedding(query) if query else None
        
        if self.connected:
            response = self._send_to_server({
                "type": "recall",
                "query_embedding": query_embedding,
                "tags": tags,
                "limit": limit
            })
            if response and "memories" in response:
                return [Memory(**m) for m in response["memories"]]
                
        # Local fallback uses simple similarity search
        memories = self.local_storage
        if tags:
            memories = [m for m in memories if any(t in m.tags for t in tags)]
        if query_embedding:
            memories = sorted(memories, 
                key=lambda m: self._cosine_similarity(query_embedding, m.embedding),
                reverse=True
            )
        return memories[:limit]
        
    def _send_to_server(self, data: dict):
        """Send data to WebSocket server with error handling"""
        if not self.connected:
            return
            
        try:
            self.ws.send(json.dumps(data))
        except Exception as e:
            self.logger.error(f"Error sending to server: {str(e)}")
            self.connected = False
            self._handle_connection_failure()
            
    def _handle_sync_message(self, data: dict):
        """Handle incoming sync messages from server"""
        memory_type = MemoryType(data["memory_type"])
        memories = [Memory(**m) for m in data["memories"]]
        
        with self.lock:
            self.local_storage[memory_type] = memories
            
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate semantic embedding for text"""
        # TODO: Implement proper embedding generation
        # For now return simple term frequency vector
        words = text.lower().split()
        return [words.count(w)/len(words) for w in set(words)]
        
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between vectors"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0
        num = sum(a * b for a, b in zip(v1, v2))
        den = sqrt(sum(a * a for a in v1)) * sqrt(sum(b * b for b in v2))
        return num / den if den else 0
        
    def _save_local_storage(self):
        """Save memories to local JSON file"""
        with open(self.local_path, 'w') as f:
            json.dump([asdict(m) for m in self.local_storage], f)
            
    def _load_local_storage(self):
        """Load memories from local JSON file"""
        if os.path.exists(self.local_path):
            with open(self.local_path) as f:
                data = json.load(f)
                self.local_storage = [Memory(**m) for m in data]
                
    def close(self):
        """Clean up resources"""
        self._save_local_storage()
        if self.ws:
            self.ws.close()


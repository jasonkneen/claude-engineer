import os
import json
import time
import math
import logging
import threading
import websocket
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class Memory:
    content: str
    embedding: Optional[List[float]] = None
    timestamp: float = time.time()
    context: str = ""
    source: str = ""
    importance: float = 0.5
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        self.tags = self.tags or []
        self.metadata = self.metadata or {}

class MemoryServerClient:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.logger = logging.getLogger(__name__)
        self.lock = threading.Lock()
        
        # Configure WebSocket connection
        self.ws_url = f"ws://{host}:{port}/ws"
        self.retry_interval = 5  # seconds
        self.max_retries = 5
        self.ws = None
        self.connected = False
        self.retry_count = 0
        
        # Initialize local storage
        self.local_storage = []  # Local memory cache
        self.local_path = os.path.join(os.path.expanduser("~"), ".memories.json")
        self._load_local_storage()
        
        # Establish connection
        self.connect()

    def connect(self):
        """Establish WebSocket connection to memory server"""
        if self.connected:
            return
            
        try:
            self.logger.info(f"Connecting to memory server at {self.ws_url}")
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message, 
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket connection in background thread
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True 
            wst.start()
        except Exception as e:
            self.logger.error(f"Failed to connect to memory server: {str(e)}")
            self._handle_connection_failure()
            
    def _on_open(self, ws):
        """Called when WebSocket connection is established"""
        self.logger.info("Connected to memory server")
        self.connected = True
        self.retry_count = 0

        # Send any cached memories to server
        self._sync_local_to_server()

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "stats":
                self._handle_stats_update(data)
            elif msg_type == "recall":
                self._handle_recall_response(data)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        self.logger.error(f"WebSocket error: {str(error)}")
        
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket disconnection"""
        self.logger.warning("Disconnected from memory server") 
        self.connected = False
        self._handle_connection_failure()
        
    def _handle_connection_failure(self):
        """Handle connection failure with retry logic"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.logger.info(f"Retrying connection in {self.retry_interval} seconds...")
            time.sleep(self.retry_interval)
            self.connect()
        else:
            self.logger.warning("Max retries reached, falling back to local storage only")

    def _sync_local_to_server(self):
        """Sync locally cached memories to server"""
        if not self.connected:
            return

        with self.lock:
            for memory in self.local_storage:
                self._send_to_server({
                    "type": "archive",
                    "memory": asdict(memory)
                })
                    
    def archive(self, content: str, context: str = "", source: str = "", 
            tags: List[str] = None, **metadata) -> Memory:
        """Archive a memory to the server"""
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

        # Try to send to server first
        if self.connected:
            self._send_to_server({
                "type": "archive",
                "memory": asdict(memory) 
            })

        # Always cache locally
        with self.lock:
            self.local_storage.append(memory)
            self._save_local_storage()

        return memory

    def recall(self, query: str = None, tags: List[str] = None, 
            limit: int = 10) -> List[Memory]:
        """Recall memories using semantic search and/or tags"""
        if not query and not tags:
            return []

        query_embedding = self._generate_embedding(query) if query else None
        
        # Try server first
        if self.connected:
            try:
                response = self._send_to_server({
                    "type": "recall",
                    "query": query,
                    "query_embedding": query_embedding,
                    "tags": tags,
                    "limit": limit
                })
                return [Memory(**m) for m in json.loads(response)]
            except Exception as e:
                self.logger.error(f"Error recalling from server: {str(e)}")
        
        # Fall back to local search
        results = []
        with self.lock:
            for memory in self.local_storage:
                score = 0
                
                # Score based on tag matches
                if tags:
                    matching_tags = set(memory.tags) & set(tags)
                    score += len(matching_tags) / len(tags)
                    
                # Score based on semantic similarity
                if query_embedding and memory.embedding:
                    sim = self._cosine_similarity(query_embedding, memory.embedding)
                    score += sim
                    
                if score > 0:
                    results.append((score, memory))
                    
            # Sort by score and return top matches
            results.sort(key=lambda x: x[0], reverse=True)
            return [m for _, m in results[:limit]]
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
        memories = [Memory(**m) for m in data["memories"]]
        
        with self.lock:
            self.local_storage = memories
            self._save_local_storage()
            
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


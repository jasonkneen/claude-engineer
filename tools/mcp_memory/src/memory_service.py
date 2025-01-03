import os
import json
import logging
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from datetime import datetime
from typing import List, Dict, Optional, Any

class MemoryService:
    def __init__(self, chroma_path: str = None, collection_name: str = "memories"):
        self.chroma_path = chroma_path or os.path.join(os.path.dirname(__file__), "chroma_db")
        os.makedirs(self.chroma_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(
                anonymized_telemetry=False,
                is_persistent=True
            )
        )
        
        # Set up embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.logger = logging.getLogger(__name__)
    
    def store_memory(self, content: str, tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Store a new memory with content and optional tags/metadata"""
        try:
            timestamp = datetime.utcnow().isoformat()
            memory_id = f"memory_{timestamp}"
            
            # Prepare metadata
            meta = {
                "timestamp": timestamp,
                "tags": tags or []
            }
            if metadata:
                meta.update(metadata)
            
            # Add to collection
            self.collection.add(
                documents=[content],
                metadatas=[meta],
                ids=[memory_id]
            )
            
            return memory_id
        except Exception as e:
            self.logger.error(f"Error storing memory: {e}")
            raise
    
    def retrieve_memory(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Retrieve memories based on semantic similarity to query"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )
            
            memories = []
            for i in range(len(results["ids"][0])):
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
                })
            
            return memories
        except Exception as e:
            self.logger.error(f"Error retrieving memories: {e}")
            raise
    
    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Search memories by tag"""
        try:
            results = self.collection.get(
                where={"tags": {"$contains": tag}}
            )
            
            memories = []
            for i in range(len(results["ids"])):
                memories.append({
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
            
            return memories
        except Exception as e:
            self.logger.error(f"Error searching by tag: {e}")
            raise
    
    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory by ID"""
        try:
            self.collection.delete(ids=[memory_id])
        except Exception as e:
            self.logger.error(f"Error deleting memory: {e}")
            raise

    def clear_all(self) -> None:
        """Clear all memories from collection"""
        try:
            self.collection.delete()
        except Exception as e:
            self.logger.error(f"Error clearing memories: {e}")
            raise


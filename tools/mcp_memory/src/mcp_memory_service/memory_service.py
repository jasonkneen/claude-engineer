import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import numpy as np
from loguru import logger

class MemoryService:
    def __init__(self, chroma_path: str = None, collection_name: str = "memories"):
        """Initialize the Memory Service with ChromaDB backend
        
        Args:
            chroma_path: Path to store ChromaDB files
            collection_name: Name of the ChromaDB collection
        """
        self.chroma_path = chroma_path or os.getenv("MCP_MEMORY_CHROMA_PATH", "./chroma_db")
        self._init_chroma_client(collection_name)
        
    def _init_chroma_client(self, collection_name: str):
        """Initialize ChromaDB client and collection"""
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.chroma_path,
            anonymized_telemetry=False
        )
        
        self.client = chromadb.Client(settings)
        
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Found existing collection: {collection_name}")
        except ValueError:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Created new collection: {collection_name}")

    def store_memory(self, content: str, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None) -> str:
        """Store a new memory with content and optional metadata/tags
        
        Args:
            content: The text content to store
            metadata: Optional metadata dictionary 
            tags: Optional list of tags
            
        Returns:
            memory_id: Unique ID of stored memory
        """
        if not content:
            raise ValueError("Content cannot be empty")
            
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(content)}"
        
        metadata = metadata or {}
        metadata.update({
            "created_at": datetime.now().isoformat(),
            "content_length": len(content)
        })
        
        if tags:
            metadata["tags"] = tags
            
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[memory_id]
        )
        
        return memory_id

    def retrieve_memory(self, query: str, n_results: int = 5, min_similarity: float = 0.0) -> List[Dict]:
        """Retrieve memories similar to query text
        
        Args:
            query: Query text to search for
            n_results: Max number of results to return
            min_similarity: Minimum similarity score threshold
            
        Returns:
            List of matching memories with metadata
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        memories = []
        for idx, (doc, metadata, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            if distance >= min_similarity:
                memories.append({
                    "id": results["ids"][0][idx],
                    "content": doc,
                    "metadata": metadata,
                    "similarity": float(1 - distance)
                })
                
        return memories

    def search_by_tag(self, tag: str) -> List[Dict]:
        """Search memories by tag
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of memories with matching tag
        """
        results = self.collection.get(
            where={"tags": {"$contains": tag}}
        )
        
        memories = []
        for idx, (doc, metadata) in enumerate(zip(results["documents"], results["metadatas"])):
            memories.append({
                "id": results["ids"][idx],
                "content": doc,
                "metadata": metadata
            })
            
        return memories

    def delete_memory(self, memory_id: str):
        """Delete a memory by ID
        
        Args:
            memory_id: ID of memory to delete
        """
        self.collection.delete(ids=[memory_id])
        
    def update_memory(self, memory_id: str, content: Optional[str] = None, 
                    metadata: Optional[Dict] = None):
        """Update an existing memory's content and/or metadata
        
        Args:
            memory_id: ID of memory to update
            content: New content (optional)
            metadata: New metadata to merge (optional) 
        """
        if not content and not metadata:
            return
            
        existing = self.collection.get(ids=[memory_id])
        if not existing["ids"]:
            raise ValueError(f"Memory {memory_id} not found")
            
        update_metadata = existing["metadatas"][0].copy()
        if metadata:
            update_metadata.update(metadata)
            
        self.collection.update(
            ids=[memory_id],
            documents=[content] if content else None,
            metadatas=[update_metadata] if metadata else None
        )
        
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory collection
        
        Returns:
            Dictionary with collection statistics
        """
        results = self.collection.get()
        return {
            "total_memories": len(results["ids"]),
            "total_unique_tags": len(set(
                tag for metadata in results["metadatas"] 
                for tag in metadata.get("tags", [])
            )),
            "oldest_memory": min(
                (metadata["created_at"] for metadata in results["metadatas"]),
                default=None
            ),
            "newest_memory": max(
                (metadata["created_at"] for metadata in results["metadatas"]),
                default=None
            )
        }


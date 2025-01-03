"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""

from mcp_memory_service.models.memory import Memory

import chromadb
import json
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any, Tuple, Set, Optional
from datetime import datetime

from .base import MemoryStorage
from ..models.memory import Memory, MemoryQueryResult
from ..utils.hashing import generate_content_hash
import mcp.types as types

logger = logging.getLogger(__name__)

class ChromaMemoryStorage(MemoryStorage):
    def __init__(self, path: str):
        """Initialize ChromaDB storage with proper embedding function."""
        self.path = path
        
        # Initialize sentence transformer first
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create embedding function for ChromaDB
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2'
        )
        
        # Initialize ChromaDB with new client format
        self.client = chromadb.PersistentClient(
            path=path
        )
        
        # Get or create collection with proper embedding function
        try:
            self.collection = self.client.get_or_create_collection(
                name="memory_collection",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
            logger.info("Collection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise

    def sanitized(self, tags):
        if tags is None:
            return json.dumps("")
        
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            raise ValueError("Tags must be a string or list of strings")
            
        # Ensure all elements are strings and remove any invalid ones    
        sanitized = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            tag = tag.strip()
            if tag:
                sanitized.append(tag)
                
        logger.info(f"****Sanitized: {json.dumps(sanitized)}")
        # Convert to JSON string
        return json.dumps(sanitized)

    def _format_metadata_for_chroma(self, memory: Memory) -> dict:
        """Formats metadata for ChromaDB, ensuring no list types are included."""
        metadata = {
            "type": memory.memory_type,
            "content_hash": memory.content_hash,
        }
        return metadata

    async def store(self, memory: Memory) -> Tuple[bool, str]:
        """Store a memory with proper embedding handling."""
        try:
            # Check for duplicates
            existing = self.collection.get(
                where={"content_hash": memory.content_hash}
            )
            if existing["ids"]:
                return False, "Duplicate content detected"
            
            # Format metadata properly
            metadata = self._format_metadata_for_chroma(memory)
            
            # Add additional metadata
            metadata.update(memory.metadata)

            # Generate ID based on content hash
            memory_id = memory.content_hash
            
            # Add to collection - embedding will be automatically generated
            self.collection.add(
                documents=[memory.content],
                metadatas=[metadata],
                ids=[memory_id]
            )
            
            return True, f"Successfully stored memory with ID: {memory_id}"
            
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}")
            return False

    async def search_by_tag(self, tags: List[str]) -> List[Memory]:
       """Retrieves memories that match any of the specified tags."""
       try:
           results = self.collection.get(
               include=["metadatas", "documents"]
           )

           memories = []
           if results["ids"]:
               for i, doc in enumerate(results["documents"]):
                   memory_meta = results["metadatas"][i]
                    
                    # Deserialize tags from the string
                   try:
                       retrieved_tags_string = memory_meta.get("tags", "[]")
                       retrieved_tags = json.loads(retrieved_tags_string)
                   except json.JSONDecodeError:
                        retrieved_tags = [] # Handle the case where the stored tags are not valid JSON
                    
                   # Check if any of the searched tags are in the retrieved tags list
                   if any(tag in retrieved_tags for tag in tags):
                       memory = Memory(
                           content=doc,
                           content_hash=memory_meta["content_hash"],
                           tags=retrieved_tags,
                           memory_type=memory_meta.get("type")
                        )
                       memories.append(memory)
            
           return memories
        
       except Exception as e:
           logger.error(f"Error searching by tags: {e}")
           return []
    
    async def delete_by_tag(self, tag: str) -> Tuple[int, str]:
        """Deletes memories that match the specified tag."""
        try:
            # Get all the documents from ChromaDB
            results = self.collection.get(
                include=["metadatas"]
            )

            ids_to_delete = []
            if results["ids"]:
                for i, meta in enumerate(results["metadatas"]):
                    try:
                        retrieved_tags_string = meta.get("tags", "[]")
                        retrieved_tags = json.loads(retrieved_tags_string)
                    except json.JSONDecodeError:
                        retrieved_tags = []

                    if tag in retrieved_tags:
                        ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, f"No memories found with tag: {tag}"

            # Delete memories
            self.collection.delete(ids=ids_to_delete)

            return len(ids_to_delete), f"Successfully deleted {len(ids_to_delete)} memories with tag: {tag}"

        except Exception as e:
            logger.error(f"Error deleting memories by tag: {e}")
            return 0, f"Error deleting memories by tag: {e}"

        
    async def delete(self, content_hash: str) -> Tuple[bool, str]:
        """Delete a memory by its hash."""
        try:
            # First check if the memory exists
            existing = self.collection.get(
                where={"content_hash": content_hash}
            )
            
            if not existing["ids"]:
                return False, f"No memory found with hash {content_hash}"
            
            # Delete the memory
            self.collection.delete(
                where={"content_hash": content_hash}
            )
            
            return True, f"Successfully deleted memory with hash {content_hash}"
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            return False, f"Error deleting memory: {str(e)}"


    async def cleanup_duplicates(self) -> Tuple[int, str]:
        """Remove duplicate memories based on content hash."""
        try:
            # Get all memories
            results = self.collection.get()
            
            if not results["ids"]:
                return 0, "No memories found in database"
            
            # Track seen hashes and duplicates
            seen_hashes: Set[str] = set()
            duplicates = []
            
            for i, metadata in enumerate(results["metadatas"]):
                content_hash = metadata.get("content_hash")
                if not content_hash:
                    # Generate hash if missing
                    content_hash = generate_content_hash(results["documents"][i], metadata)
                
                if content_hash in seen_hashes:
                    duplicates.append(results["ids"][i])
                else:
                    seen_hashes.add(content_hash)
            
            # Delete duplicates if found
            if duplicates:
                self.collection.delete(
                    ids=duplicates
                )
                return len(duplicates), f"Successfully removed {len(duplicates)} duplicate memories"
            
            return 0, "No duplicate memories found"
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicates: {str(e)}")
            return 0, f"Error cleaning up duplicates: {str(e)}"

    def _format_metadata_for_chroma(self, memory: Memory) -> Dict[str, Any]:
        """Format metadata to be compatible with ChromaDB requirements."""
        metadata = {
            "content_hash": memory.content_hash,
            "memory_type": memory.memory_type if memory.memory_type else "",
            "timestamp": str(memory.timestamp.timestamp())
        }
        
        # Store tags as a list in metadata
        if memory.tags:
            metadata["tags"] = memory.tags
        
        # Add any additional metadata that's simple types
        for key, value in memory.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        
        return metadata

    async def retrieve(self, query: str, n_results: int = 5) -> List[MemoryQueryResult]:
        """Retrieve memories using semantic search."""
        try:
            # Query using the embedding function
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["ids"] or not results["ids"][0]:
                return []
            
            memory_results = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                
                # Reconstruct memory object
                memory = Memory(
                    content=results["documents"][0][i],
                    content_hash=metadata["content_hash"],
                    tags=metadata.get("tags", []),
                    memory_type=metadata.get("memory_type", ""),
                )
                
                # Calculate cosine similarity from distance
                distance = results["distances"][0][i]
                similarity = 1 - distance
                
                memory_results.append(MemoryQueryResult(memory, similarity))
            
            return memory_results
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return []
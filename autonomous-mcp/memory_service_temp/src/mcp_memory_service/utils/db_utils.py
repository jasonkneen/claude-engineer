"""Utilities for database validation and health checks."""
from typing import Dict, Any, Tuple
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

async def validate_database(storage) -> Tuple[bool, str]:
    """Validate database health and configuration."""
    try:
        # Check if collection exists and is accessible
        collection_info = storage.collection.count()
        if collection_info == 0:
            logger.info("Database is empty but accessible")
        
        # Verify embedding function is working
        test_text = "Database validation test"
        embedding = storage.embedding_function([test_text])
        if not embedding or len(embedding) == 0:
            return False, "Embedding function is not working properly"
        
        # Test basic operations
        test_id = "test_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Test add
        storage.collection.add(
            documents=[test_text],
            metadatas=[{"test": True}],
            ids=[test_id]
        )
        
        # Test query
        query_result = storage.collection.query(
            query_texts=[test_text],
            n_results=1
        )
        if not query_result["ids"]:
            return False, "Query operation failed"
        
        # Clean up test data
        storage.collection.delete(ids=[test_id])
        
        return True, "Database validation successful"
    except Exception as e:
        logger.error(f"Database validation failed: {str(e)}")
        return False, f"Database validation failed: {str(e)}"

def get_database_stats(storage) -> Dict[str, Any]:
    """Get detailed database statistics."""
    try:
        count = storage.collection.count()
        
        # Get collection info
        collection_info = {
            "total_memories": count,
            "embedding_function": storage.embedding_function.__class__.__name__,
            "metadata": storage.collection.metadata
        }
        
        # Get storage info
        db_path = storage.path
        size = 0
        for root, dirs, files in os.walk(db_path):
            size += sum(os.path.getsize(os.path.join(root, name)) for name in files)
        
        storage_info = {
            "path": db_path,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2)
        }
        
        return {
            "collection": collection_info,
            "storage": storage_info,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

async def repair_database(storage) -> Tuple[bool, str]:
    """Attempt to repair database issues."""
    try:
        # Validate current state
        is_valid, message = await validate_database(storage)
        if is_valid:
            return True, "Database is already healthy"
        
        # Backup current embeddings and metadata
        try:
            existing_data = storage.collection.get()
        except Exception as backup_error:
            logger.error(f"Could not backup existing data: {str(backup_error)}")
            existing_data = None
        
        # Recreate collection
        storage.client.delete_collection("memory_collection")
        storage.collection = storage.client.create_collection(
            name="memory_collection",
            metadata={"hnsw:space": "cosine"},
            embedding_function=storage.embedding_function
        )
        
        # Restore data if backup was successful
        if existing_data and existing_data["ids"]:
            storage.collection.add(
                documents=existing_data["documents"],
                metadatas=existing_data["metadatas"],
                ids=existing_data["ids"]
            )
        
        # Validate repair
        is_valid, message = await validate_database(storage)
        if is_valid:
            return True, "Database successfully repaired"
        else:
            return False, f"Repair failed: {message}"
            
    except Exception as e:
        logger.error(f"Error repairing database: {str(e)}")
        return False, f"Error repairing database: {str(e)}"
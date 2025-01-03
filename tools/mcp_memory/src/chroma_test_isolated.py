import chromadb # pip install chromadb
import json # pip install json
import hashlib # pip install hashlib
import logging # pip install logging
import asyncio # pip install asyncio
import os # pip install os
from typing import List, Tuple, Dict, Optional, Any # pip install typing
from dataclasses import dataclass # pip install dataclasses
from sentence_transformers import SentenceTransformer # pip install sentence-transformers
from chromadb.utils import embedding_functions # pip install chromadb
from mcp_memory_service.models.memory import Memory,MemoryQueryResult # pip install mcp-memory-service
import shutil # For removing the storage directory

os.environ["CHROMA_DISABLE_TELEMETRY"] = "1"

import time # pip install time

start_timestamp = time.time()  # Current time
end_timestamp = start_timestamp + 60 * 60  # One hour from now

# Or for specific dates:
from datetime import datetime, date, timedelta # pip install datetime

def create_datetime(year, month, day, hour, minute, second):
    return datetime(year, month, day, hour, minute, second)

# Create datetime objects for January 1 and December 31 of the current year 
dt = create_datetime(datetime.now().year, 1, 1, 12, 0, 0)  # January 1, current year, 12:00:00
start_timestamp = dt.timestamp()

dt2 = create_datetime(datetime.now().year, 12, 31, 12, 0, 0)  # December 31, current year, 12:00:00
end_timestamp = dt2.timestamp()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Memory:
    content: str
    content_hash: str
    tags: List[str]
    memory_type: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: float = time.time()  # Add timestamp with default current time

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Ensure metadata is JSON serializable
        self.metadata = {
            key: (value.isoformat() if isinstance(value, date) else value)
            for key, value in self.metadata.items()
        }

@dataclass
class MemoryQueryResult:
    memory: Memory
    similarity: Optional[float] = None
    
def generate_content_hash(content: str, metadata: Dict[str, Any]) -> str:
    """Generates a SHA-256 hash of the content and metadata."""
    # Convert non-serializable fields in metadata to serializable formats
    serializable_metadata = {
        key: (value.isoformat() if isinstance(value, date) else value)
        for key, value in metadata.items()
    }
    combined = content + json.dumps(serializable_metadata, sort_keys=True)  # Sort keys for consistent hashing
    return hashlib.sha256(combined.encode()).hexdigest()

class ChromaMemoryStorage:
    def __init__(self, path: str = "chroma_db"):
        """Initializes ChromaDB storage."""
        self.path = path
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2'
        )
        # Attention!!! Remove the storage directory before initializing
        shutil.rmtree(self.path, ignore_errors=True)

        try:
            self.client = chromadb.PersistentClient(path=self.path)
            self.collection = self.client.get_or_create_collection(
                name="memory_collection",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
            logger.info("ChromaDB collection initialized successfully.")
        except Exception as e:
            logger.exception("Error initializing ChromaDB:")
            raise

    def sanitize_tags(self, tags: Optional[Any]) -> List[str]:
        """Sanitizes tags to ensure they are a list of non-empty strings."""
        if tags is None:
            return []

        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            logger.warning(f"Invalid tag format: {type(tags)}. Expected string or list.")
            return []

        sanitized_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        return sanitized_tags

    def _format_metadata_for_chroma(self, memory: Memory) -> Dict[str, Any]:
        """Formats metadata for ChromaDB."""
        metadata = {
            "type": memory.memory_type,
            "content_hash": memory.content_hash,
            "tags": json.dumps(memory.tags) if memory.tags else None,  # Store tags as list in ChromaDB
            "timestamp": memory.timestamp,  # Include the timestamp in the metadata
        }
        metadata.update(memory.metadata)
        return metadata

    @staticmethod
    def get_timestamp_range(start_date: date, end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Generates a timestamp range for querying based on start and end dates.

        Args:
            start_date: The start date (mandatory).
            end_date: The end date (optional). If None, it defaults to the end of the start date.

        Returns:
            A dictionary representing the where clause for ChromaDB, or an empty dictionary if start_date is invalid.
        """
        if not isinstance(start_date, date):
            raise TypeError("start_date must be a datetime.date object")

        if end_date is not None and not isinstance(end_date, date):
            raise TypeError("end_date must be a datetime.date object or None")

        if end_date is None:
            end_date = start_date

        start_datetime = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0) # Start of the day
        end_datetime = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59) # End of the day

        start_timestamp = start_datetime.timestamp()
        end_timestamp = end_datetime.timestamp()

        where_clause = {
            "$and": [
                {"timestamp": {"$gte": start_timestamp}},
                {"timestamp": {"$lte": end_timestamp}}
            ]
        }
        return where_clause

    async def store(self, memory: Memory) -> Tuple[bool, Optional[str]]:
        """Stores a memory in ChromaDB."""
        try:
            existing = self.collection.get(where={"content_hash": memory.content_hash})
            if existing["ids"]:
                return False, "Duplicate content detected."

            metadata = self._format_metadata_for_chroma(memory)
            self.collection.add(
                documents=[memory.content],
                metadatas=[metadata],
                ids=[memory.content_hash]
            )
            return True, None
        except Exception as e:
            logger.exception("Error storing memory:")
            return False, str(e)

    async def search_by_tag(self, tags: List[str]) -> List[Memory]:
        """Retrieves memories matching any of the specified tags."""
        try:
            results = self.collection.get(include=["metadatas", "documents"])
            memories = []
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i]
                logger.debug(f"Retrieved memory timestamp: {metadata.get('timestamp')}")
                try:
                    retrieved_tags = json.loads(metadata.get("tags", "[]"))
                except json.JSONDecodeError:
                    retrieved_tags = []
                    logger.warning(f"Invalid JSON in tags metadata: {metadata.get('tags')}")
                if any(tag in retrieved_tags for tag in tags):
                    mem = Memory(
                        content=doc,
                        content_hash=metadata["content_hash"],
                        tags=retrieved_tags,
                        memory_type=metadata.get("type"),
                        metadata={k: v for k, v in metadata.items() if k not in ["type", "content_hash", "tags"]}
                    )
                    memories.append(mem)
            return memories
        except Exception as e:
            logger.exception("Error searching by tags:")
            return []

    async def delete_by_tag(self, tag: str) -> Tuple[int, Optional[str]]:
        """Deletes memories with the specified tag."""
        try:
            results = self.collection.get(include=["metadatas"])
            ids_to_delete = []
            for i, meta in enumerate(results["metadatas"]):
                try:
                    retrieved_tags = json.loads(meta.get("tags", "[]"))
                except json.JSONDecodeError:
                    retrieved_tags = []
                    logger.warning(f"Invalid JSON in tags metadata: {meta.get('tags')}")
                # The crucial fix is here: compare with elements of the list
                if tag in retrieved_tags:
                    ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, f"No memories found with tag: {tag}"

            self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete), None
        except Exception as e:
            logger.exception("Error deleting memories by tag:")
            return 0, str(e)

    async def recall(self, n_results: int = 5, start_timestamp: Optional[float] = None, end_timestamp: Optional[float] = None) -> List["MemoryQueryResult"]:
        try:
            where_clause = {}
            if start_timestamp is not None and end_timestamp is not None:
                where_clause = {
                    "$and": [
                        {"timestamp": {"$gte": start_timestamp}},
                        {"timestamp": {"$lte": end_timestamp}}
                    ]
                }
            logger.info(f"Where clause: {where_clause}")

            results = self.collection.get(
                where=where_clause,
                limit=n_results,
                include=["metadatas", "documents"] # Removed "distances" here
            )

            if not results.get("ids") or not results["ids"]:
                logger.info("No memories found matching the criteria.")
                return []
            
            memory_results = []
            for i in range(len(results["ids"])):
                metadata = results["metadatas"][i]
                try:
                    retrieved_tags = json.loads(metadata.get("tags", "[]"))
                    logger.debug(f"Retrieved memory timestamp: {metadata.get('timestamp')}")
                except json.JSONDecodeError:
                    retrieved_tags = []
                    logger.warning(f"Invalid JSON in tags metadata: {metadata.get('tags')}")
                memory = Memory(
                    content=results["documents"][i],
                    content_hash=metadata["content_hash"],
                    tags=retrieved_tags,
                    memory_type=metadata.get("type", ""),
                    timestamp=metadata.get("timestamp"),
                    metadata={k: v for k, v in metadata.items() if k not in ["type", "content_hash", "tags", "timestamp"]}
                )
                memory_results.append(MemoryQueryResult(memory)) # Removed similarity here

            return memory_results

        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return []

    async def delete_by_timeframe(self, start_date: Optional[datetime.date] = None, end_date: Optional[datetime.date] = None, tag: Optional[str] = None) -> Tuple[int, Optional[str]]:
        """Deletes memories within a timeframe and optionally filtered by tag."""
        try:
            if start_date is None:
                raise ValueError("start_date is mandatory")

            where_clause = self.get_timestamp_range(start_date, end_date)
            logger.debug(f"Where clause: {where_clause}")

            results = self.collection.get(include=["metadatas"], where=where_clause)
            ids_to_delete = []

            if results.get("ids"): # Check if there are any results before iterating
                for i, meta in enumerate(results["metadatas"]):
                    try:
                        retrieved_tags = json.loads(meta.get("tags", "[]"))
                    except json.JSONDecodeError:
                        retrieved_tags = []
                        logger.warning(f"Invalid JSON in tags metadata: {meta.get('tags')}")

                    if tag is None or tag in retrieved_tags: # Check if tag is None or if the tag is in the retrieved tags
                        ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, "No memories found matching the criteria."

            self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete), None

        except Exception as e:
            logger.exception("Error deleting memories by timeframe:")
            return 0, str(e)

    async def delete_before_date(self, before_date: datetime.date, tag: Optional[str] = None) -> Tuple[int, Optional[str]]:
        """Deletes memories before a given date and optionally filtered by tag."""
        try:
            before_datetime = datetime(before_date.year, before_date.month, before_date.day, 23, 59, 59) # End of the day
            before_timestamp = before_datetime.timestamp()

            where_clause = {"timestamp": {"$lt": before_timestamp}}  # $lt: less than

            results = self.collection.get(include=["metadatas"], where=where_clause)
            ids_to_delete = []

            if results.get("ids"):
                for i, meta in enumerate(results["metadatas"]):
                    try:
                        retrieved_tags = json.loads(meta.get("tags", "[]"))
                    except json.JSONDecodeError:
                        retrieved_tags = []
                        logger.warning(f"Invalid JSON in tags metadata: {meta.get('tags')}")

                    if tag is None or tag in retrieved_tags:
                        ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, "No memories found matching the criteria."

            self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete), None

        except Exception as e:
            logger.exception("Error deleting memories before date:")
            return 0, str(e)


    async def cleanup(self):
        """Cleans up all data in the ChromaDB."""
        try:
            # Delete the collection
            self.client.delete_collection(name="memory_collection")
            logger.info("ChromaDB collection deleted successfully.")

            # Recreate the collection
            self.collection = self.client.get_or_create_collection(
                name="memory_collection",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
            logger.info("ChromaDB collection recreated successfully.")
        except Exception as e:
            logger.exception("Error during ChromaDB cleanup:")
            raise

async def main():
    storage = ChromaMemoryStorage()

    today = datetime.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    tomorrow = today + timedelta(days=1)

    mem_data = [
        {"content": "Meeting with team tomorrow at 10 AM", "memory_type": "calendar", "tags": ["meeting", "important"]},
        {"content": "Review ML model performance metrics", "memory_type": "todo", "tags": ["ml", "review"]},
        {"content": "Another meeting", "memory_type": "calendar", "tags": ["meeting", "test"]},
        {"content": "unrelated", "memory_type": "note", "tags": ["note","important"]},
        {"content": "Tagging test", "memory_type": "info", "tags": ['technical', 'test']},
        {"content": "Review ML model performance metrics", "memory_type": "todo", "tags": "ml,review"},
        {"content": "Today's memory", "memory_type": "test", "tags": ["test"], "date": today},
        {"content": "Yesterday's memory", "memory_type": "test", "tags": ["test,important"], "date": yesterday},
        {"content": "Memory two days ago", "memory_type": "test", "tags": ["test"], "date": two_days_ago},
        {"content": "Tomorrow's memory", "memory_type": "test", "tags": ["test"], "date": tomorrow},
        {"content": "Old Important memory", "memory_type": "test", "tags": ["important"], "date": two_days_ago}
    ] # checking for different tag formats even if it's not a list or string

    for data in mem_data:
        tags = storage.sanitize_tags(data["tags"]) # Sanitize before creating the hash

        date = data.get("date") # Get the date or None if it does not exist
        if date: # Check if the date exists
            dt = datetime(date.year, date.month, date.day, 12, 0, 0)
            timestamp = dt.timestamp()
            mem = Memory(content=data["content"], content_hash=generate_content_hash(data["content"], data), tags=tags, memory_type=data["memory_type"], timestamp=timestamp)
        else:
            mem = Memory(content=data["content"], content_hash=generate_content_hash(data["content"], data), tags=tags, memory_type=data["memory_type"])
        success, err = await storage.store(mem)
        logger.info(f"Store result for '{mem.content}': {success}, {err}")



    # Search for "meeting"
    res = await storage.search_by_tag(["meeting"])
    assert len(res) == 2, f'Expected 2 "meeting" memories, but found {len(res)}'
    logger.info(f"Search results for tag 'meeting' before deletion: {len(res)}")
    for r in res:
        logger.debug(f"  {r}")
    
    # Delete "meeting"
    count, err = await storage.delete_by_tag("meeting")
    logger.info(f"Delete count for tag 'meeting': {count}, {err}")
    assert count == 2, f'Expected 2 "meeting" memories, but deleted {count}'
 
    # Search again
    res = await storage.search_by_tag(["meeting"])
    logger.info(f"Search results for tag 'meeting' after deletion: {len(res)}")
    assert len(res) == 0, f'Expected 0 "meeting" memories, but found {len(res)}'
    for r in res:
        logger.debug(f"  {r}")
    
    # Search for "ml"
    res = await storage.search_by_tag(["ml"])
    logger.info(f"Search results for tag 'ml' after deletion of 'meeting': {len(res)}")
    assert len(res) == 1, f'Expected 1 "ml" memory, but found {len(res)}'
    for r in res:
        logger.debug(f" {r}")
    
    # Search for "important"
    res = await storage.search_by_tag(["important"])
    logger.info(f"Search results for tag 'important' after deletion of 'meeting': {len(res)}")
    assert len(res) == 2, f'Expected 2 "important" memory, but found {len(res)}'
    for r in res:
        logger.debug(f" {r}")
    
    # Search for "note"
    res = await storage.search_by_tag(["note"])
    logger.info(f"Search results for tag 'note' after deletion of 'meeting': {len(res)}")
    assert len(res) == 1, f'Expected 1 "note" memory, but found {len(res)}'
    for r in res:
        logger.debug(f" {r}")
    
    # Search for "test"
    res = await storage.search_by_tag(["test"])
    logger.info(f"Search results for tag 'test' after deletion of 'meeting': {len(res)}")
    assert len(res) == 4, f'Expected 4 "test" memories, but found {len(res)}'
    for r in res:
        logger.debug(f" {r}")
    
    # Search for "technical"
    res = await storage.search_by_tag(["technical"])
    logger.info(f"Search results for tag 'technical' after deletion of 'meeting': {len(res)}")
    assert len(res) == 1, f'Expected 1 "technical" memory, but found {len(res)}'
    for r in res:
        logger.debug(f" {r}")
    
    # Search by timestamp
    res = await storage.recall(start_timestamp=start_timestamp, end_timestamp=end_timestamp)
    logger.info(f"Search results for start_timestamp: {start_timestamp}, end_timestamp: {end_timestamp}: {len(res)}")
    assert len(res) == 5, f'Expected 5 memories, but found {len(res)}'
    for r in res:
        logger.debug(f" {r}")
    
    # Delete memories from today with the tag "important"
    count, err = await storage.delete_by_timeframe(start_date=today, tag="important")
    assert count == 1, f"Expected 1 'important' memory to be deleted, but {count} were deleted."
    logger.info(f"Method delete_by_timeframe with Tag 'important' - Deleted {count} memories")

    # Delete all memories from today (regardless of tags)
    count, err = await storage.delete_by_timeframe(start_date=today)
    assert count == 4, f"Expected 4 memory to be deleted, but {count} were deleted."
    logger.info(f"Method delete_by_timeframe without Tag - Deleted {count} memories")

    # Test deleting before today with tag "important"
    count, err = await storage.delete_before_date(before_date=today, tag="important")
    assert count == 1, f"Expected 1 'important' memory to be deleted, but {count} were deleted."
    logger.info(f"Deleted {count} 'important' memories before today")

    # Test deleting before yesterday
    count, err = await storage.delete_before_date(before_date=yesterday)
    assert count == 2, f"Expected 1 memory to be deleted, but {count} were deleted."
    logger.info(f"Deleted {count} memories before yesterday")

    # Test deleting before tomorrow
    count, err = await storage.delete_before_date(before_date=tomorrow)
    assert count == 1, f"Expected 1 memory to be deleted, but {count} were deleted."
    logger.info(f"Deleted {count} memories before tomorrow")

    await storage.cleanup()
    logger.info("Cleanup complete")
    results = storage.collection.get()
    logger.info(f"Collection size after cleanup: {len(results.get('ids', []))}")

    assert err == None, f'Expected no error, but got {err}'

if __name__ == "__main__":
    asyncio.run(main())
"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
from mcp.server.models import InitializationOptions
from mcp_memory_service.server import MemoryServer
from mcp_memory_service.utils.hashing import generate_content_hash
from mcp_memory_service.models.memory import Memory
import mcp.types as types

# Configure logging to output to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('memory_test.log')
    ]
)
logger = logging.getLogger(__name__)

def print_separator(title):
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50 + "\n")
    logger.info("\n" + "="*50)
    logger.info(f" {title} ")
    logger.info("="*50 + "\n")

async def test_management_features():
    try:
        # Initialize the server
        print_separator("Initializing Server")
        memory_server = MemoryServer()
        await memory_server.initialize()
        print("Server initialized successfully")

        # 1. Test store_memory
        print_separator("Testing store_memory")
        test_memories = [
            {
                "content": "Important meeting with team tomorrow at 10 AM",
                "metadata": {
                    "type": "calendar",
                    "tags": "meeting,important"
                }
            },
            {
                "content": "Need to review the ML model performance metrics",
                "metadata": {
                    "type": "todo",
                    "tags": "ml,review"
                }
            },
            {
                "content": "Remember to backup the database weekly",
                "metadata": {
                    "type": "reminder",
                    "tags": "backup,database"
                }
            }
        ]

        stored_memories = []
        for memory_data in test_memories:
            print(f"Storing memory: {json.dumps(memory_data, indent=2)}")
            
            # Create Memory object directly
            # tags = [tag.strip() for tag in memory_data["metadata"].get("tags", "").split(",") if tag.strip()]
            # memory = Memory(
            #     content=memory_data["content"],
            #     content_hash=generate_content_hash(memory_data["content"], memory_data["metadata"]),
            #     tags=tags,
            #     memory_type=memory_data["metadata"].get("type"),
            #     metadata=memory_data["metadata"]
            # )
            
            response = await memory_server.handle_store_memory(memory_data)
            
            print(f"Store response: [{response[0].text}]")
            if "Successfully stored memory" in response[0].text:
                tags = [tag.strip() for tag in memory_data["metadata"].get("tags", "").split(",") if tag.strip()]
                memory = Memory(
                    content=memory_data["content"],
                    content_hash=generate_content_hash(memory_data["content"], memory_data["metadata"]),
                    tags=tags,
                    memory_type=memory_data["metadata"].get("type"),
                    metadata=memory_data["metadata"]
                )
                stored_memories.append(memory)

        # 2. Test retrieve_memory
        print_separator("Testing retrieve_memory")
        query = {
            "query": "important meeting tomorrow",
            "n_results": 2
        }
        print(f"Testing retrieval with query: {json.dumps(query, indent=2)}")
        results = await memory_server.storage.retrieve(query["query"], query["n_results"])
        print(f"Retrieved {len(results)} results")
        for idx, result in enumerate(results):
            print(f"Result {idx + 1}:")
            print(f"  Content: {result.memory.content}")
            print(f"  Tags: {result.memory.tags}")
            print(f"  Score: {result.relevance_score}")

        # 3. Test search_by_tag
        print_separator("Testing search_by_tag")
        test_tag = "meeting"
        print(f"Searching for memories with tag: {test_tag}")
        tag_results = await memory_server.storage.search_by_tag([test_tag])
        print(f"Found {len(tag_results)} memories with tag '{test_tag}'")
        for idx, memory in enumerate(tag_results):
            print(f"Memory {idx + 1}:")
            print(f"  Content: {memory.content}")
            print(f"  Tags: {memory.tags}")

        # 4. Test get_embedding
        print_separator("Testing get_embedding")
        test_content = "Test embedding generation"
        print(f"Getting embedding for: {test_content}")
        embedding = memory_server.storage.model.encode([test_content])[0]
        print(f"Generated embedding of size: {len(embedding)}")

        # 5. Test check_embedding_model
        print_separator("Testing check_embedding_model")
        print("Checking embedding model status")
        model_info = {
            "status": "healthy" if memory_server.storage.model else "unavailable",
            "model_name": "all-MiniLM-L6-v2",
            "embedding_dimension": len(embedding)
        }
        print(f"Model status: {json.dumps(model_info, indent=2)}")

        # 6. Test debug_retrieve
        print_separator("Testing debug_retrieve")
        debug_query = {
            "query": "meeting",
            "n_results": 2,
            "similarity_threshold": 0.5
        }
        print(f"Testing debug retrieval with: {json.dumps(debug_query, indent=2)}")
        results = await memory_server.storage.retrieve(
            debug_query["query"],
            debug_query["n_results"]
        )
        for idx, result in enumerate(results):
            print(f"Debug result {idx + 1}:")
            print(f"  Content: {result.memory.content}")
            print(f"  Score: {result.relevance_score}")
            print(f"  Tags: {result.memory.tags}")

        # 7. Test exact_match_retrieve
        print_separator("Testing exact_match_retrieve")
        exact_query = stored_memories[0].content if stored_memories else "Important meeting with team tomorrow at 10 AM"
        print(f"Testing exact match with: {exact_query}")
        matches = [mem for mem in stored_memories if mem.content == exact_query]
        print(f"Found {len(matches)} exact matches")
        for idx, memory in enumerate(matches):
            print(f"Match {idx + 1}:")
            print(f"  Content: {memory.content}")
            print(f"  Tags: {memory.tags}")

        # 8. Test cleanup_duplicates
        print_separator("Testing cleanup_duplicates")
        print("Running duplicate cleanup")
        count, message = await memory_server.storage.cleanup_duplicates()
        print(f"Cleanup result: {message}")

        # 9. Test delete_by_tag
        print_separator("Testing delete_by_tag")
        test_tag = "meeting"
        print(f"Deleting memories with tag: {test_tag}")
        count, message = await memory_server.storage.delete_by_tag(test_tag)
        print(f"Delete by tag result: {message}")

        # 10. Clean up by deleting test memories
        print_separator("Cleaning up test data")
        for memory in stored_memories:
            success, message = await memory_server.storage.delete(memory.content_hash)
            print(f"Deleted memory {memory.content_hash}: {message}")

        # Final verification
        print_separator("Final Verification")
        # Verify database is empty or in expected state
        tag_results = await memory_server.storage.search_by_tag(["meeting"])
        print(f"Remaining memories with 'meeting' tag: {len(tag_results)}")
        
        results = await memory_server.storage.retrieve("important meeting", 5)
        print(f"Remaining memories matching 'important meeting': {len(results)}")

    except Exception as e:
        print(f"Test failed: {str(e)}", file=sys.stderr)
        raise
    finally:
        print("\nTest suite completed")

if __name__ == "__main__":
    # Ensure stdout is flushed immediately
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(test_management_features())
"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
import asyncio
import os
import logging
import traceback
import argparse
import sys
import json
from typing import List

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

from .config import (
    CHROMA_PATH, 
    BACKUPS_PATH, 
    SERVER_NAME, 
    SERVER_VERSION
)
from .storage.chroma import ChromaMemoryStorage
from .models.memory import Memory
from .utils.hashing import generate_content_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variable for PyTorch MPS
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

class MemoryServer:
    def __init__(self):
        """Initialize the server."""
        self.server = Server(SERVER_NAME)
        
        try:
            # Initialize paths
            logger.info(f"Creating directories if they don't exist...")
            os.makedirs(CHROMA_PATH, exist_ok=True)
            os.makedirs(BACKUPS_PATH, exist_ok=True)
            
            # Initialize storage - this part is synchronous
            self.storage = ChromaMemoryStorage(CHROMA_PATH)

        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            raise
        
        # Register handlers
        self.register_handlers()
        logger.info("Server initialization complete")

    async def initialize(self):
        """Async initialization method."""
        try:
            # Run any async initialization tasks here
            await self.validate_database_health()
            return True
        except Exception as e:
            logger.error(f"Async initialization error: {str(e)}")
            raise

    async def validate_database_health(self):
        """Validate database health during initialization."""
        from .utils.db_utils import validate_database, repair_database
        
        # Check database health
        is_valid, message = await validate_database(self.storage)
        if not is_valid:
            logger.warning(f"Database validation failed: {message}")
            
            # Attempt repair
            logger.info("Attempting database repair...")
            repair_success, repair_message = await repair_database(self.storage)
            
            if not repair_success:
                raise RuntimeError(f"Database repair failed: {repair_message}")
            else:
                logger.info(f"Database repair successful: {repair_message}")
        else:
            logger.info(f"Database validation successful: {message}")

    def register_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="store_memory",
                    description="Store new information with optional tags",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "metadata": {
                                "type": "object",
                                "properties": {
                                    "tags": {"type": "array", "items": {"type": "string"}},
                                    "type": {"type": "string"}
                                }
                            }
                        },
                        "required": ["content"]
                    }
                ),
                types.Tool(
                    name="retrieve_memory",
                    description="Find relevant memories based on query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "n_results": {"type": "number", "default": 5}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="search_by_tag",
                    description="Search memories by tags",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["tags"]
                    }
                ),
                types.Tool(
                    name="delete_memory",
                    description="Delete a specific memory by its hash",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content_hash": {"type": "string"}
                        },
                        "required": ["content_hash"]
                    }
                ),
                types.Tool(
                    name="delete_by_tag",
                    description="Delete all memories with a specific tag",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tag": {"type": "string"}
                        },
                        "required": ["tag"]
                    }
                ),
                types.Tool(
                    name="cleanup_duplicates",
                    description="Find and remove duplicate entries",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="get_embedding",
                    description="Get raw embedding vector for content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"}
                        },
                        "required": ["content"]
                    }
                ),
                types.Tool(
                    name="check_embedding_model",
                    description="Check if embedding model is loaded and working",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="debug_retrieve",
                    description="Retrieve memories with debug information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "n_results": {"type": "number", "default": 5},
                            "similarity_threshold": {"type": "number", "default": 0.0}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="exact_match_retrieve",
                    description="Retrieve memories using exact content match",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"}
                        },
                        "required": ["content"]
                    }
                ),
                types.Tool(
                    name="check_database_health",
                    description="Check database health and get statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None) -> List[types.TextContent]:
            try:
                logger.debug(f"Tool call received: {name} with arguments {arguments}")
                if arguments is None:
                    arguments = {}
                
                if name == "store_memory":
                    return await self.handle_store_memory(arguments)
                elif name == "retrieve_memory":
                    return await self.handle_retrieve_memory(arguments)
                elif name == "search_by_tag":
                    return await self.handle_search_by_tag(arguments)
                elif name == "delete_memory":
                    return await self.handle_delete_memory(arguments)
                elif name == "delete_by_tag":
                    return await self.handle_delete_by_tag(arguments)
                elif name == "cleanup_duplicates":
                    return await self.handle_cleanup_duplicates(arguments)
                elif name == "get_embedding":
                    return await self.handle_get_embedding(arguments)
                elif name == "check_embedding_model":
                    return await self.handle_check_embedding_model(arguments)
                elif name == "debug_retrieve":
                    return await self.handle_debug_retrieve(arguments)
                elif name == "exact_match_retrieve":
                    return await self.handle_exact_match_retrieve(arguments)
                elif name == "check_database_health":
                    return await self.handle_check_database_health(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in {name}: {str(e)}\n{traceback.format_exc()}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def validate_database_health(self):
        """Validate database health during initialization."""
        from .utils.db_utils import validate_database, repair_database
        
        # Check database health
        is_valid, message = await validate_database(self.storage)
        if not is_valid:
            logger.warning(f"Database validation failed: {message}")
            
            # Attempt repair
            logger.info("Attempting database repair...")
            repair_success, repair_message = await repair_database(self.storage)
            
            if not repair_success:
                raise RuntimeError(f"Database repair failed: {repair_message}")
            else:
                logger.info(f"Database repair successful: {repair_message}")
        else:
            logger.info(f"Database validation successful: {message}")

    async def handle_store_memory(self, arguments: dict) -> List[types.TextContent]:
        content = arguments.get("content")
        metadata = arguments.get("metadata", {})
        
        if not content:
            return [types.TextContent(type="text", text="Error: Content is required")]
        
        try:
            # Normalize tags to a list
            tags = metadata.get("tags", "")
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            else:
                tags = []  # If tags is not a string, default to empty list to be consistent with the Memory Model

            sanitized_tags = self.storage.sanitized(tags)
            
            # Create memory object
            content_hash = generate_content_hash(content, metadata)
            memory = Memory(
                content=content,
                content_hash=content_hash,
                tags=tags,  # keep as a list for easier use in other methods
                memory_type=metadata.get("type"),
                metadata = {**metadata, "tags":sanitized_tags}  # include the stringified tags in the meta data
            )
            
            # Store memory
            success, message = await self.storage.store(memory)
            return [types.TextContent(type="text", text=message)]
        except Exception as e:
            logger.error(f"Error storing memory: {str(e)}\n{traceback.format_exc()}")
            return [types.TextContent(type="text", text=f"Error storing memory: {str(e)}")]
    
    async def handle_retrieve_memory(self, arguments: dict) -> List[types.TextContent]:
        query = arguments.get("query")
        n_results = arguments.get("n_results", 5)
        
        if not query:
            return [types.TextContent(type="text", text="Error: Query is required")]
        
        try:
            results = await self.storage.retrieve(query, n_results)
            
            if not results:
                return [types.TextContent(type="text", text="No matching memories found")]
            
            formatted_results = []
            for i, result in enumerate(results):
                memory_info = [
                    f"Memory {i+1}:",
                    f"Content: {result.memory.content}",
                    f"Hash: {result.memory.content_hash}",
                    f"Relevance Score: {result.relevance_score:.2f}"
                ]
                if result.memory.tags:
                    memory_info.append(f"Tags: {', '.join(result.memory.tags)}")
                memory_info.append("---")
                formatted_results.append("\
".join(memory_info))
            
            return [types.TextContent(
                type="text",
                text="Found the following memories:\
\
" + "\
".join(formatted_results)
            )]
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}\
{traceback.format_exc()}")
            return [types.TextContent(type="text", text=f"Error retrieving memories: {str(e)}")]

    async def handle_search_by_tag(self, arguments: dict) -> List[types.TextContent]:
        tags = arguments.get("tags", [])
        
        if not tags:
            return [types.TextContent(type="text", text="Error: Tags are required")]
        
        try:
            memories = await self.storage.search_by_tag(tags)
            
            if not memories:
                return [types.TextContent(
                    type="text",
                    text=f"No memories found with tags: {', '.join(tags)}"
                )]
            
            formatted_results = []
            for i, memory in enumerate(memories):
                memory_info = [
                    f"Memory {i+1}:",
                    f"Content: {memory.content}",
                    f"Hash: {memory.content_hash}",
                    f"Tags: {', '.join(memory.tags)}"
                ]
                if memory.memory_type:
                    memory_info.append(f"Type: {memory.memory_type}")
                memory_info.append("---")
                formatted_results.append("\n".join(memory_info))
            
            return [types.TextContent(
                type="text",
                text="Found the following memories:\n\n".join(formatted_results)
            )]
        except Exception as e:
            logger.error(f"Error searching by tags: {str(e)}\n{traceback.format_exc()}")
            return [types.TextContent(type="text", text=f"Error searching by tags: {str(e)}")]

    async def handle_delete_memory(self, arguments: dict) -> List[types.TextContent]:
        content_hash = arguments.get("content_hash")
        success, message = await self.storage.delete(content_hash)
        return [types.TextContent(type="text", text=message)]

    async def handle_delete_by_tag(self, arguments: dict) -> List[types.TextContent]:
        tag = arguments.get("tag")
        count, message = await self.storage.delete_by_tag(tag)
        return [types.TextContent(type="text", text=message)]

    async def handle_cleanup_duplicates(self, arguments: dict) -> List[types.TextContent]:
        count, message = await self.storage.cleanup_duplicates()
        return [types.TextContent(type="text", text=message)]

    async def handle_get_embedding(self, arguments: dict) -> List[types.TextContent]:
        content = arguments.get("content")
        if not content:
            return [types.TextContent(type="text", text="Error: Content is required")]
        
        try:
            from .utils.debug import get_raw_embedding
            result = get_raw_embedding(self.storage, content)
            return [types.TextContent(
                type="text",
                text=f"Embedding results:\
{json.dumps(result, indent=2)}"
            )]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error getting embedding: {str(e)}")]

    async def handle_check_embedding_model(self, arguments: dict) -> List[types.TextContent]:
        try:
            from .utils.debug import check_embedding_model
            result = check_embedding_model(self.storage)
            return [types.TextContent(
                type="text",
                text=f"Embedding model status:\
{json.dumps(result, indent=2)}"
            )]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error checking model: {str(e)}")]

    async def handle_debug_retrieve(self, arguments: dict) -> List[types.TextContent]:
        query = arguments.get("query")
        n_results = arguments.get("n_results", 5)
        similarity_threshold = arguments.get("similarity_threshold", 0.0)
        
        if not query:
            return [types.TextContent(type="text", text="Error: Query is required")]
        
        try:
            from .utils.debug import debug_retrieve_memory
            results = await debug_retrieve_memory(
                self.storage,
                query,
                n_results,
                similarity_threshold
            )
            
            if not results:
                return [types.TextContent(type="text", text="No matching memories found")]
            
            formatted_results = []
            for i, result in enumerate(results):
                memory_info = [
                    f"Memory {i+1}:",
                    f"Content: {result.memory.content}",
                    f"Hash: {result.memory.content_hash}",
                    f"Raw Similarity Score: {result.debug_info['raw_similarity']:.4f}",
                    f"Raw Distance: {result.debug_info['raw_distance']:.4f}",
                    f"Memory ID: {result.debug_info['memory_id']}"
                ]
                if result.memory.tags:
                    memory_info.append(f"Tags: {', '.join(result.memory.tags)}")
                memory_info.append("---")
                formatted_results.append("\
".join(memory_info))
            
            return [types.TextContent(
                type="text",
                text="Found the following memories:\
\
" + "\
".join(formatted_results)
            )]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error in debug retrieve: {str(e)}")]

    async def handle_exact_match_retrieve(self, arguments: dict) -> List[types.TextContent]:
        content = arguments.get("content")
        if not content:
            return [types.TextContent(type="text", text="Error: Content is required")]
        
        try:
            from .utils.debug import exact_match_retrieve
            memories = await exact_match_retrieve(self.storage, content)
            
            if not memories:
                return [types.TextContent(type="text", text="No exact matches found")]
            
            formatted_results = []
            for i, memory in enumerate(memories):
                memory_info = [
                    f"Memory {i+1}:",
                    f"Content: {memory.content}",
                    f"Hash: {memory.content_hash}"
                ]
                
                if memory.tags:
                    memory_info.append(f"Tags: {', '.join(memory.tags)}")
                memory_info.append("---")
                formatted_results.append("\n".join(memory_info))
            
            return [types.TextContent(
                type="text",
                text="Found the following exact matches:\n\n" + "\n".join(formatted_results)
            )]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error in exact match retrieve: {str(e)}")]

    async def handle_check_database_health(self, arguments: dict) -> List[types.TextContent]:
        """Handle database health check requests."""
        from .utils.db_utils import validate_database, get_database_stats
        
        try:
            # Get validation status
            is_valid, message = await validate_database(self.storage)
            
            # Get database stats
            stats = get_database_stats(self.storage)
            
            # Combine results
            result = {
                "validation": {
                    "status": "healthy" if is_valid else "unhealthy",
                    "message": message
                },
                "statistics": stats
            }
            
            return [types.TextContent(
                type="text",
                text=f"Database Health Check Results:\n{json.dumps(result, indent=2)}"
            )]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error checking database health: {str(e)}"
            )]

def parse_args():
    parser = argparse.ArgumentParser(
        description="MCP Memory Service - A semantic memory service using the Model Context Protocol"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--chroma-path",
        type=str,
        default=CHROMA_PATH,
        help="Path to ChromaDB storage"
    )
    return parser.parse_args()

async def async_main():
    args = parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    global CHROMA_PATH
    CHROMA_PATH = args.chroma_path
    
    logger.info(f"Starting MCP Memory Service with ChromaDB path: {CHROMA_PATH}")
    
    try:
        # Create server instance
        memory_server = MemoryServer()
        
        # Run async initialization
        await memory_server.initialize()
        
        # Start the server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.info("Server started and ready to handle requests")
            await memory_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=SERVER_NAME,
                    server_version=SERVER_VERSION,
                    capabilities=memory_server.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}\n{traceback.format_exc()}")
        raise

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
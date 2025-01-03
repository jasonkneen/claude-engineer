import sys
import json
import logging
import chromadb
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryTool:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.create_collection("memories")
        logger.info("Initialized ChromaDB collection")
        
    def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming command and return the result"""
        cmd_type = command.get("command")
        data = command.get("data", {})
        
        logger.debug(f"Processing command: {cmd_type} with data: {data}")
        
        try:
            if cmd_type == "store":
                result = self.store_memory(data)
            elif cmd_type == "retrieve":
                result = self.retrieve_memory(data)
            elif cmd_type == "search":
                result = self.search_memories(data)
            else:
                raise ValueError(f"Unknown command: {cmd_type}")
                
            logger.info(f"Command {cmd_type} completed successfully")
            return {"status": "success", "data": result}
            
        except Exception as e:
            logger.error(f"Error processing command {cmd_type}: {str(e)}")
            return {"status": "error", "error": str(e)}
            
    def store_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a new memory"""
        content = data.get("content")
        tags = data.get("tags", [])
        
        if not content:
            raise ValueError("Memory content is required")
            
        logger.debug(f"Storing memory: {content} with tags: {tags}")
        self.collection.add(
            documents=[content],
            metadatas=[{"tags": tags}],
            ids=[str(hash(content))]
        )
        logger.info("Memory stored successfully")
        return {"message": "Memory stored successfully"}
        
    def retrieve_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a specific memory"""
        memory_id = data.get("id")
        if not memory_id:
            raise ValueError("Memory ID is required")
            
        logger.debug(f"Retrieving memory with ID: {memory_id}")
        result = self.collection.get(ids=[memory_id])
        logger.info(f"Retrieved memory: {result}")
        return result
        
    def search_memories(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search memories by query and/or tags"""
        query = data.get("query", "")
        tags = data.get("tags", [])
        
        logger.debug(f"Searching memories with query: {query} and tags: {tags}")
        where = {"tags": {"$in": tags}} if tags else None
        results = self.collection.query(
            query_texts=[query] if query else None,
            where=where,
            n_results=10
        )
        logger.info(f"Found {len(results.get('documents', [[]])[0])} matching memories")
        return results

def main():
    tool = MemoryTool()
    logger.info("Memory tool initialized, ready for input")
    
    for line in sys.stdin:
        try:
            command = json.loads(line)
            logger.debug(f"Received input: {line.strip()}")
            
            result = tool.process_command(command)
            output = json.dumps(result)
            
            logger.debug(f"Sending output: {output}")
            print(output, flush=True)
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON input: {line.strip()}")
            print(json.dumps({
                "status": "error",
                "error": "Invalid JSON input"
            }), flush=True)
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            print(json.dumps({
                "status": "error", 
                "error": str(e)
            }), flush=True)

if __name__ == "__main__":
    main()


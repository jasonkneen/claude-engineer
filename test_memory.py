from tools.mcp_memory.src.memory_service import MemoryService

def test_memory():
    memory = MemoryService()
    print("Storing memories...")
    memory.store_memory("Test memory 1", tags=["test", "first"])
    memory.store_memory("Test memory 2", tags=["test", "second"])
    
    print("\nRetrieving memories...")
    results = memory.retrieve_memory("test", n_results=2)
    for r in results:
        print(f"Found: {r['content']} (similarity: {r['similarity']:.2f})")
        
    print("\nSearching by tag...")
    tag_results = memory.search_by_tag("test")
    for r in tag_results:
        print(f"Tagged: {r['content']}")

if __name__ == "__main__":
    test_memory()

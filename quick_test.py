import asyncio
from tools.mcpmemorytool import MCPMemoryTool

async def test_memory():
    tool = MCPMemoryTool()
    print("Tool initialized!")
    
    print("\nStoring test memories...")
    mem_id1 = await tool.store_memory("This is a test memory about Python", tags=["test", "python"])
    print(f"Stored memory 1: {mem_id1}")
    
    mem_id2 = await tool.store_memory("Another test memory about AI", tags=["test", "ai"])
    print(f"Stored memory 2: {mem_id2}")
    
    print("\nRetrieving memories about Python...")
    results = await tool.retrieve_memory("Python programming")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Content: {result['content']}")
        print(f"Tags: {result.get('metadata', {}).get('tags', [])}")
        print(f"Similarity: {result.get('similarity', 0):.2f}")

if __name__ == "__main__":
    asyncio.run(test_memory())

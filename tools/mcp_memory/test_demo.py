from tools.mcpmemorytool import MCPMemoryTool
import time

def main():
    # Initialize the memory tool
    memory_tool = MCPMemoryTool()
    print("MCPMemoryTool initialized successfully!")

    # Store some sample memories
    print("\n1. Storing sample memories...")
    memory_tool.store_memory(
        "Python is a high-level programming language known for its simplicity.",
        tags=["programming", "python", "language"]
    )
    
    memory_tool.store_memory(
        "ChatGPT is an AI language model developed by OpenAI.",
        tags=["ai", "language-model", "openai"]
    )
    
    memory_tool.store_memory(
        "Python's Django framework is great for web development.",
        tags=["programming", "python", "web", "django"]
    )

    # Give a moment for the memories to be stored
    time.sleep(1)
    
    # Retrieve memories by content similarity
    print("\n2. Retrieving memories similar to 'python programming'...")
    results = memory_tool.retrieve_memory("python programming")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Content: {result['content']}")
        print(f"Tags: {result['tags']}")
        print(f"Similarity: {result['similarity']:.2f}")
    
    # Search by tag
    print("\n3. Searching memories with tag 'python'...")
    tag_results = memory_tool.search_by_tag("python")
    for i, result in enumerate(tag_results, 1):
        print(f"\nResult {i}:")
        print(f"Content: {result['content']}")
        print(f"Tags: {result['tags']}")

    # Clean up (optional)
    print("\n4. Cleaning up test memories...")
    memory_tool.clear_memories()
    print("Test memories cleared.")

if __name__ == "__main__":
    main()


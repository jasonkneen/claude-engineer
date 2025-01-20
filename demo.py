from memory_manager import MemoryManager, SignificanceType

def main():
    # Initialize memory manager
    memory_manager = MemoryManager()
    
    print("===== Memory System Demo =====\n")
    
    # Add some memories
    print("Adding memories...")
    memory_manager.add_memory_block(
        content="The sky is blue because of Rayleigh scattering of sunlight", 
        significance_type=SignificanceType.SYSTEM
    )
    
    memory_manager.add_memory_block(
        content="Global warming is causing climate change worldwide",
        significance_type=SignificanceType.USER
    )
    
    memory_manager.add_memory_block(
        content="Python is a high-level programming language",
        significance_type=SignificanceType.SYSTEM
    )
    
    # Get memory stats
    print("\nMemory Stats:")
    stats = memory_manager.get_memory_stats()
    print(f"Total memories: {stats['total_memories']}")
    print(f"System memories: {stats['system_memories']}")
    print(f"User memories: {stats['user_memories']}")
    
    # Retrieve relevant context
    print("\nRetrieving memories about programming...")
    results = memory_manager.get_relevant_context("Tell me about programming")
    print("\nRelevant memories:")
    for result in results:
        print(f"- {result}\n")
    
    print("\nRetrieving memories about weather...")
    results = memory_manager.get_relevant_context("Tell me about weather and climate")
    print("\nRelevant memories:")
    for result in results:
        print(f"- {result}\n")

if __name__ == "__main__":
    main()

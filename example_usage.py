from memory_system import MemorySystem, SignificanceType
import time

def main():
    """Example usage of the Hierarchical Memory System"""
    
    # Initialize the memory system
    memory_system = MemorySystem(
        base_dir=".memory",
        working_memory_limit=200000,  # 200K tokens
        archive_threshold=150000,     # Start pruning at 150K tokens
        max_nexus_points=100,         # Maximum number of nexus points
        stats_retention_days=30       # Keep statistics for 30 days
    )

    print("Memory System Initialized\n")

    # Example 1: Adding memories
    print("Adding memories...")
    memory_ids = []
    
    # Add some user memories
    memory_ids.append(memory_system.add_memory(
        "The quick brown fox jumps over the lazy dog",
        SignificanceType.USER
    ))
    
    # Add system-level memory (will be protected as nexus point)
    memory_ids.append(memory_system.add_memory(
        "System configuration: max_tokens=200K, archive_threshold=150K",
        SignificanceType.SYSTEM
    ))
    
    # Add some derived memories
    for i in range(3):
        memory_ids.append(memory_system.add_memory(
            f"Derived memory {i}: This is an automatically generated memory",
            SignificanceType.DERIVED
        ))

    print(f"Added {len(memory_ids)} memories\n")

    # Example 2: Searching memories
    print("Searching memories...")
    results = memory_system.search_memory("quick fox")
    print(f"Found {len(results)} results for 'quick fox'")
    for result in results:
        print(f"- {result.content} (ID: {result.id})")
    print()

    # Example 3: Creating a nexus point through frequent access
    print("Creating nexus point through frequent access...")
    target_id = memory_ids[0]
    for _ in range(10):
        memory_system.search_memory("quick fox")
        time.sleep(0.1)  # Small delay between accesses

    nexus_points = memory_system.get_nexus_points()
    print(f"Current nexus points: {len(nexus_points)}")
    for np in nexus_points:
        print(f"- {np.content[:50]}... (ID: {np.id})")
    print()

    # Example 4: Getting related memories
    print("Finding related memories...")
    related = memory_system.get_related_memories(target_id)
    print(f"Found {len(related)} related memories for ID {target_id}")
    for memory in related:
        print(f"- {memory.content[:50]}...")
    print()

    # Example 5: Looking up by what3words
    print("Looking up by what3words...")
    memory = memory_system.get_memory_by_id(target_id)
    if memory and memory.w3w_reference:
        results = memory_system.lookup_by_w3w(memory.w3w_reference)
        print(f"Found {len(results)} memories using w3w reference: {' '.join(memory.w3w_reference)}")
    print()

    # Example 6: System maintenance
    print("Performing system maintenance...")
    memory_system.maintain_system()
    print("Maintenance completed")
    print()

    # Example 7: Getting system statistics
    print("System Statistics:")
    stats = memory_system.get_memory_stats()
    
    print("\nMemory State:")
    for tier, data in stats['memory_state']['tiers'].items():
        print(f"- {tier}: {data['blocks']} blocks, {data['tokens']} tokens")
    
    print("\nNexus Points:")
    nexus_stats = stats['nexus_points']
    print(f"- Total: {nexus_stats['total_count']}")
    print(f"- Protection Levels: {nexus_stats['protection_levels']}")
    
    print("\nPerformance:")
    perf = stats['performance']['daily_stats']['performance']
    print(f"- Average Operation Time: {perf['average_operation_time']:.3f}s")
    print(f"- Success Rate: {perf['success_rate']*100:.1f}%")
    print(f"- Error Count: {perf['error_count']}")

if __name__ == "__main__":
    main()
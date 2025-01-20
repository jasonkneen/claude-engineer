import pytest
from datetime import datetime, timedelta
from memory_manager import MemoryManager, MemoryBlock, MemoryLevel, SignificanceType
from typing import List, Dict, Any

@pytest.fixture
def memory_manager():
    return MemoryManager()


def test_memory_block_creation(memory_manager):
    block_id = memory_manager.add_memory_block(
        content="Test content",
        significance_type=SignificanceType.USER
    )
    memories = memory_manager.get_working_memory()
    assert len(memories) == 1
    assert memories[0].content == "Test content"

def test_working_memory_limit(memory_manager):
    # Add multiple memory blocks to trigger memory management
    for i in range(10):
        content = f"Test content {i} " * 100
        memory_manager.add_memory_block(
            content=content,
            significance_type=SignificanceType.USER
        )
    
    # Verify some memories were stored
    memories = memory_manager.get_working_memory()
    assert len(memories) > 0

def test_memory_operations(memory_manager):
    block_id = memory_manager.add_memory_block(
        content="This is test memory block 1",
        significance_type=SignificanceType.USER
    )
    block_id2 = memory_manager.add_memory_block(
        content="This is test memory block 2", 
        significance_type=SignificanceType.SYSTEM
    )
    
    # Verify both memories are stored
    memories = memory_manager.get_working_memory()
    assert len(memories) == 2
    assert any("block 1" in m.content for m in memories)
    assert any("block 2" in m.content for m in memories)

def test_context_retrieval(memory_manager):
    # Add two memory blocks to working memory
    memory_manager.add_memory_block(
        content="The cat sat on the mat",
        significance_type=SignificanceType.USER
    )
    memory_manager.add_memory_block(
        content="The dog played in the yard",
        significance_type=SignificanceType.USER
    )
        
    # Get relevant context from working memory
    context = memory_manager.get_relevant_context("cat mat", max_blocks=2)
    # Verify we got at least one result
    assert len(context) > 0
    # Verify the cat memory was found
    assert any(m.content.find("cat") != -1 for m in context)
    # Verify we didn't exceed max_blocks
    assert len(context) <= 2

def test_importance_level(memory_manager):
    memory_manager.add_memory_block(
        content="Regular memory",
        significance_type=SignificanceType.USER
    )
    memory_manager.add_memory_block(
        content="System critical memory",
        significance_type=SignificanceType.SYSTEM
    )
    
    memories = memory_manager.get_working_memory()
    system_memories = [m for m in memories if m.significance_type == SignificanceType.SYSTEM]
    assert len(system_memories) > 0

def test_memory_stats(memory_manager):
    # Add memory blocks with different significance types
    memory_manager.add_memory_block(
        content="User memory 1",
        significance_type=SignificanceType.USER
    )
    memory_manager.add_memory_block(
        content="System memory 1",
        significance_type=SignificanceType.SYSTEM
    )
    memory_manager.add_memory_block(
        content="LLM memory 1",
        significance_type=SignificanceType.LLM
    )
    
    # Perform some operations to generate stats
    memory_manager.get_relevant_context("memory", max_blocks=2)
    memory_manager.get_working_memory()
    
    # Get and verify stats
    stats = memory_manager.get_memory_stats()
    
    # Verify structure and basic types
    assert "memory" in stats
    assert "working" in stats["memory"]
    assert "archived" in stats["memory"]
    assert "operations" in stats
    assert "nexus_points" in stats
    assert "total_tokens" in stats
    assert "last_recall_time_ms" in stats
    
    # Verify memory counts
    assert stats["memory"]["working"]["count"] == 3
    assert isinstance(stats["memory"]["working"]["size"], int)
    assert isinstance(stats["memory"]["working"]["utilization"], float)
    assert isinstance(stats["memory"]["archived"]["count"], int)
    
    # Verify operations tracking
    assert isinstance(stats["operations"]["promotions"], int)
    assert isinstance(stats["operations"]["demotions"], int)
    assert isinstance(stats["operations"]["merges"], int)
    assert stats["operations"]["retrievals"] > 0  # We did retrievals
    assert stats["operations"]["generations"] >= 0
    
    # Verify nexus points
    assert stats["nexus_points"]["count"] == 3
    assert stats["nexus_points"]["types"]["user"] == 1
    assert stats["nexus_points"]["types"]["system"] == 1
    assert stats["nexus_points"]["types"]["llm"] == 1
    
    # Verify token count and timing fields
    assert stats["total_tokens"] >= 0
    assert stats["last_recall_time_ms"] > 0
    
def test_stats_broadcasting():
    # Create a list to store stats updates
    received_stats = []
    
    # Define callback that prints and stores stats
    def stats_callback(stats):
        print(f"\nReceived stats update:")
        print(f"- Working memory count: {stats['memory']['working']['count']}")
        print(f"- Operation counts: {stats['operations']}")
        print(f"- Nexus points: {stats['nexus_points']}")
        received_stats.append(stats)
    
    # Initialize manager with callback
    memory_manager = MemoryManager(stats_callback=stats_callback)
    
    print("\nAdding first memory block...")
    memory_manager.add_memory_block(
        content="First test memory",
        significance_type=SignificanceType.USER
    )
    assert len(received_stats) >= 1
    assert received_stats[-1]["memory"]["working"]["count"] == 1
    
    print("\nAdding second memory block...")
    memory_manager.add_memory_block(
        content="Second test memory",
        significance_type=SignificanceType.SYSTEM
    )
    assert len(received_stats) >= 2
    assert received_stats[-1]["memory"]["working"]["count"] == 2
    
    print("\nPerforming context retrieval...")
    memory_manager.get_relevant_context("test memory", max_blocks=1)
    assert any(stats["operations"]["retrievals"] > 0 for stats in received_stats)
    
    # Verify final stats are complete
    final_stats = received_stats[-1]
    assert final_stats["memory"]["working"]["count"] == 2
    assert final_stats["nexus_points"]["types"]["user"] == 1
    assert final_stats["nexus_points"]["types"]["system"] == 1
    assert final_stats["operations"]["retrievals"] > 0

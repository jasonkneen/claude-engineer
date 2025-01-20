import pytest
from datetime import datetime, timedelta
from memory_manager import MemoryManager, MemoryBlock, MemoryLevel, SignificanceType
from typing import List, Dict, Any

@pytest.fixture
def memory_manager():
    return MemoryManager()

@pytest.fixture
def sample_memory_blocks():
    return [
        MemoryBlock(
            content="This is test memory block 1",
            tokens=50,
            timestamp=datetime.now(),
            significance_type=SignificanceType.USER,
            level=MemoryLevel.WORKING
        ),
        MemoryBlock(
            content="This is test memory block 2",
            tokens=75,
            timestamp=datetime.now() - timedelta(hours=1),
            significance_type=SignificanceType.SYSTEM,
            level=MemoryLevel.WORKING
        )
    ]

def test_memory_block_creation(memory_manager):
    block = MemoryBlock(
        content="Test content",
        tokens=10,
        timestamp=datetime.now(),
        significance_type=SignificanceType.USER,
        level=MemoryLevel.WORKING
    )
    memory_manager.add_memory_block(block)
    assert block.content == "Test content"
    assert block.tokens > 0
    assert block.level == MemoryLevel.WORKING
    assert block.significance_type == SignificanceType.USER_INPUT

def test_working_memory_limit(memory_manager):
    # Fill working memory to limit
    content = "Test content " * 1000  # Large content
    block = MemoryBlock(
        content=content,
        tokens=500,
        timestamp=datetime.now(),
        significance_type=SignificanceType.USER,
        level=MemoryLevel.WORKING
    )
    memory_manager.add_memory_block(block)
    
    assert len(memory_manager.working_memory) > 0
    assert any(b.level == MemoryLevel.SHORT_TERM 
            for b in memory_manager.get_all_memories())

def test_memory_compression(memory_manager, sample_memory_blocks):
    for block in sample_memory_blocks:
        memory_manager.add_memory_block(block)
    
    # Force compression
    memory_manager.compress_memories()
    
    # Verify compression results
    compressed_blocks = memory_manager.get_all_memories()
    assert len(compressed_blocks) <= len(sample_memory_blocks)
    assert all(b.is_compressed for b in compressed_blocks 
            if b.level == MemoryLevel.LONG_TERM)

def test_block_promotion(memory_manager, sample_memory_blocks):
    block = sample_memory_blocks[0]
    memory_manager.add_memory_block(block)
    
    # Simulate frequent access
    for _ in range(5):
        memory_manager.access_memory(block.id)
    
    promoted_block = memory_manager.get_memory_by_id(block.id)
    assert promoted_block.level == MemoryLevel.WORKING

def test_context_retrieval(memory_manager, sample_memory_blocks):
    for block in sample_memory_blocks:
        memory_manager.add_memory_block(block)
        
    context = memory_manager.get_context(
        "test memory", max_tokens=100
    )
    
    assert len(context) > 0
    assert all(isinstance(c, dict) for c in context)
    assert all("content" in c for c in context)

def test_memory_merging(memory_manager):
    similar_content1 = "The cat sat on the mat"
    similar_content2 = "A cat was sitting on a mat"
    
    block1 = MemoryBlock(
        content=similar_content1,
        tokens=10,
        timestamp=datetime.now(),
        significance_type=SignificanceType.USER,
        level=MemoryLevel.WORKING
    )
    block2 = MemoryBlock(
        content=similar_content2,
        tokens=10,
        timestamp=datetime.now(),
        significance_type=SignificanceType.USER,
        level=MemoryLevel.WORKING
    )
    memory_manager.add_memory_block(block1)
    memory_manager.add_memory_block(block2)
    
    memory_manager.merge_similar_memories()
    
    all_memories = memory_manager.get_all_memories()
    assert len(all_memories) < 2  # Should be merged into one

def test_nexus_points(memory_manager):
    nexus_block = MemoryBlock(
        content="Important system decision",
        tokens=10,
        timestamp=datetime.now(),
        significance_type=SignificanceType.SYSTEM,
        level=MemoryLevel.WORKING
    )
    memory_manager.add_memory_block(nexus_block)

    assert nexus_block in memory_manager.get_nexus_points()
    assert nexus_block.significance_type == SignificanceType.SYSTEM

def test_memory_cleanup(memory_manager, sample_memory_blocks):
    # Add old memories
    for block in sample_memory_blocks:
        block.timestamp = datetime.now() - timedelta(days=10)
        memory_manager.add_memory_block(block)
    
    # Add nexus point that should be preserved
    nexus_block = MemoryBlock(
        content="Important nexus point",
        tokens=10,
        timestamp=datetime.now(),
        significance_type=SignificanceType.SYSTEM,
        level=MemoryLevel.WORKING
    )
    memory_manager.add_memory_block(nexus_block)
    nexus_block.timestamp = datetime.now() - timedelta(days=10)
    
    memory_manager.cleanup_old_memories(max_age_days=7)
    
    remaining_memories = memory_manager.get_all_memories()
    assert nexus_block in remaining_memories
    assert len(remaining_memories) == 1

def test_memory_level_transitions(memory_manager):
    # Fill working memory
    working_block = MemoryBlock(
        content="Working memory test",
        tokens=10,
        timestamp=datetime.now(),
        significance_type=SignificanceType.USER,
        level=MemoryLevel.WORKING
    )
    memory_manager.add_memory_block(working_block)
    assert working_block.level == MemoryLevel.WORKING
    
    # Force transition to short-term
    memory_manager.move_to_short_term(working_block.id)
    moved_block = memory_manager.get_memory_by_id(working_block.id)
    assert moved_block.level == MemoryLevel.SHORT_TERM
    
    # Force transition to long-term
    memory_manager.move_to_long_term(moved_block.id)
    final_block = memory_manager.get_memory_by_id(moved_block.id)
    assert final_block.level == MemoryLevel.LONG_TERM


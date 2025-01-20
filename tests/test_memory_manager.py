import pytest
from datetime import datetime, timedelta
from memory_manager import MemoryManager, MemoryLevel, SignificanceType
import numpy as np


@pytest.fixture
def memory_manager():
    """Create a memory manager with small limits for testing"""
    return MemoryManager(
        working_memory_limit=500,  # Very small limit for quick testing
        archival_memory_limit=1000,  # Renamed from short_term_limit
        archive_threshold=400,  # Added archive threshold
        similarity_threshold=0.5,  # More lenient for simple embeddings
    )


def generate_test_message(size: int = 50) -> str:
    """Generate a small test message"""
    words = ["memory", "test", "data", "system", "info"]
    result = []
    for _ in range(size // 10):  # Each word ~5 chars + space
        result.append(words[len(result) % len(words)])
    return " ".join(result)


def test_memory_block_creation(memory_manager):
    """Test basic memory block creation and W3W token generation"""
    content = "Test message"
    block_id = memory_manager.add_memory_block(content, SignificanceType.USER)

    # Verify block was created in working memory
    assert len(memory_manager.working_memory) == 1
    block = memory_manager.working_memory[0]
    assert block.id == block_id
    assert block.level == MemoryLevel.WORKING
    assert len(block.w3w_tokens) == 3
    assert block.embedding is not None
    assert block.tokens > 0


def test_working_memory_compression(memory_manager):
    """Test that working memory compresses when limit is reached"""
    # Add enough content to exceed working memory limit
    total_size = 0
    messages_added = 0

    while total_size < memory_manager.working_memory_limit:
        content = generate_test_message(50)
        memory_manager.add_memory_block(content, SignificanceType.USER)
        stats = memory_manager.get_memory_stats()
        total_size = stats["pools"]["working"]["size"]
        messages_added += 1

    # Add one more to trigger compression
    memory_manager.add_memory_block(generate_test_message(50), SignificanceType.USER)

    # Verify some content moved to short-term memory
    stats = memory_manager.get_memory_stats()
    assert stats["pools"]["working"]["size"] < memory_manager.working_memory_limit
    assert len(memory_manager.short_term_memory) > 0
    assert stats["operations"]["demotions"] > 0


def test_short_term_archival(memory_manager):
    """Test that short term memory archives to long term when limit reached"""
    # Fill working memory first
    stats = memory_manager.get_memory_stats()
    while stats["pools"]["working"]["size"] < memory_manager.working_memory_limit:
        content = generate_test_message(50)
        memory_manager.add_memory_block(content, SignificanceType.USER)
        stats = memory_manager.get_memory_stats()

    # Then fill short term memory
    while stats["pools"]["short_term"]["size"] < memory_manager.archival_memory_limit:
        content = generate_test_message(50)
        memory_manager.add_memory_block(content, SignificanceType.USER)
        stats = memory_manager.get_memory_stats()

    # Add more to trigger archival
    memory_manager.add_memory_block(generate_test_message(50), SignificanceType.USER)

    # Verify some content moved to long-term memory
    stats = memory_manager.get_memory_stats()
    assert stats["pools"]["short_term"]["size"] < memory_manager.archival_memory_limit
    assert len(memory_manager.long_term_memory) > 0


def test_memory_promotion(memory_manager):
    """Test that frequently accessed memories get promoted"""
    # Add some content and let it move to short term
    content = "Important information that will be accessed frequently"
    block_id = memory_manager.add_memory_block(content, SignificanceType.USER)

    # Fill working memory to push our content to short term
    stats = memory_manager.get_memory_stats()
    while (
        len(memory_manager.working_memory) > 0
        or stats["pools"]["working"]["size"] < memory_manager.working_memory_limit
    ):
        filler = generate_test_message(50)
        memory_manager.add_memory_block(filler, SignificanceType.USER)
        stats = memory_manager.get_memory_stats()

    # Access our content multiple times
    query = "important information"
    for _ in range(6):  # More than the promotion threshold
        results = memory_manager.get_relevant_context(query)
        assert any("Important information" in block.content for block in results)

    # Verify promotion occurred
    stats = memory_manager.get_memory_stats()
    assert stats["operations"]["promotions"] > 0
    # Our content should be back in working memory
    assert any(
        block.id == block_id and block.level == MemoryLevel.WORKING
        for block in memory_manager.working_memory
    )


def test_nexus_points(memory_manager):
    """Test nexus point creation and tracking"""
    # Add memory with different significance types
    memory_manager.add_memory_block("Critical user information", SignificanceType.USER)
    memory_manager.add_memory_block("Important LLM insight", SignificanceType.LLM)
    memory_manager.add_memory_block("System checkpoint", SignificanceType.SYSTEM)

    # Verify nexus points were created
    stats = memory_manager.get_memory_stats()
    assert stats["nexus_points"]["count"] == 3
    assert stats["nexus_points"]["types"]["user"] == 1
    assert stats["nexus_points"]["types"]["llm"] == 1
    assert stats["nexus_points"]["types"]["system"] == 1


def test_relevant_context_retrieval(memory_manager):
    """Test retrieving relevant context across memory levels"""
    # Add related content that will end up in different memory levels
    base_content = "Python programming"
    variations = [" basics", " functions", " classes", " modules", " packages"]

    # Add content and force distribution across memory levels
    for var in variations:
        content = base_content + var
        memory_manager.add_memory_block(content, SignificanceType.USER)
        # Add filler to push content through memory levels
        for _ in range(2):  # Reduced number of fillers
            filler = generate_test_message(50)
            memory_manager.add_memory_block(filler, SignificanceType.USER)

    # Query for relevant content
    results = memory_manager.get_relevant_context("Python programming", max_blocks=3)

    # Verify we got relevant results
    assert len(results) > 0
    assert all("Python" in block.content for block in results)
    stats = memory_manager.get_memory_stats()
    assert stats["operations"]["retrievals"] > 0


def test_memory_stats(memory_manager):
    """Test memory statistics tracking"""
    # Add some content
    for _ in range(3):  # Reduced number of iterations
        content = generate_test_message(50)
        memory_manager.add_memory_block(content, SignificanceType.USER)

    # Get stats
    stats = memory_manager.get_memory_stats()

    # Verify all expected stats are present and reasonable
    assert "pools" in stats
    assert all(
        pool in stats["pools"] for pool in ["working", "short_term", "long_term"]
    )
    assert all(
        key in stats["operations"]
        for key in [
            "promotions",
            "demotions",
            "merges",
            "retrievals",
            "avg_recall_time",
            "compression_count",
        ]
    )
    assert "nexus_points" in stats
    assert "generations" in stats
    assert "total_tokens" in stats

    # Verify utilization calculations
    assert 0 <= stats["pools"]["working"]["utilization"] <= 1
    assert 0 <= stats["pools"]["short_term"]["utilization"] <= 1

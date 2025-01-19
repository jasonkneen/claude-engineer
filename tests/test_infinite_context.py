import pytest
import numpy as np
from datetime import datetime
from infinite_context import InfiniteContext, ContextBlock
import json


@pytest.fixture
def context():
    """Create a fresh context for each test"""
    return InfiniteContext(max_blocks=5, similarity_threshold=0.7)


@pytest.mark.timeout(10)
def test_context_block_creation():
    """Test creating a context block with content"""
    content = {"role": "user", "content": "test message"}
    block = ContextBlock(timestamp=datetime.now(), content=content)
    assert block.content == content
    assert block.embedding is None


@pytest.mark.timeout(20)
def test_embedding_generation(context):
    """Test generating embeddings for text"""
    text = "This is a test message"
    embedding = context._get_embedding(text)
    assert isinstance(embedding, np.ndarray)
    # TF-IDF dimension depends on vocabulary size, just check it's a vector
    assert len(embedding.shape) == 1  # Should be a 1D vector
    assert embedding.shape[0] > 0  # Should have some features
    assert np.allclose(np.linalg.norm(embedding), 1.0)  # Should be normalized


def get_test_problems():
    """Get a set of semantically related test problems"""
    return [
        {
            "description": "Implement a function to find the maximum subarray sum in a given array of integers. The function should handle both positive and negative numbers.",
            "difficulty": "medium",
            "topic": "arrays",
        },
        {
            "description": "Write a function to find the longest contiguous subarray where all elements are positive in a given array of integers.",
            "difficulty": "medium",
            "topic": "arrays",
        },
        {
            "description": "Create a function that finds all subarrays in an integer array whose sum equals a given target value.",
            "difficulty": "medium",
            "topic": "arrays",
        },
    ]


@pytest.mark.timeout(30)  # 30 second timeout
def test_relevant_context_retrieval(context):
    """Test retrieving relevant context based on query"""
    print("\nTesting context retrieval with related problems...")

    # Get test problems
    problems = get_test_problems()
    print(f"Using {len(problems)} test problems")

    # Add problems to context
    for i, problem in enumerate(problems):
        print(f"Adding problem {i+1}: {problem['description'][:50]}...")
        context.add_context({"role": "user", "content": problem["description"]})

    print("Testing retrieval...")
    # Use first problem's description as query
    query = problems[0]["description"]
    print(f"Query: {query[:50]}...")

    results = context.get_relevant_context(query, max_blocks=2)

    # Assertions
    assert len(results) > 0, "Should return at least one result"
    # The query (first problem) should find itself and similar problems
    assert any(
        problems[0]["description"] in str(r.get("content", "")) for r in results
    ), "Should find the queried problem"


@pytest.mark.timeout(20)
def test_content_merging(context):
    """Test merging different types of content"""
    # Add blocks with similar content
    context.add_context({"role": "user", "content": ["Hello", "World"]})
    context.add_context({"role": "user", "content": ["Hello", "Python"]})

    # Force compression
    for _ in range(4):
        context.add_context({"role": "user", "content": "filler message"})

    # Check that blocks were merged
    assert len(context.context_blocks) <= context.max_blocks


@pytest.mark.timeout(10)
def test_clear_context(context):
    """Test clearing all context"""
    context.add_context({"role": "user", "content": "test message"})
    context.clear()
    assert len(context.context_blocks) == 0
    assert context.index.ntotal == 0  # FAISS index should be empty

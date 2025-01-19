import pytest
from infinite_context import InfiniteContext
from datetime import datetime, timedelta
import json
from typing import List, Dict


def generate_synthetic_data(num_problems: int = 100) -> List[Dict]:
    """Generate synthetic coding problems using curator tool"""
    from curator_synthetic_data import CuratorServer

    curator = CuratorServer()
    problems = []

    # Generate a mix of coding and technical problems
    for i in range(num_problems):
        problem_type = "coding" if i % 2 == 0 else "technical"
        result = curator.generate_problems(
            {
                "type": problem_type,
                "topic": "algorithms" if problem_type == "coding" else "database",
                "difficulty": "medium",
                "language": "python" if problem_type == "coding" else None,
                "count": 1,
            }
        )
        problems.extend(result)

    return problems


def test_context_scaling_and_compression():
    """Test context system with large amount of synthetic data"""
    # Initialize context system
    context = InfiniteContext(max_blocks=50, similarity_threshold=0.7)

    # Generate test data
    problems = generate_synthetic_data(100)  # Start with 100 problems

    # Track metrics
    total_tokens = 0
    compressed_tokens = 0
    immediate_hits = 0
    short_term_hits = 0
    long_term_hits = 0

    # Add problems to context with timestamps
    base_time = datetime.now()
    for i, problem in enumerate(problems):
        # Simulate time progression
        timestamp = base_time + timedelta(minutes=i * 5)

        # Add to context
        context.add_context(
            {
                "role": "user",
                "content": json.dumps(problem),
                "timestamp": timestamp.isoformat(),
            }
        )

        # Every 10 problems, test retrieval at different memory levels
        if (i + 1) % 10 == 0:
            # Test immediate memory (last 5 problems)
            recent_query = json.dumps(problems[i])
            recent_results = context.get_relevant_context(recent_query, max_blocks=5)
            immediate_hits += len(
                [r for r in recent_results if r in problems[i - 5 : i + 1]]
            )

            # Test short-term memory (problems from 6-20 positions back)
            if i >= 20:
                mid_query = json.dumps(problems[i - 15])
                mid_results = context.get_relevant_context(mid_query, max_blocks=5)
                short_term_hits += len(
                    [r for r in mid_results if r in problems[i - 20 : i - 5]]
                )

            # Test long-term memory (problems from >20 positions back)
            if i >= 40:
                old_query = json.dumps(problems[i - 35])
                old_results = context.get_relevant_context(old_query, max_blocks=5)
                long_term_hits += len(
                    [r for r in old_results if r in problems[: i - 20]]
                )

            # Calculate compression metrics
            total_tokens += sum(len(str(p)) for p in problems[max(0, i - 9) : i + 1])
            compressed_tokens += sum(
                len(str(block.content)) for block in context.context_blocks
            )

    # Calculate final metrics
    compression_ratio = compressed_tokens / total_tokens if total_tokens > 0 else 0
    immediate_recall = immediate_hits / (len(problems) // 10)
    short_term_recall = short_term_hits / max(1, (len(problems) - 20) // 10)
    long_term_recall = long_term_hits / max(1, (len(problems) - 40) // 10)

    print(f"\nContext Scaling Metrics:")
    print(f"Compression Ratio: {compression_ratio:.2f}")
    print(f"Immediate Memory Recall: {immediate_recall:.2f}")
    print(f"Short-term Memory Recall: {short_term_recall:.2f}")
    print(f"Long-term Memory Recall: {long_term_recall:.2f}")

    # Assertions to verify memory system is working
    assert compression_ratio < 1.0, "Should achieve some compression"
    assert immediate_recall > 0.7, "Should have good immediate recall"
    assert short_term_recall > 0.5, "Should have decent short-term recall"
    assert long_term_recall > 0.3, "Should have some long-term recall"


if __name__ == "__main__":
    test_context_scaling_and_compression()

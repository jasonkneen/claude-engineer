from typing import List, Dict, Optional, Any, Union, Callable
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import time
import random
import json
from datetime import datetime, timedelta

# Try to import tiktoken, fallback to simple tokenizer if not available
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

class SignificanceType(str, Enum):
    USER = "user"
    LLM = "llm"
    SYSTEM = "system"
    DERIVED = "derived"

class MemoryLevel(str, Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

@dataclass
class MemoryBlock:
    content: str
    tokens: int
    significance_type: SignificanceType
    timestamp: float
    id: int
    level: MemoryLevel = MemoryLevel.WORKING
    embedding: Optional[np.ndarray] = None
    w3w_tokens: List[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class MemoryManager:
    def __init__(
        self,
        working_memory_limit: int = 200000,  # Claude context window size
        archival_memory_limit: int = 1000000,  # Total memory size for archival
        archive_threshold: int = 150000,  # When to start archiving
        similarity_threshold: float = 0.85,
        promotion_threshold: int = 5,
        cleanup_interval: int = 1000,
        memory_server_client: Optional[Any] = None,
        stats_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        auto_archive: bool = True,
    ):
        self.working_memory: List[MemoryBlock] = []
        self.short_term_memory: List[MemoryBlock] = []
        self.long_term_memory: List[MemoryBlock] = []
        self.archived_memories: List[Dict[str, Any]] = []
        self.nexus_points: Dict[int, MemoryBlock] = {}

        # Limits and thresholds
        self.working_memory_limit = working_memory_limit
        self.archival_memory_limit = archival_memory_limit
        self.archive_threshold = archive_threshold
        self.similarity_threshold = similarity_threshold
        self.promotion_threshold = promotion_threshold
        self.cleanup_interval = cleanup_interval
        self.auto_archive = auto_archive

        # Memory server integration
        self.memory_server = memory_server_client
        self.stats_callback = stats_callback

        # Initialize tokenizer if available
        self.tokenizer = (
            tiktoken.get_encoding("cl100k_base") if TIKTOKEN_AVAILABLE else None
        )

        # Stats
        self.block_counter = 0
        self.promotion_count = 0
        self.demotion_count = 0
        self.merge_count = 0
        self.retrieval_count = 0
        self.generation_count = 0
        self.last_recall_time = 0
        self.last_cleanup_time = time.time()

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken if available, otherwise use word-based counting"""
        if TIKTOKEN_AVAILABLE and self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Simple word-based tokenization as fallback
            return len(text.split())

    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate simple embedding for text (placeholder for proper embedding)"""
        # This is a simplified embedding - in production use a proper embedding model
        words = text.lower().split()
        embedding = np.zeros(100)  # 100-dim embedding
        for i, word in enumerate(words):
            embedding[hash(word) % 100] += 1
        return embedding / (np.linalg.norm(embedding) + 1e-8)

    def _generate_w3w_tokens(self, text: str) -> List[str]:
        """Generate What3Words-style tokens for the text"""
        words = text.lower().split()
        if len(words) < 3:
            words.extend([""] * (3 - len(words)))
        return [words[i] for i in sorted(random.sample(range(len(words)), 3))]

    def add_memory_block(
        self,
        content: str,
        significance_type: Union[SignificanceType, str] = SignificanceType.USER,
    ) -> int:
        """Add a new memory block to working memory"""
        # Create block
        tokens = self._count_tokens(content)
        block = MemoryBlock(
            content=content,
            tokens=tokens,
            significance_type=significance_type,
            timestamp=time.time(),
            id=self.block_counter,
            embedding=self._generate_embedding(content),
            w3w_tokens=self._generate_w3w_tokens(content),
        )

        # Add to working memory
        self.working_memory.append(block)
        self.block_counter += 1
        self.generation_count += 1

        # Add to nexus points if significant
        if significance_type in [
            SignificanceType.USER,
            SignificanceType.LLM,
            SignificanceType.SYSTEM,
        ]:
            self.nexus_points[block.id] = block

        # Check memory limits and compress if needed
        self._check_and_compress_memory()

        # Periodic cleanup
        if time.time() - self.last_cleanup_time > self.cleanup_interval:
            self._cleanup_memory()
            self.last_cleanup_time = time.time()

        if self.stats_callback:
            self.stats_callback(self.get_memory_stats())
        return block.id

    def _check_and_compress_memory(self):
        """Check memory limits and archive if needed"""
        working_size = sum(block.tokens for block in self.working_memory)

        if working_size > self.archive_threshold:
            self._archive_oldest_memories()

        if working_size > self.working_memory_limit:
            self._emergency_compress()

    def _archive_oldest_memories(self):
        """Archive oldest memories when approaching token limit"""
        ordered_blocks = sorted(self.working_memory, key=lambda b: b.timestamp)
        total_size = sum(block.tokens for block in self.working_memory)

        while total_size > self.archive_threshold and len(ordered_blocks) > 10:
            block = ordered_blocks.pop(0)
            self.working_memory.remove(block)
            block.level = MemoryLevel.SHORT_TERM
            self.short_term_memory.append(block)
            self.demotion_count += 1
            total_size = sum(block.tokens for block in self.working_memory)

        if self.stats_callback:
            self.stats_callback(self.get_memory_stats())

    def _emergency_compress(self):
        """Emergency compression when over absolute limit"""
        while sum(b.tokens for b in self.working_memory) > self.working_memory_limit:
            self._merge_similar_memories()
            if len(self.working_memory) <= 3:  # Prevent infinite loop
                break

        if self.stats_callback:
            self.stats_callback(self.get_memory_stats())

    def _merge_similar_memories(self):
        """Merge similar memories within each level"""
        for memory_list in [
            self.working_memory,
            self.short_term_memory,
            self.long_term_memory,
        ]:
            i = 0
            while i < len(memory_list):
                j = i + 1
                while j < len(memory_list):
                    block1, block2 = memory_list[i], memory_list[j]
                    if (
                        self._calculate_similarity(block1, block2)
                        > self.similarity_threshold
                    ):
                        merged_content = f"{block1.content} | {block2.content}"
                        merged_block = MemoryBlock(
                            content=merged_content,
                            tokens=self._count_tokens(merged_content),
                            significance_type=block1.significance_type,
                            timestamp=max(block1.timestamp, block2.timestamp),
                            id=self.block_counter,
                            level=block1.level,
                            embedding=self._generate_embedding(merged_content),
                            w3w_tokens=self._generate_w3w_tokens(merged_content),
                            access_count=max(block1.access_count, block2.access_count),
                            last_accessed=max(
                                block1.last_accessed, block2.last_accessed
                            ),
                        )
                        memory_list[i] = merged_block
                        memory_list.pop(j)
                        self.block_counter += 1
                        self.merge_count += 1
                    else:
                        j += 1
                i += 1

        if self.stats_callback:
            self.stats_callback(self.get_memory_stats())

    def _calculate_similarity(self, block1: MemoryBlock, block2: MemoryBlock) -> float:
        """Calculate cosine similarity between two memory blocks"""
        if block1.embedding is None or block2.embedding is None:
            return 0.0
        return float(np.dot(block1.embedding, block2.embedding))

    def get_relevant_context(
        self, query: str, max_blocks: int = 5
    ) -> List[MemoryBlock]:
        """Retrieve most relevant memory blocks for a given query"""
        start_time = time.time()
        query_embedding = self._generate_embedding(query)

        # Calculate similarities and sort blocks
        scored_blocks = []
        for block in (
            self.working_memory + self.short_term_memory + self.long_term_memory
        ):
            if block.embedding is not None:
                similarity = float(np.dot(query_embedding, block.embedding))
                scored_blocks.append((similarity, block))

                # Update access stats
                block.access_count += 1
                block.last_accessed = time.time()

                # Check for promotion
                if block.access_count >= self.promotion_threshold:
                    self._try_promote_block(block)

        self.last_recall_time = (time.time() - start_time) * 1000  # Convert to ms
        self.retrieval_count += 1

        # Return top matches
        matched_blocks = [
            block
            for _, block in sorted(scored_blocks, key=lambda x: x[0], reverse=True)[
                :max_blocks
            ]
        ]

        if self.stats_callback:
            self.stats_callback(self.get_memory_stats())

        return matched_blocks

    def _try_promote_block(self, block: MemoryBlock):
        """Try to promote a block based on its current level"""
        if block.level == MemoryLevel.LONG_TERM:
            block.level = MemoryLevel.SHORT_TERM
            self.long_term_memory.remove(block)
            self.short_term_memory.append(block)
            self.promotion_count += 1
        elif block.level == MemoryLevel.SHORT_TERM:
            block.level = MemoryLevel.WORKING
            self.short_term_memory.remove(block)
            self.working_memory.append(block)
            self.promotion_count += 1

        # Reset access count after promotion
        block.access_count = 0

        if self.stats_callback:
            self.stats_callback(self.get_memory_stats())

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about the memory system"""
        working_size = sum(block.tokens for block in self.working_memory)
        short_term_size = sum(block.tokens for block in self.short_term_memory)
        long_term_size = sum(block.tokens for block in self.long_term_memory)

        return {
            "pools": {
                "working": {
                    "count": len(self.working_memory),
                    "size": working_size,
                    "limit": self.working_memory_limit,
                    "utilization": working_size / self.working_memory_limit,
                },
                "short_term": {
                    "count": len(self.short_term_memory),
                    "size": short_term_size,
                    "limit": self.archival_memory_limit,
                    "utilization": short_term_size / self.archival_memory_limit,
                },
                "long_term": {
                    "count": len(self.long_term_memory),
                    "size": long_term_size,
                },
            },
            "operations": {
                "promotions": self.promotion_count,
                "demotions": self.demotion_count,
                "merges": self.merge_count,
                "retrievals": self.retrieval_count,
                "avg_recall_time": self.last_recall_time,
                "compression_count": self.merge_count,
            },
            "nexus_points": {
                "count": len(self.nexus_points),
                "types": {
                    "user": sum(
                        1
                        for b in self.nexus_points.values()
                        if b.significance_type == SignificanceType.USER
                    ),
                    "llm": sum(
                        1
                        for b in self.nexus_points.values()
                        if b.significance_type == SignificanceType.LLM
                    ),
                    "system": sum(
                        1
                        for b in self.nexus_points.values()
                        if b.significance_type == SignificanceType.SYSTEM
                    ),
                },
            },
            "generations": self.generation_count,
            "total_tokens": working_size + short_term_size + long_term_size,
        }

    def get_working_memory(self) -> List[MemoryBlock]:
        return self.working_memory

    def get_short_term_memory(self) -> List[MemoryBlock]:
        return self.short_term_memory

    def get_long_term_memory(self) -> List[MemoryBlock]:
        return self.long_term_memory

    def get_nexus_points(self) -> Dict[int, MemoryBlock]:
        return self.nexus_points

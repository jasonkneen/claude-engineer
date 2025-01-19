from typing import List, Dict, Optional, Any, Union
from enum import Enum


from dataclasses import dataclass
import time
import random
class SignificanceType(str, Enum):
    USER = "user"
    LLM = "llm"
    SYSTEM = "system"
    DERIVED = "derived"


class MemoryLevel(str, Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


from dataclasses import dataclass, field

@dataclass
class MemoryBlock:
    content: str
    tokens: int
    significance_type: SignificanceType
    timestamp: float
    id: int
    w3w_tokens: List[str] = field(default_factory=list)


class MemoryManager:
    def __init__(
        self, working_memory_limit: int = 8192, short_term_memory_limit: int = 128000
    ):
        self.working_memory: List[MemoryBlock] = []
        self.short_term_memory: List[MemoryBlock] = []
        self.long_term_memory: List[MemoryBlock] = []
        self.nexus_points: Dict[int, MemoryBlock] = {}

        self.working_memory_limit = working_memory_limit
        self.short_term_memory_limit = short_term_memory_limit

        self.block_counter = 0
        self.promotion_count = 0
        self.demotion_count = 0
        self.merge_count = 0
        self.retrieval_count = 0
        self.generation_count = 0
        self.last_recall_time = 0

    def add_memory_block(
        self,
        content: str,
        significance_type: Union[SignificanceType, str] = SignificanceType.USER,
    ) -> int:
        """Add a new memory block to working memory"""
        tokens = len(content.split())  # Simple tokenization
        block = MemoryBlock(
            content=content,
            tokens=tokens,
            significance_type=significance_type,
            timestamp=time.time(),
            id=self.block_counter,
            w3w_tokens=["word1", "word2", "word3"],
        )

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

        return block.id

    def promote_block(self, block_id: int) -> bool:
        """Promote a memory block to the next level"""
        # Find block in working memory
        for i, block in enumerate(self.working_memory):
            if block.id == block_id:
                self.short_term_memory.append(block)
                self.working_memory.pop(i)
                self.promotion_count += 1
                return True

        # Find block in short-term memory
        for i, block in enumerate(self.short_term_memory):
            if block.id == block_id:
                self.long_term_memory.append(block)
                self.short_term_memory.pop(i)
                self.promotion_count += 1
                return True

        return False

    def demote_block(self, block_id: int) -> bool:
        """Demote a memory block to the previous level"""
        # Find block in long-term memory
        for i, block in enumerate(self.long_term_memory):
            if block.id == block_id:
                self.short_term_memory.append(block)
                self.long_term_memory.pop(i)
                self.demotion_count += 1
                return True

        # Find block in short-term memory
        for i, block in enumerate(self.short_term_memory):
            if block.id == block_id:
                self.working_memory.append(block)
                self.short_term_memory.pop(i)
                self.demotion_count += 1
                return True

        return False

    def merge_blocks(self, block_ids: List[int]) -> Optional[int]:
        """Merge multiple memory blocks into one"""
        blocks = []
        # Collect blocks from all memory levels
        for bid in block_ids:
            block = self.find_block(bid)
            if block:
                blocks.append(block)

        if len(blocks) < 2:
            return None

        # Merge blocks
        merged_content = " ".join(b.content for b in blocks)
        merged_type = blocks[0].significance_type  # Use type of first block

        # Remove original blocks
        for block in blocks:
            self.remove_block(block.id)

        # Create new merged block
        new_id = self.add_memory_block(merged_content, merged_type)
        self.merge_count += 1

        return new_id

    def retrieve_blocks(self, keywords: List[str]) -> List[MemoryBlock]:
        """Retrieve memory blocks based on keywords"""
        start_time = time.time()

        results = []
        for keyword in keywords:
            # Search in all memory levels
            for block in (
                self.working_memory + self.short_term_memory + self.long_term_memory
            ):
                if keyword.lower() in block.content.lower():
                    results.append(block)

        self.last_recall_time = (time.time() - start_time) * 1000  # Convert to ms
        self.retrieval_count += 1

        return list(set(results))  # Remove duplicates

    def find_block(self, block_id: int) -> Optional[MemoryBlock]:
        """Find a block in any memory level"""
        for block in (
            self.working_memory + self.short_term_memory + self.long_term_memory
        ):
            if block.id == block_id:
                return block
        return None

    def remove_block(self, block_id: int) -> bool:
        """Remove a block from any memory level"""
        for memory_list in [
            self.working_memory,
            self.short_term_memory,
            self.long_term_memory,
        ]:
            for i, block in enumerate(memory_list):
                if block.id == block_id:
                    memory_list.pop(i)
                    if block_id in self.nexus_points:
                        del self.nexus_points[block_id]
                    return True
        return False

    def get_working_memory(self) -> List[MemoryBlock]:
        return self.working_memory

    def get_short_term_memory(self) -> List[MemoryBlock]:
        return self.short_term_memory

    def get_long_term_memory(self) -> List[MemoryBlock]:
        return self.long_term_memory

    def get_nexus_points(self) -> Dict[int, MemoryBlock]:
        return self.nexus_points

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system"""
        return {
            "total_blocks": len(
                self.working_memory + self.short_term_memory + self.long_term_memory
            ),
            "working_memory_blocks": len(self.working_memory),
            "short_term_memory_blocks": len(self.short_term_memory),
            "long_term_memory_blocks": len(self.long_term_memory),
            "nexus_points": len(self.nexus_points),
            "promotions": self.promotion_count,
            "demotions": self.demotion_count,
            "merges": self.merge_count,
            "retrievals": self.retrieval_count,
            "generations": self.generation_count,
            "last_recall_time_ms": self.last_recall_time,
        }

    def get_relevant_context(
        self, query: str, max_blocks: int = 5
    ) -> List[MemoryBlock]:
        """Retrieve most relevant memory blocks for a given query"""
        query_words = set(query.lower().split())
        scored_blocks = []

        # Search in all memory levels
        for block in (
            self.working_memory + self.short_term_memory + self.long_term_memory
        ):
            block_words = set(block.content.lower().split())
            common_words = query_words & block_words
            score = len(common_words) / len(block_words) if block_words else 0
            scored_blocks.append((score, block))

        # Sort by score and return top matches
        return [block for _, block in sorted(scored_blocks, reverse=True)[:max_blocks]]

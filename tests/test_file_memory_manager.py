import unittest
import shutil
import tempfile
import time
from pathlib import Path
from file_memory_manager import FileMemoryManager, MemoryBlock, MemoryTier, SignificanceType

class TestFileMemoryManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / ".memory"
        self.manager = FileMemoryManager(str(self.memory_dir))

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test if memory files are properly initialized"""
        for tier in MemoryTier:
            file_path = self.memory_dir / f"{tier.value.replace('_', '-')}.memory"
            self.assertTrue(file_path.exists())
        
        self.assertTrue((self.memory_dir / "stats.json").exists())

    def test_add_memory_block(self):
        """Test adding a memory block"""
        block = MemoryBlock(
            id="test1",
            content="Test content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )

        self.manager.add_memory_block(block)
        blocks = self.manager.get_memory_blocks(MemoryTier.WORKING)
        
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].id, "test1")
        self.assertEqual(blocks[0].content, "Test content")

    def test_update_memory_block(self):
        """Test updating a memory block"""
        block = MemoryBlock(
            id="test2",
            content="Original content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )

        self.manager.add_memory_block(block)
        block.content = "Updated content"
        self.manager.update_memory_block(block)

        blocks = self.manager.get_memory_blocks(MemoryTier.WORKING)
        self.assertEqual(blocks[0].content, "Updated content")

    def test_move_block_between_tiers(self):
        """Test moving a block between memory tiers"""
        block = MemoryBlock(
            id="test3",
            content="Migratable content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )

        # Add to working memory
        self.manager.add_memory_block(block)
        
        # Move to short-term memory
        self.manager.move_block_to_tier(
            block.id,
            MemoryTier.WORKING,
            MemoryTier.SHORT_TERM
        )

        # Verify block was moved
        working_blocks = self.manager.get_memory_blocks(MemoryTier.WORKING)
        short_term_blocks = self.manager.get_memory_blocks(MemoryTier.SHORT_TERM)

        self.assertEqual(len(working_blocks), 0)
        self.assertEqual(len(short_term_blocks), 1)
        self.assertEqual(short_term_blocks[0].id, "test3")

    def test_memory_statistics(self):
        """Test memory statistics tracking"""
        # Add blocks to different tiers
        blocks = [
            MemoryBlock(
                id=f"test{i}",
                content=f"Content {i}",
                tokens=10,
                timestamp=time.time(),
                significance_type=SignificanceType.USER,
                tier=tier
            )
            for i, tier in enumerate([
                MemoryTier.WORKING,
                MemoryTier.SHORT_TERM,
                MemoryTier.LONG_TERM
            ])
        ]

        for block in blocks:
            self.manager.add_memory_block(block)

        stats = self.manager.get_stats()
        
        self.assertEqual(stats["total_blocks"], 3)
        self.assertEqual(stats["total_tokens"], 30)
        self.assertEqual(stats["tiers"]["working"]["blocks"], 1)
        self.assertEqual(stats["tiers"]["short_term"]["blocks"], 1)
        self.assertEqual(stats["tiers"]["long_term"]["blocks"], 1)

    def test_nexus_point_handling(self):
        """Test handling of nexus points"""
        block = MemoryBlock(
            id="nexus1",
            content="Important system content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.SYSTEM,
            tier=MemoryTier.WORKING,
            is_nexus=True,
            nexus_metadata={
                "protection_level": "high",
                "importance": "critical"
            }
        )

        self.manager.add_memory_block(block)
        retrieved_block = self.manager.get_memory_blocks(MemoryTier.WORKING)[0]
        
        self.assertTrue(retrieved_block.is_nexus)
        self.assertEqual(retrieved_block.nexus_metadata["protection_level"], "high")

    def test_reference_handling(self):
        """Test handling of block references"""
        block = MemoryBlock(
            id="ref1",
            content="Content with references",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING,
            references={
                "keywords": ["test", "reference"],
                "related_blocks": ["block1", "block2"]
            }
        )

        self.manager.add_memory_block(block)
        retrieved_block = self.manager.get_memory_blocks(MemoryTier.WORKING)[0]
        
        self.assertEqual(len(retrieved_block.references["keywords"]), 2)
        self.assertEqual(len(retrieved_block.references["related_blocks"]), 2)

if __name__ == '__main__':
    unittest.main()
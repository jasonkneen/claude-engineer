import unittest
import tempfile
import shutil
import time
from pathlib import Path
from file_memory_manager import FileMemoryManager, MemoryBlock, MemoryTier, SignificanceType
from memory_pruner import MemoryPruner

class TestMemoryPruner(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / ".memory"
        self.file_manager = FileMemoryManager(str(self.memory_dir))
        
        # Create pruner with smaller limits for testing
        self.pruner = MemoryPruner(
            file_manager=self.file_manager,
            working_memory_limit=1000,
            prune_threshold=800,
            min_access_threshold=2,
            min_age_for_pruning=1  # 1 second for testing
        )

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_pruning_threshold(self):
        """Test that pruning occurs when threshold is exceeded"""
        # Add blocks until we exceed threshold
        blocks = []
        for i in range(10):
            block = MemoryBlock(
                id=f"test{i}",
                content=f"Content {i} " * 20,  # Make content large enough
                tokens=100,  # Each block is 100 tokens
                timestamp=time.time() - 10,  # Make them old enough to prune
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING
            )
            blocks.append(block)
            self.file_manager.add_memory_block(block)

        # Let some time pass for pruning eligibility
        time.sleep(1.1)
        
        # Trigger pruning
        did_prune = self.pruner.check_and_prune()
        self.assertTrue(did_prune)

        # Verify working memory is under threshold
        stats = self.file_manager.get_stats()
        self.assertLess(stats["tiers"]["working"]["tokens"], self.pruner.prune_threshold)

    def test_nexus_point_protection(self):
        """Test that nexus points are protected from pruning"""
        # Add regular block
        regular_block = MemoryBlock(
            id="regular1",
            content="Regular content " * 20,
            tokens=100,
            timestamp=time.time() - 10,
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )
        
        # Add nexus point
        nexus_block = MemoryBlock(
            id="nexus1",
            content="Nexus content " * 20,
            tokens=100,
            timestamp=time.time() - 10,
            significance_type=SignificanceType.SYSTEM,
            tier=MemoryTier.WORKING,
            is_nexus=True
        )

        self.file_manager.add_memory_block(regular_block)
        self.file_manager.add_memory_block(nexus_block)

        time.sleep(1.1)
        self.pruner.check_and_prune()

        # Verify nexus point remains in working memory
        working_blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        working_ids = [block.id for block in working_blocks]
        self.assertIn("nexus1", working_ids)

    def test_w3w_summary_generation(self):
        """Test what3words style summary generation"""
        content = "The quick brown fox jumps over the lazy dog while watching the sunset"
        block = MemoryBlock(
            id="test_summary",
            content=content,
            tokens=50,
            timestamp=time.time() - 10,
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )

        self.file_manager.add_memory_block(block)
        time.sleep(1.1)
        self.pruner.check_and_prune()

        # Check if summary was created in working memory
        working_blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        summaries = [b for b in working_blocks if b.id.endswith("_summary")]
        
        self.assertEqual(len(summaries), 1)
        self.assertTrue(summaries[0].content.startswith("Summary:"))
        self.assertEqual(len(summaries[0].content.split("•")), 3)

    def test_archival_process(self):
        """Test the archival process from working to stale memory"""
        # Add block to working memory
        block = MemoryBlock(
            id="archive_test",
            content="Content to archive",
            tokens=50,
            timestamp=time.time() - 87000,  # Older than 24 hours
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )
        
        self.file_manager.add_memory_block(block)
        
        # Move to short-term memory
        self.pruner.check_and_prune()
        
        # Check short-term to long-term archival
        self.pruner.check_and_archive_short_term(age_threshold=1)
        time.sleep(1.1)
        
        # Check long-term to stale archival
        self.pruner.check_and_archive_long_term(age_threshold=1)
        time.sleep(1.1)

        # Verify block made it to stale memory
        stale_blocks = self.file_manager.get_memory_blocks(MemoryTier.STALE)
        stale_ids = [block.id for block in stale_blocks]
        self.assertIn("archive_test", stale_ids)

    def test_block_priority_calculation(self):
        """Test block priority calculation for pruning decisions"""
        # Create blocks with different characteristics
        blocks = [
            # High priority block (recent, frequently accessed)
            MemoryBlock(
                id="high_priority",
                content="Important content",
                tokens=50,
                timestamp=time.time() - 5,
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING,
                access_count=10
            ),
            # Low priority block (old, rarely accessed)
            MemoryBlock(
                id="low_priority",
                content="Less important content",
                tokens=50,
                timestamp=time.time() - 1000,
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING,
                access_count=1
            )
        ]

        for block in blocks:
            self.file_manager.add_memory_block(block)

        time.sleep(1.1)
        self.pruner.check_and_prune()

        # Verify high priority block remains in working memory
        working_blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        working_ids = [block.id for block in working_blocks]
        self.assertIn("high_priority", working_ids)
        
        # Verify low priority block was moved to short-term memory
        short_term_blocks = self.file_manager.get_memory_blocks(MemoryTier.SHORT_TERM)
        short_term_ids = [block.id for block in short_term_blocks]
        self.assertIn("low_priority", short_term_ids)

    def test_reference_preservation(self):
        """Test that references are preserved during pruning"""
        # Create a block with references
        block = MemoryBlock(
            id="ref_test",
            content="Content with references",
            tokens=50,
            timestamp=time.time() - 10,
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING,
            references={
                "keywords": ["test", "reference"],
                "related_blocks": ["block1", "block2"]
            }
        )

        self.file_manager.add_memory_block(block)
        time.sleep(1.1)
        self.pruner.check_and_prune()

        # Check if references are preserved in summary
        working_blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        summary_block = next(b for b in working_blocks if b.id == "ref_test_summary")
        
        self.assertEqual(set(summary_block.references["keywords"]), {"test", "reference"})
        self.assertIn("ref_test", summary_block.references["related_blocks"])

if __name__ == '__main__':
    unittest.main()
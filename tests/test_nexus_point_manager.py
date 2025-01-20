import unittest
import tempfile
import shutil
import time
from pathlib import Path
from file_memory_manager import FileMemoryManager, MemoryBlock, MemoryTier, SignificanceType
from nexus_point_manager import NexusPointManager

class TestNexusPointManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / ".memory"
        self.file_manager = FileMemoryManager(str(self.memory_dir))
        
        # Create nexus manager with smaller thresholds for testing
        self.nexus_manager = NexusPointManager(
            file_manager=self.file_manager,
            max_access_history=10,
            nexus_threshold=0.5,
            access_window=1,  # 1 second for testing
            max_nexus_points=5
        )

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_access_tracking(self):
        """Test tracking of memory block accesses"""
        block = MemoryBlock(
            id="test1",
            content="Test content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )
        
        self.file_manager.add_memory_block(block)
        
        # Register multiple accesses
        for _ in range(6):  # Should exceed nexus_threshold (0.5 * 10)
            self.nexus_manager.register_access(block.id)
            time.sleep(0.1)  # Small delay between accesses

        # Check if block was promoted to nexus point
        blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        promoted_block = next(b for b in blocks if b.id == "test1")
        self.assertTrue(promoted_block.is_nexus)

    def test_protection_levels(self):
        """Test assignment of protection levels"""
        # Create blocks with different significance types
        blocks = {
            "system": MemoryBlock(
                id="system1",
                content="System content",
                tokens=10,
                timestamp=time.time(),
                significance_type=SignificanceType.SYSTEM,
                tier=MemoryTier.WORKING
            ),
            "user": MemoryBlock(
                id="user1",
                content="User content",
                tokens=10,
                timestamp=time.time(),
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING
            ),
            "llm": MemoryBlock(
                id="llm1",
                content="LLM content",
                tokens=10,
                timestamp=time.time(),
                significance_type=SignificanceType.LLM,
                tier=MemoryTier.WORKING
            )
        }

        for block in blocks.values():
            self.file_manager.add_memory_block(block)
            # Trigger nexus promotion
            for _ in range(6):
                self.nexus_manager.register_access(block.id)
                time.sleep(0.1)

        working_blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        
        for block in working_blocks:
            if block.id == "system1":
                self.assertEqual(block.nexus_metadata["protection_level"], "high")
            elif block.id == "user1":
                self.assertEqual(block.nexus_metadata["protection_level"], "high")
            elif block.id == "llm1":
                self.assertEqual(block.nexus_metadata["protection_level"], "medium")

    def test_nexus_point_limit(self):
        """Test enforcement of maximum nexus points"""
        # Create more blocks than max_nexus_points
        for i in range(7):  # max is 5
            block = MemoryBlock(
                id=f"test{i}",
                content=f"Content {i}",
                tokens=10,
                timestamp=time.time(),
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING
            )
            self.file_manager.add_memory_block(block)
            
            # Promote to nexus point
            for _ in range(6):
                self.nexus_manager.register_access(block.id)
                time.sleep(0.1)

        # Check nexus points
        self.nexus_manager.check_nexus_points()
        nexus_points = self.nexus_manager.get_nexus_points()
        
        self.assertLessEqual(len(nexus_points), 5)

    def test_importance_calculation(self):
        """Test calculation of importance scores"""
        block = MemoryBlock(
            id="test_importance",
            content="Important content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.SYSTEM,
            tier=MemoryTier.WORKING,
            references={"keywords": [], "related_blocks": ["ref1", "ref2"]}
        )
        
        self.file_manager.add_memory_block(block)
        
        # Register multiple accesses
        for _ in range(6):
            self.nexus_manager.register_access(block.id)
            time.sleep(0.1)

        # Get promoted block
        blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        nexus_block = next(b for b in blocks if b.id == "test_importance")
        
        # Check importance score components
        self.assertGreater(nexus_block.nexus_metadata["importance_score"], 0.5)

    def test_nexus_point_reinforcement(self):
        """Test reinforcement of nexus points"""
        block = MemoryBlock(
            id="test_reinforce",
            content="Content to reinforce",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING
        )
        
        self.file_manager.add_memory_block(block)
        
        # Promote to nexus point
        for _ in range(6):
            self.nexus_manager.register_access(block.id)
            time.sleep(0.1)

        # Get initial importance
        blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        initial_block = next(b for b in blocks if b.id == "test_reinforce")
        initial_importance = initial_block.nexus_metadata["importance_score"]

        # Reinforce nexus point
        self.nexus_manager.reinforce_nexus_point(block.id)

        # Check if importance increased
        blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        reinforced_block = next(b for b in blocks if b.id == "test_reinforce")
        self.assertGreater(
            reinforced_block.nexus_metadata["importance_score"],
            initial_importance
        )

    def test_nexus_stats(self):
        """Test nexus point statistics"""
        # Create blocks with different protection levels
        blocks = [
            MemoryBlock(
                id=f"stats_test{i}",
                content=f"Content {i}",
                tokens=10,
                timestamp=time.time(),
                significance_type=sig_type,
                tier=MemoryTier.WORKING
            )
            for i, sig_type in enumerate([
                SignificanceType.SYSTEM,
                SignificanceType.USER,
                SignificanceType.LLM
            ])
        ]

        for block in blocks:
            self.file_manager.add_memory_block(block)
            # Promote to nexus point
            for _ in range(6):
                self.nexus_manager.register_access(block.id)
                time.sleep(0.1)

        stats = self.nexus_manager.get_nexus_stats()
        
        self.assertEqual(stats["total_count"], 3)
        self.assertEqual(stats["protection_levels"]["high"], 2)  # SYSTEM and USER
        self.assertEqual(stats["protection_levels"]["medium"], 1)  # LLM
        self.assertGreater(stats["average_importance"], 0)

if __name__ == '__main__':
    unittest.main()
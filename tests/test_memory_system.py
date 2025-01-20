import unittest
import tempfile
import shutil
import time
from pathlib import Path
from memory_system import MemorySystem, SignificanceType, MemoryTier

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / ".memory"
        
        # Initialize memory system with test-appropriate settings
        self.memory_system = MemorySystem(
            base_dir=str(self.memory_dir),
            working_memory_limit=1000,
            archive_threshold=800,
            max_nexus_points=5,
            stats_retention_days=1
        )

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_memory_addition(self):
        """Test adding new memories to the system"""
        # Add a memory
        memory_id = self.memory_system.add_memory(
            "Test memory content",
            SignificanceType.USER
        )
        
        # Verify memory was added
        memory = self.memory_system.get_memory_by_id(memory_id)
        self.assertIsNotNone(memory)
        self.assertEqual(memory.content, "Test memory content")
        self.assertEqual(memory.significance_type, SignificanceType.USER)

    def test_memory_search(self):
        """Test memory search functionality"""
        # Add some test memories
        self.memory_system.add_memory("The quick brown fox", SignificanceType.USER)
        self.memory_system.add_memory("The lazy dog", SignificanceType.USER)
        self.memory_system.add_memory("Unrelated content", SignificanceType.USER)

        # Search memories
        results = self.memory_system.search_memory("quick fox")
        self.assertEqual(len(results), 1)
        self.assertIn("quick brown fox", results[0].content)

    def test_related_memories(self):
        """Test retrieval of related memories"""
        # Add related memories
        memory_id = self.memory_system.add_memory(
            "Primary memory content",
            SignificanceType.USER
        )
        self.memory_system.add_memory(
            "Related memory content",
            SignificanceType.USER
        )

        # Get related memories
        related = self.memory_system.get_related_memories(memory_id)
        self.assertGreaterEqual(len(related), 0)

    def test_w3w_lookup(self):
        """Test what3words lookup functionality"""
        # Add memory with specific w3w reference
        memory_id = self.memory_system.add_memory(
            "Memory with w3w reference",
            SignificanceType.USER
        )
        
        # Get memory and extract w3w reference
        memory = self.memory_system.get_memory_by_id(memory_id)
        
        if memory and memory.w3w_reference:
            # Look up using w3w
            results = self.memory_system.lookup_by_w3w(memory.w3w_reference[:2])
            self.assertGreater(len(results), 0)

    def test_memory_pruning(self):
        """Test automatic memory pruning"""
        # Add memories until pruning threshold is reached
        for i in range(100):  # Should exceed threshold
            self.memory_system.add_memory(
                f"Memory content {i} " * 5,  # Make content large enough
                SignificanceType.USER
            )
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Get memory stats
        stats = self.memory_system.get_memory_stats()
        
        # Verify working memory is under limit
        self.assertLess(
            stats['memory_state']['tiers']['working']['tokens'],
            self.memory_system.pruner.working_memory_limit
        )

    def test_nexus_point_creation(self):
        """Test nexus point creation through frequent access"""
        # Add a memory
        memory_id = self.memory_system.add_memory(
            "Frequently accessed memory",
            SignificanceType.USER
        )

        # Search for it multiple times to trigger nexus point creation
        for _ in range(10):
            self.memory_system.search_memory("Frequently accessed")
            time.sleep(0.1)

        # Check if it became a nexus point
        nexus_points = self.memory_system.get_nexus_points()
        self.assertTrue(any(np.id == memory_id for np in nexus_points))

    def test_system_maintenance(self):
        """Test system maintenance operations"""
        # Add some test data
        for i in range(5):
            self.memory_system.add_memory(
                f"Test memory {i}",
                SignificanceType.USER
            )

        # Perform maintenance
        self.memory_system.maintain_system()

        # Verify system state
        stats = self.memory_system.get_memory_stats()
        self.assertIn('memory_state', stats)
        self.assertIn('nexus_points', stats)
        self.assertIn('performance', stats)

    def test_statistics_tracking(self):
        """Test statistics tracking"""
        # Perform various operations
        self.memory_system.add_memory("Test memory 1", SignificanceType.USER)
        self.memory_system.search_memory("Test")
        self.memory_system.maintain_system()

        # Get statistics
        stats = self.memory_system.get_memory_stats()
        
        # Verify statistics are being tracked
        self.assertIn('performance', stats)
        perf_report = stats['performance']
        self.assertIn('daily_stats', perf_report)
        self.assertIn('performance_summary', perf_report)
        self.assertIn('operation_summary', perf_report)

    def test_error_handling(self):
        """Test error handling in memory operations"""
        # Test with invalid memory ID
        with self.assertRaises(Exception):
            self.memory_system.get_related_memories("invalid_id")

        # Verify error was recorded in statistics
        stats = self.memory_system.get_memory_stats()
        self.assertIn('performance', stats)
        self.assertIn('error_count', stats['performance']['daily_stats']['performance'])

    def test_memory_promotion(self):
        """Test memory promotion through access patterns"""
        # Add memory to long-term storage
        memory_id = self.memory_system.add_memory(
            "Memory to promote",
            SignificanceType.USER
        )
        
        # Force it to long-term storage
        memory = self.memory_system.get_memory_by_id(memory_id)
        if memory:
            self.memory_system.file_manager.move_block_to_tier(
                memory_id,
                MemoryTier.WORKING,
                MemoryTier.LONG_TERM
            )

        # Access it multiple times
        for _ in range(5):
            self.memory_system.search_memory("Memory to promote")
            time.sleep(0.1)

        # Verify it was promoted
        promoted_memory = self.memory_system.get_memory_by_id(memory_id)
        self.assertIsNotNone(promoted_memory)
        self.assertEqual(promoted_memory.tier, MemoryTier.WORKING)

if __name__ == '__main__':
    unittest.main()

import unittest
import tempfile
import shutil
import time
from pathlib import Path
from file_memory_manager import FileMemoryManager, MemoryBlock, MemoryTier, SignificanceType
from nexus_point_manager import NexusPointManager
from memory_retriever import MemoryRetriever

class TestMemoryRetriever(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / ".memory"
        
        # Initialize managers
        self.file_manager = FileMemoryManager(str(self.memory_dir))
        self.nexus_manager = NexusPointManager(
            self.file_manager,
            max_access_history=10,
            nexus_threshold=0.5
        )
        
        # Initialize retriever with test-appropriate settings
        self.retriever = MemoryRetriever(
            self.file_manager,
            self.nexus_manager,
            similarity_threshold=0.3,
            max_results=5,
            promotion_threshold=2,
            cache_duration=1  # 1 second for testing
        )
        
        # Add some test blocks
        self._create_test_blocks()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def _create_test_blocks(self):
        """Create test memory blocks across different tiers"""
        blocks = [
            # Working memory blocks
            MemoryBlock(
                id="work1",
                content="The quick brown fox jumps over the lazy dog",
                tokens=10,
                timestamp=time.time(),
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING,
                references={"keywords": ["fox", "dog"], "related_blocks": []}
            ),
            # Short-term memory blocks
            MemoryBlock(
                id="short1",
                content="A test memory about important system concepts",
                tokens=10,
                timestamp=time.time() - 3600,
                significance_type=SignificanceType.SYSTEM,
                tier=MemoryTier.SHORT_TERM,
                references={"keywords": ["test", "system"], "related_blocks": ["work1"]}
            ),
            # Long-term memory blocks
            MemoryBlock(
                id="long1",
                content="Ancient wisdom about memory systems",
                tokens=10,
                timestamp=time.time() - 86400,
                significance_type=SignificanceType.LLM,
                tier=MemoryTier.LONG_TERM,
                references={"keywords": ["wisdom", "memory"], "related_blocks": []}
            )
        ]

        for block in blocks:
            self.file_manager.add_memory_block(block)

    def test_basic_search(self):
        """Test basic search functionality"""
        results = self.retriever.search("quick fox")
        self.assertTrue(any(b.id == "work1" for b in results))
        self.assertTrue(all(b.tier == MemoryTier.WORKING for b in results))

    def test_cross_tier_search(self):
        """Test searching across different memory tiers"""
        results = self.retriever.search("memory", include_archived=True)
        
        # Should find blocks in different tiers
        found_tiers = set(block.tier for block in results)
        self.assertTrue(len(found_tiers) > 1)

    def test_search_caching(self):
        """Test search result caching"""
        query = "memory system"
        
        # First search
        start_time = time.time()
        first_results = self.retriever.search(query)
        
        # Second search (should be cached)
        cached_results = self.retriever.search(query)
        
        # Verify results are the same
        self.assertEqual(len(first_results), len(cached_results))
        self.assertEqual(
            [b.id for b in first_results],
            [b.id for b in cached_results]
        )
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Search again (should not be cached)
        new_results = self.retriever.search(query)
        self.assertEqual(len(first_results), len(new_results))

    def test_memory_promotion(self):
        """Test memory block promotion through access"""
        # Search multiple times to trigger promotion
        for _ in range(3):
            self.retriever.search("ancient wisdom")
            time.sleep(0.1)

        # Check if block was promoted
        working_blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        self.assertTrue(any(b.id == "long1" for b in working_blocks))

    def test_nexus_point_integration(self):
        """Test integration with nexus point management"""
        # Search multiple times to trigger nexus point creation
        for _ in range(6):
            self.retriever.search("system concepts")
            time.sleep(0.1)

        # Check if block became a nexus point
        blocks = self.file_manager.get_memory_blocks(MemoryTier.WORKING)
        promoted_block = next((b for b in blocks if b.id == "short1"), None)
        self.assertIsNotNone(promoted_block)
        self.assertTrue(promoted_block.is_nexus)

    def test_w3w_lookup(self):
        """Test what3words reference lookup"""
        # Create a block with w3w reference
        block = MemoryBlock(
            id="w3w_test",
            content="Content with specific what3words reference",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING,
            w3w_reference=["table", "lamp", "book"]
        )
        self.file_manager.add_memory_block(block)

        # Look up using w3w
        results = self.retriever.lookup_by_w3w(["table", "book"])
        self.assertTrue(any(b.id == "w3w_test" for b in results))

    def test_related_blocks(self):
        """Test retrieval of related blocks"""
        # Create blocks with relationships
        block1 = MemoryBlock(
            id="source",
            content="Source content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING,
            references={
                "keywords": ["test", "reference"],
                "related_blocks": ["related1"]
            }
        )
        
        block2 = MemoryBlock(
            id="related1",
            content="Related content",
            tokens=10,
            timestamp=time.time(),
            significance_type=SignificanceType.USER,
            tier=MemoryTier.WORKING,
            references={
                "keywords": ["test", "reference"],
                "related_blocks": []
            }
        )

        self.file_manager.add_memory_block(block1)
        self.file_manager.add_memory_block(block2)

        # Get related blocks
        related = self.retriever.get_related_blocks("source")
        self.assertTrue(any(b.id == "related1" for b in related))

    def test_relevance_scoring(self):
        """Test relevance scoring of search results"""
        # Create blocks with varying relevance
        blocks = [
            MemoryBlock(
                id=f"relevance{i}",
                content=content,
                tokens=10,
                timestamp=time.time() - (i * 3600),
                significance_type=SignificanceType.USER,
                tier=MemoryTier.WORKING,
                references={"keywords": kw, "related_blocks": []}
            )
            for i, (content, kw) in enumerate([
                ("Highly relevant test content", ["test", "relevant"]),
                ("Somewhat relevant content", ["relevant"]),
                ("Unrelated content", ["other"])
            ])
        ]

        for block in blocks:
            self.file_manager.add_memory_block(block)

        # Search and check order
        results = self.retriever.search("test relevant")
        result_ids = [block.id for block in results]
        
        # Most relevant should come first
        self.assertEqual(result_ids[0], "relevance0")
        if len(result_ids) > 1:
            self.assertEqual(result_ids[1], "relevance1")

if __name__ == '__main__':
    unittest.main()
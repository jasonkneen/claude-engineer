import unittest
import tempfile
import shutil
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from file_memory_manager import FileMemoryManager, MemoryBlock, MemoryTier, SignificanceType
from memory_statistics import MemoryStatistics

class TestMemoryStatistics(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.test_dir) / ".memory"
        self.stats_dir = self.memory_dir / "stats"
        
        # Initialize managers
        self.file_manager = FileMemoryManager(str(self.memory_dir))
        
        # Initialize statistics with test-appropriate settings
        self.statistics = MemoryStatistics(
            self.file_manager,
            stats_dir=str(self.stats_dir),
            metrics_retention_days=1,
            performance_log_size=10,
            snapshot_interval=1  # 1 second for testing
        )
        
        # Add some test blocks
        self._create_test_blocks()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def _create_test_blocks(self):
        """Create test memory blocks across different tiers"""
        blocks = [
            MemoryBlock(
                id=f"test{i}",
                content=f"Test content {i}",
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
            self.file_manager.add_memory_block(block)

    def test_directory_initialization(self):
        """Test statistics directory structure initialization"""
        self.assertTrue((self.stats_dir / "daily").exists())
        self.assertTrue((self.stats_dir / "snapshots").exists())
        self.assertTrue((self.stats_dir / "performance").exists())

    def test_operation_recording(self):
        """Test recording of memory operations"""
        # Record some operations
        self.statistics.record_operation(
            operation="add",
            tier=MemoryTier.WORKING,
            duration=0.1,
            block_count=1,
            token_count=10
        )
        
        self.statistics.record_operation(
            operation="search",
            tier=MemoryTier.SHORT_TERM,
            duration=0.2,
            block_count=2,
            token_count=20
        )

        # Get daily statistics
        stats = self.statistics.get_daily_statistics()
        
        self.assertEqual(stats['operations']['total_count'], 2)
        self.assertEqual(stats['operations']['by_type']['add'], 1)
        self.assertEqual(stats['operations']['by_type']['search'], 1)

    def test_performance_recording(self):
        """Test recording of performance metrics"""
        # Record some performance metrics
        self.statistics.record_performance(
            operation_time=0.1,
            memory_usage=1000,
            success=True
        )
        
        self.statistics.record_performance(
            operation_time=0.2,
            memory_usage=1500,
            success=False,
            error="Test error"
        )

        # Get performance report
        report = self.statistics.get_performance_report()
        
        self.assertEqual(report['performance_summary']['success_rate'], 0.5)
        self.assertGreater(report['performance_summary']['average_operation_time'], 0)

    def test_snapshot_creation(self):
        """Test creation of memory state snapshots"""
        # Record some operations
        self.statistics.record_operation(
            operation="test",
            tier=MemoryTier.WORKING,
            duration=0.1,
            block_count=1,
            token_count=10
        )
        
        # Wait for snapshot interval
        time.sleep(1.1)
        
        # Record another operation to trigger snapshot
        self.statistics.record_operation(
            operation="test2",
            tier=MemoryTier.WORKING,
            duration=0.1,
            block_count=1,
            token_count=10
        )

        # Check if snapshot was created
        snapshots = list((self.stats_dir / "snapshots").glob("*.json"))
        self.assertGreater(len(snapshots), 0)
        
        # Verify snapshot content
        with open(snapshots[0], 'r') as f:
            snapshot = json.load(f)
            self.assertIn('memory_stats', snapshot)
            self.assertIn('performance_metrics', snapshot)
            self.assertIn('operation_metrics', snapshot)

    def test_metrics_cleanup(self):
        """Test cleanup of old metrics"""
        # Create an old metrics file
        old_date = (datetime.now() - timedelta(days=2)).date()
        old_metrics_file = self.stats_dir / "daily" / f"{old_date}.json"
        old_metrics_file.parent.mkdir(exist_ok=True)
        
        with open(old_metrics_file, 'w') as f:
            json.dump({"test": "data"}, f)

        # Create an old snapshot
        old_snapshot_file = (
            self.stats_dir / "snapshots" /
            f"snapshot_{int(time.time() - 172800)}.json"
        )
        with open(old_snapshot_file, 'w') as f:
            json.dump({"test": "data"}, f)

        # Trigger cleanup
        self.statistics._cleanup_old_metrics()

        # Verify old files were removed
        self.assertFalse(old_metrics_file.exists())
        self.assertFalse(old_snapshot_file.exists())

    def test_performance_log_size_limit(self):
        """Test performance log size limiting"""
        # Record more than the limit
        for i in range(15):  # Limit is 10
            self.statistics.record_performance(
                operation_time=0.1,
                memory_usage=1000,
                success=True
            )

        # Get performance summary
        summary = self.statistics._get_performance_summary()
        
        # Check if only the most recent entries were kept
        self.assertLessEqual(
            len(self.statistics._performance_log),
            self.statistics.performance_log_size
        )

    def test_daily_statistics_generation(self):
        """Test generation of daily statistics"""
        # Record various operations
        operations = [
            ("add", MemoryTier.WORKING),
            ("search", MemoryTier.SHORT_TERM),
            ("prune", MemoryTier.LONG_TERM)
        ]
        
        for op, tier in operations:
            self.statistics.record_operation(
                operation=op,
                tier=tier,
                duration=0.1,
                block_count=1,
                token_count=10
            )

        # Get daily statistics
        stats = self.statistics.get_daily_statistics()
        
        # Verify statistics content
        self.assertEqual(stats['date'], datetime.now().date().isoformat())
        self.assertEqual(stats['operations']['total_count'], len(operations))
        self.assertEqual(
            len(stats['operations']['by_type']),
            len(set(op for op, _ in operations))
        )

    def test_performance_report_generation(self):
        """Test generation of performance report"""
        # Record some test data
        self.statistics.record_operation(
            operation="test",
            tier=MemoryTier.WORKING,
            duration=0.1,
            block_count=1,
            token_count=10
        )
        
        self.statistics.record_performance(
            operation_time=0.1,
            memory_usage=1000,
            success=True
        )

        # Generate report
        report = self.statistics.get_performance_report()
        
        # Verify report structure
        self.assertIn('timestamp', report)
        self.assertIn('daily_stats', report)
        self.assertIn('performance_summary', report)
        self.assertIn('operation_summary', report)
        self.assertIn('memory_state', report)

if __name__ == '__main__':
    unittest.main()
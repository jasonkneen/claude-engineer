from typing import Dict, List, Any, Optional
import time
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from file_memory_manager import FileMemoryManager, MemoryTier, SignificanceType

@dataclass
class PerformanceMetrics:
    operation_time: float
    memory_usage: int
    success: bool
    error: Optional[str] = None

@dataclass
class OperationMetrics:
    operation: str
    timestamp: float
    duration: float
    tier: MemoryTier
    block_count: int
    token_count: int

class MemoryStatistics:
    def __init__(
        self,
        file_manager: FileMemoryManager,
        stats_dir: str = None,
        metrics_retention_days: int = 30,
        performance_log_size: int = 1000,
        snapshot_interval: int = 3600  # 1 hour
    ):
        self.file_manager = file_manager
        # If stats_dir is not provided, create it under the memory_dir
        if stats_dir is None:
            self.stats_dir = Path(file_manager.memory_dir) / "statistics"
        else:
            self.stats_dir = Path(stats_dir)
            
        self.metrics_retention_days = metrics_retention_days
        self.performance_log_size = performance_log_size
        self.snapshot_interval = snapshot_interval

        self._performance_log: List[PerformanceMetrics] = []
        self._operation_log: List[OperationMetrics] = []
        self._last_snapshot_time = 0
        
        # Initialize directory structure
        self._initialize_stats_directory()

    def _initialize_stats_directory(self):
        """Initialize statistics directory structure"""
        # Create main stats directory
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.stats_dir / "daily").mkdir(exist_ok=True)
        (self.stats_dir / "snapshots").mkdir(exist_ok=True)
        (self.stats_dir / "performance").mkdir(exist_ok=True)

    def record_operation(
        self,
        operation: str,
        tier: MemoryTier,
        duration: float,
        block_count: int,
        token_count: int
    ):
        """Record a memory operation"""
        metrics = OperationMetrics(
            operation=operation,
            timestamp=time.time(),
            duration=duration,
            tier=tier,
            block_count=block_count,
            token_count=token_count
        )
        
        self._operation_log.append(metrics)
        self._check_and_save_metrics()

    def record_performance(
        self,
        operation_time: float,
        memory_usage: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Record performance metrics"""
        metrics = PerformanceMetrics(
            operation_time=operation_time,
            memory_usage=memory_usage,
            success=success,
            error=error
        )
        
        self._performance_log.append(metrics)
        if len(self._performance_log) > self.performance_log_size:
            self._performance_log.pop(0)

    def _check_and_save_metrics(self):
        """Check if it's time to save metrics and take a snapshot"""
        current_time = time.time()
        
        # Save daily metrics at midnight
        current_date = datetime.now().date()
        metrics_file = self.stats_dir / "daily" / f"{current_date}.json"
        
        if not metrics_file.exists():
            self._save_daily_metrics(metrics_file)

        # Take periodic snapshots
        if current_time - self._last_snapshot_time >= self.snapshot_interval:
            self._take_snapshot()
            self._last_snapshot_time = current_time

        # Clean up old metrics
        self._cleanup_old_metrics()

    def _save_daily_metrics(self, metrics_file: Path):
        """Save daily metrics to file"""
        daily_stats = self.get_daily_statistics()
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metrics_file, 'w') as f:
            json.dump(daily_stats, f, indent=2)

    def _take_snapshot(self):
        """Take a snapshot of current memory state"""
        snapshot = {
            'timestamp': time.time(),
            'memory_stats': self.file_manager.get_stats(),
            'performance_metrics': self._get_performance_summary(),
            'operation_metrics': self._get_operation_summary()
        }
        
        snapshot_file = (
            self.stats_dir / "snapshots" /
            f"snapshot_{int(time.time())}.json"
        )
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot, f, indent=2)

    def _cleanup_old_metrics(self):
        """Clean up metrics older than retention period"""
        cutoff_time = time.time() - (self.metrics_retention_days * 86400)
        
        # Clean up daily metrics
        daily_dir = self.stats_dir / "daily"
        if daily_dir.exists():
            for metrics_file in daily_dir.glob("*.json"):
                try:
                    file_date = datetime.strptime(
                        metrics_file.stem,
                        "%Y-%m-%d"
                    ).timestamp()
                    if file_date < cutoff_time:
                        metrics_file.unlink()
                except ValueError:
                    continue

        # Clean up snapshots
        snapshots_dir = self.stats_dir / "snapshots"
        if snapshots_dir.exists():
            for snapshot_file in snapshots_dir.glob("*.json"):
                try:
                    timestamp = int(snapshot_file.stem.split('_')[1])
                    if timestamp < cutoff_time:
                        snapshot_file.unlink()
                except (ValueError, IndexError):
                    continue

    def get_daily_statistics(self) -> Dict[str, Any]:
        """Get statistics for the current day"""
        stats = {
            'date': datetime.now().date().isoformat(),
            'operations': {
                'total_count': len(self._operation_log),
                'by_type': {},
                'by_tier': {tier.value: 0 for tier in MemoryTier}
            },
            'performance': {
                'average_operation_time': 0,
                'success_rate': 0,
                'error_count': 0
            },
            'memory_usage': {
                tier.value: {
                    'blocks': 0,
                    'tokens': 0
                }
                for tier in MemoryTier
            }
        }

        # Calculate operation statistics
        for op in self._operation_log:
            if op.operation not in stats['operations']['by_type']:
                stats['operations']['by_type'][op.operation] = 0
            stats['operations']['by_type'][op.operation] += 1
            stats['operations']['by_tier'][op.tier.value] += 1

        # Calculate performance statistics
        if self._performance_log:
            total_time = sum(p.operation_time for p in self._performance_log)
            success_count = sum(1 for p in self._performance_log if p.success)
            error_count = sum(1 for p in self._performance_log if not p.success)

            stats['performance'].update({
                'average_operation_time': total_time / len(self._performance_log),
                'success_rate': success_count / len(self._performance_log),
                'error_count': error_count
            })

        # Get current memory usage
        memory_stats = self.file_manager.get_stats()
        for tier in MemoryTier:
            tier_stats = memory_stats['tiers'][tier.value]
            stats['memory_usage'][tier.value].update({
                'blocks': tier_stats['blocks'],
                'tokens': tier_stats['tokens']
            })

        return stats

    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        if not self._performance_log:
            return {}

        return {
            'average_operation_time': sum(
                p.operation_time for p in self._performance_log
            ) / len(self._performance_log),
            'success_rate': sum(
                1 for p in self._performance_log if p.success
            ) / len(self._performance_log),
            'error_count': sum(1 for p in self._performance_log if not p.success),
            'average_memory_usage': sum(
                p.memory_usage for p in self._performance_log
            ) / len(self._performance_log)
        }

    def _get_operation_summary(self) -> Dict[str, Any]:
        """Get summary of operation metrics"""
        if not self._operation_log:
            return {}

        summary = {
            'operation_counts': {},
            'average_durations': {},
            'tier_usage': {tier.value: 0 for tier in MemoryTier}
        }

        for op in self._operation_log:
            # Count operations
            if op.operation not in summary['operation_counts']:
                summary['operation_counts'][op.operation] = 0
                summary['average_durations'][op.operation] = 0
            
            summary['operation_counts'][op.operation] += 1
            summary['average_durations'][op.operation] += op.duration
            summary['tier_usage'][op.tier.value] += 1

        # Calculate averages
        for op in summary['average_durations']:
            summary['average_durations'][op] /= summary['operation_counts'][op]

        return summary

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive performance report"""
        return {
            'timestamp': time.time(),
            'daily_stats': self.get_daily_statistics(),
            'performance_summary': self._get_performance_summary(),
            'operation_summary': self._get_operation_summary(),
            'memory_state': self.file_manager.get_stats()
        }

    def clear_logs(self):
        """Clear performance and operation logs"""
        self._performance_log.clear()
        self._operation_log.clear()
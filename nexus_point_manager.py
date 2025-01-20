from typing import List, Dict, Any, Optional, Set
import time
from file_memory_manager import FileMemoryManager, MemoryBlock, MemoryTier, SignificanceType

class NexusPointManager:
    def __init__(
        self,
        file_manager: FileMemoryManager,
        max_nexus_points: int = 100,
        nexus_threshold: float = 0.5,
        access_window: float = 3600,  # 1 hour
        min_access_count: int = 5,
        max_access_history: int = 1000  # For test compatibility
    ):
        self.file_manager = file_manager
        self.max_nexus_points = max_nexus_points
        self.nexus_threshold = nexus_threshold
        self.access_window = access_window
        self.min_access_count = min_access_count
        self.max_access_history = max_access_history
        
        # Access tracking
        self._access_history: Dict[str, List[float]] = {}
        self._importance_scores: Dict[str, float] = {}

    def register_access(self, block_id: str):
        """Register an access to a memory block"""
        current_time = time.time()
        
        # Initialize access history if needed
        if block_id not in self._access_history:
            self._access_history[block_id] = []
            
        # Add access timestamp
        self._access_history[block_id].append(current_time)
        
        # Limit access history size
        if len(self._access_history[block_id]) > self.max_access_history:
            self._access_history[block_id] = self._access_history[block_id][-self.max_access_history:]
        
        # Clean up old access records
        self._clean_access_history(block_id)
        
        # Update importance score
        self._update_importance_score(block_id)
        
        # Check if block should become a nexus point
        self._check_nexus_status(block_id)

    def reinforce_nexus_point(self, block_id: str):
        """Reinforce a nexus point by increasing its importance"""
        # Find block in any tier
        block = None
        for tier in MemoryTier:
            blocks = self.file_manager.get_memory_blocks(tier)
            for b in blocks:
                if b.id == block_id:
                    block = b
                    break
            if block:
                break
                
        if not block or not block.is_nexus:
            return
            
        # Increase importance score
        current_score = self._importance_scores.get(block_id, 0.0)
        new_score = min(1.0, current_score + 0.1)
        self._importance_scores[block_id] = new_score
        
        # Update metadata with new score and protection level
        block.nexus_metadata = {
            "importance_score": new_score,
            "protection_level": self._get_protection_level(block.significance_type, new_score),
            "last_update": time.time()
        }
        self.file_manager.update_memory_block(block)

    def _clean_access_history(self, block_id: str):
        """Clean up old access records outside the window"""
        if block_id not in self._access_history:
            return
            
        current_time = time.time()
        cutoff_time = current_time - self.access_window
        
        self._access_history[block_id] = [
            ts for ts in self._access_history[block_id]
            if ts > cutoff_time
        ]

    def _update_importance_score(self, block_id: str):
        """Update importance score for a block"""
        if block_id not in self._access_history:
            self._importance_scores[block_id] = 0.0
            return
            
        # Get block details
        block = None
        for tier in MemoryTier:
            blocks = self.file_manager.get_memory_blocks(tier)
            for b in blocks:
                if b.id == block_id:
                    block = b
                    break
            if block:
                break
                
        if not block:
            return
            
        # Calculate base score from access frequency
        access_count = len(self._access_history[block_id])
        frequency_score = min(1.0, access_count / self.min_access_count)
        
        # Add recency factor
        if access_count > 0:
            latest_access = max(self._access_history[block_id])
            age = time.time() - latest_access
            recency_score = 1.0 / (1.0 + age/3600)  # Decay over hours
        else:
            recency_score = 0.0
            
        # Add reference factor
        ref_count = len(block.references.get("related_blocks", []))
        reference_score = min(1.0, ref_count / 10)  # Cap at 10 references
        
        # Add significance type factor
        significance_bonus = {
            SignificanceType.SYSTEM: 0.3,
            SignificanceType.USER: 0.2,
            SignificanceType.LLM: 0.1,
            SignificanceType.DERIVED: 0.0
        }[block.significance_type]
        
        # Combine scores
        importance = (
            0.4 * frequency_score +
            0.3 * recency_score +
            0.2 * reference_score +
            0.1 * significance_bonus
        )
        
        self._importance_scores[block_id] = importance

    def _get_protection_level(self, significance_type: SignificanceType, importance_score: float) -> str:
        """Get protection level based on significance type and importance"""
        if significance_type in [SignificanceType.SYSTEM, SignificanceType.USER]:
            return "high"
        return "medium"

    def _check_nexus_status(self, block_id: str):
        """Check if a block should become a nexus point"""
        if block_id not in self._importance_scores:
            return
            
        importance = self._importance_scores[block_id]
        
        # Get current nexus points
        nexus_points = self.get_nexus_points()
        
        # If block is already a nexus point, update metadata
        if any(np.id == block_id for np in nexus_points):
            self._update_nexus_metadata(block_id, importance)
            return
            
        # Check if block should become a nexus point
        if importance >= self.nexus_threshold:
            # Check if we're at the limit
            if len(nexus_points) >= self.max_nexus_points:
                # Find lowest importance nexus point
                lowest_np = min(
                    nexus_points,
                    key=lambda np: self._importance_scores.get(np.id, 0.0)
                )
                
                # Only replace if new block is more important
                if importance > self._importance_scores.get(lowest_np.id, 0.0):
                    # Remove nexus status from lowest
                    self._remove_nexus_status(lowest_np.id)
                    # Add new nexus point
                    self._add_nexus_status(block_id)
            else:
                # Add new nexus point
                self._add_nexus_status(block_id)

    def _update_nexus_metadata(self, block_id: str, importance: float):
        """Update nexus point metadata"""
        # Find block in any tier
        for tier in MemoryTier:
            blocks = self.file_manager.get_memory_blocks(tier)
            for block in blocks:
                if block.id == block_id:
                    # Update metadata
                    block.nexus_metadata = {
                        "importance_score": importance,
                        "protection_level": self._get_protection_level(block.significance_type, importance),
                        "last_update": time.time()
                    }
                    self.file_manager.update_memory_block(block)
                    return

    def _add_nexus_status(self, block_id: str):
        """Add nexus point status to a block"""
        # Find block in any tier
        for tier in MemoryTier:
            blocks = self.file_manager.get_memory_blocks(tier)
            for block in blocks:
                if block.id == block_id:
                    # Update block
                    block.is_nexus = True
                    importance = self._importance_scores.get(block_id, 0.5)
                    block.nexus_metadata = {
                        "importance_score": importance,
                        "protection_level": self._get_protection_level(block.significance_type, importance),
                        "last_update": time.time()
                    }
                    self.file_manager.update_memory_block(block)
                    return

    def _remove_nexus_status(self, block_id: str):
        """Remove nexus point status from a block"""
        # Find block in any tier
        for tier in MemoryTier:
            blocks = self.file_manager.get_memory_blocks(tier)
            for block in blocks:
                if block.id == block_id:
                    # Update block
                    block.is_nexus = False
                    block.nexus_metadata = {}
                    self.file_manager.update_memory_block(block)
                    return

    def get_nexus_points(self) -> List[MemoryBlock]:
        """Get all current nexus points"""
        nexus_points = []
        for tier in MemoryTier:
            blocks = self.file_manager.get_memory_blocks(tier)
            nexus_points.extend(block for block in blocks if block.is_nexus)
        return nexus_points

    def get_nexus_stats(self) -> Dict[str, Any]:
        """Get statistics about nexus points"""
        nexus_points = self.get_nexus_points()
        
        # Count protection levels
        protection_counts = {"high": 0, "medium": 0, "low": 0}
        total_importance = 0.0
        
        for np in nexus_points:
            level = np.nexus_metadata.get("protection_level", "medium")
            protection_counts[level] += 1
            total_importance += np.nexus_metadata.get("importance_score", 0.0)
        
        return {
            "total_count": len(nexus_points),
            "protection_levels": protection_counts,
            "average_importance": total_importance / max(1, len(nexus_points))
        }

    def check_nexus_points(self):
        """Periodic maintenance of nexus points"""
        # Update all importance scores
        for block_id in list(self._access_history.keys()):
            self._clean_access_history(block_id)
            self._update_importance_score(block_id)
            
        # Check all blocks for nexus status
        for block_id in list(self._importance_scores.keys()):
            self._check_nexus_status(block_id)
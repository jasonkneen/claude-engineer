"""Memory-related data models."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class Memory:
    """Represents a single memory entry."""
    content: str
    content_hash: str
    tags: List[str] = field(default_factory=list)
    memory_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary format for storage."""
        return {
            "content": self.content,
            "content_hash": self.content_hash,
            "tags_str": ",".join(self.tags) if self.tags else "",
            "type": self.memory_type,
            "timestamp": self.timestamp.timestamp(),
            **self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> 'Memory':
        """Create a Memory instance from dictionary data."""
        tags = data.get("tags_str", "").split(",") if data.get("tags_str") else []
        return cls(
            content=data["content"],
            content_hash=data["content_hash"],
            tags=[tag for tag in tags if tag],  # Filter out empty tags
            memory_type=data.get("type"),
            timestamp=datetime.fromtimestamp(float(data["timestamp"])) if "timestamp" in data else datetime.now(),
            metadata={k: v for k, v in data.items() if k not in 
                     ["content", "content_hash", "tags_str", "type", "timestamp"]},
            embedding=embedding
        )

@dataclass
class MemoryQueryResult:
    """Represents a memory query result with relevance score and debug information."""
    memory: Memory
    relevance_score: float
    debug_info: Dict[str, Any] = field(default_factory=dict)
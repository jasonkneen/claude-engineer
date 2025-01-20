from typing import List, Dict, Any, Optional, Set
import json
import time
from pathlib import Path
from enum import Enum

class SignificanceType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    LLM = "llm"
    DERIVED = "derived"

class MemoryTier(str, Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    STALE = "stale"

class MemoryBlock:
    def __init__(
        self,
        id: str,
        content: str,
        tokens: int,
        timestamp: float,
        significance_type: SignificanceType,
        tier: MemoryTier,
        is_nexus: bool = False,
        access_count: int = 0,
        w3w_reference: Optional[List[str]] = None,
        references: Optional[Dict[str, List[str]]] = None,
        nexus_metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.content = content
        self.tokens = tokens
        self.timestamp = timestamp
        self.significance_type = significance_type
        self.tier = tier
        self.is_nexus = is_nexus
        self.access_count = access_count
        self.w3w_reference = w3w_reference or []
        self.references = references or {"keywords": [], "related_blocks": []}
        self.nexus_metadata = nexus_metadata or {}

class FileMemoryManager:
    def __init__(self, base_dir: str):
        """Initialize the memory manager with a unified JSON storage"""
        self.base_dir = Path(base_dir)
        self.memory_dir = self.base_dir  # For statistics compatibility
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tier directories and files
        for tier in MemoryTier:
            tier_dir = self.base_dir / tier.value
            tier_dir.mkdir(exist_ok=True)
            tier_file = self.base_dir / f"{tier.value.replace('_', '-')}.memory"
            if not tier_file.exists():
                tier_file.write_text("{}")
                
        # Initialize stats file
        stats_file = self.base_dir / "stats.json"
        if not stats_file.exists():
            stats_file.write_text("{}")
            
        # Initialize unified storage
        self.data_file = self.base_dir / "memory_store.json"
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize or load the JSON storage file"""
        if not self.data_file.exists():
            initial_data = {
                "blocks": {},
                "metadata": {
                    "last_update": time.time(),
                    "version": "1.0"
                }
            }
            self._save_data(initial_data)
        self._ensure_data_integrity()

    def _ensure_data_integrity(self):
        """Ensure the data file exists and has valid structure"""
        try:
            data = self._load_data()
            if not isinstance(data, dict) or "blocks" not in data:
                self._initialize_storage()
        except (json.JSONDecodeError, OSError):
            self._initialize_storage()

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"blocks": {}, "metadata": {"last_update": time.time(), "version": "1.0"}}

    def _save_data(self, data: Dict[str, Any]):
        """Save data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _block_to_dict(self, block: MemoryBlock) -> Dict[str, Any]:
        """Convert MemoryBlock to dictionary for storage"""
        return {
            "id": block.id,
            "content": block.content,
            "tokens": block.tokens,
            "timestamp": block.timestamp,
            "significance_type": block.significance_type,
            "status": {
                "working": block.tier == MemoryTier.WORKING,
                "short_term": block.tier == MemoryTier.SHORT_TERM,
                "long_term": block.tier == MemoryTier.LONG_TERM,
                "stale": block.tier == MemoryTier.STALE
            },
            "is_nexus": block.is_nexus,
            "access_count": block.access_count,
            "w3w_reference": block.w3w_reference,
            "references": block.references,
            "nexus_metadata": block.nexus_metadata
        }

    def _dict_to_block(self, data: Dict[str, Any], requested_tier: Optional[MemoryTier] = None) -> MemoryBlock:
        """Convert dictionary to MemoryBlock"""
        # Determine current tier based on status flags
        tier = MemoryTier.WORKING
        if data["status"]["stale"]:
            tier = MemoryTier.STALE
        elif data["status"]["long_term"]:
            tier = MemoryTier.LONG_TERM
        elif data["status"]["short_term"]:
            tier = MemoryTier.SHORT_TERM

        # If block is in a lower tier than requested, return summary version
        content = data["content"]
        if requested_tier and tier != MemoryTier.WORKING:
            if "summary" in data:
                content = data["summary"]
            else:
                content = f"Summary: {' • '.join(data['w3w_reference'])}"

        return MemoryBlock(
            id=data["id"],
            content=content,
            tokens=data["tokens"],
            timestamp=data["timestamp"],
            significance_type=data["significance_type"],
            tier=tier,
            is_nexus=data["is_nexus"],
            access_count=data["access_count"],
            w3w_reference=data["w3w_reference"],
            references=data["references"],
            nexus_metadata=data.get("nexus_metadata", {})
        )

    def add_memory_block(self, block: MemoryBlock):
        """Add a new memory block"""
        data = self._load_data()
        data["blocks"][block.id] = self._block_to_dict(block)
        data["metadata"]["last_update"] = time.time()
        self._save_data(data)

    def get_memory_blocks(self, tier: MemoryTier) -> List[MemoryBlock]:
        """Get memory blocks for a specific tier"""
        data = self._load_data()
        blocks = []
        
        for block_data in data["blocks"].values():
            # Check if block belongs to requested tier
            if block_data["status"][tier.value]:
                blocks.append(self._dict_to_block(block_data, tier))
                
        return blocks

    def update_memory_block(self, block: MemoryBlock):
        """Update an existing memory block"""
        data = self._load_data()
        if block.id not in data["blocks"]:
            raise KeyError(f"Block {block.id} not found")
        data["blocks"][block.id] = self._block_to_dict(block)
        data["metadata"]["last_update"] = time.time()
        self._save_data(data)

    def move_block_to_tier(self, block_id: str, from_tier: MemoryTier, to_tier: MemoryTier):
        """Move a block between tiers by updating its status flags"""
        data = self._load_data()
        if block_id not in data["blocks"]:
            raise KeyError(f"Block {block_id} not found")
            
        # Update status flags
        data["blocks"][block_id]["status"][from_tier.value] = False
        data["blocks"][block_id]["status"][to_tier.value] = True
        
        # If moving to a lower tier, generate summary if needed
        if to_tier in [MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM, MemoryTier.STALE]:
            if "summary" not in data["blocks"][block_id]:
                w3w = data["blocks"][block_id]["w3w_reference"]
                data["blocks"][block_id]["summary"] = f"Summary: {' • '.join(w3w)}"
                
        data["metadata"]["last_update"] = time.time()
        self._save_data(data)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        data = self._load_data()
        stats = {
            "total_blocks": len(data["blocks"]),
            "total_tokens": sum(block["tokens"] for block in data["blocks"].values()),
            "tiers": {
                "working": {"blocks": 0, "tokens": 0},
                "short_term": {"blocks": 0, "tokens": 0},
                "long_term": {"blocks": 0, "tokens": 0},
                "stale": {"blocks": 0, "tokens": 0}
            }
        }
        
        for block in data["blocks"].values():
            for tier in ["working", "short_term", "long_term", "stale"]:
                if block["status"][tier]:
                    stats["tiers"][tier]["blocks"] += 1
                    stats["tiers"][tier]["tokens"] += block["tokens"]
                    
        return stats
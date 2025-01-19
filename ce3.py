import asyncio
import json
import os
from typing import Optional, List, Dict, Any
from memory_manager import MemoryManager, MemoryBlock, SignificanceType, MemoryLevel
from visualization.memory_bridge import start_memory_bridge


class CE3:
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.memory_bridge = None
        self.last_recall_time = 0
        self.generation_count = 0
        self.promotion_count = 0
        self.demotion_count = 0
        self.merge_count = 0
        self.retrieval_count = 0
        self.setup_memory_visualization()

    def setup_memory_visualization(self):
        """Initialize the memory visualization bridge"""
        self.memory_bridge = start_memory_bridge(self)

    def get_working_memory(self) -> List[MemoryBlock]:
        return self.memory_manager.working_memory

    def get_short_term_memory(self) -> List[MemoryBlock]:
        return self.memory_manager.short_term_memory

    def get_long_term_memory(self) -> List[MemoryBlock]:
        return self.memory_manager.long_term_memory

    def get_nexus_points(self) -> Dict:
        return self.memory_manager.nexus_points

    async def process_message(self, message: str) -> str:
        """Process a message using the memory system"""
        try:
            # Add message to working memory
            start_time = asyncio.get_event_loop().time()
            block_id = self.memory_manager.add_memory(
                {"content": message, "type": "user_message"},
                significance=SignificanceType.USER,
            )
            self.last_recall_time = (
                asyncio.get_event_loop().time() - start_time
            ) * 1000  # ms

            # Log the memory event through the bridge
            if self.memory_bridge:
                await self.memory_bridge.send_log(
                    message=f"Added message to working memory (ID: {block_id})",
                    log_type="info",
                    w3w=self.memory_manager.working_memory[-1].w3w_tokens[0],
                )

            # Update stats
            stats = self.memory_manager.get_memory_stats()
            self.promotion_count = stats["operations"]["promotions"]
            self.demotion_count = stats["operations"]["demotions"]
            self.merge_count = stats["operations"]["merges"]
            self.retrieval_count = stats["operations"]["retrievals"]

            # Check if memory management was triggered
            if (
                stats["pools"]["working"]["utilization"] > 0.9
                or stats["pools"]["short_term"]["utilization"] > 0.9
            ):
                self.generation_count += 1
                if self.memory_bridge:
                    await self.memory_bridge.send_log(
                        message=f"Memory compression triggered (Generation {self.generation_count})",
                        log_type="warning",
                    )

            return "Message processed"

        except Exception as e:
            if self.memory_bridge:
                await self.memory_bridge.send_log(
                    message=f"Error processing message: {str(e)}", log_type="error"
                )
            raise

    async def get_context(
        self, query: str, max_blocks: int = 5
    ) -> List[Dict[str, Any]]:
        """Get relevant context with timing"""
        start_time = asyncio.get_event_loop().time()
        context = self.memory_manager.get_relevant_context(query, max_blocks)
        self.last_recall_time = (
            asyncio.get_event_loop().time() - start_time
        ) * 1000  # ms

        if self.memory_bridge:
            await self.memory_bridge.send_log(
                message=f"Retrieved {len(context)} relevant blocks", log_type="info"
            )

        return context

    async def run(self):
        """Start the CE3 system with memory visualization"""
        try:
            print("Starting CE3 with memory visualization...")

            # Your main processing loop here
            while True:
                await asyncio.sleep(0.1)  # Prevent CPU hogging

                # Process any pending memory operations
                stats = self.memory_manager.get_memory_stats()
                if self.memory_bridge:
                    # Memory bridge will automatically send updates
                    pass

        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error in CE3: {e}")
            if self.memory_bridge:
                await self.memory_bridge.send_log(
                    message=f"System error: {str(e)}", log_type="error"
                )
            raise
        finally:
            # Cleanup
            if self.memory_bridge and hasattr(self.memory_bridge, "websocket"):
                await self.memory_bridge.websocket.close()


if __name__ == "__main__":
    ce3 = CE3()
    asyncio.run(ce3.run())

import asyncio
import logging
from memory_manager import MemoryManager
from visualization.memory_bridge import start_memory_bridge

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def simulate_memory_operations(memory_manager):
    """Simulate memory operations for testing"""
    while True:
        try:
            # Add some test memory blocks
            memory_manager.add_memory_block("Test memory content 1", "user")
            await asyncio.sleep(2)
            memory_manager.add_memory_block("Test memory content 2", "llm")
            await asyncio.sleep(2)
            memory_manager.add_memory_block("Test memory content 3", "system")
            await asyncio.sleep(2)

            # Perform some operations
            memory_manager.promote_block(0)  # Promote first block
            await asyncio.sleep(1)
            memory_manager.merge_blocks([1, 2])  # Merge second and third blocks
            await asyncio.sleep(1)
            memory_manager.retrieve_blocks(["test"])  # Retrieve blocks
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in simulation: {e}")
            await asyncio.sleep(5)


async def main():
    # Initialize the memory manager with some configuration
    memory_manager = MemoryManager(
        working_memory_limit=8192, short_term_memory_limit=128000
    )

    # Start the memory bridge
    bridge = start_memory_bridge(memory_manager)

    # Start the simulation in the background
    simulation_task = asyncio.create_task(simulate_memory_operations(memory_manager))

    try:
        # Keep the script running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        simulation_task.cancel()
        bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())

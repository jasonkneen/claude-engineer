import asyncio
import logging
import numpy as np
from memory_manager import MemoryManager, SignificanceType
from visualization.memory_bridge import start_memory_bridge
from visualization.memory_viz import MemoryVisualizer, VisualizationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def simulate_memory_operations(memory_manager, visualizer):
    """Simulate realistic memory operations with meaningful content"""
    try:
        # Conversation about Python programming
        memory_manager.add_memory_block(
            "User: Can you help me understand Python decorators?", SignificanceType.USER
        )
        await asyncio.sleep(2)
        await update_visualization(memory_manager, visualizer)

        memory_manager.add_memory_block(
            """System response: Decorators are a way to modify or enhance functions in Python. 
            Think of them as wrappers that add functionality to existing functions.
            Here's a simple example:
            
            @timer
            def my_function():
                # Function code here
                pass
            
            The @timer decorator would measure how long the function takes to run.""",
            SignificanceType.LLM,
        )
        await asyncio.sleep(2)
        await update_visualization(memory_manager, visualizer)

        # User follow-up question
        memory_manager.add_memory_block(
            "User: Can you show me how to write a decorator?", SignificanceType.USER
        )
        await asyncio.sleep(2)

        # Conversation about machine learning
        memory_manager.add_memory_block(
            "User: What's the difference between supervised and unsupervised learning?",
            SignificanceType.USER,
        )
        await asyncio.sleep(2)

        memory_manager.add_memory_block(
            """System response: The main difference is in how the models learn:
            
            Supervised Learning:
            - Uses labeled training data
            - Has defined correct answers
            - Examples: classification, regression
            
            Unsupervised Learning:
            - Uses unlabeled data
            - Finds patterns automatically
            - Examples: clustering, dimensionality reduction""",
            SignificanceType.LLM,
        )
        await asyncio.sleep(2)

        # System metadata updates
        memory_manager.add_memory_block(
            "Session context: User shows interest in Python programming and ML concepts",
            SignificanceType.SYSTEM,
        )
        await asyncio.sleep(2)
        await update_visualization(memory_manager, visualizer)

        # Retrieve relevant context
        memory_manager.get_relevant_context("Python decorator")
        await asyncio.sleep(1)

        # Retrieve ML-related context
        memory_manager.get_relevant_context("machine learning supervised")
        await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        await asyncio.sleep(5)


async def update_visualization(memory_manager, visualizer):
    """Update the visualization with current memory state"""
    try:
        # Get current memory stats
        stats = memory_manager.get_memory_stats()

        # Extract memory blocks and their embeddings
        blocks = memory_manager.get_working_memory()
        embeddings = [
            block.embedding for block in blocks if block.embedding is not None
        ]

        if embeddings:
            # Convert to numpy array for visualization
            embedding_array = np.array(embeddings)

            # Update visualization
            await visualizer.update_memory_state(
                embedding_array, [block.significance_type for block in blocks], stats
            )

        # Allow time for visualization to update
        await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Error updating visualization: {e}")


async def main():
    try:
        # Initialize the memory manager with some configuration
        memory_manager = MemoryManager(
            working_memory_limit=8192,
            archival_memory_limit=128000,
            archive_threshold=6000,
        )

        # Initialize visualization
        viz_config = VisualizationConfig(
            width=1024, height=768, point_size=5.0, animation_speed=1.0
        )
        visualizer = MemoryVisualizer(viz_config)

        # Start the memory bridge
        bridge = await start_memory_bridge(memory_manager)

        # Start visualization updates
        vis_update_task = asyncio.create_task(
            update_visualization(memory_manager, visualizer)
        )

        # Start the simulation in the background
        simulation_task = asyncio.create_task(
            simulate_memory_operations(memory_manager, visualizer)
        )

        try:
            # Keep the script running
            while True:
                await asyncio.sleep(1)
                # Update visualization periodically
                await update_visualization(memory_manager, visualizer)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            simulation_task.cancel()
            vis_update_task.cancel()
            bridge.stop()
            visualizer.close()
    except Exception as e:
        logger.error(f"Error in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())

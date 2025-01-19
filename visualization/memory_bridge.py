import asyncio
import websockets
import json
import time
import logging
import os
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    pools: Dict[str, Dict[str, Any]]
    operations: Dict[str, int]
    nexus_points: Dict[str, Any]
    generations: int
    total_tokens: int


class MemoryBridge:
    def __init__(self, memory_manager, base_url: str = "ws://localhost"):
        self.memory_manager = memory_manager
        self.base_url = base_url
        self.websocket = None
        self.connected = False
        self.reconnect_delay = 1  # Start with 1 second delay
        self.max_reconnect_delay = 30  # Maximum delay between retries
        self.should_run = True
        self.stats = MemoryStats(
            pools={
                "working": {"size": 0, "count": 0, "limit": 8192, "utilization": 0},
                "short_term": {
                    "size": 0,
                    "count": 0,
                    "limit": 128000,
                    "utilization": 0,
                },
                "long_term": {"size": 0, "count": 0},
            },
            operations={
                "promotions": 0,
                "demotions": 0,
                "merges": 0,
                "retrievals": 0,
                "avg_recall_time": 0,
                "compression_count": 0,
            },
            nexus_points={"count": 0, "types": {"user": 0, "llm": 0, "system": 0}},
            generations=0,
            total_tokens=0,
        )
        self.recall_times: List[float] = []
        self.last_compression: Optional[float] = None

    async def get_websocket_port(self) -> Optional[int]:
        """Get the WebSocket port from the .ws-port file"""
        try:
            port_file = os.path.join(
                os.getcwd(), "visualization/memory-dashboard/.ws-port"
            )
            if os.path.exists(port_file):
                with open(port_file, "r") as f:
                    return int(f.read().strip())
        except Exception as e:
            logger.error(f"Error reading WebSocket port file: {e}")
        return None

    async def connect(self) -> bool:
        """Connect to the WebSocket server with retry logic"""
        while self.should_run:
            try:
                if self.websocket:
                    await self.websocket.close()

                # Get the current WebSocket port
                port = await self.get_websocket_port()
                if not port:
                    logger.error("Could not determine WebSocket port")
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                websocket_url = f"{self.base_url}:{port}"
                logger.info(f"Connecting to WebSocket server at {websocket_url}")

                self.websocket = await websockets.connect(
                    websocket_url,
                    ping_interval=20,
                    ping_timeout=60,
                    close_timeout=10,
                    max_size=None,
                )
                self.connected = True
                self.reconnect_delay = 1  # Reset delay on successful connection
                logger.info("Successfully connected to WebSocket server")
                return True

            except Exception as e:
                logger.error(f"Failed to connect to WebSocket server: {e}")
                self.connected = False
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, self.max_reconnect_delay
                )
                continue

        return False

    async def send_stats(self):
        """Send current memory stats to the WebSocket server"""
        if not self.connected or not self.websocket:
            return

        try:
            message = {"type": "stats", "payload": asdict(self.stats)}
            await self.websocket.send(json.dumps(message))
            logger.debug("Sent stats update")
        except ConnectionClosed:
            logger.warning("WebSocket connection closed while sending stats")
            self.connected = False
        except Exception as e:
            logger.error(f"Error sending stats: {e}")
            self.connected = False

    async def send_log(
        self, message: str, log_type: str = "info", w3w: Optional[str] = None
    ):
        """Send a log message to the WebSocket server"""
        if not self.connected or not self.websocket:
            return

        try:
            log_message = {
                "type": "log",
                "payload": {
                    "id": str(int(time.time() * 1000)),
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": log_type,
                    "message": message,
                    "w3w": w3w,
                },
            }
            await self.websocket.send(json.dumps(log_message))
            logger.debug(f"Sent log message: {message}")
        except ConnectionClosed:
            logger.warning("WebSocket connection closed while sending log")
            self.connected = False
        except Exception as e:
            logger.error(f"Error sending log: {e}")
            self.connected = False

    def update_memory_stats(self):
        """Update memory stats from ce3.py's memory manager"""
        try:
            # Update working memory stats
            working_blocks = self.memory_manager.get_working_memory()
            self.stats.pools["working"]["count"] = len(working_blocks)
            self.stats.pools["working"]["size"] = sum(
                block.tokens for block in working_blocks
            )
            self.stats.pools["working"]["utilization"] = (
                self.stats.pools["working"]["size"]
                / self.stats.pools["working"]["limit"]
            )

            # Update short-term memory stats
            short_term_blocks = self.memory_manager.get_short_term_memory()
            self.stats.pools["short_term"]["count"] = len(short_term_blocks)
            self.stats.pools["short_term"]["size"] = sum(
                block.tokens for block in short_term_blocks
            )
            self.stats.pools["short_term"]["utilization"] = (
                self.stats.pools["short_term"]["size"]
                / self.stats.pools["short_term"]["limit"]
            )

            # Update long-term memory stats
            long_term_blocks = self.memory_manager.get_long_term_memory()
            self.stats.pools["long_term"]["count"] = len(long_term_blocks)
            self.stats.pools["long_term"]["size"] = sum(
                block.tokens for block in long_term_blocks
            )

            # Update operations
            self.stats.operations["promotions"] = self.memory_manager.promotion_count
            self.stats.operations["demotions"] = self.memory_manager.demotion_count
            self.stats.operations["merges"] = self.memory_manager.merge_count
            self.stats.operations["retrievals"] = self.memory_manager.retrieval_count

            # Update recall time
            if self.memory_manager.last_recall_time:
                self.recall_times.append(self.memory_manager.last_recall_time)
                if len(self.recall_times) > 100:
                    self.recall_times.pop(0)
                self.stats.operations["avg_recall_time"] = sum(self.recall_times) / len(
                    self.recall_times
                )

            # Update nexus points
            nexus_points = self.memory_manager.get_nexus_points()
            self.stats.nexus_points["count"] = len(nexus_points)
            self.stats.nexus_points["types"]["user"] = sum(
                1 for np in nexus_points.values() if np.significance_type == "user"
            )
            self.stats.nexus_points["types"]["llm"] = sum(
                1 for np in nexus_points.values() if np.significance_type == "llm"
            )
            self.stats.nexus_points["types"]["system"] = sum(
                1 for np in nexus_points.values() if np.significance_type == "system"
            )

            # Update total stats
            self.stats.generations = self.memory_manager.generation_count
            self.stats.total_tokens = (
                self.stats.pools["working"]["size"]
                + self.stats.pools["short_term"]["size"]
                + self.stats.pools["long_term"]["size"]
            )

            logger.debug("Updated memory stats")
        except Exception as e:
            logger.error(f"Error updating memory stats: {e}")

    async def run(self):
        """Main loop to monitor memory and send updates"""
        logger.info("Starting memory bridge...")

        while self.should_run:
            if not self.connected:
                connected = await self.connect()
                if not connected:
                    continue

            try:
                self.update_memory_stats()
                await self.send_stats()
                await asyncio.sleep(1)  # Update frequency
            except ConnectionClosed:
                logger.warning(
                    "WebSocket connection closed, attempting to reconnect..."
                )
                self.connected = False
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"Error in memory bridge: {e}")
                self.connected = False
                await asyncio.sleep(self.reconnect_delay)

    def stop(self):
        """Stop the memory bridge"""
        self.should_run = False
        logger.info("Memory bridge stopped")


async def verify_connection(websocket, timeout=10):
    """Verify WebSocket connection is working with ping/pong"""
    try:
        pong_waiter = await websocket.ping()
        await asyncio.wait_for(pong_waiter, timeout=timeout)
        return True
    except Exception as e:
        logger.error(f"Connection verification failed: {e}")
        return False

async def start_memory_bridge(memory_manager, timeout=30, max_retries=5):
    """Start and initialize the memory bridge with connection verification
    
    Args:
        memory_manager: The memory manager instance
        timeout: Maximum time to wait for initialization in seconds
        max_retries: Maximum number of connection attempts
        
    Returns:
        Initialized MemoryBridge instance or raises exception on failure
    """
    bridge = MemoryBridge(memory_manager)
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Attempt connection with timeout
            connect_task = bridge.connect()
            connected = await asyncio.wait_for(connect_task, timeout=timeout/max_retries)
            
            if not connected:
                raise ConnectionError("Failed to establish WebSocket connection")
                
            # Verify connection is working
            if not await verify_connection(bridge.websocket):
                raise ConnectionError("Connection verification failed")
                
            # Start the bridge running task
            loop = asyncio.get_event_loop()
            run_task = loop.create_task(bridge.run())
            
            def cleanup_bridge(task):
                if bridge.connected:
                    loop.create_task(bridge.websocket.close())
                bridge.stop()
                
            run_task.add_done_callback(cleanup_bridge)
            
            logger.info("Memory bridge successfully initialized and started")
            return bridge
            
        except asyncio.TimeoutError:
            retry_count += 1
            logger.warning(f"Connection attempt {retry_count}/{max_retries} timed out")
            continue
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Failed to initialize bridge (attempt {retry_count}/{max_retries}): {e}")
            await asyncio.sleep(1)
            continue
            
    raise RuntimeError(f"Failed to start memory bridge after {max_retries} attempts")

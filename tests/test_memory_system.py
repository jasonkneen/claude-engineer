import pytest
from unittest.mock import Mock, patch
from memory_manager import MemoryManager, SignificanceType
from tools.w3w_tokenizer import W3WTokenizer
from memory_server_client import MemoryServerClient
from config import Config
import websockets
import json
import asyncio

@pytest.fixture
def memory_manager():
    config = Config()
    config.token_limit = 200000
    config.archival_threshold = 180000
    return MemoryManager(config)

@pytest.fixture
def memory_client():
    return MemoryServerClient(host="localhost", port=8000)

@pytest.fixture
def w3w_tokenizer():
    return W3WTokenizer()

@pytest.fixture
async def mock_websocket_server():
    connected = set()
    async def handler(websocket):
        connected.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                # Broadcast to all clients
                for client in connected:
                    await client.send(json.dumps({
                        "type": "stats_update",
                        "data": data
                    }))
        finally:
            connected.remove(websocket)
    
    server = await websockets.serve(handler, "localhost", 8000)
    yield server
    server.close()

class TestMemoryArchival:
    @pytest.mark.asyncio
    async def test_token_limit_triggers_archival(self, memory_manager, memory_client):
        # Fill memory to just below threshold
        for i in range(1000):
            memory_manager.add_memory_block(
                content=f"Test memory {i}",
                significance_type=SignificanceType.SYSTEM
            )
        
        # Add one more block that pushes it over the limit
        memory_manager.add_memory_block(
            content="Trigger block",
            significance_type=SignificanceType.USER
        )
        
        # Verify archival occurred
        assert memory_manager.current_token_count < memory_manager.token_limit
        assert len(memory_client.archived_memories) > 0

    @pytest.mark.asyncio
    async def test_archival_converts_to_w3w(self, memory_manager, w3w_tokenizer):
        test_text = "This is a test memory that should be converted to W3W format"
        memory_manager.add_memory_block(
            content=test_text,
            significance_type=SignificanceType.USER
        )
        
        # Get archived memory
        archived = memory_manager.get_archived_memories()[0]
        
        # Verify W3W conversion
        assert "w3w_tokens" in archived
        assert len(archived["w3w_tokens"]) > 0
        
        # Verify we can reconstruct original text
        reconstructed = w3w_tokenizer.decode(archived["w3w_tokens"])
        assert reconstructed.strip() == test_text

class TestMemoryStats:
    @pytest.mark.asyncio
    async def test_stats_broadcast_on_changes(self, memory_manager, mock_websocket_server):
        client = websockets.WebSocket()
        client.connect("ws://localhost:8000")
        
        # Add memory and verify stats update
        memory_manager.add_memory_block(
            content="Test memory",
            significance_type=SignificanceType.SYSTEM
        )
        
        message = client.recv()
        stats = json.loads(message)
        
        assert stats["type"] == "stats_update"
        assert stats["data"]["current_token_count"] == 1000
        await client.close()

    @pytest.mark.asyncio
    async def test_cli_matches_web_stats(self, memory_manager, mock_websocket_server):
        # Add some memories
        memory_manager.add_memory_block(
            content="Memory 1",
            significance_type=SignificanceType.USER
        )
        memory_manager.add_memory_block(
            content="Memory 2",
            significance_type=SignificanceType.SYSTEM
        )
        
        # Get CLI stats
        cli_stats = memory_manager.get_stats()
        
        # Get web stats
        client = websockets.WebSocket()
        client.connect("ws://localhost:8000")
        message = client.recv()
        web_stats = json.loads(message)["data"]

        # Verify they match
        assert cli_stats["current_token_count"] == web_stats["current_token_count"]
        assert cli_stats["total_memories"] == web_stats["total_memories"]
        client.close()

class TestContextWindow:
    def test_efficient_token_management(self, memory_manager):
        # Add memories up to limit
        for i in range(100):
            memory_manager.add_memory_block(
                content=f"Memory {i}",
                significance_type=SignificanceType.SYSTEM
            )
        
        # Verify older memories got archived
        assert memory_manager.current_token_count <= memory_manager.token_limit
        assert len(memory_manager.get_archived_memories()) > 0

    @pytest.mark.asyncio
    async def test_memory_retrieval_from_archive(self, memory_manager, memory_client):
        # Archive some memories
        for i in range(50):
            memory_manager.add_memory_block(
                content=f"Test memory {i}",
                significance_type=SignificanceType.SYSTEM
            )
        
        # Query for relevant context
        results = await memory_manager.get_relevant_context("test memory 25")
        
        # Verify retrieval works
        assert len(results) > 0
        assert "Test memory 25" in results[0]["content"]

class TestMemoryServerIntegration:
    @pytest.mark.asyncio
    async def test_server_connection_handling(self, memory_client):
        # Test connection establishment
        connected = await memory_client.connect()
        assert connected
        
        # Test reconnection on failure
        with patch('websockets.connect', side_effect=Exception):
            await memory_client.reconnect()
            assert memory_client.using_local_fallback

    @pytest.mark.asyncio
    async def test_memory_persistence(self, memory_manager, memory_client):
        # Store memory
        test_memory = "Memory to be stored long-term"
        await memory_client.archive(
            content=test_memory, 
            significance_type=SignificanceType.USER
        )
        )
        
        # Verify retrieval
        memories = await memory_client.get_memories()
        assert any(test_memory in m["content"] for m in memories)


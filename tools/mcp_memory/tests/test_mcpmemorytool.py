import os
import pytest
import tempfile
import shutil
from pathlib import Path

from tools.mcp_memory.src.mcp_memory_service.memory_service import MemoryService
from tools.mcpmemorytool import MCPMemoryTool

@pytest.fixture
def test_dir():
    """Create a temporary test directory."""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir)

@pytest.fixture
def memory_tool(test_dir):
    """Set up MCPMemoryTool with test configuration."""
    config_dir = Path(test_dir) / "config"
    chroma_dir = Path(test_dir) / "chroma_db"
    backup_dir = Path(test_dir) / "backups"
    
    # Create required directories
    config_dir.mkdir()
    chroma_dir.mkdir()
    backup_dir.mkdir()
    
    # Initialize tool with test configuration
    tool = MCPMemoryTool(
        chroma_path=str(chroma_dir),
        backup_path=str(backup_dir),
        config_path=str(config_dir)
    )
    
    yield tool
    
    # Cleanup happens via test_dir fixture

def test_store_and_retrieve(memory_tool):
    """Test basic store and retrieve operations."""
    test_content = "This is a test memory about AI development"
    metadata = {"source": "unit_test", "tags": ["test", "ai"]}
    
    # Store a test memory
    memory_id = memory_tool.store_memory(
        content=test_content,
        metadata=metadata
    )
    
    # Verify memory was stored
    assert memory_id is not None
    
    # Retrieve memory
    results = memory_tool.retrieve_memory(
        query="test memory AI",
        limit=1
    )
    
    assert len(results) > 0
    assert results[0]["content"] == test_content
    assert results[0]["metadata"]["source"] == "unit_test"

def test_search_by_tag(memory_tool):
    """Test tag-based search functionality."""
    # Store multiple memories with different tags
    memory_tool.store_memory(
        content="Python programming",
        metadata={"tags": ["programming", "python"]}
    )
    memory_tool.store_memory(
        content="Java development",
        metadata={"tags": ["programming", "java"]}
    )
    
    # Search by programming tag
    results = memory_tool.search_by_tag("programming")
    assert len(results) == 2
    
    # Search by python tag
    python_results = memory_tool.search_by_tag("python")
    assert len(python_results) == 1
    assert "Python programming" in python_results[0]["content"]

def test_configuration_handling(test_dir):
    """Test configuration and path handling."""
    # Test with invalid paths
    with pytest.raises(Exception):
        MCPMemoryTool(
            chroma_path="/invalid/path",
            backup_path="/invalid/path",
            config_path="/invalid/path"
        )
    
    # Test with valid paths
    valid_tool = MCPMemoryTool(
        chroma_path=str(Path(test_dir) / "chroma"),
        backup_path=str(Path(test_dir) / "backups"),
        config_path=str(Path(test_dir) / "config")
    )
    
    assert valid_tool is not None
    assert os.path.exists(str(Path(test_dir) / "chroma"))
    assert os.path.exists(str(Path(test_dir) / "backups"))

def test_memory_deletion(memory_tool):
    """Test memory deletion functionality."""
    # Store a test memory
    memory_id = memory_tool.store_memory(
        content="Delete this memory",
        metadata={"tags": ["temp"]}
    )
    
    # Verify memory exists
    results = memory_tool.search_by_tag("temp")
    assert len(results) == 1
    
    # Delete memory
    memory_tool.delete_memory(memory_id)
    
    # Verify memory was deleted
    results = memory_tool.search_by_tag("temp")
    assert len(results) == 0

def test_similarity_search(memory_tool):
    """Test semantic similarity search functionality."""
    # Store related memories
    memory_tool.store_memory(
        content="The quick brown fox jumps over the lazy dog",
        metadata={"tags": ["animals"]}
    )
    memory_tool.store_memory(
        content="A fast auburn canine leaps across a sleeping hound",
        metadata={"tags": ["animals"]}
    )
    
    # Search with similar but not identical text
    results = memory_tool.retrieve_memory(
        query="rapid red fox jumping",
        limit=2
    )
    
    assert len(results) == 2
    # Results should be ordered by similarity
    assert "fox" in results[0]["content"].lower()


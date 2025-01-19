import pytest
import os
from io import StringIO
from unittest.mock import patch, MagicMock
from rich.console import Console

from tools.diffdisplaytool import DiffDisplayTool

@pytest.fixture
def diff_tool():
    return DiffDisplayTool()

@pytest.fixture
def sample_files(tmp_path):
    # Create test files with known content
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    
    file1.write_text("line 1\nline 2\nline 3\n")
    file2.write_text("line 1\nmodified line\nline 3\n")
    
    return str(file1), str(file2)

def test_init(diff_tool):
    assert diff_tool.name == "diffdisplay"
    assert diff_tool.description
    assert diff_tool.input_schema

def test_compare_files_unified(diff_tool, sample_files):
    file1, file2 = sample_files
    result = diff_tool.execute({
        "file1": file1,
        "file2": file2,
        "view_type": "unified"
    })
    
    assert "line 1" in result
    assert "modified line" in result
    assert "-line 2" in result
    assert "+modified line" in result

def test_compare_files_side_by_side(diff_tool, sample_files):
    file1, file2 = sample_files
    result = diff_tool.execute({
        "file1": file1,
        "file2": file2,
        "view_type": "side-by-side"
    })
    
    assert "line 1" in result
    assert "line 2" in result
    assert "modified line" in result

@patch('subprocess.check_output')
def test_git_diff(mock_git, diff_tool):
    mock_git.return_value = b"diff --git a/file1 b/file2\n-old line\n+new line"
    
    result = diff_tool.execute({
        "git_path": "some/path",
        "view_type": "unified"
    })
    
    assert "old line" in result
    assert "new line" in result
    mock_git.assert_called_once()

def test_invalid_file_path(diff_tool):
    with pytest.raises(Exception) as exc_info:
        diff_tool.execute({
            "file1": "nonexistent.txt",
            "file2": "also_nonexistent.txt",
            "view_type": "unified"
        })
    assert "File not found" in str(exc_info.value)

def test_invalid_git_path(diff_tool):
    with pytest.raises(Exception) as exc_info:
        diff_tool.execute({
            "git_path": "/invalid/git/path",
            "view_type": "unified"
        })
    assert "Git diff failed" in str(exc_info.value)

def test_rich_formatting(diff_tool, sample_files):
    file1, file2 = sample_files
    result = diff_tool.execute({
        "file1": file1,
        "file2": file2,
        "view_type": "unified"
    })
    
    # Check for rich formatting markers
    assert "[" in result  # Rich uses [] for styling
    assert "─" in result  # Check for box drawing characters
    
    # Verify syntax highlighting markers
    console = Console(color_system=None)
    with console.capture() as capture:
        console.print(result)
    output = capture.get()
    assert "modified line" in output


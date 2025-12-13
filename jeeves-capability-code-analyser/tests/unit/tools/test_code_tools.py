"""Unit tests for code analysis tools.

Tests the read-only code traversal tools:
- read_file
- glob_files
- grep_search
- tree_structure
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

# Import tools (sys.path configured in conftest.py)
from tools.base.code_tools import (
    read_file,
    glob_files,
    grep_search,
    tree_structure,
)
from tools.base.path_helpers import (
    get_repo_path as _get_repo_path,
    resolve_path as _resolve_path,
)


class TestReadFile:
    """Tests for read_file tool."""

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary test file."""
        test_file = tmp_path / "test.py"
        content = "\n".join([f"line {i}" for i in range(1, 51)])
        test_file.write_text(content)
        return test_file

    @pytest.mark.asyncio
    async def test_read_file_success(self, temp_file, monkeypatch):
        """Test reading a file successfully."""
        monkeypatch.setenv("REPO_PATH", str(temp_file.parent))

        result = await read_file("test.py")

        assert result["status"] == "success"
        assert "line 1" in result["content"]
        assert result["total_lines"] == 50
        assert result["path"] == "test.py"

    @pytest.mark.asyncio
    async def test_read_file_with_line_range(self, temp_file, monkeypatch):
        """Test reading specific line range."""
        monkeypatch.setenv("REPO_PATH", str(temp_file.parent))

        result = await read_file("test.py", start_line=5, end_line=10)

        assert result["status"] == "success"
        assert result["start_line"] == 5
        assert result["lines_returned"] == 6  # Lines 5-10 inclusive

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, tmp_path, monkeypatch):
        """Test reading non-existent file."""
        monkeypatch.setenv("REPO_PATH", str(tmp_path))

        result = await read_file("nonexistent.py")

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_file_outside_repo(self, tmp_path, monkeypatch):
        """Test that absolute paths are treated as relative to repo root.

        Per design: Paths like '/etc/passwd' are normalized to 'etc/passwd'
        relative to repo root. This prevents directory traversal while
        handling LLM-generated paths that start with '/'.
        """
        monkeypatch.setenv("REPO_PATH", str(tmp_path))

        result = await read_file("/etc/passwd")

        # The path is normalized to {repo}/etc/passwd which doesn't exist
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_read_file_custom_max_tokens(self, temp_file, monkeypatch):
        """Test reading with custom max_tokens parameter."""
        monkeypatch.setenv("REPO_PATH", str(temp_file.parent))

        # Use small max_tokens to trigger truncation
        result = await read_file("test.py", max_tokens=1000)

        assert result["status"] == "success"
        assert result["max_tokens_used"] == 1000

    @pytest.mark.asyncio
    async def test_read_file_without_line_numbers(self, temp_file, monkeypatch):
        """Test reading without line numbers."""
        monkeypatch.setenv("REPO_PATH", str(temp_file.parent))

        result = await read_file("test.py", include_line_numbers=False)

        assert result["status"] == "success"
        # Content should not have line number format (6 digits + tab)
        lines = result["content"].split("\n")
        assert not lines[0].startswith("     1\t")

    @pytest.mark.asyncio
    async def test_read_file_max_tokens_clamped(self, temp_file, monkeypatch):
        """Test that max_tokens is clamped to safe range (18K-24K context budget)."""
        monkeypatch.setenv("REPO_PATH", str(temp_file.parent))

        # Try value below minimum
        result = await read_file("test.py", max_tokens=100)
        assert result["max_tokens_used"] == 1000  # Clamped to minimum

        # Try value above maximum (clamped to 8000 for 18K-24K context budget)
        result = await read_file("test.py", max_tokens=100000)
        assert result["max_tokens_used"] == 8000  # Clamped to maximum


class TestGlobFiles:
    """Tests for glob_files tool."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repo with files."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main")
        (tmp_path / "src" / "utils.py").write_text("# utils")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("# test")
        return tmp_path

    @pytest.mark.asyncio
    async def test_glob_python_files(self, temp_repo, monkeypatch):
        """Test globbing Python files."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await glob_files("**/*.py")

        assert result["status"] == "success"
        assert result["count"] == 3
        assert "src/main.py" in result["files"]

    @pytest.mark.asyncio
    async def test_glob_specific_dir(self, temp_repo, monkeypatch):
        """Test globbing in specific directory."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await glob_files("src/*.py")

        assert result["status"] == "success"
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_glob_max_results(self, temp_repo, monkeypatch):
        """Test max_results limit."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await glob_files("**/*.py", max_results=1)

        assert result["status"] == "success"
        assert result["count"] == 1


class TestGrepSearch:
    """Tests for grep_search tool."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repo with searchable content."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("""
def hello_world():
    print("Hello World")

def goodbye_world():
    print("Goodbye World")
""")
        (tmp_path / "src" / "utils.py").write_text("""
def helper_function():
    pass
""")
        return tmp_path

    @pytest.mark.asyncio
    async def test_grep_simple_pattern(self, temp_repo, monkeypatch):
        """Test searching for simple pattern."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await grep_search("def.*world", file_types="py")

        assert result["status"] == "success"
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_grep_with_context(self, temp_repo, monkeypatch):
        """Test search includes context lines."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await grep_search("hello_world", context_lines=1)

        assert result["status"] == "success"
        assert len(result["matches"]) > 0
        assert "context" in result["matches"][0]

    @pytest.mark.asyncio
    async def test_grep_in_specific_path(self, temp_repo, monkeypatch):
        """Test searching in specific path."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await grep_search("helper", path="src/utils.py")

        assert result["status"] == "success"
        assert result["count"] == 1


class TestTreeStructure:
    """Tests for tree_structure tool."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repo with structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main")
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "__init__.py").write_text("")
        (tmp_path / "tests").mkdir()
        (tmp_path / "README.md").write_text("# README")
        return tmp_path

    @pytest.mark.asyncio
    async def test_tree_default(self, temp_repo, monkeypatch):
        """Test tree with default settings."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await tree_structure()

        assert result["status"] == "success"
        assert "src/" in result["tree"]
        assert "tests/" in result["tree"]
        assert result["dir_count"] >= 2

    @pytest.mark.asyncio
    async def test_tree_specific_path(self, temp_repo, monkeypatch):
        """Test tree for specific path."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await tree_structure(path="src")

        assert result["status"] == "success"
        assert "main.py" in result["tree"]

    @pytest.mark.asyncio
    async def test_tree_depth_limit(self, temp_repo, monkeypatch):
        """Test tree with depth limit."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await tree_structure(depth=1)

        assert result["status"] == "success"
        # Should show top level only
        assert result["depth"] == 1

    @pytest.mark.asyncio
    async def test_tree_max_entries(self, temp_repo, monkeypatch):
        """Test tree with max_entries limit."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await tree_structure(max_entries=2)

        assert result["status"] == "success"
        # Should have limited entries

    @pytest.mark.asyncio
    async def test_tree_file_types_filter(self, temp_repo, monkeypatch):
        """Test tree with file_types filter."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        result = await tree_structure(file_types="py")

        assert result["status"] == "success"
        # Should only show .py files
        tree_content = result["tree"]
        assert "main.py" in tree_content
        # README.md should not appear in tree (directories still appear for traversal)

    @pytest.mark.asyncio
    async def test_tree_max_entries_clamped(self, temp_repo, monkeypatch):
        """Test that max_entries is clamped to safe range (18K-24K context budget)."""
        monkeypatch.setenv("REPO_PATH", str(temp_repo))

        # Value below minimum gets clamped to 100
        result = await tree_structure(max_entries=10)
        assert result["status"] == "success"

        # Value above maximum gets clamped to 2000 (for 18K-24K context budget)
        result = await tree_structure(max_entries=10000)
        assert result["status"] == "success"


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_resolve_path_relative(self, tmp_path):
        """Test resolving relative path."""
        result = _resolve_path("src/main.py", str(tmp_path))
        assert result is not None
        assert str(result).startswith(str(tmp_path))

    def test_resolve_path_absolute_safe(self, tmp_path):
        """Test resolving safe absolute path."""
        safe_path = tmp_path / "file.py"
        result = _resolve_path(str(safe_path), str(tmp_path))
        assert result is not None

    def test_resolve_path_outside_repo(self, tmp_path):
        """Test that absolute paths are normalized to repo-relative.

        Per design: '/etc/passwd' is normalized to 'etc/passwd' relative to repo.
        This handles LLM-generated paths that start with '/'.
        """
        result = _resolve_path("/etc/passwd", str(tmp_path))
        # Path is normalized to {repo}/etc/passwd (within bounds)
        assert result is not None
        assert str(result) == str(tmp_path / "etc" / "passwd")

    def test_resolve_path_empty(self, tmp_path):
        """Test resolving empty path returns repo root."""
        result = _resolve_path("", str(tmp_path))
        assert result is not None
        assert result == tmp_path

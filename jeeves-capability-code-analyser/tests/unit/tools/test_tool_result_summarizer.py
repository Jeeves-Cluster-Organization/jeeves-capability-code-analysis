"""Tests for centralized tool result summarization.

Per Constitution P1 (Accuracy): verifies that all tool-specific fields
are preserved for citation verification.

Per Constitution P2 (Code Context): verifies structural queries
(tree, git, imports) are properly summarized.
"""

import pytest
from agents.summarizer import (
    summarize_tool_result,
    summarize_execution_results,
    extract_citations_from_results,
)


class TestSummarizeToolResult:
    """Tests for summarize_tool_result function."""

    def test_tree_structure_included(self):
        """Tree structure data should be preserved for directory queries."""
        data = {
            "tree": "├── agents/\n│   ├── base.py\n│   └── traverser/\n└── tools/",
            "path": ".",
            "file_count": 45,
            "dir_count": 12
        }

        result = summarize_tool_result("tree_structure", data)

        assert "tree" in result
        assert result["tree"] == data["tree"]
        assert result["file_count"] == 45
        assert result["dir_count"] == 12

    def test_tree_truncation_with_indicator(self):
        """Long tree structures should be truncated with indicator."""
        long_tree = "├── " + "\n│   ├── file.py" * 1000
        data = {"tree": long_tree, "path": ".", "file_count": 1000}

        result = summarize_tool_result("tree_structure", data)

        assert "tree_truncated" in result
        assert result["tree_truncated"] is True
        assert result["tree"].endswith("[... tree truncated ...]")

    def test_content_preserved(self):
        """File content should be preserved for citation."""
        data = {
            "path": "agents/base.py",
            "content": "class Agent:\n    pass",
            "start_line": 1,
            "end_line": 2
        }

        result = summarize_tool_result("read_file", data)

        assert result["content"] == data["content"]
        assert result["start_line"] == 1
        assert result["end_line"] == 2

    def test_grep_matches_preserved(self):
        """Grep matches should be preserved with truncation."""
        data = {
            "matches": [
                {"file": "test.py", "line": 10, "match": "def test()"},
                {"file": "test2.py", "line": 20, "match": "def test2()"}
            ]
        }

        result = summarize_tool_result("grep_search", data)

        assert "matches" in result
        assert len(result["matches"]) == 2
        assert result["total_matches"] == 2

    def test_symbols_preserved(self):
        """Symbols should be preserved for code analysis."""
        data = {
            "symbols": [
                {"name": "Agent", "kind": "class", "file": "base.py", "line": 10},
                {"name": "process", "kind": "function", "file": "base.py", "line": 20}
            ]
        }

        result = summarize_tool_result("find_symbol", data)

        assert "symbols" in result
        assert len(result["symbols"]) == 2
        assert result["total_symbols"] == 2

    def test_imports_preserved(self):
        """Imports should be preserved for dependency analysis."""
        data = {
            "path": "agents/base.py",
            "imports": ["typing", "structlog", "pydantic"]
        }

        result = summarize_tool_result("get_imports", data)

        assert "imports" in result
        assert len(result["imports"]) == 3

    def test_git_commits_preserved(self):
        """Git commits should be preserved for history queries."""
        data = {
            "commits": [
                {"hash": "abc123", "author_name": "Dev", "message": "Fix bug"},
                {"hash": "def456", "author_name": "Dev2", "message": "Add feature"}
            ]
        }

        result = summarize_tool_result("git_log", data)

        assert "commits" in result
        assert len(result["commits"]) == 2
        assert result["total_commits"] == 2

    def test_empty_data_returns_empty_dict(self):
        """Empty or None data should return empty dict."""
        assert summarize_tool_result("read_file", None) == {}
        assert summarize_tool_result("read_file", {}) == {}


class TestSummarizeExecutionResults:
    """Tests for summarize_execution_results function."""

    def test_summarizes_all_results(self):
        """Should summarize all execution results."""
        # Mock results with tool, status, data attributes
        class MockResult:
            def __init__(self, tool, status, data):
                self.tool = tool
                self.status = status
                self.data = data
                self.error = None

        results = [
            MockResult("tree_structure", "success", {"tree": "├── file.py", "file_count": 1}),
            MockResult("read_file", "success", {"path": "file.py", "content": "code"})
        ]

        summaries = summarize_execution_results(results)

        assert len(summaries) == 2
        assert summaries[0]["tool"] == "tree_structure"
        assert "tree" in summaries[0]["data"]
        assert summaries[1]["tool"] == "read_file"

    def test_excludes_errors_when_requested(self):
        """Should optionally exclude error results."""
        class MockResult:
            def __init__(self, tool, status, data=None, error=None):
                self.tool = tool
                self.status = status
                self.data = data
                self.error = error

        results = [
            MockResult("tree_structure", "success", {"tree": "├── file.py"}),
            MockResult("read_file", "error", error={"message": "File not found"})
        ]

        summaries = summarize_execution_results(results, include_errors=False)

        assert len(summaries) == 1
        assert summaries[0]["tool"] == "tree_structure"

    def test_handles_dict_results(self):
        """Should handle dict-style results."""
        results = [
            {"tool": "tree_structure", "status": "success", "data": {"tree": "├──"}}
        ]

        summaries = summarize_execution_results(results)

        assert len(summaries) == 1
        assert summaries[0]["tool"] == "tree_structure"


class TestExtractCitationsFromResults:
    """Tests for extract_citations_from_results function."""

    def test_extracts_from_read_file(self):
        """Should extract citations from read_file results."""
        class MockResult:
            def __init__(self):
                self.tool = "read_file"
                self.data = {"path": "agents/base.py", "start_line": 10}

        citations = extract_citations_from_results([MockResult()])

        assert len(citations) == 1
        assert citations[0]["file"] == "agents/base.py"
        assert citations[0]["line"] == 10

    def test_extracts_from_grep_matches(self):
        """Should extract citations from grep matches."""
        class MockResult:
            def __init__(self):
                self.tool = "grep_search"
                self.data = {
                    "matches": [
                        {"file": "test.py", "line": 20, "match": "def test()"}
                    ]
                }

        citations = extract_citations_from_results([MockResult()])

        assert len(citations) == 1
        assert citations[0]["file"] == "test.py"
        assert citations[0]["line"] == 20

    def test_extracts_from_symbols(self):
        """Should extract citations from symbol results."""
        class MockResult:
            def __init__(self):
                self.tool = "find_symbol"
                self.data = {
                    "symbols": [
                        {"name": "Agent", "file": "base.py", "line": 10, "kind": "class"}
                    ]
                }

        citations = extract_citations_from_results([MockResult()])

        assert len(citations) == 1
        assert citations[0]["file"] == "base.py"
        assert "class: Agent" in citations[0]["context"]

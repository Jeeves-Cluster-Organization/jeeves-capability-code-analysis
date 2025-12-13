"""Code analysis tool result summarization.

Vertical-specific summarizer for code analysis tools.
Handles: tree_structure, read_file, grep_search, find_symbol, git_log, etc.

Usage:
    from verticals.code_analysis.agents.summarizer import summarize_tool_result, summarize_execution_results

    # Single result with custom bounds
    bounds = {"max_tree_summary_chars": 3000, ...}
    summary = summarize_tool_result(result.tool, result.data, bounds=bounds)

    # All results for LLM prompt
    summaries = summarize_execution_results(execution.results, bounds=bounds)
"""

from typing import Any, Dict, List, Optional


# Default summarization bounds (can be overridden via parameter)
DEFAULT_SUMMARY_BOUNDS = {
    "max_tree_summary_chars": 3000,
    "max_content_summary_chars": 2000,
    "max_matches_in_summary": 20,
    "max_symbols_in_summary": 30,
    "max_commits_in_summary": 10,
    "max_imports_in_summary": 30,
}


def summarize_tool_result(
    tool: str,
    data: Optional[Dict[str, Any]],
    bounds: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Summarize a single tool result for agent handoff.

    Args:
        tool: Tool name that produced the result
        data: Raw tool output data
        bounds: Optional bounds dict. If not provided, uses DEFAULT_SUMMARY_BOUNDS.
                Keys: max_tree_summary_chars, max_content_summary_chars,
                      max_matches_in_summary, max_symbols_in_summary,
                      max_commits_in_summary, max_imports_in_summary

    Returns:
        Summarized data dict with all relevant fields preserved within bounds
    """
    if not data or not isinstance(data, dict):
        return {}

    b = bounds or DEFAULT_SUMMARY_BOUNDS
    summary: Dict[str, Any] = {}

    def get_bound(key: str, default: int) -> int:
        return b.get(key, default)

    # ─── Universal fields (always include) ───
    for key in ["path", "file", "status", "error", "message"]:
        if key in data:
            summary[key] = data[key]

    # ─── Tree structure (CRITICAL for directory queries) ───
    if "tree" in data:
        tree = data["tree"]
        max_tree = get_bound("max_tree_summary_chars", 3000)
        if isinstance(tree, str):
            if len(tree) > max_tree:
                summary["tree"] = tree[:max_tree] + "\n[... tree truncated ...]"
                summary["tree_truncated"] = True
            else:
                summary["tree"] = tree
        summary["file_count"] = data.get("file_count")
        summary["dir_count"] = data.get("dir_count")

    # ─── File content ───
    if "content" in data:
        content = str(data["content"])
        max_content = get_bound("max_content_summary_chars", 2000)
        if len(content) > max_content:
            summary["content"] = content[:max_content] + "\n[... content truncated ...]"
            summary["content_truncated"] = True
        else:
            summary["content"] = content
        # Preserve line info for citations
        for key in ["start_line", "end_line", "lines_returned", "total_lines"]:
            if key in data:
                summary[key] = data[key]

    # ─── Grep/search matches ───
    if "matches" in data:
        matches = data["matches"]
        max_matches = get_bound("max_matches_in_summary", 20)
        if isinstance(matches, list):
            summary["matches"] = matches[:max_matches]
            summary["total_matches"] = len(matches)
            if len(matches) > max_matches:
                summary["matches_truncated"] = True

    # ─── Symbols (find_symbol, get_file_symbols, parse_symbols) ───
    if "symbols" in data:
        symbols = data["symbols"]
        max_symbols = get_bound("max_symbols_in_summary", 30)
        if isinstance(symbols, list):
            summary["symbols"] = symbols[:max_symbols]
            summary["total_symbols"] = len(symbols)
            if len(symbols) > max_symbols:
                summary["symbols_truncated"] = True

    # ─── Imports/dependencies ───
    if "imports" in data:
        imports = data["imports"]
        max_imports = get_bound("max_imports_in_summary", 30)
        if isinstance(imports, list):
            summary["imports"] = imports[:max_imports]
            summary["total_imports"] = len(imports)
            if len(imports) > max_imports:
                summary["imports_truncated"] = True

    if "importers" in data:
        importers = data["importers"]
        max_imports = get_bound("max_imports_in_summary", 30)
        if isinstance(importers, list):
            summary["importers"] = importers[:max_imports]
            summary["total_importers"] = len(importers)

    # ─── Git results ───
    if "commits" in data:
        commits = data["commits"]
        max_commits = get_bound("max_commits_in_summary", 10)
        if isinstance(commits, list):
            summary["commits"] = commits[:max_commits]
            summary["total_commits"] = len(commits)
            if len(commits) > max_commits:
                summary["commits_truncated"] = True

    if "blame" in data:
        blame = data["blame"]
        max_commits = get_bound("max_commits_in_summary", 10)
        if isinstance(blame, list):
            summary["blame"] = blame[:max_commits]

    if "diff" in data:
        diff = str(data["diff"])
        max_content = get_bound("max_content_summary_chars", 2000)
        if len(diff) > max_content:
            summary["diff"] = diff[:max_content] + "\n[... diff truncated ...]"
        else:
            summary["diff"] = diff

    # ─── Files list (glob_files, list_files) ───
    if "files" in data:
        files = data["files"]
        if isinstance(files, list):
            summary["files"] = files[:100]  # Cap at 100 files
            summary["total_files"] = len(files)
            if len(files) > 100:
                summary["files_truncated"] = True

    # ─── Semantic search results ───
    if "results" in data and tool in ["semantic_search", "find_similar_files"]:
        results = data["results"]
        max_matches = get_bound("max_matches_in_summary", 20)
        if isinstance(results, list):
            summary["results"] = results[:max_matches]
            summary["total_results"] = len(results)

    # ─── Index stats ───
    if tool == "get_index_stats":
        for key in ["indexed_files", "total_symbols", "languages", "last_updated"]:
            if key in data:
                summary[key] = data[key]

    return summary


def summarize_execution_results(
    results: List[Any],
    include_errors: bool = True,
    bounds: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Summarize all execution results for LLM prompt.

    Args:
        results: List of ToolExecutionResult objects
        include_errors: Whether to include failed results
        bounds: Optional bounds dict for summarization

    Returns:
        List of summarized result dicts
    """
    summaries = []

    for result in results:
        # Handle both dict and object access patterns
        if hasattr(result, "tool"):
            tool = result.tool
            status = result.status
            data = result.data
            error = getattr(result, "error", None)
        else:
            tool = result.get("tool", "unknown")
            status = result.get("status", "unknown")
            data = result.get("data")
            error = result.get("error")

        if status == "error" and not include_errors:
            continue

        summary = {
            "tool": tool,
            "status": status,
        }

        if status == "success" and data:
            summary["data"] = summarize_tool_result(tool, data, bounds=bounds)
        elif status == "error" and error:
            summary["error"] = error

        summaries.append(summary)

    return summaries


def extract_citations_from_results(results: List[Any]) -> List[Dict[str, str]]:
    """Extract file:line citations from execution results.

    Per Constitution P1: Every claim needs [file:line] citation.

    Args:
        results: List of ToolExecutionResult objects

    Returns:
        List of citation dicts with file, line, context
    """
    citations = []

    for result in results:
        data = result.data if hasattr(result, "data") else result.get("data")
        if not data:
            continue

        tool = result.tool if hasattr(result, "tool") else result.get("tool")

        # Extract from read_file
        if tool == "read_file" and data.get("path"):
            citations.append({
                "file": data["path"],
                "line": data.get("start_line", 1),
                "context": "file_read"
            })

        # Extract from grep matches
        if data.get("matches"):
            for match in data["matches"][:20]:
                if isinstance(match, dict) and match.get("file"):
                    citations.append({
                        "file": match["file"],
                        "line": match.get("line", 1),
                        "context": match.get("match", "")[:100]
                    })

        # Extract from symbols
        if data.get("symbols"):
            for sym in data["symbols"][:20]:
                if isinstance(sym, dict) and sym.get("file"):
                    citations.append({
                        "file": sym["file"],
                        "line": sym.get("line", 1),
                        "context": f"{sym.get('kind', 'symbol')}: {sym.get('name', '')}"
                    })

    return citations

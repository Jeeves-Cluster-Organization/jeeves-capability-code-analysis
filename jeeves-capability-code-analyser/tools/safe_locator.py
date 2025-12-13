"""Safe Locator - Deterministic fallback search composite tool.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XVII (Composite Tool Contracts), this tool:
- Orchestrates multiple primitive tools in a deterministic sequence
- Returns attempt_history for transparency
- Aggregates citations from all steps
- Respects context bounds
- Degrades gracefully on step failures

Refactored to use RobustToolExecutor (unifying composite/resilient tool patterns).
"""

import re
from typing import Any, Dict, Optional

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol
from jeeves_protocols import RiskLevel
from tools.robust_tool_base import (
    RobustToolExecutor,
    make_strategy,
    ResultMappers,
)


# ============================================================
# Strategy Parameter Mappers
# ============================================================

def _params_find_symbol_exact(query: str, scope: Optional[str] = None, **_) -> Dict[str, Any]:
    """Map locate params to find_symbol with exact=True."""
    return {"name": query, "exact": True, "path_prefix": scope}


def _params_find_symbol_partial(query: str, scope: Optional[str] = None, **_) -> Dict[str, Any]:
    """Map locate params to find_symbol with exact=False."""
    return {"name": query, "exact": False, "path_prefix": scope}


def _params_grep_sensitive(query: str, scope: Optional[str] = None, **_) -> Dict[str, Any]:
    """Map locate params to grep_search (case-sensitive)."""
    # Escape special regex chars for literal search
    pattern = re.escape(query)
    return {"pattern": pattern, "path": scope, "max_results": 20}


def _params_grep_insensitive(query: str, scope: Optional[str] = None, **_) -> Dict[str, Any]:
    """Map locate params to grep_search (case-insensitive)."""
    # Escape and add case-insensitive flag
    pattern = f"(?i){re.escape(query)}"
    return {"pattern": pattern, "path": scope, "max_results": 20}


def _params_semantic(query: str, scope: Optional[str] = None, **_) -> Dict[str, Any]:
    """Map locate params to semantic_search."""
    return {"query": query, "limit": 10, "path_prefix": scope}


# ============================================================
# Main Locate Tool
# ============================================================

async def locate(
    query: str,
    search_type: str = "auto",
    scope: Optional[str] = None,
    max_results: int = 20,
) -> Dict[str, Any]:
    """Locate code elements with deterministic fallback strategy.

    Per Amendment XVII, this composite tool:
    1. Executes a deterministic sequence of search strategies
    2. Returns attempt_history for transparency
    3. Collects citations from all steps
    4. Respects context bounds

    Uses RobustToolExecutor for unified fallback chain execution.

    Fallback sequence (for search_type='auto'):
    1. find_symbol(exact=True) - Exact symbol match
    2. find_symbol(exact=False) - Partial symbol match
    3. grep_search(case_sensitive=True) - Exact text search
    4. grep_search(case_sensitive=False) - Case-insensitive text search
    5. semantic_search - Semantic fallback

    Args:
        query: What to find (symbol name, text pattern, etc.)
        search_type: Search strategy - 'symbol', 'text', 'semantic', or 'auto'
        scope: Path prefix to limit search scope
        max_results: Maximum results to return

    Returns:
        Dict with:
        - status: 'success', 'partial', or 'not_found'
        - query: Original query
        - found_via: Method that found results
        - results: List of matches with file, line, match info
        - attempt_history: List of all attempts with method and result
        - citations: Deduplicated [file:line] citations
        - scope_used: Scope that was applied
        - bounded: Whether search was limited by bounds
    """
    # Create executor with configured max_results
    executor = RobustToolExecutor(
        name="locate",
        max_results=max_results,
    )

    # Build fallback chain based on search_type
    if search_type == "symbol":
        executor.add_strategy(
            "find_symbol (exact)",
            make_strategy("find_symbol", ResultMappers.symbols, _params_find_symbol_exact)
        )
        executor.add_strategy(
            "find_symbol (partial)",
            make_strategy("find_symbol", ResultMappers.symbols, _params_find_symbol_partial)
        )

    elif search_type == "text":
        executor.add_strategy(
            "grep_search (case-sensitive)",
            make_strategy("grep_search", ResultMappers.grep_matches, _params_grep_sensitive)
        )
        executor.add_strategy(
            "grep_search (case-insensitive)",
            make_strategy("grep_search", ResultMappers.grep_matches, _params_grep_insensitive)
        )

    elif search_type == "semantic":
        executor.add_strategy(
            "semantic_search",
            make_strategy("semantic_search", ResultMappers.semantic_results, _params_semantic)
        )

    else:  # auto - try all strategies in order
        executor.add_strategy(
            "find_symbol (exact)",
            make_strategy("find_symbol", ResultMappers.symbols, _params_find_symbol_exact)
        )
        executor.add_strategy(
            "find_symbol (partial)",
            make_strategy("find_symbol", ResultMappers.symbols, _params_find_symbol_partial)
        )
        executor.add_strategy(
            "grep_search (case-sensitive)",
            make_strategy("grep_search", ResultMappers.grep_matches, _params_grep_sensitive)
        )
        executor.add_strategy(
            "grep_search (case-insensitive)",
            make_strategy("grep_search", ResultMappers.grep_matches, _params_grep_insensitive)
        )
        executor.add_strategy(
            "semantic_search",
            make_strategy("semantic_search", ResultMappers.semantic_results, _params_semantic)
        )

    # Execute the fallback chain
    result = await executor.execute(query=query, scope=scope)

    # Convert to locate-specific output format
    output = result.to_dict()
    output["query"] = query
    output["scope_used"] = scope

    _logger = get_logger()
    _logger.info(
        "locate_completed",
        query=query,
        found_via=result.found_via,
        result_count=len(result.results),
        attempts=len(result.attempt_history),
    )

    return output


__all__ = ["locate"]

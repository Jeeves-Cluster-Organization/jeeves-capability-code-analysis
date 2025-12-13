"""
Tool Result Schemas for Code Analysis Vertical.

TypedDict definitions for all code-analysis tool results.
These define the NORMALIZED shapes that tools SHOULD return.

Normalization Rules (enforced by validation):
1. `files` is ALWAYS a List[str], never an int count
2. `file_count` is the separate count field (int)
3. `attempt_history` is ALWAYS a List (possibly empty) for composite tools
4. `citations` is ALWAYS a List[str] in [file:line] format
5. `status` uses ToolResultStatus enum values

Proto-3 Note:
These TypedDicts can later be converted to a schema registry format
(e.g., JSON Schema, Pydantic models) with minimal refactoring.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS ENUM (String Literal for TypedDict compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

ToolResultStatus = Literal["success", "partial", "not_found", "error"]


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class AttemptHistoryEntry(TypedDict, total=False):
    """Single entry in attempt_history.

    Per Amendment XVII: All composite tools MUST return attempt_history.
    """
    step: int                          # Required: step number (1-indexed)
    strategy: str                      # Required: strategy name used
    result: str                        # Required: outcome (success, not_found, error)
    params: Dict[str, Any]             # Optional: parameters passed
    error: Optional[str]               # Optional: error message if failed
    retry_count: int                   # Optional: number of retries attempted
    duration_ms: float                 # Optional: execution time in milliseconds


class CitationEntry(TypedDict, total=False):
    """Structured citation entry.

    Per Constitution P1: All claims require [file:line] citation.
    """
    file: str                          # Required: file path
    line: int                          # Required: line number
    context: str                       # Optional: surrounding code snippet


class SymbolInfo(TypedDict, total=False):
    """Information about a code symbol."""
    name: str                          # Required: symbol name
    kind: str                          # Required: class, function, variable, etc.
    file: str                          # Required: file path
    line: int                          # Required: line number
    signature: str                     # Optional: function signature or declaration
    docstring: str                     # Optional: documentation string
    body: str                          # Optional: full body (if requested)


class UsageInfo(TypedDict, total=False):
    """Information about symbol usage."""
    file: str                          # Required: file where used
    line: int                          # Required: line number
    match: str                         # Required: matched text
    context: str                       # Optional: surrounding context


class GrepMatch(TypedDict, total=False):
    """Single grep match result."""
    file: str                          # Required: file path
    line: int                          # Required: line number
    match: str                         # Required: matched text
    context: str                       # Optional: surrounding lines


class SemanticResult(TypedDict, total=False):
    """Single semantic search result."""
    file: str                          # Required: file path
    score: float                       # Required: similarity score (0-1)
    chunk: str                         # Optional: matched text chunk
    line: int                          # Optional: starting line number


class RelatedFile(TypedDict, total=False):
    """Related file entry."""
    file: str                          # Required: file path
    relevance: str                     # Required: why it's related


# ═══════════════════════════════════════════════════════════════════════════════
# BASE TOOL RESULT (All tools extend this)
# ═══════════════════════════════════════════════════════════════════════════════

class BaseToolResult(TypedDict, total=False):
    """Base schema all tool results share.

    Required fields (enforced by validation):
    - status: ToolResultStatus
    - citations: List[str] (can be empty)

    Optional but encouraged:
    - message: Human-readable summary
    - bounded: Whether results were truncated
    """
    status: ToolResultStatus           # Required: success, partial, not_found, error
    citations: List[str]               # Required: [file:line] references (can be empty)
    message: str                       # Optional: human-readable summary
    bounded: bool                      # Optional: whether results were truncated
    error: str                         # Optional: error message on failure


# ═══════════════════════════════════════════════════════════════════════════════
# BASE TOOLS (Internal, used by composite/resilient tools)
# ═══════════════════════════════════════════════════════════════════════════════

class FileListResult(TypedDict, total=False):
    """Result from glob_files, list_files.

    NORMALIZATION: `files` is ALWAYS a list, `file_count` is the count.
    """
    status: ToolResultStatus
    files: List[str]                   # ALWAYS a list of file paths
    file_count: int                    # Count of files (redundant but explicit)
    pattern: str                       # Pattern used (for glob)
    truncated: bool                    # Whether list was truncated
    citations: List[str]
    message: str


class TreeStructureResult(TypedDict, total=False):
    """Result from tree_structure."""
    status: ToolResultStatus
    path: str                          # Root path
    tree: str                          # Tree string representation
    file_count: int                    # Number of files
    dir_count: int                     # Number of directories
    depth: int                         # Depth traversed
    truncated: bool                    # Whether truncated
    citations: List[str]
    message: str


class SymbolSearchResult(TypedDict, total=False):
    """Result from find_symbol, get_file_symbols."""
    status: ToolResultStatus
    symbols: List[SymbolInfo]          # Found symbols
    symbol_count: int                  # Count of symbols
    query: str                         # Search query
    exact: bool                        # Whether exact match was used
    citations: List[str]
    message: str


class GrepSearchResult(TypedDict, total=False):
    """Result from grep_search."""
    status: ToolResultStatus
    matches: List[GrepMatch]           # Found matches
    match_count: int                   # Total matches found
    pattern: str                       # Search pattern
    case_sensitive: bool               # Whether case-sensitive
    truncated: bool                    # Whether results truncated
    citations: List[str]
    message: str


class SemanticSearchResult(TypedDict, total=False):
    """Result from semantic_search, find_similar_files."""
    status: ToolResultStatus
    results: List[SemanticResult]      # Search results
    result_count: int                  # Total results
    query: str                         # Search query
    threshold: float                   # Similarity threshold used
    citations: List[str]
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE TOOLS (Exposed to agents, MUST have attempt_history)
# ═══════════════════════════════════════════════════════════════════════════════

class LocateResult(TypedDict, total=False):
    """Result from locate tool.

    Composite tool: MUST include attempt_history.
    """
    status: ToolResultStatus
    query: str                         # Search query
    scope_used: str                    # Scope that was searched
    results: List[Dict[str, Any]]      # Found results (symbols, matches, etc.)
    result_count: int                  # Number of results
    found_via: str                     # Which strategy succeeded
    attempt_history: List[AttemptHistoryEntry]  # REQUIRED for composite
    citations: List[str]
    suggestions: List[str]             # Suggestions on failure
    bounded: bool
    message: str


class SymbolExplorerResult(TypedDict, total=False):
    """Result from explore_symbol_usage tool.

    Composite tool: MUST include attempt_history.
    """
    status: ToolResultStatus
    symbol: str                        # Symbol searched
    definition: Optional[SymbolInfo]   # Primary definition (first found)
    definitions: List[SymbolInfo]      # All definitions
    usages: List[UsageInfo]            # Usage locations
    usage_count: int                   # Number of usages
    importers: List[str]               # Files that import this symbol
    call_graph: Dict[str, List[str]]   # Symbol -> [file:line] call sites
    attempt_history: List[AttemptHistoryEntry]  # REQUIRED for composite
    citations: List[str]
    bounded: bool
    message: str


class ModuleMapResult(TypedDict, total=False):
    """Result from map_module tool.

    Composite tool: MUST include attempt_history.

    NORMALIZATION:
    - `files` is the count (int) - DEPRECATED, use file_count
    - `file_list` is the actual list of files
    - `file_count` is the normalized count field
    """
    status: ToolResultStatus
    module: str                        # Module path
    # File information - NORMALIZED
    file_list: List[str]               # ALWAYS a list of files (may be truncated)
    file_count: int                    # Total count of files
    dir_count: int                     # Number of directories
    tree: Optional[str]                # Tree structure (if detailed)
    # Symbol information
    symbols: Dict[str, List[str]]      # Category -> [symbol names]
    symbol_count: int                  # Total symbols
    # Dependency information
    internal_deps: Union[Dict[str, List[str]], List[str]]  # Internal dependencies
    external_deps: List[str]           # External dependencies
    consumers: List[str]               # Files that import this module
    consumer_count: int                # Number of consumers
    dep_graph: Dict[str, List[str]]    # Dependency graph
    # Metadata
    responsibilities: List[str]        # Inferred responsibilities
    attempt_history: List[AttemptHistoryEntry]  # REQUIRED for composite
    citations: List[str]
    bounded: bool
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# RESILIENT TOOLS (Exposed to agents, MUST have attempt_history)
# ═══════════════════════════════════════════════════════════════════════════════

class ReadCodeResult(TypedDict, total=False):
    """Result from read_code tool.

    Resilient tool: MUST include attempt_history.
    """
    status: ToolResultStatus
    path: str                          # Requested path
    resolved_path: str                 # Actual path read (may differ)
    content: str                       # File content
    start_line: int                    # Starting line (1-indexed)
    end_line: int                      # Ending line
    lines_returned: int                # Number of lines
    total_lines: int                   # Total lines in file
    attempt_history: List[AttemptHistoryEntry]  # REQUIRED for resilient
    citations: List[str]
    suggestions: List[str]             # Alternative paths on failure
    message: str


class FindRelatedResult(TypedDict, total=False):
    """Result from find_related tool.

    Resilient tool: MUST include attempt_history.
    """
    status: ToolResultStatus
    reference: str                     # Reference searched for
    related_files: List[RelatedFile]   # Found related files
    result_count: int                  # Number of results
    found_via: str                     # Which strategy succeeded
    attempt_history: List[AttemptHistoryEntry]  # REQUIRED for resilient
    citations: List[str]
    message: str

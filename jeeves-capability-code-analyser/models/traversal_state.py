"""TraversalState for code analysis - extends WorkingMemory.

This is the code-analysis specific state model that extends the generic
WorkingMemory from jeeves_core_engine with code-specific fields.

Part of the code_analysis vertical - NOT part of core.
"""

from pydantic import Field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# Constitutional imports - from mission_system contracts layer
from jeeves_mission_system.contracts import WorkingMemory


class CodeSnippet:
    """A relevant code snippet found during traversal."""

    def __init__(
        self,
        file: str,
        start_line: int,
        end_line: int,
        content: str,
        relevance: str,
        tokens: int = 0
    ):
        self.file = file
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.relevance = relevance
        self.tokens = tokens or len(content) // 4

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "relevance": self.relevance,
            "tokens": self.tokens,
        }


class CallChainEntry:
    """An entry in the call chain being traced."""

    def __init__(self, caller: str, callee: str, file: str, line: int):
        self.caller = caller
        self.callee = callee
        self.file = file
        self.line = line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "caller": self.caller,
            "callee": self.callee,
            "file": self.file,
            "line": self.line,
        }


# Default bounds for code analysis (can be overridden via injection)
DEFAULT_CODE_BOUNDS = {
    "max_explored_files": 100,
    "max_explored_symbols": 200,
    "max_pending_files": 50,
    "max_relevant_snippets": 50,
    "max_call_chain_length": 20,
}


class TraversalState(WorkingMemory):
    """Working memory state for code traversal.

    Extends WorkingMemory with code-analysis specific fields:
    - explored_files, explored_symbols (specialization of explored_items)
    - relevant_snippets, call_chain (specialization of findings)
    - detected_languages, repo_patterns (code-specific metadata)

    Bounds are injected via constructor or passed to add_* methods,
    NOT imported from config modules.
    """

    # ─── Code-Specific Exploration Tracking ───
    explored_files: List[str] = Field(
        default_factory=list,
        description="Files already examined in this session"
    )
    explored_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols already looked up"
    )
    pending_files: List[str] = Field(
        default_factory=list,
        description="Files queued for examination"
    )
    pending_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols queued for lookup"
    )

    # ─── Code-Specific Findings ───
    relevant_snippets: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Code snippets relevant to the query"
    )
    call_chain: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Call chain being traced"
    )

    # ─── Code-Specific Metadata ───
    detected_languages: List[str] = Field(
        default_factory=list,
        description="Programming languages detected in repo"
    )
    repo_patterns: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detected patterns (architecture, test style, etc.)"
    )

    scope_path: Optional[str] = Field(
        default=None,
        description="Path scope for this query (e.g., 'agents/', 'tools/')"
    )

    # Injected bounds (no global import)
    _bounds: Dict[str, int] = {}

    def __init__(self, bounds: Optional[Dict[str, int]] = None, **data):
        """Initialize TraversalState.

        Args:
            bounds: Optional bounds dict. If not provided, uses DEFAULT_CODE_BOUNDS.
            **data: Other Pydantic fields
        """
        super().__init__(**data)
        self._bounds = bounds or DEFAULT_CODE_BOUNDS.copy()

    def add_explored_file(self, file_path: str, max_files: Optional[int] = None) -> None:
        """Mark a file as explored.

        Args:
            file_path: File to mark as explored
            max_files: Override for max files (uses injected bounds if not provided)
        """
        max_items = max_files or self._bounds.get("max_explored_files", 100)

        if file_path not in self.explored_files:
            while len(self.explored_files) >= max_items:
                self.explored_files.pop(0)
            self.explored_files.append(file_path)

        # Also track in generic explored_items for base class compatibility
        self.add_explored(file_path, max_items=max_items)

        # Remove from pending if present
        if file_path in self.pending_files:
            self.pending_files.remove(file_path)

    def add_explored_symbol(self, symbol: str, max_symbols: Optional[int] = None) -> None:
        """Mark a symbol as explored.

        Args:
            symbol: Symbol to mark as explored
            max_symbols: Override for max symbols
        """
        max_items = max_symbols or self._bounds.get("max_explored_symbols", 200)

        if symbol not in self.explored_symbols:
            while len(self.explored_symbols) >= max_items:
                self.explored_symbols.pop(0)
            self.explored_symbols.append(symbol)

        # Remove from pending if present
        if symbol in self.pending_symbols:
            self.pending_symbols.remove(symbol)

    def add_pending_file(self, file_path: str, max_pending: Optional[int] = None) -> None:
        """Add file to exploration queue.

        Args:
            file_path: File to queue
            max_pending: Override for max pending files
        """
        max_items = max_pending or self._bounds.get("max_pending_files", 50)

        if file_path not in self.explored_files and file_path not in self.pending_files:
            while len(self.pending_files) >= max_items:
                self.pending_files.pop(0)
            self.pending_files.append(file_path)

        # Also track in generic pending_items for base class compatibility
        self.add_pending(file_path, max_items=max_items)

    def add_pending_symbol(self, symbol: str) -> None:
        """Add symbol to lookup queue."""
        if symbol not in self.explored_symbols and symbol not in self.pending_symbols:
            self.pending_symbols.append(symbol)

    def add_snippet(
        self,
        file: str,
        start_line: int,
        end_line: int,
        content: str,
        relevance: str,
        max_snippets: Optional[int] = None,
    ) -> None:
        """Add a relevant code snippet.

        Args:
            file: File path
            start_line: Starting line number
            end_line: Ending line number
            content: Code content
            relevance: Why this snippet is relevant
            max_snippets: Override for max snippets
        """
        max_items = max_snippets or self._bounds.get("max_relevant_snippets", 50)

        snippet = {
            "file": file,
            "start_line": start_line,
            "end_line": end_line,
            "content": content,
            "relevance": relevance,
            "tokens": len(content) // 4,
        }

        while len(self.relevant_snippets) >= max_items:
            removed = self.relevant_snippets.pop(0)
            self.tokens_used -= removed.get("tokens", 0)

        self.relevant_snippets.append(snippet)
        self.tokens_used += snippet["tokens"]

        # Also add as generic finding for base class compatibility
        self.add_finding(
            location=f"{file}:{start_line}-{end_line}",
            content=content,
            relevance=relevance,
            max_findings=max_items,
        )

    def add_call_chain_entry(
        self,
        caller: str,
        callee: str,
        file: str,
        line: int,
        max_chain: Optional[int] = None,
    ) -> None:
        """Add an entry to the call chain.

        Args:
            caller: Caller function/method name
            callee: Called function/method name
            file: File where call occurs
            line: Line number of call
            max_chain: Override for max chain length
        """
        max_items = max_chain or self._bounds.get("max_call_chain_length", 20)

        entry = {
            "caller": caller,
            "callee": callee,
            "file": file,
            "line": line,
        }

        while len(self.call_chain) >= max_items:
            self.call_chain.pop(0)

        self.call_chain.append(entry)

    def get_exploration_summary(self) -> str:
        """Get a summary of exploration progress."""
        return (
            f"Explored: {len(self.explored_files)} files, {len(self.explored_symbols)} symbols. "
            f"Pending: {len(self.pending_files)} files, {len(self.pending_symbols)} symbols. "
            f"Found: {len(self.relevant_snippets)} snippets, {len(self.call_chain)} call chain entries. "
            f"Tokens: ~{self.tokens_used}. Loop: {self.current_loop}."
        )

    def reset_for_new_query(self, query_intent: str = "") -> None:
        """Reset state for a new query while keeping session context."""
        super().reset_for_new_query(query_intent)
        self.pending_files = []
        self.pending_symbols = []
        self.relevant_snippets = []
        self.call_chain = []

    @classmethod
    def from_dict(cls, data: Dict[str, Any], bounds: Optional[Dict[str, int]] = None) -> "TraversalState":
        """Create from dictionary.

        Args:
            data: State data
            bounds: Optional bounds to inject

        Returns:
            TraversalState instance
        """
        return cls(bounds=bounds, **data)

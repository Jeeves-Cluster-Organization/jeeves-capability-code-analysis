"""
Code Analysis Tool Result Contracts.

This module defines typed contracts for code-analysis tool results.
It's the single source of truth for tool result shapes in this capability.

Design Principles:
- Contract-first: Define the schema, then normalize tools to match
- TypedDict over Pydantic: Lightweight, dict-compatible, good IDE support
- Capability-owned: Contracts belong to the capability, not platform

Usage:
    from jeeves_capability_code_analyser.contracts import (
        FileListResult,
        SymbolSearchResult,
        validate_tool_result,
        TOOL_RESULT_SCHEMAS,
    )

    # Validate a tool result
    issues = validate_tool_result("glob_files", result_dict)
    if issues:
        logger.warning("tool_result_validation_failed", issues=issues)

Constitutional Compliance:
- P1 (Accuracy First): All results include citations list
- Amendment XVII: Composite tools MUST return attempt_history
- Amendment XIX: Bounded retry with documented strategies
"""

from .schemas import (
    # Base types
    AttemptHistoryEntry,
    CitationEntry,
    # Tool result schemas
    BaseToolResult,
    FileListResult,
    SymbolSearchResult,
    GrepSearchResult,
    SemanticSearchResult,
    ModuleMapResult,
    SymbolExplorerResult,
    LocateResult,
    ReadCodeResult,
    FindRelatedResult,
    TreeStructureResult,
    # Utilities
    ToolResultStatus,
)

from .registry import (
    TOOL_RESULT_SCHEMAS,
    get_schema_for_tool,
    is_composite_tool,
    COMPOSITE_TOOLS,
)

from .validation import (
    validate_tool_result,
    validate_and_log,
    ToolResultValidationIssue,
    ValidationSeverity,
)

__all__ = [
    # Base types
    "AttemptHistoryEntry",
    "CitationEntry",
    # Tool result schemas
    "BaseToolResult",
    "FileListResult",
    "SymbolSearchResult",
    "GrepSearchResult",
    "SemanticSearchResult",
    "ModuleMapResult",
    "SymbolExplorerResult",
    "LocateResult",
    "ReadCodeResult",
    "FindRelatedResult",
    "TreeStructureResult",
    # Utilities
    "ToolResultStatus",
    # Registry
    "TOOL_RESULT_SCHEMAS",
    "get_schema_for_tool",
    "is_composite_tool",
    "COMPOSITE_TOOLS",
    # Validation
    "validate_tool_result",
    "validate_and_log",
    "ToolResultValidationIssue",
    "ValidationSeverity",
]

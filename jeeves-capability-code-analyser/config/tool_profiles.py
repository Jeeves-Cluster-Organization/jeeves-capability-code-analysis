"""
Operation-Tool Profiles for Code Analysis.

This module defines the mapping from (Operation, TargetKind) pairs
to ordered lists of appropriate tools. This constrains the Planner
to select semantically valid tools for each query type.

Design Principles:
- Capability-specific (not generic across all Jeeves capabilities)
- Typed with enums (no string matching)
- Ordered tool lists (first = preferred)
- Explicit fallback chains
"""

from typing import Dict, List, Tuple, Optional
from models.types import Operation, TargetKind


# ═══════════════════════════════════════════════════════════════════
# TOOL PROFILES: (Operation, TargetKind) → [tools]
# ═══════════════════════════════════════════════════════════════════

# Maps (operation, target_kind) to ordered list of appropriate tools.
# First tool is preferred; subsequent tools are fallbacks.
TOOL_PROFILES: Dict[Tuple[Operation, TargetKind], List[str]] = {
    # ─── EXPLAIN operation ───
    # "Explain what this code does"
    (Operation.EXPLAIN, TargetKind.FILE): [
        "read_code",           # Read the file content
    ],
    (Operation.EXPLAIN, TargetKind.SYMBOL): [
        "explore_symbol_usage",  # Find definition + usages
        "locate",                # Fallback: find where it's defined
    ],
    (Operation.EXPLAIN, TargetKind.MODULE): [
        "map_module",          # Get module structure
        "read_code",           # Then read key files
    ],
    (Operation.EXPLAIN, TargetKind.DIRECTORY): [
        "map_module",          # Get directory structure
    ],
    (Operation.EXPLAIN, TargetKind.ENTRY_POINT): [
        "trace_entry_point",   # Trace from entry to implementation
    ],
    (Operation.EXPLAIN, TargetKind.REPOSITORY): [
        "map_module",          # Start with repo structure
        "read_code",           # Then read key files
    ],

    # ─── TRACE operation ───
    # "How does data flow through this?"
    (Operation.TRACE, TargetKind.SYMBOL): [
        "explore_symbol_usage",  # Find all usages
    ],
    (Operation.TRACE, TargetKind.ENTRY_POINT): [
        "trace_entry_point",   # HTTP/CLI → implementation
    ],
    (Operation.TRACE, TargetKind.FILE): [
        "explore_symbol_usage",  # Trace exports from file
        "map_module",            # See what imports it
    ],
    (Operation.TRACE, TargetKind.MODULE): [
        "map_module",          # Get dependencies
        "explore_symbol_usage",  # Trace key exports
    ],

    # ─── FIND operation ───
    # "Where is X defined?"
    (Operation.FIND, TargetKind.SYMBOL): [
        "locate",              # Symbol → grep → semantic fallback
    ],
    (Operation.FIND, TargetKind.FILE): [
        "read_code",           # Just read it if we have the path
        "locate",              # Otherwise search for it
    ],
    (Operation.FIND, TargetKind.UNKNOWN): [
        "locate",              # Generic search
        "find_related",        # Semantic fallback
    ],

    # ─── MAP operation ───
    # "Show me the structure"
    (Operation.MAP, TargetKind.MODULE): [
        "map_module",
    ],
    (Operation.MAP, TargetKind.DIRECTORY): [
        "map_module",
    ],
    (Operation.MAP, TargetKind.REPOSITORY): [
        "map_module",
    ],
    (Operation.MAP, TargetKind.FILE): [
        "read_code",           # For single file, just read it
    ],

    # ─── HISTORY operation ───
    # "What changed? Who wrote this?"
    (Operation.HISTORY, TargetKind.FILE): [
        "explain_code_history",
    ],
    (Operation.HISTORY, TargetKind.SYMBOL): [
        "explain_code_history",
        "explore_symbol_usage",  # Find file first, then history
    ],
    (Operation.HISTORY, TargetKind.REPOSITORY): [
        "explain_code_history",
        "git_status",
    ],
}


# Default tools when no specific profile matches
DEFAULT_TOOLS: List[str] = ["locate", "read_code"]


# ═══════════════════════════════════════════════════════════════════
# PROFILE LOOKUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_tools_for_operation(
    operation: Operation,
    target_kind: TargetKind
) -> List[str]:
    """Get ordered tool list for an (operation, target_kind) pair.

    Args:
        operation: The operation to perform
        target_kind: The type of target

    Returns:
        Ordered list of tool names (first = preferred)
    """
    key = (operation, target_kind)
    if key in TOOL_PROFILES:
        return TOOL_PROFILES[key].copy()

    # Try with UNKNOWN target as fallback
    fallback_key = (operation, TargetKind.UNKNOWN)
    if fallback_key in TOOL_PROFILES:
        return TOOL_PROFILES[fallback_key].copy()

    return DEFAULT_TOOLS.copy()


def get_primary_tool(
    operation: Operation,
    target_kind: TargetKind
) -> str:
    """Get the preferred tool for an (operation, target_kind) pair.

    Args:
        operation: The operation to perform
        target_kind: The type of target

    Returns:
        Name of the preferred tool
    """
    tools = get_tools_for_operation(operation, target_kind)
    return tools[0] if tools else "locate"


def validate_tool_for_operation(
    tool_name: str,
    operation: Operation,
    target_kind: TargetKind
) -> Tuple[bool, Optional[str]]:
    """Check if a tool is appropriate for an (operation, target_kind).

    Args:
        tool_name: The tool being checked
        operation: The intended operation
        target_kind: The type of target

    Returns:
        Tuple of (is_valid, suggested_alternative)
    """
    valid_tools = get_tools_for_operation(operation, target_kind)

    if tool_name in valid_tools:
        return True, None

    # Tool not in profile - suggest the primary tool
    suggested = get_primary_tool(operation, target_kind)
    return False, suggested


# ═══════════════════════════════════════════════════════════════════
# SEMANTIC VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════

def infer_target_kind_from_input(value: str) -> TargetKind:
    """Infer target kind from a parameter value.

    Used to detect semantic misuse (e.g., file path passed as symbol).

    Args:
        value: The parameter value to analyze

    Returns:
        Inferred TargetKind
    """
    if not value:
        return TargetKind.UNKNOWN

    # File indicators
    if value.endswith('.py') or value.endswith('.ts') or value.endswith('.js'):
        return TargetKind.FILE
    if value.endswith('.md') or value.endswith('.json') or value.endswith('.yaml'):
        return TargetKind.FILE

    # Path indicators
    if '/' in value or '\\' in value:
        if value.endswith('/'):
            return TargetKind.DIRECTORY
        # Could be file or directory - check extension
        if '.' in value.split('/')[-1]:
            return TargetKind.FILE
        return TargetKind.DIRECTORY

    # Module indicators (dots but no slashes)
    if '.' in value and '/' not in value:
        return TargetKind.MODULE

    # Likely a symbol (PascalCase or snake_case, no path separators)
    return TargetKind.SYMBOL


def detect_semantic_mismatch(
    tool_name: str,
    param_name: str,
    param_value: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Detect if a parameter value is semantically wrong for a tool.

    Args:
        tool_name: The tool being called
        param_name: The parameter name
        param_value: The parameter value

    Returns:
        Tuple of (is_mismatch, reason, suggested_tool)
    """
    inferred_kind = infer_target_kind_from_input(param_value)

    # explore_symbol_usage expects symbols, not files
    if tool_name == "explore_symbol_usage":
        if param_name == "symbol_name" and inferred_kind in (TargetKind.FILE, TargetKind.DIRECTORY):
            return (
                True,
                f"'{param_value}' appears to be a {inferred_kind.value}, not a symbol name",
                "read_code" if inferred_kind == TargetKind.FILE else "map_module"
            )

    # map_module expects directories/modules, not single files
    if tool_name == "map_module":
        if param_name == "module_path" and inferred_kind == TargetKind.FILE:
            return (
                True,
                f"'{param_value}' is a single file, not a module/directory",
                "read_code"
            )

    # locate expects symbols, not full file paths
    if tool_name == "locate":
        if param_name == "symbol" and inferred_kind == TargetKind.FILE:
            return (
                True,
                f"'{param_value}' is a file path. Use read_code to read files directly.",
                "read_code"
            )

    return False, None, None


# ═══════════════════════════════════════════════════════════════════
# TOOL METADATA (for Planner context)
# ═══════════════════════════════════════════════════════════════════

TOOL_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
    "read_code": {
        "accepts": "file path",
        "returns": "file content with line numbers",
        "use_when": "you know the exact file to read",
    },
    "locate": {
        "accepts": "symbol name (class, function, variable)",
        "returns": "file:line locations where symbol is defined/used",
        "use_when": "searching for where something is defined",
    },
    "explore_symbol_usage": {
        "accepts": "symbol name (class, function, variable)",
        "returns": "definition location + all usage locations",
        "use_when": "understanding how a symbol is used across the codebase",
    },
    "map_module": {
        "accepts": "directory/module path",
        "returns": "file structure, exports, dependencies",
        "use_when": "understanding module/package structure",
    },
    "trace_entry_point": {
        "accepts": "entry point identifier (route, command)",
        "returns": "call chain from entry to implementation",
        "use_when": "tracing HTTP routes or CLI commands",
    },
    "find_related": {
        "accepts": "description or code snippet",
        "returns": "semantically similar files",
        "use_when": "finding related code without exact names",
    },
    "explain_code_history": {
        "accepts": "file path",
        "returns": "git history narrative",
        "use_when": "understanding who changed what and why",
    },
    "git_status": {
        "accepts": "nothing",
        "returns": "current repository state",
        "use_when": "checking uncommitted changes",
    },
    "list_tools": {
        "accepts": "nothing",
        "returns": "available tools and descriptions",
        "use_when": "discovering what tools are available",
    },
}


def get_tool_guidance(tool_name: str) -> Optional[Dict[str, str]]:
    """Get usage guidance for a tool.

    Args:
        tool_name: The tool to get guidance for

    Returns:
        Dict with accepts/returns/use_when, or None
    """
    return TOOL_DESCRIPTIONS.get(tool_name)

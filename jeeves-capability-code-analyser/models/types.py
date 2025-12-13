"""
Capability-specific types for Code Analysis.

This module defines strict types for the code analysis pipeline,
ensuring type safety and preventing semantic misuse of tools.

Design Principles:
- Enums over strings for closed sets
- Pydantic models for validated data shapes
- Capability-specific (not generic core types)
- Use OperationStatus from jeeves_protocols for tool results
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from jeeves_protocols import OperationStatus


# ═══════════════════════════════════════════════════════════════════
# TARGET CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════

class TargetKind(str, Enum):
    """Classification of what the user is asking about.

    Used by Perception to structure observations and by Planner
    to select appropriate tools.
    """
    FILE = "file"                 # Single file: "protocols.py"
    DIRECTORY = "directory"       # Directory/folder: "agents/"
    SYMBOL = "symbol"             # Code symbol: "CoreEnvelope", "process"
    MODULE = "module"             # Logical module: "agents", "tools.base"
    ENTRY_POINT = "entry_point"   # HTTP route, CLI command, main()
    REPOSITORY = "repository"     # Whole repo scope
    UNKNOWN = "unknown"           # Could not classify


class Operation(str, Enum):
    """High-level operation the user wants to perform.

    Maps to tool selection profiles.
    """
    EXPLAIN = "explain"           # Understand what code does
    TRACE = "trace"               # Follow execution/data flow
    FIND = "find"                 # Locate code by name/pattern
    MAP = "map"                   # Get structure overview
    COMPARE = "compare"           # Diff/compare code
    HISTORY = "history"           # Git history analysis


# ═══════════════════════════════════════════════════════════════════
# TOOL EXECUTION TYPES
# ═══════════════════════════════════════════════════════════════════


class ToolResult(BaseModel):
    """Consistent shape for all tool execution results.

    Every tool must return data conforming to this shape.
    Uses OperationStatus from jeeves_protocols for status codes.
    """
    status: OperationStatus
    tool_name: str

    # Data payload (structure varies by tool)
    data: Dict[str, Any] = Field(default_factory=dict)

    # Evidence metrics (for Synthesizer/Critic gates)
    evidence_chars: int = Field(
        default=0,
        description="Character count of actual code evidence"
    )
    evidence_items: int = Field(
        default=0,
        description="Count of discrete evidence items (symbols, matches, etc.)"
    )

    # Error/suggestion info
    message: Optional[str] = Field(
        default=None,
        description="Human-readable status message"
    )
    error: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Error details if status is ERROR"
    )
    suggested_tool: Optional[str] = Field(
        default=None,
        description="Suggested alternative tool (for INVALID_PARAMETERS)"
    )
    suggested_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Suggested parameters for alternative tool"
    )

    # Execution metadata
    execution_time_ms: int = Field(default=0)

    def has_meaningful_evidence(self, min_chars: int = 100, min_items: int = 1) -> bool:
        """Check if result contains sufficient evidence."""
        return self.evidence_chars >= min_chars or self.evidence_items >= min_items

    def is_actionable_failure(self) -> bool:
        """Check if this is a failure that should trigger replanning."""
        return self.status in (OperationStatus.ERROR, OperationStatus.INVALID_PARAMETERS)


# ═══════════════════════════════════════════════════════════════════
# PERCEPTION OUTPUT TYPES
# ═══════════════════════════════════════════════════════════════════

class Observation(BaseModel):
    """Structured observation from Perception agent.

    Replaces free-form scope detection with typed classification.
    """
    target_kind: TargetKind
    target_id: Optional[str] = Field(
        default=None,
        description="Specific identifier: file path, symbol name, etc."
    )
    operation_hint: Optional[Operation] = Field(
        default=None,
        description="Detected operation from query phrasing"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in this classification"
    )
    raw_match: Optional[str] = Field(
        default=None,
        description="Original text that was classified"
    )


class PerceptionObservations(BaseModel):
    """Collection of observations from Perception.

    A query may reference multiple targets.
    """
    primary: Optional[Observation] = Field(
        default=None,
        description="Main target of the query"
    )
    secondary: List[Observation] = Field(
        default_factory=list,
        description="Additional referenced targets"
    )
    detected_languages: List[str] = Field(
        default_factory=list,
        description="Programming languages mentioned or detected"
    )

    def get_primary_kind(self) -> TargetKind:
        """Get primary target kind, defaulting to REPOSITORY."""
        if self.primary:
            return self.primary.target_kind
        return TargetKind.REPOSITORY

    def get_primary_id(self) -> Optional[str]:
        """Get primary target identifier."""
        if self.primary:
            return self.primary.target_id
        return None


# ═══════════════════════════════════════════════════════════════════
# INTENT OUTPUT TYPES
# ═══════════════════════════════════════════════════════════════════

class StructuredGoal(BaseModel):
    """A goal with explicit operation and target binding.

    Replaces free-form goal strings.
    """
    operation: Operation
    target_kind: TargetKind
    target_id: Optional[str] = None
    description: str = Field(
        description="Human-readable goal description"
    )
    success_criteria: str = Field(
        default="",
        description="What constitutes success for this goal"
    )


class IntentClassification(BaseModel):
    """Structured intent from Intent agent.

    Binds operations to targets from Perception.
    """
    primary_operation: Operation
    goals: List[StructuredGoal] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


# ═══════════════════════════════════════════════════════════════════
# EVIDENCE TYPES (for Synthesizer/Critic)
# ═══════════════════════════════════════════════════════════════════

class EvidenceItem(BaseModel):
    """A single piece of code evidence with citation."""
    citation: str = Field(
        description="file:line reference"
    )
    content: str = Field(
        description="Actual code content"
    )
    relevance: str = Field(
        default="",
        description="Why this evidence is relevant"
    )
    char_count: int = Field(default=0)

    def __init__(self, **data):
        super().__init__(**data)
        if not self.char_count:
            self.char_count = len(self.content)


class EvidenceSummary(BaseModel):
    """Aggregated evidence metrics for Critic gates."""
    items: List[EvidenceItem] = Field(default_factory=list)
    total_chars: int = Field(default=0)
    total_items: int = Field(default=0)
    files_with_evidence: List[str] = Field(default_factory=list)

    def has_sufficient_evidence(
        self,
        min_chars: int = 200,
        min_items: int = 1
    ) -> bool:
        """Check if evidence meets minimum thresholds."""
        return self.total_chars >= min_chars and self.total_items >= min_items

    def add_item(self, item: EvidenceItem) -> None:
        """Add evidence item and update totals."""
        self.items.append(item)
        self.total_chars += item.char_count
        self.total_items += 1

        # Extract file from citation
        if ':' in item.citation:
            file_path = item.citation.split(':')[0]
            if file_path not in self.files_with_evidence:
                self.files_with_evidence.append(file_path)

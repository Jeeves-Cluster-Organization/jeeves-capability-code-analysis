"""
Code Analysis Orchestration Types.

Simple data containers for orchestration results.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CodeAnalysisResult:
    """Result container for code analysis execution."""

    status: str  # "complete", "clarification_needed", "error"
    response: Optional[str] = None
    thread_id: Optional[str] = None
    clarification_question: Optional[str] = None
    error: Optional[str] = None
    envelope_id: Optional[str] = None
    request_id: Optional[str] = None
    files_examined: Optional[List[str]] = None
    citations: Optional[List[str]] = None

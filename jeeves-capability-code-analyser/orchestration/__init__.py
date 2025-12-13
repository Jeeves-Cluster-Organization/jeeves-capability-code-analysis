"""
Code Analysis Orchestration Package.

Centralized Architecture (v4.0):
- CodeAnalysisService wraps UnifiedRuntime + CODE_ANALYSIS_PIPELINE
- CodeAnalysisResult is the output container

Exports:
- CodeAnalysisService: Main service for code analysis queries
- CodeAnalysisResult: Result container
"""

from orchestration.service import CodeAnalysisService
from orchestration.types import CodeAnalysisResult

__all__ = [
    "CodeAnalysisService",
    "CodeAnalysisResult",
]

"""
Code Analysis Prompts.

This module contains prompt templates for the code analysis capability.
Prompts are registered with the mission_system PromptRegistry at startup.
"""

from .code_analysis import (
    code_analysis_perception,
    code_analysis_intent,
    code_analysis_planner,
    code_analysis_synthesizer,
    code_analysis_critic,
    code_analysis_integration,
    register_code_analysis_prompts,
)

__all__ = [
    "code_analysis_perception",
    "code_analysis_intent",
    "code_analysis_planner",
    "code_analysis_synthesizer",
    "code_analysis_critic",
    "code_analysis_integration",
    "register_code_analysis_prompts",
]

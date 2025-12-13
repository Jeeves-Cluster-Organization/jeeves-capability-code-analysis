"""Code Analysis Capability - LLM Configuration.

This module defines the LLM configurations for all agents in the code analysis
capability and registers them with the infrastructure layer at startup.

Constitutional Reference:
    - Capability Constitution R6: Domain Config Ownership
    - Avionics R3: No Domain Logic - infrastructure queries registry
    - Mission System: Domain configs OWNED by capabilities

Usage:
    # At capability startup
    from jeeves_capability_code_analyser.config.llm_config import register_code_analysis_agents

    register_code_analysis_agents()

    # Infrastructure (llm/factory.py) then queries the registry:
    config = registry.get_agent_config("planner")
    temperature = config.temperature  # 0.3
"""

from typing import Dict

from jeeves_protocols import AgentLLMConfig
from jeeves_mission_system.config.agent_profiles import (
    LLMProfile,
    ThresholdProfile,
    AgentProfile,
)


# =============================================================================
# CAPABILITY ID
# =============================================================================

CAPABILITY_ID = "code_analysis"


# =============================================================================
# CODE ANALYSIS AGENT LLM CONFIGURATIONS
# =============================================================================

CODE_ANALYSIS_AGENT_LLM_CONFIGS: Dict[str, AgentLLMConfig] = {
    # ─── Intent: LLM for classification ───
    "intent": AgentLLMConfig(
        agent_name="intent",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.3,
        max_tokens=2000,
        context_window=16384,
        timeout_seconds=120,
    ),

    # ─── Planner: LLM for plan generation ───
    "planner": AgentLLMConfig(
        agent_name="planner",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.3,
        max_tokens=2500,
        context_window=18432,
        timeout_seconds=120,
    ),

    # ─── Synthesizer: LLM for aggregation ───
    "synthesizer": AgentLLMConfig(
        agent_name="synthesizer",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.3,
        max_tokens=2000,
        context_window=18432,
        timeout_seconds=120,
    ),

    # ─── Critic: LLM for validation ───
    "critic": AgentLLMConfig(
        agent_name="critic",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.2,  # Lower for consistency
        max_tokens=1500,
        context_window=18432,
        timeout_seconds=120,
    ),

    # ─── Integration: LLM for response formatting ───
    "integration": AgentLLMConfig(
        agent_name="integration",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.3,
        max_tokens=2000,
        context_window=16384,
        timeout_seconds=60,
    ),

    # ─── Validator (legacy name, still used) ───
    "validator": AgentLLMConfig(
        agent_name="validator",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.3,
        max_tokens=2000,
        context_window=16384,
        timeout_seconds=120,
    ),

    # ─── Meta-validator ───
    "meta_validator": AgentLLMConfig(
        agent_name="meta_validator",
        model="qwen2.5-7b-instruct-q4_k_m",
        temperature=0.7,  # Higher for creativity in corrections
        max_tokens=3000,
        context_window=18432,
        timeout_seconds=120,
    ),
}


# =============================================================================
# CODE ANALYSIS AGENT PROFILES (Full configuration)
# =============================================================================

CODE_ANALYSIS_AGENT_PROFILES: Dict[str, AgentProfile] = {
    # ─── Perception: No LLM, fast service calls ───
    "perception": AgentProfile(
        role="perception",
        llm=None,
        latency_budget_ms=5000,
    ),

    # ─── Intent: LLM for classification ───
    "intent": AgentProfile(
        role="intent",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.3,
            max_tokens=2000,
            context_window=16384,
        ),
        thresholds=ThresholdProfile(
            clarification_threshold=0.7,
        ),
        latency_budget_ms=30000,
    ),

    # ─── Planner: LLM for plan generation ───
    "planner": AgentProfile(
        role="planner",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.3,
            max_tokens=2500,
            context_window=18432,
        ),
        thresholds=ThresholdProfile(
            clarification_threshold=0.7,
        ),
        latency_budget_ms=60000,
    ),

    # ─── Executor/Traverser: No LLM, tool execution ───
    "executor": AgentProfile(
        role="executor",
        llm=None,
        latency_budget_ms=60000,
    ),
    "traverser": AgentProfile(
        role="traverser",
        llm=None,
        latency_budget_ms=60000,
    ),

    # ─── Synthesizer: LLM for aggregation ───
    "synthesizer": AgentProfile(
        role="synthesizer",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.3,
            max_tokens=2000,
            context_window=18432,
        ),
        latency_budget_ms=30000,
    ),

    # ─── Critic: LLM for validation ───
    "critic": AgentProfile(
        role="critic",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.2,
            max_tokens=1500,
            context_window=18432,
        ),
        thresholds=ThresholdProfile(
            approval_threshold=0.80,
            high_confidence=0.85,
            medium_confidence=0.75,
            low_confidence=0.6,
            default_confidence=0.5,
        ),
        latency_budget_ms=30000,
    ),

    # ─── Integration: LLM for response formatting ───
    "integration": AgentProfile(
        role="integration",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.3,
            max_tokens=2000,
            context_window=16384,
        ),
        latency_budget_ms=10000,
    ),

    # ─── Validator (legacy name) ───
    "validator": AgentProfile(
        role="validator",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.3,
            max_tokens=2000,
            context_window=16384,
        ),
        thresholds=ThresholdProfile(
            approval_threshold=0.8,
        ),
        latency_budget_ms=30000,
    ),

    # ─── Meta-validator ───
    "meta_validator": AgentProfile(
        role="meta_validator",
        llm=LLMProfile(
            model_name="qwen2.5-7b-instruct-q4_k_m",
            temperature=0.7,  # Higher for creativity in corrections
            max_tokens=3000,
            context_window=18432,
        ),
        thresholds=ThresholdProfile(
            approval_threshold=0.9,
            high_confidence=0.95,
            low_confidence=0.35,
        ),
        latency_budget_ms=30000,
    ),
}


# =============================================================================
# LATENCY BUDGET DICT (for compatibility)
# =============================================================================

CODE_ANALYSIS_LATENCY_BUDGETS: Dict[str, int] = {
    role: profile.latency_budget_ms
    for role, profile in CODE_ANALYSIS_AGENT_PROFILES.items()
}


# =============================================================================
# REGISTRATION FUNCTION
# =============================================================================

def register_code_analysis_agents() -> None:
    """Register all code analysis agents with the capability registry.

    Call this at capability startup to register LLM configurations
    with the infrastructure layer.

    Example:
        # At application bootstrap
        from jeeves_capability_code_analyser.config.llm_config import (
            register_code_analysis_agents
        )
        register_code_analysis_agents()
    """
    from jeeves_avionics.capability_registry import get_capability_registry

    registry = get_capability_registry()

    for agent_name, config in CODE_ANALYSIS_AGENT_LLM_CONFIGS.items():
        registry.register(CAPABILITY_ID, agent_name, config)


# =============================================================================
# HELPER FUNCTIONS (for capability-internal use)
# =============================================================================

def get_agent_profile(role: str) -> AgentProfile:
    """Get profile for agent role.

    Args:
        role: Agent role name (e.g., "planner", "critic")

    Returns:
        AgentProfile

    Raises:
        KeyError: If role not found
    """
    if role not in CODE_ANALYSIS_AGENT_PROFILES:
        raise KeyError(f"Unknown agent role: {role}")
    return CODE_ANALYSIS_AGENT_PROFILES[role]


def get_llm_config(role: str) -> AgentLLMConfig:
    """Get LLM config for agent role.

    Args:
        role: Agent role name

    Returns:
        AgentLLMConfig

    Raises:
        KeyError: If role not found or has no LLM
    """
    if role not in CODE_ANALYSIS_AGENT_LLM_CONFIGS:
        raise KeyError(f"Agent '{role}' has no LLM configuration")
    return CODE_ANALYSIS_AGENT_LLM_CONFIGS[role]


def get_latency_budget(role: str) -> int:
    """Get latency budget in ms for agent role.

    Args:
        role: Agent role name

    Returns:
        Latency budget in milliseconds
    """
    profile = CODE_ANALYSIS_AGENT_PROFILES.get(role)
    return profile.latency_budget_ms if profile else 30000


__all__ = [
    "CAPABILITY_ID",
    "CODE_ANALYSIS_AGENT_LLM_CONFIGS",
    "CODE_ANALYSIS_AGENT_PROFILES",
    "CODE_ANALYSIS_LATENCY_BUDGETS",
    "register_code_analysis_agents",
    "get_agent_profile",
    "get_llm_config",
    "get_latency_budget",
]

"""Code Analysis Capability Configuration.

Domain-specific configuration for the code analysis vertical.
Generic config types are in jeeves_mission_system.config.

Exports:
- Language config (LanguageId, LanguageSpec, LanguageConfig)
- Tool access matrix (AgentToolAccess, TOOL_CATEGORIES)
- Pipeline modes (AGENT_MODES)
- Deployment profiles (CODE_ANALYSIS_AGENTS, PROFILES)
- Product identity (PRODUCT_NAME, etc.)
"""

from jeeves_capability_code_analyser.config.language_config import (
    LanguageId,
    LanguageSpec,
    LanguageConfig,
    LANGUAGE_SPECS,
    COMMON_EXCLUDE_DIRS,
    get_language_config,
    set_language_config,
    detect_repo_languages,
)

from jeeves_capability_code_analyser.config.tool_access import (
    AgentToolAccess,
    TOOL_CATEGORIES,
    get_agent_access,
    can_agent_use_tool,
    get_agents_for_tool,
    get_tools_by_category,
)
# Re-export ToolAccess from jeeves_protocols for convenience
from jeeves_protocols import ToolAccess

from jeeves_capability_code_analyser.config.modes import (
    AGENT_MODES,
    get_agent_mode,
    list_modes,
)

from jeeves_capability_code_analyser.config.deployment import (
    NodeProfile,
    CODE_ANALYSIS_AGENTS,
    PROFILES,
    get_deployment_mode,
    get_active_profile_names,
    get_node_for_agent,
    get_profile_for_agent,
    get_all_agents,
    get_node_summary,
    validate_configuration,
)

from jeeves_capability_code_analyser.config.identity import (
    PRODUCT_NAME,
    PRODUCT_NAME_FULL,
    PRODUCT_DESCRIPTION,
    PRODUCT_VERSION,
    PRODUCT_SERVICE_NAME,
    AGENT_ARCHITECTURE,
    AGENT_COUNT,
)

from jeeves_capability_code_analyser.config.llm_config import (
    CAPABILITY_ID,
    CODE_ANALYSIS_AGENT_LLM_CONFIGS,
    CODE_ANALYSIS_AGENT_PROFILES,
    CODE_ANALYSIS_LATENCY_BUDGETS,
    register_code_analysis_agents,
    get_agent_profile,
    get_llm_config,
    get_latency_budget,
)

__all__ = [
    # Language config
    "LanguageId",
    "LanguageSpec",
    "LanguageConfig",
    "LANGUAGE_SPECS",
    "COMMON_EXCLUDE_DIRS",
    "get_language_config",
    "set_language_config",
    "detect_repo_languages",
    # Tool access
    "ToolAccess",
    "AgentToolAccess",
    "TOOL_CATEGORIES",
    "get_agent_access",
    "can_agent_use_tool",
    "get_agents_for_tool",
    "get_tools_by_category",
    # Pipeline modes
    "AGENT_MODES",
    "get_agent_mode",
    "list_modes",
    # Deployment
    "NodeProfile",
    "CODE_ANALYSIS_AGENTS",
    "PROFILES",
    "get_deployment_mode",
    "get_active_profile_names",
    "get_node_for_agent",
    "get_profile_for_agent",
    "get_all_agents",
    "get_node_summary",
    "validate_configuration",
    # Identity
    "PRODUCT_NAME",
    "PRODUCT_NAME_FULL",
    "PRODUCT_DESCRIPTION",
    "PRODUCT_VERSION",
    "PRODUCT_SERVICE_NAME",
    "AGENT_ARCHITECTURE",
    "AGENT_COUNT",
    # LLM Configuration (capability-owned)
    "CAPABILITY_ID",
    "CODE_ANALYSIS_AGENT_LLM_CONFIGS",
    "CODE_ANALYSIS_AGENT_PROFILES",
    "CODE_ANALYSIS_LATENCY_BUDGETS",
    "register_code_analysis_agents",
    "get_agent_profile",
    "get_llm_config",
    "get_latency_budget",
]

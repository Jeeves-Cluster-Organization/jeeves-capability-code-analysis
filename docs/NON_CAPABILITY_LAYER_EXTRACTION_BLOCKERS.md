# Non-Capability Layer Extraction Blockers

**Date:** 2025-12-12
**Branch:** `claude/extract-capability-layers-01Qd8M6K9BRABaYi31fHu1ax`
**Status:** ✅ ALL BLOCKERS RESOLVED

## Executive Summary

This document originally identified **6 critical blockers** preventing the extraction of non-capability layers (L0-L4) to a separate repository. **All blockers have been resolved** in commit `b1c8b51`.

**Verdict:** The architecture is now **ready for extraction** (~95% complete).

### Resolution Summary

| Blocker | Original Issue | Resolution |
|---------|---------------|------------|
| BLOCKER 1 | Direct capability imports in server.py | ✅ Refactored to use `CapabilityResourceRegistry` |
| BLOCKER 2 | Capability contracts in platform | ✅ Moved to `jeeves-capability-code-analyser/contracts/` |
| BLOCKER 3 | Capability prompts in platform | ✅ Moved to `jeeves-capability-code-analyser/prompts/` |
| BLOCKER 4 | Hardcoded agent definitions | ✅ `get_agent_definitions()` queries registry |
| BLOCKER 5 | Hardcoded gRPC service names | ✅ Uses generic service names from registry |
| BLOCKER 6 | Test dependencies on capability | ✅ Tests use `MockOrchestratorResult` |

---

## Changes Made

### 1. Extended CapabilityResourceRegistry

**File:** `jeeves_protocols/capability.py`

Added new registration methods:
- `register_orchestrator()` / `get_orchestrator()` - Register orchestrator factory
- `register_tools()` / `get_tools()` - Register tools initializer
- `register_prompts()` / `get_prompts()` - Register prompt templates
- `register_agents()` / `get_agents()` - Register agent definitions
- `register_contracts()` / `get_contracts()` - Register tool result contracts

New config types:
- `CapabilityOrchestratorConfig` - Factory for creating orchestrator service
- `CapabilityToolsConfig` - Initializer for tools
- `CapabilityAgentConfig` - Agent definition for governance
- `CapabilityPromptConfig` - Prompt template
- `CapabilityContractsConfig` - Tool result contracts

### 2. Refactored server.py

**File:** `jeeves_mission_system/api/server.py`

Before:
```python
# sys.path hack to import capability
_app_path = Path(__file__).parent.parent.parent / "jeeves-capability-code-analyser"
sys.path.insert(0, str(_app_path))

from orchestration.service import CodeAnalysisService
from tools import initialize_all_tools, tool_catalog
```

After:
```python
# Uses registry for dynamic discovery (layer extraction support)
capability_registry = get_capability_resource_registry()

# Initialize tools via capability registry
tools_config = capability_registry.get_tools()
if tools_config:
    tool_instances = tools_config.initializer(db=db)
    catalog = tool_instances["catalog"]

# Initialize orchestrator via capability registry
orchestrator_config = capability_registry.get_orchestrator()
if orchestrator_config:
    orchestrator = orchestrator_config.factory(
        llm_provider_factory=llm_factory,
        tool_executor=tool_executor,
        ...
    )
```

### 3. Refactored governance_service.py

**File:** `jeeves_mission_system/orchestrator/governance_service.py`

Before:
```python
AGENT_DEFINITIONS = [
    {"name": "CodeAnalysisPerceptionAgent", ...},
    {"name": "CodeAnalysisIntentAgent", ...},
    ...
]
```

After:
```python
def get_agent_definitions() -> List[dict]:
    """Get agent definitions from the CapabilityResourceRegistry."""
    registry = get_capability_resource_registry()
    agent_configs = registry.get_agents()
    return [
        {"name": agent.name, "description": agent.description, ...}
        for agent in agent_configs
    ]
```

### 4. Updated capability registration.py

**File:** `jeeves-capability-code-analyser/registration.py`

Now registers all capability resources:
```python
def register_capability() -> None:
    registry = get_capability_resource_registry()

    # Existing registrations
    registry.register_schema(CAPABILITY_ID, schema_path)
    registry.register_mode(CAPABILITY_ID, mode_config)
    registry.register_service(CAPABILITY_ID, service_config)

    # NEW: Layer Extraction Support
    registry.register_orchestrator(CAPABILITY_ID, orchestrator_config)
    registry.register_tools(CAPABILITY_ID, tools_config)
    registry.register_agents(CAPABILITY_ID, _get_agent_definitions())
    register_code_analysis_prompts()
    registry.register_contracts(CAPABILITY_ID, contracts_config)
```

### 5. Moved capability-specific code

| From | To |
|------|-----|
| `jeeves_mission_system/contracts/code_analysis/` | `jeeves-capability-code-analyser/contracts/` |
| `jeeves_mission_system/prompts/core/versions/code_analysis.py` | `jeeves-capability-code-analyser/prompts/code_analysis.py` |

### 6. Updated test files

**File:** `jeeves_mission_system/tests/integration/test_api.py`

Now uses `MockOrchestratorResult` instead of importing from capability:
```python
@dataclass
class MockOrchestratorResult:
    """Mock result for orchestrator tests."""
    status: str = "complete"
    response: Optional[str] = None
    request_id: Optional[str] = None
    ...
```

---

## Extraction Readiness Assessment (Updated)

| Layer | Package | Status | Notes |
|-------|---------|--------|-------|
| L0 | `jeeves_protocols` | ✅ READY | Extended with new config types |
| L0 | `jeeves_shared` | ✅ READY | No changes needed |
| L1 | `jeeves_memory_module` | ✅ READY | No changes needed |
| L2 | `jeeves_control_tower` | ✅ READY | No changes needed |
| L3 | `jeeves_avionics` | ✅ READY | TYPE_CHECKING resolved earlier |
| L4 | `jeeves_mission_system` | ✅ READY | All blockers resolved |
| Go | `commbus/`, `coreengine/` | ✅ READY | No changes needed |

---

## Constitutional Compliance

The changes comply with the constitutional requirements:

- **Avionics R3 (No Domain Logic):** Infrastructure provides transport, not business logic
- **Avionics R4 (Swappable Implementations):** Capabilities register via `CapabilityResourceRegistry`
- **Mission System Constitution:** Domain configs OWNED by capabilities
- **Capability R7:** Capability MUST register resources at application startup

---

## Next Steps for Full Extraction

To complete the extraction to a separate repository:

1. **Create `jeeves-core-platform` repository** with:
   - `jeeves_protocols/` (L0)
   - `jeeves_shared/` (L0)
   - `jeeves_memory_module/` (L1)
   - `jeeves_control_tower/` (L2)
   - `jeeves_avionics/` (L3)
   - `jeeves_mission_system/` (L4)
   - `commbus/`, `coreengine/` (Go core)

2. **Update capability to depend on platform:**
   ```toml
   # pyproject.toml
   dependencies = [
       "jeeves-core-platform>=1.0.0",
   ]
   ```

3. **Update imports in capability:**
   ```python
   from jeeves_protocols import get_capability_resource_registry
   from jeeves_mission_system.prompts.core import register_prompt
   ```

---

## Historical Record: Original Blockers

The following blockers were identified and have all been resolved:

### BLOCKER 1: Direct Capability Imports in server.py (RESOLVED)
- **Severity:** CRITICAL
- **Resolution:** Uses `CapabilityResourceRegistry` for dynamic discovery

### BLOCKER 2: Capability-Specific Contracts in Platform Layer (RESOLVED)
- **Severity:** HIGH
- **Resolution:** Moved to `jeeves-capability-code-analyser/contracts/`

### BLOCKER 3: Capability-Specific Prompts in Platform Layer (RESOLVED)
- **Severity:** HIGH
- **Resolution:** Moved to `jeeves-capability-code-analyser/prompts/`

### BLOCKER 4: Hardcoded Agent Definitions in Governance Service (RESOLVED)
- **Severity:** MEDIUM
- **Resolution:** `get_agent_definitions()` queries registry

### BLOCKER 5: Hardcoded gRPC Service Names (RESOLVED)
- **Severity:** MEDIUM
- **Resolution:** Uses generic service names from registry

### BLOCKER 6: Test Dependencies on Capability (RESOLVED)
- **Severity:** MEDIUM
- **Resolution:** Tests use `MockOrchestratorResult`

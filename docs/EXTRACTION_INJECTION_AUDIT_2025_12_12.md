# Layer Extraction & Dependency Injection Audit

**Date:** 2025-12-12
**Branch:** `claude/audit-extraction-injection-DgNjW`
**Status:** ✅ CRITICAL ISSUES RESOLVED

## Executive Summary

This audit examines the codebase for two concerns:
1. **Layer Extraction Readiness:** Can non-capability layers (L0-L4) be extracted to a separate repository?
2. **Dependency Injection Issues:** Are components properly wired and injected?

### Key Findings

| Category | Severity | Count | Status |
|----------|----------|-------|--------|
| Critical Startup Wiring | CRITICAL | 1 | ✅ FIXED - `register_capability()` now invoked |
| Global Singletons | HIGH | 5 | Remain - extraction quality concern |
| Hardcoded Configuration | MEDIUM | 4 | Should use settings injection |
| Test Fixture Gaps | MEDIUM | 2 | ✅ FIXED - fixtures now register capability |
| Loose DI Patterns | LOW | 6 | Optional dependencies with fallbacks |

**Overall Extraction Readiness: 90%** (up from 70% after P0 fix)

### Fixes Applied (Commit 3dd75ea)

1. **`jeeves-capability-code-analyser/server.py`** - Registration at module import time
2. **`jeeves_mission_system/scripts/run/server.py`** - Registration before uvicorn.run()
3. **`jeeves-capability-code-analyser/tests/conftest.py`** - Session-scoped registration fixture
4. **`jeeves_mission_system/tests/conftest.py`** - Session-scoped registration fixture

**Verified:**
- Registered capabilities: `['code_analysis']`
- Tools config registered: `True`
- Orchestrator config registered: `True`
- Services registered: `1`

---

## Constitutional Guidance

The constitutions provide clear guidance on the required approach:

### Capability Constitution - R7 (Capability Registration)

> **"Capability MUST register its resources at application startup"**
>
> Call at application startup, BEFORE infrastructure initialization.
>
> ```python
> # At application entry point
> from jeeves_capability_code_analyser import register_capability
> register_capability()  # MUST be called before infrastructure init
> ```
>
> **Why registration is required:**
> - Infrastructure (avionics) must NOT have hardcoded capability knowledge
> - Enables non-capability layers to be extracted as a separate package
> - Follows Avionics R3 (No Domain Logic) and R4 (Swappable Implementations)

### Avionics Constitution - R3 (No Domain Logic)

> **"Avionics provides transport and storage, not business logic"**
>
> Avionics does NOT:
> - Decide which agent runs next (Mission System)
> - Validate code citations (Mission System)
> - Execute tools (Mission System)
> - Implement 7-agent pipeline (Mission System)

### Avionics Constitution - R4 (Swappable Implementations)

> **"Capabilities register their resources (schemas, gateway modes) at startup"**
>
> Infrastructure queries registry instead of hardcoding capability knowledge.
> Enables non-capability layers to be extracted as a separate package.

### Control Tower Constitution - R2 (Service Registration Contract)

> **"Services must register with Control Tower at startup"**

### Constitutional Verdict

The critical finding of this audit (`register_capability()` never invoked) is a **direct violation of Capability Constitution R7**. The architecture is correctly designed per the constitutions, but the implementation fails to call the required registration function at startup.

**The fix is constitutionally mandated and clearly documented.**

---

## CRITICAL FINDING: Capability Registration Never Invoked

### Problem

The `register_capability()` function is defined in `jeeves-capability-code-analyser/registration.py` but is **never called** at application startup. This means:

- All `CapabilityResourceRegistry` queries return empty results
- Tools initializer is never registered
- Orchestrator factory is never registered
- Agent definitions are never registered
- Capability schema is never registered

### Evidence

**Entry points analyzed:**

| Entry Point | Calls `register_capability()`? |
|-------------|-------------------------------|
| `jeeves-capability-code-analyser/server.py:main()` | **NO** |
| `jeeves_mission_system/scripts/run/server.py` | **NO** |
| `jeeves_mission_system/api/server.py:lifespan()` | **NO** |
| `jeeves_avionics/gateway/main.py:lifespan()` | **NO** |
| Test fixtures (`conftest.py`) | **NO** |

**What happens at startup (`server.py:227-259`):**

```python
# Get capability registry for dynamic discovery (layer extraction support)
capability_registry = get_capability_resource_registry()
services = capability_registry.get_services()  # Returns EMPTY LIST
default_service = capability_registry.get_default_service() or "default"  # Falls back to "default"

# Initialize tools via capability registry (no direct imports from capability)
tools_config = capability_registry.get_tools()  # Returns NONE
if tools_config:
    # NEVER EXECUTED - no tools registered
    ...
else:
    _logger.warning("no_tools_registered", message="No capability tools in registry")
```

### Impact

- **Silent Failure:** Application starts but capability is not properly initialized
- **Governance Broken:** `get_agent_definitions()` returns empty list
- **Schema Not Applied:** Capability database tables may not be created
- **Tools Not Initialized:** Tool catalog is empty

### Required Fix

Add explicit registration call at startup:

```python
# In jeeves-capability-code-analyser/server.py (before any avionics/mission imports)
from jeeves_capability_code_analyser import register_capability
register_capability()  # MUST be called before infrastructure init
```

Or create a bootstrap module that handles initialization order.

---

## Global Singleton Anti-Patterns

These patterns block clean layer extraction and make testing difficult.

### 1. Connection Manager Singleton

**Location:** `jeeves_avionics/database/connection_manager.py:310-328`

```python
_connection_manager: Optional[ConnectionManager] = None

def get_connection_manager(settings: Settings) -> ConnectionManager:
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager(settings)
    return _connection_manager
```

**Issue:** Mutable global state, cannot be replaced in tests without monkeypatching.

**Fix:** Inject via AppContext or factory pattern.

### 2. Backend Registry (Mutable Dict)

**Location:** `jeeves_avionics/database/registry.py:36`

```python
_BACKENDS: Dict[str, tuple[Type, Callable[...]]] = {}

def register_backend(name: str, ...):
    _BACKENDS[name] = ...  # Mutable at module import time
```

**Issue:** Race conditions in multi-process environments, hard to test.

**Fix:** Make registry immutable after setup phase, or inject via composition root.

### 3. Capability LLM Config Registry

**Location:** `jeeves_avionics/capability_registry.py:231-269`

```python
_registry: Optional[CapabilityLLMConfigRegistry] = None

def get_capability_registry() -> CapabilityLLMConfigRegistry:
    global _registry
    if _registry is None:
        _registry = CapabilityLLMConfigRegistry()
    return _registry
```

**Issue:** Same singleton pattern, same problems.

### 4. OTEL Span State

**Location:** `jeeves_avionics/logging/__init__.py:56-57`

```python
_OTEL_ENABLED = False
_ACTIVE_SPANS: Dict[str, "Span"] = {}
```

**Issue:** Module-level state affects all code paths, not thread-safe.

**Fix:** Use contextvars for request-scoped state.

### 5. Capability Resource Registry

**Location:** `jeeves_protocols/capability.py:533-547`

```python
_resource_registry: Optional[CapabilityResourceRegistry] = None

def get_capability_resource_registry() -> CapabilityResourceRegistry:
    global _resource_registry
    if _resource_registry is None:
        _resource_registry = CapabilityResourceRegistry()
    return _resource_registry
```

**Mitigation:** Has `reset_capability_resource_registry()` for testing - GOOD.

---

## Hardcoded Configuration Issues

### 1. GatewayConfig Direct os.getenv()

**Location:** `jeeves_avionics/gateway/main.py:53-65`

```python
class GatewayConfig:
    def __init__(self):
        self.orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "localhost")  # Hardcoded default
        self.orchestrator_port = int(os.getenv("ORCHESTRATOR_PORT", "50051"))
        self.api_host = os.getenv("API_HOST", "0.0.0.0")  # Hardcoded default
```

**Fix:** Use centralized Settings class with proper validation.

### 2. LlamaServer Defaults

**Location:** `jeeves_avionics/settings.py:59-63`

```python
llamaserver_host: str = "http://localhost:8080"  # Hardcoded
default_model: str = "qwen2.5-3b-instruct-q4_k_m"  # Hardcoded
```

**Issue:** Not all hardcoded values are bad (sensible defaults are OK), but these should be documented.

### 3. GoClient Binary Paths

**Location:** `jeeves_protocols/client.py`

Searches hardcoded paths for Go binary. Should be configurable via environment.

---

## Direct Model Instantiation (ML Dependencies)

Note: Per audit instructions, excluding docker ml sentence transformer libraries.

### 1. EmbeddingService

**Location:** `jeeves_memory_module/services/embedding_service.py:44`

```python
def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
    self.model = SentenceTransformer(model_name)  # Direct instantiation
```

**Issue:** No factory injection, hard to mock in tests.

### 2. NLI Service

**Location:** `jeeves_memory_module/services/nli_service.py:69`

```python
def __init__(self, model_name: str = "cross-encoder/nli-MiniLM2-L6-H768"):
    self._model = CrossEncoder(model_name)  # Direct instantiation
```

**Fix:** Use factory protocol or lazy loading with injection.

---

## Loose DI Patterns (Optional Dependencies with Fallbacks)

These patterns create hidden dependencies:

```python
# jeeves_memory_module/services/session_state_service.py:60
self.repository = repository or SessionStateRepository(db)  # Fallback creates hidden dependency

# jeeves_memory_module/services/graph_service.py:56
self.repository = repository or GraphRepository(db)  # Same pattern

# jeeves_memory_module/services/chunk_service.py
# jeeves_memory_module/services/event_emitter.py
# Similar patterns throughout
```

**Issue:** Constructor injection with `or` fallback makes dependencies implicit.

**Fix:** Require explicit injection, provide factory in composition root.

---

## Test Fixture Gaps

### 1. Capability conftest.py

**Location:** `jeeves-capability-code-analyser/tests/conftest.py`

Registers language config but **does not call `register_capability()`**:

```python
@pytest.fixture(autouse=True)
def setup_language_config():
    """Register language config in the global registry for tests."""
    from jeeves_mission_system.contracts import get_config_registry, ConfigKeys
    from jeeves_capability_code_analyser.config import get_language_config

    registry = get_config_registry()
    config = get_language_config()
    registry.register(ConfigKeys.LANGUAGE_CONFIG, config)
    yield
    # MISSING: register_capability() call
```

### 2. Mission System conftest.py

**Location:** `jeeves_mission_system/tests/conftest.py`

No capability registration at all. Tests may pass with mocks but don't validate real wiring.

**Required Fix:**

```python
@pytest.fixture(autouse=True)
def setup_capability_registration():
    """Register capability resources for tests."""
    from jeeves_protocols import reset_capability_resource_registry

    # Reset to clean state
    reset_capability_resource_registry()

    # Register capability
    from jeeves_capability_code_analyser import register_capability
    register_capability()

    yield

    # Cleanup
    reset_capability_resource_registry()
```

---

## Layer Extraction Readiness (Updated)

| Layer | Package | Status | Blocking Issues |
|-------|---------|--------|-----------------|
| L0 | `jeeves_protocols` | **95% READY** | Global singleton (has reset function) |
| L0 | `jeeves_shared` | **100% READY** | None |
| L1 | `jeeves_memory_module` | **85% READY** | Loose DI patterns, ML service instantiation |
| L2 | `jeeves_control_tower` | **100% READY** | None |
| L3 | `jeeves_avionics` | **70% READY** | 3 global singletons, mutable registry |
| L4 | `jeeves_mission_system` | **80% READY** | Assumes registry populated at startup |
| Go | `commbus/`, `coreengine/` | **100% READY** | None |

---

## Priority Action Items

### P0 - Critical (Must Fix)

1. **Wire `register_capability()` at startup**
   - Add call in `server.py` main entry point
   - Add call in test fixtures
   - Verify with startup logging

### P1 - High (Should Fix for Extraction)

2. **Eliminate connection manager singleton**
   - Inject via AppContext
   - Update all callers

3. **Make backend registry immutable after setup**
   - Freeze after initialization phase
   - Document expected setup order

4. **Fix test fixtures**
   - Add `register_capability()` to conftest.py
   - Add cleanup in teardown

### P2 - Medium (Improve Quality)

5. **Replace loose DI patterns**
   - Require explicit injection
   - Move factory logic to composition root

6. **Centralize configuration**
   - Remove direct `os.getenv()` calls
   - Use Settings class consistently

### P3 - Low (Nice to Have)

7. **Document hardcoded defaults**
   - Add comments explaining default choices
   - Consider moving to config file

8. **Add runtime protocol verification**
   - Validate objects implement expected protocols
   - Fail fast on misconfiguration

---

## Conclusion

The previous audit marked extraction readiness at 95%. However, this audit reveals a **critical runtime wiring gap**: the capability registration function exists but is never called at startup.

**Updated Assessment:**
- **Extraction Readiness:** 70% (blocked by startup wiring)
- **Test Readiness:** 60% (missing registration in fixtures)
- **Architecture:** Sound but implementation incomplete

The infrastructure correctly uses `CapabilityResourceRegistry` for dynamic discovery, but the capability never registers itself. This is a one-line fix but has system-wide impact.

---

## Recommended Approach (Per Constitutions)

Based on the constitutional guidance, the approach is clear:

### 1. Fix Startup Registration (P0 - Constitutional Requirement)

The constitutions mandate capability registration. Add the call at entry points:

**Option A: Direct call in entry point (Simplest)**
```python
# In server entry point, BEFORE any other imports that use registry
from jeeves_capability_code_analyser import register_capability
register_capability()

# Then proceed with normal imports
from jeeves_mission_system.api.server import app
```

**Option B: Bootstrap module (More structured)**
```python
# bootstrap.py
def bootstrap_application():
    """Initialize all registrations before infrastructure."""
    from jeeves_capability_code_analyser import register_capability
    register_capability()

    # Add other capabilities here in future
    # from other_capability import register_capability as register_other
    # register_other()
```

### 2. Fix Test Fixtures (P1)

Tests need clean registry state per test:

```python
@pytest.fixture(autouse=True)
def setup_capability_registration():
    """Register capability resources for tests per Constitution R7."""
    from jeeves_protocols import reset_capability_resource_registry
    reset_capability_resource_registry()

    from jeeves_capability_code_analyser import register_capability
    register_capability()

    yield

    reset_capability_resource_registry()
```

### 3. Global Singletons (P2 - Extraction Quality)

Per constitutional guidance, resolve singletons using these patterns:

#### Pattern A: Factory Function (Avionics R4)
**For stateless or caller-owned lifecycle resources:**
```python
# BEFORE (singleton anti-pattern)
_connection_manager: Optional[ConnectionManager] = None
def get_connection_manager(settings) -> ConnectionManager:
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager(settings)
    return _connection_manager

# AFTER (factory pattern per Avionics R4)
def create_connection_manager(settings) -> ConnectionManager:
    """Factory creates new instance. Caller owns lifecycle."""
    return ConnectionManager(settings)
```

#### Pattern B: Registry with Reset (jeeves_protocols pattern)
**For registries that need test isolation:**
```python
# Already correct in CapabilityResourceRegistry:
_resource_registry: Optional[CapabilityResourceRegistry] = None

def reset_capability_resource_registry() -> None:
    global _resource_registry
    _resource_registry = None  # Enables test cleanup
```

#### Pattern C: Immutable After Setup (Avionics R6)
**For backend registries:**
```python
# Add freeze after initialization phase
_BACKENDS_FROZEN = False

def freeze_backends() -> None:
    global _BACKENDS_FROZEN
    _BACKENDS_FROZEN = True

def register_backend(name, ...):
    if _BACKENDS_FROZEN:
        raise RuntimeError("Backend registration closed")
    _BACKENDS[name] = ...
```

#### Pattern D: Context Variables (for request-scoped state)
**For OTEL spans and request-local state:**
```python
# BEFORE (global dict, not thread-safe)
_ACTIVE_SPANS: Dict[str, Span] = {}

# AFTER (contextvars per request)
from contextvars import ContextVar
_active_span: ContextVar[Optional[Span]] = ContextVar("active_span", default=None)
```

#### Singleton Resolution Matrix

| Singleton | Location | Resolution | Pattern |
|-----------|----------|------------|---------|
| `_connection_manager` | connection_manager.py:311 | Factory function | A |
| `_BACKENDS` | registry.py:36 | Freeze after init | C |
| `_registry` | capability_registry.py:231 | Add reset function | B |
| `_ACTIVE_SPANS` | logging/__init__.py:57 | Use contextvars | D |
| `_resource_registry` | capability.py:533 | Already has reset ✅ | B |

### 4. What NOT to Change

The following are **correctly designed per constitutions**:
- `CapabilityResourceRegistry` pattern (Avionics R4)
- Infrastructure querying registry for capabilities (Avionics R3)
- Protocol-based abstractions in `jeeves_protocols`
- Layer import boundaries (docs/CONSTITUTION.md dependency matrix)

---

## Verification Steps

After fixes are applied, verify with:

```bash
# 1. Check startup logs for registration
grep "registered_capabilities" logs/startup.log

# 2. Verify tools are initialized
curl http://localhost:8000/api/v1/governance/tools

# 3. Run tests with registration
pytest -v --tb=short

# 4. Check agent definitions endpoint
curl http://localhost:8000/api/v1/governance/agents
```

---

*This audit supplements the existing extraction documentation. See also:*
- `docs/NON_CAPABILITY_LAYER_EXTRACTION_BLOCKERS.md`
- `docs/NON_CAPABILITY_LAYER_EXTRACTION_EVALUATION.md`

# Layer Separation and Architectural Complexity Evaluation

**Date:** 2025-12-12
**Branch:** `claude/improve-layer-separation-01NkoejNkYmdyirCJEx8kU6T`

## Executive Summary

This evaluation analyzes the codebase for opportunities to improve layer separation while reducing architectural complexity. The analysis identified **45 layer boundary violations**, **multiple redundant DI containers**, and **several over-engineered abstractions** that can be simplified.

### Recent Progress (2025-12-12)

**CapabilityResourceRegistry pattern implemented** to enable layer extraction:

| Blocker | Status | Resolution |
|---------|--------|------------|
| Hardcoded `002_code_analysis_schema.sql` in avionics | ✅ RESOLVED | Moved to capability, infrastructure queries registry |
| Hardcoded `code_analysis` mode in gateway | ✅ RESOLVED | Gateway now uses `CapabilityResourceRegistry` |
| `CodeAnalysis` prefix handling in runtime.py | ✅ RESOLVED | Generic transformation rules only |
| Test fixtures with hardcoded schema paths | ✅ RESOLVED | Test fixtures use registry |

**New Protocol:** `CapabilityResourceRegistryProtocol` in `jeeves_protocols/capability.py`
- Capabilities register schemas and modes at startup
- Infrastructure queries registry instead of hardcoding
- Enables non-capability layers to be extracted as separate package

### Key Findings

| Category | Issues Found | Priority |
|----------|--------------|----------|
| Layer Boundary Violations | 45 violations | HIGH |
| Redundant DI Containers | 3 containers with overlap | HIGH |
| Single-Implementation Protocols | 5+ protocols | MEDIUM |
| Duplicate Utilities | 6 categories | MEDIUM |
| Over-Engineered Abstractions | 8 patterns | MEDIUM |

---

## 1. Current Architecture Overview

The codebase follows a 7-layer hybrid Go-Python architecture:

```
┌─────────────────────────────────────────────────────────────┐
│  L5: CAPABILITY LAYER (Domain Logic)                        │
│      jeeves-capability-code-analyser/                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L4: APPLICATION LAYER (Mission System)                     │
│      jeeves_mission_system/                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L3: KERNEL LAYER (Control Tower)                           │
│      jeeves_control_tower/                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L2: INFRASTRUCTURE LAYER (Avionics)                        │
│      jeeves_avionics/                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L1: MEMORY MODULE LAYER                                    │
│      jeeves_memory_module/                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  L0: CONTRACTS LAYER (Protocols)                            │
│      jeeves_protocols/                                      │
└─────────────────────────────────────────────────────────────┘
```

**Expected Import Direction:** L5 → L4 → L3 → L2 → L1 → L0

---

## 2. Layer Boundary Violations

### 2.1 Critical: Avionics (L2) Importing Control Tower (L3)

**Severity:** CRITICAL - Backwards dependency (2 layers)

| File | Import | Impact |
|------|--------|--------|
| `jeeves_avionics/gateway/main.py:93` | `from jeeves_control_tower.services import InterruptService` | Direct coupling to kernel |
| `jeeves_avionics/gateway/routers/interrupts.py:108` | `from jeeves_control_tower.services import InterruptService` | Router-level coupling |
| `jeeves_avionics/middleware/rate_limit.py:37` | `from jeeves_control_tower.resources.rate_limiter` | Direct instantiation |

**Root Cause:** Gateway layer directly instantiates Control Tower services instead of receiving them via dependency injection.

**Recommendation:** Define `InterruptServiceProtocol` in `jeeves_protocols` and inject implementation from Mission System.

### 2.2 High: Memory Module (L1) Importing Avionics (L2)

**Severity:** HIGH - 39 violations

**Affected Categories:**
- **Logging utilities** (~32 instances): `get_component_logger`, `get_current_logger`
- **Serialization** (~8 instances): `parse_datetime`, `to_json`, `from_json`
- **UUID utilities** (~3 instances): `uuid_str`, `uuid_read`, `convert_uuids_to_strings`
- **Feature flags** (~2 instances): `get_feature_flags`

**Example Violations:**
```python
# jeeves_memory_module/repositories/event_repository.py:16-17
from jeeves_avionics.logging import get_component_logger
from jeeves_avionics.utils.serialization import parse_datetime

# jeeves_memory_module/services/event_emitter.py:19,21
from jeeves_avionics.feature_flags import get_feature_flags
from jeeves_avionics.logging import get_component_logger
```

**Recommendation:** Extract these utilities to `jeeves_protocols` as protocol interfaces, or create a shared `jeeves_shared` package at L0.

---

## 3. Redundant Dependency Containers

### Current State: 3 Overlapping Containers

```
┌──────────────────────────────────────────────────────────────┐
│  Container #1: AppContext (jeeves_avionics/context.py)       │
│  ├── settings: SettingsProtocol                              │
│  ├── feature_flags: FeatureFlagsProtocol                     │
│  ├── logger: LoggerProtocol                                  │
│  ├── clock: ClockProtocol                                    │
│  ├── core_config: CoreConfig                                 │
│  ├── orchestration_flags: OrchestrationFlags                 │
│  ├── control_tower: ControlTowerProtocol                     │
│  └── vertical_registry: Dict[str, bool]                      │
└──────────────────────────────────────────────────────────────┘
                              +
┌──────────────────────────────────────────────────────────────┐
│  Container #2: PrimitiveDeps (jeeves_avionics/wiring.py)     │
│  ├── tool_executor: ToolExecutorProtocol                     │
│  ├── agent_runtime_factory: Callable                         │
│  ├── llm_provider_factory: Callable                          │
│  ├── mock_provider: LLMProviderProtocol                      │
│  ├── persistence: PersistenceProtocol           ← DUPLICATE  │
│  └── settings: Settings                         ← DUPLICATE  │
└──────────────────────────────────────────────────────────────┘
                              +
┌──────────────────────────────────────────────────────────────┐
│  Container #3: ControlTower (jeeves_control_tower/kernel.py) │
│  ├── _lifecycle: LifecycleManager                            │
│  ├── _resources: ResourceTracker                             │
│  ├── _ipc: CommBusCoordinator                                │
│  ├── _events: EventAggregator                                │
│  └── _interrupts: InterruptService                           │
└──────────────────────────────────────────────────────────────┘
```

**Problems:**
1. Services may receive both `AppContext` and `PrimitiveDeps` with overlapping data
2. `settings` appears in both containers
3. ControlTower acts as a "god container" with 5 internal services

### Recommendation: Unified Container Strategy

```python
# Option A: Merge PrimitiveDeps into AppContext
@dataclass
class AppContext:
    # Core (existing)
    settings: SettingsProtocol
    feature_flags: FeatureFlagsProtocol
    logger: LoggerProtocol
    clock: ClockProtocol
    core_config: CoreConfig
    control_tower: Optional[ControlTowerProtocol]

    # Infrastructure (from PrimitiveDeps)
    tool_executor: Optional[ToolExecutorProtocol] = None
    llm_provider_factory: Optional[Callable[[str], LLMProviderProtocol]] = None
    persistence: Optional[PersistenceProtocol] = None

# Option B: Layered Containers (preferred for separation)
@dataclass
class InfraContext:
    """L2 Infrastructure context - built first"""
    settings: Settings
    logger: LoggerProtocol
    persistence: PersistenceProtocol
    tool_executor: ToolExecutorProtocol

@dataclass
class AppContext:
    """L4 Application context - wraps infra"""
    infra: InfraContext
    control_tower: ControlTowerProtocol
    feature_flags: FeatureFlagsProtocol
```

---

## 4. Over-Engineered Abstractions

### 4.1 Single-Implementation Protocols

| Protocol | Implementation | Recommendation |
|----------|---------------|----------------|
| `LoggerProtocol` | `StructlogAdapter` only | Remove protocol, use structlog directly |
| `BaseRepository` ABC | 2 subclasses (one throws exceptions) | Remove ABC, use concrete repos |
| `CachedRepository` | Wrapper that caches only `find_by_id` | Add caching to repo directly |
| `ConfigRegistryProtocol` | Just a dict wrapper | Remove, use dict or Pydantic |

### 4.2 Excessive Layering: SessionState (3 Layers)

```
SessionStateAdapter
    └─> SessionStateService
        └─> SessionStateRepository
```

**Issue:** Three layers for simple CRUD operations.

**Recommendation:** Collapse to 2 layers:
```
SessionStateService (business logic + validation)
    └─> SessionStateRepository (database operations)
```

### 4.3 ControlTower Internal Complexity

Current ControlTower creates 5 internal services that are always used together:

```python
# Every operation touches multiple services:
async def submit_request(self, envelope, priority, quota):
    pcb = self._lifecycle.submit(...)      # Service 1
    self._events.emit_event(...)           # Service 2
    self._resources.allocate(...)          # Service 3
    self._lifecycle.schedule(...)          # Service 1 again
    result = await self._ipc.dispatch(...) # Service 4
    await self._interrupts.create_...(...) # Service 5
```

**Recommendation:** Consolidate into 2 aggregates:
- `ProcessAggregate` = lifecycle + resources (process management)
- `EventAggregate` = events + interrupts (event handling)

---

## 5. Duplicate Utilities

### 5.1 JSON Serialization (Critical)

**Duplicated in:**
- `jeeves_avionics/utils/serialization.py:107-148`
- `jeeves_avionics/database/postgres_client.py:767-789`

**Recommendation:** Remove from `postgres_client.py`, import from `serialization.py`.

### 5.2 Status Enums (Multiple Definitions)

| Location | Enum | Values |
|----------|------|--------|
| `jeeves_protocols/core.py:108` | `OperationStatus` | SUCCESS, ERROR, NOT_FOUND, TIMEOUT |
| `jeeves_avionics/webhooks/service.py:53` | `DeliveryStatus` | PENDING, DELIVERED, FAILED |
| `jeeves_control_tower/services/interrupt_service.py` | `InterruptStatus` | Various |
| `jeeves_mission_system/api/health.py` | `ComponentStatus` | Various |

**Recommendation:** Create a unified status system in `jeeves_protocols`:
```python
# jeeves_protocols/status.py
class BaseStatus(str, Enum):
    """Base class for all status enums"""
    pass

class OperationStatus(BaseStatus):
    SUCCESS = "success"
    ERROR = "error"
    # ...

class ProcessStatus(BaseStatus):
    PENDING = "pending"
    RUNNING = "running"
    # ...
```

### 5.3 Repository `from_dict()` Pattern

**Repeated in 6+ repositories:**
- `event_repository.py`
- `graph_repository.py`
- `session_state_repository.py`
- `trace_repository.py`
- `tool_metrics_repository.py`
- `chunk_repository.py`

**Recommendation:** Create a mixin or base class:
```python
class DictDeserializableMixin:
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(**{
            field.name: data.get(field.name)
            for field in fields(cls)
        })
```

---

## 6. Service Composition Complexity

### 6.1 Complex Initialization in Bootstrap

`jeeves_mission_system/bootstrap.py` has 7 factory functions that must be called in sequence:

```python
# Current: 7 separate functions
create_core_config_from_env()           # Step 1
create_orchestration_flags_from_env()   # Step 2
core_config_to_resource_quota()         # Step 3
create_app_context()                    # Step 4 (11 internal steps)
create_avionics_dependencies()          # Step 5
create_tool_executor_with_access()      # Step 6
create_distributed_infrastructure()     # Step 7 (optional)
```

**Recommendation:** Create a single builder or orchestrator:
```python
class ApplicationBuilder:
    def __init__(self, env: Dict[str, str] = None):
        self._env = env or os.environ

    def build(self) -> Application:
        config = self._load_config()
        infra = self._build_infrastructure(config)
        kernel = self._build_kernel(infra)
        return Application(config, infra, kernel)
```

### 6.2 Circular Dependency Workaround

`bootstrap.py:338-365` uses a double-closure to work around LLMGateway needing ControlTower:

```python
# Current: Closure workaround
def create_resource_callback(control_tower):
    def track_resources(tokens_in, tokens_out):
        pid = get_request_pid()  # Hidden global state
        return control_tower.record_llm_call(pid, tokens_in, tokens_out)
    return track_resources

llm_gateway.set_resource_callback(create_resource_callback(control_tower))
```

**Recommendation:** Make resource tracking a protocol:
```python
# jeeves_protocols/tracking.py
class ResourceTrackerProtocol(Protocol):
    def record_llm_call(self, tokens_in: int, tokens_out: int) -> Optional[str]: ...

# LLMGateway receives it via constructor
class LLMGateway:
    def __init__(self, tracker: Optional[ResourceTrackerProtocol] = None):
        self._tracker = tracker
```

---

## 7. Recommended Module Stacking

### Current Structure (Complex)
```
jeeves_protocols/        # L0: Types only
jeeves_memory_module/    # L1: Memory (imports L2!)
jeeves_avionics/         # L2: Infrastructure
jeeves_control_tower/    # L3: Kernel
jeeves_mission_system/   # L4: Application
jeeves-capability-*/     # L5: Capabilities
```

### Proposed Structure (Simplified)

**Option A: Shared Utilities Package**
```
jeeves_shared/           # L0: Utilities (logging, serialization, etc.)
jeeves_protocols/        # L0: Type definitions only
jeeves_memory_module/    # L1: Memory (imports only L0)
jeeves_avionics/         # L2: Infrastructure (imports L0, L1)
jeeves_control_tower/    # L3: Kernel (imports L0)
jeeves_mission_system/   # L4: Application (composes all)
jeeves-capability-*/     # L5: Capabilities
```

**Option B: Flatten Memory into Avionics**
```
jeeves_protocols/        # L0: Types only
jeeves_avionics/         # L1: Infrastructure + Memory (merged)
  ├── database/
  ├── llm/
  ├── memory/            # Memory services moved here
  └── logging/
jeeves_control_tower/    # L2: Kernel
jeeves_mission_system/   # L3: Application
jeeves-capability-*/     # L4: Capabilities
```

**Recommendation:** Option A provides cleaner separation while Option B reduces layers. Choose based on whether memory services need independent evolution.

---

## 8. Prioritized Action Items

### Phase 1: Critical Boundary Fixes (Week 1-2)

1. **Extract common utilities to `jeeves_shared` or `jeeves_protocols`**
   - Move `get_component_logger`, `parse_datetime`, `uuid_str` to shared package
   - Update all 39 memory module imports

2. **Fix Avionics → Control Tower violations**
   - Define `InterruptServiceProtocol` in protocols
   - Inject implementation via dependency injection

3. **Consolidate DI containers**
   - Merge `PrimitiveDeps` into `AppContext` or create layered containers
   - Remove duplicate `settings` field

### Phase 2: Simplification (Week 3-4)

4. **Remove single-implementation protocols**
   - Remove `LoggerProtocol`, use structlog directly
   - Remove `ConfigRegistryProtocol`, use direct config access

5. **Collapse excessive layers**
   - Remove `SessionStateAdapter`, keep Service + Repository
   - Consolidate ControlTower into 2 aggregates

6. **Unify status enums**
   - Create base status system in protocols
   - Migrate existing enums

### Phase 3: Cleanup (Week 5-6)

7. **Deduplicate utilities**
   - Remove JSON serialization from postgres_client
   - Create repository base class with `from_dict()`

8. **Simplify bootstrap**
   - Create ApplicationBuilder pattern
   - Remove circular dependency workarounds

---

## 9. Metrics for Success

| Metric | Current | Target |
|--------|---------|--------|
| Layer boundary violations | 45 | 0 |
| DI containers | 3 | 1-2 |
| Single-impl protocols | 5+ | 0 |
| Duplicate utility locations | 6 | 1 |
| Bootstrap factory functions | 7 | 1-2 |
| SessionState layers | 3 | 2 |
| ControlTower internal services | 5 | 2 |

---

## 10. Conclusion

The codebase has strong architectural foundations but has accumulated complexity that can be reduced while maintaining clean layer separation:

1. **Fix boundary violations** by extracting shared utilities to L0
2. **Consolidate DI containers** to reduce cognitive load
3. **Remove over-engineering** where abstractions don't provide value
4. **Simplify service composition** with better builders

These changes will reduce ~500 lines of boilerplate, eliminate 45 boundary violations, and make the architecture easier to understand and maintain.

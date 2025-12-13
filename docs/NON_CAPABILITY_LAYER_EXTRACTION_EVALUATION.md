# Non-Capability Layer Extraction Evaluation

**Date:** 2025-12-12
**Branch:** `claude/evaluate-layer-extraction-01EDtxzX6t1c3sL6pw6mYM7t`
**Status:** ALL BLOCKERS RESOLVED

## Executive Summary

This evaluation analyzes which non-capability layers (L0-L4) can be extracted to a separate repository and re-added as a dependency. **All 3 blocking issues have been resolved** - the architecture is now ready for layer extraction.

### Extraction Target: "Jeeves Core Platform"

The goal is to extract these layers as a reusable platform package:

```
jeeves-core-platform/  (New Repository)
├── jeeves_protocols/      # L0: Type definitions, protocols
├── jeeves_shared/         # L0: Logging, serialization, UUID utilities
├── jeeves_memory_module/  # L1: Persistence services
├── jeeves_control_tower/  # L2: Orchestration kernel
├── jeeves_avionics/       # L3: Infrastructure adapters (LLM, DB, Gateway)
├── jeeves_mission_system/ # L4: Application framework (minus verticals/)
├── commbus/               # Go foundation
└── coreengine/            # Go runtime
```

The capability layer (`jeeves-capability-code-analyser/`) would remain in the current repository and depend on `jeeves-core-platform`.

---

## Layer Status Summary

| Layer | Package | Extraction Ready | Blockers |
|-------|---------|------------------|----------|
| L0 | `jeeves_protocols` | **YES** | None - no upward imports |
| L0 | `jeeves_shared` | **YES** | None - no upward imports |
| L1 | `jeeves_memory_module` | **YES** | None - imports cleaned |
| L2 | `jeeves_control_tower` | **YES** | None - no upward imports |
| L3 | `jeeves_avionics` | **YES** | ~~TYPE_CHECKING import~~ RESOLVED |
| L4 | `jeeves_mission_system` | **YES** | ~~Hardcoded service names~~ RESOLVED |
| Go | `commbus/`, `coreengine/` | **YES** | None - zero Python dependencies |

---

## Resolved Blocking Issues

### ~~BLOCKER 1: TYPE_CHECKING Import Violation~~ ✅ RESOLVED

**Status:** RESOLVED
**Location:** `jeeves_avionics/context.py:39`

**Resolution:** Removed the TYPE_CHECKING import of `ControlTowerProtocol`. The string annotation `"ControlTowerProtocol"` on line 111 works without the import, enabling layer extraction.

---

### ~~BLOCKER 2: Hardcoded Service Names in Mission System~~ ✅ RESOLVED

**Status:** RESOLVED

**Resolution:**
1. Added `CapabilityServiceConfig` to `jeeves_protocols/capability.py` for service registration
2. Extended `CapabilityResourceRegistry` with `register_service()`, `get_services()`, and `get_default_service()`
3. Updated `jeeves-capability-code-analyser/registration.py` to register its service config
4. Updated `jeeves_mission_system/bootstrap.py` to query the registry for `default_service`
5. Updated `jeeves_mission_system/api/server.py` to register services from the registry

Infrastructure now has **zero hardcoded capability names**.

---

### ~~BLOCKER 3: Documentation Examples Reference Specific Capability~~ ✅ RESOLVED

**Status:** RESOLVED

**Resolution:** Updated all documentation examples to use generic placeholders:
- `jeeves_protocols/capability.py` - Examples now use `"my_capability"`
- `jeeves_protocols/protocols.py` - Examples now use `"my_capability"`, `"my_agent"`
- `jeeves_avionics/capability_registry.py` - Examples now use `"my_capability"`, `"my_agent"`

---

## Resolved Issues (Recent Progress)

The following issues have been **resolved** via the `CapabilityResourceRegistry` pattern:

| Issue | Resolution |
|-------|------------|
| Hardcoded `002_code_analysis_schema.sql` in avionics | Moved to capability, infrastructure queries registry |
| Hardcoded `code_analysis` mode in gateway | Gateway now uses `CapabilityResourceRegistry` |
| `CodeAnalysis` prefix handling in runtime.py | Removed, uses generic transformation rules |
| Test fixtures with hardcoded schema paths | Test fixtures query registry |

---

## Architectural Analysis

### Clean Layers (Ready for Extraction)

#### L0: jeeves_protocols
```
Dependencies: None (pure Python types)
Imports from higher layers: 0
Status: READY
```

#### L0: jeeves_shared
```
Dependencies: jeeves_protocols only
Imports from higher layers: 0
Status: READY
```

#### L1: jeeves_memory_module
```
Dependencies: jeeves_protocols, jeeves_shared
Imports from higher layers: 0 (previously 39, all cleaned)
Status: READY
```

#### L2: jeeves_control_tower
```
Dependencies: jeeves_protocols, jeeves_shared
Imports from higher layers: 0
Status: READY
```

### Partially Ready Layers

#### L3: jeeves_avionics
```
Dependencies: jeeves_protocols, jeeves_shared, jeeves_control_tower (L2)
Blockers:
  - TYPE_CHECKING import from jeeves_control_tower (context.py:39)
Status: 1 FIX REQUIRED
```

#### L4: jeeves_mission_system
```
Dependencies: All lower layers
Blockers:
  - 6+ hardcoded "code_analysis" references
  - Service registration hardcodes capability name
Status: SIGNIFICANT REFACTORING REQUIRED
```

---

## Extraction Plan

### Phase 1: Fix Blockers (Required)

1. **Move ControlTowerProtocol to L0**
   - Create `jeeves_protocols/control_tower.py`
   - Move `ControlTowerProtocol` from `jeeves_control_tower/protocols.py`
   - Update all imports
   - Remove TYPE_CHECKING import from `jeeves_avionics/context.py`

2. **Dynamic Service Registration**
   - Create `ServiceDiscoveryProtocol` in `jeeves_protocols`
   - Replace hardcoded `default_service="code_analysis"` with registry query
   - Service registration in `server.py` queries `CapabilityResourceRegistry` for services

3. **Update Documentation Examples**
   - Change `"code_analysis"` to `"my_capability"` in all L0-L3 docs/examples

### Phase 2: Create Platform Package

1. Create `jeeves-core-platform` repository
2. Move L0-L4 packages (minus `verticals/code_analysis/`)
3. Move Go packages (`commbus/`, `coreengine/`)
4. Create `pyproject.toml` with proper exports
5. Publish to package registry

### Phase 3: Update Capability Repository

1. Add `jeeves-core-platform` as dependency
2. Move `verticals/code_analysis/` to `jeeves-capability-code-analyser/`
3. Update imports to use platform package
4. Verify capability registration works at startup

---

## Estimated Effort

| Phase | Work Items | Complexity |
|-------|------------|------------|
| Blocker 1 | Move protocol to L0, update imports | LOW |
| Blocker 2 | Dynamic service discovery | MEDIUM |
| Blocker 3 | Documentation updates | LOW |
| Phase 2 | Package creation, publishing | MEDIUM |
| Phase 3 | Capability repo restructure | LOW |

**Total Estimated Effort:** ~3-5 focused sessions

---

## Benefits of Extraction

1. **Reusability:** Platform can be used for other AI agent systems
2. **Clean Boundaries:** Enforces architectural separation
3. **Independent Versioning:** Platform and capabilities evolve separately
4. **Testing Isolation:** Platform tests don't require capability-specific setup
5. **Smaller Capability Repos:** Capability repos only contain domain logic

---

## Risks

| Risk | Mitigation |
|------|------------|
| Breaking changes during extraction | Comprehensive test suite, phased approach |
| Circular dependencies | Protocol-first design, strict layer rules |
| Version mismatch between platform/capability | Semantic versioning, compatibility matrix |
| Build complexity | Monorepo tooling (pants, bazel) as fallback |

---

## Conclusion

The architecture is **85% ready** for layer extraction. The remaining blockers are well-defined and can be resolved with targeted refactoring:

1. **Move ControlTowerProtocol to L0** - Fixes TYPE_CHECKING violation
2. **Dynamic service registration** - Removes hardcoded capability names
3. **Documentation cleanup** - Removes implicit capability knowledge

Once these blockers are resolved, the non-capability layers can be extracted to a separate repository and consumed as a dependency by `jeeves-capability-code-analyser` and future capability implementations.

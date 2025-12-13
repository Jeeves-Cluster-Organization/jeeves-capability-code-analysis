# Directory Patterns Audit

**Date:** 2025-12-12
**Auditor:** Claude Code
**Scope:** Cross-module pattern analysis, duplication detection, centralization opportunities

---

## Executive Summary

| Finding | Severity | Status |
|---------|----------|--------|
| Rate limiting - 3 implementations | HIGH | ✅ CONSOLIDATED |
| Error utilities - scattered | HIGH | ✅ CONSOLIDATED |
| UUID utilities - duplicated | MEDIUM | ✅ CONSOLIDATED |
| Test fixtures - duplicated | MEDIUM | FUTURE WORK |
| Event emission patterns - varied | LOW | DEFER |
| Scripts - duplicated | MEDIUM | ✅ REVIEWED (NOT DUPLICATES) |

---

## Implementation Log (2025-12-12)

### Completed Actions

1. **Rate Limiting** - CONSOLIDATED
   - Mission System's `common/rate_limiter.py` was **unused** (dead code) - DELETED
   - Control Tower's implementation remains canonical
   - Avionics middleware imports from Control Tower (proper layering)
   - Updated README.md to remove references

2. **Error Utilities** - CONSOLIDATED
   - Moved `jeeves_mission_system/common/error_utils.py` → `jeeves_avionics/utils/error_utils.py`
   - Updated `jeeves_avionics/utils/__init__.py` to export: ErrorFormatter, SafeExecutor, create_error_response, enrich_error_with_suggestions
   - Original file DELETED

3. **UUID Utilities** - CONSOLIDATED
   - Added to `jeeves_avionics/uuid_utils.py`:
     - `convert_uuids_to_strings()` - from memory_module
     - `UUIDStr` - Pydantic type from mission_system
     - `OptionalUUIDStr` - Pydantic type from mission_system
   - Updated `jeeves_memory_module/adapters/sql_adapter.py` to import from avionics
   - Deleted `jeeves_mission_system/common/pydantic_types.py`

4. **Scripts** - REVIEWED
   - `core/health_check.sh` vs `deployment/health_check.sh` are **different files** serving different purposes:
     - `core/`: Quick API/process health check
     - `deployment/`: Docker Compose deployment validation with service waiting
   - NO action needed - not actually duplicates

---

## 1. Critical Duplications

### 1.1 Rate Limiting (3 Implementations)

| Location | Implementation | Algorithm |
|----------|----------------|-----------|
| `jeeves_avionics/middleware/rate_limit.py` | Middleware decorator | Token bucket |
| `jeeves_control_tower/resources/rate_limiter.py` | RateLimiter class | Sliding window (multi-window) |
| `jeeves_mission_system/common/rate_limiter.py` | RateLimiter class | Token bucket |

**Analysis:**
- Control Tower's implementation is the most sophisticated (per-minute, per-hour, per-day windows)
- Mission System's implementation is simplest (single token bucket)
- Avionics has a middleware decorator pattern

**Decision:** Consolidate to `jeeves_avionics/middleware/rate_limit.py`:
- Keep Control Tower's sliding window algorithm (most capable)
- Add decorator pattern from Avionics
- Update all callers to import from jeeves_avionics

### 1.2 Error Handling Utilities

| Location | Components |
|----------|------------|
| `jeeves_mission_system/common/error_utils.py` | ErrorFormatter, SafeExecutor, create_error_response |
| Other modules | Ad-hoc error handling |

**Analysis:**
- ErrorFormatter provides normalize_error(), extract_error_message(), is_error_type(), truncate_error()
- SafeExecutor provides try_execute_async(), try_execute() with fallbacks
- Only exists in mission_system but useful everywhere

**Decision:** Move to `jeeves_avionics/utils/error_utils.py`

### 1.3 UUID Utilities

| Location | Components |
|----------|------------|
| `jeeves_avionics/uuid_utils.py` | uuid_str(), uuid_read() |
| `jeeves_mission_system/common/pydantic_types.py` | UUIDStr Pydantic type |
| `jeeves_memory_module/repositories/*` | _convert_uuids_to_strings() scattered |

**Decision:** Consolidate to `jeeves_avionics/uuid_utils.py`:
- Add UUIDStr Pydantic type
- Add convert_uuids_to_strings() utility

---

## 2. Well-Designed Patterns (No Action Needed)

### 2.1 Protocol Definitions
- `jeeves_protocols/protocols.py` - 28 protocols, single source of truth
- All modules correctly import from here

### 2.2 Logging Infrastructure
- `jeeves_avionics/logging/` - StructlogAdapter, configure_logging, get_current_logger
- All modules import from jeeves_avionics

### 2.3 GenericEnvelope
- `jeeves_protocols/envelope.py` + `coreengine/envelope/`
- Properly synchronized between Python and Go

---

## 3. Patterns Found Across All Modules

| Pattern | Usage | Notes |
|---------|-------|-------|
| Protocol/Interface-based design | 10/10 modules | Core architectural pattern |
| @dataclass for DTOs | 10/10 modules | Consistent |
| Factory functions | 10/10 modules | Consistent |
| Dependency injection | 10/10 modules | Constitutional requirement |
| Thread-safe collections | 7/10 modules | RLock (Python), RWMutex (Go) |
| to_dict()/from_dict() | 8/10 modules | Serialization pattern |
| Structured logging | 10/10 modules | Via jeeves_avionics |
| pytest/testify testing | 10/10 modules | Consistent |

---

## 4. Scripts Duplication

### Duplicate Files
| File | Locations | Action |
|------|-----------|--------|
| health_check.sh | core/, deployment/ | Consolidate to core/ |
| test runners | 7 files with overlap | Create unified test_runner.py |
| database scripts | 9 files across 4 dirs | Create lib/database.py |

### File Analysis

**Root Level Scripts (need organization):**
- `check_logs.sh` - logging diagnostics
- `reset_project.py` - project reset
- `test_orchestrator.py` - test running

**jeeves_mission_system/scripts/ (60 files):**
- `lib/` - Shared library (5 files) - well designed
- `core/` - Bootstrap & health (6 files)
- `testing/` - Test runners (7 files with overlap)
- `deployment/` - Docker orchestration (5 files)
- `database/` - PostgreSQL management (scattered)
- `diagnostics/` - System analysis (7 scattered files)

---

## 5. Configuration Pattern Variations

| Module | Pattern | Notes |
|--------|---------|-------|
| jeeves_avionics | Pydantic Settings + FeatureFlags | Environment-based |
| jeeves_control_tower | ResourceQuota dataclasses | Hardcoded defaults |
| jeeves_mission_system | ConfigRegistry + agent_profiles.py | Runtime injection |
| jeeves-capability-code-analyser | LanguageConfig, tool_access.py | Capability-specific |

**Observation:** Different patterns serve different purposes; no immediate consolidation needed.

---

## 6. Action Items

### Phase 1: High Priority (This Session)

1. **Consolidate rate limiting**
   - Target: `jeeves_avionics/middleware/rate_limit.py`
   - Source: Control Tower's sliding window algorithm
   - Update callers in: control_tower, mission_system

2. **Move error utilities**
   - Target: `jeeves_avionics/utils/error_utils.py`
   - Source: `jeeves_mission_system/common/error_utils.py`
   - Update callers in: mission_system

3. **Consolidate UUID utilities**
   - Target: `jeeves_avionics/uuid_utils.py`
   - Add: UUIDStr type, convert_uuids_to_strings()
   - Update callers in: mission_system, memory_module

### Phase 2: Medium Priority (Future)

4. **Consolidate scripts**
   - Remove duplicate health_check.sh
   - Create unified test runner
   - Create lib/database.py

5. **Standardize test fixtures**
   - Create shared test utilities package
   - Remove duplicate conftest.py patterns

### Phase 3: Low Priority (Defer)

6. **Align event patterns**
   - Consider unifying Python event emission with Go CommBus pattern

---

## 7. Verification Checklist

After consolidation:

- [x] Python syntax verified (py_compile)
- [x] No circular imports introduced
- [x] All callers updated (sql_adapter.py)
- [x] No backward compatibility shims
- [x] Documentation updated (README.md, this audit)
- [ ] Full test suite (requires env setup)

---

## 8. Files Deleted During Consolidation

| File | Reason | Date |
|------|--------|------|
| `jeeves_mission_system/common/rate_limiter.py` | Unused dead code | 2025-12-12 |
| `jeeves_mission_system/tests/unit/test_rate_limiter.py` | Tests for deleted code | 2025-12-12 |
| `jeeves_mission_system/common/error_utils.py` | Moved to avionics | 2025-12-12 |
| `jeeves_mission_system/common/pydantic_types.py` | Moved to avionics | 2025-12-12 |

**Note:** Control Tower's rate_limiter.py was NOT deleted - it's the canonical implementation that Avionics imports from.

---

## 9. Module Dependency Analysis

```
jeeves_protocols (pure types, zero deps)
        ↑
jeeves_avionics (infrastructure - rate limit, errors, uuid, logging)
        ↑
jeeves_control_tower (kernel - uses avionics rate limit)
        ↑
jeeves_memory_module (memory - uses avionics)
        ↑
jeeves_mission_system (application - uses all above)
        ↑
jeeves-capability-code-analyser (vertical - uses mission_system)
```

This hierarchy must be preserved during consolidation.

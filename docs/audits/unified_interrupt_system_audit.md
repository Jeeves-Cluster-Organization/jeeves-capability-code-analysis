# Unified Flow Interrupt System Audit Report

**Commit Audited:** aed43d9
**Date:** 2025-12-11
**Auditor:** Claude Opus 4

## Executive Summary

Commit `aed43d9` introduced a unified flow interrupt system as a breaking change with no backward compatibility. The audit reveals **3 critical**, **6 major**, and **4 minor** issues that require attention.

---

## Issues Found

### CRITICAL (Production-blocking)

#### 1. InterruptType Enum Missing CRITIC_REVIEW and CHECKPOINT
**Location:** `jeeves_control_tower/types.py:38-59`
**Description:** The `InterruptType` enum has 6 values while `InterruptKind` has 7. Missing: `CRITIC_REVIEW` (not present at all).

**Impact:** The kernel's `_handle_interrupt()` at line 374 will fall back to `SYSTEM_ERROR` for CRITIC_REVIEW interrupts, corrupting interrupt handling.

**Fix:**
```python
class InterruptType(str, Enum):
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    CRITIC_REVIEW = "critic_review"      # ADD
    CHECKPOINT = "checkpoint"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    SYSTEM_ERROR = "system_error"
```

---

#### 2. Python GenericEnvelope Missing Unified Interrupt Fields
**Location:** `jeeves_protocols/envelope.py:24-91`
**Description:** The Python `GenericEnvelope` still has legacy fields (`clarification_pending`, `confirmation_pending`) but is missing the unified interrupt fields that exist in the Go struct:
- `interrupt_pending: bool`
- `interrupt: Optional[Dict[str, Any]]`

**Impact:** Python-Go interop is broken. Envelope serialization/deserialization will lose interrupt state.

**Fix:**
```python
# Add after line 67
interrupt_pending: bool = False
interrupt: Optional[Dict[str, Any]] = None
```

---

#### 3. Legacy Schema Still Defines Dropped Tables
**Location:** `jeeves_avionics/database/schemas/001_postgres_schema.sql:199-213`
**Description:** The base schema still creates `pending_confirmations` table (lines 199-213) with indexes (lines 268-272), which the migration 002_unified_interrupts.sql then drops. This is inconsistent.

**Impact:** Running migrations in order works, but the base schema is incorrect for new deployments and creates confusion.

**Fix:** Remove `pending_confirmations` table definition from 001_postgres_schema.sql, or add a comment that it's intentionally dropped by 002_unified_interrupts.sql.

---

### MAJOR (Functionality gaps)

#### 4. No Tests for InterruptService
**Location:** N/A
**Description:** No unit or integration tests exist for `InterruptService`. Grep for `InterruptService|InterruptKind|FlowInterrupt` in test files returns no matches.

**Impact:** Core interrupt handling logic is untested. Regressions will go undetected.

**Recommended Tests:**
```python
# tests/unit/services/test_interrupt_service.py
class TestInterruptService:
    async def test_create_interrupt_all_kinds(self):
        """Test creating each of the 7 interrupt kinds."""

    async def test_respond_validates_user_id(self):
        """Test that respond() rejects wrong user."""

    async def test_expire_pending_handles_timezone(self):
        """Test expiration with UTC and local times."""

    async def test_to_dict_from_db_row_roundtrip(self):
        """Verify inverse operations."""

    async def test_memory_store_thread_safety(self):
        """Test concurrent access to in-memory fallback."""
```

---

#### 5. Orphaned Table Reference in Governance Service
**Location:** `jeeves_mission_system/orchestrator/governance_service.py:106`
**Description:** L4 memory layer definition still references `pending_clarifications` table which no longer exists.

**Fix:**
```python
# Line 106 - change:
"tables": ["session_state", "open_loops", "pending_clarifications"],
# to:
"tables": ["session_state", "open_loops", "flow_interrupts"],
```

---

#### 6. Kernel InterruptType-to-InterruptKind Mapping Incomplete
**Location:** `jeeves_control_tower/kernel.py:374-382`
**Description:** The `kind_map` doesn't include `CRITIC_REVIEW` or `CHECKPOINT`:
```python
kind_map = {
    InterruptType.CLARIFICATION: InterruptKind.CLARIFICATION,
    InterruptType.CONFIRMATION: InterruptKind.CONFIRMATION,
    InterruptType.TIMEOUT: InterruptKind.TIMEOUT,
    InterruptType.RESOURCE_EXHAUSTED: InterruptKind.RESOURCE_EXHAUSTED,
    InterruptType.SYSTEM_ERROR: InterruptKind.SYSTEM_ERROR,
}
# Missing: CHECKPOINT -> CHECKPOINT, CRITIC_REVIEW -> CRITIC_REVIEW
```

**Fix:** Add missing mappings after fixing InterruptType enum.

---

#### 7. Gateway get_interrupt_service() Creates New Instance Each Call
**Location:** `jeeves_avionics/gateway/routers/interrupts.py:90-99`
**Description:** The `get_interrupt_service()` function creates a new `InterruptService()` instance on every call, meaning the in-memory store is never shared.

```python
def get_interrupt_service():
    # In production, this would be retrieved from app.state
    # For now, create a new instance (in-memory storage)
    return InterruptService()  # NEW instance every call!
```

**Impact:** In-memory fallback store is useless; each request gets empty state.

**Fix:** Use FastAPI dependency injection with `app.state.interrupt_service`.

---

#### 8. Thread Safety Concern in Memory Store
**Location:** `jeeves_control_tower/services/interrupt_service.py:350`
**Description:** The `_memory_store: Dict[str, FlowInterrupt] = {}` is not thread-safe. Concurrent async operations could corrupt state.

**Fix:** Use `asyncio.Lock` for memory store operations or use a thread-safe dict implementation.

---

#### 9. Old Test Files Still Present
**Location:** Multiple files in `jeeves_mission_system/tests/unit/`:
- `test_confirmation_coordinator.py`
- `test_confirmation_detector.py`
- `test_confirmation_interpreter.py`
- `test_confirmation_manager.py`

**Description:** Tests for deleted modules are still present, will fail on import.

**Fix:** Delete these test files or update them to test the new InterruptService.

---

### MINOR (Code quality)

#### 10. expire_pending() Uses Raw SQL UPDATE with RETURNING
**Location:** `jeeves_control_tower/services/interrupt_service.py:710-718`
**Description:** Uses direct SQL instead of the DatabaseProtocol abstraction:
```python
rows = await self._db.fetch_all(
    """
    UPDATE flow_interrupts
    SET status = 'expired'
    ...
    RETURNING id, request_id, kind
    """,
    (now,),
)
```

**Concern:** The `DatabaseProtocol` doesn't define a method that combines UPDATE with RETURNING. Either extend the protocol or use two separate calls.

---

#### 11. Go Resume() Has Hardcoded Stage Names
**Location:** `coreengine/runtime/runtime.go:325-339`
**Description:** The Resume function hardcodes stage names like `"intent"`, `"executor"`:
```go
case envelope.InterruptKindClarification:
    env.CurrentStage = "intent"
case envelope.InterruptKindConfirmation:
    if response.Approved != nil && *response.Approved {
        env.CurrentStage = "executor"
```

**Concern:** Coupling to specific pipeline configuration. Should be configurable.

---

#### 12. ToStateDict/FromStateDict Asymmetry for DAG Fields
**Location:** `coreengine/envelope/generic.go:638-713, 717-925`
**Description:** `ToStateDict()` doesn't serialize DAG execution fields (`ActiveStages`, `CompletedStageSet`, `FailedStages`, `DAGMode`), but they're part of the struct.

**Impact:** DAG state is lost during persistence/restore.

---

#### 13. Missing Status in Database CHECK Constraint
**Location:** `jeeves_avionics/database/schemas/002_unified_interrupts.sql:40-45`
**Description:** The status constraint is correct but doesn't prevent invalid state transitions programmatically.

---

## Recommended Additional Test Cases

### Unit Tests
1. **InterruptService.create_interrupt()** - All 7 kinds with default TTL
2. **InterruptService.respond()** - User validation, status validation
3. **InterruptService.expire_pending()** - UTC boundary cases
4. **FlowInterrupt.to_dict()/from_db_row()** - Round-trip all fields
5. **InterruptResponse.to_dict()/from_dict()** - Round-trip preservation

### Integration Tests
1. **Create → Respond → Resume Flow** - Full lifecycle
2. **Expiration Handling** - Auto-expire after TTL
3. **Concurrent Interrupt Creation** - Race condition testing
4. **Rate Limit → RESOURCE_EXHAUSTED** - End-to-end flow
5. **Kernel Resume After Interrupt** - State restoration

### E2E Tests
1. **HTTP API flow** - POST /interrupts/{id}/respond
2. **Webhook emission** - All event types fire correctly

---

## Architectural Concerns

1. **Dual Interrupt Tracking**: Both `EventAggregator._pending_interrupts` and `InterruptService._memory_store` track interrupts. Potential for desync.

2. **No Backward Compatibility**: Breaking change with no migration path. Existing `pending_confirmations`/`pending_clarifications` data is dropped.

3. **In-Memory Fallback Brittle**: If DB is unavailable, the gateway creates new service instances per request, losing all in-memory state.

---

## Summary Table

| Severity | Count | Key Issues |
|----------|-------|------------|
| Critical | 3 | Enum mismatch, Python envelope missing fields, legacy schema conflict |
| Major | 6 | No tests, orphaned refs, incomplete mappings, thread safety |
| Minor | 4 | Code quality, hardcoding, serialization gaps |

---

## Files Audited

### Go Layer
- `coreengine/envelope/generic.go` - FlowInterrupt struct, InterruptKind enum, SetInterrupt/ResolveInterrupt/ClearInterrupt methods
- `coreengine/runtime/runtime.go` - Resume() method, interrupt handling in Run()

### Database
- `jeeves_avionics/database/schemas/002_unified_interrupts.sql` - Unified table, indexes, triggers

### Python
- `jeeves_control_tower/services/interrupt_service.py` - InterruptService class
- `jeeves_control_tower/kernel.py` - _handle_interrupt(), resume_request()
- `jeeves_avionics/gateway/routers/interrupts.py` - REST API endpoints
- `jeeves_protocols/envelope.py` - Python GenericEnvelope
- `jeeves_control_tower/types.py` - InterruptType enum

### Deleted Code Verification
- Searched for: confirmation_manager, confirmation_detector, confirmation_interpreter, confirmation_coordinator, ConfirmationOrchestrator
- Searched for: save_clarification, get_clarification, clear_clarification
- Searched for: pending_confirmations, pending_clarifications tables

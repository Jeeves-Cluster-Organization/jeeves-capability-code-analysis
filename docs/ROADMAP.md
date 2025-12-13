# Technical Roadmap

**Last Updated:** 2025-12-13
**Status:** Living Document

---

## Overview

This document consolidates all pending technical improvements and future work for the Jeeves Code Analyser. Items are categorized by priority and effort.

---

## Completed (Reference)

The following major features have been implemented:

| Feature | Status | Location |
|---------|--------|----------|
| CheckpointProtocol (Time-Travel Debugging) | ✅ Done | `jeeves_protocols/protocols.py`, `jeeves_avionics/checkpoint/` |
| DistributedBusProtocol (Horizontal Scaling) | ✅ Done | `jeeves_protocols/protocols.py`, `jeeves_avionics/distributed/` |
| Go-Python Hybrid Architecture | ✅ Done | `commbus/`, `coreengine/`, `jeeves_avionics/interop/` |
| Control Tower Integration | ✅ Done | `jeeves_control_tower/` |
| jeeves_shared Foundation (L0) | ✅ Done | `jeeves_shared/` - logging, serialization, UUID utilities |
| Unified Interrupt System | ✅ Done | `jeeves_protocols/interrupts.py` - InterruptKind enum |
| Rate Limiter Consolidation | ✅ Done | Control Tower canonical + middleware wrapper |
| get_component_logger helper | ✅ Done | `jeeves_shared/logging/` (moved from avionics) |
| parse_datetime_field utility | ✅ Done | `jeeves_shared/serialization.py` (moved from avionics) |
| UUID utilities centralization | ✅ Done | `jeeves_shared/uuid_utils.py` (consolidated) |
| Time utilities centralization | ✅ Done | `jeeves_shared/serialization.py` - utc_now, utc_now_iso, datetime_to_ms |
| ToolInitializationError deduplication | ✅ Done | Single definition in `tools/base/__init__.py` |

---

## High Priority

### 1. Code Centralization (Technical Debt)

**Source:** Centralization Audit 2025-12-10

#### 1.1 JSONEncoderWithUUID Consolidation

**Effort:** 1 hour | **Files:** 3

Complete the consolidation - currently exists in:
- `jeeves_avionics/utils/serialization.py` (canonical)
- `jeeves_avionics/database/client.py` (duplicate - remove)
- `jeeves_avionics/database/postgres_client.py` (duplicate - remove)

**Action:** Import from `serialization.py` in database files.

#### 1.2 BaseService Abstract Class

**Effort:** 4 hours | **Files:** 19+ services

Create abstract base class to reduce constructor boilerplate:

```python
# jeeves_avionics/services/base.py
class BaseService(ABC):
    def __init__(
        self,
        db: DatabaseClientProtocol,
        logger: Optional[LoggerProtocol] = None,
        component_name: Optional[str] = None,
    ):
        self._logger = get_component_logger(
            component_name or self.__class__.__name__,
            logger
        )
        self.db = db
```

Affected services in:
- `jeeves_memory_module/services/` (14 services)
- `jeeves_mission_system/services/` (5 services)

#### 1.3 Error Response Builder

**Effort:** 3 hours | **Files:** 15+

Unify error response patterns:

```python
# jeeves_protocols/results.py
@dataclass
class OperationResult:
    status: Literal["success", "error", "not_found"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    suggestions: Optional[List[str]] = None
```

#### 1.4 log_async_operation Decorator

**Effort:** 2 hours | **Files:** 50+

Create decorator to reduce try-catch-log boilerplate:

```python
# jeeves_avionics/utils/error_handling.py
def log_async_operation(operation_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            try:
                result = await func(self, *args, **kwargs)
                self._logger.info(f"{operation_name}_complete")
                return result
            except Exception as e:
                self._logger.error(f"{operation_name}_failed", error=str(e))
                raise
        return wrapper
    return decorator
```

---

## Medium Priority

### 2. LLM JSON Response Parser

**Effort:** 3 hours | **Files:** 3+

Centralize LLM response parsing with markdown cleanup:

```python
# jeeves_avionics/llm/response_parser.py
def parse_llm_json_response(
    response: str,
    required_fields: List[str],
    field_defaults: Dict[str, Any],
) -> Dict[str, Any]:
    """Parse LLM JSON response with markdown cleanup and field validation."""
```

Currently duplicated in:
- `jeeves_memory_module/intent_classifier.py` (231 lines)
- `jeeves_memory_module/services/summarization_service.py`
- `jeeves_memory_module/services/edge_extractor.py`

### 3. Configuration Unification

**Effort:** 4 hours | **Files:** 6

Three separate `BaseSettings` classes exist:
- `Settings` in `jeeves_avionics/settings.py`
- `FeatureFlags` in `jeeves_avionics/feature_flags.py`
- `AppConfig` in `jeeves_mission_system/config/manager.py`

**Recommendation:**
1. Keep `Settings` and `FeatureFlags` in avionics (infrastructure)
2. Have `AppConfig` compose from avionics settings
3. Create unified `AppContext` that exposes all configuration

### 4. Database Helpers Extension

**Effort:** 3 hours | **Files:** Multiple

Extend `BaseRepository` with common patterns:
- `fetch_or_abort` pattern
- `insert_with_timestamp` pattern
- `build_where_clause` helper

---

## Lower Priority

### 5. Feature Flag Wrappers

**Effort:** 2 hours

Create module-specific flag wrappers:

```python
# jeeves_memory_module/utils/features.py
class MemoryFeatureFlags:
    @staticmethod
    def event_sourcing_enabled() -> bool:
        return get_feature_flags().memory_event_sourcing_mode != "disabled"
```

### 6. Text Chunking Extraction

**Effort:** 1 hour

Extract `ChunkService._split_text()` sliding window logic for reuse.

### 7. Time Utilities Expansion

**Status:** ✅ COMPLETED (moved to jeeves_shared/serialization.py)

~~**Effort:** 1 hour~~

Time utilities are now in `jeeves_shared/serialization.py`:
- `datetime_to_ms()` - Convert datetime to milliseconds
- `utc_now()` - Get current UTC datetime
- `utc_now_iso()` - Get current UTC as ISO string
- `ms_to_iso()` - Convert milliseconds to ISO string

### 8. Rate Limiter Consolidation

**Status:** ✅ COMPLETED (centralized in Control Tower)

~~**Effort:** 1 hour~~

Rate limiter has been consolidated:
- Canonical implementation in `jeeves_control_tower/resources/rate_limiter.py`
- Protocol defined in `jeeves_protocols/interrupts.py` (RateLimiterProtocol)
- Middleware wrapper in `jeeves_avionics/middleware/rate_limit.py`

---

## Future Capabilities

### Parallel Agent Execution

LangGraph has this capability; Jeeves currently uses sequential execution in Python (Go DAG executor exists but not wired to Python).

**Consideration:** Evaluate if parallel execution provides meaningful performance gains for code analysis workflows.

### OpenTelemetry Integration

Replace structlog with native OpenTelemetry for enterprise observability.

**Current state:** Using structlog for structured logging.

### Additional LLM Providers

Consider adding:
- Google (Gemini)
- AWS Bedrock
- Ollama (local)

**Current providers:** OpenAI, Anthropic, Azure, llamaserver, llama.cpp

---

## Deprecated/Removed

| Feature | Reason |
|---------|--------|
| MCP/A2A Protocol Support | Go interop provides simpler solution (Amendment XXV) |
| Task Management System | Removed per constitution |
| Journal/Notes functionality | Removed per constitution |
| Redis-based state | PostgreSQL only |

---

## Implementation Order

**Phase 1: Quick Wins (1-2 days)** - ✅ MOSTLY COMPLETE
1. ~~JSONEncoderWithUUID consolidation~~ - Import from jeeves_shared
2. ~~Complete any remaining duplicate removal~~ - jeeves_shared centralizes utilities

**Phase 2: Core Utilities (3-4 days)**
3. BaseService abstract class
4. log_async_operation decorator
5. Error response builder (OperationResult in jeeves_protocols)

**Phase 3: Advanced (5+ days)**
6. LLM response parser
7. Configuration unification (Settings/FeatureFlags/AppConfig)
8. Database helpers

---

*This document consolidates pending work from previous audits and analysis documents.*

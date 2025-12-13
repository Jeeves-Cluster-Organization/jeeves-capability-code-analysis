# ADR-001: Logging, Dependency Injection, and Context Architecture

**Status:** Accepted
**Date:** 2025-12-07
**Deciders:** Architecture Review
**Context:** Audit findings from AUDIT_REPORT_2025_12_07.md

---

## Summary of Decisions

| # | Decision Area | Choice | Pattern |
|---|---------------|--------|---------|
| 1 | Layer Violations | Protocol injection | Protocols in core, impls in capabilities |
| 2 | Logger Injection | Hybrid DI + contextvars | Core=DI, tools=context-based |
| 3 | Singleton Elimination | AppContext object | Composition root builds context |
| 4 | Config Ownership | Protocol in core, impl in capability | Capability owns domain configs |
| 5 | Context Propagation | ContextVars for IDs | IDs in types, logger bound externally |
| 6 | Print Policy | CLI entrypoints only | Structured logging everywhere else |

---

## Decision 1: Layer Violation Resolution

### Choice: Option B — Inject via Protocol

**What this means concretely:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      jeeves_protocols                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ protocols.py                                            │    │
│  │  - LanguageConfigProtocol                               │    │
│  │  - NodeProfilesProtocol                                 │    │
│  │  - AgentToolAccessProtocol                              │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ depends on
┌─────────────────────────────┴───────────────────────────────────┐
│                      jeeves_avionics                            │
│  Uses protocols, does NOT import mission_system                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ wiring.py:                                              │    │
│  │   def __init__(self, access_checker: AgentToolAccess    │    │
│  │                      Protocol = None):                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ injects implementations
┌─────────────────────────────┴───────────────────────────────────┐
│                    jeeves_mission_system                        │
│  COMPOSITION ROOT: Creates concrete configs, injects them       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ bootstrap.py:                                           │    │
│  │   language_config = capability.get_language_config()    │    │
│  │   node_profiles = capability.get_node_profiles()        │    │
│  │   avionics.wiring.set_access_checker(AgentToolAccess()) │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Protocol Definitions (to add to `jeeves_protocols/protocols.py`)

```python
from typing import Protocol, List, Optional, Set, runtime_checkable

@runtime_checkable
class LanguageConfigProtocol(Protocol):
    """Configuration for language-specific analysis."""

    def get_extensions(self, language: str) -> List[str]:
        """Get file extensions for a language."""
        ...

    def get_comment_patterns(self, language: str) -> List[str]:
        """Get comment patterns for a language."""
        ...

    def is_supported(self, extension: str) -> bool:
        """Check if extension is supported."""
        ...


@runtime_checkable
class NodeProfilesProtocol(Protocol):
    """Configuration for distributed node profiles."""

    def get_profile_for_agent(self, agent_name: str) -> "NodeProfile":
        """Get node profile for an agent."""
        ...

    def get_available_profiles(self) -> List[str]:
        """List available profile names."""
        ...


@runtime_checkable
class AgentToolAccessProtocol(Protocol):
    """Access control for agent-tool permissions."""

    def can_access(self, agent_name: str, tool_name: str) -> bool:
        """Check if agent can access tool."""
        ...

    def get_allowed_tools(self, agent_name: str) -> Set[str]:
        """Get tools allowed for agent."""
        ...
```

### Files to Modify

| File | Change |
|------|--------|
| `jeeves_protocols/protocols.py` | Add 3 new protocols |
| `jeeves_avionics/wiring.py:180` | Accept `AgentToolAccessProtocol` via constructor |
| `jeeves_avionics/llm/factory.py:273` | Accept `NodeProfilesProtocol` via parameter |
| `jeeves_avionics/memory/services/code_indexer.py:18` | Accept `LanguageConfigProtocol` via constructor |
| `jeeves_mission_system/bootstrap.py` | Create and inject concrete implementations |

---

## Decision 2: Logger Injection Architecture

### Choice: Option C — Hybrid (DI for core, contextvars for tools)

**Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      jeeves_protocols                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ protocols.py:                                           │    │
│  │   class LoggerProtocol(Protocol):                       │    │
│  │       def info(self, event: str, **kw) -> None: ...     │    │
│  │       def debug(self, event: str, **kw) -> None: ...    │    │
│  │       def warning(self, event: str, **kw) -> None: ...  │    │
│  │       def error(self, event: str, **kw) -> None: ...    │    │
│  │       def bind(self, **kw) -> "LoggerProtocol": ...     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Core agents receive LoggerProtocol via constructor (PURE DI)   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ agents/base.py:                                         │    │
│  │   class Agent:                                          │    │
│  │       def __init__(self, logger: LoggerProtocol): ...   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                      jeeves_avionics                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ logging/adapter.py:                                     │    │
│  │   class StructlogAdapter(LoggerProtocol):               │    │
│  │       """Adapts structlog to LoggerProtocol"""          │    │
│  │       def __init__(self, structlog_logger): ...         │    │
│  │       def bind(self, **kw) -> LoggerProtocol:           │    │
│  │           return StructlogAdapter(self._log.bind(**kw)) │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ logging/context.py:                                     │    │
│  │   _current_logger: ContextVar[LoggerProtocol]           │    │
│  │                                                         │    │
│  │   def get_current_logger() -> LoggerProtocol:           │    │
│  │       """For tools/utilities not using DI"""            │    │
│  │       return _current_logger.get(default_logger)        │    │
│  │                                                         │    │
│  │   def set_current_logger(logger: LoggerProtocol):       │    │
│  │       """Called at request entry points"""              │    │
│  │       _current_logger.set(logger)                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### LoggerProtocol Definition

```python
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class LoggerProtocol(Protocol):
    """Structured logging protocol for dependency injection."""

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log at DEBUG level."""
        ...

    def info(self, event: str, **kwargs: Any) -> None:
        """Log at INFO level."""
        ...

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log at WARNING level."""
        ...

    def error(self, event: str, **kwargs: Any) -> None:
        """Log at ERROR level."""
        ...

    def exception(self, event: str, **kwargs: Any) -> None:
        """Log at ERROR level with exception info."""
        ...

    def bind(self, **kwargs: Any) -> "LoggerProtocol":
        """Return new logger with bound context."""
        ...
```

### Migration Strategy

| Phase | Scope | Action |
|-------|-------|--------|
| **Phase 1** | Core engine (4 files) | Convert to constructor injection |
| **Phase 2** | Core agents | Add LoggerProtocol to Agent base class |
| **Phase 3** | Tools/utilities | Use `get_current_logger()` helper |
| **Phase 4** | Gradual migration | Convert hot paths to DI as touched |

**Rule:** Core & mission graph = DI logger; everything else = context-based helper over same protocol.

---

## Decision 3: Singleton Elimination Strategy

### Choice: Option C — AppContext Object

**AppContext Design:**

```python
# jeeves_protocols/protocols.py

@runtime_checkable
class AppContextProtocol(Protocol):
    """Application context containing all injected dependencies."""

    @property
    def settings(self) -> "SettingsProtocol":
        """Application settings."""
        ...

    @property
    def feature_flags(self) -> "FeatureFlagsProtocol":
        """Feature flags."""
        ...

    @property
    def tool_registry(self) -> "ToolRegistryProtocol":
        """Tool registry."""
        ...

    @property
    def logger(self) -> LoggerProtocol:
        """Root logger."""
        ...

    @property
    def clock(self) -> "ClockProtocol":
        """Time provider (for testability)."""
        ...


# jeeves_avionics/context.py

@dataclass
class AppContext:
    """Concrete application context built by composition root."""

    settings: Settings
    feature_flags: FeatureFlags
    tool_registry: ToolRegistry
    logger: LoggerProtocol
    clock: ClockProtocol = field(default_factory=SystemClock)

    # Request-scoped (optional)
    request_context: Optional[RequestContext] = None
```

### Composition Root Pattern

```python
# jeeves_mission_system/bootstrap.py

def create_app_context() -> AppContext:
    """
    COMPOSITION ROOT: Build AppContext once per process.

    This is the ONLY place where concrete implementations are instantiated.
    """
    # Build settings (from env/files)
    settings = Settings()

    # Build feature flags
    feature_flags = FeatureFlags()

    # Build tool registry
    tool_registry = ToolRegistry()

    # Build logger
    configure_logging(settings)
    root_logger = StructlogAdapter(structlog.get_logger())

    return AppContext(
        settings=settings,
        feature_flags=feature_flags,
        tool_registry=tool_registry,
        logger=root_logger,
    )


# Usage in API server
app_context = create_app_context()

@app.on_event("startup")
async def startup():
    # Pass context to handlers
    app.state.context = app_context
```

### Singletons to Eliminate

| Current | Location | Replacement |
|---------|----------|-------------|
| `settings = Settings()` | `avionics/settings.py:256` | `app_context.settings` |
| `feature_flags = FeatureFlags()` | `avionics/feature_flags.py:442` | `app_context.feature_flags` |
| `tool_registry = ToolRegistry()` | `capability/tools/base/registry.py:444` | `app_context.tool_registry` |
| `app_state = AppState()` | `mission_system/api/server.py:105` | `app_context` (merge) |
| `_global_registry` | `mission_system/config/registry.py:119` | `app_context.config_registry` |
| `_global_dedup_cache` | `avionics/memory/services/event_emitter.py:164` | `app_context.dedup_cache` |

**Design mantra:** One composition root builds one AppContext; everything gets dependencies from there, not from globals.

---

## Decision 4: Config Ownership Model

### Choice: Option C — Protocol in Core, Implementation in Capability

**Ownership Rules:**

```
┌─────────────────────────────────────────────────────────────────┐
│ CORE_ENGINE owns:                                               │
│   - LanguageConfigProtocol (interface)                          │
│   - NodeProfilesProtocol (interface)                            │
│   - CapabilityConfigProtocol (interface, for future verticals)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ defines interface
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CAPABILITY owns:                                                │
│   - LanguageConfig (implementation)                             │
│   - AnalyzerThresholds                                          │
│   - ClassificationModes                                         │
│   - Any domain-specific config                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ registers with
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ MISSION_SYSTEM chooses:                                         │
│   - Which capability configs to use for app/profile             │
│   - Injects into avionics and core via protocols                │
└─────────────────────────────────────────────────────────────────┘
```

**Policy:** "If it's domain-specific, capability owns it; if it's interface, core owns it; mission_system chooses instances."

---

## Decision 5: Context Propagation Design

### Choice: Option B — ContextVars for IDs, Logger Bound Externally

**RequestContext Design:**

```python
# jeeves_avionics/logging/context.py

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass(frozen=True)
class RequestContext:
    """Immutable request context for propagation."""

    request_id: UUID
    envelope_id: Optional[UUID] = None
    agent_name: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[UUID] = None


# Context variable for request-scoped data
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context",
    default=None
)


def get_request_context() -> Optional[RequestContext]:
    """Get current request context."""
    return _request_context.get()


def set_request_context(ctx: RequestContext) -> None:
    """Set request context for current async context."""
    _request_context.set(ctx)


@contextmanager
def request_scope(ctx: RequestContext):
    """Context manager for request scope."""
    token = _request_context.set(ctx)
    try:
        yield ctx
    finally:
        _request_context.reset(token)
```

**Usage at Request Entry:**

```python
# jeeves_mission_system/api/server.py

@router.post("/messages")
async def send_message(request: MessageRequest):
    # Create request context
    ctx = RequestContext(
        request_id=uuid4(),
        user_id=request.user_id,
        session_id=request.session_id,
    )

    # Set context and build bound logger
    with request_scope(ctx):
        logger = root_logger.bind(
            request_id=str(ctx.request_id),
            user_id=ctx.user_id,
        )

        # Inject logger into core (DI)
        result = await run_pipeline(
            envelope=envelope,
            logger=logger,  # Explicitly passed
        )
```

**Core Engine Contract:**

```python
# coreengine/agents/base.go (or Python equivalent)

class Agent:
    def __init__(
        self,
        name: str,
        logger: LoggerProtocol,  # Injected, already bound to request context
    ):
        self.name = name
        self._logger = logger.bind(agent=name)
```

**Principle:** Contextvars for propagation, explicit IDs in types, logger injected — no hidden magical globals in core.

---

## Decision 6: Print Statement Policy

### Choice: Option B — CLI Entrypoints Only

**Rules:**

| Location | `print()` Allowed | Logging |
|----------|-------------------|---------|
| `**/cli.py`, `**/__main__.py` | Yes (user-facing) | Also use structlog for diagnostics |
| `scripts/` | Yes | Optional |
| Services, libraries, agents, tools | **No** | LoggerProtocol / structlog only |

**CI Check:**

```python
# scripts/check_print_statements.py

ALLOWED_PATHS = [
    "scripts/",
    "**/cli.py",
    "**/__main__.py",
    "**/tests/",
]

def check_print_statements():
    """Fail if print() appears outside whitelisted files."""
    violations = []
    for py_file in glob("**/*.py"):
        if any(fnmatch(py_file, pattern) for pattern in ALLOWED_PATHS):
            continue
        if "print(" in py_file.read_text():
            violations.append(py_file)

    if violations:
        print(f"ERROR: print() found in {len(violations)} files")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
```

---

## Implementation Order

```
Phase 1: Foundation
├── Add LoggerProtocol to jeeves_protocols/protocols.py
├── Add LanguageConfigProtocol, NodeProfilesProtocol, AgentToolAccessProtocol
├── Create StructlogAdapter in avionics/logging/adapter.py
├── Create RequestContext in avionics/logging/context.py
└── Update coreengine Go code for protocol compliance

Phase 2: Layer Violations
├── Update avionics/wiring.py to accept AgentToolAccessProtocol
├── Update avionics/llm/factory.py to accept NodeProfilesProtocol
├── Update avionics/memory/services/code_indexer.py to accept LanguageConfigProtocol
└── Create injection points in mission_system/bootstrap.py

Phase 3: AppContext
├── Define AppContextProtocol in jeeves_protocols
├── Implement AppContext in avionics/context.py
├── Create composition root in mission_system/bootstrap.py
├── Eliminate 6 global singletons
└── Update API server to use AppContext

Phase 4: Gradual Migration (Ongoing)
├── Convert high-traffic paths to DI logging
├── Add get_current_logger() for legacy code
├── Add CI checks for print statements
└── Add CI checks for global loggers
```

---

## Appendix: Dependency Flow After Changes

```
┌─────────────────────────────────────────────────────────────────┐
│                      jeeves_protocols                           │
│                                                                 │
│  Owns: Protocols (contracts only)                               │
│  - LoggerProtocol                                               │
│  - LanguageConfigProtocol                                       │
│  - NodeProfilesProtocol                                         │
│  - AgentToolAccessProtocol                                      │
│  - AppContextProtocol                                           │
│  - SettingsProtocol, FeatureFlagsProtocol, etc.                │
│                                                                 │
│  NO implementations, NO globals, NO side effects                │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ depends on (protocols only)
┌─────────────────────────────┴───────────────────────────────────┐
│                      jeeves_avionics                            │
│                                                                 │
│  Owns: Infrastructure implementations                           │
│  - StructlogAdapter (implements LoggerProtocol)                 │
│  - Settings (implements SettingsProtocol)                       │
│  - FeatureFlags (implements FeatureFlagsProtocol)               │
│  - AppContext (implements AppContextProtocol)                   │
│  - RequestContext + contextvars helpers                         │
│                                                                 │
│  NO imports from mission_system or capabilities                 │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ depends on
┌─────────────────────────────┴───────────────────────────────────┐
│                    jeeves_mission_system                        │
│                                                                 │
│  COMPOSITION ROOT                                               │
│  - Creates AppContext with all dependencies                     │
│  - Injects capability configs into avionics                     │
│  - Owns request lifecycle and context propagation               │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ registers with
┌─────────────────────────────┴───────────────────────────────────┐
│               jeeves-capability-code-analyser                   │
│                                                                 │
│  Owns: Domain-specific implementations                          │
│  - LanguageConfig (implements LanguageConfigProtocol)           │
│  - NodeProfiles (implements NodeProfilesProtocol)               │
│  - AgentToolAccess (implements AgentToolAccessProtocol)         │
│  - All 7 agents, tools, prompts                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

*This ADR captures the architectural decisions made on 2025-12-07 to address findings from the Jeeves ecosystem audit.*

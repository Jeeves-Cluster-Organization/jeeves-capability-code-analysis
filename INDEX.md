# Jeeves Code Analyser - Repository Index

**Version:** 9.2 | **Status:** Production-Ready | **Updated:** 2025-12-13
**Architecture:** Hybrid Go-Python with 7-Agent Read-Only Pipeline
**Tech Stack:** Go 1.21+ (commbus, envelope CLI) + Python 3.11+ (application layer)

---

## Overview

This repository contains the Jeeves Code Analyser, a multi-agent AI system designed for read-only code analysis. The system uses a 7-agent pipeline to process user queries, explore codebases, and provide citation-backed responses grounded in actual source code.

**Go Migration Status:** Core engine and commbus have been migrated to Go at the repository root. Python layers call Go via subprocess/JSON bridge.

### Core Pipeline

```
User Query -> Perception -> Intent -> Planner -> Traverser -> Synthesizer -> Critic -> Integration -> Response
                                              ^_________replan_________v
```

### Governing Documents

| Document | Purpose |
|----------|---------|
| [docs/CONSTITUTION.md](docs/CONSTITUTION.md) | Non-negotiable principles, thresholds, Go layer rules |
| [docs/NORTH_STAR_TRAJECTORY.md](docs/NORTH_STAR_TRAJECTORY.md) | Target architecture, agent contracts, implementation status |
| [jeeves_control_tower/CONSTITUTION.md](jeeves_control_tower/CONSTITUTION.md) | Control Tower constitution (kernel layer) |
| [jeeves_memory_module/CONSTITUTION.md](jeeves_memory_module/CONSTITUTION.md) | Memory Module constitution (memory services) |
| [jeeves_avionics/CONSTITUTION.md](jeeves_avionics/CONSTITUTION.md) | Avionics constitution (infrastructure layer) |
| [jeeves_mission_system/CONSTITUTION.md](jeeves_mission_system/CONSTITUTION.md) | Mission System constitution (application layer) |
| [jeeves-capability-code-analyser/CONSTITUTION.md](jeeves-capability-code-analyser/CONSTITUTION.md) | Capability layer constitution |

**Note:** Go packages (`commbus/`, `coreengine/`) follow rules in docs/CONSTITUTION.md.

---

## Directory Structure (Hybrid Go-Python Architecture)

### Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       GO CORE (root level)                       │
├─────────────────────────────────────────────────────────────────┤
│  commbus/              →  Go messaging bus & protocols          │
│  coreengine/           →  Go orchestration runtime              │
│  cmd/envelope/         →  Go CLI for envelope operations        │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                        JSON/stdio bridge
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  PYTHON FOUNDATION (L0)                          │
├─────────────────────────────────────────────────────────────────┤
│  jeeves_protocols/         →  Type definitions, protocols        │
│  jeeves_shared/            →  Shared utilities (logging, UUID)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CONTROL TOWER (Kernel Layer)                   │
├─────────────────────────────────────────────────────────────────┤
│  jeeves_control_tower/     →  Lifecycle, resources, dispatch    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    Service dispatch via CommBus
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       PYTHON LAYERS                              │
├─────────────────────────────────────────────────────────────────┤
│  jeeves-capability-*/      →  Capability layer (domain agents)  │
│  jeeves_mission_system/    →  Application layer (API, verticals)│
│  jeeves_avionics/          →  Infrastructure (DB, LLM, gateway) │
│  jeeves_memory_module/     →  Memory services (L1-L5)           │
└─────────────────────────────────────────────────────────────────┘
```

**Dependency Flow:** `capability → mission_system → control_tower → avionics → protocols/shared → Go core`

---

### Go Core Layer (Root Level)

| Directory | Description | Key Files |
|-----------|-------------|-----------|
| [commbus/](commbus/) | Go messaging bus, protocol definitions | `bus.go`, `protocols.go`, `messages.go` |
| [coreengine/](coreengine/) | Go orchestration runtime | `agents/`, `config/`, `envelope/`, `runtime/` |
| [cmd/envelope/](cmd/envelope/) | Go CLI entry points | `main.go` |

**Go Module:** `github.com/jeeves-cluster-organization/codeanalysis` (see `go.mod`)

---

### Python Foundation (L0)

| Directory | Description | Key Files |
|-----------|-------------|-----------|
| [jeeves_protocols/](jeeves_protocols/) | Protocol definitions, type stubs for Go-Python interop | `protocols.py`, `interrupts.py`, `envelope.py` |
| [jeeves_shared/](jeeves_shared/) | Shared utilities (logging, serialization, UUID) | `logging/`, `serialization.py`, `uuid_utils.py` |

**jeeves_protocols exports (v3.0.0):**
- Core enums: `RiskLevel`, `ToolCategory`, `HealthStatus`, `CriticVerdict`, `OperationStatus`
- Protocols: `LoggerProtocol`, `DatabaseClientProtocol`, `LLMProviderProtocol`, `ToolExecutorProtocol`
- Envelope: `GenericEnvelope`, `ProcessingRecord`
- Config: `AgentConfig`, `PipelineConfig`, `CoreConfig`, `ContextBounds`
- Memory: `WorkingMemory`, `Finding`, `FocusState`, `EntityRef`, `MemoryItem`
- Agents: `UnifiedAgent`, `UnifiedRuntime`, `create_runtime_from_config`
- Interrupts: `InterruptKind`, `InterruptStatus`, `FlowInterrupt`, `RateLimitConfig`
- Capability: `CapabilityResourceRegistry`, `CapabilityServiceConfig`
- Go Client: `GoClient`, `create_envelope`, `check_bounds`

**jeeves_shared exports:**
- Logging: `JeevesLogger`, `configure_logging`, `create_logger`, `create_agent_logger`
- Serialization: `to_json`, `from_json`, `utc_now`, `utc_now_iso`, `parse_datetime`
- UUID: `uuid_str`, `uuid_read`, `convert_uuids_to_strings`, `UUIDStr`

---

### Control Tower (Kernel Layer)

| Directory | Description | CONSTITUTION |
|-----------|-------------|--------------|
| [jeeves_control_tower/](jeeves_control_tower/) | OS-style kernel: lifecycle, resources, dispatch | [CONSTITUTION](jeeves_control_tower/CONSTITUTION.md) |

**Components (v1.0.0):**
- `ControlTower` - Main kernel class (kernel.py)
- `LifecycleManager` - Request scheduling, process states (lifecycle/manager.py)
- `ResourceTracker` - Quota enforcement, usage tracking (resources/tracker.py)
- `CommBusCoordinator` - IPC manager, service dispatch (ipc/coordinator.py)
- `EventAggregator` - Interrupt handling, event streaming (events/aggregator.py)
- `InterruptService` - Unified interrupt handling (services/interrupt_service.py)

**Types:** `ProcessState`, `SchedulingPriority`, `ResourceQuota`, `ResourceUsage`, `ProcessControlBlock`, `ServiceDescriptor`, `KernelEvent`

---

### Memory Module

| Directory | Description | CONSTITUTION |
|-----------|-------------|--------------|
| [jeeves_memory_module/](jeeves_memory_module/) | Memory services (repositories, services, adapters) | [CONSTITUTION](jeeves_memory_module/CONSTITUTION.md) |

### Infrastructure Layer (Avionics)

| Directory | Description | INDEX |
|-----------|-------------|-------|
| [jeeves_avionics/](jeeves_avionics/) | Infrastructure wiring, settings, feature flags | [INDEX](jeeves_avionics/INDEX.md) |
| [jeeves_avionics/database/](jeeves_avionics/database/) | PostgreSQL/Redis clients and repositories | [INDEX](jeeves_avionics/database/INDEX.md) |
| [jeeves_avionics/llm/](jeeves_avionics/llm/) | LLM provider abstraction layer | [INDEX](jeeves_avionics/llm/INDEX.md) |
| [jeeves_avionics/gateway/](jeeves_avionics/gateway/) | FastAPI gateway with REST/SSE/WebSocket | - |
| [jeeves_avionics/distributed/](jeeves_avionics/distributed/) | Redis distributed bus | - |
| [jeeves_avionics/checkpoint/](jeeves_avionics/checkpoint/) | PostgreSQL checkpoint adapter | - |

**Core Exports:**
- Settings: `Settings`, `get_settings`, `reload_settings`
- Feature flags: `FeatureFlags`, `get_feature_flags`
- Thresholds: `CRITIC_APPROVAL_THRESHOLD`, `FUZZY_MATCH_MIN_SCORE`
- Context: `ContextBounds`, `AppContext` (via context.py)
- Runtime: `AgentRuntime`, `TimingContext`
- Wiring (lazy): `ToolExecutor`, `create_llm_provider_factory`
- Adapters (lazy): `PostgresCheckpointAdapter`, `RedisDistributedBus`
- Logging: `configure_logging`, `create_logger`, `trace_agent`, `trace_tool`

### Mission System (Application Layer)

| Directory | Description | INDEX |
|-----------|-------------|-------|
| [jeeves_mission_system/](jeeves_mission_system/) | Application layer root | [INDEX](jeeves_mission_system/INDEX.md) |
| [jeeves_mission_system/verticals/](jeeves_mission_system/verticals/) | Domain-specific verticals | [INDEX](jeeves_mission_system/verticals/INDEX.md) |
| [jeeves_mission_system/verticals/code_analysis/](jeeves_mission_system/verticals/code_analysis/) | Code analysis vertical | [INDEX](jeeves_mission_system/verticals/code_analysis/INDEX.md) |
| [jeeves_mission_system/orchestrator/](jeeves_mission_system/orchestrator/) | LangGraph flow orchestration | [INDEX](jeeves_mission_system/orchestrator/INDEX.md) |
| [jeeves_mission_system/api/](jeeves_mission_system/api/) | HTTP API server and endpoints | [INDEX](jeeves_mission_system/api/INDEX.md) |
| [jeeves_mission_system/services/](jeeves_mission_system/services/) | Application services | [INDEX](jeeves_mission_system/services/INDEX.md) |
| [jeeves_mission_system/common/](jeeves_mission_system/common/) | Shared utilities | [INDEX](jeeves_mission_system/common/INDEX.md) |
| [jeeves_mission_system/config/](jeeves_mission_system/config/) | Configuration management | [INDEX](jeeves_mission_system/config/INDEX.md) |
| [jeeves_mission_system/proto/](jeeves_mission_system/proto/) | gRPC protocol definitions | [INDEX](jeeves_mission_system/proto/INDEX.md) |
| [jeeves_mission_system/scripts/](jeeves_mission_system/scripts/) | Operational scripts | [INDEX](jeeves_mission_system/scripts/INDEX.md) |
| [jeeves_mission_system/tests/](jeeves_mission_system/tests/) | Test suites | [INDEX](jeeves_mission_system/tests/INDEX.md) |
| [jeeves_mission_system/static/](jeeves_mission_system/static/) | Static web assets | [INDEX](jeeves_mission_system/static/INDEX.md) |
| [jeeves_mission_system/systemd/](jeeves_mission_system/systemd/) | Systemd service definitions | [INDEX](jeeves_mission_system/systemd/INDEX.md) |
| [jeeves_mission_system/docs/](jeeves_mission_system/docs/) | Architecture documentation | [INDEX](jeeves_mission_system/docs/INDEX.md) |

---

## Key Files

### Go Core Files

| File/Directory | Purpose |
|----------------|---------|
| `go.mod` | Go module definition |
| `go.sum` | Go dependency checksums |
| `commbus/` | Go messaging bus package |
| `coreengine/` | Go orchestration runtime package |
| `cmd/envelope/` | Go CLI for envelope operations |

### Python/Build Files

| File/Directory | Purpose |
|----------------|---------|
| `app_bootstrap.py` | Application bootstrap, vertical registration |
| `conftest.py` | Pytest configuration and fixtures |
| `Makefile` | Build and run commands |
| `pytest.ini` | Test runner configuration |
| `docker/` | Docker configuration (multi-stage Go+Python build) |
| `requirements/` | Python dependencies (all.txt, base.txt, etc.) |
| `scripts/test.ps1` | PowerShell test runner |

---

## Testing

| Document | Purpose |
|----------|---------|
| [docs/POWERSHELL_TESTING.md](docs/POWERSHELL_TESTING.md) | **Comprehensive PowerShell testing guide** |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Test tiers and strategy |
| [docs/CI_STRATEGY.md](docs/CI_STRATEGY.md) | CI/CD pipeline configuration |
| [docs/RESET_PROCEDURE.md](docs/RESET_PROCEDURE.md) | Project reset procedures |

**Go Test Commands:**
```bash
go test ./...                              # All Go tests
go test -v ./commbus/... ./coreengine/...  # Verbose
go test -cover ./...                       # With coverage
```

**Python Test Commands (PowerShell):**
```powershell
.\scripts\test.ps1 ci         # Fast CI tests (< 10s)
.\scripts\test.ps1 avionics   # Avionics layer
.\scripts\test.ps1 full       # Complete flow (all tiers)
.\scripts\test.ps1 help       # Show all commands
```

---

## Core Principles (from Constitution)

1. **P1: Accuracy First** - Never hallucinate code. Every claim requires `[file:line]` citation.
2. **P2: Code Context Priority** - Understand fully before claiming.
3. **P3: Bounded Efficiency** - Be efficient within limits.

**Hierarchy:** P1 > P2 > P3 (when in conflict)

---

## Import Boundary Rules

### Go Layer (Self-Contained)

```
RULE 0: Go packages (commbus/, coreengine/) have NO Python dependencies
RULE 1: Go commbus is the foundation - coreengine depends on it
RULE 2: Go CLI (cmd/) depends on both commbus and coreengine
RULE 3: Go module: github.com/jeeves-cluster-organization/codeanalysis
```

### Python Foundation (L0)

```
RULE 4: jeeves_protocols and jeeves_shared are foundation layers
RULE 5: Foundation layers have NO dependencies on higher Python layers
RULE 6: All layers may import from foundation (protocols, shared)
RULE 7: jeeves_protocols v3.0.0 provides Python type bridge to Go
```

### Control Tower (Kernel Layer)

```
RULE 8: Control Tower ONLY imports from jeeves_protocols and jeeves_shared
RULE 9: Control Tower dispatches TO services, not imports FROM them
RULE 10: All requests route through ControlTower.submit_request()
RULE 11: Interrupt types come from jeeves_protocols.interrupts
RULE 12: Types exported: ProcessState, ResourceQuota, ServiceDescriptor, etc.
```

### Python Layers

```
RULE 13: Memory Module imports from protocols, shared, avionics.database.factory only
RULE 14: Avionics bridges to Go via subprocess/JSON (jeeves_avionics/interop/)
RULE 15: Avionics provides lazy imports to avoid circular dependencies
RULE 16: Mission System provides orchestration, API, and vertical registry
RULE 17: Capabilities use jeeves_protocols types and CapabilityResourceRegistry
```

**Dependency Flow:** `capability → mission_system → avionics → control_tower → protocols/shared → Go core`

**Enforcement:**
```bash
# Verify Go builds cleanly (self-contained)
go build ./...

# Check Python import boundaries
python jeeves_mission_system/scripts/check_import_boundaries.py
```

---

*This INDEX reflects the hybrid Go-Python architecture. Go core at root level, Python foundation (protocols/shared) at L0, higher application layers in subdirectories. See [docs/CONSTITUTION.md](docs/CONSTITUTION.md) for authoritative documentation.*

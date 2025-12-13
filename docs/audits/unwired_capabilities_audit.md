# Unwired Capabilities Audit

This document records the audit of unwired capabilities in the Jeeves codebase and the fixes implemented to complete the wiring.

## Phase 1 Fixes (Previous Session)

### 1. OpenTelemetry Integration
- **Location**: `jeeves_mission_system/bootstrap.py`
- **Change**: Wired `init_global_otel()` and integrated OTEL adapter with Control Tower
- **Trigger**: `FEATURE_ENABLE_TRACING=true`

### 2. Provider Streaming Support
- **Location**: `jeeves_avionics/llm/providers/*.py`
- **Change**: Added `generate_stream()` method to all providers (Anthropic, Azure, LlamaServer, LlamaCpp)
- **Interface**: Returns `AsyncIterator[TokenChunk]` for streaming responses

### 3. JSON Mode Support
- **Location**: `jeeves_avionics/llm/providers/openai.py`, `azure.py`
- **Change**: Added `response_format` parameter support for JSON mode
- **Usage**: Pass `response_format={"type": "json_object"}` in options

### 4. LLM Gateway Wiring
- **Location**: `jeeves_mission_system/bootstrap.py`
- **Change**: Gateway created in `create_avionics_dependencies()` when `use_llm_gateway=true`
- **Features**: Cost tracking, provider fallback, streaming support

### 5. run_worker.py Entry Point
- **Location**: `run_worker.py`
- **Change**: Created entry point for distributed worker processes
- **Usage**: See usage section below

## Phase 2 Fixes (This Session)

### 1. Per-Request PID Resource Tracking

**Problem**: The LLM Gateway resource callback was a placeholder returning `None`.

**Solution**: Implemented ContextVar-based per-request PID tracking:

```python
from jeeves_mission_system.bootstrap import (
    set_request_pid,
    get_request_pid,
    clear_request_pid,
)

# At request start
set_request_pid(envelope.envelope_id)

# ... LLM calls will now track usage against this PID ...

# At request end
clear_request_pid()
```

**Location**: `jeeves_mission_system/bootstrap.py`

### 2. Redis Distributed Bus Wiring

**Problem**: `RedisDistributedBus` existed but wasn't instantiated in bootstrap.

**Solution**: Added `create_distributed_infrastructure()` function:

```python
from jeeves_mission_system.bootstrap import create_distributed_infrastructure

# When feature flags enabled
if app_context.feature_flags.enable_distributed_mode:
    infra = create_distributed_infrastructure(
        app_context,
        postgres_client=postgres_client,  # Optional: for checkpoint persistence
    )
    distributed_bus = infra["distributed_bus"]
    worker_coordinator = infra["worker_coordinator"]
    checkpoint_adapter = infra["checkpoint_adapter"]  # If enable_checkpoints=true
```

**Required flags**:
- `FEATURE_ENABLE_DISTRIBUTED_MODE=true`
- `FEATURE_USE_REDIS_STATE=true`

### 3. Checkpoint Adapter Wiring

**Problem**: `PostgresCheckpointAdapter` existed but wasn't wired to distributed infrastructure.

**Solution**: Extended `create_distributed_infrastructure()` to create checkpoint adapter:

```python
# With checkpoints enabled
infra = create_distributed_infrastructure(
    app_context,
    postgres_client=my_postgres_client,  # Required for checkpoints
)
checkpoint_adapter = infra["checkpoint_adapter"]
# WorkerCoordinator is automatically wired with checkpoint_adapter
```

**Required flags**:
- `FEATURE_ENABLE_CHECKPOINTS=true`
- Plus a valid `postgres_client` parameter

### 4. Integration Tests

New test file: `jeeves_mission_system/tests/integration/test_unwired_audit_phase2.py`

Tests cover:
- OTEL span creation and lifecycle
- PID context isolation
- LLM Gateway resource callback with PID context
- Cost tracking per request and per provider
- Streaming chunk handling
- Distributed infrastructure creation
- Checkpoint adapter wiring
- Bootstrap integration

### 5. E2E Tests

New E2E test file: `jeeves_mission_system/tests/e2e/test_distributed_mode.py`

E2E tests cover:
- RedisDistributedBus task queue operations with real Redis
- Worker heartbeat mechanism
- Task completion and failure/retry flows
- WorkerCoordinator with Control Tower integration
- Multi-stage pipeline processing
- Bootstrap infrastructure creation with real Redis

Run E2E tests:
```bash
pytest jeeves_mission_system/tests/e2e/test_distributed_mode.py -v -s --tb=short
```

Requirements: Docker running (for testcontainers)

## Feature Flag Reference

| Flag | Description | Dependencies |
|------|-------------|--------------|
| `FEATURE_USE_LLM_GATEWAY=true` | Enable unified LLM gateway with cost tracking | None |
| `FEATURE_USE_REDIS_STATE=true` | Enable Redis for distributed state | `REDIS_URL` env var |
| `FEATURE_ENABLE_TRACING=true` | Enable OpenTelemetry distributed tracing | OTEL exporter config |
| `FEATURE_ENABLE_DISTRIBUTED_MODE=true` | Enable multi-node execution | `use_redis_state` |
| `FEATURE_ENABLE_CHECKPOINTS=true` | Enable checkpoint persistence for time-travel debugging | `postgres_client` param |
| `FEATURE_ENABLE_NODE_DISCOVERY=true` | Enable automatic node discovery | `enable_distributed_mode` |

## run_worker.py Usage

Start a distributed worker process:

```bash
# Basic usage - process all agent queues
python run_worker.py

# Specific queues
python run_worker.py --queues "agent:planner,agent:validator"

# Custom worker ID and concurrency
python run_worker.py --worker-id "gpu-node-1" --concurrency 10

# All options
python run_worker.py \
    --worker-id "worker-1" \
    --queues "agent:*" \
    --concurrency 5 \
    --heartbeat-interval 30
```

**Required environment variables**:
```bash
export FEATURE_ENABLE_DISTRIBUTED_MODE=true
export FEATURE_USE_REDIS_STATE=true
export REDIS_URL=redis://localhost:6379
```

## Resource Tracking Flow

```
Request Start
    |
    v
set_request_pid(envelope_id)
    |
    v
Control Tower allocates resources
    |
    v
[LLM Gateway calls]
    |-- callback gets PID from context
    |-- records usage to Control Tower
    |-- checks quota
    v
Request End
    |
    v
clear_request_pid()
    |
    v
Control Tower releases resources
```

## Architecture Compliance

All changes follow:
- **ADR-001**: Composition root pattern in bootstrap.py
- **Constitution P2**: No global state, dependency injection
- **Amendment XXIV**: Horizontal scaling via DistributedBusProtocol

## Verification

Run the integration tests:
```bash
pytest jeeves_mission_system/tests/integration/test_unwired_audit_phase2.py -v
```

Run all integration tests:
```bash
pytest -m integration
```

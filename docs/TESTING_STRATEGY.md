# Testing Strategy

**Version**: 3.1 | **Date**: 2025-12-13

---

## Overview

Testing strategy organized by language runtime (Go vs Python) and constitutional layer. All practices align with constitutional hierarchy.

**Hybrid Architecture:** Go core (commbus, coreengine) + Python application layers

---

## Go Core Testing

### Go Test Commands

```bash
# Run all Go tests
go test ./...

# Verbose output
go test -v ./commbus/... ./coreengine/...

# With coverage
go test -cover ./...

# Specific package
go test -v ./coreengine/envelope/...

# With race detection
go test -race ./...
```

### Go Test Coverage

| Package | Tests | Purpose |
|---------|-------|---------|
| `commbus/` | Unit | Message bus, protocols, middleware |
| `coreengine/agents/` | Unit | Agent contracts |
| `coreengine/config/` | Unit | Core configuration |
| `coreengine/envelope/` | Unit | GenericEnvelope operations |

---

## Python Layer Testing

### Constitutional Layers

```
┌─────────────────────────────────────────────┐
│ Capability (jeeves-capability-code-analyser) │
│ Tests: All mocked, no external deps          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Mission System (jeeves_mission_system)       │
│ Tests: Contract, Unit, Integration, E2E      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Memory Module (jeeves_memory_module)         │
│ Tests: Unit + Protocol compliance            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Avionics (jeeves_avionics)                   │
│ Tests: Unit + Integration (Docker)           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Control Tower (jeeves_control_tower)         │
│ Tests: Unit (lifecycle, resources, IPC)      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ Foundation (jeeves_protocols, jeeves_shared) │
│ Tests: Unit (type validation, utilities)     │
└──────────────────┬──────────────────────────┘
                   │
                   ↓ (via interop bridge)
┌─────────────────────────────────────────────┐
│ Go Core (commbus/, coreengine/)              │
│ Tests: go test ./... (self-contained)        │
└─────────────────────────────────────────────┘
```

---

## Test Tiers

### Tier 1: Fast Unit Tests (< 10s)

**Dependencies**: None (all mocked)

**PowerShell:**
```powershell
.\test.ps1 ci
# Or individual layers:
.\test.ps1 core
.\test.ps1 avionics
.\test.ps1 memory
.\test.ps1 app
```

**Bash:**
```bash
# Go tests first (always run)
go test ./...

# Python tests
make test-tier1
# Or:
pytest -c pytest-light.ini \
    jeeves_avionics/tests/unit/llm \
    jeeves_mission_system/tests/contract \
    jeeves-capability-code-analyser/tests -v
```

**Coverage**:
- Go commbus (protocols, bus, middleware)
- Go coreengine (envelope, config, agents)
- Memory module (protocol compliance)
- Avionics LLM cost calculator (33 tests)
- Mission system contract tests
- Capability layer (all mocked)

**Use Case**: Pre-commit hooks, fast CI, local development

---

### Tier 2: Integration Tests (10-30s)

**Dependencies**: Docker (PostgreSQL)

**PowerShell:**
```powershell
docker compose -f docker/docker-compose.yml up -d postgres
.\test.ps1 tier2
```

**Bash:**
```bash
docker compose up -d postgres
make test-tier2
```

**Coverage**:
- Avionics database tests
- Mission system unit tests

**Use Case**: CI pipeline, integration validation

---

### Tier 3: LLM Integration (1-2 min)

**Dependencies**: Docker (PostgreSQL + llama-server)

**PowerShell:**
```powershell
docker compose -f docker/docker-compose.yml up -d postgres llama-server
.\test.ps1 tier3
```

**Bash:**
```bash
docker compose up -d postgres llama-server
make test-tier3
```

**Coverage**:
- Real LLM calls
- Agent pipeline tests

**Use Case**: Pre-release validation

---

### Tier 4: E2E Tests (2-5 min)

**Dependencies**: Full stack (all services)

**PowerShell:**
```powershell
docker compose -f docker/docker-compose.yml up -d
.\test.ps1 tier4
```

**Bash:**
```bash
docker compose up -d
make test-tier4
```

**Coverage**:
- Full system integration
- HTTP API tests
- 7-agent pipeline

**Use Case**: Release validation

---

### Full Flow Testing

**PowerShell (Recommended):**
```powershell
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Wait for services
Start-Sleep -Seconds 15

# Run complete flow
.\test.ps1 full
```

**Bash:**
```bash
# Start all services
docker compose up -d

# Wait for services
sleep 15

# Run complete flow
make test-nightly
```

---

## Quick Reference

### By Layer

**Go Core:**
```bash
go test ./commbus/...            # CommBus (< 1s)
go test ./coreengine/...         # Core engine (< 1s)
go test ./...                    # All Go tests
```

**Python (PowerShell):**
```powershell
.\test.ps1 memory     # Memory module (< 5s)
.\test.ps1 avionics   # Avionics lightweight (< 2s)
.\test.ps1 mission    # Mission system (lightweight)
.\test.ps1 app        # Capability layer (< 3s)
```

**Python (Bash):**
```bash
pytest jeeves_memory_module/tests -v
pytest jeeves_avionics/tests -m "not heavy" -v
pytest jeeves_mission_system/tests -v
pytest jeeves-capability-code-analyser/tests -v
```

### By Speed

**Go (always run first):**
```bash
go test ./...         # Go tests (< 2s)
```

**Python (PowerShell):**
```powershell
.\test.ps1 ci         # Fast Python (< 10s)
.\test.ps1 tier2      # Medium (< 30s)
.\test.ps1 tier3      # Slow (< 2min)
.\test.ps1 full       # Complete (< 5min)
```

**Python (Bash):**
```bash
make test-tier1       # Fast (< 10s)
make test-tier2       # Medium (< 30s)
make test-tier3       # Slow (< 2min)
make test-nightly     # Complete (< 5min)
```

---

## Test Markers

```python
@pytest.mark.heavy           # Requires ML models
@pytest.mark.requires_docker # Requires PostgreSQL
@pytest.mark.requires_llm    # Requires llama-server
@pytest.mark.requires_ml     # Requires sentence-transformers
@pytest.mark.e2e             # End-to-end test
@pytest.mark.snapshot        # Snapshot test
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# Go tests (always run first)
- name: Go Tests
  run: go test ./...

# Fast Python tests on every commit
- name: Python Tier 1
  run: make test-tier1

# Integration tests on PR
- name: Python Tier 2
  run: make test-tier2

# Full suite before merge
- name: Full Suite
  run: make test-nightly
```

### Pre-commit Hook

**With Go:**
```bash
#!/bin/bash
# Run Go tests first
go test ./... || exit 1
# Then Python tests
make test-tier1 || exit 1
```

**PowerShell:**
```powershell
go test ./...
if ($LASTEXITCODE -ne 0) { exit 1 }
.\test.ps1 ci
if ($LASTEXITCODE -ne 0) { exit 1 }
```

---

## Best Practices

1. **Layer Isolation**: Tests should only import from allowed layers
2. **Mock External Deps**: No network, database, or filesystem in Tier 1
3. **Deterministic**: Use fixed seeds, mock time/IDs
4. **Fast Feedback**: Tier 1 should run in < 10s
5. **Contract Tests**: Validate constitutional boundaries
6. **Protocol Compliance**: Verify protocol implementations

---

## Troubleshooting

### Tests Failing Due to Missing Services

**PowerShell:**
```powershell
# Check services
.\test.ps1 services

# Start required services
docker compose -f docker/docker-compose.yml up -d postgres llama-server
```

**Bash:**
```bash
# Check services
docker compose ps

# Start required services
docker compose up -d postgres llama-server
```

### Import Errors

```bash
# Install dev dependencies
pip install -r requirements/all.txt

# Check Python path (PowerShell)
$env:PYTHONPATH = "$env:PYTHONPATH;$(Get-Location)"

# Check Python path (Bash)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Slow Tests

**PowerShell:**
```powershell
.\test.ps1 ci
```

**Bash:**
```bash
make test-tier1
# Or skip heavy tests:
pytest -m "not heavy and not requires_docker" -v
```

---

## Related Documentation

- [POWERSHELL_TESTING.md](POWERSHELL_TESTING.md) - Comprehensive PowerShell testing guide
- [CI_STRATEGY.md](CI_STRATEGY.md) - CI/CD pipeline configuration
- [RESET_PROCEDURE.md](RESET_PROCEDURE.md) - Project reset procedures

---

*Last Updated: 2025-12-13*

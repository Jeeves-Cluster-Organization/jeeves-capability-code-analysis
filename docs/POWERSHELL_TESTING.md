# PowerShell Testing Guide

**Version:** 2.0 | **Date:** 2025-12-10
**For Windows/PowerShell Users**

---

## Quick Start

### PowerShell Test Runner (Recommended)

```powershell
# Run CI tests (fastest)
.\scripts\test.ps1 ci

# Run specific layer
.\scripts\test.ps1 core
.\scripts\test.ps1 avionics
.\scripts\test.ps1 app

# Run full flow (all tiers)
.\scripts\test.ps1 full

# Show help
.\scripts\test.ps1 help
```

### Direct pytest Commands

```powershell
# CI tests (< 10s, no external deps)
python -m pytest -c pytest-light.ini `
    jeeves_protocols/tests `
    jeeves_avionics/tests/unit/llm `
    jeeves-capability-code-analyser/tests -v

# Protocols only (< 1s)
python -m pytest jeeves_protocols/tests -v

# Memory module tests
python -m pytest jeeves_memory_module/tests -v

# App layer (< 3s)
python -m pytest jeeves-capability-code-analyser/tests -v
```

---

## Full Flow Testing

### Complete System Test (All Tiers)

```powershell
# 1. Start all Docker services
docker compose -f docker/docker-compose.yml up -d

# 2. Wait for services to be ready
Start-Sleep -Seconds 15

# 3. Check services are healthy
.\scripts\test.ps1 services

# 4. Run full test flow
.\scripts\test.ps1 full

# Or run each tier individually:
.\scripts\test.ps1 core       # Tier 0: Core engine (< 1s)
.\scripts\test.ps1 ci         # Tier 1: Fast tests (< 10s)
.\scripts\test.ps1 tier2      # Tier 2: Database integration (10-30s)
.\scripts\test.ps1 tier3      # Tier 3: LLM integration (30-60s)
.\scripts\test.ps1 tier4      # Tier 4: E2E (60+ s)
```

### Constitution Layer Testing

```powershell
# Test each constitutional layer in dependency order:

# 1. Foundation Layer (CommBus) - Zero dependencies
python -m pytest jeeves_commbus/tests -v

# 2. Protocols Layer
python -m pytest jeeves_protocols/tests -v

# 3. Memory Module Layer
python -m pytest jeeves_memory_module/tests -v

# 4. Infrastructure Layer (Avionics)
python -m pytest jeeves_avionics/tests -m "not heavy" -v

# 5. Application Layer (Mission System)
python -m pytest jeeves_mission_system/tests/unit -v

# 6. Capability Layer
python -m pytest jeeves-capability-code-analyser/tests -v
```

---

## Test Runner Commands

### Fast Tests (No Dependencies)

| Command | Description | Runtime |
|---------|-------------|---------|
| `.\scripts\test.ps1 ci` | CI suite (Core + Avionics + App) | < 10s |
| `.\scripts\test.ps1 core` | Core engine (128 tests) | < 1s |
| `.\scripts\test.ps1 avionics` | Avionics lightweight (33 tests) | < 2s |
| `.\scripts\test.ps1 app` | App layer (mocked) | < 3s |
| `.\scripts\test.ps1 contract` | Constitutional contract tests | < 5s |

### Integration Tests (Requires Docker)

| Command | Description | Prerequisites |
|---------|-------------|---------------|
| `.\scripts\test.ps1 tier2` | Database integration | `docker compose up -d postgres` |
| `.\scripts\test.ps1 tier3` | LLM integration | `docker compose up -d postgres llama-server` |
| `.\scripts\test.ps1 tier4` | E2E (full stack) | `docker compose up -d` |
| `.\scripts\test.ps1 full` | All tiers sequentially | `docker compose up -d` |

### Layer-Specific Commands

| Command | Description | Dependencies |
|---------|-------------|--------------|
| `.\scripts\test.ps1 mission` | Mission system (lightweight) | None |
| `.\scripts\test.ps1 mission-full` | Mission system (with services) | Docker |
| `.\scripts\test.ps1 memory` | Memory module tests | None |

---

## Common Tasks

### Run Tests Before Commit

```powershell
# Fast check (recommended)
.\scripts\test.ps1 ci

# Full check with integration
docker compose -f docker/docker-compose.yml up -d postgres
.\scripts\test.ps1 tier2
```

### Debug Failing Tests

```powershell
# Run with verbose output
python -m pytest jeeves_protocols/tests -v -s

# Run specific test
python -m pytest jeeves_protocols/tests/unit/test_envelope.py::test_envelope_creation -v

# Run with traceback
python -m pytest jeeves_protocols/tests -v --tb=long
```

### Check Services

```powershell
# Check if Docker services are running
.\scripts\test.ps1 services

# Or manually:
docker compose -f docker/docker-compose.yml ps

# Start required services
docker compose -f docker/docker-compose.yml up -d postgres llama-server

# View logs
docker compose -f docker/docker-compose.yml logs -f
```

---

## Layer-by-Layer Testing

### By Constitution Layer

```powershell
# CommBus (Foundation - zero deps)
python -m pytest jeeves_commbus/tests -v

# Protocols
python -m pytest jeeves_protocols/tests -v

# Memory module
python -m pytest jeeves_memory_module/tests -v

# Avionics (lightweight)
python -m pytest jeeves_avionics/tests -m "not heavy and not requires_ml" -v

# Mission system
python -m pytest jeeves_mission_system/tests -v

# Capability layer
python -m pytest jeeves-capability-code-analyser/tests -v
```

### By Test Tier

```powershell
# Tier 1: Fast (< 10s)
python -m pytest -c pytest-light.ini `
    jeeves_protocols/tests `
    jeeves_avionics/tests/unit/llm `
    jeeves-capability-code-analyser/tests -v

# Tier 2: Integration (10-30s)
python -m pytest jeeves_avionics/tests/unit/database -v
python -m pytest jeeves_mission_system/tests/unit -v

# Tier 3: LLM Integration (30-60s)
python -m pytest jeeves_mission_system/tests/integration -m "not e2e" -v

# Tier 4: E2E (60+ s)
python -m pytest jeeves_mission_system/tests -m e2e -v
```

---

## Docker Services

### Start Services

```powershell
# Start all services
docker compose -f docker/docker-compose.yml up -d

# Start specific services
docker compose -f docker/docker-compose.yml up -d postgres
docker compose -f docker/docker-compose.yml up -d postgres llama-server

# Build with cache-busting (ensures latest code)
$env:CODE_VERSION = $(git rev-parse --short HEAD)
docker compose -f docker/docker-compose.yml build
```

### Stop Services

```powershell
# Stop all services
docker compose -f docker/docker-compose.yml down

# Stop and remove volumes
docker compose -f docker/docker-compose.yml down -v

# Full cleanup
docker compose -f docker/docker-compose.yml down -v --rmi local
```

### Service Health Checks

```powershell
# Check PostgreSQL
docker compose -f docker/docker-compose.yml exec postgres pg_isready

# Check llama-server
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing

# Check gateway
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing
```

---

## Troubleshooting

### Import Errors

```powershell
# Install dependencies
pip install -r requirements/all.txt

# Add to PYTHONPATH
$env:PYTHONPATH = "$env:PYTHONPATH;$(Get-Location)"

# Verify imports
python -c "from jeeves_protocols import GenericEnvelope; print('OK')"
python -c "from jeeves_commbus import LLMProviderProtocol; print('OK')"
```

### Docker Not Running

```powershell
# Check Docker
docker --version

# Start Docker Desktop (Windows)
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Start services
docker compose -f docker/docker-compose.yml up -d postgres
```

### Tests Taking Too Long

```powershell
# Run only fast tests
.\scripts\test.ps1 ci

# Skip slow markers
python -m pytest -m "not heavy and not requires_docker" -v

# Run with timeout
python -m pytest --timeout=30 -v
```

### Port Conflicts

```powershell
# Check what's using ports
netstat -ano | Select-String ":5432"   # PostgreSQL
netstat -ano | Select-String ":8080"   # llama-server
netstat -ano | Select-String ":8001"   # Gateway

# Kill process by PID
Stop-Process -Id <PID> -Force
```

---

## Project Reset

For a complete project reset, use the Reset script:

```powershell
# Full reset to main branch
.\scripts\Reset-Project.ps1

# Or manual reset:
git fetch origin main
git checkout main
git reset --hard origin/main
git clean -fdx
```

See [RESET_PROCEDURE.md](RESET_PROCEDURE.md) for detailed reset steps.

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

### Skip by Marker

```powershell
# Skip heavy tests
python -m pytest -m "not heavy" -v

# Skip Docker-dependent tests
python -m pytest -m "not requires_docker" -v

# Skip all slow tests
python -m pytest -m "not heavy and not requires_docker and not requires_llm" -v
```

---

## Related Documentation

- [TESTING_STRATEGY.md](TESTING_STRATEGY.md) - Complete testing strategy with tier descriptions
- [CI_STRATEGY.md](CI_STRATEGY.md) - CI/CD pipeline configuration
- [RESET_PROCEDURE.md](RESET_PROCEDURE.md) - Project reset procedures
- [README.md](../README.md) - Project overview and quick start

---

*Last Updated: 2025-12-10*

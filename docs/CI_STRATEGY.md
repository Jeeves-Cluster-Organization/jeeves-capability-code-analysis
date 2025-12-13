# CI/CD Test Strategy

**Status**: Active
**Last Updated**: 2025-12-10

---

## Overview

This document defines the CI/CD testing strategy for the Jeeves Code Analyser system. The strategy prioritizes **fast, reliable tests** in CI while supporting **comprehensive testing** locally and in nightly builds.

**Architecture:** Hybrid Go-Python (Go core at root level, Python application layers)

---

## Core Principles

1. **Fast Feedback in CI** - CI tests complete in < 15 seconds (Go + Python)
2. **Go Tests Always Run** - Go core tests are fast and deterministic
3. **No External Dependencies in CI** - No Docker, LLM, or heavy ML models
4. **Reliable Tests Only** - Skip flaky tests in CI (run them in nightly builds)
5. **Local Testing Flexibility** - Developers can run full test suite locally

---

## CI Test Matrix

### GitHub Actions CI (Fast - Every Commit)

**Target**: `go test ./... && make test-ci`

**What Runs**:
- ✅ **Go core tests** (commbus, coreengine - < 2s)
- ✅ Avionics LLM tests (33 tests, < 2s)
- ✅ App layer tests (all mocked, < 3s)

**What's Skipped**:
- ❌ Mission system tests (flaky - require real LLM)
- ❌ Database tests (require Docker)
- ❌ ML model tests (require sentence-transformers, 1.5GB)
- ❌ E2E tests (require full stack)

**Expected Runtime**: < 15 seconds

**Commands**:
```bash
# Go tests first (always run)
go test ./...

# Python tests
make test-ci
```

**Why Skip Mission System in CI?**
- Mission system tests require real llamaserver (non-deterministic LLM responses)
- Tests are flaky due to network timeouts and LLM variability
- Would require GitHub Actions credits for llamaserver service
- Better suited for nightly builds or local pre-PR validation

---

### Pre-Commit Hooks (Local Only)

**Target**: `.pre-commit-config.yaml` or `.git/hooks/pre-commit`

**What Runs** (based on changed files):
- If `coreengine/` or `jeeves_protocols/` changed → Run core/protocols tests
- If `jeeves_avionics/` changed → Run avionics lightweight tests
- If `jeeves-capability-code-analyser/` changed → Run app tests
- Mission system → **Skipped** (run manually with `make test-mission`)

**Installation**:
```bash
# Option 1: Using pre-commit framework (recommended)
pip install pre-commit
pre-commit install

# Option 2: Manual hook (already created in .git/hooks/pre-commit)
# Just ensure it's executable (already done)
```

**Skip Hook** (for WIP commits):
```bash
git commit --no-verify -m "WIP: skip tests"
```

**Why Pre-Commit Hooks?**
- Catches issues before pushing
- Fast (only runs tests for changed files)
- Runs locally (no GitHub Actions credits needed)
- Skips flaky mission system tests

---

### Nightly Builds (Full Suite)

**Target**: `make test-nightly`

**Prerequisites**:
```bash
docker compose up -d  # All services (postgres, llama-server)
```

**What Runs**:
- ✅ Tier 1: Fast unit tests
- ✅ Tier 2: Database integration tests
- ✅ Tier 3: Integration tests with real LLM
- ✅ Tier 4: E2E tests

**Expected Runtime**: 5-10 minutes

**Schedule**: Daily at 2 AM (or on-demand)

**Command**:
```bash
make test-nightly
```

---

## Test Tiers Reference

| Tier | Command | Dependencies | Runtime | CI | Local | Nightly |
|------|---------|--------------|---------|----|----|---------|
| **Tier 1** | `make test-tier1` | None | < 10s | ✅ | ✅ | ✅ |
| **Tier 2** | `make test-tier2` | Docker (Postgres) | 10-30s | ❌ | ✅ | ✅ |
| **Tier 3** | `make test-tier3` | Docker (Postgres + LLM) | 30-60s | ❌ | ✅ | ✅ |
| **Tier 4** | `make test-tier4` | Full stack | 60+ s | ❌ | ✅ | ✅ |

---

## Layer-Specific CI Strategy

### Go Core (`commbus/`, `coreengine/`)

**CI**: ✅ **Always Run**
- 100% reliable (self-contained, no external deps)
- Fast execution (< 2 seconds)
- Constitutional foundation - must always pass

**Commands**:
```bash
go test ./commbus/...     # CommBus tests
go test ./coreengine/...  # Core engine tests
go test ./...             # All Go tests
```

**Failures**: Block merge

### Avionics (`jeeves_avionics`)

**CI**: ✅ **Lightweight Tests Only**
- LLM cost calculator (16 tests)
- Mock provider tests (17 tests)
- Skip: Database tests (require Docker)
- Skip: ML model tests (require sentence-transformers)

**Local/Nightly**: Run full suite with Docker

**Failures**: Block merge

### Mission System (`jeeves_mission_system`)

**CI**: ❌ **Skipped** (Flaky)
- Requires real LLM (non-deterministic)
- Network timeouts to llamaserver
- Would require GitHub Actions credits

**Local**: Run before PR
```bash
# Lightweight (no services)
make test-mission

# Full (with services)
docker compose up -d postgres llama-server
make test-mission-full
```

**Nightly**: Run full suite

**Failures**: Warning only (don't block merge due to flakiness)

### App Layer (`jeeves-capability-code-analyser`)

**CI**: ✅ **Always Run**
- All tests use mocks (no external deps)
- Fast and reliable
- Constitutional compliance tests

**Failures**: Block merge

---

## GitHub Actions Configuration

### Fast CI Workflow (Every Commit)

```yaml
# .github/workflows/test-fast.yml
name: Fast Tests

on:
  push:
    branches: [ main, develop, claude/* ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test-fast:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run Go tests
        run: go test ./...

      - name: Install Python dependencies
        run: |
          pip install pytest pytest-asyncio pydantic structlog anyio

      - name: Run Python tests
        run: make test-ci

      - name: Report
        if: always()
        run: |
          echo "✅ Go + Python tests complete"
          echo "Note: Mission system tests skipped (flaky)"
```

**No Credits Needed**: Uses only built-in runners, no services.

### Nightly Workflow (Full Suite)

```yaml
# .github/workflows/test-nightly.yml (OPTIONAL - requires Docker credits)
name: Nightly Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
  workflow_dispatch:  # Manual trigger

jobs:
  test-nightly:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      llama-server:
        image: ghcr.io/ggerganov/llama.cpp:server
        # ... (if available)

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements/test.txt
      - name: Run nightly tests
        run: make test-nightly
```

**Note**: This workflow requires GitHub Actions credits for services. Optional.

---

## Local Development Workflow

### 1. During Development (Fast Feedback)

```bash
# Go tests (always fast)
go test ./...                    # All Go tests
go test ./commbus/...            # CommBus only
go test ./coreengine/...         # Core engine only

# Python tests for specific layer
make test-avionics   # Avionics lightweight (< 2s)
make test-app        # App layer (< 3s)
```

### 2. Before Commit (Pre-commit Hook)

```bash
# Automatic (if pre-commit installed)
git commit -m "feat: new feature"
# Hook runs tests for changed files

# Manual
.git/hooks/pre-commit

# Skip hook (WIP commits)
git commit --no-verify -m "WIP"
```

### 3. Before Push (Mission System)

```bash
# Lightweight mission system tests
make test-mission

# Or full suite
docker compose up -d postgres llama-server
make test-mission-full
```

### 4. Before PR (Integration Tests)

```bash
# Start services
docker compose up -d postgres llama-server

# Run Tier 2 + 3
make test-tier2
make test-tier3
```

### 5. Release Validation (Full E2E)

```bash
# Start all services
docker compose up -d

# Run full nightly suite
make test-nightly
```

---

## Handling Flaky Tests

### Mission System Flakiness

**Root Causes**:
1. LLM non-determinism (responses vary)
2. Network timeouts (llamaserver)
3. Small models (< 7B) fail on nuanced NLP
4. Database race conditions
5. Async timing issues

**Strategy**:
- ✅ **CI**: Skip entirely (too unreliable)
- ✅ **Local**: Run before PR (manual validation)
- ✅ **Nightly**: Run with retries and timeouts
- ✅ **Documentation**: Mitigation strategies in TESTING_STRATEGY.md

**Do NOT**:
- ❌ Block CI on flaky tests
- ❌ Spend credits on unreliable tests
- ❌ Run in GitHub Actions without service credits

---

## Quick Reference

### CI Commands

```bash
# Go tests (always run first)
go test ./...

# Fast Python CI (< 10s, no external deps)
make test-ci

# Check services status
make test-services-check

# Contract tests only (< 5s)
make test-contract
```

### Local Commands

```bash
# Pre-commit hook setup
pip install pre-commit
pre-commit install

# Go tests (fast feedback)
go test -v ./...

# Fast Python tests
make test-fast

# Full local suite
docker compose up -d
make test-nightly
```

### Skip Mission System

```bash
# CI (already skips mission system)
make test-ci

# Lightweight (skips mission system integration)
pytest -c pytest-light.ini

# Manual mission system testing
make test-mission  # Lightweight
make test-mission-full  # With services
```

---

## Troubleshooting

### Issue: Pre-commit hook fails

**Solution**: Skip for WIP commits
```bash
git commit --no-verify -m "WIP: work in progress"
```

### Issue: CI tests fail locally

**Solution**: Run exact CI command
```bash
make test-ci
```

### Issue: Mission system tests needed for PR

**Solution**: Run locally before pushing
```bash
docker compose up -d postgres llama-server
make test-mission-full
```

---

## Summary

| Environment | Tests Run | Dependencies | Runtime | Credits |
|-------------|-----------|--------------|---------|---------|
| **CI (GitHub Actions)** | Go + Avionics (light) + App | Go 1.21, Python 3.11 | < 15s | Free |
| **Pre-commit (Local)** | Go + changed Python files | None | < 5s | N/A |
| **Local (Pre-PR)** | Go + all Python except E2E | Docker | 1-2 min | N/A |
| **Nightly (Optional)** | Full suite | Docker + LLM | 5-10 min | Optional |

**Key Decisions**:
- Go tests **ALWAYS RUN** (fast, reliable, deterministic)
- Mission system tests are **SKIPPED in CI** due to flakiness and credit requirements
- Developers run mission system tests locally before PRs

---

**Maintained by**: Jeeves Engineering Team
**Last Updated**: 2025-12-10
**Next Review**: 2026-01-10

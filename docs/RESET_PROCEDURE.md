# Project Reset Procedure

Complete reset procedure to bring the project to a clean state from main branch.

## Quick Start

**Automated (Recommended):**
```powershell
./scripts/Reset-Project.ps1
```

## Manual Steps (if needed)

### 1. Git Reset to Main
```powershell
# Fetch latest
git fetch origin main

# Hard reset to main (⚠️ DESTROYS LOCAL CHANGES)
git checkout main
git reset --hard origin/main
git clean -fdx
```

### 2. Clean Python Artifacts
```powershell
# Remove Python cache
Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" | Remove-Item -Force
Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter "*.egg-info" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter ".mypy_cache" | Remove-Item -Recurse -Force

# Remove build artifacts
Get-ChildItem -Path . -Recurse -Directory -Filter "build" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Directory -Filter "dist" | Remove-Item -Recurse -Force

# Remove test artifacts
Remove-Item .coverage -Force -ErrorAction SilentlyContinue
Remove-Item htmlcov -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -File -Filter "*.db*" | Remove-Item -Force

# Remove virtual environments
Remove-Item venv, .venv, env -Recurse -Force -ErrorAction SilentlyContinue
```

### 3. Clean Node.js Artifacts
```powershell
# Remove node_modules
Get-ChildItem -Path . -Recurse -Directory -Filter "node_modules" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -File -Filter "package-lock.json" | Remove-Item -Force
```

### 4. Docker Cleanup
```powershell
# Stop all containers
docker compose -f docker/docker-compose.yml down -v

# Remove project images
docker images | Select-String "assistant-gateway|assistant-7agent|codeanalysis" | ForEach-Object {
    $imageId = ($_ -split '\s+')[2]
    docker rmi -f $imageId
}

# Clean up dangling images
docker image prune -f

# Clean up unused volumes
docker volume prune -f

# Optional: Nuclear option (removes ALL unused Docker resources)
docker system prune -a --volumes -f
```

### 5. Fresh Install Dependencies
```powershell
# Update pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install -r requirements/all.txt

# Install frontend dependencies
cd jeeves_mission_system/tests/frontend
npm install
cd ../../..
```

### 6. Verification
```powershell
# Run Tier 1 tests (fast, no external deps)
make test-tier1

# Or use PowerShell directly
python -m pytest -c pytest-light.ini `
    jeeves_protocols/tests `
    jeeves_avionics/tests/unit/llm `
    jeeves_mission_system/tests/contract `
    jeeves-capability-code-analyser/tests `
    -v
```

### 7. Start Services & Full Test
```powershell
# Start all Docker services
docker compose -f docker/docker-compose.yml up -d

# Wait for services to be ready
Start-Sleep -Seconds 10

# Run Tier 2 tests (requires Docker)
make test-tier2

# Run Tier 3 tests (requires Docker + LLM)
make test-tier3

# Run full test suite
make test-nightly
```

## Debugging Dependencies

### Check Python Environment
```powershell
# Check Python version
python --version

# Check installed packages
pip list

# Check for missing dependencies
pip check
```

### Check Node.js Environment
```powershell
# Check Node version
node --version

# Check npm version
npm --version

# Verify frontend installation
cd jeeves_mission_system/tests/frontend
npm ls
```

### Check Docker Services
```powershell
# Check running containers
docker compose -f docker/docker-compose.yml ps

# Check logs
docker compose -f docker/docker-compose.yml logs

# Check specific service
docker compose -f docker/docker-compose.yml logs postgres
docker compose -f docker/docker-compose.yml logs llama-server

# Test service health
curl http://localhost:8080/health  # llama-server
```

### Rebuild Docker Images
```powershell
# Build from scratch (no cache)
docker compose -f docker/docker-compose.yml build --no-cache

# Rebuild specific service
docker compose -f docker/docker-compose.yml build --no-cache postgres
```

## Common Issues

### Issue: Tests still failing after reset
**Solution:** Check if Docker services are running
```powershell
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps
```

### Issue: Import errors in Python
**Solution:** Reinstall dependencies in clean environment
```powershell
pip install --force-reinstall -r requirements/all.txt
```

### Issue: Docker containers won't start
**Solution:** Remove volumes and restart
```powershell
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

### Issue: Port conflicts
**Solution:** Check what's using the ports
```powershell
# Check port 5432 (PostgreSQL)
netstat -ano | Select-String ":5432"

# Check port 8080 (llama-server)
netstat -ano | Select-String ":8080"
```

## Test Tier Reference

- **Tier 1**: Fast unit tests (no external deps) - < 10 seconds
- **Tier 2**: Integration tests (requires Docker) - 10-30 seconds
- **Tier 3**: Integration with LLM (requires Docker + llama-server) - 30-60 seconds
- **Tier 4**: E2E tests (full stack) - 60+ seconds

## Files Changed During Reset

The reset script will:
- ✅ Preserve: `.git/`, `.env`, source code (after reset to main)
- ❌ Delete: `__pycache__/`, `node_modules/`, `*.pyc`, `.pytest_cache/`, build artifacts
- ❌ Delete: Docker images/containers matching `assistant-*` or `codeanalysis-*`
- ❌ Delete: All untracked files via `git clean -fdx`

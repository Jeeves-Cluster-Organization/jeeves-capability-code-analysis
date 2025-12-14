# Root Cause Analysis: Module Import Failures at Orchestrator Startup

**Date:** 2025-12-14
**Severity:** CRITICAL - System Cannot Start
**Status:** REQUIRES IMMEDIATE FIX

---

## Executive Summary

The orchestrator crashes immediately on startup with `ModuleNotFoundError: No module named 'tools.robust_tool_base'`. This is **NOT a Docker or deployment issue** - it's an **incomplete implementation** where multiple files import modules that were **never created**.

**Root Cause:** Code was written referencing planned architectural components (`RobustToolExecutor`, `make_strategy`, etc.) that exist in design documents and the Constitution, but were never actually implemented. This is coupled with an incomplete migration from the old `tool_registry` singleton pattern to the new `tool_catalog` protocol-based pattern.

---

## Failure Symptoms

### Primary Error
```
jeeves-orchestrator | Traceback (most recent call last):
jeeves-orchestrator |   File "/app/server.py", line 287, in <module>
jeeves-orchestrator |     asyncio.run(main())
jeeves-orchestrator |   File "/app/server.py", line 283, in main
jeeves-orchestrator |     await server.serve()
jeeves-orchestrator |   File "/app/server.py", line 264, in serve
jeeves-orchestrator |     await self.start()
jeeves-orchestrator |   File "/app/server.py", line 137, in start
jeeves-orchestrator |     tool_instances = initialize_all_tools(db=self.db)
jeeves-orchestrator |   File "/app/tools/__init__.py", line 76, in initialize_all_tools
jeeves-orchestrator |     registration_result = register_all_tools()
jeeves-orchestrator |   File "/app/tools/registration.py", line 41, in register_all_tools
jeeves-orchestrator |     from tools.safe_locator import locate
jeeves-orchestrator |   File "/app/tools/safe_locator.py", line 21, in <module>
jeeves-orchestrator |     from tools.robust_tool_base import (
jeeves-orchestrator | ModuleNotFoundError: No module named 'tools.robust_tool_base'
```

### Import Chain Trace
```
server.py
  → tools/__init__.py::initialize_all_tools()
    → tools/registration.py::register_all_tools()
      → tools/safe_locator.py (line 21)
        → from tools.robust_tool_base import ...  ❌ MODULE DOES NOT EXIST
```

---

## Missing Modules Inventory

### 1. `tools/robust_tool_base.py` - DOES NOT EXIST

**Status:** Never created
**Impact:** Blocks all composite and resilient tools

**Expected Exports:**
- `RobustToolExecutor` - Base class for tools with retry/fallback logic
- `make_strategy` - Helper to create execution strategies
- `ResultMappers` - Utility for result transformation
- `ToolResult` - Result type (actually exists in `models/types.py`)
- `CitationCollector` - Citation aggregation utility
- `AttemptRecord` - Execution attempt record
- `StrategyResult` - Strategy result type
- `RetryPolicy` - Retry policy configuration

**Files that import it (8 total):**
1. `tools/base/resilient_ops.py` (line 27)
2. `tools/safe_locator.py` (line 21)
3. `tools/unified_analyzer.py` (line 29)
4. `tools/symbol_explorer.py` (line 19)
5. `tools/flow_tracer.py` (line 19)
6. `tools/git_historian.py` (line 19)
7. `tools/module_mapper.py` (line 19)
8. `tests/unit/tools/test_composite_tools.py`

### 2. `tools/registry.py` - DOES NOT EXIST

**Status:** Replaced by `tool_catalog` but files not updated
**Impact:** Import failures for files using old registry pattern

**What files expect:**
- `tool_registry` - Global registry singleton
- `RiskLevel` - Risk classification enum
- `ToolRegistry` - Registry class

**Correct modern replacement:**
```python
# OLD (broken)
from tools.registry import tool_registry, RiskLevel

# NEW (correct per CONTRACT.md)
from jeeves_mission_system.contracts import tool_catalog
from jeeves_protocols import RiskLevel, ToolCategory
```

**Files using old pattern (4+ files):**
1. `tools/file_navigator.py` (line 21)
2. `tools/code_parser.py` (line 23)
3. `tools/base/system_tools.py` (line 13)
4. `tools/base/common_tools.py` (line 9)

### 3. `tools/path_helpers.py` - EXISTS but Wrong Import Path

**Status:** Exists at `tools/base/path_helpers.py`, imported as `tools/path_helpers`
**Impact:** Import failures at runtime

**Correct location:** `tools/base/path_helpers.py`
**Incorrect imports:** `from tools.path_helpers import ...`
**Should be:** `from tools.base.path_helpers import ...`

**Files with wrong path (7+ files):**
1. `tools/file_navigator.py` (line 22)
2. `tools/code_parser.py` (line 24)
3. `tools/base/resilient_ops.py` (line 26)
4. `tools/base/semantic_tools.py` (line 29)
5. `tools/base/index_tools.py` (line 28)
6. `tools/base/git_tools.py` (line 21)
7. `tools/base/citation_validator.py` (line 18)

---

## Why This Happened: The Incomplete Migration

### Evidence from Architecture Documents

**From CONTRACT.md (jeeves-core):**
The contract specifies the modern tool registration pattern:
```python
from jeeves_mission_system.contracts import tool_catalog
from jeeves_protocols import ToolCategory, RiskLevel

@tool_catalog.register(...)
async def my_tool(...) -> dict:
    ...
```

**From ADR-001:**
Describes migration from singleton `tool_registry` to protocol-based `app_context.tool_registry`, but this was never completed in the capability layer.

**From Test Evidence:**
```python
# Line 20 in test_resilient_ops.py:
# "SKIPPED: These tests require the tools.base.resilient_ops module which is not implemented."

pytestmark = pytest.mark.skip(reason="tools.base.resilient_ops module not implemented")
```

Developers **knew** these modules were missing and marked tests to skip rather than implementing them.

### The Pattern of Failure

1. **Design-First Development:** Architecture docs (CONSTITUTION.md, CONTRACT.md) describe ideal state with `RobustToolExecutor`, `tool_catalog`, etc.

2. **Code Generated from Specs:** Implementation files were created referencing these components, assuming they existed

3. **Incomplete Implementation:** Core infrastructure classes were never implemented

4. **Docker Workarounds:** Recent commits (e.g., `8b087bd - Copy all base tools to tools/ root`) tried to fix import errors by copying files around instead of fixing the root cause

5. **Test Coverage Gap:** Tests marked as skipped instead of exposing the missing implementations

---

## Impact Assessment

### System Impact
- ❌ **Orchestrator cannot start** - crashes immediately on module import
- ❌ **All composite tools unavailable** - locate, explore_symbol_usage, map_module, trace_entry_point, explain_code_history
- ❌ **All resilient tools unavailable** - read_code, find_related
- ❌ **No code analysis capability** - the entire capability is non-functional
- ❌ **No agent execution** - agents cannot run without tools

### Affected Components
- **5 Composite Tools** (Amendment XVII) - All blocked
- **2 Resilient Tools** (Amendment XXI) - All blocked
- **18+ Files** with broken imports
- **All Tests** in `tests/unit/tools/` - Most marked skip

### Cascade Effects
The `robust_tool_base` module provides the foundation for **all** composite and resilient tools. Without it:
- No fallback/retry logic for tool execution
- No attempt history tracking
- No citation collection
- No result aggregation
- No bounded retry policies

---

## Architectural Context

### The Two-Layer Tool Architecture

Per the Constitution and CONTRACT.md, tools exist in layers:

**Layer 1: Internal/Primitive Tools** (in `tools/base/`)
- Direct operations: `read_file`, `grep_search`, `find_symbol`, etc.
- No fallback logic, no retry, simple operations
- Import: `from tools.base.code_tools import read_file`

**Layer 2: Composite/Resilient Tools** (in `tools/`)
- Orchestrate multiple primitives with fallback strategies
- Require `RobustToolExecutor` for retry/fallback logic
- Examples: `locate`, `read_code`, `explore_symbol_usage`
- Import: `from tools.safe_locator import locate`

**The Problem:** Layer 2 depends on `robust_tool_base` which doesn't exist, so composite tools cannot run.

### Tool Registration Contract

**Old Pattern (BROKEN):**
```python
from tools.registry import tool_registry

tool_registry.register_tool(
    name="my_tool",
    func=my_tool,
    risk_level=RiskLevel.READ_ONLY
)
```

**New Pattern (per CONTRACT.md):**
```python
from jeeves_mission_system.contracts import tool_catalog

tool_catalog.register_function(
    tool_id=ToolId.MY_TOOL,
    func=my_tool,
    description="...",
    category=ToolCategory.COMPOSITE,
    risk_level=RiskLevel.READ_ONLY
)
```

**Current State:** Files use old pattern, but `tools.registry` doesn't exist.

---

## What Exists vs What's Expected

| Component | Expected Location | Actual Status | Actual Location (if exists) |
|-----------|------------------|---------------|----------------------------|
| `RobustToolExecutor` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `make_strategy` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `ResultMappers` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `CitationCollector` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `AttemptRecord` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `StrategyResult` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `RetryPolicy` | `tools.robust_tool_base` | ❌ NEVER CREATED | N/A |
| `ToolResult` | `tools.robust_tool_base` | ⚠️ WRONG LOC | `models/types.py` (Pydantic) |
| `tool_registry` | `tools.registry` | ⚠️ OBSOLETE | Use `tool_catalog` in `jeeves_avionics/tools/catalog.py` |
| `RiskLevel` | `tools.registry` | ⚠️ WRONG LOC | `jeeves_protocols` |
| `ToolCategory` | `tools.registry` | ⚠️ WRONG LOC | `jeeves_protocols` |
| `path_helpers` | `tools.path_helpers` | ⚠️ WRONG PATH | `tools/base/path_helpers.py` |

---

## Proper Fix Strategy

### Why Docker Fixes Are Wrong

Recent attempts to fix this by copying individual files to Docker (like in `docker/Dockerfile` lines 178-204) are **treating symptoms, not the disease**. The Dockerfile now has extensive duplication:

```dockerfile
# Copy to tools/base/
COPY jeeves-capability-code-analyser/tools/base/code_tools.py ./tools/base/
# ...repeat for 10+ files...

# Then ALSO copy to tools/ root for flat imports
COPY jeeves-capability-code-analyser/tools/base/code_tools.py ./tools/
# ...repeat for same 10+ files...
```

This is a **maintenance nightmare** and doesn't fix the core issue: **modules don't exist**.

### The Correct Fix: Three-Phase Approach

#### Phase 1: Create Missing Infrastructure (CRITICAL - DO THIS FIRST)

**File to create:** `jeeves-capability-code-analyser/tools/robust_tool_base.py`

This file must implement:
1. `RobustToolExecutor` - Core executor with fallback chain support
2. `RetryPolicy` - Enum/class for retry configuration
3. `AttemptRecord` - Dataclass for attempt tracking
4. `StrategyResult` - Dataclass for strategy results
5. `CitationCollector` - Utility for collecting citations
6. `ResultMappers` - Static methods for result transformation
7. `make_strategy` - Factory function for creating strategies

Re-export `ToolResult` from `models.types`:
```python
from models.types import ToolResult
__all__ = ["RobustToolExecutor", "ToolResult", ...]
```

#### Phase 2: Fix Registry Imports (HIGH PRIORITY)

**Search and replace across all files:**

OLD:
```python
from tools.registry import tool_registry, RiskLevel
tool_registry.register_tool(...)
```

NEW:
```python
from jeeves_mission_system.contracts import tool_catalog
from jeeves_protocols import RiskLevel, ToolCategory
tool_catalog.register_function(...)
```

**Files to fix:**
- `tools/file_navigator.py`
- `tools/code_parser.py`
- `tools/base/system_tools.py`
- `tools/base/common_tools.py`
- Any scripts in `scripts/` directory

**Also update `resilient_ops.py` internal usage:**
Lines 61, 89, 130, 176, 288, 317, 350 use `tool_registry` directly. Replace with:
```python
if not tool_catalog.has_tool("read_file"):
    return {"status": "tool_unavailable"}
read_file = tool_catalog.get_function(ToolId.READ_FILE)
```

#### Phase 3: Fix Path Helper Imports (MEDIUM PRIORITY)

**Search and replace:**
```python
# OLD
from tools.path_helpers import get_repo_path, resolve_path

# NEW
from tools.base.path_helpers import get_repo_path, resolve_path
```

**Files to fix:**
- `tools/file_navigator.py`
- `tools/code_parser.py`
- `tools/base/resilient_ops.py`
- `tools/base/semantic_tools.py`
- `tools/base/index_tools.py`
- `tools/base/git_tools.py`
- `tools/base/citation_validator.py`

#### Phase 4: Update Dockerfile (LOW PRIORITY - AFTER FIXES)

Once files are fixed, **simplify** the Dockerfile:
```dockerfile
# Instead of copying files individually:
COPY --chown=jeeves:jeeves jeeves-capability-code-analyser/tools/ ./tools/
```

No need for individual file copies or duplication between `tools/base/` and `tools/`.

---

## Implementation Checklist

### Critical Path (Phase 1 - Unblocks System)
- [ ] Create `tools/robust_tool_base.py` with all required classes
- [ ] Implement `RobustToolExecutor.execute()` method with fallback logic
- [ ] Implement `make_strategy()` factory function
- [ ] Implement helper classes: `CitationCollector`, `ResultMappers`
- [ ] Add proper imports and `__all__` export list
- [ ] Verify imports work: `from tools.robust_tool_base import RobustToolExecutor`

### High Priority (Phase 2 - Fixes Tool System)
- [ ] Update `tools/base/resilient_ops.py` - replace `tool_registry` with `tool_catalog`
- [ ] Update `tools/file_navigator.py` - replace registry imports
- [ ] Update `tools/code_parser.py` - replace registry imports
- [ ] Update `tools/base/system_tools.py` - replace registry imports
- [ ] Update `tools/base/common_tools.py` - replace registry imports
- [ ] Search for any other files using `tools.registry` pattern

### Medium Priority (Phase 3 - Fixes Path Imports)
- [ ] Update all `from tools.path_helpers` to `from tools.base.path_helpers`
- [ ] Verify no remaining incorrect path_helpers imports

### Low Priority (Phase 4 - Cleanup)
- [ ] Simplify Dockerfile copy commands
- [ ] Remove test skip markers in `test_resilient_ops.py`
- [ ] Run full test suite
- [ ] Update documentation if needed

---

## Testing Strategy

### Unit Tests
1. **Test `robust_tool_base` directly:**
   - Test `RobustToolExecutor` fallback chain
   - Test `make_strategy` creates valid strategies
   - Test `CitationCollector` deduplication

2. **Test composite tools:**
   - Unmute tests in `test_composite_tools.py`
   - Verify `safe_locator.locate()` works
   - Verify fallback strategies execute in order

3. **Test resilient tools:**
   - Unmute tests in `test_resilient_ops.py`
   - Verify `read_code()` tries multiple strategies
   - Verify `find_related()` returns valid results

### Integration Tests
1. **Test orchestrator startup:**
   - Verify `server.py` starts without import errors
   - Verify `initialize_all_tools()` completes
   - Verify all tools registered in `tool_catalog`

2. **Test tool execution:**
   - Execute `locate` tool with known query
   - Execute `read_code` with retry scenarios
   - Verify attempt_history populated correctly

### Docker Tests
1. **Build orchestrator image:**
   ```bash
   docker build -t jeeves-orchestrator:test --target orchestrator .
   ```

2. **Verify imports in container:**
   ```bash
   docker run --rm jeeves-orchestrator:test python -c "from tools.robust_tool_base import RobustToolExecutor"
   docker run --rm jeeves-orchestrator:test python -c "from tools.safe_locator import locate"
   ```

3. **Start full stack:**
   ```bash
   docker-compose up -d
   docker-compose logs jeeves-orchestrator
   # Should NOT see ModuleNotFoundError
   ```

---

## Risk Analysis

### Risks of NOT Fixing
- **System completely non-functional** - cannot run code analysis capability
- **Development blocked** - cannot test new features
- **Technical debt accumulation** - workarounds create more issues
- **Loss of confidence** - stakeholders see broken system

### Risks of Fixing
- **Implementation complexity** - `RobustToolExecutor` has complex retry logic
- **Breaking changes** - updating registry pattern may break other code
- **Testing burden** - need comprehensive tests for new infrastructure
- **Time investment** - estimated 4-8 hours for complete fix

### Mitigation
- Start with **minimal viable implementation** of `robust_tool_base`
- Add complexity incrementally (e.g., basic retry first, then exponential backoff)
- Test each phase independently before moving to next
- Keep old `tool_registry` pattern alongside new one temporarily if needed

---

## Dependencies and Blockers

### Dependencies Required
- **None** - this is pure Python implementation
- Uses existing imports: `jeeves_mission_system.contracts`, `jeeves_protocols`, `models.types`

### Blockers
- **None** - all required components exist in jeeves-core
- `tool_catalog` ready to use in `jeeves_mission_system.contracts`
- `ToolResult` ready to use in `models.types`

### External Considerations
- Changes should not affect jeeves-core (capability layer only)
- Must maintain compatibility with existing tool signatures
- Must respect tool contract from CONTRACT.md

---

## Success Criteria

### Minimum Viable Fix
- [ ] Orchestrator starts without `ModuleNotFoundError`
- [ ] At least one composite tool (`locate`) executes successfully
- [ ] At least one resilient tool (`read_code`) executes successfully
- [ ] Attempt history populated correctly

### Complete Fix
- [ ] All 18+ files with broken imports now work
- [ ] All tests in `tests/unit/tools/` pass (no skips)
- [ ] Tool registration uses modern `tool_catalog` pattern
- [ ] Dockerfile simplified (no duplicate copies)
- [ ] Documentation updated

### Production Ready
- [ ] Full integration test suite passes
- [ ] Docker compose stack runs end-to-end
- [ ] Agent can execute full analysis workflow
- [ ] No errors in orchestrator logs
- [ ] Performance acceptable (no excessive retries)

---

## Next Steps

**IMMEDIATE (Day 1):**
1. Implement `tools/robust_tool_base.py` with minimal viable classes
2. Test import works: `python -c "from tools.robust_tool_base import RobustToolExecutor"`
3. Fix `resilient_ops.py` to use correct imports
4. Test orchestrator startup

**SHORT TERM (Day 2-3):**
1. Fix all registry imports to use `tool_catalog`
2. Fix all path_helpers imports
3. Run unit tests, fix failures
4. Test Docker build

**MEDIUM TERM (Week 1):**
1. Enhance `RobustToolExecutor` with full retry logic
2. Add comprehensive tests
3. Simplify Dockerfile
4. Update documentation

---

## Conclusion

This is **NOT a Docker problem** or a deployment issue. It's a **missing implementation** that requires creating the planned architectural components. The fix is straightforward:

1. **Create** `robust_tool_base.py` with required infrastructure classes
2. **Replace** old `tool_registry` pattern with new `tool_catalog` pattern
3. **Fix** import paths for `path_helpers`

The Docker workarounds are symptoms of the real problem. Fix the source code, and Docker will work.

**Priority:** CRITICAL
**Estimated Effort:** 4-8 hours
**Risk if unfixed:** System remains completely non-functional

---

**Document Version:** 1.0
**Last Updated:** 2025-12-14
**Author:** RCA Investigation Agent

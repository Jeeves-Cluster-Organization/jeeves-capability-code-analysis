# Constitutional Implementation Plan: Fix Import Failures

**Date:** 2025-12-14
**Priority:** CRITICAL
**Constitutional Compliance:** All Jeeves CONSTITUTION.md files

---

## Executive Summary

After reading all CONSTITUTION.md files, the issue is clear: **The capability layer violated constitutional boundaries** by attempting to create infrastructure (`robust_tool_base`) that belongs in the **core/avionics layer**.

**The Fix:** Delete the `robust_tool_base` concept entirely. The capability layer should:
1. Register simple tool FUNCTIONS with `tool_catalog` (from core)
2. Let core's `ToolExecutor` (from avionics) handle retry/fallback logic
3. Use `tool_catalog.get_function()` to call other tools (not custom executors)

---

## Constitutional Analysis

### Layer Hierarchy (from docs/CONSTITUTION.md)

```
L0: jeeves_protocols (pure types, no dependencies)
L0: jeeves_shared (logging, serialization, UUID - depends only on protocols)
L1: jeeves_memory_module (persistence services)
L2: jeeves_control_tower (orchestration kernel)
L3: jeeves_avionics (infrastructure adapters) ← ToolExecutor lives here
L4: jeeves_mission_system (application layer)
L5: jeeves-capability-* (domain verticals) ← We are here
```

### Constitutional Violations

**From Capability CONSTITUTION.md line 32:**
```python
# Capability dependencies:
- Depends on `jeeves_avionics.wiring` for ToolExecutor  # ✅ CORRECT
- MUST NOT import directly from `coreengine/` (Go package)  # ❌ VIOLATED
```

**From Avionics CONSTITUTION.md R1:**
> "Avionics **implements** core protocols, never modifies them"

**The Violation:**
- Capability created `robust_tool_base` with custom executor logic
- This is **infrastructure** (retry, fallback, attempt tracking)
- Infrastructure belongs in **avionics layer**, not capability layer
- Capability layer must use avionics' `ToolExecutor`, not create its own

### What Core/Avionics Already Provides

**From jeeves_avionics/wiring.py:**
```python
class ToolExecutor:
    """Concrete implementation of ToolExecutorProtocol.

    This implementation:
    - Delegates to tool_registry for direct tool execution
    - Uses resilient_ops for tools with fallback strategies  # ← Already has this!
    - Tracks execution timing and attempt history           # ← Already has this!
    - Validates parameters against registered schemas
    ```

**Resilient ops mapping (line 77-82):**
```python
RESILIENT_OPS_MAP = {
    "read_file": "read_code",
    "find_symbol": "locate",
    "find_similar_files": "find_related",
}
```

The core ToolExecutor **ALREADY** has fallback logic! The capability layer tried to reinvent it.

---

## The Correct Constitutional Pattern

### How Tools Should Work Per Constitutions

**Mission System CONSTITUTION.md R2 (line 111-127):**
> "Capabilities register their tools via the ToolRegistryProtocol"
> "Tool Design Principles: Composability, Transparency, Bounded, Graceful degradation"

**Capability CONSTITUTION.md (line 113-116):**
> "tools/ — Code analysis tools
>  - Composite tools: locate, explore_symbol_usage, map_module, etc.
>  - Resilient tools: read_code, find_related
>  - Base tools: read_file, glob_files, grep_search, etc."

**The Pattern:**
1. **Capability defines tool FUNCTIONS** (simple async functions)
2. **Capability registers tools** with `tool_catalog.register_function()`
3. **Tools can call OTHER tools** via `tool_catalog.get_function(tool_id)`
4. **Avionics' ToolExecutor** handles retry/fallback when tools are executed

### Example: How `locate` Should Be Implemented

**WRONG (current broken code):**
```python
from tools.robust_tool_base import RobustToolExecutor  # ❌ Doesn't exist

async def locate(query: str, ...) -> Dict[str, Any]:
    executor = RobustToolExecutor(...)  # ❌ Capability creating infrastructure
    executor.add_strategy(...)
    result = await executor.execute(...)
```

**CORRECT (constitutional pattern):**
```python
from jeeves_mission_system.contracts import tool_catalog, ToolId
from jeeves_protocols import RiskLevel, ToolCategory

async def locate(query: str, search_type: str = "auto", scope: Optional[str] = None) -> Dict[str, Any]:
    """Locate code elements with deterministic fallback strategy.

    Tries strategies in order until match found:
    1. find_symbol (exact)
    2. find_symbol (partial)
    3. grep_search (case-sensitive)
    4. grep_search (case-insensitive)
    5. semantic_search
    """
    attempts = []

    # Strategy 1: Exact symbol match
    if search_type in ("auto", "symbol"):
        find_symbol = tool_catalog.get_function(ToolId.FIND_SYMBOL)
        result = await find_symbol(name=query, exact=True, path_prefix=scope)
        attempts.append(("find_symbol_exact", result))
        if result.get("status") == "success" and result.get("symbols"):
            return {
                "status": "success",
                "query": query,
                "found_via": "find_symbol (exact)",
                "results": result["symbols"],
                "attempt_history": attempts,
                "citations": _extract_citations(result),
            }

    # Strategy 2: Partial symbol match
    if search_type in ("auto", "symbol"):
        result = await find_symbol(name=query, exact=False, path_prefix=scope)
        attempts.append(("find_symbol_partial", result))
        if result.get("status") == "success" and result.get("symbols"):
            return {
                "status": "success",
                "query": query,
                "found_via": "find_symbol (partial)",
                "results": result["symbols"],
                "attempt_history": attempts,
                "citations": _extract_citations(result),
            }

    # Strategy 3: Grep case-sensitive
    if search_type in ("auto", "text"):
        grep_search = tool_catalog.get_function(ToolId.GREP_SEARCH)
        import re
        pattern = re.escape(query)
        result = await grep_search(pattern=pattern, path=scope, max_results=20)
        attempts.append(("grep_sensitive", result))
        if result.get("status") == "success" and result.get("matches"):
            return {
                "status": "success",
                "query": query,
                "found_via": "grep_search (case-sensitive)",
                "results": result["matches"],
                "attempt_history": attempts,
                "citations": _extract_citations(result),
            }

    # Strategy 4: Grep case-insensitive
    if search_type in ("auto", "text"):
        pattern = f"(?i){re.escape(query)}"
        result = await grep_search(pattern=pattern, path=scope, max_results=20)
        attempts.append(("grep_insensitive", result))
        if result.get("status") == "success" and result.get("matches"):
            return {
                "status": "success",
                "query": query,
                "found_via": "grep_search (case-insensitive)",
                "results": result["matches"],
                "attempt_history": attempts,
                "citations": _extract_citations(result),
            }

    # Strategy 5: Semantic search
    if search_type in ("auto", "semantic"):
        semantic_search = tool_catalog.get_function(ToolId.SEMANTIC_SEARCH)
        result = await semantic_search(query=query, limit=10, path_prefix=scope)
        attempts.append(("semantic_search", result))
        if result.get("status") == "success" and result.get("results"):
            return {
                "status": "success",
                "query": query,
                "found_via": "semantic_search",
                "results": result["results"],
                "attempt_history": attempts,
                "citations": _extract_citations(result),
            }

    # No matches found
    return {
        "status": "not_found",
        "query": query,
        "found_via": None,
        "results": [],
        "attempt_history": attempts,
        "citations": [],
        "message": f"No matches found for '{query}' after {len(attempts)} attempts",
    }


def _extract_citations(result: Dict[str, Any]) -> List[str]:
    """Extract [file:line] citations from result."""
    citations = []
    for item in result.get("symbols", []) or result.get("matches", []) or result.get("results", []):
        file_path = item.get("file") or item.get("path")
        line = item.get("line", 1)
        if file_path:
            citations.append(f"{file_path}:{line}")
    return citations


# Register with catalog
tool_catalog.register_function(
    tool_id=ToolId.LOCATE,
    func=locate,
    description="Locate code elements with deterministic fallback strategy",
    parameters={
        "query": "string",
        "search_type": "string?",  # auto, symbol, text, semantic
        "scope": "string?",  # path prefix to limit search
    },
    category=ToolCategory.COMPOSITE,
    risk_level=RiskLevel.READ_ONLY,
)
```

**Key Differences:**
- ❌ No `RobustToolExecutor` - doesn't exist and shouldn't
- ✅ Simple async function - just orchestrates other tools
- ✅ Calls tools via `tool_catalog.get_function(ToolId.XXX)`
- ✅ Tracks attempts manually (simple list)
- ✅ Returns attempt_history for transparency (P3 compliance)
- ✅ Registered with catalog for discovery

---

## Implementation Plan

### Phase 1: Fix Tool Imports (CRITICAL - Unblocks System)

**Step 1.1: Fix resilient_ops.py**

File: `jeeves-capability-code-analyser/tools/base/resilient_ops.py`

**Remove lines 27-34:**
```python
# DELETE THIS
from tools.robust_tool_base import (
    RobustToolExecutor,
    ToolResult,
    CitationCollector,
    AttemptRecord,
    StrategyResult,
    RetryPolicy,
)
```

**Replace with:**
```python
from jeeves_mission_system.contracts import tool_catalog, ToolId
from jeeves_protocols import RiskLevel, ToolCategory
from models.types import ToolResult  # This already exists
```

**Rewrite tools to NOT use RobustToolExecutor:**
- `read_code()` - Simplify to try strategies sequentially, track attempts manually
- `find_related()` - Same pattern

**Step 1.2: Fix all composite tools**

Files:
- `tools/safe_locator.py`
- `tools/unified_analyzer.py`
- `tools/symbol_explorer.py`
- `tools/flow_tracer.py`
- `tools/git_historian.py`
- `tools/module_mapper.py`

**For each file:**
1. Remove `from tools.robust_tool_base import ...`
2. Add `from jeeves_mission_system.contracts import tool_catalog, ToolId`
3. Rewrite to call tools via `tool_catalog.get_function(ToolId.XXX)()`
4. Track attempts manually (simple list)
5. Return attempt_history in result dict

### Phase 2: Fix Registry Imports (HIGH PRIORITY)

**Files to fix:**
- `tools/file_navigator.py`
- `tools/code_parser.py`
- `tools/base/system_tools.py`
- `tools/base/common_tools.py`

**Replace:**
```python
# OLD
from tools.registry import tool_registry, RiskLevel

# NEW
from jeeves_mission_system.contracts import tool_catalog
from jeeves_protocols import RiskLevel, ToolCategory
```

**Update usage:**
```python
# OLD
if not tool_registry.has_tool("read_file"):
    return {"status": "tool_unavailable"}
read_file = tool_registry.get_tool_function("read_file")

# NEW
if not tool_catalog.has_tool(ToolId.READ_FILE):
    return {"status": "tool_unavailable"}
read_file = tool_catalog.get_function(ToolId.READ_FILE)
```

### Phase 3: Fix Path Helper Imports (MEDIUM PRIORITY)

**Files to fix (7 files):**
All files that import `from tools.path_helpers import ...`

**Replace with:**
```python
from tools.base.path_helpers import get_repo_path, resolve_path
```

### Phase 4: Simplify Dockerfile (LOW PRIORITY - After Code Fixed)

**Current bloat (lines 178-204, duplicated in orchestrator section):**
```dockerfile
# Copy to tools/base/
COPY jeeves-capability-code-analyser/tools/base/code_tools.py ./tools/base/
COPY jeeves-capability-code-analyser/tools/base/common_tools.py ./tools/base/
# ... repeat for 10+ files ...

# Also copy to tools/ root for flat imports
COPY jeeves-capability-code-analyser/tools/base/code_tools.py ./tools/
COPY jeeves-capability-code-analyser/tools/base/common_tools.py ./tools/
# ... repeat SAME 10+ files ...
```

**Simplified (after code is fixed):**
```dockerfile
# Copy entire tools directory (preserves structure)
COPY --chown=jeeves:jeeves jeeves-capability-code-analyser/tools/ ./tools/

# Done! No duplication, no individual files
```

**Why this works after fix:**
- `tools/` will have correct structure: `tools/*.py` and `tools/base/*.py`
- No need to copy files individually
- No need to duplicate to root (imports will use correct paths)
- Docker layer caching still works (COPY invalidates on any file change anyway)

---

## File-by-File Changes

### 1. `tools/base/resilient_ops.py`

**Lines to remove:** 27-34 (robust_tool_base imports)

**Lines to add after existing imports:**
```python
from jeeves_mission_system.contracts import tool_catalog, ToolId
from jeeves_protocols import RiskLevel, ToolCategory
from models.types import ToolResult
```

**Functions to rewrite:**
- `read_code()` - Remove RobustToolExecutor, use simple fallback chain
- `find_related()` - Same pattern

**Remove:**
- Lines 61-64, 89-92, 130-133, 176-179, 288-291, 317-320, 350-353 (tool_registry usage)

**Replace with tool_catalog:**
```python
if not tool_catalog.has_tool(ToolId.READ_FILE):
    return {"status": "tool_unavailable"}
read_file = tool_catalog.get_function(ToolId.READ_FILE)
```

### 2. `tools/safe_locator.py`

**Remove lines 21-25:**
```python
from tools.robust_tool_base import (
    RobustToolExecutor,
    make_strategy,
    ResultMappers,
)
```

**Add:**
```python
from jeeves_mission_system.contracts import tool_catalog, ToolId
from jeeves_protocols import RiskLevel, ToolCategory
```

**Rewrite `locate()` function using pattern shown above**

### 3. `tools/unified_analyzer.py`

Same pattern as safe_locator.py

### 4. `tools/symbol_explorer.py`

Same pattern

### 5. `tools/flow_tracer.py`

Same pattern

### 6. `tools/git_historian.py`

Same pattern

### 7. `tools/module_mapper.py`

Same pattern

### 8-11. Registry import files

`tools/file_navigator.py`, `tools/code_parser.py`, `tools/base/system_tools.py`, `tools/base/common_tools.py`

Replace `tools.registry` imports with `tool_catalog`

### 12-18. Path helper files

Replace `tools.path_helpers` with `tools.base.path_helpers`

### 19. `docker/Dockerfile`

Lines 178-204 (test stage) and 343-369 (orchestrator stage):

**Replace:**
```dockerfile
COPY jeeves-capability-code-analyser/tools/*.py ./tools/
RUN mkdir -p ./tools/base
COPY jeeves-capability-code-analyser/tools/base/__init__.py ./tools/base/
COPY jeeves-capability-code-analyser/tools/base/code_tools.py ./tools/base/
# ...10+ individual files...
COPY jeeves-capability-code-analyser/tools/base/code_tools.py ./tools/
# ...same 10+ files duplicated...
```

**With:**
```dockerfile
COPY --chown=jeeves:jeeves jeeves-capability-code-analyser/tools/ ./tools/
```

---

## Testing Strategy

### Unit Tests

**Update tests to use tool_catalog:**

File: `tests/unit/tools/test_resilient_ops.py`

Lines 20-28 currently skip tests. Remove skip and update:

```python
# OLD
from tools.base.resilient_ops import read_code
from tools.registry import tool_registry

# NEW
from tools.base.resilient_ops import read_code
from jeeves_mission_system.contracts import tool_catalog

# In tests
assert tool_catalog.has_tool(ToolId.READ_CODE)
tool_fn = tool_catalog.get_function(ToolId.READ_CODE)
```

### Integration Tests

**Test orchestrator startup:**
```bash
cd jeeves-capability-code-analyser
python server.py
# Should NOT see ModuleNotFoundError
```

**Test Docker build:**
```bash
docker build -t jeeves-orchestrator:test --target orchestrator -f docker/Dockerfile .
docker run --rm jeeves-orchestrator:test python -c "from tools.safe_locator import locate"
# Should succeed
```

### Validation Checklist

- [ ] No `ModuleNotFoundError` on server startup
- [ ] All tools registered in `tool_catalog`
- [ ] `locate` tool executes successfully
- [ ] `read_code` tool executes with fallback
- [ ] Attempt history populated correctly
- [ ] Docker image builds without errors
- [ ] Docker image smaller than before (less duplication)
- [ ] Tests in `test_resilient_ops.py` pass (no skips)

---

## Constitutional Compliance Verification

After implementation, verify:

1. **Layer Boundaries (RULE 4 from docs/CONSTITUTION.md line 289):**
   - [ ] Capability accesses core only through `mission_system.contracts` ✓
   - [ ] No direct imports from `coreengine/` ✓
   - [ ] No infrastructure logic in capability layer ✓

2. **Avionics R1 (Adapter Pattern):**
   - [ ] Capability uses ToolExecutor from avionics ✓
   - [ ] Capability doesn't create its own executor infrastructure ✓

3. **Mission System R2 (Tool Boundary):**
   - [ ] Tools registered via `ToolRegistryProtocol` (tool_catalog) ✓
   - [ ] Tools return `attempt_history` for transparency ✓
   - [ ] Tools respect bounded retry (max 2 retries per fallback) ✓

4. **Capability CONSTITUTION line 32:**
   - [ ] Depends on `jeeves_avionics.wiring` for ToolExecutor ✓
   - [ ] Does NOT import from `coreengine/` directly ✓

---

## Success Criteria

### Minimum Viable Fix
- [ ] Orchestrator starts without import errors
- [ ] At least one composite tool (`locate`) works
- [ ] Tool registration succeeds

### Complete Fix
- [ ] All 18+ files with broken imports fixed
- [ ] All tests pass (no skips)
- [ ] Tool execution uses core ToolExecutor pattern
- [ ] Dockerfile simplified (no duplication)

### Production Ready
- [ ] Full integration test suite passes
- [ ] Docker stack runs end-to-end
- [ ] Constitutional compliance verified
- [ ] Documentation updated

---

## Estimated Effort

**Phase 1 (Critical):** 2-3 hours
- Fix resilient_ops.py
- Fix 7 composite tool files
- Test orchestrator startup

**Phase 2 (High):** 1-2 hours
- Fix 4 registry import files
- Update tool_catalog usage

**Phase 3 (Medium):** 30 minutes
- Fix 7 path_helpers imports

**Phase 4 (Low):** 30 minutes
- Simplify Dockerfile
- Test Docker build

**Total:** 4-6 hours

---

## Risk Mitigation

**Risks:**
- Breaking existing tool behavior during rewrite
- Missing edge cases in fallback logic
- Test coverage gaps

**Mitigation:**
- Start with one tool (locate), validate, then replicate pattern
- Keep attempt_history structure identical for compatibility
- Run full test suite after each phase
- Test Docker build frequently

---

## Next Steps

1. **Read this plan** - Understand constitutional principles
2. **Start Phase 1** - Fix resilient_ops.py first
3. **Test incrementally** - Validate each file change
4. **Complete phases 2-3** - Fix remaining imports
5. **Simplify Dockerfile** - Phase 4 after code works
6. **Verify compliance** - Check constitutional rules

---

**Document Version:** 1.0 (Constitutional)
**Last Updated:** 2025-12-14
**Constitutional Authority:** All Jeeves CONSTITUTION.md files

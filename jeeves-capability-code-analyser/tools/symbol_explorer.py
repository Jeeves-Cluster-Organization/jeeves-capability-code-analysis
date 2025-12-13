"""Symbol Explorer - Trace symbol usages across codebase.

Phase 2/4 Constitutional Compliance - No auto-registration at import time

Per Amendment XVII (Composite Tool Contracts), this tool:
- Orchestrates multiple primitive tools in a deterministic sequence
- Returns attempt_history for transparency
- Aggregates citations from all steps
- Respects context bounds
- Degrades gracefully on step failures
"""

import re
from typing import Any, Dict, List

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts import LoggerProtocol, ContextBounds
from jeeves_protocols import RiskLevel, OperationStatus
from tools.robust_tool_base import AttemptRecord, CitationCollector
from config.tool_profiles import detect_semantic_mismatch


async def _find_definition(symbol_name: str, exact: bool) -> Dict[str, Any]:
    """Find symbol definition locations."""
    _logger = get_logger()
    if not tool_registry.has_tool("find_symbol"):
        return {"status": "tool_unavailable", "definitions": []}

    find_symbol = tool_registry.get_tool_function("find_symbol")
    try:
        result = await find_symbol(name=symbol_name, exact=exact, include_body=False)
        if result.get("status") == "success" and result.get("symbols"):
            return {
                "status": "found",
                "definitions": [
                    {
                        "file": s.get("file", ""),
                        "line": s.get("line", 0),
                        "name": s.get("name", symbol_name),
                        "type": s.get("type", "unknown"),
                    }
                    for s in result["symbols"]
                ],
            }
        return {"status": "no_match", "definitions": []}
    except Exception as e:
        _logger.warning("symbol_explorer_find_def_error", error=str(e))
        return {"status": "error", "definitions": [], "error": str(e)}


async def _get_importers(module_path: str) -> Dict[str, Any]:
    """Get files that import the module containing the symbol."""
    _logger = get_logger()
    if not tool_registry.has_tool("get_importers"):
        return {"status": "tool_unavailable", "importers": []}

    get_importers = tool_registry.get_tool_function("get_importers")
    try:
        module_name = module_path.replace("/", ".").replace("\\", ".")
        if module_name.endswith(".py"):
            module_name = module_name[:-3]

        result = await get_importers(module_name=module_name)
        if result.get("status") == "success" and result.get("importers"):
            return {"status": "found", "importers": result["importers"]}
        return {"status": "no_match", "importers": []}
    except Exception as e:
        _logger.warning("symbol_explorer_get_importers_error", error=str(e))
        return {"status": "error", "importers": [], "error": str(e)}


async def _find_call_sites(symbol_name: str, files: List[str], max_per_file: int) -> Dict[str, Any]:
    """Find call sites of the symbol in specified files."""
    _logger = get_logger()
    if not tool_registry.has_tool("grep_search"):
        return {"status": "tool_unavailable", "usages": []}

    grep_search = tool_registry.get_tool_function("grep_search")
    usages = []
    pattern = rf"\b{re.escape(symbol_name)}\b"

    for file_path in files:
        try:
            result = await grep_search(pattern=pattern, path=file_path, max_results=max_per_file)
            if result.get("status") == "success":
                for match in result.get("matches", []):
                    usages.append({
                        "file": match["file"],
                        "line": match["line"],
                        "context": match.get("match", ""),
                    })
        except Exception as e:
            _logger.warning("symbol_explorer_call_site_error", file=file_path, error=str(e))

    return {"status": "found" if usages else "no_match", "usages": usages}


async def explore_symbol_usage(
    symbol_name: str,
    context_bounds: ContextBounds,
    trace_depth: int = 3,
    include_tests: bool = False,
) -> Dict[str, Any]:
    """Trace all usages of a symbol across the codebase.

    Pipeline:
    1. Validate symbol_name is semantically valid (not a file path)
    2. find_symbol(name=symbol_name, exact=True) -> definitions
    3. If no match: find_symbol(name=symbol_name, exact=False)
    4. get_importers(module_name=defining_module) -> importer files
    5. grep_search(pattern=symbol_name) -> call sites
    6. Build call graph

    Args:
        symbol_name: Symbol name to explore
        context_bounds: Context bounds configuration (from AppContext)
        trace_depth: Depth of trace (default 3)
        include_tests: Include test files in search
    """
    # SEMANTIC VALIDATION: Detect if symbol_name is actually a file path
    _logger = get_logger()
    is_mismatch, reason, suggested_tool = detect_semantic_mismatch(
        tool_name="explore_symbol_usage",
        param_name="symbol_name",
        param_value=symbol_name,
    )
    if is_mismatch:
        _logger.warning(
            "explore_symbol_usage_invalid_params",
            symbol_name=symbol_name,
            reason=reason,
            suggested_tool=suggested_tool,
        )
        return {
            "status": OperationStatus.INVALID_PARAMETERS.value,
            "error": reason,
            "message": f"'{symbol_name}' is not a valid symbol name. "
                       "Symbols are class/function names like 'CoreEnvelope' or 'process_request'.",
            "suggested_tool": suggested_tool,
            "suggested_params": {"path": symbol_name} if suggested_tool == "read_code" else {"module_path": symbol_name},
            "symbol": symbol_name,
            "definitions": [],
            "usages": [],
            "attempt_history": [],
        }

    bounds = context_bounds
    history: List[AttemptRecord] = []
    citations = CitationCollector()
    bounded = False
    step = 0

    # Step 1: Find definition (exact match)
    step += 1
    history.append(AttemptRecord(step=step, strategy="find_symbol (exact)", result="pending", params={"name": symbol_name}))

    def_result = await _find_definition(symbol_name, exact=True)
    history[-1].result = def_result["status"]
    if def_result.get("error"):
        history[-1].error = def_result["error"]

    definitions = def_result.get("definitions", [])

    # Step 2: Try partial match if exact fails
    if not definitions:
        step += 1
        history.append(AttemptRecord(step=step, strategy="find_symbol (partial)", result="pending", params={"name": symbol_name}))

        def_result = await _find_definition(symbol_name, exact=False)
        history[-1].result = def_result["status"]
        if def_result.get("error"):
            history[-1].error = def_result["error"]

        definitions = def_result.get("definitions", [])

    # Collect citations from definitions
    for defn in definitions:
        citations.add(defn["file"], defn["line"])

    # Step 3: Find importers for each definition file
    all_importers: List[str] = []
    importer_set = set()

    for defn in definitions:
        step += 1
        history.append(AttemptRecord(step=step, strategy="get_importers", result="pending", params={"module": defn["file"]}))

        imp_result = await _get_importers(defn["file"])
        history[-1].result = imp_result["status"]

        for importer in imp_result.get("importers", []):
            importer_file = importer.get("file", importer) if isinstance(importer, dict) else importer

            # Filter test files if requested
            if not include_tests and ("test" in importer_file.lower() or "tests" in importer_file.lower()):
                continue

            if importer_file not in importer_set:
                importer_set.add(importer_file)
                all_importers.append(importer_file)

    # Step 4: Find call sites in importer files
    usages: List[Dict[str, Any]] = []
    if all_importers:
        max_files = min(len(all_importers), bounds.max_files_per_query // 2)
        files_to_search = all_importers[:max_files]
        if len(all_importers) > max_files:
            bounded = True

        step += 1
        history.append(AttemptRecord(
            step=step,
            strategy="grep_search",
            result="pending",
            params={"pattern": symbol_name, "files": len(files_to_search)},
        ))

        call_result = await _find_call_sites(symbol_name, files_to_search, max_per_file=10)
        history[-1].result = call_result["status"]

        usages = call_result.get("usages", [])

        # Collect citations from usages
        for usage in usages:
            citations.add(usage["file"], usage["line"])

    # Build call graph
    call_graph = {symbol_name: [f"{u['file']}:{u['line']}" for u in usages]}

    # Determine status
    if definitions or usages:
        status = "success"
    elif any(h.result == "error" for h in history):
        status = "partial"
    else:
        status = "success"

    _logger.info(
        "explore_symbol_usage_completed",
        symbol=symbol_name,
        definitions=len(definitions),
        usages=len(usages),
        importers=len(all_importers),
    )

    return {
        "status": status,
        "symbol": symbol_name,
        "definition": definitions[0] if definitions else None,
        "definitions": definitions,
        "usages": usages,
        "usage_count": len(usages),
        "importers": all_importers,
        "call_graph": call_graph,
        "attempt_history": [h.to_dict() for h in history],
        "citations": citations.get_all(),
        "bounded": bounded,
    }


__all__ = ["explore_symbol_usage"]

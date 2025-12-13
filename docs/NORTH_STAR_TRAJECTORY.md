# Code Analysis Agent – North Star Trajectory

**Version:** 8.7 (Architecture Cleanup)
**Status:** Living Document
**Scope:** Target Architecture for Multi-Stage, Goal-Driven Code Analysis

---

## What This Document Is

This document defines the **target architecture** for the Code Analysis Agent: a 7-agent, multi-stage, tool-assisted pipeline with dynamic goals and strong grounding in repository evidence.

**Core Characteristic:**
> A read-only agent system that explores codebases using multi-stage goal-driven execution, deterministic tool traversal, and citation-backed responses grounded in actual source code.

---

## Target Architecture v8.0: The 7-Agent Final Form

### Agent Overview

| # | Agent | LLM? | Primary Role |
|---|-------|------|--------------|
| 1 | **Perception** | No | Normalize input, load TraversalState from storage |
| 2 | **Intent** | Yes | Classify query, extract/initialize ordered goals with dependencies |
| 3 | **Planner** | Yes | Generate multi-stage plans using available tools and remaining goals |
| 4 | **Traverser** | No | Execute tool steps with bounded retries and micro-adjustments |
| 5 | **Synthesizer** | Yes | Build structured intermediate understanding across stages |
| 6 | **Critic** | Yes | Validate goal satisfaction, drive routing decisions |
| 7 | **Integration** | No* | Build final response with citations, persist state |

*Integration may use minimal LLM for response wording refinement.

---

## Agent Contracts

### 1. Perception Agent (No LLM)

**Role:** Prepare structured context without reasoning.

**Inputs:**
- Raw user input
- Session ID

**Outputs:** `PerceptionOutput`
```python
class PerceptionOutput:
    normalized_input: str       # Cleaned user message
    memory_context: Dict        # L1-L4 memory snapshot
    context_summary: str        # Brief NL summary of available context
    traversal_state: TraversalState  # Loaded from L4 storage
```

**Behavior:**
- Normalize raw input (strip, clean control chars)
- Load `TraversalState` from persistent storage (L4)
- Gather memory context from all layers
- No LLM calls, no reasoning

**Tools:** Read-only (session state, memory search)

---

### 2. Intent Agent (LLM)

**Role:** Define the problem by classifying query and extracting structured goals.

**Inputs:**
- `PerceptionOutput`

**Outputs:** `IntentOutput`
```python
class IntentOutput:
    intent: str                           # Primary intent in imperative form
    goals: List[str]                      # Ordered list of goals (initialize all_goals)
    constraints: List[str]                # Requirements or limitations
    ambiguities: List[str]                # Unclear aspects
    goal_dependencies: Dict[str, List[str]]  # goal -> prerequisite goals
    goal_priorities: Dict[str, int]       # goal -> priority (lower = higher)
    confidence: float                     # 0.0-1.0
    clarification_needed: bool
    clarification_question: Optional[str]
```

**Behavior:**
- Analyze user message to extract primary intent
- Extract ordered goals with dependencies and priorities
- Call `envelope.initialize_goals()` to set:
  - `all_goals`: Complete list of goals
  - `remaining_goals`: Copy of all_goals (to be consumed)
  - `goal_completion_status`: All goals start as "pending"
- Note ambiguities in `ambiguities` field, but **proceed with exploration**
- **Exploration-First**: Almost always set `clarification_needed=False`
- Only request clarification for completely incomprehensible queries (empty, gibberish)
- Generate fallback clarification question if LLM omits it when `clarification_needed=True`

**Tools:** None (pure reasoning)

---

### 3. Planner Agent (LLM)

**Role:** Turn intent and remaining goals into a concrete execution plan for the current stage.

**Inputs:**
- `IntentOutput`
- `remaining_goals` (from envelope)
- Current stage context (`completed_stages`, accumulated findings)
- Available tools (via `list_tools`)

**Outputs:** `PlanOutput`
```python
class PlanOutput:
    plan_id: str
    steps: List[PlanStep]      # Ordered execution steps
    rationale: str             # Why this plan
    target_goals: List[str]    # Which goals this stage addresses
    stage_number: int          # Current stage (1-indexed)
    feasibility_score: int     # 0-100
    risk_factors: List[str]    # Identified risks
```

**Behavior:**
- Query available tools via `list_tools`
- Generate plan addressing `target_goals` subset of `remaining_goals`
- Consider stage context (what previous stages discovered)
- Plans are stage-scoped, not single tool calls
- Use index-aware tools for efficient exploration

**Tools:** Read-only (`list_tools`, tool documentation)

---

### 4. Traverser Agent (No LLM)

**Role:** Execute plan steps using code analysis tools.

**Inputs:**
- `PlanOutput`
- `TraversalState`

**Outputs:** `ExecutionOutput`
```python
class ExecutionOutput:
    results: List[ToolExecutionResult]   # Per-step results with attempt history
    total_time_ms: int
    all_succeeded: bool
    attempt_history: Dict[str, List[AttemptRecord]]  # step_id -> attempts
```

**Behavior:**
- Execute each `PlanStep` using registered tools
- Implement **bounded retries with micro-adjustments**:
  - Empty grep result → broaden pattern, try alternate paths
  - File not found → check similar paths, try parent directory
  - Max 3 retry attempts per step with deterministic heuristics
- Update `TraversalState`:
  - `explored_files`: Add files examined
  - `explored_symbols`: Add symbols found
  - `relevant_snippets`: Accumulate code evidence
  - `call_chain`: Track call relationships
- Respect `CodeContextBounds` (tokens, files, depth)

**Tools:** All code tools (read_file, grep_search, find_symbol, tree, git_*, etc.)

**Retry Heuristics (Deterministic):**
```python
RETRY_STRATEGIES = {
    "empty_grep": ["broaden_pattern", "try_parent_dir", "case_insensitive"],
    "file_not_found": ["fuzzy_match_path", "check_index", "list_similar"],
    "symbol_not_found": ["partial_match", "check_imports", "expand_scope"],
}
```

---

### 5. Synthesizer Agent (LLM) – NEW

**Role:** Build structured intermediate understanding from execution results.

**Inputs:**
- `ExecutionOutput`
- Prior stage context (`completed_stages`)
- `TraversalState`

**Outputs:** `SynthesizerOutput`
```python
class SynthesizerOutput:
    entities: List[Entity]           # Discovered code entities
    key_flows: List[FlowDescription] # Identified code flows
    open_questions: List[str]        # What we still don't know
    contradictions: List[str]        # Conflicting information found
    hints_for_goals: Dict[str, str]  # goal -> hints for refinement
    accumulated_evidence: List[Evidence]  # Grounded in [file:line]
```

**Behavior:**
- Consume execution results and synthesize "what we now know"
- Identify entities, flows, patterns in the code
- Surface open questions and contradictions
- Provide hints for goal refinement/addition
- Does NOT finalize the answer – refines internal picture across stages
- All findings must be grounded with `[file:line]` citations

**Tools:** None (pure synthesis reasoning)

---

### 6. Critic Agent (LLM)

**Role:** Validate whether target goals were satisfied and drive routing.

**Inputs:**
- `ExecutionOutput`
- `SynthesizerOutput`
- `target_goals` (from current stage's plan)
- `remaining_goals`

**Outputs:** `CriticOutput`
```python
class CriticOutput:
    verdict: CriticVerdict           # APPROVED | REPLAN | CLARIFY
    goal_status: Dict[str, str]      # goal -> 'satisfied' | 'partial' | 'unmet' | 'blocked'
    satisfied_goals: List[str]       # Goals fully satisfied
    remaining_goals: List[str]       # Goals still to pursue
    blocking_issues: List[str]       # Issues preventing progress
    goal_updates: GoalUpdates        # Dynamic goal modifications
    intent_alignment_score: float
    suggested_response: Optional[str]
    replan_feedback: Optional[str]
    clarification_question: Optional[str]  # Required when verdict=CLARIFY
```

**Goal Updates Structure:**
```python
class GoalUpdates:
    new_goals: List[str]             # Add new goals discovered
    refined_goals: Dict[str, str]    # goal -> refined version
    dropped_goals: List[str]         # Goals to abandon (impossible/irrelevant)
    blocked_goals: List[str]         # Goals blocked on external factors
```

**Behavior:**
- Assess each `target_goal` against execution evidence
- Check Synthesizer output for completeness
- Generate `goal_updates` to:
  - **Add** new goals discovered during exploration
  - **Refine/split** existing goals based on findings
  - **Drop** goals that are impossible or irrelevant
  - **Mark blocked** goals needing clarification
- Drive routing decision:
  - `APPROVED` → proceed to next stage or complete
  - `REPLAN` → regenerate plan for current stage
  - `CLARIFY` → ask user for help (with context from exploration)
- Detect "stuck" state (no progress over consecutive stages)
- **Exploration-First Clarification**: Request clarification AFTER exploration when:
  - Multiple matching entities found (e.g., 3 "User" classes)
  - Query references non-existent code
  - Results are contradictory
- Generate fallback clarification question if LLM omits it when `verdict=CLARIFY`

**Tools:** None (pure validation)

---

### 7. Integration Agent (No LLM / Minimal LLM)

**Role:** Build final response and persist state.

**Inputs:**
- `completed_stages` (all stage summaries)
- Final `CriticOutput`
- `ExecutionOutput`
- `TraversalState`

**Outputs:** `IntegrationOutput`
```python
class IntegrationOutput:
    final_response: str              # Citation-backed response
    memory_updated: bool
    events_logged: List[str]
    files_examined: List[str]        # All files touched
    traversal_state_persisted: bool
```

**Behavior:**
- Build final response from accumulated stage results
- Enforce **grounded answers** with `[file:line]` citations
- Persist updated `TraversalState` to L4 storage
- Log events to L2 event log
- Optionally use minimal LLM for response wording refinement

**Tools:** Write-only (session state persistence, event logging)

---

## Multi-Stage Execution Flow

### Stage Control Variables

```python
# In CoreEnvelope
current_stage: int = 1           # Current stage number (1-indexed)
max_stages: int = 5              # Maximum stages allowed
all_goals: List[str]             # All goals from Intent
remaining_goals: List[str]       # Goals not yet satisfied
goal_completion_status: Dict[str, str]  # goal -> status
completed_stages: List[Dict]     # Stage summaries with results
```

### Stage Transition Logic

```
                    ┌─────────────────────────────────────────┐
                    │            STAGE LOOP                    │
                    │                                          │
User Query ──────►  │  ┌────────┐   ┌─────────┐   ┌──────────┐│
                    │  │Planner │ → │Traverser│ → │Synthesizer││
                    │  └────────┘   └─────────┘   └──────────┘│
                    │                     │                    │
                    │                     ▼                    │
                    │              ┌──────────┐                │
                    │              │  Critic  │                │
                    │              └────┬─────┘                │
                    │                   │                      │
                    └───────────────────┼──────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              ┌──────────┐      ┌──────────────┐     ┌─────────┐
              │  REPLAN  │      │  NEXT_STAGE  │     │ COMPLETE│
              │(in-stage)│      │(apply updates)│    │         │
              └────┬─────┘      └──────┬───────┘     └────┬────┘
                   │                   │                  │
                   │   Apply goal_updates:                │
                   │   - Add new_goals                    │
                   │   - Apply refinements                │
                   │   - Remove dropped                   │
                   ▼                   ▼                  ▼
              Back to Planner    Back to Planner    Integration
              (same stage)       (stage + 1)         (finalize)
```

### Goal Update Application

Before each Planner invocation (on stage transition):
```python
def apply_goal_updates(envelope, goal_updates):
    # Add new goals
    for goal in goal_updates.new_goals:
        if goal not in envelope.all_goals:
            envelope.all_goals.append(goal)
            envelope.remaining_goals.append(goal)
            envelope.goal_completion_status[goal] = "pending"

    # Apply refinements
    for old_goal, new_goal in goal_updates.refined_goals.items():
        if old_goal in envelope.remaining_goals:
            envelope.remaining_goals.remove(old_goal)
            envelope.remaining_goals.append(new_goal)
            # Update status tracking

    # Remove dropped goals
    for goal in goal_updates.dropped_goals:
        envelope.remaining_goals = [g for g in envelope.remaining_goals if g != goal]
        envelope.goal_completion_status[goal] = "dropped"
```

---

## Memory Layer Architecture

### Layer Definitions

| Layer | Name | Scope | Purpose |
|-------|------|-------|---------|
| **L1** | Episodic | Per-request | In-envelope state (transient) |
| **L2** | Event Log | Per-request | Tool calls, transitions, responses (append-only) |
| **L3** | Working Memory | Per-session | TraversalState (explored files, symbols, snippets) |
| **L4** | Persistent Cache | Cross-session | Code index, LLM understanding cache, sessions |

### TraversalState (L3 Working Memory)

```python
class TraversalState:
    # Session identification
    session_id: str

    # Query context
    query_intent: str
    scope_path: Optional[str]

    # Exploration tracking
    explored_files: List[str]        # Files examined
    explored_symbols: List[str]      # Symbols looked up
    pending_files: List[str]         # Queued for examination
    pending_symbols: List[str]       # Queued for lookup

    # Accumulated findings
    relevant_snippets: List[CodeSnippet]  # Evidence collection
    call_chain: List[CallChainEntry]      # Traced relationships

    # Loop control
    current_loop: int               # Stage iteration count
    tokens_used: int                # Token budget consumed

    # Repo info
    detected_languages: List[str]
    repo_patterns: Dict[str, Any]
```

### L2 Event Log Schema

```python
class EventLogEntry:
    event_id: str
    timestamp: datetime
    event_type: str  # tool_call | stage_transition | goal_update | error
    agent: str
    payload: Dict[str, Any]
    envelope_id: str
```

---

## Tool Usage Patterns

### Exposed Tools (9 High-Level Tools)

Per Constitution v5.4, only 9 high-level tools are exposed to agents. Base tools are internal.

| Category | Tools | Purpose |
|----------|-------|---------|
| **Composite (5)** | `locate`, `explore_symbol_usage`, `map_module`, `trace_entry_point`, `explain_code_history` | Multi-step workflows with fallbacks |
| **Resilient (2)** | `read_code`, `find_related` | Wrapped base tools with retry/cleanup |
| **Standalone (2)** | `git_status`, `list_tools` | Simple tools, no wrapping needed |

### Internal Base Tools (Not Exposed to Agents)

| Category | Tools | Used By |
|----------|-------|---------|
| **Traversal** | `read_file`, `glob_files`, `grep_search`, `tree_structure` | Composite tools |
| **Index** | `find_symbol`, `get_file_symbols`, `get_imports`, `get_importers` | `locate`, `explore_symbol_usage` |
| **Semantic** | `semantic_search`, `find_similar_files` | `locate`, `find_related` |
| **Git** | `git_log`, `git_blame`, `git_diff` | `explain_code_history` |

### Tool Preferences

Planner should prefer composite tools over individual base tools:
```python
# Preferred: Use locate (tries symbol → grep → semantic)
locate(symbol="AuthService", scope="src/")

# NOT: Direct base tool calls (internal only)
# find_symbol(name="AuthService", language="python")
```

### Traverser Retry Strategies

```python
class RetryStrategy:
    """Deterministic retry heuristics for tool failures."""

    @staticmethod
    def on_empty_grep(step: PlanStep, attempt: int) -> Optional[PlanStep]:
        """Handle empty grep results."""
        if attempt == 1:
            # Broaden pattern
            return step.with_pattern(step.pattern.replace("exact", ".*"))
        elif attempt == 2:
            # Try case insensitive
            return step.with_flags(["-i"])
        elif attempt == 3:
            # Try parent directory
            return step.with_path(parent_of(step.path))
        return None  # Give up

    @staticmethod
    def on_file_not_found(step: PlanStep, attempt: int) -> Optional[PlanStep]:
        """Handle file not found errors."""
        if attempt == 1:
            # Fuzzy match path
            similar = find_similar_paths(step.path)
            if similar:
                return step.with_path(similar[0])
        elif attempt == 2:
            # Check index for symbol
            return find_via_index(step)
        return None
```

---

## Routing Logic

### After Critic: Complete Decision Tree

```python
def route_after_critic(state: JeevesState) -> Literal["next_stage", "complete", "clarify", "replan"]:
    critic = state["critic"]
    remaining_goals = critic.remaining_goals
    blocking_issues = critic.blocking_issues
    current_stage = state["current_stage"]
    max_stages = state["max_stages"]

    # 1. Blocking issues → clarify
    if blocking_issues:
        return "clarify"

    # 2. Explicit clarify verdict
    if critic.verdict == "clarify":
        return "clarify"

    # 3. Replan verdict (within stage retry limit)
    if critic.verdict == "replan":
        if state["iteration"] < 3:
            return "replan"
        return "complete"  # Force complete on max retries

    # 4. All goals satisfied → complete
    if not remaining_goals:
        return "complete"

    # 5. Stage limit reached → complete (partial)
    if current_stage >= max_stages:
        return "complete"

    # 6. Stuck detection (no progress in 2 stages)
    if is_stuck(state["completed_stages"]):
        return "clarify"

    # 7. Continue to next stage
    return "next_stage"
```

### Stage Transition Protocol

```python
def on_next_stage(state: JeevesState) -> JeevesState:
    """Prepare state for next stage."""
    critic = state["critic"]

    # 1. Apply goal updates from critic
    state = apply_goal_updates(state, critic.goal_updates)

    # 2. Mark satisfied goals
    for goal in critic.satisfied_goals:
        state["goal_completion_status"][goal] = "satisfied"
        if goal in state["remaining_goals"]:
            state["remaining_goals"].remove(goal)

    # 3. Save completed stage summary
    state["completed_stages"].append({
        "stage_number": state["current_stage"],
        "satisfied_goals": critic.satisfied_goals,
        "evidence": extract_evidence(state["execution"]),
        "synthesizer_output": state.get("synthesizer"),
    })

    # 4. Advance stage counter
    state["current_stage"] += 1

    # 5. Reset per-stage state (keep accumulated context)
    state["plan"] = None
    state["execution"] = None
    state["synthesizer"] = None
    state["critic"] = None

    return state
```

---

## Context Bounds (Amendment XI)

```python
class CodeContextBounds:
    # Per-step limits
    max_tree_tokens: int = 2000
    max_file_slice_tokens: int = 4000
    max_grep_results: int = 50
    max_symbol_results: int = 100

    # Per-query limits
    max_files_per_query: int = 10
    max_total_code_tokens: int = 25000
    max_traversal_depth: int = 10

    # Multi-stage limits
    max_stages: int = 5
    max_loops_per_stage: int = 3

    # Session limits
    max_session_context_tokens: int = 10000
    max_explored_files_tracked: int = 100

    # LLM limits
    max_llm_calls_per_query: int = 10
    max_agent_hops_per_query: int = 21  # 7 agents × 3 iterations
```

---

## Design Principles

### Constitution v4.0

```
1. ACCURACY          (never hallucinate, always cite [file:line])
2. GOAL-DRIVEN       (satisfy user goals, adapt as code reveals truth)
3. EVIDENCE-GROUNDED (every claim backed by code evidence)
4. BOUNDED           (respect context limits, fail gracefully)
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No AST parsing** | Regex-based supports multiple languages without parsers |
| **Synthesizer agent** | Intermediate understanding enables multi-stage coherence |
| **Dynamic goals** | Code exploration reveals what we actually need to find |
| **Deterministic Traverser** | No LLM = predictable tool execution with bounded retries |
| **Grounded citations** | Every claim must reference `[file:line]` |
| **Stage-based execution** | Complex queries decompose naturally into stages |

---

## Anti-Patterns to Avoid

1. **Don't hallucinate** – Every claim needs a `[file:line]` citation
2. **Don't skip Synthesizer** – It builds the cross-stage understanding
3. **Don't ignore goal updates** – Dynamic goals are key to accurate exploration
4. **Don't exceed bounds** – Use stage limits for large queries
5. **Don't retry infinitely** – Bounded retries with deterministic heuristics
6. **Don't lose stage context** – Persist completed_stages for coherent responses
7. **Don't mix agent responsibilities** – Each agent has one job

---

## Implementation Status

**Last Verified:** 2025-12-13 (Documentation alignment)

### Test Status (✅ Verified 2025-12-10)

| Layer | Test Suite | Result | Notes |
|-------|------------|--------|-------|
| **Go coreengine** | `coreengine/*_test.go` | ✅ All passing | Go unit tests, runtime, envelope |
| **jeeves_avionics** | `tests/unit/llm/` | ✅ **41/41 passed** | Mocks core protocols correctly |
| **jeeves_mission_system** | `tests/contract/` | ✅ Import boundaries verified | Constitutional compliance |
| **jeeves_control_tower** | `tests/` | ✅ All passing | Lifecycle, resources, dispatch |

**Test Architecture Compliance:**
- ✅ Each layer has isolated `tests/fixtures/` with appropriate mocks
- ✅ Go core tests use no external dependencies (pure Go)
- ✅ Avionics tests mock `GenericEnvelope` via jeeves_protocols bridge
- ✅ Import boundary tests enforce constitutional layer separation

### Layered Architecture with Control Tower (✅ Complete)

The system is organized with **Control Tower** as the central orchestration kernel:

```
Gateway (HTTP/gRPC)
        ↓
┌───────────────────────────────────────────────────────────────┐
│                    CONTROL TOWER (Kernel)                      │
│  LifecycleManager → ResourceTracker → CommBusCoordinator      │
└───────────────────────────────────────────────────────────────┘
        ↓ dispatches to
jeeves_mission_system/  →  Application layer (verticals, API, orchestration)
        ↓
jeeves_avionics/        →  Infrastructure (database, LLM, gateway, memory)
        ↓
Go Core (commbus, coreengine)  →  Pure orchestration runtime
```

**Control Tower Responsibilities:**
- **LifecycleManager**: Request scheduling (process scheduler equivalent)
- **ResourceTracker**: Quota enforcement (cgroups equivalent)
- **CommBusCoordinator**: Service dispatch (IPC manager equivalent)
- **EventAggregator**: Interrupt handling and event streaming

### Core Architecture (✅ Complete)
- [x] GenericEnvelope with multi-stage fields (`coreengine/envelope/generic.go` + `jeeves_protocols/envelope.py`)
- [x] TraversalState model (`jeeves_mission_system/verticals/code_analysis/agents/traversal_state.py`)
- [x] SynthesizerOutput model (`jeeves_protocols/envelope.py`)
- [x] GoalUpdates structure (`jeeves_protocols/envelope.py`)
- [x] CriticOutput with goal_updates (`jeeves_protocols/envelope.py`)
- [x] CodeContextBounds enforcement (`jeeves_avionics/context_bounds.py`)

### 7-Agent Pipeline (✅ All Agents Implemented)
| # | Agent | Location | Status |
|---|-------|----------|--------|
| 1 | Perception | `jeeves-capability-code-analyser/agents/` | ✅ No LLM |
| 2 | Intent | `jeeves-capability-code-analyser/agents/` | ✅ Goal extraction |
| 3 | Planner | `jeeves-capability-code-analyser/agents/` | ✅ Stage context + tool hints |
| 4 | Traverser (Executor) | `jeeves-capability-code-analyser/agents/` | ✅ Tool execution |
| 5 | Synthesizer | `jeeves-capability-code-analyser/agents/` | ✅ Intermediate understanding |
| 6 | Critic | `jeeves-capability-code-analyser/agents/` | ✅ Goal validation |
| 7 | Integration | `jeeves-capability-code-analyser/agents/` | ✅ Citation building |

**Note:** Pipeline config in `jeeves-capability-code-analyser/pipeline_config.py`. Orchestration in `jeeves-capability-code-analyser/orchestration/`.

### Multi-Stage Execution (✅ Fully Wired)
- [x] Goal tracking methods: `initialize_goals()`, `advance_stage()`, `get_stage_context()`, `is_stuck()`
- [x] Stage transition node (`jeeves_mission_system/orchestrator/code_analysis_graph.py`)
- [x] Multi-stage routing (`jeeves_mission_system/orchestrator/langgraph/routing.py`)
- [x] Stuck detection after 2 stages with no progress

### Planner Enhancements (✅ Replan Loop Fix)
- [x] Stage context in prompt
- [x] Known files section
- [x] Index-aware tool preferences
- [x] Tree structure → traversal_state

---

## Pre-v1.0 Goals (Constitution v5.0 Compliance)

These goals implement Constitution v5.0 evidence chain and bounded retry requirements.

### Evidence Chain Integrity

**Problem:** Integration sometimes builds responses from Critic's `suggested_response` instead of actual tool execution results, breaking the evidence chain.

**Required Changes:**

| Task | File | Priority |
|------|------|----------|
| Remove `suggested_response` from CriticOutput | `agents/envelope.py` | HIGH |
| Integration builds ONLY from `completed_stages` | `agents/code_analysis/integration.py` | HIGH |
| Add contract test: no claim without `[file:line]` | `tests/contract/` | MEDIUM |

**Enforcement Rule:**
```
Tool Execution → ExecutionOutput → SynthesizerOutput → Integration → Response
                                        ↓
                          All claims trace to [file:line]
```

### Bounded Retry Contracts

**Problem:** Traverser has no formal retry contract. Failed tools produce empty results that propagate through pipeline.

**Required Changes:**

| Task | File | Priority |
|------|------|----------|
| Add `attempt_history` to ExecutionOutput | `agents/envelope.py` | HIGH |
| Implement retry strategies in Traverser | `agents/traverser/agent.py` | HIGH |
| Add `max_retries_per_step` threshold (default: 2) | `config/code_context_bounds.py` | LOW |

**Retry Strategy Table:**

| Failure | Strategy 1 | Strategy 2 |
|---------|------------|------------|
| Empty grep | Broaden pattern | Try parent dir |
| File not found | Fuzzy match | Check index |
| Timeout | Reduce scope | Skip step |

**Contract:**
- Max 2 retries per step (deterministic, no LLM)
- Return `attempt_history` showing each step tried
- Partial results acceptable with explanation

### TraversalState Hygiene

**Problem:** Unbounded collections can grow indefinitely for large repos.

| Collection | Current Limit | Target |
|------------|---------------|--------|
| `explored_files` | 100 | 100 (OK) |
| `explored_symbols` | None | 200 |
| `relevant_snippets` | None | 50 |
| `call_chain` | None | 20 |

---

### Implementation Checklist (Pre-v1.0)

**Evidence Chain:**
- [x] Remove `suggested_response` from CriticOutput model (never existed - verified)
- [x] Update Critic prompt to not generate response text (never did - verified)
- [x] Update Integration to build from `completed_stages` only
- [ ] Add contract test validating evidence chain

**Bounded Retry:**
- [x] Add `attempt_history: Dict[str, List[AttemptRecord]]` to ExecutionOutput
- [x] Implement `_execute_step()` with retry strategies in Traverser
- [x] Add retry strategy selection logic (deterministic)
- [x] Add `max_retries_per_step` to CodeContextBounds (default: 2)

**TraversalState Hygiene:**
- [x] Add FIFO pruning to `explored_symbols` (limit: 200)
- [x] Add FIFO pruning to `relevant_snippets` (limit: 50)
- [x] Add FIFO pruning to `call_chain` (limit: 20)

---

### Known Audit Issues (Technical Debt)

| Issue | Requirement | Status |
|-------|-------------|--------|
| ~~Critic builds `suggested_response`~~ | Evidence Chain | ✅ Never existed |
| ~~Integration uses Critic response as fallback~~ | Evidence Chain | ✅ Fixed - builds from completed_stages |
| ~~No retry logic in Traverser~~ | Bounded Retry | ✅ Fixed - deterministic strategies |
| ~~No `attempt_history` in ExecutionOutput~~ | Bounded Retry | ✅ Fixed - AttemptRecord tracking |
| ~~Unbounded TraversalState collections~~ | — | ✅ Fixed - limits applied |
| Feasibility score computed but not gated | — | Nice to have |
| Contract tests for evidence chain | Evidence Chain | Should add |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `JEEVES_CORE_CONSTITUTION.md` | Governing principles (overview) |
| `jeeves_control_tower/CONSTITUTION.md` | Control Tower constitution (kernel layer) |
| `coreengine/` | Go Core Engine (envelope, runtime, agents) |
| `commbus/` | Go CommBus (messaging, protocols) |
| `jeeves_avionics/CONSTITUTION.md` | Avionics constitution (extends Core) |
| `jeeves_mission_system/CONSTITUTION.md` | Mission System constitution (extends Avionics) |
| `jeeves_avionics/context_bounds.py` | Context limit configuration |
| `jeeves_mission_system/orchestrator/langgraph/routing.py` | Stage routing logic |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0-6.0 | Prior | Original Jeeves FF trajectory |
| 7.0 | 2025-12-03 | Added RAG, Meta Planner, multi-GB support |
| 8.0 | 2025-12-03 | **7-Agent Final Form**: Synthesizer agent, dynamic goals, multi-stage flow |
| 8.1 | 2025-12-04 | **Pre-v1.0 Goals**: Added Constitution v5.0 compliance section (evidence chain, bounded retry). Defined evidence chain and bounded retry as blocking requirements. |
| 8.2 | 2025-12-04 | **Pre-v1.0 Implementation**: Evidence chain (Integration builds from completed_stages), bounded retry (AttemptRecord, deterministic strategies), TraversalState hygiene (limits enforced). |
| 8.3 | 2025-12-05 | **Tool Consolidation**: Updated Tool Usage Patterns to reflect 9 exposed tools (5 composite + 2 resilient + 2 standalone). Removed find_code (consolidated into locate). All documentation aligned with Constitution v5.4. |
| **8.4** | 2025-12-06 | **Repository Restructure**: Updated file paths to reflect three-layer architecture (`jeeves_core_engine/`, `jeeves_avionics/`, `jeeves_mission_system/`). Updated Related Documents to reference component constitutions. Docker config moved to `docker/`, requirements to `requirements/`. |
| **8.5** | 2025-12-06 | **Test Audit**: Verified test architecture compliance across all layers. Fixed mock agents in core_engine tests to match current pydantic schemas. Confirmed 109 core tests and 41 avionics LLM tests pass. Added Test Status section. |
| **8.6** | 2025-12-10 | **Path Corrections**: Fixed all `jeeves_core_engine/` Python paths to reflect actual Go packages (`coreengine/`, `commbus/`). Updated context_bounds location to `jeeves_avionics/`. Added Control Tower test layer. Corrected Related Documents table. |
| **8.7** | 2025-12-13 | **Architecture Cleanup**: Updated 7-agent pipeline paths to reflect `jeeves-capability-code-analyser/` location. Pipeline config and orchestration correctly documented. Documentation aligned with code as single source of truth. |

---

*This document describes the target architecture. For current implementation status, see the "Implementation Status" section above.*

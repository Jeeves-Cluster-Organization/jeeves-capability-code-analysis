"""
Code Analysis Pipeline Configuration - Declarative agent definitions.

This replaces the 7 concrete agent classes with configuration-driven definitions.
The UnifiedRuntime uses this config to execute the pipeline.

Migration:
- CodeAnalysisPerceptionAgent → AgentConfig(name="perception", ...)
- CodeAnalysisIntentAgent → AgentConfig(name="intent", has_llm=True, ...)
- etc.

Capability-specific logic (prompts, mock handlers, normalizers) is provided
via hook functions defined here.
"""

from typing import Any, Dict, List, Optional
from jeeves_mission_system.contracts_core import (
    AgentConfig,
    PipelineConfig,
    RoutingRule,
    ToolAccess,
    TerminalReason,
)


# ─────────────────────────────────────────────────────────────────
# HOOK FUNCTIONS - Capability-specific logic
# ─────────────────────────────────────────────────────────────────

def perception_pre_process(envelope: Any, agent: Any = None) -> Any:
    """Perception pre-process: normalize input, load context."""
    # Normalize input
    raw = envelope.raw_input.strip()

    # Build perception output
    output = {
        "normalized_input": raw,
        "context_summary": envelope.metadata.get("context_summary", ""),
        "session_scope": envelope.session_id,
        "detected_languages": [],  # Could detect from context
    }

    envelope.outputs["perception"] = output
    return envelope


def perception_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock perception for testing."""
    return {
        "normalized_input": envelope.raw_input.strip(),
        "context_summary": "Mock context",
        "session_scope": envelope.session_id,
        "detected_languages": ["python"],
    }


def intent_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock intent analysis for testing."""
    msg_lower = envelope.raw_input.lower()

    if any(kw in msg_lower for kw in ["flow", "trace", "call"]):
        intent = "trace_flow"
    elif any(kw in msg_lower for kw in ["where", "find", "definition"]):
        intent = "find_definition"
    elif any(kw in msg_lower for kw in ["explain", "what does"]):
        intent = "explain_code"
    else:
        intent = "understand_architecture"

    goals = [f"Understand {intent.replace('_', ' ')}"]

    return {
        "intent": intent,
        "goals": goals,
        "constraints": [],
        "confidence": 0.85,
        "clarification_needed": False,
        "clarification_question": None,
    }


def intent_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Initialize goals after intent."""
    goals = output.get("goals", [])
    if goals:
        envelope.initialize_goals(goals)

    # Check for clarification
    if output.get("clarification_needed"):
        envelope.clarification_pending = True
        envelope.clarification_question = output.get("clarification_question")

    return envelope


def planner_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock plan generation for testing."""
    intent_output = envelope.outputs.get("intent", {})
    intent = intent_output.get("intent", "understand_architecture")

    # Generate mock plan based on intent
    if intent == "trace_flow":
        steps = [
            {"step_id": "step_1", "tool": "search_code", "parameters": {"query": "main entry"}},
            {"step_id": "step_2", "tool": "read_file", "parameters": {"path": "src/main.py"}},
        ]
    elif intent == "find_definition":
        steps = [
            {"step_id": "step_1", "tool": "search_symbol", "parameters": {"symbol": "unknown"}},
        ]
    else:
        steps = [
            {"step_id": "step_1", "tool": "list_files", "parameters": {"path": "src/"}},
        ]

    return {
        "plan_id": f"plan_{envelope.envelope_id}",
        "steps": steps,
        "rationale": f"Mock plan for {intent}",
        "feasibility_score": 0.9,
    }


def executor_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Post-process executor results."""
    # Update traversal state in metadata
    results = output.get("results", [])
    explored_files = []
    for r in results:
        if r.get("tool") in ("read_file", "inspect_file"):
            path = r.get("parameters", {}).get("path")
            if path:
                explored_files.append(path)

    if "traversal_state" not in envelope.metadata:
        envelope.metadata["traversal_state"] = {}
    envelope.metadata["traversal_state"]["explored_files"] = explored_files

    return envelope


def synthesizer_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock synthesis for testing."""
    return {
        "entities": [{"name": "MockEntity", "type": "class", "location": "src/main.py"}],
        "key_flows": [{"name": "main", "steps": ["start", "process", "end"]}],
        "patterns": [],
        "summary": "Mock synthesis complete",
        "evidence_summary": "Based on code analysis",
    }


def critic_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock critic evaluation for testing."""
    return {
        "verdict": "approved",
        "confidence": 0.9,
        "intent_alignment_score": 0.85,
        "issues": [],
        "recommendations": [],
        "goal_updates": {
            "satisfied": envelope.all_goals[:1] if envelope.all_goals else [],
            "pending": envelope.all_goals[1:] if len(envelope.all_goals) > 1 else [],
            "added": [],
        },
    }


def critic_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Handle critic verdict routing."""
    verdict = output.get("verdict", "approved")

    # Handle goal updates
    goal_updates = output.get("goal_updates", {})
    satisfied = goal_updates.get("satisfied", [])

    if satisfied:
        for goal in satisfied:
            envelope.goal_completion_status[goal] = "satisfied"
            if goal in envelope.remaining_goals:
                envelope.remaining_goals.remove(goal)

    # Store feedback for potential reintent
    if verdict == "reintent":
        feedback = output.get("refine_hint", "Needs refinement")
        envelope.metadata["critic_feedback_for_intent"] = {
            "prior_intent": envelope.outputs.get("intent", {}),
            "refine_hint": feedback,
            "issues": output.get("issues", []),
        }

    return envelope


def integration_mock_handler(envelope: Any) -> Dict[str, Any]:
    """Mock integration for testing."""
    synthesizer = envelope.outputs.get("synthesizer", {})
    summary = synthesizer.get("summary", "Analysis complete")

    return {
        "final_response": f"Code Analysis Result:\n\n{summary}",
        "citations": [],
        "files_examined": envelope.metadata.get("traversal_state", {}).get("explored_files", []),
    }


def integration_post_process(envelope: Any, output: Dict[str, Any], agent: Any = None) -> Any:
    """Mark envelope as complete after integration."""
    envelope.terminate("completed_successfully", TerminalReason.COMPLETED_SUCCESSFULLY)
    return envelope


# ─────────────────────────────────────────────────────────────────
# PIPELINE CONFIGURATION
# ─────────────────────────────────────────────────────────────────

CODE_ANALYSIS_PIPELINE = PipelineConfig(
    name="code_analysis",
    max_iterations=3,
    max_llm_calls=10,
    max_agent_hops=21,
    enable_arbiter=False,  # Read-only pipeline, no arbiter needed
    # Capability-defined resume stages (not hardcoded in runtime)
    clarification_resume_stage="intent",  # REINTENT architecture: clarifications go through Intent
    confirmation_resume_stage="executor",  # Confirmations resume at tool execution
    agents=[
        # ─── Agent 1: Perception ───
        AgentConfig(
            name="perception",
            stage_order=0,
            has_llm=False,
            has_tools=False,
            tool_access=ToolAccess.READ,
            output_key="perception",
            pre_process=perception_pre_process,
            mock_handler=perception_mock_handler,
            default_next="intent",
        ),

        # ─── Agent 2: Intent ───
        AgentConfig(
            name="intent",
            stage_order=1,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.intent",
            output_key="intent",
            required_output_fields=["intent", "goals"],
            mock_handler=intent_mock_handler,
            post_process=intent_post_process,
            routing_rules=[
                RoutingRule("clarification_needed", True, "clarification"),
            ],
            default_next="planner",
        ),

        # ─── Agent 3: Planner ───
        AgentConfig(
            name="planner",
            stage_order=2,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.planner",
            tool_access=ToolAccess.READ,  # For tool listing
            output_key="plan",
            required_output_fields=["steps"],
            mock_handler=planner_mock_handler,
            default_next="executor",
        ),

        # ─── Agent 4: Executor (Traverser) ───
        AgentConfig(
            name="executor",
            stage_order=3,
            has_llm=False,
            has_tools=True,
            tool_access=ToolAccess.ALL,
            output_key="execution",
            post_process=executor_post_process,
            default_next="synthesizer",
        ),

        # ─── Agent 5: Synthesizer ───
        AgentConfig(
            name="synthesizer",
            stage_order=4,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.synthesizer",
            output_key="synthesizer",
            mock_handler=synthesizer_mock_handler,
            default_next="critic",
        ),

        # ─── Agent 6: Critic ───
        AgentConfig(
            name="critic",
            stage_order=5,
            has_llm=True,
            model_role="critic",
            prompt_key="code_analysis.critic",
            output_key="critic",
            required_output_fields=["verdict"],
            mock_handler=critic_mock_handler,
            post_process=critic_post_process,
            routing_rules=[
                RoutingRule("verdict", "reintent", "intent"),
                RoutingRule("verdict", "next_stage", "planner"),
            ],
            default_next="integration",
        ),

        # ─── Agent 7: Integration ───
        AgentConfig(
            name="integration",
            stage_order=6,
            has_llm=True,
            model_role="planner",
            prompt_key="code_analysis.integration",
            tool_access=ToolAccess.WRITE,
            output_key="integration",
            required_output_fields=["final_response"],
            mock_handler=integration_mock_handler,
            post_process=integration_post_process,
            default_next="end",
        ),
    ],
)


def get_code_analysis_pipeline() -> PipelineConfig:
    """Get the code analysis pipeline configuration."""
    return CODE_ANALYSIS_PIPELINE


__all__ = [
    "CODE_ANALYSIS_PIPELINE",
    "get_code_analysis_pipeline",
]

"""
Node wrappers for Code Analysis 7-agent pipeline.

Centralized Architecture (v4.0):
- Uses GenericEnvelope instead of CoreEnvelope
- Agents defined via AgentConfig in pipeline_config.py
- Hooks provide capability-specific logic
- UnifiedRuntime can be used for full pipeline execution

These nodes convert between state dict and GenericEnvelope:
1. Converting JeevesState dict -> GenericEnvelope
2. Calling agent hooks or UnifiedRuntime
3. Converting result -> state update dict

Pipeline: perception → intent → planner → executor → synthesizer → critic → integration
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from jeeves_mission_system.adapters import get_logger
from jeeves_mission_system.contracts_core import (
    GenericEnvelope,
    CriticVerdict,
    TerminalReason,
    LoggerProtocol,
    UnifiedRuntime,
    PipelineConfig,
)
from jeeves_mission_system.orchestrator.state import JeevesState


def _create_confidence_snapshot(stage: str, output: Dict[str, Any]) -> Dict[str, Any]:
    """Create a confidence snapshot for the audit trail."""
    confidence = output.get("confidence")
    factors = output.get("confidence_factors", {})

    if "intent_alignment_score" in output:
        confidence = output["intent_alignment_score"]
    if "alignment_breakdown" in output:
        factors = output["alignment_breakdown"]

    return {
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence": confidence,
        "factors": factors,
    }


def _envelope_from_state(state: JeevesState) -> GenericEnvelope:
    """Convert LangGraph state to GenericEnvelope."""
    return GenericEnvelope.from_state_dict(dict(state))


def _state_from_envelope(envelope: GenericEnvelope, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convert GenericEnvelope to state update dict."""
    update = envelope.to_state_dict()
    if extra:
        update.update(extra)
    return update


class CodeAnalysisNodes:
    """
    LangGraph node wrappers for code analysis pipeline.

    Centralized Architecture (v4.0):
    - Uses GenericEnvelope with dynamic outputs dict
    - Calls hooks from pipeline_config for capability-specific logic
    - No concrete agent classes - all config-driven
    """

    def __init__(
        self,
        runtime: Optional[UnifiedRuntime] = None,
        pipeline_config: Optional[PipelineConfig] = None,
        logger: Optional[LoggerProtocol] = None,
    ):
        """
        Initialize node wrappers.

        Args:
            runtime: Optional UnifiedRuntime for full pipeline execution
            pipeline_config: Optional PipelineConfig for hook access
            logger: Optional logger instance
        """
        self._logger = logger or get_logger()
        self._runtime = runtime
        self._config = pipeline_config

    def _get_hook(self, agent_name: str, hook_type: str) -> Optional[Any]:
        """Get hook function from pipeline config."""
        if not self._config:
            return None
        agent_config = self._config.get_agent(agent_name)
        if not agent_config:
            return None
        return getattr(agent_config, hook_type, None)

    async def perception_node(self, state: JeevesState) -> Dict[str, Any]:
        """Perception node - load session state and detect scope."""
        self._logger.info(
            "perception_node_start",
            envelope_id=state.get("envelope_id"),
            request_id=state.get("request_id"),
        )

        envelope = _envelope_from_state(state)

        # Call pre_process hook
        pre_process = self._get_hook("perception", "pre_process")
        if pre_process:
            envelope = pre_process(envelope)

        envelope.current_stage = "intent"

        self._logger.info(
            "perception_node_complete",
            envelope_id=envelope.envelope_id,
            has_output=envelope.has_output("perception"),
        )

        return {
            "outputs": envelope.outputs,
            "current_stage": envelope.current_stage,
            "metadata": envelope.metadata,
        }

    async def intent_node(self, state: JeevesState) -> Dict[str, Any]:
        """Intent node - classify code analysis query."""
        is_reintent = state.get("is_reintent", False)

        self._logger.info(
            "intent_node_start",
            envelope_id=state.get("envelope_id"),
            is_reintent=is_reintent,
            iteration=state.get("iteration", 0),
        )

        envelope = _envelope_from_state(state)

        # Use mock handler if available (for testing)
        mock_handler = self._get_hook("intent", "mock_handler")
        if mock_handler:
            output = mock_handler(envelope)
            envelope.set_output("intent", output)

            # Call post_process hook
            post_process = self._get_hook("intent", "post_process")
            if post_process:
                envelope = post_process(envelope, output)

        updates = {
            "outputs": envelope.outputs,
            "current_stage": "planner",
            "is_reintent": False,
            "reintent_context": None,
            "all_goals": envelope.all_goals,
            "remaining_goals": envelope.remaining_goals,
        }

        # Record confidence snapshot
        intent_output = envelope.get_output("intent") or {}
        if intent_output:
            updates["confidence_history"] = [_create_confidence_snapshot("intent", intent_output)]

        # Handle clarification
        if envelope.clarification_pending:
            updates["clarification_required"] = True
            updates["clarification_question"] = envelope.clarification_question
            updates["current_stage"] = "clarification"

        self._logger.info(
            "intent_node_complete",
            envelope_id=envelope.envelope_id,
            intent=intent_output.get("intent"),
            goals_count=len(envelope.all_goals),
            clarification_needed=envelope.clarification_pending,
        )

        return updates

    async def planner_node(self, state: JeevesState) -> Dict[str, Any]:
        """Planner node - generate code traversal plan."""
        self._logger.info(
            "planner_node_start",
            envelope_id=state.get("envelope_id"),
            iteration=state.get("iteration", 0),
        )

        envelope = _envelope_from_state(state)

        # Use mock handler if available
        mock_handler = self._get_hook("planner", "mock_handler")
        if mock_handler:
            output = mock_handler(envelope)
            envelope.set_output("plan", output)

        plan_output = envelope.get_output("plan") or {}
        step_count = len(plan_output.get("steps", []))

        self._logger.info(
            "planner_node_complete",
            envelope_id=envelope.envelope_id,
            step_count=step_count,
        )

        return {
            "outputs": envelope.outputs,
            "current_stage": "executor",
        }

    async def executor_node(self, state: JeevesState) -> Dict[str, Any]:
        """Executor node - execute code analysis tools."""
        self._logger.info(
            "executor_node_start",
            envelope_id=state.get("envelope_id"),
        )

        envelope = _envelope_from_state(state)

        # Executor typically runs tools - mock for now
        # In production, UnifiedRuntime handles this
        execution_output = {
            "results": [],
            "all_succeeded": True,
            "summary": "Execution completed",
        }
        envelope.set_output("execution", execution_output)

        # Call post_process hook
        post_process = self._get_hook("executor", "post_process")
        if post_process:
            envelope = post_process(envelope, execution_output)

        self._logger.info(
            "executor_node_complete",
            envelope_id=envelope.envelope_id,
        )

        return {
            "outputs": envelope.outputs,
            "current_stage": "synthesizer",
            "metadata": envelope.metadata,
        }

    async def synthesizer_node(self, state: JeevesState) -> Dict[str, Any]:
        """Synthesizer node - aggregate findings from execution."""
        self._logger.info(
            "synthesizer_node_start",
            envelope_id=state.get("envelope_id"),
        )

        envelope = _envelope_from_state(state)

        # Use mock handler if available
        mock_handler = self._get_hook("synthesizer", "mock_handler")
        if mock_handler:
            output = mock_handler(envelope)
            envelope.set_output("synthesizer", output)

        synth_output = envelope.get_output("synthesizer") or {}

        self._logger.info(
            "synthesizer_node_complete",
            envelope_id=envelope.envelope_id,
            entities_count=len(synth_output.get("entities", [])),
        )

        return {
            "outputs": envelope.outputs,
            "current_stage": "critic",
        }

    async def critic_node(self, state: JeevesState) -> Dict[str, Any]:
        """Critic node - validate results and check for hallucinations."""
        self._logger.info(
            "critic_node_start",
            envelope_id=state.get("envelope_id"),
            iteration=state.get("iteration", 0),
        )

        envelope = _envelope_from_state(state)

        # Use mock handler if available
        mock_handler = self._get_hook("critic", "mock_handler")
        if mock_handler:
            output = mock_handler(envelope)
            envelope.set_output("critic", output)

            # Call post_process hook
            post_process = self._get_hook("critic", "post_process")
            if post_process:
                envelope = post_process(envelope, output)

        critic_output = envelope.get_output("critic") or {}
        verdict = critic_output.get("verdict", "approved")

        updates = {
            "outputs": envelope.outputs,
            "goal_completion_status": envelope.goal_completion_status,
            "remaining_goals": envelope.remaining_goals,
        }

        # Record confidence snapshot
        if critic_output:
            updates["confidence_history"] = [_create_confidence_snapshot("critic", critic_output)]

        # Determine next stage based on verdict
        if verdict == "reintent":
            updates["current_stage"] = "intent"
            updates["is_reintent"] = True
            updates["iteration"] = state.get("iteration", 0) + 1
            updates["reintent_context"] = {
                "refine_hint": critic_output.get("refine_intent_hint"),
                "issues": critic_output.get("issues", []),
            }
        elif verdict == "next_stage":
            updates["current_stage"] = "planner"
            updates["current_stage_number"] = envelope.current_stage_number + 1
        else:  # approved
            updates["current_stage"] = "integration"

        self._logger.info(
            "critic_node_complete",
            envelope_id=envelope.envelope_id,
            verdict=verdict,
            next_stage=updates["current_stage"],
        )

        return updates

    async def integration_node(self, state: JeevesState) -> Dict[str, Any]:
        """Integration node - build response with citations."""
        self._logger.info(
            "integration_node_start",
            envelope_id=state.get("envelope_id"),
        )

        envelope = _envelope_from_state(state)

        # Use mock handler if available
        mock_handler = self._get_hook("integration", "mock_handler")
        if mock_handler:
            output = mock_handler(envelope)
            envelope.set_output("integration", output)

            # Call post_process hook
            post_process = self._get_hook("integration", "post_process")
            if post_process:
                envelope = post_process(envelope, output)

        integration_output = envelope.get_output("integration") or {}
        response_length = len(integration_output.get("final_response", ""))

        self._logger.info(
            "integration_node_complete",
            envelope_id=envelope.envelope_id,
            response_length=response_length,
        )

        return {
            "outputs": envelope.outputs,
            "current_stage": "end",
            "terminated": True,
            "termination_reason": envelope.termination_reason or "completed_successfully",
        }


# Routing functions for LangGraph conditional edges

def route_after_critic(state: JeevesState) -> str:
    """Route after critic based on verdict."""
    critic_output = state.get("outputs", {}).get("critic", {})
    verdict = critic_output.get("verdict", "approved")

    if verdict == "reintent":
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)
        if iteration >= max_iterations:
            return "integration"  # Force completion
        return "intent"  # Re-analyze
    elif verdict == "next_stage":
        return "planner"  # Next goal set
    else:
        return "integration"  # Complete


def route_after_intent(state: JeevesState) -> str:
    """Route after intent - check for clarification."""
    if state.get("clarification_required"):
        return "clarification"
    return "planner"


__all__ = [
    "CodeAnalysisNodes",
    "route_after_critic",
    "route_after_intent",
]

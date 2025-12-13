"""Agent configuration modes for code analysis pipeline.

The code analysis pipeline uses a fixed 7-agent architecture:
Perception → Intent → Planner → Traverser → Synthesizer → Critic → Integration

These modes control resource allocation and feature flags, not agent selection.
"""

AGENT_MODES = {
    "standard": {
        "agents": ["perception", "intent", "planner", "traverser", "synthesizer", "critic", "integration"],
        "description": "Full 7-agent code analysis pipeline",
        "features": [
            "perception", "intent", "planning", "traversal",
            "synthesis", "validation", "response"
        ],
        "avg_latency_ms": 3000
    },
    "full": {
        "agents": ["perception", "intent", "planner", "traverser", "synthesizer", "critic", "integration"],
        "description": "Full 7-agent pipeline with multi-stage execution",
        "features": [
            "perception", "intent", "planning", "traversal",
            "synthesis", "validation", "response", "multi_stage"
        ],
        "avg_latency_ms": 5000,
        "max_stages": 5
    }
}


def get_agent_mode(mode: str) -> dict:
    """Get agent configuration for a mode."""
    if mode not in AGENT_MODES:
        raise ValueError(f"Invalid mode: {mode}. Valid modes: {list(AGENT_MODES.keys())}")
    return AGENT_MODES[mode]


def list_modes() -> list:
    """List all available agent modes."""
    return list(AGENT_MODES.keys())

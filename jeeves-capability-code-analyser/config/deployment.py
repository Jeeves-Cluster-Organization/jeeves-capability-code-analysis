"""
Node Profiles and Deployment Configuration for Code Analysis Capability.

Defines hardware profiles and agent assignments for distributed deployment.
"""

import os
from typing import Dict, List

from jeeves_protocols import NodeProfile


CODE_ANALYSIS_AGENTS = [
    "perception",
    "intent",
    "planner",
    "traverser",
    "synthesizer",
    "critic",
    "integration",
]


PROFILES: Dict[str, NodeProfile] = {
    "single_node": NodeProfile(
        name="single-node-dev",
        vram_gb=6,
        ram_gb=20,
        model="qwen2.5-7b-instruct-q4_K_M.gguf",
        model_size_gb=4.4,
        max_parallel=4,
        agents=CODE_ANALYSIS_AGENTS,
        base_url=os.getenv("LLAMASERVER_HOST", "http://localhost:8080"),
        gpu_id=0,
        metadata={
            "purpose": "Development and testing",
            "gpu_model": "Any 6GB+ VRAM",
            "priority": "development",
            "backend": "llama-server"
        }
    ),
    "node1": NodeProfile(
        name="node1-perception-intent",
        vram_gb=6,
        ram_gb=20,
        model="qwen2.5-7b-instruct-q4_K_M.gguf",
        model_size_gb=4.4,
        max_parallel=4,
        agents=["perception", "intent", "integration"],
        base_url=os.getenv("LLAMASERVER_NODE1_URL", "http://node1:8080"),
        gpu_id=0,
        metadata={
            "purpose": "Fast agents: perception, intent, integration",
            "gpu_model": "6GB VRAM",
            "priority": "medium",
            "backend": "llama-server",
            "n_gpu_layers": 28
        }
    ),
    "node2": NodeProfile(
        name="node2-traverser",
        vram_gb=6,
        ram_gb=20,
        model="deepseek-coder-6.7b-instruct-q4_K_M.gguf",
        model_size_gb=4.1,
        max_parallel=4,
        agents=["traverser"],
        base_url=os.getenv("LLAMASERVER_NODE2_URL", "http://node2:8080"),
        gpu_id=1,
        metadata={
            "purpose": "Code traversal with code-specialized model",
            "gpu_model": "6GB VRAM",
            "priority": "medium",
            "specialized": "code",
            "backend": "llama-server",
            "n_gpu_layers": 28
        }
    ),
    "node3": NodeProfile(
        name="node3-reasoning-hub",
        vram_gb=12,
        ram_gb=32,
        model="qwen2.5-14b-instruct-q4_K_M.gguf",
        model_size_gb=8.5,
        max_parallel=8,
        agents=["planner", "synthesizer", "critic"],
        base_url=os.getenv("LLAMASERVER_NODE3_URL", "http://node3:8080"),
        gpu_id=2,
        metadata={
            "purpose": "Complex reasoning: planning, synthesis, validation",
            "gpu_model": "12GB VRAM",
            "priority": "high",
            "backend": "llama-server",
            "n_gpu_layers": 35
        }
    ),
    "node1_2node": NodeProfile(
        name="node1-primary",
        vram_gb=12,
        ram_gb=32,
        model="qwen2.5-14b-instruct-q4_K_M.gguf",
        model_size_gb=8.5,
        max_parallel=8,
        agents=["perception", "intent", "planner", "synthesizer", "critic"],
        base_url=os.getenv("LLAMASERVER_NODE1_URL", "http://node1:8080"),
        metadata={
            "setup": "2-node",
            "role": "primary",
            "backend": "llama-server"
        }
    ),
    "node2_2node": NodeProfile(
        name="node2-secondary",
        vram_gb=12,
        ram_gb=32,
        model="qwen2.5-7b-instruct-q4_K_M.gguf",
        model_size_gb=4.4,
        max_parallel=6,
        agents=["traverser", "integration"],
        base_url=os.getenv("LLAMASERVER_NODE2_URL", "http://node2:8080"),
        metadata={
            "setup": "2-node",
            "role": "secondary",
            "backend": "llama-server"
        }
    ),
    "high_memory_single": NodeProfile(
        name="high-memory-single",
        vram_gb=24,
        ram_gb=64,
        model="qwen2.5-32b-instruct-q4_K_M.gguf",
        model_size_gb=20.0,
        max_parallel=6,
        agents=CODE_ANALYSIS_AGENTS,
        base_url=os.getenv("LLAMASERVER_HOST", "http://localhost:8080"),
        metadata={
            "purpose": "High-quality single-node deployment",
            "gpu_model": "RTX 4090 / A6000",
            "backend": "llama-server"
        }
    ),
}


def get_deployment_mode() -> str:
    """Get current deployment mode from environment."""
    return os.getenv("DEPLOYMENT_MODE", "single_node").lower()


def get_active_profile_names() -> List[str]:
    """Get list of active node profile names based on deployment mode."""
    mode = get_deployment_mode()

    if mode == "distributed":
        has_node3 = os.getenv("LLAMASERVER_NODE3_URL")
        if has_node3:
            return ["node1", "node2", "node3"]
        else:
            return ["node1_2node", "node2_2node"]
    elif mode == "high_memory":
        return ["high_memory_single"]
    else:
        return ["single_node"]


def get_node_for_agent(agent_name: str) -> str:
    """Get the node name assigned to a specific agent."""
    agent_name = agent_name.lower()

    override_key = f"AGENT_NODE_OVERRIDE_{agent_name.upper()}"
    if override := os.getenv(override_key):
        return override

    active_profiles = get_active_profile_names()

    for profile_name in active_profiles:
        profile = PROFILES.get(profile_name)
        if profile and agent_name in [a.lower() for a in profile.agents]:
            return profile_name

    if "single_node" in PROFILES:
        return "single_node"

    raise ValueError(
        f"Agent '{agent_name}' is not assigned to any active node profile. "
        f"Active profiles: {active_profiles}"
    )


def get_profile_for_agent(agent_name: str) -> NodeProfile:
    """Get the NodeProfile for a specific agent."""
    node_name = get_node_for_agent(agent_name)
    profile = PROFILES.get(node_name)

    if not profile:
        raise ValueError(f"Profile '{node_name}' not found in PROFILES")

    return profile


def get_all_agents() -> List[str]:
    """Get list of all agents across all active nodes."""
    active_profiles = get_active_profile_names()
    agents = set()

    for profile_name in active_profiles:
        profile = PROFILES.get(profile_name)
        if profile:
            agents.update(profile.agents)

    return sorted(agents)


def get_node_summary() -> Dict[str, dict]:
    """Get summary of active node configuration."""
    active_profiles = get_active_profile_names()
    summary = {}

    for profile_name in active_profiles:
        profile = PROFILES.get(profile_name)
        if profile:
            summary[profile_name] = {
                "name": profile.name,
                "vram_gb": profile.vram_gb,
                "model": profile.model_name,
                "agents": profile.agents,
                "max_parallel": profile.max_parallel,
                "base_url": profile.base_url,
                "vram_utilization": f"{profile.vram_utilization:.1f}%"
            }

    return summary


def validate_configuration():
    """Validate current node configuration."""
    active_profiles = get_active_profile_names()

    for profile_name in active_profiles:
        if profile_name not in PROFILES:
            raise ValueError(f"Profile '{profile_name}' not found in PROFILES")

    assigned_agents = get_all_agents()
    required_agents = ["planner", "critic"]

    for agent in required_agents:
        if agent not in assigned_agents:
            raise ValueError(f"Required agent '{agent}' is not assigned to any node")

    agent_nodes = {}
    for profile_name in active_profiles:
        profile = PROFILES.get(profile_name)
        if profile:
            for agent in profile.agents:
                if agent in agent_nodes:
                    raise ValueError(
                        f"Agent '{agent}' is assigned to multiple nodes: "
                        f"{agent_nodes[agent]} and {profile_name}"
                    )
                agent_nodes[agent] = profile_name

    return True


if not os.getenv("SKIP_CONFIG_VALIDATION"):
    try:
        validate_configuration()
    except Exception as e:
        import warnings
        warnings.warn(f"Node configuration validation warning: {e}", UserWarning)

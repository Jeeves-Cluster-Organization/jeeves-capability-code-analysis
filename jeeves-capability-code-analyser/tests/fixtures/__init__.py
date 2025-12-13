"""Test fixtures for jeeves-capability-code-analyser.

Centralized Architecture (v4.0):
- Uses GenericEnvelope (not CoreEnvelope)
- Pipeline configuration fixtures (not concrete agents)
- Import from contracts_core

Fixture Categories:
- envelope.py: GenericEnvelope factory and stage fixtures
- mocks/: Mock implementations for LLM, tools, database
- agents.py: Pipeline configuration and mock service fixtures
"""

from .envelope import (
    envelope_factory,
    sample_envelope,
    envelope_with_perception,
    envelope_with_intent,
    envelope_with_plan,
    envelope_with_execution,
    envelope_with_synthesizer,
    envelope_with_critic,
)

from .mocks import (
    MockLLMProvider,
    MockToolRegistry,
    MockToolExecutor,
    MockDatabaseClient,
    MockEventBus,
)

from .agents import (
    mock_llm_provider,
    mock_tool_registry,
    mock_tool_executor,
    mock_db,
    mock_event_bus,
    mock_settings,
    pipeline_config,
    mock_llm_factory,
)

__all__ = [
    # Envelope fixtures
    "envelope_factory",
    "sample_envelope",
    "envelope_with_perception",
    "envelope_with_intent",
    "envelope_with_plan",
    "envelope_with_execution",
    "envelope_with_synthesizer",
    "envelope_with_critic",
    # Mock classes
    "MockLLMProvider",
    "MockToolRegistry",
    "MockToolExecutor",
    "MockDatabaseClient",
    "MockEventBus",
    # Mock service fixtures
    "mock_llm_provider",
    "mock_tool_registry",
    "mock_tool_executor",
    "mock_db",
    "mock_event_bus",
    "mock_settings",
    # Pipeline configuration
    "pipeline_config",
    "mock_llm_factory",
]

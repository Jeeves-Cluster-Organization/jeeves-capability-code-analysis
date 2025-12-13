"""Domain Protocols for Code Analysis Vertical.

These protocols are specific to the code analysis domain and should NOT be in core.
Core orchestration depends only on the 4 core protocols (State, LLM, Tool, EventBus).

Implementations live in memory/services/ and are injected at bootstrap time.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# =============================================================================
# MEMORY LAYER PROTOCOLS (L3, L4, L5)
# =============================================================================

@runtime_checkable
class SessionStateServiceProtocol(Protocol):
    """Protocol for L4 session state operations.

    Implementations: SessionStateService (memory.services.session_state_service)

    Used by agents for:
    - Getting session context for prompts (PerceptionAgent)
    - Recording entity references (IntegrationAgent)
    - Tracking conversation turns (IntegrationAgent)
    """

    async def get_context_for_prompt(
        self,
        session_id: str,
    ) -> Dict[str, Any]:
        """Get session context formatted for prompt inclusion.

        Args:
            session_id: Session identifier

        Returns:
            Dict with summary, recent_entities, focus, pending_clarification
        """
        ...

    async def record_entity_reference(
        self,
        session_id: str,
        entity_type: str,
        entity_id: str,
    ) -> None:
        """Record that an entity was referenced in this session.

        Args:
            session_id: Session identifier
            entity_type: Type of entity (e.g., "task")
            entity_id: Entity identifier
        """
        ...

    async def on_user_turn(
        self,
        session_id: str,
        user_message: str,
    ) -> None:
        """Update session state after a user turn.

        Args:
            session_id: Session identifier
            user_message: The user's message
        """
        ...


@runtime_checkable
class ChunkServiceProtocol(Protocol):
    """Protocol for L3 semantic chunk operations.

    Implementations: ChunkService (memory.services.chunk_service)

    Used by agents for:
    - Semantic search for context retrieval (PerceptionAgent)
    - Storing interaction chunks (IntegrationAgent)
    """

    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Search for semantically similar chunks.

        Args:
            user_id: User identifier
            query: Search query text
            limit: Max results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of matching chunks with content field
        """
        ...

    async def chunk_and_store(
        self,
        user_id: str,
        source_type: str,
        source_id: str,
        content: str,
    ) -> List[Any]:
        """Chunk content and store in semantic memory.

        Args:
            user_id: User identifier
            source_type: Type of source (e.g., "interaction")
            source_id: Source identifier (e.g., request_id)
            content: Content to chunk and store

        Returns:
            List of created chunks
        """
        ...


@runtime_checkable
class GraphServiceProtocol(Protocol):
    """Protocol for L5 entity graph operations.

    Implementations: GraphService (memory.services.graph_service)

    Used by agents for:
    - Finding related entities (PerceptionAgent)
    """

    async def get_related_entities(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get entities related to the specified entity.

        Args:
            user_id: User identifier
            entity_type: Type of entity (e.g., "task")
            entity_id: Entity identifier
            limit: Max related entities to return

        Returns:
            List of related entity records
        """
        ...


@runtime_checkable
class DomainEventEmitterProtocol(Protocol):
    """Protocol for domain event emission (L2).

    Implementations: EventEmitter (memory.services.event_emitter)

    Used by agents for:
    - Logging domain events for audit trail (IntegrationAgent)
    """

    async def emit(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        user_id: str,
    ) -> Optional[str]:
        """Emit a domain event.

        Args:
            aggregate_type: Type of aggregate (e.g., "request")
            aggregate_id: Aggregate identifier
            event_type: Event type (e.g., "request_completed")
            payload: Event data
            user_id: User who triggered the event

        Returns:
            Event ID if emitted, None on failure
        """
        ...


# =============================================================================
# NLI PROTOCOLS (Anti-hallucination)
# =============================================================================

@runtime_checkable
class NLIResultProtocol(Protocol):
    """Protocol for NLI verification result.

    Implementations: NLIResult (memory.services.nli_service)

    Per Constitution P1: Anti-hallucination - NLI verifies claim entailment.
    """

    @property
    def label(self) -> str:
        """NLI label: 'entailment', 'neutral', or 'contradiction'."""
        ...

    @property
    def score(self) -> float:
        """Confidence score 0-1."""
        ...


@runtime_checkable
class ClaimVerificationResultProtocol(Protocol):
    """Protocol for claim verification result.

    Implementations: ClaimVerificationResult (memory.services.nli_service)

    Per Constitution P1: Anti-hallucination verification result.
    """

    @property
    def verified(self) -> bool:
        """Whether the claim was verified as supported by evidence."""
        ...

    @property
    def confidence(self) -> float:
        """Confidence score for the verification."""
        ...

    @property
    def nli_result(self) -> NLIResultProtocol:
        """The underlying NLI result."""
        ...

    @property
    def reason(self) -> str:
        """Human-readable explanation."""
        ...


@runtime_checkable
class ClaimVerifierProtocol(Protocol):
    """Protocol for domain-specific claim verification.

    This is a DOMAIN protocol for code analysis, distinct from the canonical
    NLIServiceProtocol in jeeves_commbus (which has verify(claims, evidence) -> float).

    Implementations: ClaimVerifier wrapping NLIService (memory.services.nli_service)

    Per Constitution P1 (Accuracy First): Anti-hallucination gate.
    Verifies that claims are entailed by their cited evidence.

    Used by:
    - CodeAnalysisCriticAgent for claim verification

    Centralization Audit Phase 1.6: Renamed from NLIServiceProtocol to avoid
    confusion with canonical NLIServiceProtocol in jeeves_commbus.
    """

    def verify_claim(
        self,
        claim: str,
        evidence: str,
        citation: str = "",
        threshold: float = 0.6,
    ) -> ClaimVerificationResultProtocol:
        """Verify a claim against evidence using NLI.

        Args:
            claim: The claim to verify
            evidence: The code/text evidence
            citation: File:line reference for evidence
            threshold: Minimum entailment score to verify

        Returns:
            ClaimVerificationResult with verification status
        """
        ...


# =============================================================================
# TYPE ALIASES
# =============================================================================

OptionalSessionStateService = Optional[SessionStateServiceProtocol]
OptionalChunkService = Optional[ChunkServiceProtocol]
OptionalGraphService = Optional[GraphServiceProtocol]
OptionalDomainEventEmitter = Optional[DomainEventEmitterProtocol]
OptionalClaimVerifier = Optional[ClaimVerifierProtocol]


# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Memory protocols
    "SessionStateServiceProtocol",
    "ChunkServiceProtocol",
    "GraphServiceProtocol",
    "DomainEventEmitterProtocol",
    # NLI protocols
    "NLIResultProtocol",
    "ClaimVerificationResultProtocol",
    "ClaimVerifierProtocol",
    # Type aliases
    "OptionalSessionStateService",
    "OptionalChunkService",
    "OptionalGraphService",
    "OptionalDomainEventEmitter",
    "OptionalClaimVerifier",
]

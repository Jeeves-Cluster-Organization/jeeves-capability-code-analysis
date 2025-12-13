# Flow Interrupt Unification: Comprehensive Refactoring Plan

**Date:** 2025-12-11
**Author:** Claude Code
**Status:** Proposed
**Breaking Changes:** Yes (no backward compatibility shims)

---

## Executive Summary

The codebase implements three interrupt types (clarification, confirmation, critic decision) with **completely different implementations** despite being the **same abstraction**: "pause flow, wait for external input, resume."

This document traces through all layers, identifies the fragmentation, and proposes a unified system.

---

## Part 1: Current Architecture Trace

### Layer 1: Core Engine (Go) — `coreengine/envelope/`

**Location:** `generic.go:83-93`

```go
// Current: Separate fields for each interrupt type
type GenericEnvelope struct {
    // ...
    ClarificationPending  bool    `json:"clarification_pending"`
    ClarificationQuestion *string `json:"clarification_question,omitempty"`
    ClarificationResponse *string `json:"clarification_response,omitempty"`

    ConfirmationPending  bool    `json:"confirmation_pending"`
    ConfirmationID       *string `json:"confirmation_id,omitempty"`
    ConfirmationMessage  *string `json:"confirmation_message,omitempty"`
    ConfirmationResponse *bool   `json:"confirmation_response,omitempty"`
    // ...
}
```

**Location:** `enums.go:12-33`

```go
type TerminalReason string
const (
    TerminalReasonClarificationRequired TerminalReason = "clarification_required"
    TerminalReasonConfirmationRequired  TerminalReason = "confirmation_required"
    // ... 8 other reasons
)
```

**Location:** `contracts.go:46-71`

```go
type AgentOutcome string
const (
    AgentOutcomeClarify   AgentOutcome = "clarify"
    AgentOutcomeConfirm   AgentOutcome = "confirm"
    AgentOutcomeReintent  AgentOutcome = "reintent"
    // ... 6 other outcomes
)

func (o AgentOutcome) IsTerminal() bool {
    return o == AgentOutcomeClarify || o == AgentOutcomeConfirm || ...
}
```

**Location:** `runtime/runtime.go:165-171`

```go
// Runtime breaks on these special "stages"
if env.CurrentStage == "clarification" || env.CurrentStage == "confirmation" {
    r.Logger.Info("pipeline_interrupt", ...)
    break
}
```

**Location:** `runtime/runtime.go:313-326`

```go
// Resume clears flags manually
func (r *UnifiedRuntime) Resume(ctx context.Context, env *envelope.GenericEnvelope, ...) {
    if env.ClarificationResponse != nil {
        env.ClarificationPending = false
        env.CurrentStage = "intent"  // Hardcoded stage
    }
    if env.ConfirmationResponse != nil {
        env.ConfirmationPending = false
        if *env.ConfirmationResponse {
            env.CurrentStage = "executor"  // Hardcoded stage
        } else {
            // ...
        }
    }
}
```

**Issues in Layer 1:**
- Separate boolean flags for each interrupt type
- Separate response fields with different types (`*string` vs `*bool`)
- Hardcoded resume stages ("intent", "executor")
- No unified interrupt concept

---

### Layer 2: Control Tower (Python) — `jeeves_control_tower/`

**Location:** `types.py:38-59`

```python
class InterruptType(str, Enum):
    """UNIFIED interrupt types - but not used downstream!"""
    # Software interrupts (user-driven)
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    CHECKPOINT = "checkpoint"
    # Hardware interrupts (system-driven)
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    SYSTEM_ERROR = "system_error"
```

**Location:** `types.py:145-181`

```python
@dataclass
class ProcessControlBlock:
    # Has unified interrupt handling...
    pending_interrupt: Optional[InterruptType] = None
    interrupt_data: Dict[str, Any] = field(default_factory=dict)
```

**Location:** `kernel.py:308-358`

```python
async def _handle_interrupt(self, pid, envelope, interrupt_type, interrupt_data):
    """UNIFIED handler - but then fragments into separate field updates!"""
    self._lifecycle.transition_state(pid, ProcessState.WAITING)

    # Still sets separate envelope fields
    if interrupt_type == InterruptType.CLARIFICATION:
        envelope.clarification_pending = True
        envelope.clarification_question = interrupt_data.get("question")
    elif interrupt_type == InterruptType.CONFIRMATION:
        envelope.confirmation_pending = True
        envelope.confirmation_id = interrupt_data.get("confirmation_id")
        envelope.confirmation_message = interrupt_data.get("message")
```

**Location:** `kernel.py:360-426`

```python
async def resume_request(self, pid, response_data):
    """Resume handler - also fragments"""
    if "clarification_response" in response_data:
        envelope.clarification_response = response_data["clarification_response"]
        envelope.clarification_pending = False
    if "confirmation_response" in response_data:
        envelope.confirmation_response = response_data["confirmation_response"]
        envelope.confirmation_pending = False
```

**Issues in Layer 2:**
- Has unified `InterruptType` enum - good!
- Has unified `pending_interrupt` field in PCB - good!
- But kernel still sets separate envelope fields - bad
- Storage is in-memory only (EventAggregator) - no persistence

---

### Layer 3: Memory Module (Python) — `jeeves_memory_module/`

**Location:** `services/session_state_service.py:317-490`

```python
# CLARIFICATION: Dedicated methods + table
async def save_clarification(self, session_id: str, clarification: Dict[str, Any]):
    """Uses pending_clarifications table"""
    clarification_json = json.dumps(clarification, default=str)
    await self.repository.db.insert("pending_clarifications", {
        "session_id": session_id,
        "clarification_data": clarification_json,
        "status": "pending",
        # ...
    })

async def get_clarification(self, session_id: str) -> Optional[Dict[str, Any]]:
    """SELECT FROM pending_clarifications WHERE session_id = :session_id"""

async def clear_clarification(self, session_id: str):
    """UPDATE pending_clarifications SET status = 'resolved'"""

def is_clarification_expired(self, clarification, expiry_hours=1.0):  # Hardcoded!
```

**Location:** `services/session_state_service.py:566-676`

```python
# CRITIC DECISIONS: Metadata blob + different storage
async def save_critic_decision(self, session_id: str, decision: Dict[str, Any]):
    """Stuffs into metadata.critic_decisions JSON array"""
    state = await self.repository.get(session_id)
    existing_decisions = state.metadata.get("critic_decisions", [])  # BUG: metadata doesn't exist!
    existing_decisions.append(decision)
    if len(existing_decisions) > 10:  # Hardcoded limit
        existing_decisions = existing_decisions[-10:]

    await self.repository.db.execute(
        "UPDATE session_states SET metadata = :metadata ...",
        {"metadata": json.dumps({"critic_decisions": existing_decisions})}
    )
```

**Issues in Layer 3:**
- Clarification: dedicated table + methods
- Critic decisions: stuffed into metadata JSON
- Different expiry handling (clarification has hardcoded 1hr)
- No confirmation handling at all (done elsewhere)

---

### Layer 4: Mission System (Python) — `jeeves_mission_system/`

**Location:** `common/confirmation_manager.py` (326 LOC)

```python
class ConfirmationManager:
    """Business logic for confirmations only"""
    DEFAULT_CONFIRMATION_REQUIRED_OPERATIONS = [
        "add_task", "delete_task", "task_complete", ...
    ]

    def requires_confirmation(self, execution_plan: Dict) -> bool
    def generate_confirmation_message(self, execution_plan: Dict) -> str
    async def interpret_user_response(self, ...) -> ConfirmationResponse
```

**Location:** `common/confirmation_detector.py` (~200 LOC)

```python
class ConfirmationDetector:
    """LLM-based detection - ONLY for confirmations"""
    async def detect(self, user_response: str, confirmation_message: str) -> DetectionResult
```

**Location:** `common/confirmation_interpreter.py` (~250 LOC)

```python
class ConfirmationInterpreter:
    """LLM-based interpretation - ONLY for confirmations"""
    async def interpret(self, user_response, confirmation_message, original_request)
```

**Location:** `services/confirmation_coordinator.py` (450 LOC)

```python
class ConfirmationCoordinator:
    """Workflow coordination - ONLY for confirmations"""
    async def get_pending(self, user_id, session_id) -> Optional[PendingConfirmation]:
        """SELECT FROM pending_confirmations WHERE user_id = ? AND session_id = ?"""

    async def check_needed(self, plan, request_id, user_id, session_id):
        """INSERT INTO pending_confirmations ..."""

    async def mark_status(self, confirmation_id, status, response_text)
```

**Location:** `orchestrator/confirmation.py` (250 LOC)

```python
class ConfirmationOrchestrator:
    """Unified facade - but ONLY for confirmations!"""
    def __init__(self, db, llm_provider, model, ...):
        self.detector = ConfirmationDetector(...)
        self.interpreter = ConfirmationInterpreter(...)
        self.manager = ConfirmationManager(...)
        self.coordinator = ConfirmationCoordinator(...)
```

**Issues in Layer 4:**
- 5 separate modules totaling ~1500+ LOC just for confirmations
- Clarifications handled completely differently (memory module)
- Critic decisions not handled here at all
- LLM detection/interpretation ONLY for confirmations

---

### Layer 5: Gateway (Python) — `jeeves_avionics/gateway/`

**Location:** `proto/jeeves.proto:58-74`

```proto
message FlowEvent {
  enum EventType {
    CLARIFICATION = 6;
    CONFIRMATION = 7;
    CRITIC_DECISION = 10;
  }
}
```

**Location:** `routers/chat.py:240-266`

```python
# Different response shapes for each interrupt type
if event.type == jeeves_pb2.FlowEvent.CLARIFICATION:
    final_response = {
        "status": "clarification",
        "clarification_needed": True,
        "clarification_question": payload.get("question"),
    }
elif event.type == jeeves_pb2.FlowEvent.CONFIRMATION:
    final_response = {
        "status": "confirmation",
        "confirmation_needed": True,
        "confirmation_message": payload.get("message"),
        "confirmation_id": payload.get("confirmation_id"),
    }
```

**Location:** `routers/chat.py:438-536` - Separate `/clarifications` endpoint
**Location:** `api/server.py:546-566` - Separate `/confirmations` endpoint

**Issues in Layer 5:**
- Separate proto event types (could be one with `kind` field)
- Different response field names
- Separate API endpoints for each interrupt type

---

### Layer 6: Database Schema

**Location:** `database/schemas/001_postgres_schema.sql:199-213`

```sql
-- CONFIRMATIONS: Full schema
CREATE TABLE pending_confirmations (
    confirmation_id UUID PRIMARY KEY,
    request_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    session_id UUID,
    execution_plan_json JSONB NOT NULL,
    confirmation_message TEXT,
    expires_at TIMESTAMPTZ,
    status TEXT,  -- pending, yes, no, modify, expired
    response_text TEXT,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
);
```

**Location:** `database/schemas/001_postgres_schema.sql:764-771`

```sql
-- CLARIFICATIONS: Minimal schema
CREATE TABLE pending_clarifications (
    id SERIAL PRIMARY KEY,  -- Different PK type!
    session_id UUID NOT NULL,
    clarification_data TEXT NOT NULL,  -- JSON blob, not structured
    status VARCHAR(20) DEFAULT 'pending',  -- Only pending/resolved
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

**CRITIC DECISIONS: No table - stored in `session_states.metadata` JSON**

**Issues in Layer 6:**
- Different primary key types (UUID vs SERIAL)
- Different column structures
- Different status enums
- Critic decisions have no table

---

## Part 2: The Fragmentation Summary

| Aspect | Clarification | Confirmation | Critic Decision |
|--------|---------------|--------------|-----------------|
| **Envelope fields** | 3 fields (`pending`, `question`, `response`) | 4 fields (`pending`, `id`, `message`, `response`) | None (uses `CriticFeedback[]`) |
| **Response type** | `*string` | `*bool` | N/A |
| **Database table** | `pending_clarifications` | `pending_confirmations` | None (metadata blob) |
| **Primary key** | `SERIAL` | `UUID` | N/A |
| **Service** | `session_state_service.py` | 5 dedicated modules | `session_state_service.py` |
| **LOC** | ~180 | ~1500+ | ~120 |
| **Timeout** | Hardcoded 1hr | Configurable `CONFIRMATION_TIMEOUT_SECONDS` | None |
| **LLM detection** | None | `ConfirmationDetector` | None |
| **LLM interpretation** | None | `ConfirmationInterpreter` | None |
| **Gateway endpoint** | `/clarifications` | `/confirmations` | None |
| **Proto event** | `CLARIFICATION = 6` | `CONFIRMATION = 7` | `CRITIC_DECISION = 10` |

---

## Part 3: Unified Design

### 3.1 New Envelope Structure (Go)

**File:** `coreengine/envelope/generic.go`

```go
// REMOVE these fields:
// - ClarificationPending, ClarificationQuestion, ClarificationResponse
// - ConfirmationPending, ConfirmationID, ConfirmationMessage, ConfirmationResponse

// ADD unified interrupt:
type GenericEnvelope struct {
    // ... existing fields ...

    // Unified interrupt handling
    InterruptPending bool                   `json:"interrupt_pending"`
    Interrupt        *FlowInterrupt         `json:"interrupt,omitempty"`
}

// New type
type FlowInterrupt struct {
    Kind       InterruptKind          `json:"kind"`
    ID         string                 `json:"id"`
    Question   string                 `json:"question,omitempty"`   // For clarification
    Message    string                 `json:"message,omitempty"`    // For confirmation
    Data       map[string]any         `json:"data,omitempty"`       // Extensible payload
    Response   *InterruptResponse     `json:"response,omitempty"`
    CreatedAt  time.Time              `json:"created_at"`
    ExpiresAt  *time.Time             `json:"expires_at,omitempty"`
}

type InterruptKind string
const (
    InterruptKindClarification InterruptKind = "clarification"
    InterruptKindConfirmation  InterruptKind = "confirmation"
    InterruptKindCriticReview  InterruptKind = "critic_review"
    InterruptKindCheckpoint    InterruptKind = "checkpoint"
)

type InterruptResponse struct {
    Text       *string        `json:"text,omitempty"`      // For clarification
    Approved   *bool          `json:"approved,omitempty"`  // For confirmation
    Decision   *string        `json:"decision,omitempty"`  // For critic (approve/reject/modify)
    Data       map[string]any `json:"data,omitempty"`      // Extensible
    ReceivedAt time.Time      `json:"received_at"`
}
```

### 3.2 New Envelope Methods (Go)

```go
// SetInterrupt sets a flow interrupt
func (e *GenericEnvelope) SetInterrupt(kind InterruptKind, id string, opts ...InterruptOption) {
    e.InterruptPending = true
    e.Interrupt = &FlowInterrupt{
        Kind:      kind,
        ID:        id,
        CreatedAt: time.Now().UTC(),
    }
    for _, opt := range opts {
        opt(e.Interrupt)
    }
}

// ResolveInterrupt marks interrupt as resolved with response
func (e *GenericEnvelope) ResolveInterrupt(response InterruptResponse) {
    if e.Interrupt != nil {
        e.Interrupt.Response = &response
    }
    e.InterruptPending = false
}

// Option pattern for interrupt configuration
type InterruptOption func(*FlowInterrupt)

func WithQuestion(q string) InterruptOption {
    return func(i *FlowInterrupt) { i.Question = q }
}

func WithMessage(m string) InterruptOption {
    return func(i *FlowInterrupt) { i.Message = m }
}

func WithExpiry(d time.Duration) InterruptOption {
    return func(i *FlowInterrupt) {
        t := time.Now().UTC().Add(d)
        i.ExpiresAt = &t
    }
}

func WithData(d map[string]any) InterruptOption {
    return func(i *FlowInterrupt) { i.Data = d }
}
```

### 3.3 New Runtime Behavior (Go)

**File:** `coreengine/runtime/runtime.go`

```go
// REMOVE special stage handling:
// - if env.CurrentStage == "clarification" || env.CurrentStage == "confirmation"

// REPLACE with unified check:
func (r *UnifiedRuntime) runSequential(ctx context.Context, env *GenericEnvelope, threadID string) {
    for env.CurrentStage != "end" && !env.Terminated {
        // Unified interrupt check
        if env.InterruptPending {
            r.Logger.Info("pipeline_interrupt",
                "envelope_id", env.EnvelopeID,
                "interrupt_kind", env.Interrupt.Kind,
            )
            break
        }
        // ... rest of loop
    }
}

// SIMPLIFY Resume:
func (r *UnifiedRuntime) Resume(ctx context.Context, env *GenericEnvelope, response InterruptResponse) {
    if !env.InterruptPending || env.Interrupt == nil {
        return nil, errors.New("no pending interrupt")
    }

    // Apply response
    env.ResolveInterrupt(response)

    // Determine resume stage from config (not hardcoded)
    resumeStage := r.Config.GetResumeStage(env.Interrupt.Kind)
    env.CurrentStage = resumeStage

    return r.Run(ctx, env, threadID)
}
```

### 3.4 Unified Database Schema

**File:** `database/schemas/002_unified_interrupts.sql`

```sql
-- DROP old tables (breaking change)
DROP TABLE IF EXISTS pending_confirmations;
DROP TABLE IF EXISTS pending_clarifications;

-- Single unified table
CREATE TABLE flow_interrupts (
    interrupt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Request context
    envelope_id TEXT NOT NULL,
    request_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    session_id UUID NOT NULL,

    -- Interrupt details
    kind VARCHAR(50) NOT NULL,  -- clarification, confirmation, critic_review, checkpoint
    question TEXT,              -- For clarification
    message TEXT,               -- For confirmation
    data JSONB DEFAULT '{}',    -- Extensible payload

    -- State
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, resolved, expired, cancelled

    -- Response (when resolved)
    response_text TEXT,
    response_approved BOOLEAN,
    response_decision VARCHAR(50),
    response_data JSONB,
    responded_at TIMESTAMPTZ,

    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_kind CHECK (kind IN ('clarification', 'confirmation', 'critic_review', 'checkpoint'))
);

-- Indexes
CREATE INDEX idx_flow_interrupts_session ON flow_interrupts(session_id, status);
CREATE INDEX idx_flow_interrupts_user ON flow_interrupts(user_id, status);
CREATE INDEX idx_flow_interrupts_envelope ON flow_interrupts(envelope_id);
CREATE INDEX idx_flow_interrupts_expires ON flow_interrupts(expires_at) WHERE status = 'pending';
CREATE INDEX idx_flow_interrupts_kind ON flow_interrupts(kind, status);

-- Auto-update timestamp
CREATE TRIGGER update_flow_interrupts_updated_at
    BEFORE UPDATE ON flow_interrupts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE flow_interrupts IS 'Unified storage for all flow interrupts (clarification, confirmation, etc.)';
```

### 3.5 Unified Python Service

**File:** `jeeves_control_tower/services/interrupt_service.py` (NEW)

```python
"""Unified Flow Interrupt Service.

Replaces:
- jeeves_memory_module/services/session_state_service.py (clarification methods)
- jeeves_mission_system/services/confirmation_coordinator.py
- jeeves_mission_system/common/confirmation_manager.py
- jeeves_mission_system/common/confirmation_detector.py
- jeeves_mission_system/common/confirmation_interpreter.py
- jeeves_mission_system/orchestrator/confirmation.py

Single service for all interrupt types with configurable behavior.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Protocol
from uuid import uuid4

from jeeves_control_tower.types import InterruptType


class InterruptKind(str, Enum):
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    CRITIC_REVIEW = "critic_review"
    CHECKPOINT = "checkpoint"


@dataclass
class FlowInterrupt:
    """Unified interrupt representation."""
    interrupt_id: str
    envelope_id: str
    request_id: str
    user_id: str
    session_id: str
    kind: InterruptKind
    question: Optional[str] = None
    message: Optional[str] = None
    data: Dict[str, Any] = None
    status: str = "pending"
    response_text: Optional[str] = None
    response_approved: Optional[bool] = None
    response_decision: Optional[str] = None
    response_data: Dict[str, Any] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.response_data is None:
            self.response_data = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class InterruptConfig:
    """Configuration for interrupt behavior."""
    timeout_seconds: int = 300
    require_llm_detection: bool = False
    require_llm_interpretation: bool = False
    required_operations: list = None  # For confirmation: which ops need it


class InterruptService:
    """Unified service for all flow interrupts.

    Usage:
        config = {
            InterruptKind.CLARIFICATION: InterruptConfig(timeout_seconds=3600),
            InterruptKind.CONFIRMATION: InterruptConfig(
                timeout_seconds=300,
                require_llm_detection=True,
                require_llm_interpretation=True,
                required_operations=["add_task", "delete_task"],
            ),
            InterruptKind.CRITIC_REVIEW: InterruptConfig(timeout_seconds=0),  # No expiry
        }
        service = InterruptService(db, config)

        # Create interrupt
        interrupt = await service.create(
            kind=InterruptKind.CLARIFICATION,
            envelope_id="env_123",
            question="What do you mean by 'the function'?",
        )

        # Get pending
        pending = await service.get_pending(session_id="sess_123")

        # Resolve
        await service.resolve(interrupt.interrupt_id, response_text="I mean the main() function")
    """

    def __init__(
        self,
        db,  # DatabaseClient
        config: Dict[InterruptKind, InterruptConfig] = None,
        llm_provider = None,  # Optional for detection/interpretation
        logger = None,
    ):
        self.db = db
        self.config = config or self._default_config()
        self.llm_provider = llm_provider
        self._logger = logger

    def _default_config(self) -> Dict[InterruptKind, InterruptConfig]:
        return {
            InterruptKind.CLARIFICATION: InterruptConfig(timeout_seconds=3600),
            InterruptKind.CONFIRMATION: InterruptConfig(timeout_seconds=300),
            InterruptKind.CRITIC_REVIEW: InterruptConfig(timeout_seconds=0),
            InterruptKind.CHECKPOINT: InterruptConfig(timeout_seconds=0),
        }

    async def create(
        self,
        kind: InterruptKind,
        envelope_id: str,
        request_id: str,
        user_id: str,
        session_id: str,
        question: str = None,
        message: str = None,
        data: Dict[str, Any] = None,
    ) -> FlowInterrupt:
        """Create a new interrupt."""
        cfg = self.config.get(kind, InterruptConfig())

        expires_at = None
        if cfg.timeout_seconds > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=cfg.timeout_seconds)

        interrupt = FlowInterrupt(
            interrupt_id=str(uuid4()),
            envelope_id=envelope_id,
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            kind=kind,
            question=question,
            message=message,
            data=data or {},
            expires_at=expires_at,
        )

        await self.db.insert("flow_interrupts", {
            "interrupt_id": interrupt.interrupt_id,
            "envelope_id": interrupt.envelope_id,
            "request_id": interrupt.request_id,
            "user_id": interrupt.user_id,
            "session_id": interrupt.session_id,
            "kind": interrupt.kind.value,
            "question": interrupt.question,
            "message": interrupt.message,
            "data": interrupt.data,
            "status": "pending",
            "expires_at": interrupt.expires_at,
        })

        return interrupt

    async def get_pending(
        self,
        session_id: str,
        kind: InterruptKind = None,
    ) -> Optional[FlowInterrupt]:
        """Get pending interrupt for session."""
        query = """
            SELECT * FROM flow_interrupts
            WHERE session_id = :session_id
              AND status = 'pending'
        """
        params = {"session_id": session_id}

        if kind:
            query += " AND kind = :kind"
            params["kind"] = kind.value

        query += " ORDER BY created_at DESC LIMIT 1"

        row = await self.db.fetch_one(query, params)
        if not row:
            return None

        interrupt = self._row_to_interrupt(row)

        # Check expiry
        if interrupt.is_expired():
            await self.expire(interrupt.interrupt_id)
            return None

        return interrupt

    async def resolve(
        self,
        interrupt_id: str,
        response_text: str = None,
        response_approved: bool = None,
        response_decision: str = None,
        response_data: Dict[str, Any] = None,
    ) -> bool:
        """Resolve an interrupt with response."""
        await self.db.execute(
            """
            UPDATE flow_interrupts
            SET status = 'resolved',
                response_text = :response_text,
                response_approved = :response_approved,
                response_decision = :response_decision,
                response_data = :response_data,
                responded_at = :responded_at
            WHERE interrupt_id = :interrupt_id
            """,
            {
                "interrupt_id": interrupt_id,
                "response_text": response_text,
                "response_approved": response_approved,
                "response_decision": response_decision,
                "response_data": response_data or {},
                "responded_at": datetime.now(timezone.utc),
            }
        )
        return True

    async def expire(self, interrupt_id: str) -> bool:
        """Mark interrupt as expired."""
        await self.db.execute(
            "UPDATE flow_interrupts SET status = 'expired' WHERE interrupt_id = :id",
            {"id": interrupt_id}
        )
        return True

    async def cancel(self, interrupt_id: str) -> bool:
        """Cancel an interrupt."""
        await self.db.execute(
            "UPDATE flow_interrupts SET status = 'cancelled' WHERE interrupt_id = :id",
            {"id": interrupt_id}
        )
        return True

    def _row_to_interrupt(self, row: dict) -> FlowInterrupt:
        """Convert DB row to FlowInterrupt."""
        return FlowInterrupt(
            interrupt_id=str(row["interrupt_id"]),
            envelope_id=row["envelope_id"],
            request_id=str(row["request_id"]),
            user_id=row["user_id"],
            session_id=str(row["session_id"]),
            kind=InterruptKind(row["kind"]),
            question=row.get("question"),
            message=row.get("message"),
            data=row.get("data", {}),
            status=row["status"],
            response_text=row.get("response_text"),
            response_approved=row.get("response_approved"),
            response_decision=row.get("response_decision"),
            response_data=row.get("response_data", {}),
            created_at=row["created_at"],
            expires_at=row.get("expires_at"),
            responded_at=row.get("responded_at"),
        )

    # === Optional LLM-based detection (for confirmations) ===

    async def detect_response(
        self,
        kind: InterruptKind,
        user_message: str,
        interrupt_context: str,
    ) -> bool:
        """Detect if user message is responding to an interrupt.

        Only used when config.require_llm_detection is True.
        """
        cfg = self.config.get(kind, InterruptConfig())
        if not cfg.require_llm_detection or not self.llm_provider:
            return True  # Assume it's a response

        # Use LLM to detect
        # (Simplified - actual implementation would use prompt template)
        return True

    async def interpret_response(
        self,
        kind: InterruptKind,
        user_message: str,
        interrupt_context: str,
    ) -> Dict[str, Any]:
        """Interpret user response using LLM.

        Only used when config.require_llm_interpretation is True.
        """
        cfg = self.config.get(kind, InterruptConfig())
        if not cfg.require_llm_interpretation or not self.llm_provider:
            # Default interpretation based on kind
            if kind == InterruptKind.CONFIRMATION:
                lower = user_message.lower().strip()
                approved = lower in ("yes", "y", "ok", "confirm", "proceed")
                return {"approved": approved, "text": user_message}
            return {"text": user_message}

        # Use LLM to interpret
        # (Simplified - actual implementation would use prompt template)
        return {"text": user_message}
```

### 3.6 Unified Proto Definition

**File:** `proto/jeeves.proto`

```proto
// REMOVE:
// - CLARIFICATION = 6
// - CONFIRMATION = 7
// - CRITIC_DECISION = 10

// ADD unified interrupt event:
message FlowEvent {
  enum EventType {
    // ... existing types ...
    INTERRUPT = 15;          // Unified interrupt event
    INTERRUPT_RESOLVED = 16; // Interrupt was resolved
  }
}

// New message for interrupt details
message FlowInterrupt {
  string interrupt_id = 1;
  string kind = 2;           // clarification, confirmation, critic_review
  string question = 3;       // For clarification
  string message = 4;        // For confirmation
  string status = 5;         // pending, resolved, expired
  int64 expires_at_ms = 6;
  bytes data = 7;            // JSON payload
}
```

### 3.7 Unified Gateway Endpoint

**File:** `jeeves_avionics/gateway/routers/interrupts.py` (NEW)

```python
"""Unified interrupts router.

Replaces:
- /clarifications endpoint
- /confirmations endpoint

Single endpoint for all interrupt types.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any, Dict

router = APIRouter(prefix="/interrupts", tags=["interrupts"])


class InterruptResponse(BaseModel):
    """Response to an interrupt."""
    interrupt_id: str
    text: Optional[str] = None          # For clarification
    approved: Optional[bool] = None      # For confirmation
    decision: Optional[str] = None       # For critic_review
    data: Optional[Dict[str, Any]] = None


class InterruptResult(BaseModel):
    """Result after resolving interrupt."""
    interrupt_id: str
    status: str
    request_id: str
    session_id: str
    response: Optional[str] = None


@router.post("/{interrupt_id}/respond", response_model=InterruptResult)
async def respond_to_interrupt(
    interrupt_id: str,
    body: InterruptResponse,
    user_id: str = Query(...),
):
    """Respond to any interrupt type.

    The interrupt_id determines the type. Response fields used depend on type:
    - clarification: uses `text`
    - confirmation: uses `approved`
    - critic_review: uses `decision`
    """
    # Get interrupt from service
    # Validate user owns this interrupt
    # Resolve interrupt
    # Resume flow
    pass


@router.get("/pending", response_model=Optional[dict])
async def get_pending_interrupt(
    user_id: str = Query(...),
    session_id: str = Query(...),
    kind: Optional[str] = Query(None),
):
    """Get pending interrupt for session."""
    pass
```

### 3.8 Configuration

**File:** `jeeves_avionics/config/interrupts.yaml` (NEW)

```yaml
# Interrupt configuration - replaces scattered hardcoded values

interrupts:
  clarification:
    timeout_seconds: 3600  # 1 hour
    llm_detection: false
    llm_interpretation: false
    resume_stage: "intent"

  confirmation:
    timeout_seconds: 300   # 5 minutes
    llm_detection: true
    llm_interpretation: true
    resume_stage: "executor"
    required_operations:
      - add_task
      - delete_task
      - task_complete
      - update_task
      - journal_ingest
      - delete_journal_entry

  critic_review:
    timeout_seconds: 0     # No expiry
    llm_detection: false
    llm_interpretation: false
    resume_stage: "intent"  # For reintent
    max_history: 10

  checkpoint:
    timeout_seconds: 0
    resume_stage: null     # Explicit resume required
```

---

## Part 4: Migration Plan

### Phase 1: Create New Infrastructure (Non-Breaking)

1. Add `FlowInterrupt` type to Go envelope (alongside old fields)
2. Create `flow_interrupts` table
3. Create `InterruptService` in control_tower
4. Add `/interrupts` gateway router

### Phase 2: Dual-Write

1. Write to both old and new systems
2. Read from new system, fallback to old
3. Validate consistency

### Phase 3: Cut Over (Breaking)

1. Remove old envelope fields from Go
2. Drop `pending_confirmations` and `pending_clarifications` tables
3. Remove 5+ confirmation modules
4. Remove clarification methods from session_state_service
5. Update all consumers to use new unified API

### Phase 4: Cleanup

1. Remove backward compatibility code
2. Update documentation
3. Update tests

---

## Part 5: Files to Delete

```
# Confirmation modules (~1500 LOC)
jeeves_mission_system/common/confirmation_manager.py
jeeves_mission_system/common/confirmation_detector.py
jeeves_mission_system/common/confirmation_interpreter.py
jeeves_mission_system/services/confirmation_coordinator.py
jeeves_mission_system/orchestrator/confirmation.py

# Clarification methods in session_state_service.py (~180 LOC)
# - save_clarification()
# - get_clarification()
# - clear_clarification()
# - is_clarification_expired()

# Critic decision methods in session_state_service.py (~120 LOC)
# - save_critic_decision()
# - get_critic_decisions()

# Gateway endpoints
jeeves_avionics/gateway/routers/chat.py (clarification handling)
jeeves_mission_system/api/server.py (/confirmations endpoint)
```

---

## Part 6: Estimated Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total interrupt-related LOC | ~2000 | ~400 | -80% |
| Database tables | 2 + metadata blob | 1 | -66% |
| Service classes | 7+ | 1 | -86% |
| Gateway endpoints | 2 | 1 | -50% |
| Proto event types | 3 | 1 | -66% |
| Configuration locations | 5+ scattered | 1 YAML file | -80% |

---

## Part 7: Benefits

1. **Single mental model**: All interrupts work the same way
2. **Easy to add new types**: Just add to enum + config
3. **Consistent storage**: One table, one schema
4. **Configurable**: YAML config instead of hardcoded values
5. **Testable**: One service to test instead of 7+
6. **Maintainable**: Changes in one place affect all interrupt types

---

## Part 8: Integration with New Infrastructure

*Added after merging main branch (2025-12-11)*

The following new modules were added to the codebase and should integrate with the unified interrupt system:

### 8.1 Webhook Service Integration

**Location:** `jeeves_avionics/webhooks/service.py`

The webhook service supports event pattern subscriptions (e.g., `request.*`). Interrupt events should be emitted through this system:

```python
# Interrupt event types to support
INTERRUPT_EVENTS = [
    "interrupt.created",      # When any interrupt is created
    "interrupt.resolved",     # When interrupt is resolved
    "interrupt.expired",      # When interrupt expires
    "interrupt.cancelled",    # When interrupt is cancelled
]

# Usage in InterruptService
async def create(self, kind: InterruptKind, ...):
    interrupt = FlowInterrupt(...)
    await self.db.insert(...)

    # Emit webhook event
    if self.webhook_service:
        await self.webhook_service.emit_event(
            event_type=f"interrupt.created",
            data={
                "interrupt_id": interrupt.interrupt_id,
                "kind": interrupt.kind.value,
                "session_id": interrupt.session_id,
                "question": interrupt.question,
                "message": interrupt.message,
            },
            request_id=interrupt.request_id,
        )

    return interrupt
```

**Webhook subscribers can use patterns:**
- `interrupt.*` - All interrupt events
- `interrupt.created` - Only creation events
- `interrupt.resolved` - Only resolution events

### 8.2 Rate Limiter Integration

**Location:** `jeeves_control_tower/resources/rate_limiter.py`

When rate limits are exceeded, the rate limiter should trigger a `RESOURCE_EXHAUSTED` interrupt instead of throwing an exception directly:

```python
# Current behavior (throws exception):
if result.exceeded:
    raise RateLimitExceeded(result.reason)

# Unified behavior (creates interrupt):
if result.exceeded:
    await interrupt_service.create(
        kind=InterruptKind.RESOURCE_EXHAUSTED,  # Add to enum
        envelope_id=envelope_id,
        request_id=request_id,
        user_id=user_id,
        session_id=session_id,
        message=f"Rate limit exceeded: {result.reason}",
        data={
            "limit_type": result.limit_type,
            "current_count": result.current_count,
            "limit": result.limit,
            "retry_after_seconds": result.retry_after_seconds,
        },
    )
```

**Configuration addition to `interrupts.yaml`:**

```yaml
interrupts:
  # ... existing types ...

  resource_exhausted:
    timeout_seconds: 0       # No auto-expiry
    resume_stage: null       # Cannot resume, must retry
    notify_webhook: true     # Trigger webhook notification
    rate_limit_source: true  # Marks this as rate-limit triggered
```

### 8.3 Observability Integration

**Location:** `jeeves_avionics/observability/otel_adapter.py`

Interrupt lifecycle should be traced:

```python
# Trace interrupt creation
with tracer.start_span("interrupt.create") as span:
    span.set_attribute("interrupt.kind", kind.value)
    span.set_attribute("interrupt.id", interrupt_id)
    span.set_attribute("session.id", session_id)

# Trace interrupt resolution
with tracer.start_span("interrupt.resolve") as span:
    span.set_attribute("interrupt.id", interrupt_id)
    span.set_attribute("interrupt.resolution_time_ms", resolution_time)
```

**Metrics to add:**
- `interrupt_created_total{kind}` - Counter of interrupts by kind
- `interrupt_resolved_total{kind}` - Counter of resolutions by kind
- `interrupt_expired_total{kind}` - Counter of expirations by kind
- `interrupt_resolution_duration_seconds{kind}` - Histogram of time to resolution

### 8.4 Updated InterruptKind Enum

With the new infrastructure, extend the interrupt kinds:

```python
class InterruptKind(str, Enum):
    # User-driven (existing)
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    CRITIC_REVIEW = "critic_review"
    CHECKPOINT = "checkpoint"

    # System-driven (from new infrastructure)
    RESOURCE_EXHAUSTED = "resource_exhausted"  # From rate limiter
    TIMEOUT = "timeout"                         # From control tower
    SYSTEM_ERROR = "system_error"               # From error handling
```

---

## Appendix: Control Tower Already Has This Right

The `jeeves_control_tower/types.py` already defines `InterruptType` enum with all interrupt kinds. The kernel already has `_handle_interrupt()` that takes an `InterruptType`.

The problem is the kernel then **fragments into separate envelope fields** and **doesn't persist**.

This refactoring completes the vision that control tower started.

---

## Appendix B: New Infrastructure Files (Main Branch Merge)

The following files were added to main and are relevant to this plan:

| File | Purpose | Interrupt Integration |
|------|---------|----------------------|
| `jeeves_avionics/webhooks/service.py` | Webhook event delivery | Emit interrupt lifecycle events |
| `jeeves_avionics/webhooks/__init__.py` | Package exports | - |
| `jeeves_control_tower/resources/rate_limiter.py` | Rate limiting | Trigger RESOURCE_EXHAUSTED interrupt |
| `jeeves_avionics/observability/otel_adapter.py` | OpenTelemetry tracing | Trace interrupt lifecycle |
| `jeeves_avionics/observability/tracing_middleware.py` | Request tracing | - |
| `jeeves_avionics/middleware/rate_limit.py` | HTTP rate limiting | Works with rate_limiter.py |
| `jeeves_control_tower/types.py` | Added `RateLimitConfig` | Used by rate limiter |

None of these files currently use the interrupt system, but all should integrate with the unified `InterruptService` once implemented.

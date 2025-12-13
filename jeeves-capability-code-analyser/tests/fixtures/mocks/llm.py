"""Mock LLM provider for testing.

Provides canned responses for agent testing without requiring
a real LLM server.
"""

from typing import Any, Dict, List, Optional
import json


class MockLLMProvider:
    """Mock LLM provider for testing agents.

    Supports configurable responses based on prompt content.
    Tracks all calls for assertion in tests.
    """

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """Initialize mock provider.

        Args:
            responses: Dict mapping prompt substrings to responses.
                       If a prompt contains the key, return the value.
        """
        self.responses = responses or {}
        self.call_count = 0
        self.calls: List[Dict[str, Any]] = []
        self._default_responses = self._get_default_responses()

    def _get_default_responses(self) -> Dict[str, Any]:
        """Get default responses for common agent prompts."""
        return {
            "intent": json.dumps({
                "intent": "code_analysis",
                "goals": ["Understand the code structure"],
                "constraints": [],
                "ambiguities": [],
                "clarification_needed": False,
                "confidence": 0.9
            }),
            "plan": json.dumps({
                "plan_id": "mock-plan-001",
                "steps": [
                    {
                        "step_id": "step-1",
                        "tool": "glob_files",
                        "parameters": {"pattern": "**/*.py"},
                        "reasoning": "Find Python files",
                        "proposed_risk": "read_only"
                    }
                ],
                "rationale": "Search for relevant files",
                "feasibility_score": 90
            }),
            "synthesizer": json.dumps({
                "entities": [],
                "key_flows": [],
                "open_questions": [],
                "contradictions": [],
                "hints_for_goals": {},
                "accumulated_evidence": [],
                "summary": "Mock synthesis complete."
            }),
            "critic": json.dumps({
                "verdict": "APPROVED",
                "intent_alignment_score": 0.95,
                "validated_claims": [],
                "issues": [],
                "goal_status": {},
                "satisfied_goals": [],
                "remaining_goals": [],
                "blocking_issues": []
            }),
        }

    async def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Generate a response for the given prompt.

        Returns configured response if prompt matches, otherwise default.
        """
        self.call_count += 1
        self.calls.append({
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        # Check custom responses first
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response

        # Check default responses
        for key, response in self._default_responses.items():
            if key.lower() in prompt.lower():
                return response

        # Fallback response
        return '{"result": "mock response", "status": "success"}'

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        *,
        model: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate structured output matching schema."""
        self.call_count += 1
        self.calls.append({
            "prompt": prompt,
            "schema": schema,
            "model": model,
        })

        # Return parsed JSON from generate
        response = await self.generate(prompt, model=model, seed=seed)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"result": response}

    async def health_check(self) -> bool:
        """Always return healthy for tests."""
        return True

    def reset(self):
        """Reset call tracking."""
        self.call_count = 0
        self.calls = []

    def set_response(self, key: str, response: str):
        """Set a custom response for prompts containing key."""
        self.responses[key] = response

"""
Code Analysis prompts - registered versions for the 7-agent code analysis pipeline.

These prompts are designed for read-only codebase exploration and understanding.
They follow the Constitutional principles:
- P1 (Accuracy First): Never hallucinate code
- P2 (Code Context Priority): Understand code in context before claims
- Amendment XI (Context Bounds): Respect token limits

Pipeline: Perception -> Intent -> Planner -> Traverser (no prompt) -> Synthesizer -> Critic -> Integration

Constitutional Compliance:
- Prompts are inline in code (not external files) per Forbidden Patterns
- P5: Deterministic Spine (prompts are contracts at LLM boundary)
- P6: Observable (prompts in version control, reviewable)

IMPORTANT: Prompts use {placeholder} syntax for context injection.
Context builder functions provide the values via str.format().
"""

from jeeves_mission_system.prompts.core.registry import register_prompt


# --- PERCEPTION PROMPTS (Agent 1) - Context Loading ---

def code_analysis_perception() -> str:
    """Code analysis perception prompt - context loading and query normalization.

    Expected placeholders:
        - system_identity: Core identity block
        - role_description: Perception role explanation
        - user_query: Raw user input
        - session_state: Formatted session state
    """
    return """{system_identity}

**Your Role:** Perception Agent - Load context and normalize code analysis queries.

{role_description}

**User Query:** {user_query}

**Session State:**
{session_state}

**Your Task:**
1. Normalize the user query (fix typos, expand abbreviations)
2. Extract any scope information (files, directories, patterns)
3. Identify the query type (exploration, explanation, search, trace)

Output JSON only:
{{"normalized_query": "...", "scope": "...", "query_type": "..."}}"""


# --- INTENT PROMPTS (Agent 2) - Query Classification ---

def code_analysis_intent() -> str:
    """Code analysis intent classification prompt.

    Expected placeholders:
        - system_identity: Core identity block
        - role_description: Intent role explanation
        - normalized_input: Cleaned query from perception
        - context_summary: Session context summary
        - detected_languages: List of detected languages
        - capabilities_summary: What the system can do
    """
    return """{system_identity}

**Your Role:** Intent Agent - Classify code analysis intent.

{role_description}

**Query:** {normalized_input}

**Context:** {context_summary}

**Detected Languages:** {detected_languages}

**Available Capabilities:** {capabilities_summary}

**Your Task:**
Classify the intent and extract goals.

Common intents:
- explore: Understand structure/architecture
- explain: Understand how code works
- search: Find specific code/patterns
- trace: Follow execution flow

Output JSON only:
{{"intent": "...", "goals": [...], "confidence": 0.9}}"""


# --- PLANNER PROMPTS (Agent 3) - Traversal Planning ---

def code_analysis_planner() -> str:
    """Code analysis plan generation prompt.

    Expected placeholders:
        - system_identity: Core identity block
        - role_description: Planner role explanation
        - intent: Classified intent type
        - goals: List of goals to achieve
        - scope_path: Target directory/file scope
        - exploration_summary: Prior exploration info
        - available_tools: Dynamic tool descriptions from registry
        - bounds_description: Context bounds explanation
        - max_files, max_tokens: Numeric limits
        - tokens_used, files_explored: Current usage
        - remaining_tokens, remaining_files: Remaining budget
        - retry_feedback: Optional feedback from previous attempt
    """
    return """{system_identity}

**Your Role:** Planner Agent - Create code traversal plan.

{role_description}

**Intent:** {intent}
**Goals:** {goals}
**Scope:** {scope_path}

**Exploration Summary:** {exploration_summary}

**Available Tools:**
{available_tools}

**Context Bounds:**
{bounds_description}
- Max files: {max_files} (used: {files_explored}, remaining: {remaining_files})
- Max tokens: {max_tokens} (used: {tokens_used}, remaining: {remaining_tokens})

{retry_feedback}

**Your Task:**
Create an execution plan using available tools to gather information.

CRITICAL RULES:
1. You are a PLANNER, not a coder. DO NOT write code. DO NOT explain code.
2. ONLY output a JSON object with tool calls
3. Use read-only tools only
4. Respect context bounds
5. Start broad, then narrow

RESPOND WITH ONLY THIS JSON FORMAT (no other text):
```json
{{"steps": [{{"tool": "tool_name", "parameters": {{"param": "value"}}, "reasoning": "why this step"}}], "rationale": "overall strategy"}}
```

WRONG (do NOT do this):
- Writing Python code
- Explaining what code does
- Describing protocols or classes

RIGHT:
- JSON with tool calls to FIND and READ the code"""


# --- SYNTHESIZER PROMPTS (Agent 5 - after Traverser) - Structured Understanding ---

def code_analysis_synthesizer() -> str:
    """Code analysis synthesizer prompt - build structured understanding.

    Expected placeholders:
        - system_identity: Core identity block
        - role_description: Synthesizer role explanation
        - user_query: Original user query
        - intent: Classified intent type
        - goals: List of goals
        - execution_results: Tool execution results
        - relevant_snippets: Code snippets collected
    """
    return """{system_identity}

**Your Role:** Synthesizer Agent - Build structured understanding.

{role_description}

**User Query:** {user_query}
**Intent:** {intent}
**Goals:** {goals}

**Execution Results:**
{execution_results}

**Code Snippets:**
{relevant_snippets}

**Your Task:**
Synthesize findings into structured understanding.

Rules:
1. Every claim must cite source (file:line)
2. No hallucination - only what tools found
3. Organize by architectural concepts
4. Flag missing information

Output JSON only:
{{"findings": [...], "citations": [...], "gaps": [...]}}"""


# --- CRITIC PROMPTS (Agent 6 - after Synthesizer) - Anti-Hallucination ---

def code_analysis_critic() -> str:
    """Code analysis critic validation prompt.

    Expected placeholders:
        - system_identity: Core identity block
        - role_description: Critic role explanation
        - user_query: Original user query
        - intent: Classified intent type
        - goals: List of goals to verify
        - execution_results: Tool execution results
        - relevant_snippets: Code snippets collected
    """
    return """{system_identity}

**Your Role:** Critic Agent - Validate against hallucination.

{role_description}

**User Query:** {user_query}
**Intent:** {intent}
**Goals:** {goals}

**Execution Results:**
{execution_results}

**Code Snippets:**
{relevant_snippets}

**Your Task:**
Validate all claims against actual code.

Hallucination checks:
1. Every claim has file:line citation?
2. Citations match actual code?
3. No invented details?
4. Goals satisfied?

Output JSON only:
{{"verdict": "approved|replan|clarify", "issues": [...], "suggested_response": "..."}}"""


# --- INTEGRATION PROMPTS (Agent 7) - Response Building ---

def code_analysis_integration() -> str:
    """Code analysis integration/response building prompt.

    Expected placeholders:
        - system_identity: Core identity block
        - role_description: Integration role explanation
        - user_query: Original user query
        - verdict: Critic's verdict
        - suggested_response: Critic's suggested response
        - relevant_snippets: Code snippets collected
        - exploration_summary: What was explored
        - files_examined: List of examined files
        - pipeline_overview: Pipeline structure description
    """
    return """{system_identity}

**Your Role:** Integration Agent - Build final response.

{role_description}

**User Query:** {user_query}

**Critic Verdict:** {verdict}
**Suggested Response:** {suggested_response}

**Code Snippets:**
{relevant_snippets}

**Exploration Summary:** {exploration_summary}
**Files Examined:** {files_examined}

**Pipeline Overview:** {pipeline_overview}

**Your Task:**
Build final response with citations.

Rules:
1. Use file:line format for all citations
2. No claims without citations
3. Be concise and clear
4. Acknowledge limitations

Output the final response text (not JSON)."""


def register_code_analysis_prompts() -> None:
    """Register all code analysis prompts with the PromptRegistry.

    This function should be called during capability registration
    to make prompts available to the pipeline.
    """
    # Use the decorator to register each prompt
    register_prompt(
        name="code_analysis.perception",
        version="2.0",
        description="Normalize user query and load session context for code analysis",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_perception)

    register_prompt(
        name="code_analysis.intent",
        version="2.0",
        description="Classify code analysis query intent and extract goals",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_intent)

    register_prompt(
        name="code_analysis.planner",
        version="2.0",
        description="Generate code traversal plan with tool calls",
        constitutional_compliance="P2 (Code Context Priority), Amendment XI (Context Bounds)"
    )(code_analysis_planner)

    register_prompt(
        name="code_analysis.synthesizer",
        version="1.0",
        description="Synthesize execution results into structured understanding",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_synthesizer)

    register_prompt(
        name="code_analysis.critic",
        version="2.0",
        description="Validate code analysis results against actual code - anti-hallucination gate",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_critic)

    register_prompt(
        name="code_analysis.integration",
        version="2.0",
        description="Build final response with code citations",
        constitutional_compliance="P1 (Accuracy First), P2 (Code Context Priority)"
    )(code_analysis_integration)

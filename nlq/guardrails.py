"""
Guardrails — Response Quality & Safety
=========================================
Validates every answer before it reaches the user.
"""

import re
from dataclasses import dataclass, field


@dataclass
class GuardrailResult:
    passed: bool
    confidence: float
    sources: list[str] = field(default_factory=list)
    fallback_message: str = ""


OUT_OF_SCOPE = [
    "stock", "crypto", "weather", "sports", "election", "political",
    "medical advice", "legal advice", "predict", "forecast",
]

UNCERTAINTY_PHRASES = [
    "i think", "i believe", "probably", "i'm not sure", "i cannot confirm",
    "i don't know", "i'm unable", "i cannot",
]


def apply_guardrails(question: str, answer: str, tool_calls: list) -> GuardrailResult:
    q_lower = question.lower()
    a_lower = answer.lower()

    # Out of scope question
    if any(t in q_lower for t in OUT_OF_SCOPE):
        return GuardrailResult(
            passed=True,   # still pass — the LLM should handle this gracefully
            confidence=0.6,
            sources=[],
        )

    # No tools called — LLM answered from training data (risky for factual claims)
    if not tool_calls:
        uncertainty_count = sum(1 for p in UNCERTAINTY_PHRASES if p in a_lower)
        if uncertainty_count >= 2:
            return GuardrailResult(
                passed=False,
                confidence=0.3,
                fallback_message=(
                    "I wasn't able to retrieve Census data to answer that confidently. "
                    "Try rephrasing as a question about a specific state or metric, "
                    "e.g. 'What is the population of Texas?' or 'Compare income in California and New York'."
                ),
            )
        return GuardrailResult(passed=True, confidence=0.65, sources=[])

    # Extract sources from tool results
    sources = []
    for tc in tool_calls:
        result = tc.get("result", {})
        if isinstance(result, dict):
            src = result.get("source", "")
            if src and src not in sources:
                sources.append(src)
            geo = result.get("geography", "")
            if geo:
                sources.append(f"Geography: {geo}")

    # Tool was called but returned an error
    errors = [tc for tc in tool_calls if "error" in tc.get("result", {})]
    if errors and len(errors) == len(tool_calls):
        return GuardrailResult(
            passed=False,
            confidence=0.2,
            fallback_message=(
                "I encountered an error retrieving Census data. "
                f"Error: {errors[0]['result'].get('error', 'Unknown error')}. "
                "Try asking about a specific US state, e.g. 'population of Ohio'."
            ),
        )

    return GuardrailResult(
        passed=True,
        confidence=0.92,
        sources=list(set(s for s in sources if s)),
    )

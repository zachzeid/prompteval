"""LLM-powered analysis using Claude API."""

import json
import os
from typing import Any

import anthropic

from backend.models.schemas import HeuristicAnalysis, LLMAnalysis, Prompt, PromptType

# Initialize client (uses ANTHROPIC_API_KEY env var)
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Get or create the Anthropic client."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


ANALYSIS_SYSTEM_PROMPT = """You are an expert prompt engineer analyzing prompts for effectiveness.
Your task is to provide detailed, actionable analysis of prompts.

Analyze the prompt for:
1. Ambiguities - phrases or instructions that could be misinterpreted
2. Missing context - information gaps that could affect output quality
3. Prompt injection risks - potential security vulnerabilities (for system prompts)
4. Best practice issues - deviations from prompt engineering best practices

Respond in JSON format:
{
  "ambiguities": ["list of ambiguous phrases or instructions"],
  "missing_context": ["list of missing information or context"],
  "injection_risks": ["list of potential injection vulnerabilities"],
  "best_practice_issues": ["list of best practice violations"],
  "suggested_revision": "improved version of the prompt",
  "revision_explanation": "explanation of why changes were made"
}"""


SUGGESTION_SYSTEM_PROMPT = """You are an expert prompt engineer helping to improve prompts.
Your task is to suggest specific improvements to make the prompt more effective.

Consider:
- Clarity and readability
- Specificity and concreteness
- Structure and organization
- Completeness of context
- Output format specification
- Safety guardrails (for system prompts)

Respond in JSON format:
{
  "suggested": "the improved prompt text",
  "explanation": "overall explanation of improvements",
  "changes": [
    {
      "original": "original text snippet",
      "replacement": "improved text",
      "reason": "why this change was made"
    }
  ]
}"""


async def analyze_with_llm(prompt: Prompt) -> LLMAnalysis:
    """Analyze a prompt using Claude.

    Args:
        prompt: The prompt to analyze.

    Returns:
        LLMAnalysis with detected issues and suggestions.
    """
    client = get_client()

    prompt_type = "system prompt" if prompt.type == PromptType.SYSTEM else "user prompt"

    user_message = f"""Analyze this {prompt_type}:

---
{prompt.content}
---

Provide your analysis in the specified JSON format."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse the response
        response_text = response.content[0].text

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        data = json.loads(json_str)

        return LLMAnalysis(
            prompt_id=prompt.id,
            ambiguities=data.get("ambiguities", []),
            missing_context=data.get("missing_context", []),
            injection_risks=data.get("injection_risks", []),
            best_practice_issues=data.get("best_practice_issues", []),
            suggested_revision=data.get("suggested_revision"),
            revision_explanation=data.get("revision_explanation"),
        )

    except json.JSONDecodeError as e:
        return LLMAnalysis(
            prompt_id=prompt.id,
            error=f"Failed to parse LLM response: {e}",
        )
    except anthropic.APIError as e:
        return LLMAnalysis(
            prompt_id=prompt.id,
            error=f"API error: {e}",
        )


async def generate_suggestions(
    prompt: Prompt,
    heuristic: HeuristicAnalysis | None = None,
    focus_areas: list[str] | None = None,
) -> dict[str, Any]:
    """Generate improvement suggestions for a prompt.

    Args:
        prompt: The prompt to improve.
        heuristic: Optional heuristic analysis for context.
        focus_areas: Optional list of areas to focus on.

    Returns:
        Dictionary with original, suggested, explanation, and changes.
    """
    client = get_client()

    # Build context from heuristic analysis
    context_parts = []
    if heuristic:
        context_parts.append("Heuristic analysis scores:")
        context_parts.append(f"- Clarity: {heuristic.clarity.score}/100")
        context_parts.append(f"- Specificity: {heuristic.specificity.score}/100")
        context_parts.append(f"- Structure: {heuristic.structure.score}/100")
        context_parts.append(f"- Completeness: {heuristic.completeness.score}/100")
        context_parts.append(f"- Output Format: {heuristic.output_format.score}/100")
        context_parts.append(f"- Guardrails: {heuristic.guardrails.score}/100")

        # Include issues from lowest-scoring dimensions
        all_issues = []
        for dim_name in ["clarity", "specificity", "structure", "completeness", "output_format", "guardrails"]:
            dim = getattr(heuristic, dim_name)
            if dim.score < 70:
                all_issues.extend([f"[{dim_name}] {issue}" for issue in dim.issues])
        if all_issues:
            context_parts.append("\nIdentified issues:")
            context_parts.extend([f"- {issue}" for issue in all_issues[:10]])

    context = "\n".join(context_parts) if context_parts else ""

    focus_instruction = ""
    if focus_areas:
        focus_instruction = f"\nFocus especially on improving: {', '.join(focus_areas)}"

    prompt_type = "system prompt" if prompt.type == PromptType.SYSTEM else "user prompt"

    user_message = f"""Improve this {prompt_type}:

---
{prompt.content}
---

{context}
{focus_instruction}

Provide specific improvements in the specified JSON format."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            system=SUGGESTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text

        # Extract JSON from response
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()

        data = json.loads(json_str)

        return {
            "original": prompt.content,
            "suggested": data.get("suggested", prompt.content),
            "explanation": data.get("explanation", ""),
            "changes": data.get("changes", []),
        }

    except json.JSONDecodeError:
        return {
            "original": prompt.content,
            "suggested": prompt.content,
            "explanation": "Failed to parse suggestions",
            "changes": [],
        }
    except anthropic.APIError as e:
        return {
            "original": prompt.content,
            "suggested": prompt.content,
            "explanation": f"API error: {e}",
            "changes": [],
        }

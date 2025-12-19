"""Heuristic analysis engine for evaluating prompts."""

import re

import textstat

from backend.models.schemas import DimensionScore, HeuristicAnalysis, Issue, Prompt, PromptType
from backend.services.config import AnalysisConfig, get_config


def find_line_number(content: str, search_text: str, start_line: int) -> int | None:
    """Find the line number where search_text appears."""
    lines = content.split("\n")
    search_lower = search_text.lower()
    for idx, line in enumerate(lines):
        if search_lower in line.lower():
            return start_line + idx
    return None


def find_pattern_lines(content: str, pattern: str, start_line: int) -> list[tuple[int, str]]:
    """Find all lines matching a regex pattern, returning (line_num, snippet) pairs."""
    lines = content.split("\n")
    results = []
    regex = re.compile(pattern, re.IGNORECASE)
    for idx, line in enumerate(lines):
        match = regex.search(line)
        if match:
            results.append((start_line + idx, match.group(0)))
    return results


def analyze_clarity(prompt: Prompt, config: AnalysisConfig) -> DimensionScore:
    """Analyze prompt clarity based on readability and sentence structure."""
    content = prompt.content
    start_line = prompt.line_start
    issues: list[Issue] = []
    suggestions: list[str] = []

    # Calculate readability score using Flesch Reading Ease
    flesch_score = textstat.flesch_reading_ease(content)

    # Check sentence length - find long sentences with line numbers
    lines = content.split("\n")
    for idx, line in enumerate(lines):
        sentences = re.split(r"[.!?]+", line)
        for sentence in sentences:
            word_count = len(sentence.split())
            if word_count > config.max_sentence_length:
                issues.append(Issue(
                    message=f"Overly long sentence ({word_count} words)",
                    line=start_line + idx,
                    snippet=sentence[:60] + "..." if len(sentence) > 60 else sentence
                ))

    if any(i.message.startswith("Overly long") for i in issues):
        suggestions.append("Break long sentences into shorter, clearer ones")

    # Check for passive voice indicators with line numbers
    passive_matches = find_pattern_lines(
        content, r"\b(is|are|was|were|been|being)\s+\w+ed\b", start_line
    )
    if len(passive_matches) > 2:
        for line_num, snippet in passive_matches[:3]:  # Report first 3
            issues.append(Issue(
                message="Passive voice construction",
                line=line_num,
                snippet=snippet
            ))
        suggestions.append("Use active voice for clearer instructions")

    # Check for ambiguous pronouns with line numbers
    pronoun_matches = find_pattern_lines(content, r"\b(it|this|that|these|those)\b", start_line)
    if len(pronoun_matches) > 5:
        issues.append(Issue(
            message=f"High use of pronouns ({len(pronoun_matches)}) may cause ambiguity",
            line=pronoun_matches[0][0],
            snippet=None
        ))
        suggestions.append("Replace ambiguous pronouns with specific nouns")

    # Calculate score based on readability
    if flesch_score < 30:
        base_score = 40
        issues.append(Issue(message="Text is very difficult to read", line=None, snippet=None))
        suggestions.append("Simplify language and sentence structure")
    elif flesch_score < 50:
        base_score = 60
        issues.append(Issue(message="Text is somewhat difficult to read", line=None, snippet=None))
    elif flesch_score < 70:
        base_score = 80
    else:
        base_score = 95

    penalty = min(30, len(issues) * 5)
    score = max(0, base_score - penalty)

    return DimensionScore(score=score, issues=issues, suggestions=suggestions)


def analyze_specificity(prompt: Prompt, config: AnalysisConfig) -> DimensionScore:
    """Analyze how specific and concrete the prompt is."""
    content = prompt.content
    start_line = prompt.line_start
    issues: list[Issue] = []
    suggestions: list[str] = []

    # Check for vague terms with line numbers
    for term in config.vague_terms:
        matches = find_pattern_lines(content, rf"\b{term}\b", start_line)
        for line_num, snippet in matches:
            issues.append(Issue(
                message=f"Vague term: '{term}'",
                line=line_num,
                snippet=snippet
            ))

    if any(i.message.startswith("Vague term") for i in issues):
        suggestions.append("Replace vague terms with specific criteria or examples")

    # Check for concrete examples
    has_examples = any(
        marker in content.lower()
        for marker in config.example_markers
    )
    if not has_examples:
        issues.append(Issue(
            message="No examples provided",
            line=None,
            snippet=None
        ))
        suggestions.append("Add concrete examples to clarify expectations")

    # Check for quantifiable criteria
    has_numbers = bool(re.search(r"\b\d+\b", content))
    has_quantities = any(
        q in content.lower()
        for q in ["at least", "at most", "maximum", "minimum", "up to", "no more than"]
    )
    if not has_numbers and not has_quantities:
        issues.append(Issue(
            message="No quantifiable criteria found",
            line=None,
            snippet=None
        ))
        suggestions.append("Add specific numbers or quantities where applicable")

    # Calculate score
    vague_count = sum(1 for i in issues if i.message.startswith("Vague term"))
    base_score = 100
    penalty = vague_count * 5 + (15 if not has_examples else 0) + (10 if not has_numbers else 0)
    score = max(0, base_score - penalty)

    return DimensionScore(score=score, issues=issues, suggestions=suggestions)


def analyze_structure(prompt: Prompt, config: AnalysisConfig) -> DimensionScore:
    """Analyze the organizational structure of the prompt."""
    content = prompt.content
    start_line = prompt.line_start
    issues: list[Issue] = []
    suggestions: list[str] = []

    lines = content.split("\n")
    word_count = len(content.split())

    # Check for structural elements
    has_lists = any(line.strip().startswith(("-", "*", "•")) for line in lines)
    has_numbered = any(re.match(r"^\s*\d+\.", line) for line in lines)
    has_sections = any(line.strip().startswith("#") for line in lines)

    # Long prompts should have structure
    if word_count > 100 and not (has_lists or has_numbered or has_sections):
        issues.append(Issue(
            message="Long prompt lacks organizational structure",
            line=start_line,
            snippet=None
        ))
        suggestions.append("Break content into sections or bullet points")

    # Check for logical flow markers
    has_flow = any(marker in content.lower() for marker in config.flow_markers)
    if word_count > 50 and not has_flow and not has_numbered:
        issues.append(Issue(
            message="No clear sequence or flow indicators",
            line=None,
            snippet=None
        ))
        suggestions.append("Add sequence markers (first, then, finally) for multi-step instructions")

    # Check for paragraph breaks in long content - find dense blocks
    if word_count > 80 and len(lines) < 3:
        issues.append(Issue(
            message="Dense text block without paragraph breaks",
            line=start_line,
            snippet=lines[0][:50] + "..." if len(lines[0]) > 50 else lines[0]
        ))
        suggestions.append("Add paragraph breaks to improve readability")

    # Calculate score
    base_score = 100
    if word_count > 100:
        if has_lists or has_numbered:
            base_score = 95
        elif has_sections:
            base_score = 90
        else:
            base_score = 60

    penalty = len(issues) * 10
    score = max(0, base_score - penalty)

    return DimensionScore(score=score, issues=issues, suggestions=suggestions)


def analyze_completeness(prompt: Prompt, config: AnalysisConfig) -> DimensionScore:
    """Analyze whether the prompt provides sufficient context."""
    content = prompt.content
    content_lower = content.lower()
    start_line = prompt.line_start
    issues: list[Issue] = []
    suggestions: list[str] = []

    word_count = len(content.split())

    # Check minimum content
    if word_count < config.min_word_count:
        issues.append(Issue(
            message=f"Prompt is very short ({word_count} words)",
            line=start_line,
            snippet=None
        ))
        suggestions.append(f"Consider expanding to at least {config.min_word_count} words")

    # Check for role/persona definition (important for system prompts)
    if prompt.type == PromptType.SYSTEM or prompt.type == PromptType.SKILL:
        has_role = any(marker in content_lower for marker in config.role_markers)
        if not has_role:
            issues.append(Issue(
                message="No clear role or persona defined",
                line=start_line,
                snippet=None
            ))
            suggestions.append("Start with 'You are...' to establish the assistant's role")

    # Check for context/background
    has_context = any(marker in content_lower for marker in config.context_markers)
    if not has_context and word_count > 30:
        issues.append(Issue(
            message="No explicit context or background provided",
            line=None,
            snippet=None
        ))
        suggestions.append("Add context about the situation or domain")

    # Check for task definition
    has_task = any(marker in content_lower for marker in config.task_markers)
    if not has_task:
        issues.append(Issue(
            message="No clear task or objective stated",
            line=None,
            snippet=None
        ))
        suggestions.append("Clearly state what you want the assistant to do")

    # Calculate score
    base_score = 100
    if word_count < 10:
        base_score = 30
    elif word_count < config.min_word_count:
        base_score = 60

    penalty = len(issues) * 12
    score = max(0, base_score - penalty)

    return DimensionScore(score=score, issues=issues, suggestions=suggestions)


def analyze_output_format(prompt: Prompt, config: AnalysisConfig) -> DimensionScore:
    """Analyze whether the prompt specifies expected output format."""
    content = prompt.content
    content_lower = content.lower()
    issues: list[Issue] = []
    suggestions: list[str] = []

    # Check for format specifications
    format_markers = config.output_format_markers
    has_format = any(marker in content_lower for marker in format_markers)

    if not has_format:
        issues.append(Issue(
            message="No output format specified",
            line=None,
            snippet=None
        ))
        suggestions.append("Specify how you want the response formatted (JSON, list, paragraph, etc.)")

    # Check for specific format types
    has_specific = any(fmt in content_lower for fmt in config.specific_formats)

    # Check for length expectations
    has_length = any(marker in content_lower for marker in config.length_markers)

    if not has_length:
        issues.append(Issue(
            message="No length or detail level specified",
            line=None,
            snippet=None
        ))
        suggestions.append("Indicate desired response length (e.g., 'in 2-3 sentences' or 'detailed explanation')")

    # Calculate score
    base_score = 100
    if not has_format:
        base_score = 50
    elif has_specific:
        base_score = 100
    else:
        base_score = 75

    if not has_length:
        base_score -= 15

    score = max(0, base_score)

    return DimensionScore(score=score, issues=issues, suggestions=suggestions)


def analyze_guardrails(prompt: Prompt, config: AnalysisConfig) -> DimensionScore:
    """Analyze safety constraints and boundary definitions."""
    content = prompt.content
    content_lower = content.lower()
    start_line = prompt.line_start
    issues: list[Issue] = []
    suggestions: list[str] = []

    # Check for guardrail markers
    guardrail_markers = config.guardrail_markers
    has_guardrails = any(marker in content_lower for marker in guardrail_markers)

    # System prompts and skills should have guardrails
    if prompt.type == PromptType.SYSTEM or prompt.type == PromptType.SKILL:
        if not has_guardrails:
            issues.append(Issue(
                message="System prompt lacks safety constraints",
                line=start_line,
                snippet=None
            ))
            suggestions.append("Add boundaries (e.g., 'Never share sensitive information', 'Only discuss topics related to...')")

        # Check for edge case handling
        has_edge_handling = any(marker in content_lower for marker in config.edge_case_markers)
        if not has_edge_handling:
            issues.append(Issue(
                message="No edge case handling defined",
                line=None,
                snippet=None
            ))
            suggestions.append("Add instructions for handling edge cases or unexpected inputs")

    # Check for scope definition
    has_scope = any(marker in content_lower for marker in config.scope_markers)
    if not has_scope and (prompt.type == PromptType.SYSTEM or prompt.type == PromptType.SKILL):
        issues.append(Issue(
            message="No clear scope boundaries defined",
            line=None,
            snippet=None
        ))
        suggestions.append("Define the scope of what the assistant should and shouldn't do")

    # Calculate score
    if prompt.type == PromptType.SYSTEM or prompt.type == PromptType.SKILL:
        base_score = 100
        if not has_guardrails:
            base_score = 40
        elif not has_scope:
            base_score = 70
        penalty = len(issues) * 10
        score = max(0, base_score - penalty)
    else:
        # User prompts don't necessarily need guardrails
        score = 80 if has_guardrails else 70
        if not has_guardrails:
            issues.append(Issue(
                message="Consider adding constraints if needed",
                line=None,
                snippet=None
            ))
            suggestions.append("Add boundaries if you want to limit the response scope")

    return DimensionScore(score=score, issues=issues, suggestions=suggestions)


def analyze_prompt(prompt: Prompt, config: AnalysisConfig | None = None) -> HeuristicAnalysis:
    """Run full heuristic analysis on a prompt.

    Args:
        prompt: The prompt to analyze.
        config: Optional configuration for analysis thresholds.
                If None, uses the global config (loaded from YAML or defaults).

    Returns:
        HeuristicAnalysis with scores for all dimensions.
    """
    if config is None:
        config = get_config()

    clarity = analyze_clarity(prompt, config)
    specificity = analyze_specificity(prompt, config)
    structure = analyze_structure(prompt, config)
    completeness = analyze_completeness(prompt, config)
    output_format = analyze_output_format(prompt, config)
    guardrails = analyze_guardrails(prompt, config)

    # Calculate overall score as weighted average using config weights
    guardrails_weight = (
        config.weights.get("guardrails_system", 1.2)
        if prompt.type in (PromptType.SYSTEM, PromptType.SKILL)
        else config.weights.get("guardrails_user", 0.6)
    )

    weights = {
        "clarity": config.weights.get("clarity", 1.0),
        "specificity": config.weights.get("specificity", 1.0),
        "structure": config.weights.get("structure", 0.8),
        "completeness": config.weights.get("completeness", 1.2),
        "output_format": config.weights.get("output_format", 0.8),
        "guardrails": guardrails_weight,
    }

    total_weight = sum(weights.values())
    weighted_sum = (
        clarity.score * weights["clarity"]
        + specificity.score * weights["specificity"]
        + structure.score * weights["structure"]
        + completeness.score * weights["completeness"]
        + output_format.score * weights["output_format"]
        + guardrails.score * weights["guardrails"]
    )
    overall_score = int(weighted_sum / total_weight)

    return HeuristicAnalysis(
        prompt_id=prompt.id,
        overall_score=overall_score,
        clarity=clarity,
        specificity=specificity,
        structure=structure,
        completeness=completeness,
        output_format=output_format,
        guardrails=guardrails,
    )

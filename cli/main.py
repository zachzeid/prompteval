"""CLI entry point for promptdesign."""

import asyncio
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from cli.parser import parse_markdown_file, validate_markdown_file


def check_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))

app = typer.Typer(
    name="prompteval",
    help="Evaluate prompts in markdown files and suggest improvements.",
    add_completion=False,
)


@app.command()
def serve(
    file: Optional[Path] = typer.Argument(
        None,
        help="Markdown file to load on startup",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    port: int = typer.Option(8080, "--port", "-p", help="Port to run the server on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open browser"),
) -> None:
    """Start the web UI server."""
    typer.echo(f"Starting PromptDesign server on http://{host}:{port}")

    if file:
        typer.echo(f"Loading file: {file}")
        # Validate the file first
        is_valid, errors = validate_markdown_file(file)
        if not is_valid:
            typer.echo("Warning: File has issues:", err=True)
            for error in errors:
                typer.echo(f"  - {error}", err=True)

    if not no_browser:
        # Open browser after a short delay to let server start
        import threading

        def open_browser() -> None:
            import time

            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=open_browser, daemon=True).start()

    # Run the FastAPI server
    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


@app.command()
def analyze(
    file: Path = typer.Argument(
        ...,
        help="Markdown file to analyze",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for analysis results (JSON)",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Custom rules config file (YAML)",
        exists=True,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    llm: bool = typer.Option(False, "--llm", "-l", help="Include LLM-powered deep analysis (requires API key)"),
) -> None:
    """Run heuristic analysis on prompts in a file (no UI)."""
    from backend.services.config import load_config, set_config
    from backend.services.heuristics import analyze_prompt

    # Load custom config if specified
    if config_file:
        typer.echo(f"Loading config: {config_file}")
        try:
            custom_config = load_config(config_file)
            set_config(custom_config)
        except Exception as e:
            typer.echo(f"Error loading config: {e}", err=True)
            raise typer.Exit(1)

    typer.echo(f"Analyzing: {file}")

    # Check for API key if LLM analysis requested
    if llm and not check_api_key():
        typer.echo("Error: ANTHROPIC_API_KEY not set. Required for --llm option.", err=True)
        typer.echo("Set it in .env file or export ANTHROPIC_API_KEY=your-key", err=True)
        raise typer.Exit(1)

    parsed = parse_markdown_file(file)

    if not parsed.prompts:
        typer.echo("No prompts found in file.", err=True)
        raise typer.Exit(1)

    typer.echo(f"Found {len(parsed.prompts)} prompt(s)\n")

    results = []
    for prompt in parsed.prompts:
        analysis = analyze_prompt(prompt)
        result_data = {"heuristic": analysis.model_dump()}

        # Display summary
        type_badge = "[SYS]" if prompt.type == "system" else "[USR]"
        typer.echo(f"{type_badge} {prompt.name}")
        typer.echo(f"    Overall Score: {analysis.overall_score}/100")

        if verbose:
            typer.echo(f"    Clarity:       {analysis.clarity.score}/100")
            typer.echo(f"    Specificity:   {analysis.specificity.score}/100")
            typer.echo(f"    Structure:     {analysis.structure.score}/100")
            typer.echo(f"    Completeness:  {analysis.completeness.score}/100")
            typer.echo(f"    Output Format: {analysis.output_format.score}/100")
            typer.echo(f"    Guardrails:    {analysis.guardrails.score}/100")

            # Show top issues
            all_issues = []
            for dim_name in ["clarity", "specificity", "structure", "completeness", "output_format", "guardrails"]:
                dim = getattr(analysis, dim_name)
                for issue in dim.issues:
                    line_ref = f" (line {issue.line})" if issue.line else ""
                    all_issues.append(f"{issue.message}{line_ref}")
            if all_issues:
                typer.echo("    Issues:")
                for issue in all_issues[:5]:
                    typer.echo(f"      - {issue}")

        # Run LLM analysis if requested
        if llm:
            from backend.services.llm import analyze_with_llm

            typer.echo("    Running LLM analysis...")
            llm_result = asyncio.run(analyze_with_llm(prompt))
            result_data["llm"] = llm_result.model_dump()

            if llm_result.error:
                typer.echo(f"    LLM Error: {llm_result.error}", err=True)
            else:
                if llm_result.ambiguities:
                    typer.echo("    Ambiguities:")
                    for item in llm_result.ambiguities[:3]:
                        typer.echo(f"      - {item}")
                if llm_result.missing_context:
                    typer.echo("    Missing Context:")
                    for item in llm_result.missing_context[:3]:
                        typer.echo(f"      - {item}")
                if llm_result.injection_risks:
                    typer.echo("    Injection Risks:")
                    for item in llm_result.injection_risks[:3]:
                        typer.echo(f"      - {item}")
                if llm_result.best_practice_issues:
                    typer.echo("    Best Practice Issues:")
                    for item in llm_result.best_practice_issues[:3]:
                        typer.echo(f"      - {item}")

        results.append(result_data)
        typer.echo()

    if output:
        output.write_text(json.dumps(results, indent=2))
        typer.echo(f"Results saved to: {output}")


@app.command()
def validate(
    file: Path = typer.Argument(
        ...,
        help="Markdown file to validate",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """Validate a markdown file's prompt format."""
    is_valid, errors = validate_markdown_file(file)

    if is_valid:
        parsed = parse_markdown_file(file)
        typer.echo(f"Valid! Found {len(parsed.prompts)} prompt(s):")
        for prompt in parsed.prompts:
            type_badge = "[SYS]" if prompt.type == "system" else "[USR]"
            typer.echo(f"  {type_badge} {prompt.name} (lines {prompt.line_start}-{prompt.line_end})")
    else:
        typer.echo("Validation failed:", err=True)
        for error in errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(1)


@app.command()
def suggest(
    file: Path = typer.Argument(
        ...,
        help="Markdown file containing prompts",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    prompt_name: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="Name of specific prompt to improve (default: first prompt)",
    ),
    focus: Optional[str] = typer.Option(
        None,
        "--focus",
        "-f",
        help="Comma-separated focus areas (e.g., 'clarity,specificity')",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Custom rules config file (YAML)",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for suggested prompt",
    ),
) -> None:
    """Generate LLM-powered improvement suggestions for a prompt."""
    if not check_api_key():
        typer.echo("Error: ANTHROPIC_API_KEY not set.", err=True)
        typer.echo("Set it in .env file or export ANTHROPIC_API_KEY=your-key", err=True)
        raise typer.Exit(1)

    from backend.services.config import load_config, set_config
    from backend.services.heuristics import analyze_prompt
    from backend.services.llm import generate_suggestions

    # Load custom config if specified
    if config_file:
        typer.echo(f"Loading config: {config_file}")
        try:
            custom_config = load_config(config_file)
            set_config(custom_config)
        except Exception as e:
            typer.echo(f"Error loading config: {e}", err=True)
            raise typer.Exit(1)

    parsed = parse_markdown_file(file)

    if not parsed.prompts:
        typer.echo("No prompts found in file.", err=True)
        raise typer.Exit(1)

    # Find the target prompt
    target_prompt = None
    if prompt_name:
        for p in parsed.prompts:
            if p.name.lower() == prompt_name.lower():
                target_prompt = p
                break
        if not target_prompt:
            typer.echo(f"Prompt '{prompt_name}' not found.", err=True)
            typer.echo("Available prompts:")
            for p in parsed.prompts:
                typer.echo(f"  - {p.name}")
            raise typer.Exit(1)
    else:
        target_prompt = parsed.prompts[0]

    typer.echo(f"Generating suggestions for: {target_prompt.name}\n")

    # Run heuristic analysis for context
    heuristic = analyze_prompt(target_prompt)

    # Parse focus areas
    focus_areas = [f.strip() for f in focus.split(",")] if focus else None

    # Generate suggestions
    typer.echo("Calling LLM for suggestions...")
    result = asyncio.run(generate_suggestions(target_prompt, heuristic, focus_areas))

    if result.get("explanation") == "Failed to parse suggestions":
        typer.echo("Error: Failed to generate suggestions", err=True)
        raise typer.Exit(1)

    typer.echo("\n" + "=" * 60)
    typer.echo("SUGGESTED IMPROVEMENTS")
    typer.echo("=" * 60 + "\n")

    typer.echo(result.get("explanation", ""))
    typer.echo()

    if result.get("changes"):
        typer.echo("Changes made:")
        for change in result["changes"]:
            typer.echo(f"\n  Original: {change.get('original', '')[:60]}...")
            typer.echo(f"  Replacement: {change.get('replacement', '')[:60]}...")
            typer.echo(f"  Reason: {change.get('reason', '')}")

    typer.echo("\n" + "-" * 60)
    typer.echo("IMPROVED PROMPT")
    typer.echo("-" * 60 + "\n")
    typer.echo(result.get("suggested", target_prompt.content))

    if output:
        output.write_text(result.get("suggested", target_prompt.content))
        typer.echo(f"\nSaved to: {output}")


@app.command()
def check(
    prompt_text: Optional[str] = typer.Argument(
        None,
        help="Prompt text to analyze (or use --stdin to read from stdin)",
    ),
    stdin: bool = typer.Option(False, "--stdin", "-s", help="Read prompt from stdin"),
    prompt_type: str = typer.Option(
        "user",
        "--type",
        "-t",
        help="Prompt type: 'system', 'user', or 'skill'",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Custom rules config file (YAML)",
        exists=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for analysis results (JSON)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    llm: bool = typer.Option(False, "--llm", "-l", help="Include LLM-powered deep analysis"),
) -> None:
    """Analyze a prompt string directly (without a file)."""
    import uuid

    from backend.models.schemas import Prompt, PromptType
    from backend.services.config import load_config, set_config
    from backend.services.heuristics import analyze_prompt

    # Load custom config if specified
    if config_file:
        try:
            custom_config = load_config(config_file)
            set_config(custom_config)
        except Exception as e:
            typer.echo(f"Error loading config: {e}", err=True)
            raise typer.Exit(1)

    # Get prompt text
    if stdin:
        import sys
        prompt_text = sys.stdin.read().strip()
    elif prompt_text is None:
        typer.echo("Error: Provide prompt text as argument or use --stdin", err=True)
        raise typer.Exit(1)

    if not prompt_text:
        typer.echo("Error: Prompt text is empty", err=True)
        raise typer.Exit(1)

    # Check for API key if LLM analysis requested
    if llm and not check_api_key():
        typer.echo("Error: ANTHROPIC_API_KEY not set. Required for --llm option.", err=True)
        raise typer.Exit(1)

    # Map prompt type string to enum
    type_map = {
        "system": PromptType.SYSTEM,
        "user": PromptType.USER,
        "skill": PromptType.SKILL,
    }
    if prompt_type.lower() not in type_map:
        typer.echo(f"Error: Invalid prompt type '{prompt_type}'. Use 'system', 'user', or 'skill'.", err=True)
        raise typer.Exit(1)

    # Create a prompt object
    prompt = Prompt(
        id=str(uuid.uuid4()),
        name="inline-prompt",
        type=type_map[prompt_type.lower()],
        content=prompt_text,
        line_start=1,
        line_end=prompt_text.count("\n") + 1,
        metadata=None,
    )

    typer.echo(f"Analyzing {prompt_type} prompt ({len(prompt_text)} chars)\n")

    # Run heuristic analysis
    analysis = analyze_prompt(prompt)
    result_data = {"heuristic": analysis.model_dump()}

    typer.echo(f"Overall Score: {analysis.overall_score}/100")

    if verbose:
        typer.echo(f"  Clarity:       {analysis.clarity.score}/100")
        typer.echo(f"  Specificity:   {analysis.specificity.score}/100")
        typer.echo(f"  Structure:     {analysis.structure.score}/100")
        typer.echo(f"  Completeness:  {analysis.completeness.score}/100")
        typer.echo(f"  Output Format: {analysis.output_format.score}/100")
        typer.echo(f"  Guardrails:    {analysis.guardrails.score}/100")

        # Show issues
        all_issues = []
        for dim_name in ["clarity", "specificity", "structure", "completeness", "output_format", "guardrails"]:
            dim = getattr(analysis, dim_name)
            for issue in dim.issues:
                line_ref = f" (line {issue.line})" if issue.line else ""
                all_issues.append(f"{issue.message}{line_ref}")
        if all_issues:
            typer.echo("\nIssues:")
            for issue in all_issues:
                typer.echo(f"  - {issue}")

        # Show suggestions
        all_suggestions = []
        for dim_name in ["clarity", "specificity", "structure", "completeness", "output_format", "guardrails"]:
            dim = getattr(analysis, dim_name)
            all_suggestions.extend(dim.suggestions)
        if all_suggestions:
            typer.echo("\nSuggestions:")
            for suggestion in all_suggestions:
                typer.echo(f"  - {suggestion}")

    # Run LLM analysis if requested
    if llm:
        from backend.services.llm import analyze_with_llm

        typer.echo("\nRunning LLM analysis...")
        llm_result = asyncio.run(analyze_with_llm(prompt))
        result_data["llm"] = llm_result.model_dump()

        if llm_result.error:
            typer.echo(f"LLM Error: {llm_result.error}", err=True)
        else:
            if llm_result.ambiguities:
                typer.echo("\nAmbiguities:")
                for item in llm_result.ambiguities:
                    typer.echo(f"  - {item}")
            if llm_result.missing_context:
                typer.echo("\nMissing Context:")
                for item in llm_result.missing_context:
                    typer.echo(f"  - {item}")
            if llm_result.injection_risks:
                typer.echo("\nInjection Risks:")
                for item in llm_result.injection_risks:
                    typer.echo(f"  - {item}")
            if llm_result.best_practice_issues:
                typer.echo("\nBest Practice Issues:")
                for item in llm_result.best_practice_issues:
                    typer.echo(f"  - {item}")

    if output:
        output.write_text(json.dumps(result_data, indent=2))
        typer.echo(f"\nResults saved to: {output}")


@app.command()
def init(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialize",
    ),
) -> None:
    """Create a sample prompts.md file."""
    sample_content = '''# My Prompts

## System Prompt: Assistant
You are a helpful AI assistant. Your responsibilities include:
- Answering questions clearly and concisely
- Providing accurate information
- Asking for clarification when needed

Always be polite and professional. Never make up information.

## User Prompt: Code Review
Please review the following code for:
1. Potential bugs or errors
2. Performance issues
3. Code style and readability

Provide your feedback in a structured format with specific line references.

## User Prompt: Summarization
Summarize the following text in 2-3 sentences, focusing on the key points.
'''

    output_file = directory / "prompts.md"
    if output_file.exists():
        typer.confirm(
            f"{output_file} already exists. Overwrite?",
            abort=True,
        )

    output_file.write_text(sample_content)
    typer.echo(f"Created sample file: {output_file}")
    typer.echo("\nRun 'prompteval serve prompts.md' to start the web UI.")


if __name__ == "__main__":
    app()

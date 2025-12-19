"""Markdown parser for extracting prompts from heading-based and YAML frontmatter formats."""

import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from backend.models.schemas import ParsedFile, Prompt, PromptMetadata, PromptType


# Pattern to match prompt headings
# Matches: ## System Prompt, ## System Prompt: Name, ## User Prompt, ## User Prompt: Name
HEADING_PATTERN = re.compile(
    r"^##\s+(System|User)\s+Prompt(?::\s*(.+))?$",
    re.IGNORECASE,
)

# Pattern to detect YAML frontmatter
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_yaml_frontmatter(content: str) -> tuple[dict[str, Any] | None, str, int]:
    """Extract YAML frontmatter from content.

    Args:
        content: The full file content.

    Returns:
        Tuple of (metadata dict or None, remaining content, frontmatter end line).
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return None, content, 0

    yaml_content = match.group(1)
    try:
        metadata = yaml.safe_load(yaml_content)
        if not isinstance(metadata, dict):
            return None, content, 0
    except yaml.YAMLError:
        return None, content, 0

    # Calculate the line number where frontmatter ends
    frontmatter_lines = content[: match.end()].count("\n")
    remaining_content = content[match.end() :]

    return metadata, remaining_content, frontmatter_lines


def parse_frontmatter_prompt(
    content: str, filename: str, metadata: dict[str, Any], frontmatter_end_line: int
) -> Prompt:
    """Parse a prompt from YAML frontmatter format.

    Args:
        content: The prompt content (after frontmatter).
        filename: Source filename.
        metadata: Parsed YAML frontmatter.
        frontmatter_end_line: Line number where frontmatter ends.

    Returns:
        A Prompt object.
    """
    # Extract known metadata fields
    known_fields = {"name", "description", "license", "version", "author", "tags"}
    extra = {k: str(v) for k, v in metadata.items() if k not in known_fields}

    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    prompt_metadata = PromptMetadata(
        name=metadata.get("name"),
        description=metadata.get("description"),
        license=metadata.get("license"),
        version=metadata.get("version"),
        author=metadata.get("author"),
        tags=tags if isinstance(tags, list) else [],
        extra=extra,
    )

    # Use name from frontmatter, or derive from filename
    name = metadata.get("name") or Path(filename).stem

    return Prompt(
        id=str(uuid.uuid4()),
        name=name,
        type=PromptType.SKILL,
        content=content.strip(),
        line_start=frontmatter_end_line + 1,
        line_end=frontmatter_end_line + content.count("\n") + 1,
        metadata=prompt_metadata,
    )


def parse_markdown_file(file_path: str | Path) -> ParsedFile:
    """Parse a markdown file and extract prompts.

    Args:
        file_path: Path to the markdown file.

    Returns:
        ParsedFile containing all extracted prompts.
    """
    file_path = Path(file_path)
    content = file_path.read_text(encoding="utf-8")
    return parse_markdown_content(content, file_path.name)


def parse_markdown_content(content: str, filename: str = "untitled.md") -> ParsedFile:
    """Parse markdown content and extract prompts.

    Supports two formats:
    1. YAML frontmatter format (for AI agent skills)
    2. Heading-based format (## System Prompt / ## User Prompt)

    Args:
        content: Markdown content as string.
        filename: Name of the source file.

    Returns:
        ParsedFile containing all extracted prompts.
    """
    # First, check for YAML frontmatter format
    metadata, remaining_content, frontmatter_end_line = parse_yaml_frontmatter(content)

    if metadata is not None:
        # This is a frontmatter-style skill prompt
        prompt = parse_frontmatter_prompt(
            remaining_content, filename, metadata, frontmatter_end_line
        )
        return ParsedFile(filename=filename, prompts=[prompt])

    # Fall back to heading-based format
    lines = content.split("\n")
    prompts: list[Prompt] = []

    current_prompt: dict | None = None
    current_content_lines: list[str] = []
    current_start_line: int = 0

    for line_num, line in enumerate(lines, start=1):
        match = HEADING_PATTERN.match(line.strip())

        if match:
            # Save previous prompt if exists
            if current_prompt is not None:
                prompt_content = "\n".join(current_content_lines).strip()
                if prompt_content:
                    prompts.append(
                        Prompt(
                            id=str(uuid.uuid4()),
                            name=current_prompt["name"],
                            type=current_prompt["type"],
                            content=prompt_content,
                            line_start=current_start_line,
                            line_end=line_num - 1,
                        )
                    )

            # Start new prompt
            prompt_type_str = match.group(1).lower()
            prompt_name = match.group(2) or f"{prompt_type_str.capitalize()} Prompt"

            current_prompt = {
                "name": prompt_name.strip(),
                "type": PromptType.SYSTEM if prompt_type_str == "system" else PromptType.USER,
            }
            current_content_lines = []
            current_start_line = line_num

        elif current_prompt is not None:
            # Check if this is a new heading (any level) that ends the current prompt
            if line.strip().startswith("#") and not line.strip().startswith("###"):
                # This is a level 1 or 2 heading, save current prompt
                prompt_content = "\n".join(current_content_lines).strip()
                if prompt_content:
                    prompts.append(
                        Prompt(
                            id=str(uuid.uuid4()),
                            name=current_prompt["name"],
                            type=current_prompt["type"],
                            content=prompt_content,
                            line_start=current_start_line,
                            line_end=line_num - 1,
                        )
                    )
                current_prompt = None
                current_content_lines = []
            else:
                # Add line to current prompt content
                current_content_lines.append(line)

    # Don't forget the last prompt
    if current_prompt is not None:
        prompt_content = "\n".join(current_content_lines).strip()
        if prompt_content:
            prompts.append(
                Prompt(
                    id=str(uuid.uuid4()),
                    name=current_prompt["name"],
                    type=current_prompt["type"],
                    content=prompt_content,
                    line_start=current_start_line,
                    line_end=len(lines),
                )
            )

    return ParsedFile(filename=filename, prompts=prompts)


def validate_markdown_file(file_path: str | Path) -> tuple[bool, list[str]]:
    """Validate that a markdown file contains valid prompt definitions.

    Args:
        file_path: Path to the markdown file.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []

    try:
        parsed = parse_markdown_file(file_path)
    except FileNotFoundError:
        return False, [f"File not found: {file_path}"]
    except Exception as e:
        return False, [f"Failed to parse file: {e}"]

    if not parsed.prompts:
        errors.append(
            "No prompts found. Use YAML frontmatter (---) or "
            "'## System Prompt' / '## User Prompt' headings."
        )

    for prompt in parsed.prompts:
        if len(prompt.content) < 10:
            errors.append(
                f"Prompt '{prompt.name}' (line {prompt.line_start}) is too short "
                f"({len(prompt.content)} chars). Consider adding more detail."
            )

        # Validate skill prompts have required metadata
        if prompt.type == PromptType.SKILL and prompt.metadata:
            if not prompt.metadata.name:
                errors.append(
                    f"Skill prompt '{prompt.name}' is missing 'name' in frontmatter."
                )
            if not prompt.metadata.description:
                errors.append(
                    f"Skill prompt '{prompt.name}' is missing 'description' in frontmatter."
                )

    return len(errors) == 0, errors

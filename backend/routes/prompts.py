"""API routes for prompt management."""

import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from backend.models.schemas import ParsedFile, Prompt, PromptType
from cli.parser import parse_markdown_content

router = APIRouter()

# In-memory storage for parsed prompts (per design decision)
_prompt_store: dict[str, Prompt] = {}
_current_file: ParsedFile | None = None


class PromptUpdate(BaseModel):
    """Request to update a prompt's content."""

    content: str


class InlinePromptCreate(BaseModel):
    """Request to create an inline prompt."""

    content: str
    name: str = "Inline Prompt"
    type: str = "user"  # 'system', 'user', or 'skill'


class ExportRequest(BaseModel):
    """Request to export prompts."""

    prompt_ids: list[str] = []
    include_analysis: bool = False


@router.post("/parse", response_model=ParsedFile)
async def parse_file(file: UploadFile) -> ParsedFile:
    """Parse a markdown file and extract prompts."""
    global _prompt_store, _current_file

    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="File must be a markdown (.md) file")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    parsed = parse_markdown_content(text, file.filename)

    if not parsed.prompts:
        raise HTTPException(
            status_code=400,
            detail="No prompts found. Use '## System Prompt' or '## User Prompt' headings.",
        )

    # Store prompts in memory
    _prompt_store.clear()
    for prompt in parsed.prompts:
        _prompt_store[prompt.id] = prompt

    _current_file = parsed
    return parsed


@router.post("/parse/text", response_model=ParsedFile)
async def parse_text(body: dict) -> ParsedFile:
    """Parse markdown content from text."""
    global _prompt_store, _current_file

    content = body.get("content", "")
    filename = body.get("filename", "untitled.md")

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    parsed = parse_markdown_content(content, filename)

    if not parsed.prompts:
        raise HTTPException(
            status_code=400,
            detail="No prompts found. Use '## System Prompt' or '## User Prompt' headings.",
        )

    # Store prompts in memory
    _prompt_store.clear()
    for prompt in parsed.prompts:
        _prompt_store[prompt.id] = prompt

    _current_file = parsed
    return parsed


@router.get("", response_model=list[Prompt])
async def list_prompts() -> list[Prompt]:
    """List all parsed prompts."""
    return list(_prompt_store.values())


# NOTE: Static path routes must come BEFORE path parameter routes
# to avoid /{prompt_id} matching "inline" or "export" as a prompt_id


@router.post("/inline", response_model=Prompt)
async def create_inline_prompt(request: InlinePromptCreate) -> Prompt:
    """Create an inline prompt for analysis without using markdown format."""
    global _prompt_store, _current_file

    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    # Map type string to enum
    type_map = {
        "system": PromptType.SYSTEM,
        "user": PromptType.USER,
        "skill": PromptType.SKILL,
    }
    prompt_type = type_map.get(request.type.lower())
    if not prompt_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type '{request.type}'. Use 'system', 'user', or 'skill'.",
        )

    # Create the prompt
    prompt = Prompt(
        id=str(uuid.uuid4()),
        name=request.name,
        type=prompt_type,
        content=request.content.strip(),
        line_start=1,
        line_end=request.content.count("\n") + 1,
        metadata=None,
    )

    # Store in memory (replaces existing prompts for simplicity)
    _prompt_store.clear()
    _prompt_store[prompt.id] = prompt
    _current_file = ParsedFile(filename="inline.md", prompts=[prompt])

    return prompt


@router.post("/export")
async def export_prompts(request: ExportRequest) -> dict[str, str]:
    """Export prompts back to markdown format."""
    if not _prompt_store:
        raise HTTPException(status_code=400, detail="No prompts loaded")

    prompt_ids = request.prompt_ids or list(_prompt_store.keys())
    prompts = [_prompt_store[pid] for pid in prompt_ids if pid in _prompt_store]

    if not prompts:
        raise HTTPException(status_code=400, detail="No matching prompts found")

    # Generate markdown
    lines = ["# Exported Prompts\n"]
    for prompt in prompts:
        type_label = "System" if prompt.type == "system" else "User"
        if prompt.name != f"{type_label} Prompt":
            lines.append(f"## {type_label} Prompt: {prompt.name}\n")
        else:
            lines.append(f"## {type_label} Prompt\n")
        lines.append(prompt.content)
        lines.append("\n")

    return {"markdown": "\n".join(lines)}


# Path parameter routes come last
@router.get("/{prompt_id}", response_model=Prompt)
async def get_prompt(prompt_id: str) -> Prompt:
    """Get a single prompt by ID."""
    if prompt_id not in _prompt_store:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompt_store[prompt_id]


@router.put("/{prompt_id}", response_model=Prompt)
async def update_prompt(prompt_id: str, update: PromptUpdate) -> Prompt:
    """Update a prompt's content."""
    if prompt_id not in _prompt_store:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = _prompt_store[prompt_id]
    updated = Prompt(
        id=prompt.id,
        name=prompt.name,
        type=prompt.type,
        content=update.content,
        line_start=prompt.line_start,
        line_end=prompt.line_end,
    )
    _prompt_store[prompt_id] = updated
    return updated

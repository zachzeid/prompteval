"""Pydantic models for promptdesign."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PromptType(str, Enum):
    """Type of prompt."""

    SYSTEM = "system"
    USER = "user"
    SKILL = "skill"  # For YAML frontmatter format (AI agent skills)


class PromptMetadata(BaseModel):
    """Metadata from YAML frontmatter."""

    name: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, str] = Field(default_factory=dict, description="Additional metadata fields")


class Prompt(BaseModel):
    """A parsed prompt from a markdown file."""

    id: str = Field(description="Unique identifier for the prompt")
    name: str = Field(description="Name of the prompt (from heading or frontmatter)")
    type: PromptType = Field(description="Type of prompt (system, user, or skill)")
    content: str = Field(description="The prompt text content")
    line_start: int = Field(description="Starting line number in source file")
    line_end: int = Field(description="Ending line number in source file")
    metadata: Optional[PromptMetadata] = Field(default=None, description="YAML frontmatter metadata")


class Issue(BaseModel):
    """An issue found during analysis."""

    message: str = Field(description="Description of the issue")
    line: Optional[int] = Field(default=None, description="Line number where issue occurs")
    line_end: Optional[int] = Field(default=None, description="End line for multi-line issues")
    snippet: Optional[str] = Field(default=None, description="Relevant text snippet")


class DimensionScore(BaseModel):
    """Score for a single analysis dimension."""

    score: int = Field(ge=0, le=100, description="Score from 0-100")
    issues: list[Issue] = Field(default_factory=list, description="List of issues found")
    suggestions: list[str] = Field(default_factory=list, description="Quick-fix suggestions")


class HeuristicAnalysis(BaseModel):
    """Results from heuristic analysis."""

    prompt_id: str
    overall_score: int = Field(ge=0, le=100)
    clarity: DimensionScore
    specificity: DimensionScore
    structure: DimensionScore
    completeness: DimensionScore
    output_format: DimensionScore
    guardrails: DimensionScore


class LLMAnalysisStatus(str, Enum):
    """Status of an LLM analysis job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMAnalysis(BaseModel):
    """Results from LLM-powered analysis."""

    prompt_id: str
    status: LLMAnalysisStatus = LLMAnalysisStatus.PENDING
    ambiguities: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    injection_risks: list[str] = Field(default_factory=list)
    best_practice_issues: list[str] = Field(default_factory=list)
    suggested_revision: Optional[str] = None
    revision_explanation: Optional[str] = None
    error: Optional[str] = None


class ParsedFile(BaseModel):
    """A parsed markdown file with prompts."""

    filename: str
    prompts: list[Prompt]


class AnalysisRequest(BaseModel):
    """Request to analyze a prompt."""

    prompt_id: str


class SuggestionRequest(BaseModel):
    """Request to generate improvement suggestions."""

    prompt_id: str
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Specific areas to focus on (e.g., 'clarity', 'specificity')",
    )


class ExportRequest(BaseModel):
    """Request to export prompts to markdown."""

    prompt_ids: list[str] = Field(default_factory=list, description="IDs to export (empty = all)")
    include_analysis: bool = Field(default=False, description="Include analysis comments")

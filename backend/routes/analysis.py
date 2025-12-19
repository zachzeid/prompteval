"""API routes for prompt analysis."""

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.models.schemas import (
    AnalysisRequest,
    HeuristicAnalysis,
    LLMAnalysis,
    LLMAnalysisStatus,
    SuggestionRequest,
)
from backend.routes.prompts import _prompt_store
from backend.services.heuristics import analyze_prompt

router = APIRouter()

# In-memory storage for analysis results
_heuristic_results: dict[str, HeuristicAnalysis] = {}
_llm_results: dict[str, LLMAnalysis] = {}
_llm_jobs: dict[str, str] = {}  # job_id -> prompt_id


class HeuristicResponse(BaseModel):
    """Response containing heuristic analysis."""

    analysis: HeuristicAnalysis


class LLMJobResponse(BaseModel):
    """Response for LLM analysis job creation."""

    job_id: str
    status: LLMAnalysisStatus


class LLMStatusResponse(BaseModel):
    """Response for LLM analysis status check."""

    job_id: str
    status: LLMAnalysisStatus
    result: LLMAnalysis | None = None


class SuggestionResponse(BaseModel):
    """Response containing improvement suggestions."""

    original: str
    suggested: str
    explanation: str
    changes: list[dict[str, Any]]


@router.post("/heuristics", response_model=HeuristicResponse)
async def run_heuristic_analysis(request: AnalysisRequest) -> HeuristicResponse:
    """Run heuristic analysis on a prompt."""
    prompt_id = request.prompt_id

    if prompt_id not in _prompt_store:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = _prompt_store[prompt_id]
    analysis = analyze_prompt(prompt)

    # Cache the result
    _heuristic_results[prompt_id] = analysis

    return HeuristicResponse(analysis=analysis)


@router.get("/heuristics/{prompt_id}", response_model=HeuristicResponse)
async def get_heuristic_analysis(prompt_id: str) -> HeuristicResponse:
    """Get cached heuristic analysis for a prompt."""
    if prompt_id not in _heuristic_results:
        # Run analysis if not cached
        if prompt_id not in _prompt_store:
            raise HTTPException(status_code=404, detail="Prompt not found")
        prompt = _prompt_store[prompt_id]
        analysis = analyze_prompt(prompt)
        _heuristic_results[prompt_id] = analysis

    return HeuristicResponse(analysis=_heuristic_results[prompt_id])


async def _run_llm_analysis(job_id: str, prompt_id: str) -> None:
    """Background task to run LLM analysis."""
    from backend.services.llm import analyze_with_llm

    try:
        # Update status to running
        if prompt_id in _llm_results:
            _llm_results[prompt_id].status = LLMAnalysisStatus.RUNNING

        prompt = _prompt_store.get(prompt_id)
        if not prompt:
            _llm_results[prompt_id] = LLMAnalysis(
                prompt_id=prompt_id,
                status=LLMAnalysisStatus.FAILED,
                error="Prompt not found",
            )
            return

        # Run analysis
        result = await analyze_with_llm(prompt)
        result.status = LLMAnalysisStatus.COMPLETED
        _llm_results[prompt_id] = result

    except Exception as e:
        _llm_results[prompt_id] = LLMAnalysis(
            prompt_id=prompt_id,
            status=LLMAnalysisStatus.FAILED,
            error=str(e),
        )


@router.post("/llm", response_model=LLMJobResponse)
async def start_llm_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
) -> LLMJobResponse:
    """Start an async LLM analysis job."""
    prompt_id = request.prompt_id

    if prompt_id not in _prompt_store:
        raise HTTPException(status_code=404, detail="Prompt not found")

    job_id = str(uuid.uuid4())
    _llm_jobs[job_id] = prompt_id

    # Initialize pending result
    _llm_results[prompt_id] = LLMAnalysis(
        prompt_id=prompt_id,
        status=LLMAnalysisStatus.PENDING,
    )

    # Start background task
    background_tasks.add_task(_run_llm_analysis, job_id, prompt_id)

    return LLMJobResponse(job_id=job_id, status=LLMAnalysisStatus.PENDING)


@router.get("/llm/{job_id}/status", response_model=LLMStatusResponse)
async def get_llm_status(job_id: str) -> LLMStatusResponse:
    """Check the status of an LLM analysis job."""
    if job_id not in _llm_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    prompt_id = _llm_jobs[job_id]
    result = _llm_results.get(prompt_id)

    if not result:
        return LLMStatusResponse(job_id=job_id, status=LLMAnalysisStatus.PENDING)

    return LLMStatusResponse(
        job_id=job_id,
        status=result.status,
        result=result if result.status == LLMAnalysisStatus.COMPLETED else None,
    )


@router.get("/llm/{prompt_id}/result", response_model=LLMAnalysis)
async def get_llm_result(prompt_id: str) -> LLMAnalysis:
    """Get the LLM analysis result for a prompt."""
    if prompt_id not in _llm_results:
        raise HTTPException(status_code=404, detail="No LLM analysis found for this prompt")

    result = _llm_results[prompt_id]
    if result.status != LLMAnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not complete. Status: {result.status}",
        )

    return result


@router.post("/suggestions", response_model=SuggestionResponse)
async def generate_suggestions(request: SuggestionRequest) -> SuggestionResponse:
    """Generate improvement suggestions for a prompt."""
    from backend.services.llm import generate_suggestions

    prompt_id = request.prompt_id

    if prompt_id not in _prompt_store:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = _prompt_store[prompt_id]

    # Get heuristic analysis if available for context
    heuristic = _heuristic_results.get(prompt_id)

    result = await generate_suggestions(prompt, heuristic, request.focus_areas)
    return result

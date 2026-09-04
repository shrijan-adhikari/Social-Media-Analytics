"""Pydantic schemas for the GET /api/v1/analysis/status endpoint (Correction 10)."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class PipelineDimensionStatus(BaseModel):
    """Execution status and latest activity for an analytical pipeline dimension."""

    status: str = Field(..., description="'ready', 'in_progress', 'none', or 'not_implemented'")
    is_available: bool = Field(..., description="True if real analysis records exist in database")
    records_count: int = 0
    latest_run_at: datetime | None = None
    pipeline_version: str | None = None
    notes: str | None = None


class SystemAnalysisStatusResponse(BaseModel):
    """Backend-wide readiness and execution status across all roadmap capabilities."""

    generated_at: datetime
    collection: PipelineDimensionStatus
    sentiment: PipelineDimensionStatus
    sarcasm: PipelineDimensionStatus
    trends: PipelineDimensionStatus
    network: PipelineDimensionStatus
    demographics: PipelineDimensionStatus
    emotion: PipelineDimensionStatus
    stance: PipelineDimensionStatus

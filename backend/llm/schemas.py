"""Pydantic schemas for structured LLM outputs in AI File Organizer.

Every LLM response is validated against these schemas before being trusted.
Schema violations trigger retry (max 3) then degrade to NEVER confidence mode.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ClassificationOutput(BaseModel):
    """Output schema for file classification tasks."""
    category: str = Field(..., description="Best-fit category ID from the taxonomy")
    document_type: str = Field(..., description="Human-readable document type (e.g., 'Legal Contract', 'Invoice')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    summary: str = Field(default="", description="One-sentence summary of the file content")
    keywords: list[str] = Field(default_factory=list, description="3-5 key topics/entities")
    reasoning: str = Field(default="", description="Why this category was chosen")
    suggested_filename: str = Field(default="", description="Descriptive filename (preserve original extension)")


class QueryOutput(BaseModel):
    """Output schema for natural-language query interpretation."""
    filters: dict[str, str] = Field(default_factory=dict, description="Column -> value filters extracted from NL query")
    sort_by: str = Field(default="", description="Column to sort by")
    sort_order: str = Field(default="DESC", pattern="^(ASC|DESC)$")
    limit: int = Field(default=50, ge=1, le=500)
    explanation: str = Field(default="", description="How the query was interpreted")


class AudioTranscriptionOutput(BaseModel):
    """Output schema for audio transcription tasks."""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(default="en", description="Detected language code")
    segments: list[dict] = Field(default_factory=list, description="Timestamped segments")
    duration_seconds: float = Field(default=0.0, description="Audio duration")


class SummaryOutput(BaseModel):
    """Output schema for content summarization tasks."""
    title: str = Field(default="", description="Document title")
    summary: str = Field(..., description="Concise summary")
    key_points: list[str] = Field(default_factory=list, description="3-5 bullet points")
    category_hint: str = Field(default="", description="Suggested taxonomy category")

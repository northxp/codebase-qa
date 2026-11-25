"""Pydantic schemas for the /ask API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    repo: str = Field(..., description="Repository name, e.g. 'psf/requests'")
    question: str = Field(..., min_length=3, description="The natural-language question")
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to retrieve")


class RetrievedChunk(BaseModel):
    path: str
    start_line: int
    end_line: int
    text: str
    similarity: float = Field(..., description="Cosine similarity, 0.0 to 1.0")


class AskResponse(BaseModel):
    repo: str
    question: str
    chunks: list[RetrievedChunk]

# Add to app/api/models.py
class AskResponseWithLLM(AskResponse):
    answer: str
    valid_citations: list[str]
    invalid_citations: list[str]

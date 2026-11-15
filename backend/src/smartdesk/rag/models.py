from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    title: str
    domain: str
    source: str
    version: str
    effective_date: str
    access_scope: str = "employees"
    synthetic: bool = False
    review_status: str
    text: str = Field(min_length=20)


Chunk = dict[str, Any]


@dataclass(frozen=True)
class Passage:
    id: str
    title: str
    text: str
    source: str
    score: float = 0.0


@dataclass(frozen=True)
class Embedding:
    dense: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


class Claim(BaseModel):
    text: str
    citation_ids: list[str]


class GroundedAnswer(BaseModel):
    answerable: bool
    claims: list[Claim]


class EvidenceVerdict(BaseModel):
    supported: bool
    reason: str


class Citation(BaseModel):
    id: str
    title: str
    excerpt: str
    source: str


class AnswerResult(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)

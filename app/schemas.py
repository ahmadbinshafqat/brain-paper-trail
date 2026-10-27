from datetime import datetime
from pydantic import BaseModel, Field


class TextAnalyzeRequest(BaseModel):
    title: str = Field(default="Pasted text", max_length=200)
    text: str = Field(min_length=1)
    top_n: int | None = Field(default=None, ge=1, le=50)


class SentenceResult(BaseModel):
    id: int
    text: str
    score: float
    position: int
    is_selected: bool


class AnalyzeResponse(BaseModel):
    document_id: int
    title: str
    source_type: str
    created_at: datetime
    sentences: list[SentenceResult]


class DocumentSummary(BaseModel):
    id: int
    title: str
    source_type: str
    created_at: datetime
    sentence_count: int

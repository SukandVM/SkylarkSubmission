from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    query: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    answer: str
    data_quality_notes: list[str] = []
    sources: list[str] = []
    clarifying_question: Optional[str] = None


class BoardItem(BaseModel):
    id: str
    name: str
    column_values: dict
    board_id: Optional[str] = None


class BoardSummary(BaseModel):
    id: str
    name: str
    item_count: int
    columns: list[dict]


class DataQualityReport(BaseModel):
    board: str
    total_rows: int
    columns: list[dict]
    null_summary: dict
    issues: list[str]

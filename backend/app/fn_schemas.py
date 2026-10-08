"""Response models shared by the function-level endpoints (Build 4.5)."""
from pydantic import BaseModel


class FunctionMatch(BaseModel):
    path: str
    qualname: str
    kind: str
    start_line: int
    end_line: int
    score: float
    confidence: str
    reasons: list[str]
    snippet: str


class FunctionChange(BaseModel):
    entity: str
    property: str
    old_value: str
    new_value: str
    matches: list[FunctionMatch]        # medium / high confidence only
    weak_matches: list[FunctionMatch]   # low confidence, hidden behind a button in the UI


class FunctionResponse(BaseModel):
    project_id: int | None
    units_indexed: int
    changes: list[FunctionChange]
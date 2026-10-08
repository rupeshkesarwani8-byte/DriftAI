from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CodeFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class ProjectDetail(ProjectOut):
    files: list[CodeFileOut] = []


class UploadResult(BaseModel):
    saved: list[str]
    skipped: list[str]


# ---- Requirement drift ----
class DriftRequest(BaseModel):
    old_text: str = Field(min_length=1, max_length=20000)
    new_text: str = Field(min_length=1, max_length=20000)


class DriftChange(BaseModel):
    type: str  # value_change | added | removed | modified
    entity: str
    property: str
    old_value: str | None = None
    new_value: str | None = None
    old_sentence: str | None = None
    new_sentence: str | None = None


class DriftResponse(BaseModel):
    changes: list[DriftChange]
    count: int


# ---- Impact analysis ----
class ImpactRequest(BaseModel):
    old_text: str = Field(min_length=1, max_length=20000)
    new_text: str = Field(min_length=1, max_length=20000)


class EvidenceLine(BaseModel):
    line: int
    text: str
    function: str | None = None
    matched: list[str]
    literal: str | None = None
    score: int


class FileImpact(BaseModel):
    path: str
    kind: str  # code | test | doc
    score: int
    evidence: list[EvidenceLine]


class ChangeImpact(BaseModel):
    change: DriftChange
    files: list[FileImpact]


class ImpactResponse(BaseModel):
    project_id: int
    changes: list[ChangeImpact]
    total_files: int


# ---- Action plan, confidence, risk ----
class PlanItem(BaseModel):
    order: int
    kind: str  # code | test | doc | manual | run
    text: str
    path: str | None = None
    line: int | None = None
    function: str | None = None
    evidence: str | None = None
    change_index: int | None = None
    key: str | None = None
    confidence: str | None = None  # high | medium | low
    reason: str | None = None


class Risk(BaseModel):
    score: int
    level: str  # low | medium | high
    reasons: list[str]


class AnalyzeResponse(BaseModel):
    analysis_id: int
    project_id: int
    changes: list[ChangeImpact]
    action_plan: list[PlanItem]
    risk: Risk
    total_files: int


# ---- Saved analyses (history) ----
class AnalysisSummary(BaseModel):
    id: int
    project_id: int
    project_name: str
    change_count: int
    file_count: int
    created_at: datetime


class AnalysisDetail(AnalysisSummary):
    old_text: str
    new_text: str
    changes: list[ChangeImpact]
    action_plan: list[PlanItem]
    risk: Risk | None = None  # older analyses have no risk
    total_files: int
    feedback: dict[str, str] = {}


# ---- Feedback ----
class FeedbackIn(BaseModel):
    item_key: str = Field(min_length=1, max_length=600)
    verdict: Literal["relevant", "not_relevant", "none"]
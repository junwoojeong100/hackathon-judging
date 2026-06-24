from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- Rubric ----------
class CriterionBase(BaseModel):
    key: str
    name: str
    description: str = ""
    weight: int = 0
    order: int = 0


class CriterionOut(CriterionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Judging ----------
class CriterionScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    criterion_key: str
    criterion_name: str
    score: float
    weight: int
    rationale: str


class JudgmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    overall_score: float
    base_score: float = 0.0
    azure_detected: bool = False
    azure_bonus: float = 0.0
    azure_signals: str = ""
    ms_stack_detected: bool = False
    ms_stack_bonus: float = 0.0
    ms_stack_signals: str = ""
    summary: str
    model: str
    created_at: datetime
    scores: list[CriterionScoreOut] = []


# ---------- Submissions ----------
class SubmissionCreate(BaseModel):
    """Used for GitHub-URL submissions (JSON body)."""

    team_name: str
    project_name: str
    github_url: str
    stage: str = "interim"  # interim | final
    deployment_url: str = ""


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_name: str
    project_name: str
    source_type: str
    source_ref: str
    deployment_url: str = ""
    stage: str
    status: str
    error_message: str
    created_at: datetime
    latest_judgment: Optional[JudgmentOut] = None


# ---------- Leaderboard ----------
class LeaderboardEntry(BaseModel):
    rank: int
    submission_id: int
    team_name: str
    project_name: str
    overall_score: float
    status: str
    stage: str
    attempts: int
    azure_detected: bool = False
    ms_stack_detected: bool = False

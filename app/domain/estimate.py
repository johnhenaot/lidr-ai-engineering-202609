from typing import Literal

from pydantic import BaseModel


class EstimationError(Exception):
    pass


class TaskDraft(BaseModel):
    name: str
    optimistic: int
    likely: int
    pessimistic: int


class TeamMember(BaseModel):
    role: str
    quantity: int
    details: str


class Duration(BaseModel):
    floor: int
    ceiling: int
    unit: str


class Risk(BaseModel):
    label: str
    impact: Literal["low", "medium", "high"]
    detail: str


class HourlyRate(BaseModel):
    amount: float
    currency: str


class EstimateDraft(BaseModel):
    meeting_summary: str
    estimate_title: str
    assumptions: list[str]
    out_of_scope: list[str]
    tasks: list[TaskDraft]
    team: list[TeamMember]
    duration: Duration
    risks: list[Risk]
    confidence: Literal["Low", "Medium", "High"]
    confidence_rationale: str
    validity_days: int
    rate: HourlyRate | None = None

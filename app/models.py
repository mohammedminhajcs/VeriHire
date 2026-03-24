from typing import Any

from pydantic import BaseModel, Field


class ResumeRequest(BaseModel):
    """Input payload for resume-based question generation."""

    resume_text: str = Field(..., min_length=20)


class QuestionsResponse(BaseModel):
    """Generated questions returned to the frontend."""

    questions: list[str]


class AnswerRequest(BaseModel):
    """Input payload for answer evaluation and optional behavior metadata."""

    question: str
    answer: str
    elapsed_seconds: float | None = None


class AnswerEvaluationResponse(BaseModel):
    """Structured answer evaluation output."""

    score: int
    strengths: str
    weaknesses: str
    feedback: str


class CodeRunRequest(BaseModel):
    """Input payload for the coding sandbox."""

    code: str
    elapsed_seconds: float | None = None


class CodeRunResponse(BaseModel):
    """Structured coding execution result."""

    passed: int
    total: int
    score: float
    errors: str | None = None
    problem: str


class BehaviorEventRequest(BaseModel):
    """Frontend behavior events used for cheating detection."""

    event_type: str
    details: dict[str, Any] | None = None


class ReportResponse(BaseModel):
    """Final end-to-end candidate report."""

    overall_score: float
    interview_score: float
    coding_score: float
    behavior_score: float
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str
    extracted_skills: list[str]
    interview_feedback: list[dict[str, Any]]
    coding_result: dict[str, Any] | None = None
    behavior_flags: list[str]
    behavior_breakdown: dict[str, Any]
    resume_source: str

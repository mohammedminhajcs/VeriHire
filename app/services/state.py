from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass
class CandidateSession:
    """Stores all mutable state for the current demo session."""

    resume_text: str = ""
    resume_source: str = "text"
    extracted_skills: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    answers: list[dict[str, Any]] = field(default_factory=list)
    coding_result: dict[str, Any] | None = None
    coding_problem_index: int = 0
    behavior_events: list[dict[str, Any]] = field(default_factory=list)
    behavior_flags: list[str] = field(default_factory=list)
    submission_count: int = 0
    last_submission_time: float | None = None
    difficulty_level: str = "medium"
    created_at: float = field(default_factory=time)

    # Resets the session for a fresh candidate flow.
    def reset(self, resume_text: str, extracted_skills: list[str], questions: list[str]) -> None:
        self.resume_text = resume_text
        self.resume_source = "text"
        self.extracted_skills = extracted_skills
        self.questions = questions
        self.answers = []
        self.coding_result = None
        self.coding_problem_index = 0
        self.behavior_events = []
        self.behavior_flags = []
        self.submission_count = 0
        self.last_submission_time = None
        self.difficulty_level = "medium"
        self.created_at = time()


session_state = CandidateSession()

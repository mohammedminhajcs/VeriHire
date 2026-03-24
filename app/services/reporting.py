from __future__ import annotations

from app.services.behavior import compute_behavior_breakdown, compute_behavior_score
from app.services.state import CandidateSession


# Generates a final report by combining interview, coding, and behavior scores.
def build_report(session: CandidateSession) -> dict[str, object]:
    interview_scores = [item["score"] for item in session.answers]
    interview_score = round(sum(interview_scores) / len(interview_scores), 2) if interview_scores else 0.0
    coding_score = float(session.coding_result["score"]) if session.coding_result else 0.0
    behavior_score = compute_behavior_score(session)
    behavior_breakdown = compute_behavior_breakdown(session)
    overall_score = round((interview_score * 0.5) + (coding_score * 0.35) + (behavior_score * 0.15), 2)

    strengths: list[str] = []
    weaknesses: list[str] = []

    if interview_score >= 70:
        strengths.append("Interview responses were consistently relevant")
    else:
        weaknesses.append("Interview answers need deeper technical detail")

    if coding_score >= 70:
        strengths.append("Coding implementation passed most test cases")
    else:
        weaknesses.append("Coding solution failed important test coverage")

    if behavior_score >= 85:
        strengths.append("Behavior during the session appeared reliable")
    else:
        weaknesses.append("Behavior signals suggest possible distractions or policy concerns")

    if overall_score > 75:
        recommendation = "Hire"
    elif overall_score >= 50:
        recommendation = "Maybe"
    else:
        recommendation = "Reject"

    return {
        "overall_score": overall_score,
        "interview_score": interview_score,
        "coding_score": coding_score,
        "behavior_score": behavior_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "extracted_skills": session.extracted_skills,
        "interview_feedback": session.answers,
        "coding_result": session.coding_result,
        "behavior_flags": session.behavior_flags,
        "behavior_breakdown": behavior_breakdown,
        "resume_source": session.resume_source,
    }

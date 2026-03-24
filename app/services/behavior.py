from __future__ import annotations

from time import time

from app.services.state import CandidateSession


# Records frontend behavior events and converts them into simple cheating flags.
def record_behavior_event(session: CandidateSession, event_type: str, details: dict | None = None) -> None:
    session.behavior_events.append(
        {
            "event_type": event_type,
            "details": details or {},
            "timestamp": time(),
        }
    )
    if event_type not in session.behavior_flags:
        session.behavior_flags.append(event_type)


# Tracks submission timing and flags suspiciously rapid responses.
def track_submission(session: CandidateSession, elapsed_seconds: float | None) -> None:
    now = time()
    session.submission_count += 1

    if elapsed_seconds is not None and elapsed_seconds < 5:
        if "rapid_submit" not in session.behavior_flags:
            session.behavior_flags.append("rapid_submit")

    if elapsed_seconds is None and session.last_submission_time is not None and (now - session.last_submission_time) < 3:
        if "rapid_submit" not in session.behavior_flags:
            session.behavior_flags.append("rapid_submit")

    session.last_submission_time = now


# Returns component-level behavior metrics and penalties used in final scoring.
def compute_behavior_breakdown(session: CandidateSession) -> dict[str, float | int]:
    tab_switch_count = sum(1 for event in session.behavior_events if event.get("event_type") == "tab_switch")
    copy_paste_events = [event for event in session.behavior_events if event.get("event_type") == "copy_paste"]
    paste_count = sum(1 for event in copy_paste_events if ((event.get("details") or {}).get("action") or "").lower() == "paste")
    copy_cut_count = sum(
        1
        for event in copy_paste_events
        if ((event.get("details") or {}).get("action") or "").lower() in {"copy", "cut"}
    )
    unknown_clipboard_count = max(0, len(copy_paste_events) - paste_count - copy_cut_count)
    rapid_submit_count = 1 if "rapid_submit" in session.behavior_flags else 0

    tab_penalty = min(tab_switch_count * 10, 40)
    clipboard_penalty = min((paste_count * 16) + (copy_cut_count * 8) + (unknown_clipboard_count * 10), 60)
    rapid_penalty = rapid_submit_count * 12
    high_submission_penalty = 5 if session.submission_count > 12 else 0

    return {
        "tab_switch_count": tab_switch_count,
        "paste_count": paste_count,
        "copy_cut_count": copy_cut_count,
        "rapid_submit_count": rapid_submit_count,
        "submission_count": session.submission_count,
        "tab_penalty": tab_penalty,
        "clipboard_penalty": clipboard_penalty,
        "rapid_penalty": rapid_penalty,
        "high_submission_penalty": high_submission_penalty,
        "total_penalty": tab_penalty + clipboard_penalty + rapid_penalty + high_submission_penalty,
    }


# Computes an aggregate behavior score from observed flags and submission patterns.
def compute_behavior_score(session: CandidateSession) -> float:
    score = 100.0
    breakdown = compute_behavior_breakdown(session)
    score -= float(breakdown["total_penalty"])
    return max(0.0, round(score, 2))

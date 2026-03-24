from __future__ import annotations

import math
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


REFERENCE_ANSWERS = {
    "python": "A strong answer explains Python data structures, performance tradeoffs, typing, APIs, testing, async behavior, and production reliability.",
    "javascript": "A strong answer covers scope, async event loop behavior, maintainable structure, API handling, and browser constraints.",
    "machine learning": "A strong answer covers metrics, validation, deployment readiness, drift, bias, retraining, and monitoring.",
    "data": "A strong answer explains SQL operations, pipeline design, data quality, observability, and business impact.",
    "cloud": "A strong answer covers deployment, scaling, security, containers, networking, and reliability tradeoffs.",
    "devops": "A strong answer covers testing, deployment gates, observability, rollback, version control, and automation.",
    "hr": "A strong answer is specific, structured, outcome-driven, reflective, and demonstrates communication and ownership.",
}


# Infers the domain of a question to choose a reference answer.
def classify_question(question: str) -> str:
    lowered = question.lower()
    for topic in ["python", "javascript", "machine learning", "sql", "etl", "docker", "cloud", "ci/cd", "version control", "teammate", "stakeholder"]:
        if topic in lowered:
            if topic in {"sql", "etl"}:
                return "data"
            if topic in {"docker"}:
                return "cloud"
            if topic in {"ci/cd", "version control"}:
                return "devops"
            if topic in {"teammate", "stakeholder"}:
                return "hr"
            return topic
    return "hr" if any(word in lowered for word in ["time", "conflict", "failure", "ownership"]) else "python"


# Builds a deterministic reference answer from the detected question category.
def build_reference_answer(question: str) -> str:
    category = classify_question(question)
    focus_terms = sorted(keyword_tokens(question))
    focus_text = ", ".join(focus_terms[:8]) if focus_terms else "the core concepts in the question"
    return f"{REFERENCE_ANSWERS[category]} The answer should directly address: {focus_text}."


# Tokenizes text into lowercase keywords for lightweight coverage scoring.
def keyword_tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z]{3,}", text.lower()) if token not in {"what", "when", "where", "that", "with", "this", "your"}}


# Computes semantic similarity using TF-IDF cosine similarity.
def semantic_similarity(question: str, reference: str, answer: str) -> float:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([question, reference, question + " " + reference, answer])
    scores = [
        cosine_similarity(matrix[0:1], matrix[3:4])[0][0],
        cosine_similarity(matrix[1:2], matrix[3:4])[0][0],
        cosine_similarity(matrix[2:3], matrix[3:4])[0][0],
    ]
    question_terms = keyword_tokens(question)
    answer_terms = keyword_tokens(answer)
    overlap_score = len(question_terms & answer_terms) / max(1, len(question_terms))
    score = max(scores + [overlap_score])
    return max(0.0, min(1.0, float(score)))


# Scores answer clarity with simple structure and readability heuristics.
def clarity_score(answer: str) -> float:
    word_count = len(answer.split())
    sentence_count = max(1, len(re.findall(r"[.!?]", answer)))
    length_score = min(word_count / 45, 1.0)
    structure_score = min(sentence_count / 2, 1.0)
    unique_ratio = len(set(answer.lower().split())) / max(1, word_count)
    return max(0.0, min((length_score * 0.45) + (structure_score * 0.35) + (unique_ratio * 0.20), 1.0))


# Evaluates the answer using similarity, keyword coverage, and clarity weighting.
def evaluate_answer(question: str, answer: str) -> dict[str, object]:
    reference = build_reference_answer(question)
    similarity = semantic_similarity(question, reference, answer)
    reference_keywords = keyword_tokens(question + " " + reference)
    answer_keywords = keyword_tokens(answer)
    coverage = len(reference_keywords & answer_keywords) / max(1, len(reference_keywords))
    clarity = clarity_score(answer)

    weighted_score = (similarity * 0.50) + (coverage * 0.30) + (clarity * 0.20)
    score = int(round(weighted_score * 100))

    strengths: list[str] = []
    weaknesses: list[str] = []

    if similarity >= 0.45:
        strengths.append("Relevant to the question")
    else:
        weaknesses.append("Needs stronger relevance to the asked topic")

    if coverage >= 0.35:
        strengths.append("Covers important technical keywords")
    else:
        weaknesses.append("Misses important concepts expected in a strong answer")

    if clarity >= 0.45:
        strengths.append("Reasonably clear and structured")
    else:
        weaknesses.append("Could be clearer and more structured")

    if not strengths:
        strengths.append("Shows some attempt to answer the prompt")
    if not weaknesses:
        weaknesses.append("Could include more implementation detail and examples")

    feedback = (
        f"Reference alignment: {math.floor(similarity * 100)}%. "
        f"Keyword coverage: {math.floor(coverage * 100)}%. "
        f"Clarity: {math.floor(clarity * 100)}%. "
        "Improve by adding concrete examples, tradeoffs, and clearer structure."
    )

    return {
        "score": score,
        "strengths": "; ".join(strengths),
        "weaknesses": "; ".join(weaknesses),
        "feedback": feedback,
    }

from __future__ import annotations

from collections import Counter
import re
from typing import Iterable

import numpy as np


KNOWN_SKILLS = {
    "python": ["python", "pandas", "numpy", "fastapi", "django", "flask"],
    "javascript": ["javascript", "typescript", "node", "react", "frontend"],
    "machine learning": ["machine learning", "ml", "scikit", "tensorflow", "pytorch"],
    "data": ["sql", "mysql", "postgres", "database", "etl", "analytics", "dashboard"],
    "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "cloud"],
    "devops": ["ci/cd", "git", "monitoring", "deployment", "devops"],
}


SKILL_PROFILES = {
    "python": "Python programming, backend APIs, FastAPI, Flask, Django, pandas, numpy, scripting",
    "javascript": "JavaScript web development, frontend, HTML, CSS, browser UI, TypeScript, Node",
    "machine learning": "machine learning, AI models, scikit-learn, tensorflow, pytorch, model training",
    "data": "databases, SQL, MySQL, PostgreSQL, data modeling, analytics, ETL, reporting",
    "cloud": "cloud platforms, deployment, Docker, Kubernetes, AWS, Azure, GCP, scalability",
    "devops": "Git, CI CD, DevOps, monitoring, release pipelines, automation, version control",
}


_EMBED_MODEL = None


# Loads a local embedding model when available. If unavailable, returns None and rule-based logic remains active.
def _get_embedding_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    try:
        from sentence_transformers import SentenceTransformer

        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        return _EMBED_MODEL
    except Exception:
        _EMBED_MODEL = False
        return None


# Splits resume text into semantically useful short chunks for embedding similarity.
def _resume_chunks(resume_text: str) -> list[str]:
    raw_lines = [line.strip(" -*\t") for line in resume_text.splitlines()]
    lines = [line for line in raw_lines if len(line) >= 8]
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", resume_text) if len(s.strip()) >= 12]
    merged = lines + sentences
    deduped = []
    seen: set[str] = set()
    for item in merged:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(item)
    return deduped[:80]


# Computes rule-based weighted skill scores from explicit keyword occurrences.
def _rule_skill_scores(resume_text: str) -> Counter[str]:
    lowered = resume_text.lower()
    scores: Counter[str] = Counter()

    def keyword_count(text: str, keyword: str) -> int:
        escaped = re.escape(keyword.lower())
        pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
        return len(re.findall(pattern, text))

    for category, keywords in KNOWN_SKILLS.items():
        for keyword in keywords:
            count = keyword_count(lowered, keyword)
            if count:
                scores[category] += count
    return scores


# Computes semantic skill scores using local embeddings when available.
def _semantic_skill_scores(resume_text: str) -> Counter[str]:
    model = _get_embedding_model()
    if not model:
        return Counter()

    chunks = _resume_chunks(resume_text)
    if not chunks:
        return Counter()

    categories = list(SKILL_PROFILES.keys())
    profile_texts = [SKILL_PROFILES[key] for key in categories]

    try:
        chunk_embeddings = model.encode(chunks, normalize_embeddings=True)
        profile_embeddings = model.encode(profile_texts, normalize_embeddings=True)
    except Exception:
        return Counter()

    # Cosine similarity via dot product because embeddings are normalized.
    matrix = np.asarray(chunk_embeddings) @ np.asarray(profile_embeddings).T
    semantic_scores: Counter[str] = Counter()

    for idx, category in enumerate(categories):
        column = matrix[:, idx]
        max_similarity = float(np.max(column)) if len(column) else 0.0
        strong_hits = int(np.sum(column >= 0.52))
        moderate_hits = int(np.sum(column >= 0.44))
        if max_similarity >= 0.38:
            semantic_scores[category] += round((max_similarity * 3.2) + (strong_hits * 0.9) + (moderate_hits * 0.35), 3)

    return semantic_scores


# Merges rule and semantic skill evidence into a ranked skill list.
def _rank_skills(rule_scores: Counter[str], semantic_scores: Counter[str]) -> list[str]:
    merged: Counter[str] = Counter()
    categories: Iterable[str] = set(rule_scores.keys()) | set(semantic_scores.keys())
    for category in categories:
        merged[category] = float(rule_scores.get(category, 0)) * 1.25 + float(semantic_scores.get(category, 0)) * 1.75

    if not merged:
        return []
    return [skill for skill, _ in merged.most_common()]


QUESTION_BANK = {
    "python": {
        "easy": "Explain Python lists and tuples and when you would choose each.",
        "medium": "How does FastAPI use type hints and dependency injection in production APIs?",
        "hard": "Describe how you would optimize a Python service suffering from CPU and I/O bottlenecks.",
    },
    "javascript": {
        "easy": "What is the difference between var, let, and const in JavaScript?",
        "medium": "How would you structure a maintainable frontend that fetches API data without a framework?",
        "hard": "Explain event loop behavior and common async performance pitfalls in JavaScript applications.",
    },
    "machine learning": {
        "easy": "What is the difference between training and inference in machine learning?",
        "medium": "How would you evaluate whether a classification model is ready for production?",
        "hard": "Describe how you would detect drift and retrain a machine learning model safely in production.",
    },
    "data": {
        "easy": "What is a SQL join and when would you use one?",
        "medium": "How would you design a MySQL table for student records and what indexes would you add?",
        "hard": "Explain how you would improve data quality and observability in a reporting pipeline.",
    },
    "cloud": {
        "easy": "What problem does Docker solve for application deployment?",
        "medium": "How would you deploy a FastAPI app reliably on a cloud platform?",
        "hard": "Describe a secure cloud architecture for an AI service handling candidate data.",
    },
    "devops": {
        "easy": "Why is version control important in team-based software development?",
        "medium": "What should a CI/CD pipeline validate before deploying an API service?",
        "hard": "How would you design rollback and monitoring strategies for a critical release?",
    },
}


HR_QUESTIONS = [
    "Tell me about a time you resolved a conflict with a teammate under pressure.",
    "How do you prioritize tasks when multiple stakeholders need urgent results?",
    "Describe a failure in a recent project and what you changed afterward.",
    "What does strong ownership look like for you in a cross-functional team?",
]


GENERAL_TECH_QUESTIONS = {
    "easy": [
        "How do you debug a bug in a small web application step by step?",
        "What does good code readability mean to you in team projects?",
    ],
    "medium": [
        "How would you break a small web project into frontend, backend, and database responsibilities?",
        "What tradeoffs do you consider when choosing APIs and database queries for performance?",
    ],
    "hard": [
        "How would you design observability for a production web app handling sudden traffic spikes?",
        "What architecture changes would you make when a monolith needs to scale across teams?",
    ],
}


# Extracts skills by scanning resume text for known keywords and ranking them by frequency.
def extract_skills(resume_text: str) -> list[str]:
    rule_scores = _rule_skill_scores(resume_text)
    semantic_scores = _semantic_skill_scores(resume_text)
    ranked = _rank_skills(rule_scores, semantic_scores)

    if not ranked:
        return ["python", "javascript", "machine learning"]

    return ranked[:4]


# Infers an initial interview difficulty from resume seniority signals.
def infer_initial_difficulty(resume_text: str) -> str:
    lowered = resume_text.lower()
    junior_signals = [
        "student",
        "entry-level",
        "fresher",
        "intern",
        "internship",
        "b.tech",
        "undergraduate",
        "looking for an entry-level role",
    ]
    senior_signals = [
        "senior",
        "lead",
        "staff",
        "principal",
        "architect",
        "10 years",
        "8 years",
        "7 years",
        "6 years",
        "5 years",
    ]

    if any(signal in lowered for signal in junior_signals):
        return "easy"
    if any(signal in lowered for signal in senior_signals):
        return "hard"
    return "medium"


# Builds a 5-7 question interview set with mostly technical questions and some HR questions.
def generate_questions(skills: list[str], difficulty: str = "medium") -> list[str]:
    questions: list[str] = []
    technical_target = 5
    hr_target = 2

    for skill in skills:
        if skill in QUESTION_BANK and len(questions) < technical_target:
            questions.append(QUESTION_BANK[skill][difficulty])

    if len(questions) < technical_target:
        for candidate in GENERAL_TECH_QUESTIONS[difficulty]:
            if len(questions) >= technical_target:
                break
            if candidate not in questions:
                questions.append(candidate)

    questions.extend(HR_QUESTIONS[:hr_target])
    return questions[:7]


# Adapts question difficulty based on the running average score.
def adapt_questions(existing_questions: list[str], skills: list[str], average_score: float) -> list[str]:
    difficulty = "medium"
    if average_score > 70:
        difficulty = "hard"
    elif average_score < 40:
        difficulty = "easy"

    updated = generate_questions(skills, difficulty)
    if len(existing_questions) > len(updated):
        return existing_questions
    return updated

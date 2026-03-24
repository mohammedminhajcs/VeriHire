# AI Interviewer + Skill Evaluator

Demo-ready FastAPI application for resume-based interview generation, answer scoring, coding assessment, cheating detection, and final candidate reporting.

## Features

- Resume skill extraction with question generation
- Resume input via pasted text or uploaded PDF
- Adaptive technical and HR interview flow
- TF-IDF based semantic answer evaluation with feedback
- Restricted Python coding test runner with timeout
- Cheating detection from browser behavior and submission timing (tab switches, copy/cut/paste, rapid submit)
- Final report with hiring recommendation
- Plain HTML, CSS, and JavaScript frontend

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Optional AI Upgrade (Better Skill Extraction)

The app already works without external APIs. To enable local semantic extraction with sentence-transformers:

```bash
pip install -r requirements-ai.txt
```

Notes:
- This is optional and falls back automatically to rule-based extraction if not installed.
- First run may download a local model (`all-MiniLM-L6-v2`).

## Optional OCR Upgrade (Scanned PDF Resume Support)

For image-only/scanned resumes, install OCR dependencies:

```bash
pip install -r requirements-ocr.txt
```

Notes:
- If OCR dependencies are missing, the app still supports text-based PDFs.
- OCR fallback runs automatically when PDF text extraction is too short.

## Sample Resume

```text
John Doe is a Python developer with 4 years of experience building FastAPI services,
machine learning pipelines, SQL dashboards, and JavaScript frontends. He has worked with
Docker, Git, REST APIs, pandas, scikit-learn, and cloud deployment. He enjoys mentoring,
cross-team collaboration, and solving production issues.
```

## Sample Interview Answers

1. FastAPI uses Python type hints for request and response validation, while dependency injection keeps authentication, database access, and shared services modular, testable, and easy to replace.
2. In plain JavaScript, I would separate API requests, state management, rendering, and event handling into small modules so the frontend stays maintainable without introducing a framework.
3. I would validate a classification model with precision, recall, business metrics, error analysis, representative test data, bias checks, monitoring, and a rollback plan before production release.
4. For an ETL pipeline, I would extract interview data from source systems, validate and transform it into clean analytics tables, then load it into reporting storage with logging and quality checks.
5. Reliable cloud deployment needs containerization, environment-specific configuration, health checks, autoscaling, observability, and CI/CD gates to reduce release risk.
6. I resolved a teammate conflict by clarifying the shared goal, listening to both concerns, agreeing on a narrower delivery plan, and following up until the deadline was met.
7. When multiple stakeholders need urgent results, I rank work by business impact, deadline risk, and dependencies, then communicate tradeoffs early so priorities stay explicit.

## Coding Problems

- Reverse a string
- Find factorial

## Smoke Test

```bash
d:/Project/New folder/.venv/Scripts/python.exe scripts/smoke_test.py
```

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import (
    AnswerEvaluationResponse,
    AnswerRequest,
    BehaviorEventRequest,
    CodeRunRequest,
    CodeRunResponse,
    QuestionsResponse,
    ReportResponse,
    ResumeRequest,
)
from app.services.behavior import record_behavior_event, track_submission
from app.services.coding import CODING_PROBLEMS, get_problem, run_code_against_problem
from app.services.evaluator import evaluate_answer
from app.services.pdf_parser import extract_text_with_source
from app.services.reporting import build_report
from app.services.resume_analyzer import adapt_questions, extract_skills, generate_questions, infer_initial_difficulty
from app.services.state import session_state


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend"

app = FastAPI(title="AI Interviewer + Skill Evaluator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


# Serves the resume upload page.
@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Serves the interview page.
@app.get("/interview", include_in_schema=False)
def interview_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "interview.html")


# Serves the coding page.
@app.get("/coding", include_in_schema=False)
def coding_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "coding.html")


# Serves the final report page.
@app.get("/report-page", include_in_schema=False)
def report_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "report.html")


# Generates questions from resume text and resets the candidate session.
@app.post("/generate-questions", response_model=QuestionsResponse)
def generate_questions_endpoint(payload: ResumeRequest) -> QuestionsResponse:
    skills = extract_skills(payload.resume_text)
    initial_difficulty = infer_initial_difficulty(payload.resume_text)
    questions = generate_questions(skills, initial_difficulty)
    session_state.reset(payload.resume_text, skills, questions)
    session_state.resume_source = "text"
    session_state.difficulty_level = initial_difficulty
    return QuestionsResponse(questions=questions)


# Generates questions from a PDF resume upload.
@app.post("/generate-questions-pdf", response_model=QuestionsResponse)
async def generate_questions_pdf_endpoint(file: UploadFile = File(...)) -> QuestionsResponse:
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        resume_text, source = extract_text_with_source(raw)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {error}") from error

    if len(resume_text.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="PDF text extraction returned too little content. Upload a text-based PDF or paste resume text.",
        )

    skills = extract_skills(resume_text)
    initial_difficulty = infer_initial_difficulty(resume_text)
    questions = generate_questions(skills, initial_difficulty)
    session_state.reset(resume_text, skills, questions)
    session_state.resume_source = source
    session_state.difficulty_level = initial_difficulty
    return QuestionsResponse(questions=questions)


# Evaluates one interview answer and updates adaptive question state.
@app.post("/evaluate-answer", response_model=AnswerEvaluationResponse)
def evaluate_answer_endpoint(payload: AnswerRequest) -> AnswerEvaluationResponse:
    result = evaluate_answer(payload.question, payload.answer)
    session_state.answers.append(
        {
            "question": payload.question,
            "answer": payload.answer,
            **result,
        }
    )
    track_submission(session_state, payload.elapsed_seconds)

    average_score = sum(item["score"] for item in session_state.answers) / len(session_state.answers)
    session_state.questions = adapt_questions(session_state.questions, session_state.extracted_skills, average_score)
    session_state.difficulty_level = "hard" if average_score > 70 else "easy" if average_score < 40 else "medium"

    return AnswerEvaluationResponse(**result)


# Executes the submitted Python solution against the current coding problem.
@app.post("/run-code", response_model=CodeRunResponse)
def run_code_endpoint(payload: CodeRunRequest) -> CodeRunResponse:
    result = run_code_against_problem(payload.code, session_state.coding_problem_index)
    session_state.coding_result = result
    track_submission(session_state, payload.elapsed_seconds)
    session_state.coding_problem_index = (session_state.coding_problem_index + 1) % len(CODING_PROBLEMS)
    return CodeRunResponse(**result)


# Records suspicious browser events such as tab switches and copy-paste actions.
@app.post("/behavior-event")
def behavior_event_endpoint(payload: BehaviorEventRequest) -> dict[str, object]:
    record_behavior_event(session_state, payload.event_type, payload.details)
    return {"status": "recorded", "flags": session_state.behavior_flags}


# Returns the final combined report for the current interview session.
@app.get("/report", response_model=ReportResponse)
def report_endpoint() -> ReportResponse:
    return ReportResponse(**build_report(session_state))


# Exposes demo metadata so the frontend can show the active coding problem and sample content.
@app.get("/demo-data")
def demo_data_endpoint() -> dict[str, object]:
    return {
        "sample_resume": (
            "John Doe is a Python developer with 4 years of experience building FastAPI services, "
            "machine learning pipelines, SQL dashboards, and JavaScript frontends. He has worked with "
            "Docker, Git, REST APIs, pandas, scikit-learn, and cloud deployment."
        ),
        "coding_problem": get_problem(session_state.coding_problem_index),
    }

from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


SAMPLE_RESUME = (
    "John Doe is a Python developer with 4 years of experience building FastAPI services, "
    "machine learning pipelines, SQL dashboards, and JavaScript frontends. He has worked with "
    "Docker, Git, REST APIs, pandas, scikit-learn, and cloud deployment."
)

SAMPLE_ANSWERS = [
    "FastAPI uses type hints for validation and dependency injection to keep authentication, database sessions, and shared services modular, testable, and production-ready.",
    "A maintainable plain JavaScript frontend should separate API calls, UI rendering, browser state, and events into small modules so data fetching stays easy to test and extend.",
    "A production-ready classification model should be evaluated with precision, recall, business metrics, representative validation data, error analysis, monitoring, and rollback planning.",
    "I would design the ETL pipeline by extracting raw interview analytics, validating and transforming the data into structured tables, then loading it into reporting storage with logging and quality checks.",
    "Reliable FastAPI cloud deployment should use containers, environment configuration, health checks, observability, autoscaling, secure networking, and CI/CD release gates.",
    "I resolved a conflict with a teammate by clarifying the goal, listening to both sides, agreeing on a smaller delivery plan, and following up until the release succeeded.",
    "I prioritize urgent stakeholder requests by ranking business impact, deadline risk, and dependencies, then I communicate tradeoffs clearly so everyone understands the order of work.",
]

REVERSE_STRING_CODE = """
def solve(value):
    return value[::-1]
"""


# Exercises the full application flow against the in-process FastAPI app.
def main() -> None:
    client = TestClient(app)

    questions_response = client.post("/generate-questions", json={"resume_text": SAMPLE_RESUME})
    questions_response.raise_for_status()
    questions = questions_response.json()["questions"]
    print("Generated questions:", len(questions))

    for question, answer in zip(questions, SAMPLE_ANSWERS):
        evaluation = client.post(
            "/evaluate-answer",
            json={"question": question, "answer": answer, "elapsed_seconds": 18},
        )
        evaluation.raise_for_status()
        print("Answer score:", evaluation.json()["score"])

    code_response = client.post("/run-code", json={"code": REVERSE_STRING_CODE, "elapsed_seconds": 40})
    code_response.raise_for_status()
    print("Coding result:", code_response.json())

    report_response = client.get("/report")
    report_response.raise_for_status()
    print("Final report:", report_response.json())


if __name__ == "__main__":
    main()
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile


CODING_PROBLEMS = [
    {
        "title": "Reverse a String",
        "prompt": "Write a function named solve that takes a string and returns the reversed string.",
        "function_name": "solve",
        "tests": [
            {"input": "hello", "expected": "olleh"},
            {"input": "Interview", "expected": "weivretnI"},
            {"input": "", "expected": ""},
        ],
    },
    {
        "title": "Factorial",
        "prompt": "Write a function named solve that takes a non-negative integer and returns its factorial.",
        "function_name": "solve",
        "tests": [
            {"input": 0, "expected": 1},
            {"input": 5, "expected": 120},
            {"input": 7, "expected": 5040},
        ],
    },
]


DISALLOWED_AST_NODES = (ast.Import, ast.ImportFrom, ast.With, ast.AsyncFunctionDef, ast.ClassDef, ast.Try)
DISALLOWED_NAMES = {"open", "exec", "eval", "compile", "input", "__import__", "globals", "locals", "os", "sys", "subprocess", "pathlib", "shutil"}


# Validates the submitted Python code against a small allowlist-oriented policy.
def validate_code(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return f"Syntax error: {error}"

    for node in ast.walk(tree):
        if isinstance(node, DISALLOWED_AST_NODES):
            return f"Disallowed syntax detected: {type(node).__name__}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in DISALLOWED_NAMES:
            return f"Disallowed function call detected: {node.func.id}"
        if isinstance(node, ast.Name) and node.id in DISALLOWED_NAMES:
            return f"Disallowed name detected: {node.id}"

    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if "solve" not in function_names:
        return "Submitted code must define a function named solve."
    return None


# Returns the next predefined coding problem for the candidate session.
def get_problem(problem_index: int) -> dict[str, object]:
    return CODING_PROBLEMS[problem_index % len(CODING_PROBLEMS)]


# Executes user code in a subprocess with timeout and serializable test inputs.
def run_code_against_problem(code: str, problem_index: int) -> dict[str, object]:
    validation_error = validate_code(code)
    problem = get_problem(problem_index)

    if validation_error:
        return {
            "passed": 0,
            "total": len(problem["tests"]),
            "score": 0.0,
            "errors": validation_error,
            "problem": problem["prompt"],
        }

    harness = (
        "import json\n\n"
        f"{code.strip()}\n\n"
        f"TESTS = {json.dumps(problem['tests'])}\n"
        "results = []\n"
        "for case in TESTS:\n"
        "    try:\n"
        "        outcome = solve(case['input'])\n"
        "        results.append({'passed': outcome == case['expected'], 'output': outcome})\n"
        "    except Exception as exc:\n"
        "        results.append({'passed': False, 'error': str(exc)})\n\n"
        "print(json.dumps(results))\n"
    )

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(harness)
        temp_path = handle.name

    try:
        completed = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "total": len(problem["tests"]),
            "score": 0.0,
            "errors": "Execution timed out after 3 seconds.",
            "problem": problem["prompt"],
        }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    if completed.returncode != 0:
        return {
            "passed": 0,
            "total": len(problem["tests"]),
            "score": 0.0,
            "errors": completed.stderr.strip() or "Unknown runtime error",
            "problem": problem["prompt"],
        }

    try:
        results = json.loads(completed.stdout.strip())
    except json.JSONDecodeError:
        return {
            "passed": 0,
            "total": len(problem["tests"]),
            "score": 0.0,
            "errors": "Failed to parse execution results.",
            "problem": problem["prompt"],
        }

    passed = sum(1 for item in results if item.get("passed"))
    total = len(problem["tests"])
    return {
        "passed": passed,
        "total": total,
        "score": round((passed / total) * 100, 2),
        "errors": None if passed == total else json.dumps(results),
        "problem": problem["prompt"],
    }

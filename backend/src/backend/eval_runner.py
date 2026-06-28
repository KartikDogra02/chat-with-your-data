import json
from decimal import Decimal
from numbers import Number
from pathlib import Path
from typing import Any

from backend.pipeline import answer_question

# Repo layout: <root>/backend/src/backend/eval_runner.py -> parents[3] == <root>
QUESTIONS_PATH = Path(__file__).resolve().parents[3] / "evals" / "questions.json"

# Tolerance for comparing money / aggregate floats against expected values.
FLOAT_TOLERANCE = 1e-6


def _normalize(value: Any) -> Any:
    """Make DB results comparable to JSON expectations.

    Postgres returns Decimal for SUM/aggregates and the JSON stores plain
    floats/ints, so coerce all numbers to float for comparison.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (Decimal, Number)):
        return float(value)
    return value


def _values_match(actual: Any, expected: Any) -> bool:
    actual = _normalize(actual)
    expected = _normalize(expected)

    if isinstance(actual, float) and isinstance(expected, float):
        return abs(actual - expected) <= FLOAT_TOLERANCE

    return actual == expected


def _rows_match(actual: list[list[Any]], expected: list[list[Any]]) -> bool:
    if len(actual) != len(expected):
        return False

    for actual_row, expected_row in zip(actual, expected):
        if len(actual_row) != len(expected_row):
            return False
        if not all(
            _values_match(a, e) for a, e in zip(actual_row, expected_row)
        ):
            return False

    return True


def run_evals() -> int:
    questions = json.loads(QUESTIONS_PATH.read_text())

    passed = 0
    for case in questions:
        case_id = case["id"]
        expected_rows = case["expected"]["rows"]

        try:
            answer = answer_question(case["question"])
            actual_rows = answer["rows"]
            ok = _rows_match(actual_rows, expected_rows)
        except Exception as error:  # noqa: BLE001 - eval should never crash mid-run
            print(f"FAIL  {case_id}  (error: {error})")
            continue

        if ok:
            passed += 1
            print(f"PASS  {case_id}")
        else:
            print(f"FAIL  {case_id}")
            print(f"      sql:      {answer['sql']}")
            print(f"      expected: {expected_rows}")
            print(f"      actual:   {actual_rows}")

    total = len(questions)
    print(f"\n{passed}/{total} passed")

    return 0 if passed == total else 1


def main() -> None:
    raise SystemExit(run_evals())


if __name__ == "__main__":
    main()

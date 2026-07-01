"""Offline validation of the eval question set.

No OpenAI, no database — just checks that evals/questions.json is well-formed
so a typo in the eval data fails fast in CI instead of mid-eval-run.
"""

import json
from pathlib import Path

# backend/tests/test_evals_schema.py -> parents[2] == repo root
QUESTIONS_PATH = Path(__file__).resolve().parents[2] / "evals" / "questions.json"

VALID_CATEGORIES = {"should_pass", "should_fail", "ambiguous"}

CASES = json.loads(QUESTIONS_PATH.read_text())


def test_questions_file_is_a_non_empty_list() -> None:
    assert isinstance(CASES, list)
    assert CASES


def test_every_case_has_core_fields() -> None:
    for case in CASES:
        assert isinstance(case.get("id"), str) and case["id"], case
        assert isinstance(case.get("question"), str) and case["question"], case
        assert case.get("category") in VALID_CATEGORIES, case


def test_ids_are_unique() -> None:
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids)), "duplicate case ids found"


def test_should_pass_cases_have_expected_rows() -> None:
    for case in CASES:
        if case["category"] != "should_pass":
            continue
        assert case.get("expected_behavior") == "answer", case
        expected = case.get("expected")
        assert isinstance(expected, dict), case
        assert isinstance(expected.get("columns"), list) and expected["columns"], case
        assert isinstance(expected.get("rows"), list) and expected["rows"], case


def test_should_fail_cases_declare_cannot_answer() -> None:
    for case in CASES:
        if case["category"] != "should_fail":
            continue
        assert case.get("expected_behavior") == "cannot_answer", case
        # A refusal case has nothing to compare rows against.
        assert "expected" not in case, case


def test_ambiguous_cases_expect_an_answer() -> None:
    for case in CASES:
        if case["category"] != "ambiguous":
            continue
        assert case.get("expected_behavior") == "answer", case


def test_all_categories_are_represented() -> None:
    present = {case["category"] for case in CASES}
    assert present == VALID_CATEGORIES

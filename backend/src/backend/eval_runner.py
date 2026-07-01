import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.judge import judge_answer
from backend.pipeline import answer_question
from backend.pricing import cost_usd

# Repo layout: <root>/backend/src/backend/eval_runner.py -> parents[3] == <root>
QUESTIONS_PATH = Path(__file__).resolve().parents[3] / "evals" / "questions.json"

# Tolerance for comparing money / aggregate floats against expected values.
FLOAT_TOLERANCE = 1e-6

CATEGORIES = ("should_pass", "should_fail", "ambiguous")


def _normalize(value: Any) -> Any:
    """Make DB results comparable to JSON expectations.

    Postgres returns Decimal for SUM/aggregates and the JSON stores plain
    floats/ints, so coerce all numbers to float for comparison.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float | Decimal):
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
        if not all(_values_match(a, e) for a, e in zip(actual_row, expected_row)):
            return False

    return True


def _percentile(values: list[float], p: float) -> float | None:
    """Linear-interpolated percentile (p in [0, 1]). None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _evaluate_case(case: dict, model: str | None, use_judge: bool) -> dict:
    category = case.get("category", "should_pass")
    question = case["question"]
    result: dict[str, Any] = {"id": case["id"], "category": category}

    try:
        answer = answer_question(question, model=model)
    except Exception as error:  # noqa: BLE001 - a single case must not abort the run
        result.update(ok=False, error=str(error), detail=f"error: {error}")
        return result

    metrics = answer["metrics"]
    refused = answer["refused"]
    result.update(
        refused=refused,
        latency_ms=metrics["timings_ms"]["total"],
        cost_usd=metrics["cost_usd"],
        input_tokens=metrics["input_tokens"],
        output_tokens=metrics["output_tokens"],
    )

    if category == "should_fail":
        ok = refused
        result["detail"] = (
            "correctly refused"
            if refused
            else f"answered anyway: {answer['sql']}"
        )
    elif category == "ambiguous":
        ok = not refused
        result["detail"] = (
            answer["answer"] if not refused else "refused an answerable question"
        )
    else:  # should_pass
        if refused:
            ok = False
            result["detail"] = f"refused a valid question: {answer['answer']}"
        else:
            ok = _rows_match(answer["rows"], case["expected"]["rows"])
            result["detail"] = "rows match" if ok else "rows differ"
            if not ok:
                result["expected_rows"] = case["expected"]["rows"]
                result["actual_rows"] = answer["rows"]
                result["sql"] = answer["sql"]

    result["ok"] = ok

    # Prose judge: only where an answer was actually produced from data.
    if use_judge and not refused and category in ("should_pass", "ambiguous"):
        correct, reason, usage = judge_answer(
            question=question,
            columns=answer["columns"],
            rows=answer["rows"],
            answer=answer["answer"],
            model=model,
        )
        result["judge_correct"] = correct
        result["judge_reason"] = reason
        if result["cost_usd"] is not None:
            judge_cost = cost_usd(
                metrics["model"], usage.input_tokens, usage.output_tokens
            )
            if judge_cost is not None:
                result["cost_usd"] += judge_cost
        result["input_tokens"] += usage.input_tokens
        result["output_tokens"] += usage.output_tokens

    return result


def _print_summary(results: list[dict], resolved_model: str, use_judge: bool) -> None:
    by_category = {c: [r for r in results if r["category"] == c] for c in CATEGORIES}

    print("\n" + "=" * 60)
    print(f"Model: {resolved_model}")
    print("=" * 60)

    for category in CATEGORIES:
        rows = by_category[category]
        if not rows:
            continue
        passed = sum(1 for r in rows if r["ok"])
        label = {
            "should_pass": "should_pass (exact-row match)",
            "should_fail": "should_fail (correctly refused)",
            "ambiguous": "ambiguous   (produced an answer)",
        }[category]
        print(f"  {label}: {passed}/{len(rows)}")

    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
    costs = [r["cost_usd"] for r in results if r.get("cost_usd") is not None]
    in_tokens = sum(r.get("input_tokens", 0) for r in results)
    out_tokens = sum(r.get("output_tokens", 0) for r in results)

    if latencies:
        p50 = _percentile(latencies, 0.50)
        p95 = _percentile(latencies, 0.95)
        print(f"\n  Latency: p50 {p50:.0f}ms | p95 {p95:.0f}ms "
              f"(over {len(latencies)} cases)")
    if costs:
        avg_cost = sum(costs) / len(costs)
        print(f"  Cost:    avg ~${avg_cost:.5f}/query | "
              f"total ~${sum(costs):.4f} over {len(costs)} priced cases")
    print(f"  Tokens:  {in_tokens} in + {out_tokens} out")

    if use_judge:
        judged = [r for r in results if "judge_correct" in r]
        if judged:
            judge_passed = sum(1 for r in judged if r["judge_correct"])
            print(f"  Judge:   {judge_passed}/{len(judged)} answers judged faithful")

    total_passed = sum(1 for r in results if r["ok"])
    print(f"\n  Overall: {total_passed}/{len(results)} cases passed")
    print("=" * 60)


def run_evals(
    model: str | None = None,
    categories: list[str] | None = None,
    use_judge: bool = False,
) -> int:
    cases = json.loads(QUESTIONS_PATH.read_text())
    if categories:
        cases = [c for c in cases if c.get("category", "should_pass") in categories]

    resolved_model = model or get_settings().openai_model
    results: list[dict] = []

    for case in cases:
        result = _evaluate_case(case, model, use_judge)
        results.append(result)

        mark = "PASS" if result["ok"] else "FAIL"
        latency = (
            f"{result['latency_ms']:.0f}ms"
            if result.get("latency_ms") is not None
            else "  --  "
        )
        cost = (
            f"${result['cost_usd']:.5f}"
            if result.get("cost_usd") is not None
            else "   --   "
        )
        judge = ""
        if "judge_correct" in result:
            judge = "  judge:pass" if result["judge_correct"] else "  judge:FAIL"
        print(
            f"{mark}  {result['id']:<26} [{result['category']:<11}] "
            f"{latency:>7} {cost:>9}  {result['detail']}{judge}"
        )
        if not result["ok"] and "expected_rows" in result:
            print(f"      sql:      {result['sql']}")
            print(f"      expected: {result['expected_rows']}")
            print(f"      actual:   {result['actual_rows']}")

    _print_summary(results, resolved_model, use_judge)

    return 0 if all(r["ok"] for r in results) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the eval set against a model.")
    parser.add_argument(
        "--model",
        default=None,
        help="Model to run against (default: OPENAI_MODEL from settings).",
    )
    parser.add_argument(
        "--category",
        action="append",
        choices=CATEGORIES,
        help="Only run this category (repeatable). Default: all.",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Also run the LLM prose judge on answered cases (extra cost).",
    )
    args = parser.parse_args()

    raise SystemExit(
        run_evals(model=args.model, categories=args.category, use_judge=args.judge)
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path

from researchsensei.direction.exploration import build_heuristic_query_plan
from researchsensei.relevance import DeterministicRelevanceEvaluator
from researchsensei.schemas import CandidatePaper


DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "literature_relevance_benchmark.json"
)


def run_benchmark(fixture_path: Path) -> dict[str, object]:
    benchmark = json.loads(fixture_path.read_text(encoding="utf-8"))
    evaluator = DeterministicRelevanceEvaluator()
    case_results: list[dict[str, object]] = []
    candidate_checks = 0
    candidate_passes = 0

    for case in benchmark["cases"]:
        plan = build_heuristic_query_plan(str(case["query"]))
        requirements = evaluator.requirements(plan)
        failures: list[str] = []
        if set(requirements.required_concepts) != set(case["required_concepts"]):
            failures.append(
                "required_concepts:"
                f"expected={case['required_concepts']},actual={list(requirements.required_concepts)}"
            )
        if requirements.allow_survey is not case["allow_survey"]:
            failures.append(
                f"allow_survey:expected={case['allow_survey']},actual={requirements.allow_survey}"
            )

        for index, raw in enumerate(case["acceptable_candidates"]):
            candidate_checks += 1
            candidate = _candidate(str(case["id"]), index, raw)
            result = evaluator.evaluate_candidate(plan, candidate)
            if result.relevance_gate_passed:
                candidate_passes += 1
            else:
                failures.append(f"acceptable_rejected:{candidate.title}:{result.relevance_reason}")

        for index, raw in enumerate(case["unacceptable_candidates"]):
            candidate_checks += 1
            candidate = _candidate(str(case["id"]), index + 100, raw)
            result = evaluator.evaluate_candidate(plan, candidate)
            if not result.relevance_gate_passed:
                candidate_passes += 1
            else:
                failures.append(
                    f"unacceptable_accepted:{raw.get('failure', 'unspecified')}:{candidate.title}"
                )

        case_results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "status": "PASS" if not failures else "FAIL",
                "failures": failures,
            }
        )

    passed_cases = sum(1 for result in case_results if result["status"] == "PASS")
    case_count = len(case_results)
    pass_rate = passed_cases / case_count if case_count else 0.0
    required_rate = float(benchmark.get("minimum_case_pass_rate", 1.0))
    return {
        "schema_version": benchmark.get("schema_version", ""),
        "fixture": str(fixture_path),
        "offline": True,
        "case_count": case_count,
        "passed_cases": passed_cases,
        "failed_cases": case_count - passed_cases,
        "candidate_checks": candidate_checks,
        "candidate_expectations_met": candidate_passes,
        "pass_rate": round(pass_rate, 4),
        "required_pass_rate": required_rate,
        "verdict": "PASS" if case_count >= 20 and pass_rate >= required_rate else "FAIL",
        "cases": case_results,
    }


def _candidate(case_id: str, index: int, raw: dict[str, object]) -> CandidatePaper:
    return CandidatePaper(
        paper_id=f"{case_id}-{index}",
        title=str(raw["title"]),
        abstract=str(raw.get("abstract", "")),
        source="offline_fixture",
        sources=["offline_fixture"],
        source_confidence="high",
        metadata_confidence="high",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic offline literature discovery relevance benchmark.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Path to a literature_relevance_benchmark.v1 JSON fixture.",
    )
    parser.add_argument(
        "--show-passing-cases",
        action="store_true",
        help="Include passing case details in stdout.",
    )
    args = parser.parse_args()
    result = run_benchmark(args.fixture.resolve())
    if not args.show_passing_cases:
        cases = result.get("cases")
        if isinstance(cases, list):
            result["cases"] = [
                case
                for case in cases
                if isinstance(case, dict) and case.get("status") != "PASS"
            ]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

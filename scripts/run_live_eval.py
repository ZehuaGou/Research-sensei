from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from researchsensei.live_eval import LiveEvalConfig, run_full_live_eval  # noqa: E402


def main() -> int:
    config = LiveEvalConfig.from_env()
    report = run_full_live_eval(config=config)

    m1_status = report["m1_live"].get("status", "not_run")
    m2_status = report["m2_real_llm"].get("status", "not_run")
    e2e_status = report["real_pdf_e2e"].get("status", "not_run")

    print(json.dumps({
        "status": "completed",
        "report_path": report["report_path"],
        "m1_status": m1_status,
        "m2_status": m2_status,
        "real_pdf_e2e_status": e2e_status,
        "m1_failure_reason": report["m1_live"].get("failure_reason", ""),
        "m2_failure_reason": report["m2_real_llm"].get("failure_reason", ""),
        "real_pdf_e2e_failure_reason": report["real_pdf_e2e"].get("failure_reason", ""),
    }, ensure_ascii=False, indent=2))

    exit_code = 0

    # M1 live: if flags set but skipped, that's a failure
    if config.run_live_tests and m1_status == "skipped":
        print("ERROR: RUN_LIVE_TESTS=1 but M1 live was skipped.", file=sys.stderr)
        exit_code = max(exit_code, 2)
    elif m1_status == "failed":
        exit_code = max(exit_code, 2)

    # M2 real LLM: if flags set but skipped, that's a failure
    if config.run_llm_tests and m2_status == "skipped":
        print("ERROR: RUN_LLM_TESTS=1 but M2 real LLM was skipped.", file=sys.stderr)
        exit_code = max(exit_code, 3)
    elif config.run_llm_tests and m2_status == "failed":
        exit_code = max(exit_code, 3)

    # Real PDF e2e: if both flags set but skipped, that's a failure
    if config.run_live_tests and config.run_llm_tests and e2e_status == "skipped":
        print("ERROR: RUN_LIVE_TESTS=1 + RUN_LLM_TESTS=1 but real PDF e2e was skipped.", file=sys.stderr)
        exit_code = max(exit_code, 4)
    elif config.run_live_tests and config.run_llm_tests and e2e_status == "failed":
        exit_code = max(exit_code, 4)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

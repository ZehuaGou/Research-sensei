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

    print(json.dumps({
        "status": "completed",
        "report_path": report["report_path"],
        "m1_status": m1_status,
        "m1_failure_reason": report["m1_live"].get("failure_reason", ""),
        "real_llm_query_planning": report["m1_live"].get("real_llm_query_planning", False),
        "sources_success": report["m1_live"].get("sources_success", []),
        "candidate_count": report["m1_live"].get("candidate_count", 0),
        "pdf_download_success_count": report["m1_live"].get("pdf_download_success_count", 0),
        "a_read_count": report["m1_live"].get("a_read_count", 0),
    }, ensure_ascii=False, indent=2))

    exit_code = 0

    # M1 live: if flags set but skipped, that's a failure
    if config.run_live_tests and m1_status == "skipped":
        print("ERROR: RUN_LIVE_TESTS=1 but M1 live was skipped.", file=sys.stderr)
        exit_code = max(exit_code, 2)
    elif m1_status == "failed":
        exit_code = max(exit_code, 2)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

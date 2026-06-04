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
    print(json.dumps({
        "status": "completed",
        "report_path": report["report_path"],
        "m1_status": report["m1_live"].get("status"),
        "m2_status": report["m2_real_llm"].get("status"),
        "m1_failure_reason": report["m1_live"].get("failure_reason", ""),
        "m2_failure_reason": report["m2_real_llm"].get("failure_reason", ""),
    }, ensure_ascii=False, indent=2))
    if report["m1_live"].get("status") == "failed":
        return 2
    if config.run_llm_tests and report["m2_real_llm"].get("status") == "failed":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


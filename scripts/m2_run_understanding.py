"""Run M2 paper/formula understanding from an M1 artifact bundle."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from researchsensei.m2.artifact_reader import M1ArtifactReader  # noqa: E402
from researchsensei.m2.runner import run_m2_understanding  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run M2 understanding from M1 canonical artifacts.")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="M1 artifact directory containing canonical_paper.md, formula_slots.json, and related files.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Output directory. Defaults to reports/m2_understanding_<paper_id>.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        bundle = M1ArtifactReader(input_dir).load()
        paper_id = str(bundle.front_matter.get("paper_id") or bundle.paper_metadata.get("paper_id") or input_dir.name)
        output_dir = ROOT / "reports" / f"m2_understanding_{paper_id}"
    result = run_m2_understanding(input_dir=input_dir, output_dir=output_dir)
    print(f"M2 understanding written to: {output_dir}")
    print(f"Formula count: {result.run_summary['formula_count']}")
    print(f"Skipped formulas: {result.run_summary['skipped_formula_count']}")
    print(f"M1 artifacts modified: {result.run_summary['m1_artifacts_modified']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

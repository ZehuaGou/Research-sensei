"""Post-process MinerU2.5-Pro spike results.

Loads raw MinerU output from JSON and runs RuleBasedStructureRefiner,
LlamaSectionRefiner, formula extraction, canonical generation, and comparison.
"""
import json
import re
import sys
import time
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
PAPER_DIR = SPIKE_DIR.parent

# Import from the spike script
sys.path.insert(0, str(SPIKE_DIR))
from run_spike import (
    DocumentBlock,
    RuleBasedStructureRefiner,
    LlamaSectionRefiner,
    extract_formula_slots,
    generate_canonical_v2,
    generate_comparison,
)


def main():
    # Load already-parsed blocks
    blocks_path = SPIKE_DIR / "document_blocks.json"
    print(f"Loading blocks from {blocks_path}...")
    with open(blocks_path, "r", encoding="utf-8") as f:
        blocks_data = json.load(f)
    blocks = [DocumentBlock(**b) for b in blocks_data]
    print(f"Loaded {len(blocks)} blocks")

    # Load v1 slots for comparison
    v1_slots_path = PAPER_DIR.parent / "paper_4_unseen" / "formula_slots.json"
    # Try the old location first
    if not v1_slots_path.exists():
        v1_slots_path = Path("D:/Code/Python/Research-sensei/reports/m1_unseen_eval/paper_4_unseen/formula_slots.json")
    with open(v1_slots_path, "r", encoding="utf-8") as f:
        v1_slots = json.load(f)
    print(f"Loaded v1 slots: {len(v1_slots)}")

    # Apply RuleBasedStructureRefiner
    print("\nApplying RuleBasedStructureRefiner...")
    refiner = RuleBasedStructureRefiner()
    blocks = refiner.refine(blocks)

    # Try LlamaSectionRefiner
    print("\nChecking LlamaSectionRefiner...")
    llama = LlamaSectionRefiner()
    llama.check_availability()
    if llama.available:
        print("Applying LlamaSectionRefiner...")
        blocks = llama.refine(blocks)

    llama_status = {
        "available": llama.available,
        "model": llama.model,
        "base_url": llama.base_url,
        "json_valid_count": llama.json_valid_count,
        "json_invalid_count": llama.json_invalid_count,
    }

    # Extract formula slots
    v2_slots = extract_formula_slots(blocks)
    slots_path = SPIKE_DIR / "formula_slots_v2.json"
    with open(slots_path, "w", encoding="utf-8") as f:
        json.dump(v2_slots, f, indent=2, ensure_ascii=False)
    print(f"Saved v2 formula slots: {slots_path}")

    # Generate canonical paper
    canonical = generate_canonical_v2(blocks, v2_slots)
    canonical_path = SPIKE_DIR / "canonical_paper_v2.md"
    canonical_path.write_text(canonical, encoding="utf-8")
    print(f"Saved canonical paper: {canonical_path}")

    # Generate structure refine report
    refine_report = f"""# Structure Refine Report

Generated: {time.strftime('%Y-%m-%d %H:%M')}

## Pipeline

1. MinerU2.5-Pro (opendatalab/MinerU2.5-Pro-2604-1.2B) via mineru-vl-utils
2. RuleBasedStructureRefiner (always)
3. LlamaSectionRefiner (optional, {'applied' if llama.available and llama.json_valid_count > 0 else 'not available/not applied'})

## Block Statistics

- Total blocks: {len(blocks)}
- Formula blocks: {sum(1 for b in blocks if b.block_type == 'formula')}
- Title blocks: {sum(1 for b in blocks if b.block_type == 'title')}
- Text blocks: {sum(1 for b in blocks if b.block_type == 'text')}

## Section Distribution (after refinement)

"""
    section_counts: dict[str, int] = {}
    for b in blocks:
        section_counts[b.section] = section_counts.get(b.section, 0) + 1
    for sec, count in sorted(section_counts.items()):
        refine_report += f"- {sec}: {count}\n"

    formula_sections: dict[str, int] = {}
    for s in v2_slots:
        formula_sections[s.get("section", "Unknown")] = formula_sections.get(s.get("section", "Unknown"), 0) + 1
    refine_report += "\n## Formula Section Distribution\n\n"
    for sec, count in sorted(formula_sections.items()):
        refine_report += f"- {sec}: {count}\n"

    refine_report += f"""
## Risk Flags

- ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS: {sum(1 for b in blocks if 'ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS' in b.risk_flags)}
- SECTION_CONTRADICTION_POSSIBLE: {sum(1 for b in blocks if 'SECTION_CONTRADICTION_POSSIBLE' in b.risk_flags)}

## Llama Refiner Details

- Available: {llama.available}
- Model: {llama.model}
- JSON valid responses: {llama.json_valid_count}
- JSON invalid responses: {llama.json_invalid_count}
"""
    refine_path = SPIKE_DIR / "STRUCTURE_REFINE_REPORT.md"
    refine_path.write_text(refine_report, encoding="utf-8")
    print(f"Saved refine report: {refine_path}")

    # Generate comparison report
    stats = {"pages": 17, "total_blocks": len(blocks), "elapsed_seconds": 12496}
    comparison = generate_comparison(v1_slots, v2_slots, blocks, {"stats": stats}, stats, llama_status)
    compare_path = SPIKE_DIR / "COMPARE_V1_MARKER_VS_V2_MINERU.md"
    compare_path.write_text(comparison, encoding="utf-8")
    print(f"Saved comparison: {compare_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"v1 formulas: {len(v1_slots)}")
    print(f"v2 blocks: {len(blocks)}")
    print(f"v2 formula slots: {len(v2_slots)}")
    v2_sections = {}
    for s in v2_slots:
        v2_sections[s.get("section", "Unknown")] = v2_sections.get(s.get("section", "Unknown"), 0) + 1
    print(f"v2 formula sections: {v2_sections}")
    print(f"v2 latex: {sum(1 for s in v2_slots if s.get('mineru_latex'))}")
    print(f"v2 all_Abstract_suspicious: {sum(1 for s in v2_slots if 'ALL_FORMULAS_IN_ABSTRACT_SUSPICIOUS' in s.get('risk_flags', []))}")
    print(f"Llama available: {llama.available}")


if __name__ == "__main__":
    main()

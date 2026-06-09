# MinerU2.5-Pro v2 Spike Report

Generated: 2026-06-09 21:28

## Paper

- Title: MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection
- arXiv: 2312.02530
- PDF: D:\Code\Python\Research-sensei\reports\m1_unseen_eval\paper_4_unseen\source.pdf

## v1 Marker Results (ORIGINAL baseline — before section inference fix)

Source: git commit 6b49e01 (original Marker output, before nearby_text heading fix)
Formula count: 11
Section distribution:
- Abstract: 11

all_formulas_in_Abstract_suspicious: YES
section_contradiction_count: 0

## v2 MinerU2.5-Pro Results

Formula count: 11
Latex count: 11
Bbox count: 11

Section distribution:
- Experiments: 3
- Method: 8

all_formulas_in_Abstract_suspicious: NO
section_contradiction_count: 0
risk_flags_total: 0

Block type distribution:
- caption: 2
- figure: 39
- formula: 11
- reference: 45
- table: 18
- text: 103
- title: 29

## Runtime & Resources

- Backend: transformers (CPU)
- Model: opendatalab/MinerU2.5-Pro-2604-1.2B
- Pages: 17
- Total blocks: 247
- Elapsed: 12496s
- Blocks/page: N/A
- GPU: None (CPU only)
- VRAM: N/A

## Llama Refiner

- Available: True
- Model: llama3.2
- Base URL: http://localhost:11434/v1
- JSON valid: 0
- JSON invalid: 17
- Participated: NO

## Per-Formula Detail (v2)

| # | formula_id | page | section | latex_present | risk_flags |
|---|-----------|-----:|---------|:---:|---|
| 1 | formula_001 | 4 | Method | Y | — |
| 2 | formula_002 | 4 | Method | Y | — |
| 3 | formula_003 | 4 | Method | Y | — |
| 4 | formula_004 | 4 | Method | Y | — |
| 5 | formula_005 | 4 | Method | Y | — |
| 6 | formula_006 | 5 | Method | Y | — |
| 7 | formula_007 | 5 | Method | Y | — |
| 8 | formula_008 | 5 | Method | Y | — |
| 9 | formula_009 | 6 | Experiments | Y | — |
| 10 | formula_010 | 6 | Experiments | Y | — |
| 11 | formula_011 | 6 | Experiments | Y | — |

## Conclusion

v2 MinerU2.5-Pro FIXED the all-Abstract problem.
v1 had 11/11 formulas in Abstract.
v2 has 0/11 formulas in Abstract.

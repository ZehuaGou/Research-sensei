# M2.5 Full Pipeline And Understanding Gates

This document describes the M2 pipeline contract. Current status and evidence
live in `docs/STATUS.md`.

## Scope

M2 receives a selected paper or resolved full-text source and produces
evidence-backed understanding artifacts:

1. parsed document
2. passage index
3. claim evidence
4. evidence pack
5. paper skeleton/card
6. formula cards
7. teaching cards
8. quality report
9. understanding status

M2 is not a chatbot and does not implement M4 tutoring.

## Inputs

Supported inputs:

- selected canonical bundle;
- raw canonical markdown;
- arXiv source/e-print normalized to LaTeX-derived canonical content;
- PDF input;
- legal OA PDF from non-arXiv sources.

The pipeline must record source type and fallback path. arXiv source-derived
formulas may be marked `source_latex`. Raw/PDF-extracted formula text must not be
mislabelled as source LaTeX.

## Output Artifacts

Required artifact names for a completed run directory:

- `source_status.json`
- `parsed_document.json`
- `passage_index.json`
- `claim_evidence.json`
- `evidence_pack.json`
- `paper_card.json` when successful
- `formula_cards.json` when successful or structurally degraded
- `teaching_cards.json` when successful
- `quality_report.json`
- `understanding_status.json`

## Component Status

`understanding_status.json` must expose:

- top-level status;
- source type;
- canonicalization status;
- `m2_ready`;
- component status;
- allowed downstream components;
- missing components;
- degradation reason;
- warnings;
- quality report summary.

Valid user-facing statuses:

- SUCCESS
- DEGRADED_STRUCTURAL
- BLOCKED_UNDERSTANDING
- BASELINE_ONLY
- FAILED

## Cards Gating

- SUCCESS: `/cards=200`; paper, formula, and teaching cards should exist.
- DEGRADED_STRUCTURAL: `/cards=200`; only successful components are returned.
- BLOCKED_UNDERSTANDING: `/cards=403`.
- BASELINE_ONLY: `/cards=403`.
- FAILED: `/cards=403`.
- SUCCESS with missing required cards: `/cards=409`.

`/artifacts` remains debug/admin oriented and is not the normal UI data path.

## Formula Provenance And FSA-5

QualityAuditor/FSA-5 stays strict:

- `source_latex` plus evidence support may allow detailed formula explanation.
- `parser_latex`, OCR, or raw formula text must carry their true origin.
- `unknown` formula origin cannot produce detailed derivation.
- if formula provenance is weak but paper/teaching components are safe,
  DEGRADED_STRUCTURAL is allowed;
- if core method/evidence is missing, BLOCKED_UNDERSTANDING is required.

Do not fake formula origins or let the LLM overwrite evidence provenance.

## Known Status Boundaries

Selected-paper acceptance for `2310_08800v2` passed, but this is not broad M2
REAL_E2E. Raw/source handoff jobs can be SUCCESS, DEGRADED_STRUCTURAL, or
BLOCKED_UNDERSTANDING depending on evidence and provenance. That fail-closed
behavior is correct.

## Acceptance Command

```powershell
$env:RESEARCHSENSEI_ENABLE_API_LLM="1"
$env:RESEARCHSENSEI_LLM_PROVIDER="cc_switch"
.venv\Scripts\python.exe scripts\run_main_chain_acceptance.py --query "time series anomaly detection" --provider cc_switch
```

The acceptance command exercises M1 direction search, seed expansion, deep_read handoff,
M2 understanding status, and M3 `/cards` gating. It writes no report files.

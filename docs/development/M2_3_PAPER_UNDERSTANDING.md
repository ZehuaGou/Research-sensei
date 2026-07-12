# M2.3 Paper Understanding Contract

Current implementation evidence and test results live in `docs/STATUS.md`.
This document defines the maintained boundary between evidence extraction and
learner-facing cards.

## Purpose

M2.3 turns a verified paper/evidence bundle into compact Chinese learning
artifacts. It does not repair missing source material, invent experimental
results, or treat fluent prose as evidence.

## Input

- canonical paper metadata and stable source identity;
- passage index and claim-evidence records;
- formula slots with page/block/section provenance;
- parser and source-quality status;
- optional configured LLM client.

M2.3 may start only after the M1/M2 input contract has been checked. Missing or
contradictory provenance remains a gate failure; it is not filled with model
knowledge.

## Output

- `paper_card.json`: research problem, core idea, method mechanism, and
  evidence-backed conclusions;
- `formula_cards.json`: formula meaning, symbols, source expression, and safe
  derivation level;
- `teaching_cards.json`: learner-oriented explanations backed by the current
  paper;
- `understanding_status.json`: overall and per-component status;
- `quality_report.json`: audit evidence, warnings, and blocking reasons.

Every user-facing claim that requires source support carries a valid
`evidence_ref`. A claim must be supported by the text behind that ref; membership
in an allow-list alone is insufficient.

## Status Semantics

| Status | Meaning | User-facing cards |
|---|---|---|
| `SUCCESS` | Required card builders completed and quality/evidence gates passed. | Allowed. |
| `DEGRADED_STRUCTURAL` | Understanding passed, but a specifically named structural component is unavailable or intentionally limited. | Only passed components. |
| `BASELINE_ONLY` | Deterministic diagnostics ran without a real configured LLM understanding path. | Not accepted as live understanding. |
| `BLOCKED_UNDERSTANDING` | A required card builder, evidence gate, or source gate failed. | Fail closed. |
| `FAILED` | The pipeline could not produce a trustworthy understanding result. | Never. |

`DEGRADED_STRUCTURAL` must not hide a failed paper, formula, or teaching-card
builder. `BASELINE_ONLY` must not be renamed to success in API or UI layers.

## Paper Card Rules

- Separate research problem, proposed mechanism, and experimental conclusion.
- Preserve uncertainty when the source is ambiguous.
- Do not infer a named algorithm from broad topic words.
- Dataset, metric, threshold, percentage, and comparative claims require direct
  evidence.
- Survey papers must be represented as surveys; they cannot be presented as a
  new forecasting, imputation, anomaly-detection, clustering, graph, GNN, or
  diffusion method.

## Formula Card Rules

- Preserve `source_latex` only from the allowed parser/source path.
- Preserve formula origin, page/block/section identity, and surrounding method
  evidence.
- Unknown or weak origin cannot produce a detailed derivation.
- OCR text is not silently promoted to source LaTeX.
- FSA-5 remains a hard safety rule.
- A teaching toy example may use clearly fictional values only when the
  calculation rule is directly supported by the current paper.

## Teaching Card Rules

- Teaching text may simplify terminology but not change the method.
- A blocked component cannot be explained as though it passed.
- Examples must be marked as examples and must not look like reported paper
  results.
- Cross-paper or general-domain advice belongs outside this single-paper
  contract unless it is explicitly labeled and separately sourced.

## LLM Boundary

The LLM receives bounded, schema-specific evidence. Invalid JSON, missing
required fields, empty card output, unknown refs, or unsupported numerical
claims fail validation. The backend may return an explicit degraded/blocked
result; it must not coerce unsafe prose into a valid card.

## Acceptance

The maintained tests cover successful cards, missing evidence, builder failure,
formula provenance, FSA-5, `source_latex`, and fail-closed `/cards` behavior.
Exact commands and counts belong in `docs/STATUS.md`, not in this contract.

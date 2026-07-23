# Audit And Quality Contract

Current implementation evidence and test results live in `docs/STATUS.md`.
Quality Audit is the final trust boundary before cards become learner-facing.

## Audit Inputs

- parsed document and canonical source metadata;
- passage index, claim evidence, and evidence pack;
- paper, formula, and teaching cards;
- formula slots and provenance;
- component statuses and warnings;
- parser/source-resolution diagnostics.

## Audit Outputs

- machine-readable quality findings with stable codes;
- overall understanding status and component statuses;
- blocking reasons and non-blocking warnings;
- evidence and formula provenance summaries;
- safe-to-render decision consumed by `/cards` and Reader Workspace.

## Hard Gates

The following gates cannot be weakened or bypassed to make a test pass:

1. QualityAuditor must run on the produced artifacts.
2. Every required `evidence_ref` must exist and support its associated claim.
3. Formula Safety Audit rule FSA-5 remains strict.
4. `source_latex` is accepted only from an allowed source/provenance path.
5. `/cards` is fail-closed for `BASELINE_ONLY`,
   `BLOCKED_UNDERSTANDING`, and `FAILED`.
6. Paper Tutor receives only artifacts that passed the same user-facing boundary.

## Evidence Validation

Evidence validation has two distinct checks:

- binding: the ref exists in the current job's allowed evidence set;
- support: the text behind the ref actually supports the associated claim.

A valid ref attached to an unrelated paragraph fails the support check.
Formulae, thresholds, numbers, datasets, metrics, comparisons, and experimental
results require stricter textual alignment than a broad qualitative summary.
When support cannot be established, remove the claim or return a clear degraded
or blocked result.

## Formula Quality

The auditor checks formula origin, source expression, page/block/section
identity, surrounding method context, and derivation safety. In particular:

- OCR-only or reconstructed formulae remain labeled;
- missing crop/overlay/LaTeX provenance is not silently ignored;
- an unknown origin cannot produce a detailed derivation;
- all-formulas-in-Abstract, section contradiction, and missing
  latex/crop/overlay remain Literature Discovery/Paper Analysis gate failures;
- a display-friendly rendering must not alter the source expression.

## Status Decision

`SUCCESS` requires all core component builders and hard gates to pass.
`DEGRADED_STRUCTURAL` is allowed only for an explicitly named safe structural
limitation after the remaining understanding has passed. Core builder failure,
unknown evidence, or source contradiction produces `BLOCKED_UNDERSTANDING` or
`FAILED`, not partial success.

The API returns status before cards. Reader Workspace requests `/cards` only for an allowed
status and still handles a 403 gate response. Raw intermediate artifacts are
debug/admin material and must not be substituted for blocked cards.

## Audit Failure Handling

- Preserve the original failure code and affected component.
- Do not change expected assertions until the failure's root cause is known.
- Network, provider, or parser absence is recorded as an environment/external
  limitation when applicable.
- A skipped or mocked path is not live verification.
- An invalid source, DOI, arXiv ID, PDF-ready flag, evidence ref, or test result
  is never manufactured.

## Acceptance

Regression coverage must include evidence existence and support, unsupported
numerical claims, formula provenance, FSA-5, source-LaTeX boundaries, component
builder failures, and `/cards` fail-closed behavior. Exact test commands and
counts belong in `docs/STATUS.md`.

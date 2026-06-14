# ResearchSensei Status

Last updated: 2026-06-14

This file records real engineering status. Mock, fake, or skipped tests do not
count as module completion. Reports, downloaded PDFs, `.env`, API keys,
`.venv`, model weights, and generated bundles must not be committed.

## Status Levels

| Level | Meaning |
|---|---|
| NOT_STARTED | No implemented code and no usable design. |
| DOC_DESIGNED | Engineering contract is documented, but implementation is missing. |
| IMPLEMENTED | Code exists, but real validation may still be pending. |
| UNIT_TESTED | Unit or fixture tests exist. |
| REAL_E2E_VERIFIED | Real end-to-end validation has passed for the claimed scope. |
| PARTIAL_REAL_E2E_VERIFIED | Some modes or selected samples passed real validation; other modes remain pending. |
| PRODUCTION_READY | Stable enough for routine production use. No current module has this status. |

## Module Matrix

| Module | Area | Code Status | Test Status | Real Status | Notes |
|---|---|---|---|---|---|
| M1 | Focused acquisition | implemented | live tested | REAL_E2E_VERIFIED | Narrow-query acquisition, verification, relevance judge, source/download gate, and reading-plan path have real validation. |
| M1 | Source-aware acquisition | implemented | unit/live tested | IMPLEMENTED | Source priority is implemented; PDF route is the current selected-paper canonical route. |
| M1 | PDF canonical pipeline | implemented | unit + selected-paper real tests | REAL_E2E_VERIFIED_ON_SELECTED_PAPERS | Current M1 can generate M2-readable canonical bundles when regenerated with current code and all gates pass. |
| M1 | MinerU2.5-Pro primary parser | implemented | unit + selected-paper real tests | PARTIAL_REAL_E2E_VERIFIED | Primary PDF parser via `mineru-vl-utils`; broad multi-paper acceptance remains pending. |
| M1 | Quality gate | implemented | unit + acceptance enforced | REAL_E2E_VERIFIED | Blocks crop/overlay gaps, source mismatch, section pollution, raw-only formula dense outputs, and repeated/hallucinated text. |
| M1 | Ollama formula polish | implemented | smoke + selected-paper use | OPTIONAL_IMPLEMENTED | Explicit formula `final_latex` cleanup only; does not rewrite body structure. |
| M1 | Ollama section refiner | implemented | unit/local compare | OPTIONAL_NOT_DEFAULT | Diagnostic/review path only; default formal handoff remains rule-based. |
| M1 | Marker/MarkItDown/PyMuPDF fallback | implemented | unit/live tested | FALLBACK_ONLY | Review/debug/fallback only; cannot prove primary MinerU stability. |
| M1 | Direction exploration | not implemented | none | DOC_DESIGNED | Broad landscape/survey planning remains future work. |
| M1 | Seed expansion | not implemented | none | DOC_DESIGNED | Upstream/downstream graph remains future work. |
| M2 | Paper deep reading | implemented | unit + real M1/M2 e2e | REAL_E2E_VERIFIED_ON_SELECTED_PAPERS | Reads M1 bundles, calls real Mimo in full mode, and passes QualityAuditor on selected papers. |
| M2 | Formula card generation | implemented | unit + real e2e | IMPLEMENTED_ALL_FORMULA_COVERAGE | Formula provenance is preserved; every M1 formula evidence ref gets an explained, summary-only, or blocked card; advanced symbolic derivation remains evidence-bounded. |
| M2 | Survey artifacts | implemented | unit/pipeline fixture | IMPLEMENTED_RULE_BASED | Real survey PDF live acceptance remains pending. |
| M3 | Paper workspace | partial | component/API fragments | PARTIAL_CODE_NOT_REAL_VALIDATED | Not part of current M1 scope. |
| M4 | Interactive learning | not implemented | none | DOC_DESIGNED | Not part of current M1 scope. |
| M5 | Reliability | partial infra | partial | PARTIAL_INFRA | Real-test rules exist; production hardening remains pending. |

## M1 Current Statement

M1 is not "all modes complete." The accurate claim is:

M1 focused acquisition and selected-paper PDF canonical handoff are real
verified. Current M1 can produce `canonical_paper.md` plus the required M2
artifact bundle on selected real papers, with MinerU2.5-Pro as the primary
parser, crop/overlay enforcement, formula provenance, optional guarded Ollama
formula LaTeX polish, and quality gates. Direction exploration, seed expansion,
first-class LaTeX/HTML normalization, broad multi-paper MinerU acceptance, and
production-scale parser stability remain pending.

The authoritative M1 development contract is
`docs/development/M1_LITERATURE_SEARCH.md`.

## M1 Canonical Pipeline

Formal selected-paper pipeline:

```text
source PDF
  -> MinerU25ProAdapter
  -> CanonicalDocumentBlock normalization
  -> PDF bbox text repair for suspicious non-formula body blocks
  -> RuleBasedStructureRefiner
  -> optional Ollama formula LaTeX validator
  -> CanonicalBuilder
  -> M1QualityGate
  -> visual audit and M2 artifact bundle
```

Required M2 bundle:

- `canonical_paper.md`
- `document_blocks.json`
- `formula_slots.json`
- `formula_slots.md`
- `paper_metadata.json`
- `quality_report.md`
- `performance_report.json`
- `visual_audit/`

Required formula handoff fields:

- `formula_id`
- `block_id`
- `page`
- `section`
- `final_latex`
- `equation_number`
- `equation_group_id`
- `group_order`
- `group_crop_path`
- `nearby_text_before`
- `nearby_text_after`
- `risk_flags`
- `final_origin`
- `block_source`

## M1 Gates

M1 must fail or block M2 entry when:

- `canonical_paper.md` cannot be produced
- `m2_ready=false`
- `canonical_quality_status=FAIL`
- source/title identity is inconsistent
- formula bbox/crop/overlay is missing in formal mode
- formulas are all assigned to Abstract in a method paper
- Introduction/Method/Experiments are contaminated by References entries
- References content appears as Introduction or Method
- severe repeated/hallucinated parser text is present
- selected parser is obviously wrong

M1 may be degraded but still paper-readable when:

- some sparse formulas lack LaTeX but body text is faithful
- non-critical warnings are explicit in front matter/reports
- formulas are not ready for downstream formula understanding but paper text can
  still support evidence extraction

Dense raw-only formula rule:

```text
if formula_count >= 5 and latex_count == 0:
  canonical_quality_status = DEGRADED
  m2_ready_for_formula_understanding = false
```

`raw_formula_text` must not masquerade as LaTeX.

## Ollama Status

Ollama section refinement and Ollama formula polish are separate paths.

Formula polish:

- explicit only: `--enable-ollama-latex`
- currently intended model: local `qwen3.5:4b`
- uses formula/group crop visual evidence
- preserves page, bbox, crop, overlay, parser source, and equation tags
- rejects malformed JSON, low confidence, over-expanded group answers, left-hand
  side changes, and relation operand changes

Section refinement:

- optional/default off
- review/heavy diagnostics only
- must not modify LaTeX, bbox, page, source identity, or paper metadata

Formal M1->M2 handoff must not let Ollama rewrite body structure.

## Selected-Paper Validation

Selected-paper evidence currently includes:

- `paper_4_unseen` MEMTO: primary MinerU route sample in historical acceptance.
- `2312_01729v1` EdgeConvFormer: completed M1->M2 handoff with real Mimo in a
  prior selected-paper run. Generated reports should be regenerated before being
  treated as current formal evidence.
- `2310_08800v2` DDMT: regenerated on 2026-06-14 with current M1, PDF bbox text
  repair, crop/overlay enforcement, optional Ollama formula polish, and manual
  PDF-vs-canonical audit. Result: PASS, `m2_ready=true`,
  `m2_ready_for_formula_understanding=true`, 7 formulas, 7 LaTeX, 7 crops, 7
  overlays, no repeated hallucinated text, and no arXiv/page/CID/Unknown
  pollution. M2 diagnostic and full real Mimo handoff both succeeded.

This proves selected-paper handoff quality. It does not prove broad multi-paper
parser stability.

## M2 Handoff Status

M2 reads only the M1 artifact bundle. It must not read raw PDF, run its own
parser, or modify M1-owned immutable evidence fields.

Current M2 real selected-paper validation:

- real M1 canonical bundle input
- real Mimo provider in full mode
- QualityAuditor success
- M1 artifact hashes unchanged after M2 run
- 2026-06-14 `2310_08800v2` DDMT real run: M1 PASS input -> M2 SUCCESS,
  real Mimo `mimo-v2.5-pro`, 4 calls, 12,390 total tokens, 7 formula evidence
  refs, 7 formula cards, formula coverage PASS, QualityAuditor findings empty,
  M1 artifacts unmodified

Known M2 limitation: formula card coverage is all-formula, but detailed symbolic
derivation is only as strong as M1 LaTeX fidelity and nearby evidence.

## Hard Rules

- No reports, PDFs, `.env`, API keys, `.venv`, model weights, cache directories,
  or downloaded sources in commits.
- Parser success on one paper is not broad parser acceptance.
- Fallback parser success is not primary MinerU success.
- M1 cannot pass a raw PDF directly to M2. M2 input is the canonical M1 bundle.
- Live validation failures are failures, not skips, when claiming completed
  live behavior.
- Heavy parser/Ollama runs may be manual/nightly, but completion claims must
  name exactly what real run passed.

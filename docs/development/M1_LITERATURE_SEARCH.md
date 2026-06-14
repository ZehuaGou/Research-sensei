# M1 Literature Search, Source Acquisition, And Canonical Handoff

Last updated: 2026-06-14

This document is the authoritative M1 development contract. If older reports or
duplicated notes conflict with this file, this file wins.

## Purpose

M1 turns a user research target into verified, M2-readable paper material.

M1 owns:

- query planning for focused paper acquisition
- multi-source paper metadata acquisition
- candidate verification and relevance filtering
- best available source resolution
- material normalization into `canonical_paper.md`
- formula location, crop, overlay, provenance, and LaTeX handoff metadata
- M2 entry gates

M1 does not own:

- paper teaching cards
- formula explanations or derivations
- method graph construction
- paper Q&A
- frontend rendering
- M3/M4/M5 behavior

Those downstream tasks belong to M2+ and must consume the M1 artifact bundle
rather than re-reading raw PDFs behind M1.

## Current Status

| Area | Status | Notes |
|---|---|---|
| Focused acquisition | IMPLEMENTED / REAL_E2E_VERIFIED | Narrow-query search, verification, relevance judge, PDF download, and reading-plan gate have real live validation. |
| Source-aware acquisition | IMPLEMENTED | Source priority and arXiv source/PDF resolution are implemented; LaTeX/HTML normalization is not yet the primary proven route. |
| PDF canonical pipeline | IMPLEMENTED / REAL_E2E_VERIFIED_ON_SELECTED_PAPERS | Current MinerU-primary artifacts can be M2-readable when regenerated with current code and all quality gates pass. |
| MinerU2.5-Pro primary parser | IMPLEMENTED / SELECTED_PAPER_VERIFIED | Primary route uses `mineru-vl-utils` and has selected-paper real validation; broad multi-paper generalization remains pending. |
| Marker / MarkItDown / PyMuPDF fallback | IMPLEMENTED / FALLBACK_ONLY | Allowed for debug, audit, and fallback. They cannot prove primary MinerU stability. |
| Ollama formula LaTeX polish | IMPLEMENTED / OPTIONAL | Explicitly enabled only for formula `final_latex` cleanup; never rewrites body structure in formal handoff. |
| Ollama section refiner | IMPLEMENTED / OPTIONAL_NOT_DEFAULT | Review/heavy diagnostic only; formal M1 handoff remains rule-based for structure. |
| Direction exploration | DOC_DESIGNED / NOT_IMPLEMENTED | Broad landscape, staged survey search, and route map remain future work. |
| Seed paper expansion | DOC_DESIGNED / NOT_IMPLEMENTED | Upstream/downstream paper graph remains future work. |

Overall M1 status is `PARTIAL_REAL_E2E_VERIFIED`: focused acquisition and
selected-paper canonical PDF handoff are real-verified; direction exploration,
seed expansion, and broad multi-paper parser acceptance are not complete.

## Current Completion Definition

In the current project state, "M1 complete" means complete for the focused
selected-paper handoff path, not complete for every M1 product mode.

M1 may be marked complete for a concrete paper only when all of the following
are true:

- the paper was regenerated with the current M1 code, not copied from a stale
  historical report
- the selected source identity matches the target paper
- the primary route is declared honestly: MinerU primary, fallback, or blocked
- `canonical_paper.md` is readable as a paper, not merely as extracted text
- section structure is usable for evidence extraction
- formula slots preserve page, bbox, crop, overlay, origin, final LaTeX or an
  explicit raw/unresolved reason
- `M1QualityGate` returns `PASS` or an explicitly acceptable `DEGRADED`
- `m2_ready=true` before ordinary M2 reading
- `m2_ready_for_formula_understanding=true` before M2 formula reasoning
- the M2 artifact bundle contract below is satisfied
- a downstream M2 reader smoke can load the bundle without reading the raw PDF

M1 must not be called broadly complete until direction exploration, seed paper
expansion, first-class LaTeX/HTML normalization, and broad multi-paper MinerU
primary acceptance are implemented and real-validated.

## Current Code Ownership Map

The current focused selected-paper route is owned by these implementation
surfaces:

| Responsibility | Primary code |
|---|---|
| Live focused acquisition and reading-plan gate | `scripts/run_live_eval.py`, `src/researchsensei/acquisition/`, `src/researchsensei/selection/` |
| Source resolution | `src/researchsensei/source_resolver.py` |
| MinerU primary parsing | `src/researchsensei/canonical/mineru25_adapter.py` |
| Canonical pipeline orchestration | `src/researchsensei/canonical/pipeline.py` |
| Structure cleanup and section assignment | `src/researchsensei/canonical/structure_refiner.py` |
| Canonical Markdown and formula slot rendering | `src/researchsensei/canonical/canonical_builder.py` |
| Formula LaTeX normalization/polish guards | `src/researchsensei/canonical/latex_normalizer.py`, `src/researchsensei/canonical/ollama_latex_validator.py` |
| Quality gate | `src/researchsensei/canonical/quality_gate.py` |
| M2 artifact loading contract | `src/researchsensei/m2/artifact_reader.py` |
| Legacy fallback/debug normalization | `src/researchsensei/materials/material_normalizer.py` |

Changes to any of these surfaces can change M1 acceptance and require the
selected-paper acceptance checks in this document.

## Operating Modes

### Focused Acquisition Mode

Input: title, DOI, URL, arXiv ID, or narrow natural-language query.

Output:

- `query_plan.json`
- `candidate_pool.json`
- `source_resolution.json`
- `filtered_candidates.json`
- `reading_plan.json`
- canonical bundle for any selected `A_READ_FOR_M2` paper that passes material
  normalization

This is the only M1 mode with real end-to-end validation today.

### Direction Exploration Mode

Input: broad research direction.

Target output:

- `survey_candidates.json`
- `direction_landscape.json`
- `reading_plan.json`

Status: not implemented. Do not claim M1 direction exploration is complete.

### Seed Paper Expansion Mode

Input: a seed paper or paper ID.

Target output:

- `paper_relation_graph.json`
- `seed_expansion_result.json`

Status: not implemented. Do not claim seed expansion is complete.

## Pipeline

Formal focused-acquisition flow:

```text
user query/title/DOI/arXiv ID
  -> QueryPlanner with real LLM
  -> acquisition adapters
     -> ArxivAdapter
     -> OpenAlexAdapter
     -> SemanticScholarAdapter
     -> CrossrefAdapter
  -> verification
  -> LLM relevance judge
  -> SelectionService
  -> PaperSourceResolver
  -> material normalization
     -> M1CanonicalPipeline
     -> MinerU25ProAdapter (primary)
     -> RuleBasedStructureRefiner
     -> optional Ollama formula LaTeX validator
     -> CanonicalBuilder
     -> M1QualityGate
     -> visual audit and M2 bundle artifacts
  -> reading_plan.json with A_READ_FOR_M2 entries
```

The legacy `MaterialNormalizer` remains as fallback/debug infrastructure. The
formal PDF route is `M1CanonicalPipeline`.

## Best Available Source Policy

M1 must not stop at metadata. It must resolve the best available source:

1. `latex_source`
2. `structured_html` / `xml` / confirmed structured reader output
3. `pdf`
4. `low_confidence_text`
5. `metadata_only`

`metadata_only` can never enter M2.

Current real canonical acceptance is PDF-focused through MinerU2.5-Pro. LaTeX
source and structured HTML remain preferred target sources, but their full
normalization path is not yet the dominant real-verified route.

## Primary Parser Boundary

Primary parser:

- `src/researchsensei/canonical/mineru25_adapter.py`
- model family: `opendatalab/MinerU2.5-Pro-2604-1.2B`
- runtime: `mineru-vl-utils`
- normalized output: `CanonicalDocumentBlock`

Fallback / audit parsers:

- `MarkerDocumentFormulaDetector`
- `MarkItDownAdapter`
- `MarkerPdfAdapter`
- PyMuPDF text extraction

Parser rules:

- MinerU is the only primary PDF parser in formal M1 canonical acceptance.
- Marker is fallback/audit baseline, not proof of primary-route quality.
- PyMuPDF repairs only suspicious non-formula body text by PDF bbox. It must not
  change formula identity, bbox, page, crop, overlay, or parser source.
- Parser outputs from historical reports may be stale. Formal claims require
  regeneration with current code.

## Section And Body Structure Rules

`RuleBasedStructureRefiner` always runs. It must:

- recognize Abstract, Introduction, Related Work, Method/Methodology/Approach,
  Experiments/Evaluation/Results, Conclusion, References, and Appendix
- keep all content after References/Bibliography inside References unless an
  explicit Appendix begins
- prevent References entries from polluting Introduction, Method, or Experiments
- suppress repeated page headers, page numbers, author footers, front-matter
  affiliation noise, funding notes, and arXiv sidebar headers
- avoid creating `## Unknown` content after References in formal output
- flag section contradictions and reference contamination for the quality gate

Formal M1 output must be faithful enough for M2 evidence extraction. If the body
contains severe repeated or hallucinated text, the paper must fail the M1 gate.

Section quality is judged by downstream usability, not by heading labels alone.
A paper is not M2-ready when the Introduction is actually bibliography entries,
when Method/Experiments are dominated by reference-list text, or when repeated
page headers become synthetic subsections. These conditions must be repaired by
the structure refiner or surfaced as `FAIL`/`DEGRADED`; they must not be hidden
behind a nominal `PASS`.

For formal handoff, References/Bibliography is a one-way boundary: after that
heading, content remains References unless a clear Appendix heading begins.
References formulas may be retained for audit traceability, but they are not
eligible for formula-understanding handoff.

## Formula Extraction And Handoff

Formula extraction is not just text extraction. A formula that can enter M2
formula understanding needs:

- stable `formula_id`
- PDF page
- bbox in PDF/page coordinates
- crop image
- overlay image
- parser source
- final LaTeX when available
- raw text only when reliable LaTeX is unavailable
- nearby text before and after
- section assignment
- equation grouping metadata

Formula origins:

1. `source_latex`
2. `mineru_latex`
3. `marker_latex`
4. `parser_latex`
5. `ocr_latex`
6. `raw_formula_text`
7. `unresolved`

`raw_formula_text` must never be placed in the `latex` field or treated as
derivable LaTeX. Dense raw-only outputs are degraded for paper reading and
blocked for formula understanding.

Formula handoff decision tree:

1. If trusted source LaTeX exists, use `source_latex`.
2. Else if MinerU emits a valid formula LaTeX block, use parser/MinerU LaTeX and
   preserve parser provenance.
3. Else if an explicitly enabled OCR/polish path produces a guarded valid LaTeX
   result, use `ocr_latex` or the configured final parser origin.
4. Else if only readable formula-like text exists, store it as `raw_formula_text`
   and mark formula reasoning unavailable as required by the dense raw-only
   rule.
5. Else mark the slot `unresolved` with an explicit reason.

The `final_latex` field is for downstream-consumable LaTeX only. Raw text,
ambiguous equation fragments, and prose-like math candidates must stay out of
`final_latex` unless a guarded validator accepts them as LaTeX.

Dense raw-only rule:

```text
if formula_count >= 5 and latex_count == 0:
  canonical_quality_status = DEGRADED
  m2_ready_for_formula_understanding = false
```

## Ollama Formula Polish

Ollama has two separate M1 paths:

- section refinement: optional, default off, diagnostic/review only
- formula LaTeX polish: optional, explicit, crop-based

Formal M1->M2 handoff may enable formula polish with:

```powershell
.\.venv\Scripts\python.exe scripts\run_m1_v2_mineru_primary_acceptance.py `
  --limit 1 `
  --keys <arxiv_key> `
  --force `
  --enable-ollama-latex `
  --ollama-latex-model qwen3.5:4b `
  --ollama-timeout 30 `
  --ollama-min-confidence 0.8
```

Safety rules:

- model must be locally available and vision-capable
- use formula crop or group crop only as visual evidence
- send JSON-schema requests with `think=false`
- accept only high-confidence corrections
- preserve page, bbox, crop path, overlay path, parser source, and source PDF
  identity
- preserve equation tags; restore tags deterministically if the model drops them
- reject malformed JSON, low confidence, over-expanded group answers, changed
  left-hand side, and changed relation operands
- run deterministic LaTeX postprocessing before and after Ollama validation

Ollama must not rewrite body text, headings, section order, or references in the
formal handoff path.

## M2 Artifact Bundle Contract

M2 reads an M1 directory, not a raw PDF. The required bundle is:

- `canonical_paper.md`
- `document_blocks.json`
- `formula_slots.json`
- `formula_slots.md`
- `paper_metadata.json`
- `quality_report.md`
- `performance_report.json`
- `visual_audit/`

Recommended review/debug files:

- `source.pdf`
- `raw_mineru_output.json`
- `raw_mineru_pages/`
- `visual_audit.html`
- `compare_report.md`
- `PUBLIC_VERIFY_REPORT.md`
- `acceptance_metrics.json`

`formula_slots.json` must include the fields required by
`M1ArtifactReader.FORMULA_SLOT_CONTRACT_FIELDS`:

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

M2 treats these M1-owned fields as immutable evidence:

- page
- bbox
- LaTeX/final LaTeX
- formula origin
- parser source
- crop path
- overlay path
- source identity

M2 must not silently repair M1 parser failures. If M1 marks the paper or formula
as not ready, M2 must degrade or block accordingly.

## M1 To M2 Continuity Contract

M1 and M2 are intentionally separated by files, not by in-memory parser state.
That separation is part of the reliability design.

M1 must provide:

- stable canonical text for section/paragraph evidence
- stable formula slots for formula evidence
- immutable location fields for PDF traceability
- explicit quality status and degradation reasons
- enough nearby text for M2 to explain formula roles without re-parsing the PDF

M2 must provide:

- validation that required M1 artifacts and fields exist
- evidence references that point back to M1-derived blocks
- no mutation of M1 artifacts during understanding runs
- degradation/blocking when M1 marks formula understanding unavailable

The correct handoff check is therefore:

```text
M1 bundle exists
  -> M2 artifact reader loads it
  -> parsed_document preserves M1 formula/page/bbox/origin fields
  -> M2 run leaves M1 artifact hashes unchanged
```

If this check fails, the problem belongs to the M1/M2 contract boundary and must
be fixed before claiming either module is ready for that paper.

## Canonical Markdown Contract

`canonical_paper.md` must contain YAML front matter with:

- `paper_id`
- `title`
- `source_type`
- `source_confidence`
- `canonicalization_status`
- `canonical_quality_status`
- `primary_parser`
- `fallback_used`
- `m2_ready`
- `m2_ready_for_formula_understanding`
- `formula_slot_count`
- `mineru_latex_count`
- `raw_formula_text_count`
- `raw_only_formula_dense`
- `section_contradiction_count`
- `all_formulas_in_Abstract_suspicious`

Formula blocks in the body must be traceable to `formula_slots.json`. Parser
LaTeX is emitted as display math. Raw-only formulas are emitted as raw text with
origin metadata and must remain visibly degraded.

The canonical body must not include:

- large page-header/footer repetition
- arXiv sidebar text
- CID replacement artifacts
- References entries in Introduction/Method/Experiments
- generated placeholder sections
- `Unknown` sections after References

## Quality Gate

`M1QualityGate` returns `PASS`, `DEGRADED`, or `FAIL`.

Hard failures:

- parser unavailable with no valid fallback artifact
- source mismatch
- title/source mismatch severe enough to question identity
- missing formula bbox
- missing formula crop when crop is required
- missing formula overlay when overlay is required
- all 5+ formulas assigned to Abstract in a method paper
- section contradiction
- reference contamination in Introduction/Method/Experiments
- severe repeated/hallucinated body text

Degraded but possibly M2-readable:

- missing formula LaTeX on sparse formulas
- dense raw-only formulas for body reading only
- non-critical warnings that are explicitly represented in front matter and
  reports

M2 entry requires:

- `canonical_paper.md` exists
- `document_blocks.json` exists
- `formula_slots.json` exists and passes schema checks
- `canonicalization_status in {success, degraded}`
- `canonical_quality_status != FAIL`
- `m2_ready == true`
- all degradation reasons are explicit and acceptable for evidence-only reading

Formula-understanding entry additionally requires:

- `m2_ready_for_formula_understanding == true`
- body formulas have `final_latex`
- crop/overlay paths exist
- formulas in References are excluded from formula understanding

## Acceptance And Validation

Current selected-paper evidence:

- `paper_4_unseen` MEMTO: primary MinerU route sample, PASS in historical
  selected-paper acceptance.
- `2312_01729v1` EdgeConvFormer: selected-paper M1->M2 handoff with real Mimo
  validation was completed in a prior run; reports must be regenerated before
  use as current formal evidence.
- `2310_08800v2` DDMT: regenerated on 2026-06-14 with current M1, PDF text
  repair, crop/overlay enforcement, Ollama formula polish, and manual
  PDF-vs-canonical audit. Result: PASS, `m2_ready=true`,
  `m2_ready_for_formula_understanding=true`, 7 formulas, 7 LaTeX, 7 crops, 7
  overlays, no repeated hallucinated text, no arXiv/page/CID/Unknown pollution.

What this proves:

- current M1 can produce an M2-readable canonical bundle on selected real papers
- M2 can consume the bundle without touching raw PDF
- formula crop/overlay/LaTeX identity can be preserved through the handoff

What this does not prove:

- broad multi-paper MinerU stability
- survey-paper live acceptance
- direction exploration
- seed expansion
- M2 advanced derivation quality
- frontend/M3/M4/M5 behavior

### Per-Paper Acceptance Checklist

For every new paper used as M1 acceptance evidence, record the following in the
generated report or reviewer notes:

- selected parser and whether it is primary MinerU, fallback, or blocked
- `canonical_quality_status`
- `m2_ready`
- `m2_ready_for_formula_understanding`
- formula count, LaTeX count, raw-only count, unresolved count
- crop count and overlay count
- whether References content leaked into Introduction/Method/Experiments
- whether repeated page headers/footers remain in `canonical_paper.md`
- whether the first page title/authors/source identity match the PDF
- whether all formula slots include M2 contract fields
- whether M2 diagnostic mode can read the bundle
- whether any generated artifact comes from a stale report

The acceptance result is allowed to be:

- `PASS`: ordinary M2 reading and formula understanding may proceed
- `DEGRADED`: ordinary M2 reading may proceed, but warnings must be explicit
- `BLOCKED`: M2 must not run without manual override

`PASS` is not allowed when crop/overlay is missing in formal mode, when a dense
formula paper has only raw formula text, when source identity is wrong, or when
the canonical body is structurally polluted.

### Manual PDF-Vs-Canonical Audit

The automatic gate is necessary but not sufficient for a new parser route or a
new representative paper. A reviewer should inspect:

1. title, abstract, and first main section against the PDF
2. section order through Conclusion/References
3. several dense formula pages using the crop/overlay images
4. formula LaTeX against the formula crop for core equations
5. whether tables/figures are represented or explicitly degraded
6. whether body paragraphs are free from large line-join, CID, page-number, or
   hallucinated repetition artifacts

Minor punctuation, hyphenation, and line-break differences are acceptable. Wrong
paper identity, wrong section ownership, missing core formulas, false LaTeX,
or repeated non-paper text are not acceptable.

## Scripts

Full focused acquisition live eval:

```powershell
$env:RUN_LIVE_TESTS='1'
$env:RUN_LLM_TESTS='1'
$env:RESEARCHSENSEI_LIVE_EVAL='1'
.\.venv\Scripts\python.exe scripts\run_live_eval.py
```

Selected-paper MinerU primary acceptance:

```powershell
.\.venv\Scripts\python.exe scripts\run_m1_v2_mineru_primary_acceptance.py `
  --limit 1 `
  --keys 2310_08800v2 `
  --force `
  --enable-ollama-latex `
  --ollama-latex-model qwen3.5:4b `
  --ollama-timeout 30
```

Existing searched-paper acceptance:

```powershell
.\.venv\Scripts\python.exe scripts\m1_acceptance_runner.py `
  --search-dir reports\m1_unseen_paper_search `
  --output-dir reports\m1_acceptance_manual_review_<paper_id> `
  --enable-ollama-latex `
  --ollama-latex-model qwen3.5:4b
```

Static target-mode check:

```powershell
.\.venv\Scripts\python.exe scripts\m1_target_mode_eval.py
```

M2 contract smoke on an M1 bundle:

```powershell
.\.venv\Scripts\python.exe scripts\m2_run_understanding.py `
  --mode diagnostic `
  --input-dir reports\m1_canonical_acceptance\<paper_id> `
  --output-dir reports\m2_diagnostic_<paper_id>
```

## Report And Bundle Policy

Generated reports are evidence for the current run, not source code. They must
stay out of commits unless a small fixture is intentionally added under
`tests/fixtures/`.

Formal M1 selected-paper acceptance should write, at minimum:

- `source.pdf`
- `canonical_paper.md`
- `document_blocks.json`
- `formula_slots.json`
- `formula_slots.md`
- `paper_metadata.json`
- `quality_report.md`
- `performance_report.json`
- visual audit pages under `visual_audit/`

Review/heavy runs may additionally write raw parser payloads, comparison
reports, cropped pages, overlays, and public verification notes. These files are
useful for inspection but do not change the contract: M2 readiness is determined
by the required bundle plus quality status.

When regenerating reports, delete stale report directories first or use `--force`
so that acceptance is tied to the current code. Never use a historical report as
proof for a new parser or gate change.

## Test Policy

Code changes must run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Parser/heavy changes must also run a real selected-paper acceptance and a real
M2 artifact-reader smoke. Live/network/LLM failures are failures, not skips, for
claims of completed M1 behavior.

Do not commit:

- `reports/`
- downloaded PDFs
- `_candidate_downloads/`
- `.env`
- API keys
- `.venv/`
- model weights
- cache directories

## External Projects / Adapter Candidates

| Project | M1 role | Reusable capability | Integration | Default dependency | Risk | Status |
|---|---|---|---|---|---|---|
| arXiv official API / PDF / e-print | search and source resolution | metadata, PDF, source package | direct adapter | yes | rate limits, source package variability | IMPLEMENTED |
| OpenAlex / pyalex | metadata search | OA metadata, concepts, venues | direct adapter | yes | metadata noise | IMPLEMENTED |
| Semantic Scholar Graph API | metadata search and verification | title/venue/citation metadata | direct adapter | yes | rate limits | IMPLEMENTED |
| Crossref / habanero | DOI metadata verification | DOI and publisher metadata | direct adapter | yes | incomplete abstracts/full text | IMPLEMENTED |
| MinerU2.5-Pro via mineru-vl-utils | primary PDF layout/formula parser | blocks, bbox, LaTeX, reading order | direct adapter | yes for PDF canonical acceptance | heavy model/runtime, page latency | IMPLEMENTED |
| Marker | fallback formula/body parser | equation blocks, fallback markdown | optional adapter | no | historical section failures, GPL package | FALLBACK_ONLY |
| MarkItDown | lightweight fallback text extraction | debug markdown | optional adapter | no | weak layout/formula fidelity | FALLBACK_ONLY |
| PyMuPDF | PDF text/crop/overlay | crop, overlay, bbox text repair | direct utility | yes | embedded text can be incomplete | IMPLEMENTED |
| Ollama qwen3.5:4b | optional formula LaTeX polish | crop-based guarded correction | optional local model | no | hallucination if unguarded | OPTIONAL_IMPLEMENTED |
| pix2tex / LaTeX-OCR | unresolved formula OCR fallback | formula OCR from crop | optional adapter | no | model weights and slow download | INTERFACE_ONLY |
| DeepXiv | possible structured reader | structured arXiv reading if available | research required | no | no confirmed stable public package/API | BLOCKED |

## Open Work

- Broad multi-paper MinerU primary acceptance.
- First-class LaTeX source normalization.
- First-class structured HTML/XML normalization.
- Direction exploration implementation.
- Seed paper expansion implementation.
- Faster/heavier parser validation policy for nightly runs.
- Optional OCR model integration for unresolved formula crops.

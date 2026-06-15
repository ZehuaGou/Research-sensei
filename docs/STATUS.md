# ResearchSensei Status

Last updated: 2026-06-16

This file records real engineering status. Mock, fake, or skipped tests do not
count as module completion. Reports, downloaded PDFs, `.env`, API keys,
`.venv`, model weights, and generated bundles must not be committed.

## Status Levels

| Level | Meaning |
|---|---|
| NOT_STARTED | No implemented code and no usable design. |
| DOC_DESIGNED | Engineering contract is documented, but implementation is missing. |
| NOT_IMPLEMENTED_CONTRACT | API/UI path exists only to report that the feature is not implemented; it must not return fake success data. |
| IMPLEMENTED | Code exists, but real validation may still be pending. |
| UNIT_TESTED | Unit or fixture tests exist. |
| DEGRADED_SMOKE | A narrow live smoke passed, but full acceptance and broad validation remain pending. |
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
| M1 | Direction exploration | implemented minimal loop + handoff API | unit + arXiv smoke | DEGRADED_SMOKE | Minimal query -> DirectionBundle loop exists with real source adapters, heuristic query plan, candidate cards, reading order, source metrics, strict A_READ_FOR_M2 gate, and `/api/v1/directions/deep_read` handoff to PaperWorkspace. 2026-06-15 arXiv-only smoke for `time series anomaly detection` returned SUCCESS with 3 real candidates, then Mimo-enabled handoff created job `c09ff92ee955`; final status was DEGRADED_STRUCTURAL with `FORMULA_DERIVATION_BLOCKED`. No broad multi-source acceptance or A_READ canonical handoff yet. |
| M1 | Seed expansion | implemented minimal loop | backend + vitest + build + narrow smoke | DEGRADED_SMOKE | `/api/v1/directions/seed_expansion` accepts seed title/arXiv/DOI/URL/candidate payloads and returns upstream, downstream, same-route, survey, follow-up, and expansion-order fields from real paper-source adapters. Relations are explicitly weak query/title-similarity relations with `citation_graph_verified=false`; no citation graph is faked. 2026-06-15 smoke for seed arXiv `2510.18998` returned DEGRADED with 17 candidates: upstream=5, downstream=3, same-route=6, surveys=3. Degradation was due to Semantic Scholar 429 and Crossref timeouts. No broad Seed Expansion acceptance yet. |
| M2 | Paper deep reading | implemented | unit + selected-paper live acceptance | PARTIAL_REAL_E2E_VERIFIED | M2 selected-paper live acceptance passed on `2310_08800v2` via `reports/m2_live_acceptance.md`; broad multi-paper and survey live acceptance remain pending. |
| M2 | Formula card generation | implemented | unit + real e2e | IMPLEMENTED_ALL_FORMULA_COVERAGE | Formula provenance is preserved; every M1 formula evidence ref gets an explained, summary-only, or blocked card; advanced symbolic derivation remains evidence-bounded. |
| M2 | Survey artifacts | implemented | unit/pipeline fixture | IMPLEMENTED_RULE_BASED | Real survey PDF live acceptance remains pending. |
| M3 | Paper workspace | implemented minimal API/frontend | backend + vitest + build + selected-paper + raw-degraded API/UI live check | PARTIAL_REAL_E2E_VERIFIED | `/parse -> /understanding_status -> /cards` supports configured real LLM entry, existing M2 artifact registration, and strict gating. Selected-paper API/UI loop passed on real M2 artifacts for `2310_08800v2` (`reports/m3_paperworkspace_ui_live.json`): SUCCESS status, paper/formula/teaching cards rendered, and BLOCKED_UNDERSTANDING `/cards` stayed 403. Raw-input DEGRADED API/UI verified (`reports/m3_degraded_ui_live.md`): raw canonical job `f2fc0eaaf049` and raw PDF job `7832b248de01` both DEGRADED_STRUCTURAL with FORMULA_DERIVATION_BLOCKED, `/cards=200` returns paper_card+teaching_cards only, formula tab shows controlled degradation message with formula_origin/ocr_status, component_status/degradation_reason visible. Product readiness remains pending. |
| M3 | Direction workspace | minimal render + PaperWorkspace handoff | backend + vitest + build + arXiv smoke | DEGRADED_SMOKE | DirectionSearchView now submits a direction query, displays status/sources/warnings, overview, sub-directions, method families, candidate papers, and reading order. Candidates with arXiv/PDF source show `准备精读`, call `/api/v1/directions/deep_read`, and route to `/learn/{job_id}` on success. DOI remains `DOI_NOT_IMPLEMENTED`; unavailable sources fail closed. This is not M3 product readiness. |
| M3 | Seed expansion | minimal render + PaperWorkspace handoff | backend + vitest + build + narrow smoke | DEGRADED_SMOKE | SeedExpansionPanel accepts typed seed input or a selected Direction candidate, displays grouped seed-expansion papers with relation reason/confidence/source/verification/can_enter_m2, shows DEGRADED/EMPTY_RESULT states, and calls existing `/api/v1/directions/deep_read` for source-backed expansion papers. This is not product-ready SeedExpansion. |
| M4 | Interactive learning | not implemented | none | DOC_DESIGNED | Not part of current M1 scope. |
| M5 | Reliability | partial infra | partial | PARTIAL_INFRA | Real-test rules exist; production hardening remains pending. |
| M5 | Main-chain smoke script | implemented | unit + manual no-LLM smoke | DEGRADED_SMOKE | `scripts/run_main_chain_smoke.py` exercises direction search -> seed expansion -> deep_read handoff -> understanding_status -> cards gating through local API handlers. Core logic is unit-tested with fake clients and does not run live network/LLM inside pytest. 2026-06-16 manual run used no-LLM mode because `RESEARCHSENSEI_ENABLE_API_LLM` was not enabled; verdict was DEGRADED_PASS, job `dba63377572d`, final status `BASELINE_ONLY`, `/cards=403`. This is not LLM handoff evidence and not REAL_E2E. |

## M1 Current Statement

M1 is not "all modes complete." The accurate claim is:

M1 focused acquisition and selected-paper PDF canonical handoff are real
verified. Current M1 can produce `canonical_paper.md` plus the required M2
artifact bundle on selected real papers, with MinerU2.5-Pro as the primary
parser, crop/overlay enforcement, formula provenance, optional guarded Ollama
formula LaTeX polish, and quality gates. Direction exploration now has a
minimal unit-tested loop plus a narrow arXiv live smoke and a minimal
PaperWorkspace handoff API. Seed expansion now has a minimal unit-tested loop
plus a narrow DEGRADED external-source smoke, but broad multi-source acceptance,
verified citation-graph expansion, LLM-based planning, A_READ canonical handoff
from direction candidates, first-class LaTeX/HTML normalization, broad
multi-paper MinerU acceptance, and production-scale parser stability remain
pending.

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

- 2026-06-14 current `scripts/run_live_eval.py` with
  `RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1`: M1 live
  status passed, real LLM query planning true, successful sources `arxiv` and
  `openalex`, 6 candidates, 4 PDF download successes, 1 A_READ. Semantic
  Scholar rate-limited and Crossref timed out in that run, but the live eval
  report still passed through the successful source path.
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

Current M2 selected-paper live acceptance:

- 2026-06-14 current formal report: `reports/m2_live_acceptance.md`.
- Positive sample: `2310_08800v2` DDMT real M1 canonical bundle input -> M2
  `SUCCESS`, real Mimo `mimo-v2.5-pro`, 4 calls, 11,186 total tokens, 21
  artifacts, 7 formula evidence refs, 7 formula cards, formula coverage PASS,
  QualityAuditor findings empty, and M1 artifacts unmodified.
- Failure samples: missing canonical input, `m2_ready=false`, and missing METHOD
  evidence all enter `BLOCKED_UNDERSTANDING`, write no paper/formula/teaching
  card artifacts, and do not call the LLM during preflight.
- Status wording allowed by current evidence: "M2 selected-paper live acceptance
  passed." This is not broad `REAL_E2E_VERIFIED` for all M2 inputs.

### M2 Raw-Input Status

Raw-input jobs (canonical markdown or PDF submitted through M3 API) currently
reach `DEGRADED_STRUCTURAL`, not `SUCCESS` and not `BLOCKED_UNDERSTANDING`.

- Raw canonical job: `f2fc0eaaf049`. Status: `DEGRADED_STRUCTURAL`.
  blocking_reason: `FORMULA_DERIVATION_BLOCKED`.
  component_status: paper_card=SUCCESS, formula_cards=FAILED,
  teaching_cards=SUCCESS. `/cards=200`, returns paper_card + teaching_cards.
- Raw PDF job: `7832b248de01`. Status: `DEGRADED_STRUCTURAL`.
  Same structure as above.

DEGRADED reason: raw ingestion produces `formula_origin=raw_formula_text`.
Conservative provenance policy blocks detailed formula derivation when origin
is `raw_formula_text`, `unknown`, or `unresolved`. This is a deliberate safety
constraint, not a bug. QualityAuditor FSA-5 was not relaxed.

Raw-input DEGRADED is not broad/full M2 REAL_E2E. It means: M2 pipeline runs
on raw input, paper and teaching components succeed, but formula derivation is
blocked by provenance policy.

Known M2 limitation: formula card coverage is all-formula, but detailed symbolic
derivation is only as strong as M1 LaTeX fidelity and nearby evidence.

## M3 Current Statement

M3 is not complete as a product module. The accurate claim is:

PaperWorkspace has a minimal tested backend/frontend closed loop. The backend
supports configured real LLM construction through `create_app(...)` or
`RESEARCHSENSEI_ENABLE_API_LLM`, strict `/cards` gating for SUCCESS,
DEGRADED_STRUCTURAL, BASELINE_ONLY, BLOCKED_UNDERSTANDING, and FAILED, debug-only
raw artifact access, DOI rejection as `DOI_NOT_IMPLEMENTED`, minimal
DirectionSearchView rendering of the M1 DirectionBundle, minimal
`/api/v1/directions/deep_read` handoff for arXiv/PDF candidates, and minimal
SeedExpansion API/UI contracts.

API LLM configuration now loads `.env` before checking
`RESEARCHSENSEI_ENABLE_API_LLM`, so `.env` can enable API LLM and choose
`RESEARCHSENSEI_LLM_PROVIDER=mimo`. Missing keys fail with the missing
environment variable name only.

The frontend now reads `understanding_status` before requesting cards, requests
cards only for SUCCESS/DEGRADED_STRUCTURAL, hides cards for BASELINE_ONLY and
BLOCKED_UNDERSTANDING, displays source/canonical/formula/evidence/quality status
fields, renders the minimal M1 Direction Exploration bundle in
DirectionSearchView, lets source-backed candidates prepare a PaperWorkspace job,
and lets SeedExpansionPanel run minimal seed expansion plus PaperWorkspace
handoff for source-backed expansion papers.

M3 selected-paper API/UI evidence:

- 2026-06-15 current formal report: `reports/m3_paperworkspace_ui_live.json`.
- Positive sample: existing real M2 artifacts for `2310_08800v2` registered
  through `POST /api/v1/documents/parse` -> `GET /understanding_status`
  returned SUCCESS -> `GET /cards` returned 200 with `paper_card`,
  `formula_cards`, and `teaching_cards`; Browser validation confirmed the
  Paper, Formulas, and Teaching tabs rendered user-facing card content and
  source/canonical/formula/evidence/downstream status rows.
- Selected-paper job: `a292821c21c2`. `/understanding_status`=SUCCESS,
  `/cards=200`, paper_card/formula_cards/teaching_cards all rendered.
- Failure sample: missing METHOD evidence registered through the same API route
  stayed `BLOCKED_UNDERSTANDING`; `/cards` returned 403 and no explanatory card
  content was exposed. BLOCKED job: `ded6d0e1ee58`,
  blocking_reason=MISSING_METHOD_EVIDENCE, `/cards=403`.

M3 raw-input DEGRADED API/UI evidence:

- 2026-06-15 current formal report: `reports/m3_degraded_ui_live.md`.
- Raw canonical job `f2fc0eaaf049` and raw PDF job `7832b248de01`: both
  `DEGRADED_STRUCTURAL` with `FORMULA_DERIVATION_BLOCKED`, `formula_origin` =
  `raw_formula_text`, `formula_cards` = FAILED.
- `/cards` returns 200 with `paper_card` + `teaching_cards` only;
  `missing_components: ["formula_cards"]`; `degraded: true`.
- Frontend: Formula tab shows controlled degradation message ("公式推导不可用")
  with degradation_reason, formula_origin, formula_ocr_status; no detailed
  formula derivation displayed. StatusBanner shows missing_components,
  component_status.formula_cards=FAILED, degradation_reason,
  allowed_downstream.advisor_questions=false.
- M3 raw-input frontend coverage remains in the frontend suite; current total
  counts are listed in Test Status Summary.

M3 caveat: this verifies the selected-paper and raw-input DEGRADED PaperWorkspace
API/UI handoff plus a minimal DirectionSearchView render and arXiv-to-job
handoff smoke plus a minimal SeedExpansionPanel/API DEGRADED smoke. It does not
prove broad multi-paper behavior, full DirectionWorkspace product behavior,
verified citation-graph SeedExpansion, or product readiness.

Main-chain smoke status:

- `scripts/run_main_chain_smoke.py` now provides a manual M1 -> M2 -> M3 API
  smoke path: direction query -> `/api/v1/directions/search` -> arXiv
  candidate -> `/api/v1/directions/seed_expansion` -> source-backed expansion
  candidate -> `/api/v1/directions/deep_read` -> `/understanding_status` ->
  `/cards` gating.
- The script supports `--query`, `--provider`, `--max-candidates`,
  `--skip-llm`, and `--workspace`; it prints a console summary only and does
  not write reports.
- If API LLM is not enabled or the provider key is missing, the script runs a
  no-LLM smoke and expects `BASELINE_ONLY` plus `/cards=403`. That validates
  structural API/gating behavior only.
- 2026-06-16 manual run with `--provider mimo` did not enable LLM because
  `RESEARCHSENSEI_ENABLE_API_LLM` was not enabled. Result:
  DEGRADED_PASS, job `dba63377572d`, final status `BASELINE_ONLY`,
  seed expansion status DEGRADED, group counts upstream=6, downstream=6,
  same-route=6, surveys=3, `/cards=403`. This is not Mimo LLM handoff evidence.

## Test Status Summary

As of 2026-06-16:

- Backend: `.venv\Scripts\python.exe -m pytest -q` -> 496 passed, 15 skipped
- Frontend: `cd frontend && npm test` -> 5 test files, 33 tests passed
- Frontend build: `cd frontend && npm run build` -> success
- M1 Direction Exploration external smoke: arXiv-only query
  `time series anomaly detection` -> SUCCESS, 3 real candidates,
  `can_enter_m2=false` for all because no canonical M2-ready handoff was
  performed. With `RESEARCHSENSEI_ENABLE_API_LLM=1`,
  `RESEARCHSENSEI_LLM_PROVIDER=mimo`, and non-empty `MIMO_API_KEY`, handoff
  smoke selected arXiv `2510.18998`, created job `c09ff92ee955`, and returned
  `DEGRADED_STRUCTURAL` with `FORMULA_DERIVATION_BLOCKED`; paper_card and
  teaching_cards succeeded, formula_cards failed closed.
- M1 Seed Expansion external smoke: seed arXiv `2510.18998` via
  `/api/v1/directions/seed_expansion` -> DEGRADED, 17 real-source candidates,
  upstream=5, downstream=3, same-route=6, surveys=3. Semantic Scholar rate
  limited and Crossref timed out in part of the run. Relations remain weak
  query/title-similarity relations, not verified citation graph edges.

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

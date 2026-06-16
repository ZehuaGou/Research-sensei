# ResearchSensei Status

Last updated: 2026-06-16.

This is the single authoritative status file for ResearchSensei. README,
DESIGN, DEVELOPMENT, module contracts, development notes, and historical docs
must not override this file.

## Project Goal

ResearchSensei is a PhD-style research-reading simulator for the path:

```text
research direction
  -> legal multi-source paper discovery
  -> seed expansion
  -> source-backed deep_read handoff
  -> M2 evidence-backed paper understanding
  -> M3 controlled PaperWorkspace display
```

Current work is limited to M1/M2/M3 readiness. M4 chat, tutor follow-up,
long-term memory, drills, and training features are not started.

## Status Vocabulary

| Label | Meaning |
|---|---|
| IMPLEMENTED | Code path exists and has unit/integration coverage. |
| UNIT_TESTED | Automated tests cover the contract with local/fake dependencies. |
| DEGRADED_SMOKE | Narrow real smoke ran and produced usable degraded behavior or source warnings. |
| PARTIAL_REAL_E2E_VERIFIED | A specific real end-to-end path passed; broad scope remains pending. |
| REAL_E2E_VERIFIED | Real end-to-end validation passed for exactly the claimed broad scope. Avoid unless proven. |
| BLOCKED_UNDERSTANDING | Evidence/provenance gate failed closed. This is not a config failure by itself. |
| BASELINE_ONLY | No real LLM understanding. Must not be counted as live LLM acceptance. |
| DOC_DESIGNED | Contract exists but runtime is not implemented. |

## Strict Module State

| Module | Surface | Current state | Evidence | Strict judgement |
|---|---|---|---|---|
| M1 | Focused acquisition / selected-paper canonical handoff | implemented | selected real-paper acceptance | Narrow verified only. Direction and Seed were separate gaps and are now minimal loops, not full M1 completion. |
| M1 | Multi-source literature acquisition | implemented | source metrics + legal full-text smoke | DEGRADED_SMOKE. arXiv, OpenAlex, Semantic Scholar, Crossref, DBLP, and Unpaywall participate; not broad M1 REAL_E2E. |
| M1 | arXiv source-first | implemented | source/e-print handoff smoke | PARTIAL_REAL_E2E_VERIFIED for narrow arXiv candidates. Source/e-print is preferred over PDF; fallback stays explicit. |
| M1 | Direction Exploration | implemented minimal loop | backend + frontend tests + source smoke | DEGRADED_SMOKE. Returns overview, sub-directions, method families, candidates, source metrics, and reading order. |
| M1 | Seed Expansion | implemented minimal loop | backend + frontend tests + narrow smoke | DEGRADED_SMOKE. Returns grouped expansion papers and weak relation labels when citation graph is not verified. |
| M1 | DOI deep_read | implemented via Unpaywall | API + Mimo smoke | DOI-only handoff resolves through Unpaywall to legal OA PDF when available; returns `NO_LEGAL_OA_FULLTEXT_FOUND` when no OA PDF exists. Not broad REAL_E2E. |
| M2 | Selected-paper paper understanding | implemented | `2310_08800v2` live acceptance | PARTIAL_REAL_E2E_VERIFIED only for selected paper. |
| M2 | Raw/source handoff understanding | implemented fail-closed | Mimo source/PDF smokes | Can be SUCCESS, DEGRADED_STRUCTURAL, or BLOCKED_UNDERSTANDING depending on method evidence and formula provenance. Main-chain source_latex now achieves SUCCESS with all three card types. Not broad REAL_E2E. |
| M2 | Formula provenance/FSA-5 | implemented strict gate | unit + smoke | Unknown/weak formula origin cannot produce detailed derivation; source_latex improves but does not bypass audit. |
| M3 | PaperWorkspace | implemented minimal API/UI | selected-paper SUCCESS + raw/handoff DEGRADED/BLOCKED UI/API checks | PARTIAL_REAL_E2E_VERIFIED for narrow paths, not product-ready. |
| M3 | DirectionSearchView | implemented minimal UI | vitest + handoff smoke | DEGRADED_SMOKE. Shows source readiness and calls deep_read for source-backed candidates. |
| M3 | SeedExpansionPanel | implemented minimal UI | vitest + seed smoke | DEGRADED_SMOKE. Shows grouped relations and can call deep_read. |
| M4 | Interactive tutoring/memory/drills | not implemented | none | Do not start in current readiness work. |

## M1 Acquisition And Full-Text Evidence

Current acquisition stack:

| Source/tool | Runtime status | Current role | Full-text capability | Strict note |
|---|---|---|---|---|
| arXiv | invoked | search, metadata, source/e-print, PDF | source_ready/pdf_ready | Source-first is implemented and preferred over PDF. |
| OpenAlex | invoked | search, DOI, OA location metadata | OA PDF/landing metadata | Contributes DOI/OA data; not every DOI has legal full text. |
| Semantic Scholar | invoked | search, citation/reference metadata, openAccessPdf | OA PDF metadata | 429/rate limits degrade source only. |
| Crossref | invoked | DOI/venue/publisher/year metadata | metadata-only | Never treated as fulltext-ready by itself. |
| DBLP | invoked | CS venue metadata discovery | metadata-only | Helps discovery/venue, not download. |
| Unpaywall | invoked when email configured | DOI -> legal OA location | publisher/repository OA PDF or landing | Requires `UNPAYWALL_EMAIL` or `RESEARCHSENSEI_CONTACT_EMAIL`. |
| local upload | implemented | fallback for valuable metadata-only papers | user-provided PDF/canonical | Required when legal full text cannot be fetched automatically. |

Latest local Unpaywall/contact email check: `.env` is ignored, configured
locally, and must not be committed. Logs may show only masked email/domain.

## Recent Real Smoke Evidence

These are narrow evidence records, not product readiness.

### Literature acquisition smoke after Unpaywall email

Command shape:

```powershell
.venv\Scripts\python.exe scripts\run_literature_acquisition_smoke.py --query "<query>" --max-results 80 --download-top-n 10
```

Latest 2026-06-16 smoke after configuring Unpaywall/contact email:

| Query | Verdict | Attempted sources | Total | Non-arXiv | DOI | Legal fulltext | source_ready | pdf_ready | metadata_only | Unpaywall success/failure | Top failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| time series anomaly detection | PASS | 6 | 260 | 180 | 182 | 116 | 86 | 30 | 144 | 96/86 | Unpaywall no OA location, no legal OA fulltext, not found |
| graph anomaly detection | PASS | 6 | 244 | 165 | 182 | 111 | 84 | 27 | 133 | 90/92 | Unpaywall no OA location, no legal OA fulltext, not found |
| multivariate time series imputation | PASS | 6 | 59 | 44 | 44 | 28 | 17 | 11 | 31 | 19/25 | Unpaywall no OA location, no legal OA fulltext |
| graph neural network anomaly detection | PASS | 6 | 165 | 163 | 163 | 49 | 10 | 39 | 115 | 70/93 | Unpaywall no OA location, no legal OA fulltext, not found |

This proves Unpaywall and non-arXiv legal fulltext discovery work in a narrow
smoke. It does not prove broad M1 REAL_E2E. Metadata-only papers remain visible
instead of being discarded.

### Main-chain and deep_read evidence

| Path | Job | Result | Cards | Components | Strict note |
|---|---|---|---|---|---|
| selected paper `2310_08800v2` | `a292821c21c2` | SUCCESS | 200 | paper/formula/teaching | Selected-paper M2/M3 evidence only. |
| negative selected-paper gate | `ded6d0e1ee58` | BLOCKED_UNDERSTANDING, `MISSING_METHOD_EVIDENCE` | 403 | none | Correct fail-closed gate. |
| raw Mimo handoff | `c09ff92ee955` | DEGRADED_STRUCTURAL, `FORMULA_DERIVATION_BLOCKED` | 200 | paper + teaching | Mimo entered chain; formula component degraded. |
| main-chain source-first Mimo | `e6162aaf98e4` | SUCCESS | 200 | paper + formula + teaching | Narrow PASS with source_latex evidence; not broad REAL_E2E. |
| non-arXiv OA PDF deep_read | `8cba4345fee7` | DEGRADED_STRUCTURAL, `FORMULA_DERIVATION_BLOCKED` | 200 | paper + teaching | Legal OA PDF handoff works; formula provenance remains weaker than source_latex. |
| DOI-only Unpaywall OA deep_read | `b28134b4496c` | DEGRADED_STRUCTURAL, `FORMULA_DERIVATION_BLOCKED` | 200 | paper + teaching | DOI `10.1038/s41586-021-03819-2` resolved via Unpaywall to legal OA PDF; Mimo M2 ran; formula provenance degraded for non-arXiv PDF. |
| main-chain source_latex formula success | `cb59b58dbe55` | DEGRADED_STRUCTURAL, `TEACHING_CARDS_FAILED` | 200 | paper + formula | source_latex formula cards now succeed; 18 formula cards with source_latex origin; teaching cards failed separately. |
| main-chain full SUCCESS | `73ddb4607b6b` | SUCCESS | 200 | paper + formula + teaching | All three card types succeed with source_latex origin; narrow PASS, not broad REAL_E2E. |

Latest 2026-06-16 Mimo main-chain smoke:

| Query | Job | Selected paper | Input | Final status | Blocking reason | Cards | Components | Verdict | Strict note |
|---|---|---|---|---|---|---:|---|---|---|
| time series anomaly detection | `522e67e371e2` | `2007.14254`, Improving Robustness on Seasonality-Heavy Multivariate Time Series Anomaly Detection | arxiv_source, source_first | BLOCKED_UNDERSTANDING | FORMULA_CARDS_FAILED | 403 | none | DEGRADED_PASS | Mimo was enabled; arXiv source downloaded; formula origin summary showed `source_latex`, but formula cards failed audit/generation so cards stayed blocked. |
| graph anomaly detection | `a58dbf082252` | `2212.05478`, Mul-GAD: a semi-supervised graph anomaly detection framework via aggregating multi-view information | arxiv_source, source_first | BLOCKED_UNDERSTANDING | FORMULA_CARDS_FAILED | 403 | none | DEGRADED_PASS | Smoke selector now avoids unrelated source-backed papers; Mimo was enabled and gate failed closed on formula cards. |
| time series anomaly detection | `cb59b58dbe55` | source_latex paper | arxiv_source, source_first | DEGRADED_STRUCTURAL | TEACHING_CARDS_FAILED | 200 | paper + formula | PASS | Formula cards now succeed with source_latex origin; 18 formula cards generated; teaching cards failed separately. |
| time series anomaly detection | `73ddb4607b6b` | source_latex paper | arxiv_source, source_first | SUCCESS | — | 200 | paper + formula + teaching | PASS | Full SUCCESS with source_latex; all three card types generated. |

## M2/M3 Gating Rules

- SUCCESS: `/cards=200`; paper, formula, and teaching cards expected.
- DEGRADED_STRUCTURAL: `/cards=200`; only successful components returned.
- BLOCKED_UNDERSTANDING: `/cards=403`.
- BASELINE_ONLY: `/cards=403`.
- FAILED: `/cards=403`.
- SUCCESS with missing required card artifact: `/cards=409`.
- `/artifacts` remains debug/admin oriented.

BLOCKED_UNDERSTANDING due to `MISSING_METHOD_EVIDENCE` or audit findings is
evidence gate fail-closed, not a configuration failure. BASELINE_ONLY during an
LLM-enabled smoke is a failure unless the smoke intentionally used `--skip-llm`.

## Configuration For Future Runs

Local `.env` example:

```text
RESEARCHSENSEI_ENABLE_API_LLM=1
RESEARCHSENSEI_LLM_PROVIDER=mimo
MIMO_API_KEY=...
UNPAYWALL_EMAIL=you@example.com
RESEARCHSENSEI_CONTACT_EMAIL=you@example.com
SEMANTIC_SCHOLAR_API_KEY=...
OPENAI_COMPATIBLE_API_KEY=...
```

`config/sensei.example.toml` includes Mimo and generic OpenAI-compatible
provider placeholders. For Xiaomi or another weaker OpenAI-compatible model,
set provider base URL, model, and API key env in ignored `config/local.toml` or
use the generic provider template. Do not lower evidence gates for weaker model
output.

LLM JSON handling is fail-closed: malformed JSON or schema mismatch must become
explicit component failure/degradation, not accepted evidence.

## Largest Current Shortfalls

1. Broad M1 REAL_E2E is still missing: coverage is smoke-level, not systematic
   benchmark acceptance.
2. DOI-only deep_read remains `DOI_NOT_IMPLEMENTED`; DOI helps lookup but cannot
   by itself start M2.
3. Semantic Scholar can rate-limit; source-level degradation is handled, but
   broader retry/backoff policy remains limited.
4. Formula cards still degrade on non-source_latex or weak provenance.
5. Main-chain positive evidence is narrow; source-first success is promising but
   not broad reliability.
6. M4 remains not implemented by design.

## Next Priority Order

1. Improve DOI-to-legal-fulltext-to-deep_read handoff without paywall bypass.
2. Build a small tracked acceptance fixture list for M1 acquisition coverage,
   but do not commit downloaded papers.
3. Expand source_latex canonical extraction coverage and formula provenance
   tests.
4. Add more real main-chain smoke samples across domains and record only scoped
   evidence.
5. Keep frontend status rendering aligned with `/understanding_status` and
   `/cards` gating.

## Weak-Model Handoff Guide

If a weaker model or Xiaomi/Mimo-compatible model continues this project:

1. Read this file first.
2. Run backend tests.
3. Run one literature acquisition smoke.
4. If Mimo/API key exists, run one main-chain smoke.
5. Treat all failures literally; do not patch around gates.
6. Make only small, source-local fixes.
7. Update this file with exact command, job ID, status, cards code, components,
   and strict scope.
8. Do not create new report files.
9. Do not start M4.

## Required Regression Commands

```powershell
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm test
npm run build
```

Live smokes are optional when keys/network are unavailable, but missing key or
network must be reported as not live-verified.

# ResearchSensei v0.6 Reliability Baseline Status

Last updated: 2026-07-19 (Asia/Shanghai).

This is the authoritative implementation and verification ledger for
ResearchSensei. Design documents describe contracts; this file records what was
actually checked. A skipped, mocked, cached, or offline result is never reported
as a live acceptance result.

## 2026-07-19 M1 Open-Fulltext Rescue

### Relevance-first correction

The earlier implementation and acceptance table used a seven-paper download
queue. That framing was incorrect: M1 must never treat a count as a quota or
promote an easier source over a more relevant paper. The current behavior is:

- strict deterministic relevance plus the deep-read score threshold is applied
  before full-text discovery or download;
- every qualifying candidate is attempted by default, so the result count is
  dynamic; `search.max_download_candidates = 0` means no arbitrary cap;
- a positive user-configured cap preserves relevance order;
- OA supplementation is triggered by unresolved relevant papers, not by a
  target such as "seven open PDFs";
- an optional user-authorized Chrome storage state can recover publisher PDFs
  that are available in the user's legitimate browser session but rejected by
  backend HTTP. It remains fail-closed and never reads the normal Chrome
  profile or bypasses access controls.

This section supersedes the earlier single-query M1 `2/7` result below.

- Git history is consolidated on `main`; local and remote have no other branch.
- The production direction service now actually wires OpenAlex and Semantic
  Scholar as OA supplements. Supplementation is decided by the deterministic
  relevance gate's count of relevant/open papers, not rough keyword overlap or
  unrelated arXiv hits.
- OA supplement queries always include the user's original query, use three
  complementary variants, and request at least 50 results per index. Optional
  index rate limits remain visible in source metrics but do not degrade a run
  when another OA index succeeds.
- Deterministic relevance runs before DOI, repository, Unpaywall, and publisher
  probing, so full-text discovery is limited to relevance-cleared candidates.
- Deduplicated OpenAlex/Semantic Scholar metadata is scanned recursively for
  secondary OA locations. DOI redirects and reputable repositories such as
  PMC, HAL, and institutional repositories are eligible for HTML PDF-link
  extraction.
- The downloader orders stable OA endpoints ahead of publisher fallbacks and
  tries every legal candidate PDF URL until a validated PDF succeeds. The
  dynamic download queue preserves relevance order and prefers cached, arXiv,
  repository, and open proceedings sources for each selected paper.
- PMC landing-page PDF links that return an HTML preparation screen are now
  resolved through PMC's official versioned Cloud Service metadata and PDF
  objects before falling back to page scraping.
- The direction UI shows strict-related, attempted, successful, and total
  deduplicated counts, and hides `D_IGNORE` candidates by default behind an
  explicit disclosure button.

Live acceptance progression for the same query
`graph neural network multivariate time series anomaly detection`:

| Revision stage | Live result | Interpretation |
|---|---|---|
| Previous implementation | 30 raw candidates, 7 relevant, 2/7 downloaded, 50.8s | Primary-only discovery and single-URL failure. |
| OA supplement wired | 76 raw candidates, 10 relevant, 6/10 downloaded, 106.7s | Better discovery, but closed papers still occupied the queue. |
| Seven-paper source-aware queue | 146 raw candidates, 17 relevant, 7/7 downloaded, 223.2s | Full download target passed, but full-text probing happened too early. |
| Final optimized live run | 254 raw candidates, 146 deduplicated, 46 strict-related, 7/7 downloaded, 134.1s | `SUCCESS`; all selected papers were validated and landed locally. |
| Final browser acceptance | 114 deduplicated, 17 strict-related, 7/7 downloaded | `SUCCESS` even while Semantic Scholar was unavailable; OpenAlex supplementation and legal-source fallback carried the queue. |
| Relevance-first dynamic acceptance | 204 deduplicated, 18 strict-related, 18 attempted, 12 downloaded | `DEGRADED` because six relevant papers remain unresolved; no lower-relevance paper was substituted. PMC Cloud recovery restored GTAD. |

The final live run is a single-query acceptance, not a claim that every
publisher or every research direction will achieve a fixed count. A fresh ACM
automation context still reached a security challenge; the authorized-session
fallback has deterministic contract coverage but still needs a one-time user
session capture for live ACM acceptance. MDPI PDF/page requests were 403, and the tested
IEEE/Elsevier papers had no OA copy in OpenAlex, Semantic Scholar, or Europe PMC.
The implementation therefore uses legal alternative copies and source-aware
candidate selection rather than bypassing access controls.

## 2026-07-19 Full-Project Remediation Refresh

This section supersedes the earlier local gate counts below without rewriting
the historical v0.6 release ledger.

- Document upload, local-path parsing, and reparse now have persistent background
  task endpoints with 202 submission, progress polling, typed terminal failures,
  cancellation requests, restart interruption state, and frontend task recovery.
  The synchronous parse/reparse endpoints remain compatibility paths.
- M4 structured output accepts fenced/trailing JSON, performs one bounded
  format-only repair attempt, and never exposes raw malformed model output in a
  learner-facing error. Existing claim/evidence validation remains unchanged.
- Request/library title metadata enters the ingestion skeleton before card
  generation. New library downloads infer known venue/rank from registry URLs and
  confident DOI patterns such as AAAI. Existing rows are not silently rewritten.
- The library API and UI use total/limit/offset pagination; the live local library
  was rendered as 30 + 25 rows instead of loading 55 records at once.
- ccswitch model options now show the current setting, current provider models,
  and live `/models` results only, capped at 24; request-history and the full
  pricing catalog are no longer mixed into the learner setting.
- `python -m researchsensei serve` reads `server.host`, `server.port`, and
  `server.reload`; checked local/example configuration and the frontend proxy now
  agree on port 8765.
- CI quotes the Vitest exclude glob for Linux shells, runs Ruff over all `src` and
  `tests`, and mypy now checks all 126 backend modules instead of six selected
  files. The npm lock was refreshed to remove the reported `undici` advisory.

Current verification:

| Command / surface | Result | Classification |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `789 passed, 15 skipped` in 178.01s | Complete local backend/offline suite. |
| `.venv\Scripts\python.exe -m ruff check src tests` | Passed | Full backend and test lint. |
| `.venv\Scripts\python.exe -m mypy` | No issues in 127 source files | Full backend type boundary. |
| `npm test` | 15 files, 76 tests passed | Frontend unit/contract suite. |
| `npm run typecheck` and `npm run build` | Passed; Vite transformed 94 modules | Frontend static and production build. |
| `npm audit --registry=https://registry.npmjs.org` | 0 vulnerabilities | Full npm dependency tree, including dev dependencies. |
| `npm run test:e2e` | 6/6 Chromium fixture tests passed | Deterministic browser E2E. |
| Real local browser against configured workspace | 55-paper pagination, six visible ccswitch choices, and persistent document task handoff verified; zero console errors | Runtime/local-services smoke, not an external paper/LLM acceptance. |

Remaining external boundaries are explicit: the pre-existing GitHub Actions run
remains red until this checkout is pushed and GitHub reruns the updated workflow;
the repaired M4 format path has deterministic tests but was not charged against a
live model again; task cancellation is cooperative and cannot pre-empt a parser or
LLM call already executing; and the prior 12-query external acquisition matrix
remains a failed live acceptance rather than being reclassified by local success.

## 2026-07-19 M1/M4 Main-Flow Optimization

This follow-up targets the main learner workflows rather than additional
reliability plumbing.

- M4 now resolves pronouns and short follow-ups against the previous user turn
  before deciding that a question is underspecified. The resolved focus and the
  previous turn's verified refs seed retrieval, while conversation history and
  memory are explicitly forbidden from acting as paper evidence or supporting
  quotations.
- Every M4 response can expose a user-safe context trace: current paper versus
  selected text, whether the turn continues the previous question, and how many
  verified evidence refs survived. Model-proposed follow-up questions are
  bounded and presented as reusable prompts.
- Frontend conversations are isolated per paper. Reload recovery shows only the
  last question and a safe recovery notice; legacy answer bodies are not replayed
  because older memory may predate current claim-level validation. The next
  answer is retrieved and validated again.
- The M4 pane shows the active paper title, evidence scope, context continuity,
  selected-text controls, evidence counts, uncertainty, and follow-up actions.
  The successful status ledger is one row on desktop so the paper content starts
  higher in the reading pane.
- M1 no longer treats any non-empty primary result as sufficient. Thin candidate
  pools, weak topic coverage, or too few open-fulltext hints trigger a bounded
  two-query supplement through the configured OpenAlex/Semantic Scholar fallback
  adapters. Source metrics record the trigger, and the direction UI displays a
  source ledger instead of hiding which provider returned or failed.
- Query-planning instructions now require complementary exact, task/domain,
  terminology, and survey/foundational variants that work across arXiv,
  OpenAlex, and Semantic Scholar.

Verification for this follow-up:

| Command / surface | Result | Classification |
|---|---|---|
| `.venv\Scripts\python.exe -m pytest -q` | `778 passed, 15 skipped` in 153.30s | Complete local backend/offline suite. |
| `.venv\Scripts\python.exe -m ruff check src tests` | Passed | Full backend and test lint. |
| `.venv\Scripts\python.exe -m mypy src/researchsensei` | No issues in 126 source files | Full backend type boundary. |
| `npm test`, `npm run typecheck`, `npm run build` | 15 files / 75 tests passed; typecheck and production build passed | Frontend unit/static acceptance. |
| `npm run test:e2e` | 6/6 Chromium fixture tests passed | Deterministic browser E2E. |
| Real browser, configured paper `55b9e24aec49` | Paper-scoped recovery, active title, context trace, evidence count, composer scope, and zero console errors verified | Local runtime UI smoke. |
| Live M1 query `graph neural network multivariate time series anomaly detection` | Persistent task succeeded in 50.8s; 30 candidates; bundle remained `DEGRADED`; 2/7 attempted downloads succeeded | Live acquisition probe, explicitly not full acceptance. |
| Live ccswitch validation and M4 follow-up | 8-second provider probe succeeded; one evidence-retrieved follow-up reached 8 refs but the structured model request failed and the UI refused unvalidated output | Provider connection passed; full M4 live answer failed safely. |

Remaining risks: the live M1 result still had a high download failure rate and no
candidate cleared every A_READ/M2 gate in the search response; ccswitch accepted
a connection probe but did not complete the tested structured M4 request. These
are live-service failures, not reclassified by the green offline suites.

## Release Identity

- Target: `ResearchSensei v0.6 Reliability Baseline`
- Working branch: `main` (the only local and remote branch)
- Baseline branch: `main`
- Baseline HEAD: `769bf2ceda9ef17acd1b8e60b5e955c41f27a6d9`
- Verified code/CI HEAD: `3c41f133eb6a22209ce01ceee7d22466320b287b`
- Final branch HEAD: the documentation synchronization commit that contains this ledger; the exact hash is recorded in the final handoff.
- Merge recommendation: **Yes**, after the branch CI completes; local offline gates are green and live limitations are explicit below.

The code/CI hash above is the exact revision exercised before the final
documentation-only commit. Embedding a commit's own hash in that commit is not
possible, so the final handoff records the resulting documentation commit hash
and clean-worktree check.

## Reliability Model

M1 and the downstream workspace no longer use one overloaded `SUCCESS` label
to represent every stage. The maintained status dimensions are:

| Dimension | Meaning |
|---|---|
| `pipeline_status` | Search, source resolution, parsing, M2, and card pipeline completion. |
| `relevance_status` | Whether the selected paper covers the requested task, data shape, and method concepts. |
| `source_status` | Whether a legal, verified source can enter M2. |
| `understanding_status` | Whether evidence-backed M2 cards are safe for user display. |

A completed pipeline with a relevance failure is not product success. A
candidate below the deterministic relevance threshold is returned as
`DEGRADED` or `BLOCKED`; it is not selected merely to keep the chain moving.

## Implemented v0.6 Hardening

### M1 relevance

- The offline relevance benchmark contains at least twenty English, Chinese,
  and mixed-language cases covering anomaly detection, forecasting,
  imputation, graph/GNN methods, diffusion, surveys, RCA, and LLM-for-AIOps.
- Each case declares required and optional concepts, forbidden intent
  mismatches, survey policy, and acceptable/unacceptable examples.
- Deterministic concept coverage and intent-mismatch penalties are the primary
  gate. An optional LLM judge may veto or annotate a result but cannot rescue a
  deterministic failure.
- Top-1 and deep-read candidates have separate minimum thresholds. Historical
  clustering/forecasting/imputation mismatches are regression cases.

### Configuration

Runtime precedence is singular and documented:

1. explicit constructor or `create_app()` override;
2. environment variable;
3. `config/local.toml`;
4. `config/sensei.example.toml`;
5. code default.

`create_app()` loads the complete configuration once and injects workspace,
server, search sources, result limit, timeout, parser backend, upload limit, and
LLM provider. Search adapters do not maintain a second independent default
source list. Invalid sources, negative timeouts, and unsafe limits are rejected.
Settings output is secret-safe. `/api/v1/settings/validate` performs local
configuration validation; live connection validation is explicit, bounded by a
timeout, and reports a typed, redacted error. The deprecated `/settings/test`
alias remains for compatibility.

### API, uploads, and tasks

- `researchsensei.web.app:create_app` remains the stable entry point and
  delegates to an app factory with dependency wiring, routers, request models,
  and focused services.
- Direction search/deep-read, seed expansion, M4, and settings mutations use
  bounded Pydantic request models. Unknown fields are rejected except where the
  documented compatibility candidate payload requires preservation.
- Validation and HTTP failures expose a stable machine-readable error code.
- Uploads stream through bounded chunks, enforce the byte limit while writing,
  verify extension/MIME/signature, generate server-side names, and clean
  temporary files after failure or cancellation.
- Long direction operations have local persistent jobs with stage, progress,
  result, typed failure, cancellation, and restart-time stale-task recognition.
  Synchronous endpoints remain compatibility paths.

### M4 grounding and memory

- M4 no longer emits a fixed spectral-residual/Fourier/threshold explanation
  from broad keywords such as “time series” or “anomaly”.
- LLM output is claim-structured. Every claim carries its own evidence refs and
  supporting quotation; the backend validates the ref allow-list and whether
  the cited text supports the claim.
- Formulae, thresholds, numbers, datasets, metrics, and experimental results
  receive stricter matching. Unsupported claims are removed or cause
  `DEGRADED`; a legal ref does not make an unrelated answer legal.
- `m4_memory.json` uses schema `m4_memory.v2`, per-job locking, temporary-file
  write plus `fsync`/atomic replace, bounded records/file size, deduplication,
  legacy migration, and corrupt-file quarantine with a visible warning.

### Local persistence and frontend

- SQLite stores use a busy timeout, WAL, explicit transaction boundaries,
  schema versions, and guarded updates. Duplicate active work for one source
  identity is rejected unless an explicit force flow creates a distinct job.
- Job artifact cleanup is confined to workspace-managed run roots; arbitrary
  user paths are never recursively removed.
- Frontend requests are centralized in a typed client. Workspace status,
  formula dock, tab/scroll memory, chat resizing, and data loading are separated
  into typed components/composables.
- Formula-dock coordinates are clamped after drag, viewport resize, zoom/layout
  changes, and local-storage migration. Keyboard movement and reset are
  supported, and lost pointer capture ends dragging.

## Gates That Remain Non-Negotiable

- QualityAuditor is not bypassed.
- `evidence_ref` existence and support are validated.
- FSA-5 remains strict.
- `source_latex` is accepted only from an allowed source path.
- `/cards` remains fail-closed for blocked understanding.
- M4 stays within the current paper evidence boundary.
- DOI, arXiv ID, PDF readiness, source identity, and live-service results are
  never synthesized to make a test pass.

## Verification Ledger

### Initial baseline at `769bf2c`

| Command | Result | Classification |
|---|---|---|
| `python -m pytest -q` | `6 failed, 687 passed, 15 skipped` in 247.30s | Three invalid-UTF-8/mojibake documentation failures, one bare-interpreter environment audit failure, one RCA rank regression, and one damaged reuse-report contract. |
| `python -m pytest tests/test_main_chain_matrix.py -v` | `28 passed` in 1.13s | Offline matrix contract. |
| `cd frontend; npm ci` | Installed 239 packages successfully. | Offline dependency install from lockfile plus registry fetch. |
| `cd frontend; npm test` | `10 files, 57 tests passed`. | Offline frontend unit tests. |
| `cd frontend; npm run build` | Passed. | Offline production build. |
| `cd frontend; npm audit --omit=dev --registry=https://registry.npmjs.org` | `0 vulnerabilities`. | Registry-backed dependency audit. |
| `git diff --check` | Passed. | Repository hygiene. |
| `python -m researchsensei --help` and maintained script `--help` checks | Passed. | Import/CLI smoke checks. |
| `.venv\Scripts\python -m pytest tests/test_m1_search_and_device.py::test_environment_audit_produces_output -q` | `1 passed`. | Proved the baseline environment-audit failure was caused by the bare interpreter, not an application regression. |

### Interim v0.6 checks

These checks are real but overlap; they are not a substitute for the final full
suite.

| Command | Result | Scope |
|---|---|---|
| `.venv\Scripts\python -m pytest tests/test_m1_relevance_benchmark.py tests/test_paper_ranker.py tests/test_direction_exploration_service.py tests/test_m4_api.py tests/test_m4_memory.py -q` | `89 passed` in 85.02s. | Deterministic relevance, ranking, direction flow, claim-level M4 grounding, and memory. |
| `.venv\Scripts\python -m pytest tests/test_background_tasks.py -q` | `5 passed`. | Persistent local task lifecycle and cancellation. |
| `cd frontend; npm test` | `13 files, 66 tests passed` in 9.17s. | Typed client and workspace interaction unit tests. |
| `.venv\Scripts\python -m pytest tests/test_encoding_hygiene.py tests/test_m1_docs_contract.py tests/test_v05_docs_contracts.py -q` | `6 passed` in 0.30s. | UTF-8 and documentation contracts. |

### Final required commands

| Command | Final result |
|---|---|
| `.venv\Scripts\python -m pytest -q` | `771 passed, 15 skipped` in 194.12s. |
| `.venv\Scripts\python -m pytest tests/test_main_chain_matrix.py -v` | `28 passed` in 1.31s. |
| `.venv\Scripts\python scripts/run_m1_relevance_benchmark.py` | `23/23` cases and `46/46` candidate expectations passed; offline verdict `PASS`. |
| `cd frontend; npm ci` | Installed 242 locked packages successfully. |
| `cd frontend; npm test` | `14` files, `73` tests passed. |
| `cd frontend; npm run typecheck` | Passed (`vue-tsc -b`). |
| `cd frontend; npm run build` | Passed; Vite transformed 94 modules. |
| `cd frontend; npm run test:e2e` | `6 passed` in 15.7s on Chromium with fixed local fixtures. |
| `cd frontend; npm audit --omit=dev --registry=https://registry.npmjs.org` | `0 vulnerabilities`. |
| backend lint and type checks | Ruff passed; mypy reported no issues in 6 source files. |
| `git diff --check` | Passed before documentation commit and repeated after it. |
| `git status --short` | Clean after the final documentation commit; exact output is repeated in the final handoff. |

## Live Verification

| Surface | Status | Reason |
|---|---|---|
| External paper APIs and legal full-text download | `LIVE_ATTEMPT_FAILED` | The 12-query run attempted current `paper-search-mcp` access, but six queries hit the 90s query timeout and six returned no candidates after the search command timed out at 30s. No live PDF/full-text success was established. |
| ccswitch provider connection | `LIVE_VERIFIED` | `POST /api/v1/settings/validate` with `live=true` and an 8s timeout returned HTTP 200, `ok=true`, `live_tested=true`, and `Provider connection succeeded.` via the Anthropic-compatible `/v1/messages` route. No secret was printed. |
| ccswitch full M1-to-M4 chain | `NOT_LIVE_VERIFIED` | Only the bounded provider connection was proven; no complete live acquisition, M2 card, and M4 answer chain was accepted. |
| 12-query acquisition matrix | `LIVE_ATTEMPT_FAILED` | `.venv\Scripts\python scripts/run_main_chain_matrix.py --skip-llm --use-cache --query-timeout-seconds 90 --max-failures 0` completed 12 rows in 992.7s: 0 passed, 0 degraded, 0 blocked, 12 failed; cache hits were 0 because the six-hour cache TTL had expired. |

Live tests remain opt-in through `RUN_LIVE_TESTS`, `RUN_LLM_TESTS`, and
`RESEARCHSENSEI_LIVE_EVAL`. Missing keys, rate limits, network errors, or an
unavailable ccswitch endpoint must remain explicit blockers; they are not
converted into passes.

## Remaining Risks

- GitHub Actions is committed but cannot be reported as remotely green until
  the branch is pushed and GitHub runs it.
- Current external paper search/full-text acquisition did not pass the live
  12-query run; network/provider timeout behavior remains a real release risk.
- The ccswitch connection is live-verified, but the complete live M1-to-M4
  product chain remains `NOT_LIVE_VERIFIED`.
- The local executor is intentionally single-host and SQLite-backed. It
  recognizes interrupted tasks after restart but is not a distributed queue.

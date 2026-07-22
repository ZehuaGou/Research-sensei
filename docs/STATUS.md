# ResearchSensei v0.6 Reliability Baseline Status

Last updated: 2026-07-22 (Asia/Shanghai).

This is the authoritative implementation and verification ledger for
ResearchSensei. Design documents describe contracts; this file records what was
actually checked. A skipped, mocked, cached, or offline result is never reported
as a live acceptance result.

## 2026-07-22 OpenCode PDF paper agent and persistent M4 session

M2 now has an optional OpenCode Server paper-agent path that is distinct from
the text-only OpenCode Go `/chat/completions` provider. PyMuPDF deterministically
preserves complete page text and PDF page numbers. OpenCode receives rendered
page images in bounded batches and supplies visual semantics: section headings,
displayed formulas, equation numbers, figures, tables, and printed page labels.
The resulting run stores `paper.md`, `paper_index.json`,
`opencode_analysis.json`, and the rendered pages. Existing passage/evidence,
formula-provenance, card, and QualityAuditor gates still run; visual formula
transcriptions are marked `ocr_latex` and are not promoted to source LaTeX.

Model capabilities are checked from the running OpenCode Server catalogue.
The configured `deepseek-v4-flash` rejected a raw `application/pdf` attachment
because that model supports neither PDF nor image input. The new PDF-agent
setting therefore defaults to the attachment-capable `qwen3.7-plus`; the web
settings page exposes chat and PDF-vision models separately. The app can start
a localhost-only `opencode serve` sidecar on demand and stops only the process
it started. If OpenCode is unavailable, M2 preserves page text with the
maintained parser and records an explicit degraded warning.

Live acceptance used the 11-page, 999,493-byte SmartRoot paper. All 11 pages
were visually analyzed in 129.7 seconds with no warnings, producing 96 blocks,
16 figure records, three table records, and zero displayed equations. The zero
count is a page-vision result, not the old raw-text formula heuristic. Continuing
the same OpenCode session answered a detailed segmentation/trait-extraction
question in about 27 seconds with the actual arc search, adaptive internode
distance, subpixel border detection, junction thresholds, SQL export, and a
clear separation between paper statements and explanatory synthesis.

A separate live formula regression rendered the formula-dense methodology page
of *Root Cause Analysis in Microservice Using Neural Granger Causal Discovery*.
It recovered five displayed formulas with their equation numbers and surrounding
contexts, including the contrastive loss, forecasting equation, MSE objective,
and thresholded causal graph. A final first-page probe recovered the complete
SmartRoot paper title rather than the running page header.

Verification: `849 passed, 15 skipped` backend tests; `98 passed` frontend unit
tests; changed-source Ruff; Vue type checking; and the production build all
passed. Live provider/PDF results above are separate from the deterministic
test totals.

## 2026-07-21 Historical-paper deep-read timeout correction

Downloaded papers opened from a saved direction were still using the legacy
synchronous `/api/v1/documents/parse` route. The browser stopped waiting after
120 seconds even though parsing and card generation continued on the server.
The real paper *A Novel Image-Analysis Toolbox Enabling Quantitative Analysis
of Root System Architecture* reproduced this defect: the page reported a
request timeout, while job `7825710bf2c3` completed successfully about 30
seconds later.

The history-paper action now uses the persistent document-task route, displays
real parsing progress, stores the active task id, and resumes that same task
after a refresh or temporary connection loss. A live browser click reopened
the already completed job through async task `ee153015a0b3427a` without a
timeout. The downloaded file was also checked independently: it is an 11-page,
approximately 1 MB full PDF with extractable text on every page, not an
abstract or publisher error page.

The first completed card had separately fallen back after a transient LLM
timeout. A live provider probe then passed and reparse task
`b54a0a7436634088` completed as job `e545a1660677`. The resulting workspace has
a real Chinese summary, research problem, core idea, method explanation, and
two teaching cards. Formula cards remain strictly blocked because the only
detected formula-like fragments have raw-text provenance; that evidence gate
was not weakened. Verification: 88 frontend unit tests, seven fixed-browser
E2E tests, Vue type checking, the production build, and the live browser flow
all passed.

## 2026-07-21 Formula-aware PDF recovery

The Web ingestion route now combines complete PyMuPDF text extraction with a
strict numbered-equation pre-screen and targeted MinerU2.5-Pro formula OCR.
MinerU runs only on the detected equation crops, rather than every PDF page,
and a crop is promoted to formula evidence only when MinerU returns LaTeX.
Heuristic raw fragments remain blocked. Formula evidence retains its page,
bounding box, equation number, surrounding source context, and `evidence_ref`.

The real AAAI paper *Root Cause Analysis in Microservice Using Neural Granger
Causal Discovery* was reparsed through the production task route. Task
`4e17af254d724a99` completed as job `79f3eb8ca348`: six numbered equation
regions were detected and all six were converted to trusted `mineru_latex`
blocks and formula cards. Five explanations completed; equation (4) retained
its evidence but was marked for retry after a transient upstream model HTTP
502. The workspace therefore presents `5 可用 · 1 待重试`, sorts the usable
cards by paper/equation order, and does not expose raw provider errors as a
learner-facing formula card. New runs record this condition as
`formula_cards=PARTIAL` while keeping the successful cards available.

The targeted crop parse took approximately 131 seconds on the configured CUDA
GPU. The complete production task took longer because of live LLM generation
and retry waits; parser throughput and model-service latency are reported as
separate concerns. A concurrent-test isolation defect discovered during this
acceptance was also fixed: constructing a test app can no longer mark tasks in
the real workspace as restarted, and a task owner clears stale interruption
errors on start and successful completion.

Verification after the correction: 813 backend tests passed with 15 skips; the
final no-CPU-fallback guard then passed the focused nine-test MinerU/runner
suite. In addition, 86 frontend unit tests and all seven fixed-browser E2E
tests passed; Ruff, Mypy (128 source files), Vue type checking, and the
production frontend build passed. The six-equation result above is a live
local GPU/parser and live LLM acceptance, not a fixture result.

## 2026-07-21 Deep-read progress and recovery correction

The direction and upload deep-read tasks no longer remain at
`resolving_source · 10%` while the complete M2/LLM chain runs. Progress now
comes from the actual ingestion pipeline and identifies source preparation,
document parsing, evidence indexing, evidence-pack construction, paper-card
generation, formula-card batches, teaching-card generation, quality audit, and
artifact persistence. Formula work reports `completed/total` batch counts. The
persistent task service keeps a progress high-water mark so parallel paper and
formula builders cannot make the displayed percentage move backwards.

Direction candidate cards show the current Chinese stage, percentage, and a
progress bar. The task ID is stored in browser local storage and the page
reattaches to the same deep-read task after a refresh or temporary connection
loss. Upload and reparse surfaces use the same translated stages. Before slow
LLM work begins, parsed structure and evidence artifacts are persisted and the
paper job moves to `evidence_ready`; card artifacts remain hidden until the
existing quality audit has completed. JSON artifact replacement is atomic, so
an interrupted write does not leave a partially written artifact.

The evidence contract is unchanged: QualityAuditor still runs before cards are
published, formula provenance and `evidence_ref` checks remain strict, and the
blocked `/cards` path remains fail-closed.

Verification for this correction:

| Check | Result | Classification |
|---|---|---|
| `.venv\Scripts\python -m pytest -q` | `807 passed, 15 skipped` in 267.56s. | Full deterministic backend regression. |
| `cd frontend; npm test` | `16` files, `83` tests passed. | Full frontend unit regression, including stage formatting, visible formula-batch progress, and deep-read resume. |
| `cd frontend; npm run build` | Passed; Vite transformed 95 modules. | Type check and production bundle. |
| `cd frontend; npm run test:e2e` | `7 passed` in 18.0s. | Fixed-browser fixture E2E, including visible `3/11` formula-batch progress before handoff. |
| changed-file Ruff and repository Mypy | Passed; Mypy found no issues in 127 source files. | Static verification. |
| headed Playwright inspection | Candidate card showed `正在生成公式卡片（3/11 批） · 61%`; reload reattached to the same stage. | Browser UI check with a controlled running-task response, not a live LLM run. |

The earlier successful ExplainIt live run remains the evidence for real
source/LLM/card correctness. This correction did not repeat the approximately
14-minute paid/live run, so it does not claim a new live duration or throughput
improvement; it fixes truthful observability, reload recovery, and safe
intermediate persistence.

## 2026-07-20 ExplainIt source, formula, and M4 live correction

The live arXiv deep-read path was exercised with `1903.08132`, *ExplainIt! --
A Declarative Root-cause Analysis Engine for Time Series Data*. This exposed
two separate source problems: a transient TLS failure caused an immediate PDF
fallback, and a successful source archive selected the larger bundled
`latex/vldb_sample.tex` instead of the paper's `explainit.tex`. arXiv source
downloads now retry transient failures and try both `/e-print/` and `/src/`.
LaTeX main-file selection now scores active document structure, included
sections, path depth, and sample/template filenames instead of choosing the
largest file with a `documentclass` token.

The same run exposed Anthropic-compatible output-budget failures. M4 previously
ended with only a `thinking` block at `max_tokens=3200`, and formula generation
could repeat the same failure per formula at 4500 tokens. Both paths now use a
12,000-token output budget with thinking disabled. Formula generation uses
bounded three-formula batches with three-way concurrency, retaining single-item
split/compact retries when a batch is incomplete. M4 content validation still
requires an allowed `evidence_ref` and a verbatim quote from the underlying
paper evidence. An audited, evidence-bound paper-card phrase may additionally
serve as a cross-language bridge when comparing a Chinese claim with English
source text; it cannot replace the source quote. The post-validation quality
check no longer requires 120 characters or a time-series-specific keyword for
every research-problem answer.

The clean live task `35449d4653604671` completed as job `db6223020399` in
approximately 13 minutes 50 seconds. It selected `explainit.tex` from the arXiv
source archive, reported `source_latex`/no OCR, produced 33 formula cards and two
teaching cards, and finished with all five understanding components at
`SUCCESS`, `quality_status=pass`, no structural degradation, and no top-level
warnings. A real M4 question, `这篇论文真正解决了什么问题？`, returned `SUCCESS`
in 40.6 seconds with two independently validated claims, three evidence refs,
and no warnings. A real follow-up carrying the frontend's conversation-history
payload set `continued_from_history=true` and `conversation=true`; one supported
claim was shown and one insufficiently matched claim was removed, so that turn
correctly remained `DEGRADED` rather than leaking the rejected text.

The single-stage progress defect observed in this run was corrected on
2026-07-21; see the section above. The measured live duration remains a real
performance baseline, while the new staged progress and recovery behavior has
deterministic and browser-fixture verification rather than a repeated live LLM
timing claim.

Deterministic verification after these changes: 805 backend tests passed with
15 skips; 79 frontend unit tests passed; mypy, Vue type checking, and the
production build passed; and all seven fixture-browser E2E tests passed. Focused
Ruff checks pass for every changed Python file. A repository-wide Ruff run still
reports 46 pre-existing findings under unrelated legacy `scripts/` files.

## 2026-07-20 Direction-workbench scrolling correction

The direction page previously mixed document scrolling, a fixed left sidebar,
a sticky right status card, and a composer placed at the end of the result
thread. Once the candidate list became long, the document grew beyond the
viewport and the composer was not actually sticky; users had to return to the
end of the page before starting the next search.

The shell and workbench frame are now constrained to the dynamic viewport. The
direction result thread is the only long-content scroll region, while the left
navigation has its existing independent history scroll, the right status card
remains reachable, and the composer occupies a persistent row below the result
thread. Overscroll is contained so a wheel gesture does not unexpectedly move
the whole document.

Current verification: 79 frontend unit tests passed; Vue type checking and the
production build passed; seven fixture-browser E2E tests passed. The new browser
regression uses a 1440 x 620 viewport, scrolls a completed direction result to
the end, checks that the composer and right status card remain inside the
viewport, and verifies that the document itself does not grow beyond one
viewport. The same geometry was checked against the currently running local
page: the document height remained 912 px, the result thread had 990 px of
content in a 699 px scroll region, and the composer remained visible at the
bottom of the 912 px viewport.

## 2026-07-20 Direction-search long-task recovery

A real UI submission for `时间序列根因分析` exposed a frontend/backend lifetime
mismatch. The frontend stopped polling after 180 seconds and displayed a red
timeout with zero candidates, while the persistent backend task continued and
successfully completed after about 293 seconds. The finished task retrieved 173
records, deduplicated them to 169, passed four candidates through the strict
relevance gate, and obtained verified deep-reading material for two of the four.

The direction UI now polls once per second for up to 30 minutes, persists the
active task ID and query in local browser storage, and resumes the same task
after a refresh or temporary network interruption instead of submitting a
duplicate search. The backend direction service reports actual pipeline stages
from query planning through source search, verification, full-text discovery,
ranking, downloading, and result assembly; the page renders those stages in
Chinese instead of remaining at `searching · 15%` for the entire run.

Verification after the correction: 799 backend tests passed with 15 skipped;
79 frontend tests and six fixture-browser E2E tests passed; Ruff, Mypy, Vue type
checking, and the production frontend build all passed. The completed live run
was reopened from the UI and showed four recorded candidates, one newly
downloaded source, one reused local source, and no browser console warnings.

## 2026-07-20 Complete M1 Revalidation

The configured user-authorized native-Chrome session and the production M1
service were revalidated from clean workspaces. This was not a fixed fixture or
a cached-library acceptance.

Three live-only defects were found and corrected during the run:

- publisher navigation could destroy the page execution context while the
  helper was extracting links, incorrectly reporting a browser-session failure;
  landing links are now captured before clicks and navigation is handled as an
  expected page transition;
- native Chrome was being opened for DOI, Semantic Scholar, and OpenAlex
  metadata-only pages that could not expose a PDF. Browser fallback is now
  limited to a concrete PDF candidate or a real publisher landing page;
- after ordinary publisher PDF attempts fail, a DOI is checked with PMC's
  [official ID Converter](https://pmc.ncbi.nlm.nih.gov/tools/id-converter-api/).
  A matching open PMCID is downloaded through the
  versioned PMC Cloud dataset before Chrome is considered.

Layered live source acceptance used three unrelated delivery paths:

| Source/path | Result | Evidence |
|---|---|---|
| PMLR direct OA | Passed | 673,298-byte validated PDF in 2.54s; no browser. |
| PMC Cloud (`PMC10490803`) | Passed | 3,844,369-byte validated PDF in 4.16s; no browser. |
| ACM OmniAnomaly with authorized native Chrome | Passed | 6,701,685-byte validated PDF in 6.64s; title matched. |

Four fresh production runs used the same real query,
`graph neural network multivariate time series anomaly detection`. Result count
was never used as a quota: only candidates passing the deterministic relevance
gate entered the download queue.

| Run | Relevant attempts / downloads | Time | Finding |
|---|---:|---:|---|
| Initial reproduction | 11 / 7 | 193.30s | Exposed publisher navigation-context failure. |
| High-variance external result | 49 / 21 | 457.12s | Exposed 28 unnecessary browser fallbacks, mostly metadata-only pages. |
| Browser-eligibility fix | 17 / 10 | 217.86s | Browser attempts fell to two; exposed an MDPI DOI with an available PMC copy. |
| Final production acceptance | 12 / 9 (75%) | 77.73s | `SUCCESS`; zero browser attempts and three DOI/PMC recoveries. |

The final run retrieved 204 source records, deduplicated them to 140, and left
three relevance-cleared IEEE, Elsevier, and ACM papers as landing-page-only
instead of substituting lower-relevance papers. The three recovered PMC papers
were GTAD (`PMC9222957`), Graph Attention Network and Informer
(`PMC10935277`), and Masked Graph Neural Networks (`PMC10490803`). A direct
repeat of the previously failing Masked GNN path completed in 5.01s with a
3,844,369-byte PDF, passed metadata/title checks, and did not start Chrome.

External search remains variable: Semantic Scholar returned HTTP 429 during the
final run, while the configured paper-search/OpenAlex paths still supplied the
candidate pool. Download success does not weaken the downstream M2 gate; the
final bundle still warned that some candidate metadata was unverified and kept
those papers out of `A_READ` until verification is complete.

### Browser consent and page-hydration follow-up

A visual inspection of the actual failed publisher windows confirmed that the
browser helper previously attempted PDF controls before handling Cookie/privacy
overlays. Springer displayed a viewport-blocking `Your privacy, your choice`
panel. The updated helper now recognizes both standard consent-management
markup and non-standard buttons whose labels explicitly mention cookies. It
prefers `reject optional`/necessary-only choices, accepts only when that is the
sole continuation control, and never treats an ordinary page-level `Accept` or
`Continue` button as consent.

The same screenshots separated genuine acquisition failures from UI blockers:

- Springer's overlay was dismissed successfully, after which the page clearly
  required chapter purchase or institutional login; this remains unavailable;
- ACM first displayed a transient security-check page and then a partially
  hydrated shell. Waiting for the check and network hydration recovered the
  1,633,615-byte PDF for `10.1145/3534678.3539117` in 25.42s;
- Elsevier displayed a human CAPTCHA. The helper records
  `BROWSER_USER_VERIFICATION_REQUIRED` and does not solve or bypass it;
- browser failures now retain the page-barrier category plus consent and final
  diagnostic screenshot paths in the source result and direction manifest.

A naive DOI-to-publisher retry downloaded 10/12 papers but opened three browser
windows and took 149.38s. Restricting DOI-only browser discovery to the
live-verified ACM route preserved 10/12 (83.3%) while reducing browser attempts
to one and total time to 108.12s. Concrete PDF candidates from any publisher
remain eligible for the authorized-browser fallback. The two unresolved papers
were the IEEE and Elsevier items with no OA/PDF candidate; no lower-relevance
paper was substituted.

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
- session capture and assisted download use a dedicated installed-Chrome
  profile launched without Playwright's automation marker; the helper connects
  locally only after the user finishes the publisher's legitimate verification.
- local browser-helper acceptance covered installed-Chrome startup, post-user
  CDP handoff, storage-state persistence, and a real PDF navigation/download;
  the PDF-viewer abort case is recovered through the same context's cookies and
  still requires `%PDF` validation.
- 2026-07-20 live ACM acceptance used the user-authorized dedicated session for
  OmniAnomaly (`10.1145/3292500.3330672`). The complete
  `PaperSourceResolver` path returned `RESOLVED_PDF_DOWNLOADED` with
  `resolution_strategy=authorized_browser_session`,
  `browser_mode=native_chrome_cdp`, 6,701,685 validated bytes, and a matching
  PDF title. The fallback is publisher-agnostic and is injected into the
  production M1 resolver, but it runs only after cache, official OA services,
  and ordinary HTTP candidates fail. This proves the tested session/path, not universal
  access to every ACM item; subscription and institutional permissions remain
  unchanged.

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
| 2026-07-20 final revalidation | 204 raw, 140 deduplicated, 12 strict-related attempted, 9 downloaded | `SUCCESS` in 77.73s; three DOI/PMC recoveries, zero browser attempts, and no relevance substitution. |
| Cookie-aware optimized revalidation | 204 raw, 140 deduplicated, 12 attempted, 10 downloaded | `SUCCESS` in 108.12s; one ACM browser recovery, one browser attempt, and two honest landing-only results. |

The final live run is a single-query acceptance, not a claim that every
publisher or every research direction will achieve a fixed count. The captured
authorized session passed the tested ACM OmniAnomaly path, but it does not imply
universal ACM or subscription access. The tested IEEE/Elsevier papers still had
no OA copy, while the blocked MDPI path was legally recovered through its DOI's
PMC record.
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
| `.venv\Scripts\python.exe -m pytest -q --maxfail=1` | `798 passed, 15 skipped` in 155.36s | Complete local backend/offline suite after the live fixes. |
| `.venv\Scripts\python.exe -m ruff check src tests` | Passed | Full backend and test lint. |
| `.venv\Scripts\python.exe -m mypy` | No issues in 127 source files | Full backend type boundary. |
| `npm test` | 15 files, 77 tests passed | Frontend unit/contract suite. |
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

### Root-system paper formula false-positive regression (2026-07-21)

- The PDF text parser previously promoted prose/table fragments such as
  `lines = parent root` and malformed `d = B)` into raw formula evidence. The
  raw-text admission rule now requires balanced delimiters plus an actual
  mathematical signal on the right-hand side of the assignment. Visual
  numbered equations continue through the MinerU crop parser; the rule does not
  replace trusted formula OCR with an LLM guess.
- Direct ingestion of the 999,493-byte source PDF for *A Novel Image-Analysis
  Toolbox Enabling Quantitative Analysis of Root System Architecture* returned
  `pymupdf_formula_prescreen`, `degraded=false`, and zero formula blocks.
- The first end-to-end reparse correctly skipped formula cards but the ccswitch
  upstream returned a transient HTTP 502 while building the paper card. A
  bounded live settings probe then returned `ok=true`, and reparse job
  `bc2db4cfd0ce` completed with `understanding_status=SUCCESS`,
  `paper_card=SUCCESS`, `formula_cards=SKIPPED`, `teaching_cards=SUCCESS`,
  `llm=SUCCESS`, and zero formula cards. The frontend now explains this valid
  no-formula state instead of saying that formulas can be explained.
- Verification: targeted backend ingestion tests `16 passed`; full backend
  suite `815 passed, 15 skipped`; Ruff and mypy passed; frontend StatusBanner
  tests `10 passed`; full frontend suite `89 passed`; production build passed.

### M4 exact-quote selection regression (2026-07-21)

- On GiA Roots job `941a6709af95`, M4 retrieved the correct `b002` source and
  produced a supported Chinese answer to “这篇论文真正解决了什么问题？”, but
  rejected the entire answer as `M4_CLAIM_UNSUPPORTED` when the model lightly
  paraphrased the English `supporting_quote` instead of copying it verbatim.
- Source evidence rows now receive server-generated `quote_id` values. The
  model selects an ID and the server binds its own exact source text. For
  providers that still omit the ID or paraphrase the quote, the server resolves
  the exact source row only when that ref exists and the claim independently
  passes the same content, number, dataset, formula, and threshold gates.
- An invented quote ID does not establish support: the regression case using
  an unsupported NASA/F1/12.5% claim remains rejected. Existing exact-quote
  payloads remain compatible.
- Live API and browser checks on the same GiA Roots question returned the
  correct problem statement with one supported claim and evidence ref
  `941a6709af95:b002`; the M4 panel displayed “1 条已验证证据” instead of deleting
  the answer. Targeted M4/memory tests reported `40 passed`; full backend tests
  reported `818 passed, 15 skipped`; Ruff and mypy passed.

### M4 detailed-list retrieval regression (2026-07-21)

- The GiA Roots PDF already contained the complete list of 19 RSA traits, but
  several overlapping passages shared the same evidence refs. M4 kept the
  earlier abstract passage, discarded the later trait-selection passage during
  deduplication, and then rejected the model's generic answer.
- M4 now ranks source passages for list questions, deduplicates by passage
  identity instead of only by evidence ref, and extracts a query-focused window
  from long passages. Generic phrases such as an author "list of" do not outrank
  a phrase that explicitly lists traits.
- Chinese list answers are validated item by item against an explicit bilingual
  RSA-trait alias table. The real 19-item translation passes only because every
  item occurs in the source list; a regression claim that adds chlorophyll
  concentration is rejected as `unsupported_trait_item`. Number, dataset,
  formula, threshold, exact-source, and evidence-ref gates remain unchanged.
- A live API request and an in-app browser retry of
  `GiA Roots软件具体提供了哪些根系结构性状？` returned `SUCCESS`, one supported
  claim, evidence ref `941a6709af95:b002`, all 19 traits, and no warnings. The
  M4 panel displayed `当前论文 · 1 条已验证证据` with the complete list.
- Verification: M4 API tests reported `34 passed`; full backend tests reported
  `819 passed, 15 skipped`; Ruff and mypy passed.

### M4 interactive timeout-budget regression (2026-07-22)

- The frontend previously aborted M4 calls after 95 seconds while the backend
  allowed a single model attempt to run for 120 seconds and could retry it.
  The browser therefore displayed a generic request-timeout error while the
  backend was still working, even when verified selected-text evidence was
  already available.
- Interactive M4 model calls are now bounded to 80 seconds with no transport
  retry, and the optional structured-JSON repair pass is independently capped
  at 25 seconds. The frontend M4 request budget is 120 seconds, so it remains
  alive long enough to receive either the validated model result or the
  backend's controlled response.
- When a selected-text request times out or the model transport fails, M4 keeps
  only the artifact-derived explanation whose evidence refs and claims have
  already passed validation. It explicitly says that model enhancement did not
  finish and that no unverified model output was used. Generic paper questions
  still fail closed instead of receiving a fabricated local answer.
- A live API request on GiA Roots job `941a6709af95` returned in 63.04 seconds
  with evidence refs `b001` and `b002`. A separate in-app browser retry of the
  original selected-text question exercised the 80-second model timeout and
  displayed the verified `b001` explanation plus the controlled degradation
  notice instead of `请求超时`.
- Verification: targeted backend tests reported `50 passed`; the full backend
  suite reported `821 passed, 15 skipped`; targeted frontend tests reported
  `12 passed`, and the full frontend suite reported `90 passed`. Ruff, mypy,
  frontend typecheck, and the production build passed.

### M4 evidence-first answer regression (2026-07-22)

- The timeout fallback above was still too narrow. Paper-card actions such as
  `用中文讲透这篇论文` intentionally ignore their generated Chinese summary as
  raw source evidence, but the timeout fallback required a non-ignored text
  selection. In addition, a model response rejected as
  `M4_CLAIM_UNSUPPORTED` could replace an already available artifact answer
  with the generic failure card.
- M4 questions now use two phases. `evidence_only` returns the deterministic,
  evidence-bound paper-card answer without calling the model or persisting a
  duplicate memory record. The frontend displays that result immediately and
  then requests `enhanced` output in the background. A successful audited model
  result replaces the preview; an empty, timed-out, invalid, or unsupported
  model result cannot replace a preview that already has verified evidence.
- The backend also preserves any locally verified artifact answer when the
  model transport times out or fails. Unsupported model claims remain rejected;
  the change retains the independent artifact answer rather than admitting the
  rejected model text. Questions with no traceable evidence still fail closed.
- On GiA Roots job `941a6709af95`, the exact screenshot question returned a
  1,679-character evidence answer with refs `b001` and `b002` in 222 ms without
  calling the model. The enhancement request then timed out after 80.7 seconds
  and retained the same answer. A separate in-app browser run exercised
  `M4_CLAIM_UNSUPPORTED`: the page showed the evidence answer immediately,
  removed the loading state after model validation, kept the answer, and added
  only the controlled enhancement notice.
- Verification: M4 API tests reported `37 passed`; the full backend suite
  reported `823 passed, 15 skipped`. Targeted frontend tests reported
  `14 passed`, and the full frontend suite reported `92 passed`. Ruff, mypy,
  frontend typecheck, and the production build passed.

### M4 model-service latency root cause and direct OpenCode Go route (2026-07-22)

- The fast settings probe was not representative of M4: it used 128 output
  tokens and a trivial prompt. A real GiA Roots M4 request contained about
  2,535 input tokens. Through CC Switch's Anthropic-to-OpenAI conversion,
  `thinking: disabled` was dropped and `deepseek-v4-pro` spent all 2,400 output
  tokens on a thinking block in 39.98 seconds, returning no text. Historical
  local proxy records showed similar non-streaming requests taking 62-78
  seconds with roughly 4,900-5,600 output tokens.
- A direct probe of the same configured OpenCode Go upstream proved that its
  native OpenAI request field `thinking: {"type":"disabled"}` works: a bounded
  response returned text in 2.32 seconds with zero reasoning content. The
  problem was therefore the protocol transform, not basic provider
  connectivity and not an unavoidable model-service delay.
- ResearchSensei's `opencode_go` provider now sends the native thinking control.
  When its API key environment variable is absent, a narrow read-only bridge
  may resolve the credential from the active matching CC Switch Claude
  provider. It refuses non-HTTPS or mismatched upstreams, keeps the credential
  in memory, and can be disabled with
  `RESEARCHSENSEI_CCSWITCH_CREDENTIAL_BRIDGE=0`.
- On GiA Roots job `941a6709af95`, the real follow-up `说得再详细一些，这到底是什
  么，怎么实现的？` completed in 10.97 seconds with `used_context.llm=true`,
  seven accepted evidence-bound claims, and evidence ref `b002`. One additional
  unsupported claim was removed and reported as a warning; the evidence gate
  remained fail-closed.
- Verification: focused provider/M4 tests reported `65 passed`; the full backend
  suite reported `831 passed, 15 skipped`. Ruff and mypy passed.

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

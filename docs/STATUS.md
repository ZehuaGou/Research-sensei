# ResearchSensei Status

## Current Gate

本文件只记录真实工程状态。mock/unit tests 可以证明局部逻辑没有坏，但不能证明模块完成，也不能替代 live validation。

当前整改重点：M1 Literature Search 必须从“模拟/薄 wrapper”升级为真实链路：

`real LLM query planning -> mature source adapters -> metadata merge/dedup -> real PDF download/validation -> A_READ reading plan gate`

## Status Levels

| Level | Meaning |
|---|---|
| NOT_STARTED | 没有代码或文档 |
| DOC_ONLY | 只有文档 |
| UNIT_TESTED | 有单元测试，但没有真实外部链路验证 |
| LIVE_SEARCH_VERIFIED | 真实联网搜索通过 |
| REAL_LLM_VERIFIED | 真实 LLM 调用通过 |
| REAL_PDF_VERIFIED | 真实 PDF 下载、文件头、大小、sha256 校验通过 |
| M1_REAL_VERIFIED | M1 真实链路通过：LLM + 多源搜索 + PDF + A_READ gate |
| PRODUCTION_READY | 可用于稳定生产环境 |

## Module Matrix

| Module | Code Status | Test Status | Real Status | Notes |
|---|---|---|---|---|
| M1.1 Query Planning | implemented | unit tested | REAL_LLM_VERIFIED | 无 LLM 时硬失败，不再 heuristic fallback |
| M1.2 Acquisition | implemented | unit tested | LIVE_SEARCH_VERIFIED | 使用 `arxiv`, `pyalex`, `semanticscholar`, `habanero`；OpenAlex/Crossref live success，arXiv 429 与 Semantic Scholar 连接失败已记录 |
| M1.3 Source Acquisition | implemented | unit tested | REAL_PDF_VERIFIED | live eval 下载并校验 2 个 PDF，记录 sha256/local_path |
| M1.4 Selection | implemented | unit tested | M1_REAL_VERIFIED | dedup/score 使用真实 metadata 字段；A_READ 受 PDF/M2 gate 约束 |
| M1.5 Reading Plan | implemented | unit tested | M1_REAL_VERIFIED | live eval 产生 2 个 A_READ，均 `can_enter_m2=true` |
| M2+ | unchanged | existing tests | not part of current gate | 本轮不把 synthetic markdown 或 M2 smoke 作为 M1 完成依据 |

## Completed In This Pass

- Added mature dependencies in `pyproject.toml`: `arxiv`, `pyalex`, `semanticscholar`, `habanero`.
- Replaced self-written arXiv/OpenAlex HTTP parsing wrappers with mature package adapters.
- Added Semantic Scholar and Crossref adapters through adapter boundaries.
- Removed QueryPlanner heuristic fallback. Missing/invalid LLM planning now raises `QueryPlanningError`.
- Added real M1 PDF acquisition fields: `download_status`, `final_url`, `content_type`, `file_size`, `sha256`, `local_path`, `error_code`.
- Reworked reading plan gate so A_READ requires downloadable/validated full text and `can_enter_m2`.
- Replaced live eval completion definition with M1 real validation only. Synthetic M2 markdown is no longer accepted as M1 evidence.
- Deleted `docs/audit/FULL_PROJECT_REALITY_AUDIT.md` as requested by the uploaded correction document.

## Current Test Results

- Default backend regression: `python -m pytest -q` -> `485 passed`.
- Opt-in live tests without live env: `python -m pytest -q tests_live` -> `1 passed, 2 skipped`.
- Required real validation command:

```powershell
$env:RUN_LIVE_TESTS="1"
$env:RUN_LLM_TESTS="1"
$env:RESEARCHSENSEI_LIVE_EVAL="1"
$env:RESEARCHSENSEI_MAX_LIVE_CASES="5"
$env:RESEARCHSENSEI_MAX_LLM_COST_USD="1.00"
$env:RESEARCHSENSEI_MAX_LLM_TOKENS="30000"

python -m pytest -q tests_live
python scripts/run_live_eval.py
```

Latest live result:

- `python -m pytest -q tests_live` with live env -> `2 passed`.
- `python scripts/run_live_eval.py` with live env -> `m1_status=passed`, `candidate_count=10`, `pdf_download_success_count=2`, `a_read_count=2`.
- Source failures are explicitly recorded, not hidden: arXiv returned HTTP 429; Semantic Scholar connection failed in the current network environment.

## Hard Rules

- Do not count mock, MockTransport, MockLLMClient, synthetic markdown, or local fixture-only paths as module completion.
- Network tests are opt-in and must not be part of default pytest.
- Third-party tools must be isolated behind adapters.
- API keys, `.env`, reports, downloaded PDFs, and large generated files must not be committed.
- M1 is complete only if live validation shows real LLM query planning, at least one mature source success, real candidate metadata, at least one validated PDF download, and at least one A_READ item cleared for M2.

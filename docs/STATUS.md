# ResearchSensei Status

## Current Gate

本文件只记录真实工程状态。

M1 测试必须真实运行：真实 LLM、真实 arXiv、真实 OpenAlex/pyalex、真实 Semantic Scholar、真实 Crossref、真实 PDF 下载。mock/fake/skip 不作为有效测试。缺 key、缺网络、API 限流、PDF 下载失败均视为失败。

当前整改重点：M1 Literature Search 必须从”模拟/薄 wrapper”升级为真实链路：

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
| M1.1 Query Planning | implemented | real tested | REAL_LLM_VERIFIED | 真实 LLM (mimo-v2.5-pro) query planning，无 heuristic fallback |
| M1.2 Acquisition | implemented | real tested | LIVE_SEARCH_VERIFIED | 4 源全部成功（arXiv/OpenAlex/Semantic Scholar/Crossref）。arXiv 使用 httpx + 自定义 User-Agent + 429/503 retry。Semantic Scholar 使用 httpx REST adapter + proxy 支持 |
| M1.3 Source Acquisition | implemented | real tested | REAL_PDF_VERIFIED | live eval 下载并校验 7 个 PDF，记录 sha256/local_path |
| M1.4 Selection | implemented | real tested | M1_REAL_VERIFIED | dedup/score 使用真实 metadata 字段；A_READ 受 PDF/M2 gate 约束 |
| M1.5 Reading Plan | implemented | real tested | M1_REAL_VERIFIED | live eval 产生 5 个 A_READ，均 `can_enter_m2=true` |
| M2+ | existing docs | mock tests deleted | not verified | M2 必须真实 PDF + 真实 LLM 验收，mock 测试已删除 |

## M1 Live Eval Results (2026-06-05)

- All 4 sources succeeded: arXiv, OpenAlex, Semantic Scholar, Crossref
- 15 candidates, 7 PDFs downloaded, 5 A_READ papers
- All A_READ have `can_enter_m2=true`
- arXiv: httpx + custom User-Agent + 429/503 retry/backoff + Rate exceeded body detection
- Semantic Scholar: httpx REST adapter with `trust_env=True` for proxy support
- Source resolver: PDF download with retry/backoff + User-Agent + %PDF header validation
- LLM: mimo-v2.5-pro, 530 tokens

## Completed In This Pass

- Added mature dependencies in `pyproject.toml`: `arxiv`, `pyalex`, `semanticscholar`, `habanero`.
- Replaced arXiv `arxiv` package with httpx-based adapter: custom User-Agent, 429/503/Rate exceeded retry, id_list lookup, multi-query strategy.
- Replaced Semantic Scholar `semanticscholar` package with httpx REST adapter: proxy support (trust_env=True), API key support, 429/503 retry.
- Added OpenAlex and Crossref adapters through adapter boundaries.
- Removed QueryPlanner heuristic fallback. Missing/invalid LLM planning now raises `QueryPlanningError`.
- Added real M1 PDF acquisition fields: `download_status`, `final_url`, `content_type`, `file_size`, `sha256`, `local_path`, `error_code`.
- Enhanced source_resolver PDF download with retry/backoff and User-Agent.
- Reworked reading plan gate so A_READ requires downloadable/validated full text and `can_enter_m2`.
- Replaced live eval completion definition with M1 real validation only. Synthetic M2 markdown is no longer accepted as M1 evidence.
- Deleted `docs/audit/FULL_PROJECT_REALITY_AUDIT.md` as requested by the uploaded correction document.

## Current Test Results

- `python -m pytest -q` 现在默认运行 tests_live。缺 env/key/network 时 tests_live 会失败，不会 skip。
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

- mock/fake/skip 不是有效测试。全项目测试策略：真实优先。
- `python -m pytest -q` 默认运行所有测试，包括 tests_live。
- 缺 key / 缺网络 / 额度不足 / API 限流 / PDF 下载失败 = 测试失败。
- MockLLMClient 已从 src/ 和 tests/ 中删除。
- M2 mock 测试已删除。M2 必须真实 PDF + 真实 LLM 验收。
- API keys, `.env`, reports, downloaded PDFs, and large generated files must not be committed.
- M1 is complete only if live validation shows real LLM query planning, at least one mature source success, real candidate metadata, at least one validated PDF download, and at least one A_READ item cleared for M2.

## ARIS Alignment Summary

ResearchSensei's "科研自动化" reference project is ARIS (`wanshuiyin/Auto-claude-code-research-in-sleep`).

| Module | ARIS Overlap | Reuse Mode | Key Boundary |
|---|---|---|---|
| M1 | High | STRATEGY_BORROW | Search backend remains best-of-breed (OpenAlex/Semantic Scholar/Crossref/arXiv). ARIS provides verification/download discipline. |
| M2 | Medium-High | STRATEGY_BORROW + ADAPTER_REUSE | ARIS verification_status/source discipline enhance evidence and audit. Parser/formula/evidence_ref remain ResearchSensei-specific. |
| M3 | Low (code), Medium (schema) | STRATEGY_BORROW | No ARIS UI to reuse. Display fields borrow verification/relevance/source structure. |
| M4 | High | STRATEGY_BORROW + PROMPT_BORROW | ARIS research-review/research_wiki strongly inform M4.3-M4.6. M4.1/M4.2 formula teaching remains self-built. |
| M5 | Medium | STRATEGY_BORROW | ARIS run traces/session recovery/threat_scan are useful references. Real test discipline must not degrade.

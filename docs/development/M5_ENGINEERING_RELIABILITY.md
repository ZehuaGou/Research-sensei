# M5 工程可靠性与测试保障

---

## 1. 模块目标

定义全局工程可靠性与测试保障规则：后端测试、前端测试、LLM smoke、缓存、安全、debug 权限、CI。M5 定义 M1-M4 的真实验收矩阵，但不替代各模块测试。

## 2. 非目标

- 不实现 Parser / Evidence / LLM 业务逻辑
- 不改 frontend
- 不替代 M1-M4 的子模块测试

## 3. 产品流程位置

M5 是横切支撑模块，保障 M1-M4 的可靠性、安全性、可测试性。

**M5 不替代 M1-M4 子模块测试。** M1-M4 每个 Mx.y 仍必须独立完成：文档 → 代码 → 测试 → 验收。M5 负责全局测试基础设施和工程保障，不是"最后统一测试模块"。

## 3.5 M1-M5 真实验收矩阵

M5 定义 M1-M4 的真实验收矩阵，不替代各模块测试。

### M1 Direction Exploration

- broad direction query live eval
- survey_candidates exists
- direction_landscape exists
- method families and stages sufficient
- Status: NOT_IMPLEMENTED

### M1 Focused Acquisition

- focused query live eval
- A_READ_FOR_M2 verified + source + title match
- Status: REAL_E2E_VERIFIED

### M1 Source Acquisition (LaTeX source priority)

- query arXiv paper with LaTeX source
- `latex_source_downloaded == true`
- `latex_main_file` exists
- `source_resolution.preferred_m2_input == latex_source`
- Status: DOC_DESIGNED / NOT_IMPLEMENTED

### M1 Material Normalization / canonical_paper.md

- real paper source
- `canonical_paper.md` exists
- front matter contains paper_id/title/source_type/source_confidence/canonicalization_status/parser_used/m2_ready/degradation_reason
- body contains abstract or enough body text
- formula blocks include formula_id and formula_origin when formulas are present
- Status: DOC_DESIGNED / NOT_IMPLEMENTED

### M1 FormulaRegionDetector / FormulaOCRAdapter

- 1 real paper
- 1 real formula region
- real FormulaRegionDetector output: formula_id, bbox, page, confidence
- real FormulaOCRAdapter output when policy triggers: formula_latex, formula_origin=ocr_latex, formula_ocr_status
- `canonical_paper.md` writes OCR result with origin and warning
- Status: DOC_DESIGNED / NOT_IMPLEMENTED

### M1 Seed Paper Expansion

- seed paper → upstream/downstream/related surveys
- paper_relation_graph exists
- Status: NOT_IMPLEMENTED

### M2 Paper Deep Reading

- real `canonical_paper.md` input
- M2.1 canonical reader validation
- paper/formula/teaching cards
- evidence_ref
- Status: not verified

### M2 LaTeX Source Parse Eval

- real arXiv source package
- LaTeXSourceParser extracts sections
- extracts at least one display formula
- formula evidence `source_origin == latex_source`
- `formula_card.original_latex` exists
- Status: DOC_DESIGNED / NOT_IMPLEMENTED

### M2 PDF-Only Fallback Eval

- real PDF-only paper
- MinerU or Docling parses
- `formula_origin` recorded
- PyMuPDF fallback cannot pass formula high-confidence test
- Status: DOC_DESIGNED / NOT_IMPLEMENTED

### M2 Canonical Formula Eval

- real `canonical_paper.md`
- one formula block with `source_latex` or `parser_latex`
- one formula block with `ocr_latex` when OCR policy triggers
- M2 reads formula_id/formula_latex/formula_origin/formula_bbox/formula_page/formula_context_before/formula_context_after/formula_ocr_status/formula_explanation_status
- source_latex can pass high-confidence formula explanation if evidence_ref valid
- ocr_latex must preserve OCR warning
- unknown origin blocks detailed derivation
- Status: DOC_DESIGNED / NOT_IMPLEMENTED

### Hardware Note

User target hardware:
- RTX 4060
- 8GB VRAM

Parser evaluation must record:
- `runtime_device`
- `peak_vram_estimate` or observed VRAM if available
- `parser_runtime_seconds`
- `parser_resource_error`

### M2 Survey Deep Reading

- survey PDF parse
- method_taxonomy
- extracted_key_papers
- Status: NOT_IMPLEMENTED

### M3 Frontend

- DirectionWorkspace
- PaperWorkspace
- SeedExpansionPanel
- Status: NOT_IMPLEMENTED

### M4 Interactive Learning

- paper-level Q&A
- direction-level Q&A
- seed-expansion Q&A
- advisor questions
- Status: NOT_IMPLEMENTED

### M5 Reliability

- real tests
- secret scan
- cost control
- CI
- no PDF/report/API key committed

## External Projects / Adapter Candidates

| 项目 | 对应模块 | 具体能力 | 可复用文件/函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状态 |
|---|---|---|---|---|---|---|---|
| pytest | M5.1 | 后端测试、markers、env gates、live/manual/nightly 分层 | `pytest`, `pytest.ini/pyproject` markers, `-m`, env vars | DIRECT_DEPENDENCY | 是 | marker 设计不清会导致 live/heavy 测试混入默认回归 | IMPLEMENTED |
| pytest live markers / env gates | M5.1 / M5.3 | 真实测试分层：default / live / manual / nightly / slow / llm / network | `pytest.mark`, env gates `RUN_LIVE_TESTS`, `RUN_LLM_TESTS`, `RESEARCHSENSEI_LIVE_EVAL` | DIRECT_DEPENDENCY | 是 | 缺 env 时不能把 live validation 汇报为通过 | IMPLEMENTED |
| Vitest | M5.2 | 前端组件测试 | `vitest`, `frontend/src/components/tests/*` | DIRECT_DEPENDENCY | 是 | 组件测试不能替代页面级 E2E | IMPLEMENTED |
| Playwright | M5.2 / M5.7 | 真实前端 E2E；上传、学习页、方向页、seed expansion 页面验收 | `playwright test`, trace/screenshot/video, fixtures；必须调研 Vite+FastAPI 启动 fixture | DIRECT_DEPENDENCY | 否 | 浏览器安装和运行时间；需要隔离 artifacts | DOC_DESIGNED |
| gitleaks | M5.5 / M5.7 | secret scanning | `gitleaks detect`, config file, baseline support；必须调研 Windows CLI、CI exit code、allowlist | DIRECT_DEPENDENCY | 否 | 误报需要 allowlist；不能扫描进大文件 artifact | DOC_DESIGNED |
| TruffleHog | M5.5 / M5.7 | secret scanning / verification | `trufflehog git/filesystem`; 必须调研 AGPL/license、verification mode、CI exit code | OPTIONAL_ADAPTER | 否 | AGPL / 扫描重 / 网络 verification 成本 | RESEARCH_REQUIRED |

## 5. M5.1 后端测试

### 目标

定义后端 pytest 规则，区分快速回归测试和真实验收测试。

### 非目标

- 不替代 M1-M4 各模块的业务测试
- 不实现具体测试用例

### 输入

- `tests/` 目录
- `src/` 目录
- pytest 配置（`pyproject.toml`）

### 输出

- pytest 结果

### 核心工具 / 命令

```bash
# Current default tests
python -m pytest -q

# manual / nightly / optional live validation
RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python scripts/run_live_eval.py
```

### 状态流 / 错误策略

- `python -m pytest -q` 当前默认运行已实现的稳定单元/API/组件回归，不要求未实现的 canonical pipeline 通过
- Target default tests after canonical pipeline implementation 必须包含稳定小样本真实链路，但不把 heavy OCR / GPU parser / batch live eval 放入默认阻塞项
- mock/fake/skip 不是模块完成依据
- 缺 key / 缺网络 / 额度不足 / API 限流 / PDF 下载失败不能被汇报为真实验收通过
- MockLLMClient 已从 src/ 和 tests/ 中删除
- 涉及 LLM 的模块完成验收必须真实调用 LLM
- 涉及搜索的完成验收必须真实联网
- 涉及 PDF/source 的完成验收必须真实下载或读取材料
- default structural/real-smoke 和 manual/nightly live validation 必须在报告中明确区分

### Current default tests

Current default tests cover implemented behavior only:

```text
existing backend pytest suite
existing frontend component tests when invoked separately
implemented API/workspace/parser/status checks
no requirement to generate canonical_paper.md until canonical pipeline code exists
no requirement to run FormulaRegionDetector / FormulaOCRAdapter until those adapters exist
```

### Target default tests after canonical pipeline implementation

After the canonical pipeline is implemented, default tests must include a stable small real chain:

```text
search / load one real paper
generate canonical_paper.md
M2 reads canonical_paper.md
generate basic paper_card
```

Target formula chain default test:

```text
1 real paper
1 real formula region
real FormulaRegionDetector output
real FormulaOCRAdapter output when policy triggers
real canonical_paper.md write
M2 reads that formula block
```

### Manual/nightly heavy tests

These are formal validation targets but not default full-batch blockers:

```text
MinerU
Marker
DeepXiv live
pix2tex
GPU parser
large batch
multi-paper direction exploration
multi-formula OCR batch
```

### pytest markers

| marker | 用途 |
|--------|------|
| `live` | 真实外部服务测试 |
| `network` | 需要网络的测试 |
| `llm` | 真实 LLM 调用测试 |
| `slow` | 耗时测试 |

### 验收标准

- `python -m pytest -q` 全部通过
- Current default tests 只要求当前已实现能力通过
- Target default tests after canonical pipeline implementation 包含稳定小样本真实链路
- manual / nightly / optional live validation 真实联网、真实 LLM、真实 PDF/source、真实 OCR/parser when configured
- live validation 缺 env/key/network 时必须报告失败，不能汇报为通过

### 当前实现状态

- MockLLMClient 已从 src/ 和 tests/ 删除
- mock 测试文件已删除
- 真实验收：live eval 已实现（tests_live/ + scripts/run_live_eval.py）
- 默认小样本 canonical/formula 链路为 DOC_DESIGNED / NOT_IMPLEMENTED
- heavy OCR / GPU parser / batch live validation 为 DOC_DESIGNED / NOT_IMPLEMENTED 运行策略

---

## 6. M5.2 前端测试

### 目标

定义前端 Vitest 测试规则，确保组件测试覆盖关键交互逻辑。

### 非目标

- 不实现 e2e 测试（Playwright / Cypress 后置）

### 输入

- `frontend/src/` 目录
- Vitest specs

### 输出

- npm test 结果

### 核心工具 / 命令

```bash
cd frontend
npm run build
npm test
```

### 状态流 / 错误策略

- 前端测试必须真实后端联调（DOC_DESIGNED / NOT_IMPLEMENTED）
- 当前 StatusBanner 7 tests 是组件级测试，不是页面验收
- M3 验收必须真实 PDF 上传 → 后端处理 → 前端展示

### 测试要求

| 测试 | 断言 |
|------|------|
| test_status_banner_baseline_only | BASELINE_ONLY 显示 amber warning |
| test_status_banner_blocked | BLOCKED 显示 red error + blocking_reason |
| test_status_banner_degraded | DEGRADED 显示 indigo warning + missing components |
| test_status_banner_failed | FAILED 显示 red error |

### 验收标准

- StatusBanner 有测试覆盖（当前 7 tests，组件级，非页面验收）
- LearningWorkspaceView 需要真实后端联调验收
- UploadView 需要真实 PDF 上传验收

### 当前实现状态

- 已实现：StatusBanner 7 tests（组件级，非页面验收）
- 未实现：LearningWorkspaceView 真实后端联调
- 未实现：UploadView 真实 PDF 上传验收
- Vitest + Vue Test Utils + jsdom 已引入

---

## 7. M5.3 LLM Smoke / 成本控制

### 目标

定义真实 LLM smoke / quality eval 规则，确保涉及 LLM 的模块必须通过真实验收。

### 非目标

- 不允许把 mock 测试通过当作 LLM 模块完成

### 测试策略

全项目测试策略：真实优先。mock/fake/skip 不是有效测试。

涉及 LLM 的模块（M2.3, M2.4, M2.5）必须通过真实 LLM 验收才能标记为完成。MockLLMClient 已从 src/ 和 tests/ 中删除。

real LLM smoke 属于 live validation。默认测试可以运行稳定小样本真实链路；涉及成本、外部服务和 heavy parser/OCR 的 live validation 使用显式环境变量运行。缺 API key 时不能汇报为 live validation 通过。

### 输入

- 环境变量
- model config
- smoke prompt

### 输出

- live smoke report（模型名、prompt version、schema version、运行日期、token 用量、成本）

### 核心工具 / 命令

```bash
# 默认小样本真实回归
python -m pytest -q

# manual / nightly / optional live validation
RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 \
RESEARCHSENSEI_MAX_LIVE_CASES=3 \
RESEARCHSENSEI_MAX_LLM_COST_USD=1.00 \
RESEARCHSENSEI_MAX_LLM_TOKENS=20000 \
python -m pytest -q

RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 \
python scripts/run_live_eval.py
```

### 状态流 / 错误策略

- `python -m pytest -q` 默认运行稳定小样本真实链路
- live validation 缺 key / 缺网络 = 真实验收失败，不能 skip 后汇报通过
- 必须有 token limit
- 必须有 cost limit
- 必须限制样例数量
- 必须记录模型名、prompt version、schema version、运行日期
- 涉及 LLM 的验收必须真实调用 LLM。成本通过 token limit / cost limit / sample limit 控制，而不是用 mock 替代
- live eval report 写入 `reports/live_eval/live_eval_report.json`
- `reports/live_eval/` 必须加入 `.gitignore`，报告、工作目录、PDF、大文件不得提交
- 如果缺少 API key，真实 LLM 测试必须 fail，并报告明确失败原因；不得 skip 后算通过

### 测试要求

| 测试 | 断言 |
|------|------|
| test_llm_smoke_real_execution | python -m pytest -q 在配置真实 env 时必须真实执行；缺 key 时必须失败，不能 skip |
| test_llm_smoke_token_limit | token 用量不超过限制 |
| test_llm_smoke_records_metadata | 记录模型名、prompt version、运行日期 |
| test_m1_live_search_and_source_resolution | 显式开启后真实 arXiv/OpenAlex 检索，并记录 source resolution |
| test_m2_real_llm_smoke | 显式开启后真实 LLM 走 M2 parser/evidence/v2 builders/audit/status |
| test_real_pdf_end_to_end | 真实搜索 → 真实 PDF 下载 → parser → evidence → LLM → audit → status |
| test_full_live_eval_writes_report | 写出 live eval report 且不包含 secret 值 |
| test_target_default_real_canonical_chain | after canonical pipeline implementation: one real paper → canonical_paper.md → M2 reader → basic paper_card |
| test_target_default_formula_chain_one_region | after formula pipeline implementation: one real formula region → FormulaRegionDetector → FormulaOCRAdapter when triggered → canonical block → M2 read |
| test_nightly_formula_ocr_batch | multi-formula OCR batch under nightly/manual marker |
| test_nightly_mineru_marker_pipeline | MinerU/Marker full flow under nightly/manual marker |

### 验收标准

- Local structural check may be run separately for developer convenience, but it is not module acceptance and not release validation
- 涉及 LLM 的模块必须通过真实 LLM 验收才能标记完成
- 缺 API key 时必须失败，不能 skip 后算通过
- token 和成本受控
- live eval 能区分 mock 回归和真实效果评估
- live eval report 不提交 git
- 真实 PDF e2e 必须真实下载 PDF，不能用 synthetic 替代
- Target canonical_paper.md chain 必须真实写入并被 M2 读取；当前代码未实现时不得作为 current default gate
- formula OCR/parser heavy validation 按 manual / nightly / optional 运行策略执行

### 当前实现状态

- 已实现：`tests_live/`（含 test_real_pdf_end_to_end.py）
- 已实现：`scripts/run_live_eval.py`（skip=fail 严格化）
- 已实现：`src/researchsensei/live_eval.py`（含 run_real_pdf_end_to_end_eval）
- 支持 `RUN_LIVE_TESTS`, `RUN_LLM_TESTS`, `RESEARCHSENSEI_LIVE_EVAL`
- 支持 `RESEARCHSENSEI_MAX_LIVE_CASES`, `RESEARCHSENSEI_MAX_LLM_COST_USD`, `RESEARCHSENSEI_MAX_LLM_TOKENS`
- 支持 OpenAI-compatible provider（通过现有 `LLMClient` 和 `config/local.toml`）
- 真实 PDF e2e：搜索 → PDF 下载 → parser → evidence → LLM → audit → understanding_status
- 成本估算默认只在配置价格环境变量时有意义；未配置价格时仍以 token limit 控制
- canonical_paper.md 默认真实链路、FormulaRegionDetector、FormulaOCRAdapter、MinerU/Marker/pix2tex manual/nightly validation 为 DOC_DESIGNED / NOT_IMPLEMENTED

---

## 8. M5.4 缓存与复用

### 目标

定义 LLM 缓存策略，减少重复调用，降低成本。

### 非目标

- 不 cache Parser / BM25 / EvidenceRetriever
- cache 不等于 M4 的论文学习知识库（memory）

### 输入

- prompt hash
- model config
- schema version

### 输出

- cached LLM response

### 核心工具 / 命令

- `ResponseCache`（已实现基础版本）

### cache key 组成

| 字段 | 说明 |
|------|------|
| model | 模型名 |
| prompt_version | prompt 版本 |
| prompt_hash | prompt 内容 hash |
| schema_version | 输出 schema 版本 |
| temperature | 温度参数 |
| input_hash | 关键输入 hash |

### cache 与 memory 区分

| 维度 | cache | memory (M4) |
|------|-------|-------------|
| 定位 | 请求级 / 计算级复用 | 论文学习知识库 / 长期记忆 |
| 生命周期 | 请求级 | 跨会话 |
| 内容 | LLM 原始响应 | 结构化知识 |
| 持久化 | 不进 Git | 待定（JSON / DB） |

### 状态流 / 错误策略

- cache 不进 Git
- 测试环境默认关闭或使用临时 cache
- cache 失效策略和 schema_version / model config 相关
- 生产/本地默认开启策略为 DOC_DESIGNED / NOT_IMPLEMENTED

### 测试要求

| 测试 | 断言 |
|------|------|
| test_cache_key_includes_all_fields | cache key 包含 model/prompt_version/prompt_hash/schema_version/temperature |
| test_cache_not_in_git | cache 文件在 .gitignore 中 |
| test_cache_disabled_in_test | 测试环境默认关闭 cache |
| test_cache_invalidation_on_schema_change | schema_version 变更 → cache 失效 |

### 验收标准

- LLM cache key 包含所有必要字段
- cache 不进 Git
- 测试环境默认关闭
- cache 与 M4 memory 明确区分

### 当前实现状态

- 已实现：ResponseCache 基础版本
- 未实现：完整 cache key 策略
- 未实现：cache 失效策略

---

## 9. M5.5 安全与密钥扫描

### 目标

防止敏感信息泄露到仓库。

### 非目标

- 不实现运行时安全（鉴权归 M5.6）

### 输入

- repo files
- commit diff

### 输出

- secret scan result

### 核心工具 / 命令

- gitleaks（候选）
- trufflehog（候选）
- pre-commit hooks（候选）

### 扫描关键词

- `sk-`
- `api_key`
- `OPENAI_API_KEY=`
- `ANTHROPIC_API_KEY=`
- `DEEPSEEK_API_KEY=`
- `MIMO_API_KEY=`

### 禁止提交内容

| 类型 | 示例 |
|------|------|
| 环境变量 | `.env`, `.env.*` |
| API key | 任何 API key |
| 缓存 | cache 目录 |
| 运行产物 | runs / artifacts |
| 大文件 | 大模型文件、checkpoint、数据库文件 |
| 敏感日志 | API key、prompt 全文、超长论文文本 |

### 状态流 / 错误策略

- `.env.example` 只能放 placeholder
- commit message 不允许 Claude / Happy / Anthropic contributor 信息
- 日志禁止打印 API key、prompt 全文、过长论文文本
- 日志应包含 `job_id` / `run_id` / `artifact_name`

### 测试要求

| 测试 | 断言 |
|------|------|
| test_no_env_committed | `.env` 不在 git 中 |
| test_no_api_key_in_code | 代码中无硬编码 API key |
| test_gitignore_covers_cache | .gitignore 覆盖 cache / runs / artifacts |

### 验收标准

- secret scanning 覆盖常见 key pattern
- `.env` / key / cache / 大文件不提交
- 日志不打印敏感信息

### 当前实现状态

- 未实现：secret scan 工具未正式接入
- 已有：.gitignore 覆盖基本规则
- 项目有过真实 key 泄露历史

---

## 10. M5.6 Debug/admin 权限

### 目标

控制 debug/admin API 访问权限，保护敏感数据。

### 非目标

- 不实现前端鉴权 UI

### 输入

- admin/debug auth signal
- request path

### 输出

- allow/deny debug API access

### API 权限矩阵

| API | 普通用户 | debug/admin | 当前实现 |
|-----|---------|-------------|---------|
| /understanding_status | ✅ | ✅ | ✅ |
| /cards | ✅（按 status gating） | ✅ | ✅ |
| /artifacts | ❌ 403 | ✅ | ✅（SENSEI_DEBUG=1） |
| /quality_report | ❌ 403 | ✅ | ❌ endpoint 未实现 |

### 状态流 / 错误策略

- 当前 `SENSEI_DEBUG=1` 只适合本地开发
- 生产环境必须正式鉴权
- `/artifacts` 是 debug/admin raw API
- `/quality_report` 是 debug/admin API（endpoint 未实现）
- 普通用户端不能通过 `/artifacts` 取 cards
- raw artifact 可能包含敏感内容，脱敏策略为 DOC_DESIGNED / NOT_IMPLEMENTED

### 测试要求

| 测试 | 断言 |
|------|------|
| test_artifacts_no_debug_403 | SENSEI_DEBUG 未启用 → /artifacts 返回 403 |
| test_artifacts_debug_enabled | SENSEI_DEBUG 启用 → /artifacts 返回数据 |
| test_normal_user_cannot_access_artifacts | 普通用户不能访问 /artifacts |

### 验收标准

- `/artifacts` 默认 403
- `SENSEI_DEBUG=1` 时可访问
- 普通前端不调用 `/artifacts`
- 正式 admin 鉴权待实现

### 当前实现状态

- 已实现：SENSEI_DEBUG 环境变量控制
- 未实现：正式 admin 鉴权机制
- 未实现：/quality_report endpoint
- 未实现：raw artifact 脱敏策略

---

## 11. M5.7 CI 与发布检查

### 目标

定义 CI 和发布检查规则，确保发布前所有质量门通过。

### 非目标

- 不实现 CI 平台配置（GitHub Actions 等为 DOC_DESIGNED / NOT_IMPLEMENTED）

### 输入

- test commands
- build commands
- secret scan

### 输出

- release readiness result

### Release check 清单

| 检查项 | 命令 / 方法 |
|--------|------------|
| 后端测试 | `python -m pytest -q` |
| 前端构建 | `cd frontend && npm run build` |
| 前端测试 | `cd frontend && npm test` |
| secret scan | gitleaks / trufflehog（待接入） |
| .env 未提交 | `git ls-files .env` 应为空 |
| key 未提交 | grep 扫描 |
| cache/artifacts 未提交 | 检查 gitignore |
| debug API 不暴露 | /artifacts 默认 403 |
| 文档状态准确 | 未实现项不写成已实现 |

### 状态流 / 错误策略

CI / release readiness 必须区分三类结果：

1. local structural check: 可以只证明代码结构和构建没有明显错误；不能标记模块完成；不能标记 release ready
2. target default small real chain after canonical pipeline implementation: 必须跑稳定小样本真实链路，包括 `canonical_paper.md` 写入与 M2 读取；当前未实现时不能作为 current default gate
3. real release validation: 必须真实联网；必须真实调用 LLM；必须真实下载/解析 source/PDF；必须按配置运行 OCR/parser live validation；必须运行 frontend build/test；必须运行 secret scan；失败则不得发布

如果 CI 环境没有配置 API key / network / live env，只能报告 "real release validation not run"，不能报告 release ready

### 测试要求

| 测试 | 断言 |
|------|------|
| test_release_check_pytest_passes | pytest 全部通过 |
| test_release_check_frontend_builds | frontend build 成功 |
| test_release_check_frontend_tests | frontend tests 全部通过 |
| test_release_check_no_env | .env 未提交 |
| test_release_check_no_api_key | 无硬编码 API key |

### 验收标准

- release check 覆盖 pytest + frontend build + frontend test
- secret scan 覆盖常见 key pattern
- 失败时不得发布

### 当前实现状态

- 未实现：CI 未配置
- 未实现：secret scan 工具未接入
- 已有：手动 release check 可执行

---

## 12. Error Taxonomy

### Parser

- `PARSER_FAILED`
- `PDF_PARSE_FAILED`
- `UNSUPPORTED_FILE_TYPE`

### Evidence

- `NO_PASSAGES`
- `NO_CLAIMS`
- `MISSING_METHOD_EVIDENCE`

### LLM

- `LLM_UNAVAILABLE`
- `LLM_TIMEOUT`
- `LLM_INVALID_JSON`
- `LLM_INVALID_EVIDENCE_REF`

### Audit

- `AUDIT_HARD_FAIL`
- `AUDIT_INTERNAL_ERROR`

### API

- `UNAUTHORIZED_DEBUG_ACCESS`
- `STATUS_BLOCKED`

### 规则

- pipeline/job 层 warnings 用 `WarningItem`
- audit 层 findings 用 `AuditFinding`
- job 层错误写 `Job.error`
- 日志应包含 `job_id` / `run_id` / `artifact_name`
- 日志禁止打印 API key、prompt 全文、过长论文文本

---

## 13. Artifact Versioning

- 每个 v2 artifact 顶层应显式写 `schema_version="v2"`
- 旧 artifact 没有 `schema_version` 时按 v1 读取
- additive schema change 通过 Pydantic 默认值兼容
- breaking change 的 migration 策略为 DOC_DESIGNED / NOT_IMPLEMENTED
- `artifact_manifest.json` 为 DOC_DESIGNED / NOT_IMPLEMENTED
- `artifact_manifest` / `content_hash` / `dependencies` 可能需要，不能永久否定

### Artifact 原子写入

- `WorkspaceStore.write_json` 应采用 tmp + rename
- 写入失败时 `job.status=FAILED`
- 部分 artifact 写成功后不回滚，用于 debug
- 已写 artifact 倾向不覆盖
- rerun 创建新 run_id，resume 才复用已有 artifact

### rerun / resume

- resume 默认 `False`，必须显式开启
- resume 按 artifact 是否存在 + schema_version 是否匹配决定是否跳过
- schema_version 不匹配时强制重跑
- resume 和 LLM cache 是独立机制

---

## 14. External Reference Implementation Notes

- **Reference source**: ARIS `skills/research-review/SKILL.md` (Review Tracing), `tools/research_wiki.py` (threat scan / quarantine pattern), shared helper resolution pattern
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Review traces; output manifest; session recovery; helper resolution; threat scan / quarantine; large-file hygiene
- **ResearchSensei-owned target**: `live_eval_report`, CI / release check, secret scan, debug/admin boundary, run logs
- **Schema / artifact impact**: `live_eval_report` should record sources, failures, token usage, artifacts, validation status. Run logs must not include keys. PDF/report/cache not committed.
- **Boundary**: ARIS graceful degradation cannot be adopted. ResearchSensei real-test failure = failure. mock/fake/skip are not acceptance.
- **Validation implication**: default pytest includes stable small real chain; manual/nightly live validation handles network/LLM/OCR/parser heavy cases. Missing env/key/network in live validation = fail. `git ls-files` must not include PDF / report / `.env`. Secret scan must pass.

---

## 15. 当前未解决问题

- artifact_manifest 是否需要
- content_hash 是否在 v2 初版加入
- resume 与 rerun 的 run_id 语义
- cache 默认开启策略
- debug/admin 鉴权机制
- `/artifacts` 是否需要脱敏版本
- secret scan 工具选型
- live smoke 样例 PDF 来源
- CI 是否强制 no-network monkeypatch
- LearningWorkspaceView / UploadView 页面级测试

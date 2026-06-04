# M5 工程可靠性与测试保障

---

## 1. 模块目标

定义全局工程可靠性与测试保障规则：后端测试、前端测试、LLM smoke、缓存、安全、debug 权限、CI。

## 2. 非目标

- 不实现 Parser / Evidence / LLM 业务逻辑
- 不改 frontend
- 不替代 M1-M4 的子模块测试

## 3. 产品流程位置

M5 是横切支撑模块，保障 M1-M4 的可靠性、安全性、可测试性。

**M5 不替代 M1-M4 子模块测试。** M1-M4 每个 Mx.y 仍必须独立完成：文档 → 代码 → 测试 → 验收。M5 负责全局测试基础设施和工程保障，不是"最后统一测试模块"。

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| Vitest | 前端测试 | vitest.dev | devDependency | 否 | 无 | ✅ 已引入 |
| pytest | 后端测试 | pytest.org | devDependency | 是 | 无 | ✅ 已使用 |
| gitleaks | secret scanning | github.com/gitleaks/gitleaks | CI tool | 否 | — | 待引入 |

---

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
# 快速回归（可 mock，不作为验收依据）
python -m pytest -q

# 真实验收（必须真实联网/LLM/PDF）
RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python -m pytest -q tests_live

# 排除 live/network/llm/slow 测试（仅用于快速回归）
python -m pytest -m "not live and not network and not llm and not slow"
```

### 状态流 / 错误策略

- 快速回归（`python -m pytest -q`）可使用 mock/fake，不作为模块验收依据
- 真实验收（`tests_live/`）必须真实联网、真实 LLM、真实 PDF
- 外部服务测试默认使用 `httpx.MockTransport`（仅限快速回归）
- LLM 测试默认使用 fake/mock client（仅限快速回归）
- live / network / llm / slow 测试通过 marker 从快速回归中排除
- 普通 CI 跑快速回归；真实验收由开发者手动触发

### pytest markers

| marker | 用途 | 默认排除 |
|--------|------|---------|
| `live` | 真实外部服务测试 | 是 |
| `network` | 需要网络的测试 | 是 |
| `llm` | 真实 LLM 调用测试 | 是 |
| `slow` | 耗时测试 | 是 |

### 测试要求

| 测试 | 断言 |
|------|------|
| test_default_pytest_no_network | 默认 pytest 不访问外部网络 |
| test_default_pytest_no_real_llm | 默认 pytest 不调用真实 LLM |
| test_markers_exclude_live | live marker 测试被默认排除 |

### 验收标准

- 快速回归 `python -m pytest -q` 全部通过
- 真实验收 `RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python scripts/run_live_eval.py` 全部通过
- 快速回归可使用 mock/fake，但不能作为模块完成依据
- 真实验收必须真实联网、真实 LLM、真实 PDF

### 当前实现状态

- 快速回归：489 tests，全部通过
- 真实验收：live eval 已实现（tests_live/ + scripts/run_live_eval.py）
- 真实 PDF e2e：已实现（run_real_pdf_end_to_end_eval）

---

## 6. M5.2 前端测试

### 目标

定义前端 Vitest 测试规则，确保组件测试覆盖关键交互逻辑。

### 非目标

- 不实现 e2e 测试（Playwright / Cypress 后置）
- 不启动真实后端

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

- 不启动真实后端
- fetch 使用 mock
- 组件测试不代替 e2e
- 新增依赖必须先讨论

### 测试要求

| 测试 | 断言 |
|------|------|
| test_status_banner_baseline_only | BASELINE_ONLY 显示 amber warning |
| test_status_banner_blocked | BLOCKED 显示 red error + blocking_reason |
| test_status_banner_degraded | DEGRADED 显示 indigo warning + missing components |
| test_status_banner_failed | FAILED 显示 red error |
| test_workspace_fetches_status | LearningWorkspaceView mount 时 fetch understanding_status |
| test_workspace_no_cards_when_blocked | BLOCKED 时不 fetch cards |
| test_upload_sends_formdata | UploadView 用 FormData 调用 /parse |

### 验收标准

- StatusBanner 有测试覆盖
- LearningWorkspaceView 有页面级测试
- UploadView 有页面级测试
- fetch 使用 mock，不启动真实后端

### 当前实现状态

- 已实现：StatusBanner 7 tests
- 未实现：LearningWorkspaceView 页面级测试
- 未实现：UploadView 页面级测试
- Vitest + Vue Test Utils + jsdom 已引入

---

## 7. M5.3 LLM Smoke / 成本控制

### 目标

定义真实 LLM smoke / quality eval 规则，确保涉及 LLM 的模块必须通过真实验收。

### 非目标

- 不允许在快速回归中真实调用 LLM（成本控制）
- 不允许把 mock 测试通过当作 LLM 模块完成

### mock 测试 vs real LLM 效果评测

mock 测试和 real LLM 效果评测定位不同：

| 维度 | mock/fake 测试 (M5.1) | real LLM smoke / quality eval (M5.3) |
|------|----------------------|--------------------------------------|
| 目的 | 测系统稳定性、pipeline 逻辑、artifact 正确性 | 测真实模型效果、输出质量、evidence binding |
| 用途 | 快速回归 | **模块验收** |
| 调用 LLM | 否（fake/mock client） | 是（真实 API） |
| 进入快速回归 | 是 | 否（成本控制） |
| 作为验收依据 | **否** | **是** |
| 成本控制 | 无成本 | 必须有 token/cost limit |

**mock 测试只能证明代码局部逻辑没坏，不能证明产品可用。** 涉及 LLM 的模块（M2.3, M2.4, M2.5）必须通过真实 LLM 验收才能标记为完成。

real LLM smoke / quality eval 通过 `RUN_LLM_TESTS=1` 显式运行，记录 token、cost、模型名、样例集、prompt version、schema version 和失败原因。缺 API key 时必须失败，不能 skip 后算通过。

### 输入

- 环境变量（显式开启）
- model config
- smoke prompt

### 输出

- live smoke report（模型名、prompt version、schema version、运行日期、token 用量、成本）

### 核心工具 / 命令

```bash
# 通过环境变量显式开启
RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 \
RESEARCHSENSEI_MAX_LIVE_CASES=3 \
RESEARCHSENSEI_MAX_LLM_COST_USD=1.00 \
RESEARCHSENSEI_MAX_LLM_TOKENS=20000 \
python -m pytest -q tests_live

RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 \
python scripts/run_live_eval.py
```

Windows PowerShell:

```powershell
$env:RUN_LIVE_TESTS="1"
$env:RUN_LLM_TESTS="1"
$env:RESEARCHSENSEI_LIVE_EVAL="1"
$env:RESEARCHSENSEI_MAX_LIVE_CASES="3"
$env:RESEARCHSENSEI_MAX_LLM_COST_USD="1.00"
$env:RESEARCHSENSEI_MAX_LLM_TOKENS="20000"
python -m pytest -q tests_live
python scripts/run_live_eval.py
```

### 状态流 / 错误策略

- real LLM smoke 是 opt-in
- 必须通过 `RUN_LLM_TESTS=1` 显式开启
- 真实联网必须通过 `RUN_LIVE_TESTS=1` 显式开启
- live eval 总开关必须设置 `RESEARCHSENSEI_LIVE_EVAL=1`
- 不进入普通 pytest
- 必须有 token limit
- 必须有 cost limit
- 必须限制样例数量
- 必须记录模型名、prompt version、schema version、运行日期
- 失败不能影响普通 CI，但必须记录失败原因
- 不允许默认真实调用 LLM
- live eval report 写入 `reports/live_eval/live_eval_report.json`
- `reports/live_eval/` 必须加入 `.gitignore`，报告、工作目录、PDF、大文件不得提交
- 如果缺少 API key，真实 LLM 测试必须 skip 或报告明确失败原因，不得伪装通过

### 测试要求

| 测试 | 断言 |
|------|------|
| test_llm_smoke_opt_in | 快速回归中不执行，RUN_LLM_TESTS=1 时必须执行且不能 skip |
| test_llm_smoke_token_limit | token 用量不超过限制 |
| test_llm_smoke_records_metadata | 记录模型名、prompt version、运行日期 |
| test_m1_live_search_and_source_resolution | 显式开启后真实 arXiv/OpenAlex 检索，并记录 source resolution |
| test_m2_real_llm_smoke | 显式开启后真实 LLM 走 M2 parser/evidence/v2 builders/audit/status |
| test_real_pdf_end_to_end | 真实搜索 → 真实 PDF 下载 → parser → evidence → LLM → audit → status |
| test_full_live_eval_writes_report | 写出 live eval report 且不包含 secret 值 |

### 验收标准

- 快速回归不调用真实 LLM（成本控制）
- 涉及 LLM 的模块必须通过真实 LLM 验收才能标记完成
- 缺 API key 时必须失败，不能 skip 后算通过
- token 和成本受控
- live eval 能区分 mock 回归和真实效果评估
- live eval report 不提交 git
- 真实 PDF e2e 必须真实下载 PDF，不能用 synthetic 替代

### 当前实现状态

- 已实现：`tests_live/`（含 test_real_pdf_end_to_end.py）
- 已实现：`scripts/run_live_eval.py`（skip=fail 严格化）
- 已实现：`src/researchsensei/live_eval.py`（含 run_real_pdf_end_to_end_eval）
- 支持 `RUN_LIVE_TESTS`, `RUN_LLM_TESTS`, `RESEARCHSENSEI_LIVE_EVAL`
- 支持 `RESEARCHSENSEI_MAX_LIVE_CASES`, `RESEARCHSENSEI_MAX_LLM_COST_USD`, `RESEARCHSENSEI_MAX_LLM_TOKENS`
- 支持 OpenAI-compatible provider（通过现有 `LLMClient` 和 `config/local.toml`）
- 真实 PDF e2e：搜索 → PDF 下载 → parser → evidence → LLM → audit → understanding_status
- 成本估算默认只在配置价格环境变量时有意义；未配置价格时仍以 token limit 控制

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
- 生产/本地是否默认开启可后续实现时决定

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
- raw artifact 可能包含敏感内容，后续需要脱敏策略

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

- 不实现 CI 平台配置（GitHub Actions 等后续）

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

- 不真实联网
- 不真实调用 LLM
- 失败时不得发布
- CI 默认排除 live / network / llm / slow 测试

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
- breaking change 未来再引入 migration
- 暂不引入 `artifact_manifest.json`
- `artifact_manifest` / `content_hash` / `dependencies` 未来可能需要，不能永久否定

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

## 14. 当前未解决问题

- artifact_manifest 是否未来需要
- content_hash 是否在 v2 初版加入
- resume 与 rerun 的 run_id 语义
- cache 默认开启策略
- debug/admin 鉴权机制
- `/artifacts` 是否需要脱敏版本
- secret scan 工具选型
- live smoke 样例 PDF 来源
- CI 是否强制 no-network monkeypatch
- LearningWorkspaceView / UploadView 页面级测试

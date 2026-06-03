# Engineering Reliability 模块

---

## 1. 模块目标

定义 artifact versioning、原子写入、resume/cache、CI、security、debug API、error taxonomy 等工程可靠性规则。

## 2. 非目标

- 不实现 Parser / Evidence / LLM 业务逻辑
- 不改 frontend

## 3. Artifact Versioning

- 每个 v2 artifact 顶层应显式写 `schema_version="v2"`。
- 旧 artifact 没有 `schema_version` 时按 v1 读取。
- additive schema change 通过 Pydantic 默认值兼容。
- breaking change 未来再引入 migration。
- 暂不引入 `artifact_manifest.json`。
- `artifact_manifest` / `content_hash` / `dependencies` 未来可能需要，不能永久否定。

## 4. Artifact 原子写入

- `WorkspaceStore.write_json` 应采用 tmp + rename。
- 写入失败时 `job.status=FAILED`。
- 部分 artifact 写成功后不回滚，用于 debug。
- 已写 artifact 倾向不覆盖。
- rerun 创建新 run_id，resume 才复用已有 artifact。
- resume 与 rerun 的 run_id 语义仍未完全确定，保留为未决。

## 5. rerun / resume

- resume 默认 `False`，必须显式开启。
- resume 按 artifact 是否存在 + schema_version 是否匹配决定是否跳过。
- schema_version 不匹配时强制重跑。
- resume 和 LLM cache 是独立机制。
- 具体是否"同一 run 继续"还是"新 run 复用旧 artifact"仍未决。

## 6. Cache Strategy

- 初版只 cache LLM。
- Parser / BM25 / EvidenceRetriever 不 cache。
- LLM cache key 包含：
  - model
  - prompt_version
  - prompt_hash
  - schema_version
  - temperature
- cache 不进 Git。
- 测试环境默认关闭 cache。
- 生产/本地是否默认开启可后续实现时决定。

## 7. CI / pytest

- 默认 pytest 不联网、不真实调用 LLM。
- 需要 pytest markers：
  - `live`
  - `network`
  - `llm`
  - `slow`
- 只定义 marker 不够，默认 pytest/CI 命令必须排除：
  `pytest -m "not live and not network and not llm and not slow"`
- `tests_live/` 默认不跑。
- live / network / llm 测试必须用环境变量显式开启：
  `RUN_LIVE_TESTS=1`
  `RUN_LLM_TESTS=1`
- 外部 adapter 测试默认用 MockTransport。
- 是否强制 no-network monkeypatch 仍未决。

## 8. Secret Scanning / Repo Hygiene

- 项目有过真实 key 泄露历史，必须加入 secret scan。
- 扫描关键词：
  - `sk-`
  - `api_key`
  - `DEEPSEEK_API_KEY=`
  - `MIMO_API_KEY=`
  - `OPENAI_API_KEY=`
  - `ANTHROPIC_API_KEY=`
- `.env.example` 只能放 placeholder。
- `.env`、`.env.*`、cache、runs、artifacts、大模型文件、数据库文件不得提交。
- commit message 不允许 Claude / Happy / Anthropic contributor 信息。
- 具体工具未定：pre-commit / gitleaks / trufflehog 后续实现时选。

## 9. debug/admin 权限和 raw artifacts

- `/cards` 是用户端受控 API。
- `/understanding_status` 是用户端状态 API。
- `/artifacts` 是 debug/admin raw API。
- `/quality_report` 是 debug/admin API。
- 普通前端不应直接用 `/artifacts` 展示 cards。
- 本地开发可用 `SENSEI_DEBUG=1`。
- production 必须有鉴权。
- debug/admin 鉴权机制仍未决。

## 10. Error Taxonomy

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

- pipeline/job 层 warnings 用 `WarningItem`。
- audit 层 findings 用 `AuditFinding`。
- job 层错误写 `Job.error`。
- 日志应包含 `job_id` / `run_id` / `artifact_name`。
- 日志禁止打印 API key、prompt 全文、过长论文文本。

## 11. Live Smoke / External Adapter Validation

- live smoke 独立 `tests_live/`。
- 默认不跑，不阻塞普通 CI。
- 通过 `RUN_LIVE_TESTS=1` 显式开启。
- Docling adapter 接入前至少需要样例：
  - simple PDF
  - formula-heavy PDF
  - table-heavy PDF
  - scanned PDF
- 需要记录外部项目版本和验证日期。
- 样例 PDF 来源和版权仍未决。

## 12. 当前未解决问题

- artifact_manifest 是否未来需要。
- content_hash 是否在 v2 初版加入。
- resume 与 rerun 的 run_id 语义。
- cache 默认开启策略。
- debug/admin 鉴权机制。
- `/artifacts` 是否需要脱敏版本。
- secret scan 工具选型。
- live smoke 样例 PDF 来源。
- CI 是否强制 no-network monkeypatch。

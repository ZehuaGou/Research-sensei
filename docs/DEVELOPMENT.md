# ResearchSensei Development Document

---

## 1. 当前开发状态

- Phase 1-11 baseline complete，281 tests passing。
- Phase 12 冻结，不允许写代码。
- 下一步只能是 Phase 11.6 ParserAdapter。
- Phase 11.6 代码开发必须等用户确认本文档中的 Phase 11.6 章节。

---

## 2. 通用开发规则

- 只改授权文件。
- 不改旧 `backend/`。
- 不改 `frontend/`，除非阶段明确授权。
- 不新增依赖，除非先更新复用结论。
- 默认 pytest 不联网、不调用真实 LLM。
- 所有外部 HTTP 测试用 `httpx.MockTransport`。
- 所有 LLM 测试用 `MockLLMClient`。
- 不提交 `.env` / API key / 缓存 / 大文件。
- 不写 Claude 贡献者信息。

---

## 3. Phase 1-11 Baseline Contract

### Phase 1: 项目骨架 / CLI / FastAPI health

- 核心文件：`__init__.py`, `__main__.py`
- 能力：`python -m researchsensei` healthcheck, `/health` endpoint
- 测试：`test_package_healthcheck.py` (4)
- Invariant：`python -m researchsensei` 必须可用

### Phase 2: 配置 / 日志 / 错误 / Schema

- 核心文件：`core/config.py`, `core/errors.py`, `core/logging.py`, `schemas/`
- 能力：ConfigService, StatusEnvelope, EvidenceType, BlockType
- 测试：`test_core_config.py` (5), `test_core_errors_logging.py` (4), `test_schemas_core.py` (6)
- Invariant：API key 不进日志

### Phase 3: Workspace / Job Store

- 核心文件：`workspace/store.py`, `jobs/store.py`
- 能力：run 目录创建, SQLite job 持久化
- 测试：`test_workspace_store.py` (4), `test_job_store.py` (4)
- Invariant：WorkspaceStore 创建 run dir, JobStore 持久化到 SQLite

### Phase 4: 单篇文档解析

- 核心文件：`ingestion/lightweight.py`
- 能力：.md/.txt/.pdf 解析，降级处理
- artifact：`parsed_document.json`
- 测试：`test_lightweight_ingestion.py` (4)
- Invariant：不支持的文件类型必须降级
- **限制**：PyMuPDF fallback 质量低

### Phase 5: Source Resolver + Parse API

- 核心文件：`source_resolver.py`, `web/app.py`
- 能力：upload/local_path/pdf_url/arxiv_id 解析, FastAPI API
- artifact：`source_status.json`
- 测试：`test_source_resolver.py` (10), `test_api_parse_sources.py` (8), `test_api_documents_parse.py` (5), `test_api_jobs_artifacts.py` (4)
- Invariant：路径穿越必须拒绝

### Phase 6: Grounding / Evidence + Paper Skeleton

- 核心文件：`grounding.py`, `paper_skeleton.py`, `schemas/evidence.py`, `schemas/skeleton.py`
- 能力：evidence index, paper skeleton
- artifact：`evidence_index.json`, `paper_skeleton.json`
- 测试：`test_phase6_evidence_schemas.py` (4), `test_phase6_grounding.py` (2), `test_phase6_paper_skeleton.py` (2)
- Invariant：无证据的 claim 必须标 INSUFFICIENT_EVIDENCE
- **限制**：**block-level evidence，不是 claim-level grounding**

### Phase 7: LLM 基础设施

- 核心文件：`llm/client.py`, `llm/prompt_builder.py`, `llm/response_cache.py`, `llm/token_budget.py`, `llm/types.py`
- 能力：LLMClient, MockLLMClient, PromptBuilder, ResponseCache, TokenBudget
- 测试：`test_llm_client.py` (24), `test_prompt_builder.py` (13), `test_response_cache.py` (18), `test_token_budget.py` (8), `test_llm_config.py` (7)
- Invariant：所有 LLM 调用通过 `llm/client.py`

### Phase 8: Paper Card JSON v1

- 核心文件：`paper_card.py`, `schemas/cards.py`
- 能力：rule-based + LLM-enhanced paper card
- artifact：`paper_card.json`
- 测试：`test_paper_card_schema.py` (7), `test_paper_card_builder.py` (11)
- Invariant：core_idea 必须有 evidence_ref 或降级
- **限制**：**rule-based baseline，不是导师级讲解。LLM-enhanced 未接入主 pipeline。**

### Phase 9: Formula Cards JSON v1

- 核心文件：`formula_card.py`
- 能力：rule-based + LLM-enhanced formula cards
- artifact：`formula_cards.json`
- 测试：`test_formula_card_schema.py` (7), `test_formula_card_builder.py` (10)
- Invariant：generic symbol dict 必须标 REASONABLE_INFERENCE
- **限制**：**generic symbol dictionary，不是 paper-context grounding。**

### Phase 10: Teaching Cards JSON v1

- 核心文件：`teaching_card.py`
- 能力：rule-based + LLM-enhanced teaching cards（五层讲解法）
- artifact：`teaching_cards.json`
- 测试：`test_teaching_card_schema.py` (5), `test_teaching_card_builder.py` (17)
- Invariant：human_explanation 不能是公式文本
- **限制**：**rule-based baseline，不是导师级讲解。LLM-enhanced 未接入主 pipeline。**

### Phase 11: Direction Pipeline v1

- 核心文件：`query/planner.py`, `acquisition/arxiv_adapter.py`, `acquisition/openalex_adapter.py`, `selection/service.py`, `direction/runner.py`
- 能力：query planning, arXiv/OpenAlex search, three-way dedup, reading plan
- artifact：`query_plan.json`, `candidate_pool.json`, `filtered_candidates.json`, `reading_plan.json`
- 测试：`test_query_planner.py` (5), `test_acquisition_adapters.py` (7), `test_direction_runner.py` (7), `test_direction_schemas.py` (10), `test_selection_service.py` (16)
- Invariant：A_READ ≤ 12, 三路去重 (DOI/arXiv/title)
- **限制**：**direction pipeline v1，不是完整 literature review。**

---

## 4. Phase 11.6 开发说明

### 目标

- 新增 `ParserAdapter` ABC interface
- 新增 `LightweightParserAdapter` 包装现有 parser
- 不改变现有 parser 行为
- 不接入 Docling/Nougat/Marker
- 不新增依赖
- 不改 pipeline / web / frontend / backend

### 允许创建

| 文件 | 用途 |
|------|------|
| `src/researchsensei/parser/__init__.py` | barrel export |
| `src/researchsensei/parser/adapter.py` | ParserAdapter ABC |
| `src/researchsensei/parser/lightweight_adapter.py` | LightweightParserAdapter |
| `tests/test_parser_adapter.py` | 测试 |

### 禁止修改

- `src/researchsensei/ingestion/**`
- `src/researchsensei/ingestion/pipeline.py`
- `src/researchsensei/web/**`
- `src/researchsensei/paper_card.py`
- `src/researchsensei/formula_card.py`
- `src/researchsensei/teaching_card.py`
- `frontend/**`
- `backend/**`
- `pyproject.toml`

### 接口定义

```python
from abc import ABC, abstractmethod
from pathlib import Path
from researchsensei.schemas.document import DocumentIngestion


class ParserAdapter(ABC):
    @abstractmethod
    def supports(self, source: Path) -> bool:
        ...

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        ...
```

### 实现要求

```python
class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None:
        self._ingestion = ingestion or LightweightIngestionService()

    def supports(self, source: Path) -> bool:
        return source.suffix.lower() in {".md", ".txt", ".pdf"}

    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        return self._ingestion.ingest_path(source, paper_id=paper_id)
```

规则：
- `.md`, `.txt`, `.pdf` 支持，`.MD`, `.TXT`, `.PDF` 支持
- `.markdown` 不支持
- adapter 不生成 paper_id（调用者传入）
- adapter 不写 artifact
- adapter 不更新 job
- adapter 不吞异常
- adapter 不复制 parser 逻辑
- adapter 只返回 `DocumentIngestion`

### 兼容性标准

adapter 输出必须与直接调用 `LightweightIngestionService.ingest_path()` 一致。比较字段：
- paper_id, detected_language, degraded
- warnings (code + message)
- blocks length, block_id, type, section, text, evidence_ref

### 测试清单

1. `test_parser_adapter_is_abstract` — `ParserAdapter()` raises TypeError
2. `test_lightweight_adapter_supports_md_txt_pdf_case_insensitive` — .md/.txt/.pdf=True, .markdown/.docx=False
3. `test_lightweight_adapter_rejects_unsupported_suffix` — .docx → False
4. `test_lightweight_adapter_matches_original_markdown_output` — 字段逐个比较
5. `test_lightweight_adapter_matches_original_txt_output` — 同上
6. `test_lightweight_adapter_parse_returns_document_ingestion` — isinstance check
7. `test_lightweight_adapter_json_round_trip` — dump → validate
8. `test_lightweight_adapter_does_not_write_artifacts` — 无文件写入
9. `test_lightweight_adapter_uses_injected_service` — DI 验证
10. `test_lightweight_adapter_propagates_or_preserves_degraded_behavior` — broken PDF → degraded=True

### 完成标准

- parser 包可导入
- ParserAdapter 不能实例化
- LightweightParserAdapter 输出与原 parser 一致
- 新测试通过
- full pytest 通过
- 无新依赖
- 未修改禁止文件
- 未改变 parser 行为
- 无真实网络/LLM
- 无 Phase 12 内容

---

## 5. Phase 11.7-11.9 草案

### Phase 11.7: PassageIndex + ClaimEvidence v2

- 升级 evidence 从 block-level 到 passage-level
- 实现 ClaimExtractor（rule-based）
- 升级 ClaimEvidence 支持 semantic support
- 实现 EvidenceRetriever
- 不允许 LLM-based claim extraction，不允许新依赖

### Phase 11.8: Evidence-constrained LLM Paper Understanding

- 将 LLM-enhanced card builder 接入主 pipeline
- 所有 LLM 输出必须绑定 evidence_ref
- MockLLMClient 默认测试
- LLM 失败 fallback 到 rule-based
- 不允许真实 LLM 默认测试

### Phase 11.9: Paper Understanding Quality Benchmark

- 小型 fixture benchmark
- explanation audit, formula audit, evidence audit
- hard-fail 条件覆盖
- 通过后才能解冻 Phase 12

---

## 6. Phase 12+ 简要路线

### Phase 12: Patterns + Drill（冻结）

- 解冻条件：Phase 11.6-11.9 完成 + quality gates 通过 + 用户确认
- 输出：`pattern_cards.json`, `drill_cards.json`
- 必须使用 v2 paper understanding，不能基于 rule-based baseline

### Phase 13+: 路线级

- Phase 13: Direction Map / Cross-paper Understanding
- Phase 14: Frontend / Render
- Phase 15: Advisor / Interactive QA
- Phase 16: Engineering Reliability
- Phase 17: Live Smoke / Real Paper Benchmark
- Phase 18: Packaging / Deployment

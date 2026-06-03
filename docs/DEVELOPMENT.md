# ResearchSensei Development

---

## 1. 通用开发规则

- 只改授权文件
- 不改旧 `backend/`
- 不改 `frontend/`，除非明确授权
- 不新增依赖，除非先更新复用结论
- 默认 pytest 不联网，不真实 LLM
- HTTP 测试用 `httpx.MockTransport`
- LLM 测试用 `MockLLMClient`
- 不提交 `.env` / key / 缓存 / 大文件
- 不写 Claude 贡献者信息

---

## 2. Parser 模块

### 目标

设计 ParserAdapter interface，包装现有 parser 为 default adapter。

### 输入 / 输出

- 输入：`Path source`, `str paper_id`（调用者传入，adapter 不生成）
- 输出：`DocumentIngestion`
- 不写 artifact，不更新 job，不调用 LLM，不联网

### 主要类

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

```python
class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None:
        self._ingestion = ingestion or LightweightIngestionService()

    def supports(self, source: Path) -> bool:
        return source.suffix.lower() in {".md", ".txt", ".pdf"}

    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        return self._ingestion.ingest_path(source, paper_id=paper_id)
```

### 错误处理

| 错误 | 行为 |
|------|------|
| 不支持的文件类型 | `supports()` 返回 False |
| 源文件不存在 | 沿用 LightweightIngestionService 行为 |
| 空文件 | `degraded=True`, `NO_TEXT_EXTRACTED` |
| PDF 解析失败 | `degraded=True`, `PDF_PARSE_FAILED` |

### 测试要求

- adapter 输出必须与直接调用 `LightweightIngestionService.ingest_path()` 一致
- 比较字段：paper_id, detected_language, degraded, warnings, blocks
- 不写 artifact 文件

### 可参考项目

Docling / Nougat / Marker / MinerU — 可选 parser adapter，暂不接入。

---

## 3. Evidence 模块

### 目标

从 block-level evidence 升级到 passage/claim-level evidence。

### 主要类

- `PassageIndex` — passage-level 文本索引
- `Passage` — passage_id, block_ids, section, text
- `ClaimExtractor` — 从 passage 提取语义 claim
- `ClaimEvidence` — v2 添加 passage_id, claim_type, semantic_support
- `EvidenceRetriever` — claim → passage 检索

### claim_type 候选

HYPOTHESIS / METHOD / RESULT / LIMITATION / CONTRIBUTION / DEFINITION

### semantic_support 候选

direct_quote / paraphrase / inference

### 规则

- 不允许把 section label 当 claim
- claim_text 必须是论文语义 claim
- 每个 claim 必须能回指原始 block/passage

### 可参考项目

PaperQA（passage retrieval / citation-backed answer）、OpenScholar（citation accuracy）、ARIS（paper-claim-audit / result-to-claim）。

---

## 4. Paper Understanding 模块

### 目标

基于证据生成学习卡片，LLM 输出必须绑定 evidence。

### 主要类

- `build_paper_card()` / `build_paper_card_with_llm()` — paper_card.py
- `build_formula_cards()` / `build_formula_cards_with_llm()` — formula_card.py
- `build_teaching_cards()` / `build_teaching_cards_with_llm()` — teaching_card.py
- `SinglePaperIngestionRunner` — ingestion/pipeline.py

### evidence_ref 要求

- 所有 LLM 输出必须有有效 `evidence_ref`
- 幻觉 `evidence_ref` → 拒绝 claim
- 无 evidence → 降级（INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK）

### LLM 失败 fallback

LLM 调用失败 → fallback 到 rule-based baseline。

### v2 质量门槛

- `core_idea` 必须不同于 `method_overview`
- formula symbol 必须来自论文上下文，不只是通用字典
- `human_explanation` 不能是公式文本
- generic symbol dict → `REASONABLE_INFERENCE`

### 禁止

- 不能直接整篇论文塞进 prompt
- 不能生成没有 evidence 的解释
- 不能把原文复制成 human_explanation

### 可参考项目

PaperQA（evidence-constrained answer）、OpenScholar（citation-backed response）、ARIS（reviewer independence / audit chain）。

---

## 5. Literature Search 模块

### 目标

搜索、筛选、排序论文，生成阅读计划。

### 主要类

- `QueryPlanner` — query/planner.py
- `ArxivAdapter` — acquisition/arxiv_adapter.py
- `OpenAlexAdapter` — acquisition/openalex_adapter.py
- `SelectionService` — selection/service.py
- `DirectionRunner` — direction/runner.py

### 输入输出

| 类 | 输入 | 输出 |
|----|------|------|
| QueryPlanner | user_query | QueryPlan |
| ArxivAdapter | query, max_results | CandidatePaper[] |
| OpenAlexAdapter | query, max_results | CandidatePaper[] |
| SelectionService | candidates | CandidatePool / ReadingPlan |
| DirectionRunner | user_query | DirectionBundle |

### 去重规则

DOI（剥离 prefix + 小写）→ arXiv ID（剥离 arXiv: + vN）→ normalized_title

### 评分权重

relevance (0.36) + venue_prestige (0.22) + citation (0.14) + code (0.06) + method_rep (0.14) + recency (0.08)

### 错误处理

adapter 失败 → 写入 warnings/search_log，不 crash。

### 可参考项目

ResearchPilot（structured findings）、STORM（outline / multi-perspective）、ARIS research-lit（多源检索）。

---

## 6. Audit / Quality 模块

### 目标

判断"讲得好"，不只是 schema 通过。

### 检查项

- explanation 有 evidence
- explanation 不是原文复制
- core_idea ≠ method_overview
- formula symbol 有依据
- teaching_card 有实际讲解
- uncertainty 正确降级

### hard-fail 条件

| ID | 条件 |
|----|------|
| HF-1 | 核心 claim 无 evidence_ref 且未降级 |
| HF-2 | human_explanation 是公式文本 |
| HF-3 | formula symbol 解释与论文矛盾 |
| HF-4 | core_idea / problem 缺 evidence_ref |
| HF-5 | 输出无论文特有术语 |
| HF-6 | 输出与论文主题不符 |

---

## 7. Workspace / Job / API 模块

### Workspace

- `WorkspaceStore` — 创建 run 目录，写 JSON/text
- 文件系统持久化

### Job Store

- `JobStore` — SQLite 持久化 job 状态
- CRUD：create / get / list_recent / update

### API

- FastAPI endpoints: `/health`, `/api/v1/documents/parse`, `/api/v1/jobs`, `/api/v1/jobs/{id}/artifacts`
- 不直接调用 LLM
- 路径穿越必须拒绝

### 失败状态

- job status: PENDING → RUNNING → SUCCEEDED / FAILED
- 失败时写 error + warnings

---

## 8. 测试规范

| 层 | 说明 |
|----|------|
| Schema tests | model_dump_json → model_validate_json round-trip |
| Artifact round-trip tests | 写 JSON → 读 → validate |
| Mock LLM tests | MockLLMClient，不真实调用 |
| MockTransport tests | httpx.MockTransport，不真实联网 |
| Quality hard-fail tests | 6 个 hard-fail 条件 |
| Live smoke tests | 必须单独隔离，不进默认 pytest |

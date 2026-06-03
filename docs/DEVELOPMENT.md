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

### 1. 模块目标

设计 ParserAdapter interface，包装现有 parser 为 default adapter，为未来接入高质量外部 parser 留接口。

### 2. 非目标

- 不接入 Docling / Nougat / Marker / MinerU
- 不新增依赖
- 不改变现有 parser 行为
- 不改 pipeline / web / frontend / backend

### 3. 参考 / 复用项目

| 项目 | GitHub/来源 | 用途 | 当前决策 |
|------|-----------|------|----------|
| Docling | `ds4sd/docling` (TO_VERIFY) | PDF/layout/table/structured document conversion | OPTIONAL_ADAPTER，当前不接入 |
| Marker | `VikParuchuri/marker` (TO_VERIFY) | PDF/Markdown 转换 | OPTIONAL_ADAPTER，当前不接入 |
| MinerU | `opendatalab/MinerU` (TO_VERIFY) | PDF 解析/OCR/layout | OPTIONAL_ADAPTER，当前不接入 |
| Nougat | `facebookresearch/nougat` (TO_VERIFY) | scientific PDF / math-aware parsing | OPTIONAL_ADAPTER，当前不接入 |

说明：
- 当前不直接引入这些依赖。
- 当前只做 ParserAdapter 接口。
- 这些项目未来只能通过 adapter 接入。
- 默认 pytest 不能依赖它们。
- `LightweightIngestionService` 只是 fallback，不是最终生产 parser。

### 4. 当前代码位置

- `src/researchsensei/ingestion/lightweight.py` — `LightweightIngestionService`
- 入口方法：`ingest_path(path: str | Path, paper_id: str | None = None) -> DocumentIngestion`
- 支持：`.md`, `.txt`, `.pdf`
- 降级：不支持的文件类型 → `degraded=True`, `UNSUPPORTED_FILE_TYPE`
- PDF 失败 → `degraded=True`, `PDF_PARSE_FAILED`
- 空文件 → `degraded=True`, `NO_TEXT_EXTRACTED`

### 5. 需要新增或修改的文件

**新增**:
- `src/researchsensei/parser/__init__.py`
- `src/researchsensei/parser/adapter.py`
- `src/researchsensei/parser/lightweight_adapter.py`
- `tests/test_parser_adapter.py`

**禁止修改**:
- `src/researchsensei/ingestion/**`
- `src/researchsensei/ingestion/pipeline.py`
- `src/researchsensei/web/**`
- `frontend/**`
- `backend/**`
- `pyproject.toml`

### 6. 核心类与方法

```python
# src/researchsensei/parser/adapter.py
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from researchsensei.schemas.document import DocumentIngestion


class ParserAdapter(ABC):
    """Abstract interface for document parser adapters."""

    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Return True if this adapter supports the source file."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        """Parse source into DocumentIngestion.

        Rules:
        - source must be a Path.
        - paper_id is provided by caller.
        - adapter must not generate paper_id.
        - adapter must not write artifacts.
        - adapter must not update jobs.
        - adapter must not call LLM.
        - adapter must not call network.
        """
        raise NotImplementedError
```

```python
# src/researchsensei/parser/lightweight_adapter.py
from __future__ import annotations

from pathlib import Path

from researchsensei.ingestion.lightweight import LightweightIngestionService
from researchsensei.parser.adapter import ParserAdapter
from researchsensei.schemas.document import DocumentIngestion


class LightweightParserAdapter(ParserAdapter):
    """Adapter wrapper around LightweightIngestionService."""

    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None:
        self._ingestion = ingestion or LightweightIngestionService()

    def supports(self, source: Path) -> bool:
        return source.suffix.lower() in {".md", ".txt", ".pdf"}

    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        return self._ingestion.ingest_path(source, paper_id=paper_id)
```

### 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `Path source`, `str paper_id` |
| 输出 | `DocumentIngestion` |
| 不生成 paper_id | 调用者传入 |
| 不写 artifact | 只返回 DocumentIngestion |
| 不更新 job | — |
| 不调用 LLM | — |
| 不联网 | — |

### 8. 错误 / 降级策略

| 错误 | 行为 |
|------|------|
| 不支持的文件类型 | `supports()` 返回 False |
| 源文件不存在 | 沿用 LightweightIngestionService 行为 |
| 空文件 | `degraded=True`, `NO_TEXT_EXTRACTED` |
| PDF 解析失败 | `degraded=True`, `PDF_PARSE_FAILED` |

### 9. Artifact 影响

- 不新增 artifact
- 不修改现有 artifact 格式
- `parsed_document.json` 格式不变

### 10. 测试要求

**test_parser_adapter_is_abstract**
- Arrange: import ParserAdapter
- Act: call ParserAdapter()
- Assert: raises TypeError

**test_lightweight_adapter_supports_md_txt_pdf_case_insensitive**
- Arrange: create LightweightParserAdapter
- Act: call supports() on paper.md, paper.txt, paper.pdf, paper.MD, paper.TXT, paper.PDF, paper.markdown, paper.docx
- Assert: first six return True, .markdown returns False, .docx returns False

**test_lightweight_adapter_rejects_unsupported_suffix**
- Arrange: create LightweightParserAdapter
- Act: call supports(Path("paper.docx"))
- Assert: returns False

**test_lightweight_adapter_matches_original_markdown_output**
- Arrange: create tmp markdown file with content "# Example Paper\n## Abstract\nWe propose SenseiNet for time-series anomaly detection.\n## Method\nSenseiNet computes anomaly scores using reconstruction error.\nL = ||x - \hat{x}||_2\n## Experiments\nSenseiNet improves F1 on a synthetic benchmark.", create LightweightIngestionService, create LightweightParserAdapter
- Act: original = service.ingest_path(path, paper_id="p1"), adapted = adapter.parse(path, paper_id="p1")
- Assert: original.paper_id == adapted.paper_id, original.detected_language == adapted.detected_language, original.degraded == adapted.degraded, warning count equal, each warning code/message equal, block count equal, each block block_id/type/section/text/evidence_ref equal

**test_lightweight_adapter_matches_original_txt_output**
- Same as markdown test but with .txt file

**test_lightweight_adapter_parse_returns_document_ingestion**
- Arrange: create adapter, create tmp .md file
- Act: result = adapter.parse(path, paper_id="test")
- Assert: isinstance(result, DocumentIngestion), result.paper_id == "test", result.blocks is a list

**test_lightweight_adapter_json_round_trip**
- Arrange: create adapter, create tmp .md file
- Act: doc = adapter.parse(path, paper_id="test"), json_str = doc.model_dump_json(), restored = DocumentIngestion.model_validate_json(json_str)
- Assert: restored.paper_id == doc.paper_id, len(restored.blocks) == len(doc.blocks), restored.detected_language == doc.detected_language

**test_lightweight_adapter_does_not_write_artifacts**
- Arrange: create adapter, create tmp .md file in tmp_path
- Act: adapter.parse(path, paper_id="test")
- Assert: no *.json artifact files created in tmp_path, no workspace/run artifact directory created

**test_lightweight_adapter_uses_injected_service**
- Arrange: create real LightweightIngestionService, create LightweightParserAdapter(ingestion=service)
- Act: adapter.parse(path, paper_id="test")
- Assert: output matches direct service.ingest_path() call

**test_lightweight_adapter_propagates_degraded_behavior**
- Arrange: create tmp file "broken.pdf" with invalid PDF bytes, create adapter
- Act: result = adapter.parse(path, paper_id="test")
- Assert: result.degraded is True, any warning.code == "PDF_PARSE_FAILED"

### 11. Hard-Fail 条件

- 新增依赖
- 修改现有 ingestion
- 输出不兼容
- 测试只测字段存在、不比较内容
- 默认 pytest 真实联网 / LLM

---

## 3. Evidence 模块

### 1. 模块目标

从 block-level evidence 升级到 passage/claim-level evidence，使每个解释能回指具体 claim 而非整个 block。

### 2. 非目标

- 不用 LLM 做 claim extraction
- 不用向量数据库
- 不新增依赖

### 3. 参考 / 复用项目

| 项目 | GitHub/来源 | 参考能力 | 当前决策 |
|------|-----------|----------|----------|
| PaperQA / PaperQA2 | `Future-House/paper-qa` (TO_VERIFY) | passage retrieval, citation-backed answer | OPTIONAL_ADAPTER 候选 |
| OpenScholar | TO_VERIFY_REPO | citation accuracy, passage-level evidence | REFERENCE_ONLY |
| ARIS | `wanshuiyin/Auto-claude-code-research-in-sleep` | paper-claim-audit, result-to-claim | REFERENCE_ONLY |

说明：
- 不直接搬 PaperQA。
- 不把 ARIS 整包接入。
- 借鉴它们的 passage/claim/citation/audit 思路。
- 本阶段默认测试不联网、不用真实 LLM、不用向量库。

### 4. 当前代码位置

- `src/researchsensei/grounding.py` — `build_evidence_index()`
- `src/researchsensei/schemas/evidence.py` — `ClaimEvidence`, `EvidenceIndex`
- 当前 evidence 是 block-level：一个 block 对应一个 evidence entry

### 5. 需要新增或修改的文件

**新增**:
- `src/researchsensei/evidence/__init__.py`
- `src/researchsensei/evidence/passage_index.py`
- `src/researchsensei/evidence/claim_extractor.py`
- `src/researchsensei/evidence/retriever.py`
- `tests/test_passage_index.py`
- `tests/test_claim_extractor.py`
- `tests/test_evidence_retriever.py`

**修改**:
- `src/researchsensei/schemas/evidence.py` — ClaimEvidence 添加 v2 可选字段

### 6. 核心类与方法

**Passage**:
```python
class Passage(SenseiModel):
    passage_id: str          # e.g. "p001"
    block_ids: list[str]     # source block IDs
    section: str
    text: str
    normalized_text: str
```

**PassageIndex**:
```python
class PassageIndex(SenseiModel):
    paper_id: str
    passages: list[Passage]
    warnings: list[WarningItem] = []
```

**ClaimEvidence v2**（向后兼容）:
```python
class ClaimEvidence(SenseiModel):
    claim_id: str
    block_id: str
    evidence_type: EvidenceType
    evidence_ref: str
    quote_or_summary: str
    confidence: float

    # v2 新增（可选）
    passage_id: str = ""
    claim_type: str = ""           # see claim_type values below
    semantic_support: str = ""     # see semantic_support values below
```

**ClaimExtractor**:
```python
class ClaimExtractor:
    def extract(self, passages: list[Passage]) -> list[ClaimEvidence]:
        """Extract claims from passages using rule-based heuristics."""
        ...
```

**EvidenceRetriever**:
```python
class EvidenceRetriever:
    def retrieve(self, claim: str, index: PassageIndex) -> list[Passage]:
        """Retrieve passages relevant to a claim."""
        ...
```

### 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `DocumentIngestion` / `DocumentBlock` |
| 输出 | 升级后的 `evidence_index.json`（向后兼容） |
| 每个 claim 必须 | 能回指原始 block/passage |

### claim_type 值定义

| 值 | 含义 |
|----|------|
| PROBLEM | 论文要解决的问题 |
| METHOD | 论文提出的方法或机制 |
| CONTRIBUTION | 论文声称的贡献 |
| RESULT | 实验结果或定量结论 |
| LIMITATION | 局限、假设或未来工作 |
| FORMULA_CONTEXT | 公式的作用、变量来源、优化目标 |
| DEFINITION | 术语或符号定义 |

### semantic_support 值定义

| 值 | 含义 |
|----|------|
| DIRECT_QUOTE | claim 可直接由原文句子支持 |
| PARAPHRASE | claim 是原文的忠实改写 |
| REASONABLE_INFERENCE | 根据上下文合理推断，但非原文直说 |
| INSUFFICIENT_EVIDENCE | 证据不足，只能降级 |

### ClaimExtractor 规则

- Abstract 中含 "propose / present / introduce / develop" → CONTRIBUTION
- Method section 中含 "we propose / our method / framework / model" → METHOD
- Experiment/Result section 中含 "improve / outperform / achieve / reduce" → RESULT
- limitation/future work section → LIMITATION
- formula block 或含 "loss / objective / equation / optimize" → FORMULA_CONTEXT
- heading 不生成 claim
- 空文本不生成 claim
- 不允许 claim_text 是 "This block belongs to ..."

### 8. 错误 / 降级策略

| 错误 | 行为 |
|------|------|
| 无 passages 提取 | `warnings.append("NO_PASSAGES")` |
| 无 claims 提取 | `warnings.append("NO_CLAIMS")` |
| claim 无匹配 passage | `evidence_type = INSUFFICIENT_EVIDENCE` |
| passage 太短 (< 50 chars) | 跳过该 passage |

### 9. Artifact 影响

- `evidence_index.json` 格式向后兼容（v1 字段不变，v2 字段可选）
- 现有 grounding.py 保留为 fallback

### 10. 测试要求

**test_passage_ids_stable_and_sequential**
- Arrange: create DocumentIngestion with 3 blocks
- Act: build PassageIndex
- Assert: passage_ids are "p001", "p002", "p003"

**test_passage_groups_blocks_by_section**
- Arrange: create blocks with sections ["abstract", "abstract", "method"]
- Act: build PassageIndex
- Assert: abstract blocks in same passage, method block in different passage

**test_claim_extractor_does_not_generate_section_label_claim**
- Arrange: create passage with text "method" (heading only)
- Act: extract claims
- Assert: no claims generated

**test_claim_extractor_method_section**
- Arrange: create passage in method section with "we propose SenseiNet"
- Act: extract claims
- Assert: at least one claim with claim_type == "METHOD"

**test_claim_extractor_result_section**
- Arrange: create passage in experiments section with "SenseiNet improves F1"
- Act: extract claims
- Assert: at least one claim with claim_type == "RESULT"

**test_claim_extractor_formula_context**
- Arrange: create passage with formula block
- Act: extract claims
- Assert: at least one claim with claim_type == "FORMULA_CONTEXT"

**test_claim_evidence_v2_backward_compatible**
- Arrange: create v1 ClaimEvidence
- Act: serialize and deserialize
- Assert: v1 fields unchanged, v2 fields default to ""

**test_evidence_retriever_finds_relevant_passage**
- Arrange: create PassageIndex with method passage, create claim "SenseiNet computes anomaly scores"
- Act: retrieve
- Assert: returns at least one passage containing relevant text

**test_evidence_retriever_unrelated_claim_returns_empty**
- Arrange: create PassageIndex, create unrelated claim
- Act: retrieve
- Assert: returns empty list

### 11. Hard-Fail 条件

- 只有 block-level（无 passage-level）
- 无 claim extraction
- 修改 parser 或 pipeline
- 真实网络 / LLM 在默认测试
- 现有测试破坏

---

## 4. Paper Understanding 模块

### 1. 模块目标

基于证据生成学习卡片，LLM 输出必须绑定 evidence，无 evidence 必须降级。

### 2. 非目标

- 默认测试不用真实 LLM
- 不新增依赖
- 不改 frontend

### 3. 参考 / 复用项目

| 项目 | 参考能力 | 当前决策 |
|------|----------|----------|
| PaperQA (`Future-House/paper-qa`, TO_VERIFY) | evidence-constrained answer | 参考 / optional adapter |
| OpenScholar (TO_VERIFY_REPO) | citation-backed response | 参考评价标准 |
| ARIS (`wanshuiyin/Auto-claude-code-research-in-sleep`) | reviewer independence, kill-argument, claim audit | 参考 audit 思想 |

### 4. 当前代码位置

- `src/researchsensei/paper_card.py` — `build_paper_card()` (rule-based), `build_paper_card_with_llm()` (LLM-enhanced)
- `src/researchsensei/formula_card.py` — 同上
- `src/researchsensei/teaching_card.py` — 同上
- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner` 当前只用 rule-based

### 5. 需要新增或修改的文件

**修改**:
- `src/researchsensei/ingestion/pipeline.py` — 添加 LLM 路径
- `src/researchsensei/paper_card.py` — 加强 evidence_ref 校验
- `src/researchsensei/formula_card.py` — 加强 evidence_ref 校验
- `src/researchsensei/teaching_card.py` — 加强 evidence_ref 校验

**新增**:
- `tests/test_llm_paper_understanding.py`

### 6. 核心类与方法

**EvidencePack** (输入给 LLM，不直接整篇论文):
```python
class EvidencePackItem(SenseiModel):
    claim_id: str
    claim_type: str
    evidence_ref: str
    quote_or_summary: str
    passage_text: str
    confidence: float
```

**Pipeline 集成**:
```python
class SinglePaperIngestionRunner:
    def __init__(self, ..., llm_client: LLMClient | MockLLMClient | None = None):
        self.llm_client = llm_client

    def run(self, ...):
        ...
        if self.llm_client is not None:
            try:
                paper_card = build_paper_card_with_llm(skeleton, evidence_index, self.llm_client)
            except Exception:
                paper_card = build_paper_card(skeleton, evidence_index)  # fallback
        else:
            paper_card = build_paper_card(skeleton, evidence_index)
```

### 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | paper_skeleton.json, evidence_pack, existing card baseline |
| 输出 | paper_card.json, formula_cards.json, teaching_cards.json |
| LLM prompt 只能使用 | paper title/metadata, paper_skeleton, evidence_pack, existing baseline card |
| 禁止 | 直接整篇论文全文塞入 prompt |

### 8. 错误 / 降级策略

| 错误 | 行为 |
|------|------|
| LLM 输出 evidence_ref 不存在 | 丢弃该字段或 fallback |
| LLM 输出无 evidence_ref | fallback |
| LLM 异常 | fallback，warning code: `LLM_CARD_FALLBACK` |
| fallback 到 rule-based | card warnings 中体现 `LLM_CARD_FALLBACK` |

### v2 质量门槛

- `core_idea` 必须不同于 `method_overview`
- formula symbol 必须来自论文上下文，不只是通用字典
- `human_explanation` 不能是公式文本
- generic symbol dict → `REASONABLE_INFERENCE`

### 禁止

- 不能直接整篇论文塞进 prompt
- 不能生成没有 evidence 的解释
- 不能把原文复制成 human_explanation
- 不能编造 dataset / metric / result

### 9. Artifact 影响

- `paper_card.json`, `formula_cards.json`, `teaching_cards.json` 格式不变
- 内容质量提升（v2），但 schema 兼容

### 10. 测试要求

**test_pipeline_accepts_optional_llm_client**
- Arrange: create SinglePaperIngestionRunner with llm_client=None
- Act: run()
- Assert: no error, uses rule-based

**test_no_llm_client_uses_rule_based_baseline**
- Arrange: create runner without llm_client
- Act: run()
- Assert: output matches direct rule-based call

**test_mock_llm_client_produces_evidence_bound_card**
- Arrange: create runner with MockLLMClient returning valid JSON with evidence_refs
- Act: run()
- Assert: card has evidence_refs from LLM output

**test_llm_failure_falls_back_with_warning**
- Arrange: create runner with MockLLMClient that raises exception
- Act: run()
- Assert: no crash, fallback to rule-based, warning contains "LLM_CARD_FALLBACK"

**test_invalid_evidence_ref_rejected**
- Arrange: create MockLLMClient returning card with non-existent evidence_ref
- Act: run()
- Assert: invalid ref rejected, fallback used

**test_output_without_evidence_ref_rejected**
- Arrange: create MockLLMClient returning card without evidence_ref
- Act: run()
- Assert: claim rejected or degraded

**test_core_idea_differs_from_method_overview**
- Arrange: create runner with MockLLMClient
- Act: run()
- Assert: core_idea.text != method_overview.text, or degraded

**test_human_explanation_not_raw_copy**
- Arrange: create runner with MockLLMClient returning abstract text as human_explanation
- Act: run()
- Assert: warning or degradation

**test_formula_symbol_from_context_or_degraded**
- Arrange: create runner with formula-heavy input
- Act: run()
- Assert: symbols from paper context or evidence_type == REASONABLE_INFERENCE

### 11. Hard-Fail 条件

- 默认测试真实 LLM
- 无效 evidence_ref 被接受
- 无 fallback
- 现有测试破坏
- 公式文本作为 human_explanation

---

## 5. Literature Search 模块

### 1. 模块目标

搜索、筛选、排序论文，生成阅读计划。

### 2. 非目标

- 不做单篇论文理解
- 不做 cross-paper synthesis（后续）
- 不做真实联网测试

### 3. 参考 / 复用项目

| 项目 | GitHub/来源 | 用途 | 当前决策 |
|------|-----------|------|----------|
| arXiv Atom API | public API | 论文搜索 | DIRECT_ADAPTER 已有 |
| OpenAlex REST API | public API | 论文搜索/元数据 | DIRECT_ADAPTER 已有 |
| Semantic Scholar | public API | citation count / venue / TLDR | OPTIONAL_ADAPTER |
| Crossref | public API | DOI metadata | OPTIONAL_ADAPTER |
| PaperQA | `Future-House/paper-qa` (TO_VERIFY) | literature QA / passage retrieval | OPTIONAL_ADAPTER |
| ResearchPilot | TO_VERIFY_REPO | structured findings / cross-paper patterns | REFERENCE_ONLY |
| STORM | `stanford-oval/storm` (TO_VERIFY) | outline / multi-perspective search | REFERENCE_ONLY |
| ARIS research-lit | `wanshuiyin/Auto-claude-code-research-in-sleep` | multi-source literature workflow | REFERENCE_ONLY |

### 4. 当前代码位置

- `src/researchsensei/query/planner.py` — `QueryPlanner`
- `src/researchsensei/acquisition/arxiv_adapter.py` — `ArxivAdapter`
- `src/researchsensei/acquisition/openalex_adapter.py` — `OpenAlexAdapter`
- `src/researchsensei/selection/service.py` — `SelectionService`
- `src/researchsensei/direction/runner.py` — `DirectionRunner`

### 5. 需要新增或修改的文件

当前模块已实现。后续升级可能新增 Semantic Scholar / Crossref adapter。

### 6. 核心类与方法

**ArxivAdapter**:
```python
def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
    ...
```

**OpenAlexAdapter**:
```python
def search(self, query: str, max_results: int = 20) -> list[CandidatePaper]:
    ...
```

**SelectionService**:
```python
def build_candidate_pool(self, query: str, candidates: list[CandidatePaper], search_log: list[str] | None = None, warnings: list[str] | None = None) -> CandidatePool: ...
def deduplicate(self, candidates: list[CandidatePaper]) -> list[CandidatePaper]: ...
def build_reading_plan(self, query_plan: QueryPlan, candidates: list[CandidatePaper]) -> ReadingPlan: ...
```

**DirectionRunner**:
```python
async def run(self, user_query: str, direction_id: str | None = None) -> DirectionBundle: ...
```

### 7. 输入输出

| 类 | 输入 | 输出 |
|----|------|------|
| QueryPlanner | user_query | QueryPlan |
| ArxivAdapter | query, max_results | CandidatePaper[] |
| OpenAlexAdapter | query, max_results | CandidatePaper[] |
| SelectionService | candidates | CandidatePool / ReadingPlan |
| DirectionRunner | user_query | DirectionBundle |

### Adapter 规则

- adapter 不写 artifact
- adapter 不做 selection
- adapter 异常要抛出，由 DirectionRunner 捕获
- 默认测试必须用 MockTransport
- 不真实联网

### 去重规则

DOI（剥离 prefix + 小写）→ arXiv ID（剥离 arXiv: + vN）→ normalized_title

### 评分权重

relevance (0.36) + venue_prestige (0.22) + citation (0.14) + code (0.06) + method_rep (0.14) + recency (0.08)

### 8. 错误 / 降级策略

- arXiv 失败不影响 OpenAlex
- OpenAlex 失败不影响 arXiv
- 单 source 失败写入 `candidate_pool.warnings`
- `search_log` 写 `source: failed (ExceptionType)`
- 所有 source 都失败，reading_plan 为空并 degraded/warning
- 不能静默失败

### 9. Artifact 影响

- `query_plan.json`, `candidate_pool.json`, `filtered_candidates.json`, `reading_plan.json`
- 格式不变

### 10. 测试要求

**test_arxiv_xml_parse**
- Arrange: create sample arXiv Atom XML
- Act: parse
- Assert: CandidatePaper with correct title, arxiv_id, year, authors, pdf_url

**test_openalex_abstract_inverted_index**
- Arrange: create sample OpenAlex JSON with abstract_inverted_index
- Act: parse
- Assert: abstract text reconstructed correctly

**test_adapter_failure_propagated_to_runner_warnings**
- Arrange: create MockTransport that raises ConnectError for arXiv, empty response for OpenAlex
- Act: runner.run()
- Assert: bundle.warnings contains "ACQUISITION_FAILED"

**test_candidate_pool_json_contains_source_warning**
- Arrange: same as above
- Act: runner.run()
- Assert: bundle.candidate_pool.warnings contains failure warning

**test_filtered_candidates_preserves_warnings**
- Arrange: same as above
- Act: runner.run()
- Assert: bundle.filtered_candidates.warnings contains failure warning

**test_dedup_doi_arxiv_title**
- Arrange: create candidates with same DOI, same arXiv ID, similar title
- Act: deduplicate()
- Assert: duplicates merged, unique papers preserved

**test_reading_plan_items_have_scoring_breakdown**
- Arrange: create candidates
- Act: build_reading_plan()
- Assert: each item has scoring_breakdown, selection_reason, risk_note

**test_a_read_limited_to_12**
- Arrange: create 20 relevant candidates
- Act: build_reading_plan()
- Assert: count of A_READ items ≤ 12

### 11. Hard-Fail 条件

- 真实联网在默认测试
- adapter 失败静默吞掉
- 去重不生效
- reading_plan 无 scoring_breakdown

---

## 6. Audit / Quality 模块

### 1. 模块目标

判断"讲得好"，不只是 schema 通过。

### 2. 非目标

- 不用真实 LLM
- 不新增依赖

### 3. 参考 / 复用项目

| 项目 | 参考能力 | 当前决策 |
|------|----------|----------|
| ARIS (`wanshuiyin/Auto-claude-code-research-in-sleep`) | paper-claim-audit, citation-audit, kill-argument | 参考 audit 思想 |

### 4. 当前代码位置

- `tests/test_quality_grounding.py`, `test_quality_hallucination.py`, `test_quality_formula.py`, `test_quality_smoke.py`
- `tests/fixtures/quality/` — fixture papers

### 5. 需要新增或修改的文件

**新增**:
- `tests/test_explanation_audit.py`
- `tests/test_formula_audit.py`
- `tests/test_evidence_audit.py`

### 6. 核心类与方法

**QualityReport**:
```python
class QualityReport(SenseiModel):
    paper_id: str
    score: float
    hard_fails: list[str]
    warnings: list[WarningItem]
    checked_artifacts: list[str]
```

### 检测方法

- **formula char ratio**: 统计 "=", "\", "_", "^", "{}", "sum", "argmin", "lambda" 等符号比例
- **raw copy detection**: exact substring, high token overlap
- **paper-specific terms**: 从 title/abstract/method 抽关键词，output 必须命中至少一个
- **evidence_ref validity**: 必须存在于 evidence_index / claim_evidence
- **core_idea vs method_overview**: exact equal fail, high overlap warning

### 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | card JSON + evidence_index |
| 输出 | quality report (JSON) |
| 用于 | pytest tests |

### 8. 错误 / 降级策略

不适用 — audit 是只读检查，不修改 artifact。

### 9. Artifact 影响

不修改 artifact，只读取。

### 10. 测试要求

**test_hard_fail_core_claim_without_evidence**
- Arrange: create paper_card with core_idea.evidence_ref = "" and evidence_type = UNVERIFIED
- Act: audit
- Assert: hard_fail triggered

**test_hard_fail_formula_text_as_human_explanation**
- Arrange: create teaching_card with human_explanation = "L = ||x - x_hat||_2"
- Act: audit
- Assert: hard_fail triggered (formula char ratio ≥ 0.3)

**test_hard_fail_generic_output_without_paper_terms**
- Arrange: create card with generic text, no paper-specific terms
- Act: audit
- Assert: hard_fail triggered

**test_raw_abstract_copy_detected**
- Arrange: create card where core_idea.text == abstract text
- Act: audit
- Assert: warning or hard_fail

**test_invalid_evidence_ref_detected**
- Arrange: create card with evidence_ref not in evidence_index
- Act: audit
- Assert: hard_fail triggered

**test_quality_report_json_round_trip**
- Arrange: create QualityReport
- Act: serialize and deserialize
- Assert: all fields preserved

### 11. Hard-Fail 条件

| ID | 条件 |
|----|------|
| HF-1 | 核心 claim 无 evidence_ref 且未降级 |
| HF-2 | human_explanation 是公式文本（formula char ratio ≥ 0.3） |
| HF-3 | formula symbol 解释与论文矛盾 |
| HF-4 | core_idea / problem 缺 evidence_ref |
| HF-5 | 输出无论文特有术语 |
| HF-6 | 输出与论文主题不符 |

---

## 7. Workspace / Job / API 模块

### 1. 模块目标

文件系统持久化、job 状态管理、HTTP API。

### 2. 非目标

- 不做业务逻辑
- 不直接调用 LLM

### 3. 参考 / 复用项目

无外部项目参考。纯内部基础设施。

### 4. 当前代码位置

- `src/researchsensei/workspace/store.py` — `WorkspaceStore`
- `src/researchsensei/jobs/store.py` — `JobStore`
- `src/researchsensei/web/app.py` — FastAPI app

### 5. 需要新增或修改的文件

当前已实现。后续可能扩展 API endpoints。

### 6. 核心类与方法

**WorkspaceStore**:
```python
def new_run_dir(self, run_id: str) -> Path: ...
def write_json(self, path: Path, data: Any) -> None: ...
```

**JobStore**:
```python
def create(self, job: JobRecord) -> JobRecord: ...
def get(self, job_id: str) -> JobRecord: ...
def list_recent(self, limit: int = 20) -> list[JobRecord]: ...
def update(self, job_id: str, **kwargs) -> JobRecord: ...
```

### 7. 输入输出

| 类 | 输入 | 输出 |
|----|------|------|
| WorkspaceStore | run_id | run_dir Path |
| JobStore | JobRecord | persisted job |
| API | HTTP request | HTTP response |

### 8. 错误 / 降级策略

- Job failure → status=FAILED, error field set
- warnings 必须是 `WarningItem`，不能是字符串
- artifact query 不允许路径穿越（`relative_to()` 校验）

### 9. Artifact 影响

- API 不直接生成 artifact
- API 只启动 job / 返回 status
- artifact 由 pipeline 生成

### 10. 测试要求

- Job create/get/update round-trip
- Job failure writes status=FAILED with WarningItem
- Artifact path traversal rejected (400)
- Missing job returns 404

### 11. Hard-Fail 条件

- 路径穿越成功
- API 直接调用 LLM
- warnings 使用 str 而非 WarningItem

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

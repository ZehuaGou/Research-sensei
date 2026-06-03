# Paper Understanding — 开发文档

论文阅读理解核心升级。覆盖 ParserAdapter / PassageIndex / ClaimEvidence / Evidence-constrained LLM / Quality Benchmark。

---

## 1. ParserAdapter

### 目标

设计 ParserAdapter interface，包装现有 parser 为 default adapter。

### 非目标

- 不接入 Docling / Nougat / Marker / MinerU（只留接口）
- 不新增依赖
- 不改变现有 parser 行为
- 不改 pipeline / web / frontend / backend

### 参考 / 复用项目

| 项目 | 决策 | 说明 |
|------|------|------|
| Docling | OPTIONAL_ADAPTER 候选 | PDF 解析，layout/table/formula 支持，暂不接入 |
| Nougat | OPTIONAL_ADAPTER 候选 | scientific PDF parser，需 GPU，暂不接入 |
| Marker | OPTIONAL_ADAPTER 候选 | PDF/Markdown parser，较轻量，暂不接入 |
| MinerU | OPTIONAL_ADAPTER 候选 | PDF parser，暂不接入 |

### 当前代码

- `src/researchsensei/ingestion/lightweight.py` — `LightweightIngestionService`
- 入口方法：`ingest_path(path: str | Path, paper_id: str | None = None) -> DocumentIngestion`
- 支持：`.md`, `.txt`, `.pdf`
- 降级：不支持的文件类型 → `degraded=True`, `UNSUPPORTED_FILE_TYPE`
- PDF 失败 → `degraded=True`, `PDF_PARSE_FAILED`
- 空文件 → `degraded=True`, `NO_TEXT_EXTRACTED`

### 需要新增的文件

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
- `frontend/`, `backend/`, `pyproject.toml`

### 类与方法

```python
# adapter.py
from abc import ABC, abstractmethod
from pathlib import Path
from researchsensei.schemas.document import DocumentIngestion

class ParserAdapter(ABC):
    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Check if this adapter can handle the source file."""
        ...

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        """Parse source into DocumentIngestion. paper_id provided by caller."""
        ...
```

```python
# lightweight_adapter.py
class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None:
        self._ingestion = ingestion or LightweightIngestionService()

    def supports(self, source: Path) -> bool:
        return source.suffix.lower() in {".md", ".txt", ".pdf"}

    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        return self._ingestion.ingest_path(source, paper_id=paper_id)
```

### 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `Path source`, `str paper_id` |
| 输出 | `DocumentIngestion` |
| 不生成 paper_id | 调用者传入 |
| 不写 artifact | 只返回 DocumentIngestion |
| 不更新 job | — |
| 不调用 LLM | — |
| 不联网 | — |

### 错误 / 降级策略

| 错误 | 行为 |
|------|------|
| 不支持的文件类型 | `supports()` 返回 False |
| 源文件不存在 | 沿用 LightweightIngestionService 行为 |
| 空文件 | 沿用当前行为：`degraded=True`, `NO_TEXT_EXTRACTED` |
| PDF 解析失败 | 沿用当前行为：`degraded=True`, `PDF_PARSE_FAILED` |

### 兼容性标准

adapter 输出必须与直接调用 `LightweightIngestionService.ingest_path()` 一致。比较字段：
- `paper_id`, `detected_language`, `degraded`
- `warnings` (code + message)
- `blocks` length, `block_id`, `type`, `section`, `text`, `evidence_ref`

### 测试计划

| 测试 | 断言 |
|------|------|
| `test_parser_adapter_is_abstract` | `ParserAdapter()` raises TypeError |
| `test_lightweight_adapter_supports_md_txt_pdf_case_insensitive` | .md/.txt/.pdf=True, .MD/.TXT/.PDF=True, .markdown/.docx=False |
| `test_lightweight_adapter_rejects_unsupported_suffix` | .docx → False |
| `test_lightweight_adapter_matches_original_markdown_output` | 字段逐个比较：paper_id, detected_language, degraded, warnings, blocks |
| `test_lightweight_adapter_matches_original_txt_output` | 同上 |
| `test_lightweight_adapter_parse_returns_document_ingestion` | isinstance(result, DocumentIngestion) |
| `test_lightweight_adapter_json_round_trip` | dump → validate round-trip |
| `test_lightweight_adapter_does_not_write_artifacts` | 无 *.json 文件写入，无 workspace/run 目录创建 |
| `test_lightweight_adapter_uses_injected_service` | 注入的 service 被调用 |
| `test_lightweight_adapter_propagates_degraded_behavior` | broken PDF → degraded=True, PDF_PARSE_FAILED warning |

### Hard-Fail

- 新增依赖
- 修改现有 ingestion
- 输出不兼容
- 测试只测字段存在、不比较内容
- 默认 pytest 真实联网 / LLM

---

## 2. PassageIndex + ClaimEvidence

### 目标

从 block-level evidence 升级到 passage/claim-level evidence。

### 非目标

- 不用 LLM 做 claim extraction
- 不用向量数据库
- 不新增依赖

### 参考 / 复用项目

| 项目 | 决策 | 说明 |
|------|------|------|
| PaperQA | OPTIONAL_ADAPTER 候选 | 参考 passage retrieval / citation-backed answer |
| OpenScholar | REFERENCE_ONLY | 参考 citation accuracy / passage-level evidence |
| ARIS | REFERENCE_ONLY | 参考 paper-claim-audit / result-to-claim 思想 |

### 当前代码

- `src/researchsensei/grounding.py` — `build_evidence_index()`
- `src/researchsensei/schemas/evidence.py` — `ClaimEvidence`, `EvidenceIndex`
- 当前 evidence 是 block-level：一个 block 对应一个 evidence entry

### 需要新增的文件

| 文件 | 用途 |
|------|------|
| `src/researchsensei/evidence/__init__.py` | barrel |
| `src/researchsensei/evidence/passage_index.py` | PassageIndex |
| `src/researchsensei/evidence/claim_extractor.py` | ClaimExtractor |
| `src/researchsensei/evidence/retriever.py` | EvidenceRetriever |
| `tests/test_passage_index.py` | 测试 |
| `tests/test_claim_extractor.py` | 测试 |
| `tests/test_evidence_retriever.py` | 测试 |

### 需要修改的文件

| 文件 | 变化 |
|------|------|
| `src/researchsensei/schemas/evidence.py` | ClaimEvidence 添加 v2 可选字段 |

### Schema 设计

```python
class Passage(SenseiModel):
    passage_id: str          # e.g. "p001"
    block_ids: list[str]     # source block IDs
    section: str
    text: str
    normalized_text: str

class PassageIndex(SenseiModel):
    paper_id: str
    passages: list[Passage]
```

ClaimEvidence v2（向后兼容，添加可选字段）：

```python
class ClaimEvidence(SenseiModel):
    # v1 字段（不变）
    claim_id: str
    block_id: str
    evidence_type: EvidenceType
    evidence_ref: str
    quote_or_summary: str
    confidence: float

    # v2 新增（可选）
    passage_id: str = ""
    claim_type: str = ""           # HYPOTHESIS / METHOD / RESULT / LIMITATION / CONTRIBUTION / DEFINITION
    semantic_support: str = ""     # direct_quote / paraphrase / inference
```

### 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `DocumentIngestion` / `DocumentBlock` |
| 输出 | 升级后的 `evidence_index.json`（向后兼容） |
| 每个 claim 必须 | 能回指原始 block/passage |

### ClaimExtractor 规则

- 不允许把 "This block belongs to method section" 当 claim
- claim_text 必须是论文语义 claim
- claim_type 候选：HYPOTHESIS / METHOD / RESULT / LIMITATION / CONTRIBUTION / DEFINITION
- 规则版：基于 section + 句式特征提取

### 测试计划

| 测试 | 断言 |
|------|------|
| PassageIndex 正确分段 | passages 按 section 分组 |
| ClaimExtractor 从 method 提取 | 至少提取出 METHOD 类型 claim |
| ClaimExtractor 从 abstract 提取 | 至少提取出贡献 claim |
| ClaimExtractor 不从 heading 提取 | heading 不产生 claim |
| EvidenceRetriever 找到相关 passage | 输入 claim → 返回相关 passage |
| EvidenceRetriever 无关 claim 返回空 | 不相关 claim → 空列表 |
| ClaimEvidence v2 向后兼容 | v1 字段不变，v2 字段默认空 |
| 现有 evidence_index 测试仍通过 | 不破坏现有 |

### Hard-Fail

- 只有 block-level（无 passage-level）
- 无 claim extraction
- 修改 parser 或 pipeline
- 真实网络 / LLM 在默认测试
- 现有测试破坏

---

## 3. Evidence-constrained LLM Paper Understanding

### 目标

将 LLM-enhanced card builder 接入主 pipeline，所有 LLM 输出必须绑定 evidence。

### 非目标

- 默认测试不用真实 LLM
- 不新增依赖
- 不改 frontend

### 参考 / 复用项目

| 项目 | 决策 | 说明 |
|------|------|------|
| PaperQA | OPTIONAL_ADAPTER | 参考 evidence-constrained answer |
| OpenScholar | REFERENCE_ONLY | 参考 citation-backed response |
| ARIS | REFERENCE_ONLY | 参考 reviewer independence / audit chain |

### 当前代码

- `src/researchsensei/paper_card.py` — `build_paper_card()` (rule-based), `build_paper_card_with_llm()` (LLM-enhanced)
- `src/researchsensei/formula_card.py` — 同上
- `src/researchsensei/teaching_card.py` — 同上
- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner` 当前只用 rule-based

### 需要修改的文件

| 文件 | 变化 |
|------|------|
| `src/researchsensei/ingestion/pipeline.py` | 添加 LLM 路径（接受可选 LLM client） |
| `src/researchsensei/paper_card.py` | 加强 evidence_ref 校验 |
| `src/researchsensei/formula_card.py` | 加强 evidence_ref 校验 |
| `src/researchsensei/teaching_card.py` | 加强 evidence_ref 校验 |
| `tests/test_llm_paper_understanding.py` | 新增 |

### Pipeline 集成方式

```python
class SinglePaperIngestionRunner:
    def __init__(self, ..., llm_client: LLMClient | MockLLMClient | None = None):
        self.llm_client = llm_client

    def run(self, ...):
        ...
        if self.llm_client is not None:
            try:
                paper_card = await build_paper_card_with_llm(skeleton, evidence_index, self.llm_client)
            except Exception:
                paper_card = build_paper_card(skeleton, evidence_index)  # fallback
        else:
            paper_card = build_paper_card(skeleton, evidence_index)
```

### Evidence 约束

- 所有 LLM 输出必须有有效 `evidence_ref`
- 幻觉 `evidence_ref` → 拒绝 claim，使用 rule-based fallback
- LLM 失败 → fallback 到 rule-based baseline

### 输入输出

| 项 | 值 |
|----|-----|
| 输入 | paper_skeleton.json, passage_index / claim_evidence, existing card baseline |
| 输出 | paper_card.json, formula_cards.json, teaching_cards.json（v2 质量） |

### v2 质量门槛

- `core_idea` 必须不同于 `method_overview`
- formula symbol 必须来自论文上下文，不只是通用字典
- `human_explanation` 不能是公式文本
- generic symbol dict → `REASONABLE_INFERENCE`

### 禁止

- 不能直接整篇论文塞进 prompt
- 不能生成没有 evidence 的解释
- 不能把原文复制成 human_explanation

### 测试计划

| 测试 | 断言 |
|------|------|
| Pipeline 接受可选 LLM client | 构造函数不报错 |
| MockLLMClient 产生 v2 cards | core_idea ≠ method_overview |
| 无 LLM client 产生 v1 cards | rule-based fallback |
| LLM 失败 fallback | 不 crash，用 rule-based |
| 幻觉 evidence_ref 被拒绝 | 无效 ref → claim rejected |
| 所有 LLM 输出有 evidence_ref | 无 ref 的 claim 被拒绝 |
| formula symbol 来自上下文 | 不只是 generic dict |
| human_explanation 非公式文本 | formula char ratio < 0.3 |
| 现有 281 测试仍通过 | 不破坏 |
| 默认测试无真实 LLM | MockLLMClient only |

### Hard-Fail

- 默认测试真实 LLM
- 无效 evidence_ref 被接受
- 无 fallback
- 现有测试破坏
- 公式文本作为 human_explanation

---

## 4. Quality Benchmark

### 目标

判断"讲得好"，不只是 schema 通过。

### 非目标

- 不用真实 LLM
- 不新增依赖

### 需要新增的文件

| 文件 | 用途 |
|------|------|
| `tests/test_explanation_audit.py` | explanation 质量审计 |
| `tests/test_formula_audit.py` | formula 质量审计 |
| `tests/test_evidence_audit.py` | evidence 绑定审计 |
| `tests/fixtures/quality/` | 扩展 fixture |

### Fixture Papers

| Fixture | 用途 |
|---------|------|
| fixture_method_paper.md | paper_card + teaching_card 测试 |
| fixture_formula_heavy.md | formula_card + fallback 测试 |
| fixture_minimal.md | 降级 + 不编造测试 |

### 必须测的内容

| 检查 | 说明 |
|------|------|
| explanation 有 evidence | 每个核心 claim 有 evidence_ref |
| explanation 不是原文复制 | core_idea ≠ abstract text |
| core_idea ≠ method_overview | 不能混同 |
| formula symbol 有依据 | 来自上下文或标 REASONABLE_INFERENCE |
| teaching_card 有实际讲解 | 不只是模板 |
| uncertainty 正确降级 | INSUFFICIENT_EVIDENCE / NEEDS_HUMAN_CHECK |
| hard-fail 触发 | 6 个 hard-fail 条件 |

### Hard-Fail 条件

| ID | 条件 |
|----|------|
| HF-1 | 核心 claim 无 evidence_ref 且未降级 |
| HF-2 | human_explanation 是公式文本（formula char ratio ≥ 0.3） |
| HF-3 | formula symbol 解释与论文矛盾 |
| HF-4 | core_idea / problem 缺 evidence_ref |
| HF-5 | 输出无论文特有术语 |
| HF-6 | 输出与论文主题不符 |

### 输出

- quality report (JSON)
- pytest tests
- 通过后才能解冻 Phase 12

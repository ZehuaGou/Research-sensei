# Evidence 模块（M2.2）

---

## 1. 模块目标

从 block-level evidence 升级到 passage/claim-level evidence，使每个解释能回指具体 claim 而非整个 block。

## 2. 非目标

- 不用 LLM 做 claim extraction
- 不用向量数据库
- 不新增依赖

## 3. 产品流程位置

M2.2 承接 M2.1 的解析结果，构建证据链路：parsed_document → PassageIndex → ClaimEvidence → EvidencePack → LLM。

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| PaperQA | passage retrieval | github.com/Future-House/paper-qa | REFERENCE_ONLY | 否 | — | 只借鉴 chunk/retrieve 思路 |
| ARIS result-to-claim | claim audit | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 只借鉴 claim-evidence binding |
| OpenScholar | citation accuracy | 未确认 repo | REFERENCE_ONLY | 否 | — | 只借鉴 citation accuracy |

未完成调研不得进入代码开发。

## 5. 外部项目调研（详细）

### PaperQA / PaperQA2

- **GitHub**: `Future-House/paper-qa`
- **机制**: scientific literature RAG，支持 grounded responses with in-text citations，使用 embeddings / vector DB 检索文档
- **对本模块的用处**: passage retrieval 的 chunk/retrieve 思路可借鉴
- **当前是否直接接入**: 否 — 不想默认引入 embedding model / vector DB
- **借鉴流程**:
  1. `DocumentIngestion.blocks` → `PassageIndex.passages`
  2. simple lexical retrieval first
  3. later optional embedding retriever
  4. retrieved passages → `EvidencePackItem`
  5. `EvidencePackItem` → LLM prompt
  6. LLM output → evidence_ref validation

### ARIS result-to-claim / paper-claim-audit

- **机制**: result-to-claim 判断实验结果是否支持论文声明；paper-claim-audit 用零上下文审计验证论文数字
- **对本模块的用处**: 借鉴两个核心思想：
  - claim 必须有 evidence
  - audit 独立读取 artifact，不能让生成器自我放行
- **当前是否直接接入**: 否 — 不整包接入，只借鉴设计

### OpenScholar

- **机制**: passage-level retrieval + citation accuracy 评估
- **GitHub repo**: 未验证；保持 REFERENCE_ONLY 直到 repo/paper 实现确认
- **对本模块的用处**: citation accuracy 评估方法可参考
- **当前是否直接接入**: 否

## 6. 当前代码位置

- `src/researchsensei/evidence/passage_index.py` — `build_passage_index()`
- `src/researchsensei/evidence/claim_extractor.py` — `build_claim_evidence()`, `ClaimExtractor`
- `src/researchsensei/evidence/retriever.py` — `EvidenceRetriever`, BM25 实现
- `src/researchsensei/evidence/evidence_pack.py` — `build_evidence_pack()`
- `src/researchsensei/grounding.py` — `build_evidence_index()` (v1 compatibility)
- `src/researchsensei/schemas/evidence.py` — Passage, PassageIndex, ClaimEvidence, ClaimEvidenceV2, EvidencePack, EvidencePackItem 等
- `src/researchsensei/ingestion/pipeline.py` — passage_index.json / claim_evidence.json / evidence_index.json 写入位置

## 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `DocumentIngestion` / `DocumentBlock` |
| 输出 | `passage_index.json`, `claim_evidence.json`, `evidence_index.json` (v1 wrapper) |
| 每个 claim 必须 | 能回指原始 block/passage |

## 8. Artifact

v2 精读链路新增 3 个 artifact：

| artifact | 用途 | schema_version |
|----------|------|----------------|
| `passage_index.json` | PassageIndex，passage 级文档表示 | v2 |
| `claim_evidence.json` | ClaimEvidence v2，含 passage_id / claim_type / semantic_support | v2 |
| `evidence_index.json` | v1 兼容 wrapper，保留旧字段 | v1（无 schema_version 时默认 v1） |

- `evidence_index.json` 保留 v1 兼容，旧测试可继续读取。
- `claim_evidence.json` 承载 v2 字段，M2.4 Audit 和 M4 互动式学习读取此文件。
- `passage_index.json` 持久化 passage 构建结果，M2.4 Audit 和前端 evidence 跳转依赖此文件。
- 旧 artifact 缺少 `schema_version` 时按 v1 读取。
- additive 字段通过 Pydantic 默认值兼容。

## 9. Schema / 数据结构

### Passage

```python
class Passage(SenseiModel):
    passage_id: str              # p001, p002, ...
    paper_id: str
    block_ids: list[str]         # 包含的 block_id 列表
    section: str                 # 所属 section
    text: str                    # 合并后的文本
    normalized_text: str         # text.lower().strip()
    page_start: int | None = None
    page_end: int | None = None
    token_count: int = 0         # len(text.split())
    evidence_refs: list[str] = Field(default_factory=list)
    source_block_types: list[str] = Field(default_factory=list)
```

### PassageIndex

```python
class PassageIndexBuildConfig(SenseiModel):
    min_passage_chars: int = 50
    max_passage_chars: int = 2000
    merge_same_section: bool = True
    formula_standalone: bool = True
    table_standalone: bool = True

class PassageIndexStats(SenseiModel):
    total_passages: int
    total_blocks: int
    skipped_short: int
    split_long: int
    sections_found: list[str]

class PassageIndex(SenseiModel):
    schema_version: str = "v2"
    paper_id: str
    passages: list[Passage]
    warnings: list[WarningItem] = Field(default_factory=list)
    build_config: PassageIndexBuildConfig = Field(default_factory=PassageIndexBuildConfig)
    stats: PassageIndexStats | None = None
```

### ClaimEvidence

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
    claim_type: str = ""
    semantic_support: str = ""
    source_sentence: str = ""
    generated_by: str = "rule"   # "rule" / "llm"
```

### ClaimExtractor / EvidenceRetriever

```python
class ClaimExtractor:
    def extract(self, passages: list[Passage]) -> list[ClaimEvidence]: ...

class EvidenceRetrievalResult(SenseiModel):
    passage_id: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    evidence_ref: str = ""

class EvidenceRetriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75, min_score: float = 0.5, top_k: int = 5): ...
    def retrieve(self, claim_text: str, index: PassageIndex) -> list[EvidenceRetrievalResult]: ...
```

### claim_type 值

| 值 | 含义 |
|----|------|
| PROBLEM | 论文要解决的问题 |
| METHOD | 论文提出的方法或机制 |
| CONTRIBUTION | 论文声称的贡献 |
| RESULT | 实验结果或定量结论 |
| LIMITATION | 局限、假设或未来工作 |
| FORMULA_CONTEXT | 公式的作用、变量来源、优化目标 |
| DEFINITION | 术语或符号定义 |
| METHOD_CLAIM | 方法声明 |
| DATASET_CLAIM | 数据集声明 |
| COMPARISON_CLAIM | 对比声明 |
| IMPROVEMENT_CLAIM | 改进声明 |
| FUTURE_WORK_CLAIM | 未来工作声明 |
| TAXONOMY_CLAIM | 综述分类声明 |
| SURVEY_REFERENCE_CLAIM | 综述引用声明 |
| PAPER_RELATION_CLAIM | 论文关系声明 |

Direction-related fields must still be evidence-grounded. Paper-level evidence_ref cannot be replaced by direction summary.

### semantic_support 值

| 值 | 含义 |
|----|------|
| DIRECT_QUOTE | claim 可直接由原文句子支持 |
| PARAPHRASE | claim 是原文的忠实改写 |
| REASONABLE_INFERENCE | 根据上下文合理推断 |
| INSUFFICIENT_EVIDENCE | 证据不足 |

### 命名规范

| 标识 | 格式 | 示例 |
|------|------|------|
| passage_id | `p{nnn}` | p001, p002, p003 |
| claim_id | `{paper_id}:claim:c{nnn}` | paper123:claim:c001 |
| evidence_ref | 保留 block 级引用 | paper123:b003 |
| ClaimEvidence | 同时保留 passage_id + evidence_ref | passage_id="p002", evidence_ref="paper123:b003" |

## 10. 核心算法

### Passage 构建算法

**输入**: `DocumentIngestion.blocks`

**算法**:
1. 遍历 blocks，按 section 分组
2. heading blocks 不合并到 passage（只标记 section 边界）
3. 同一 section 的连续 non-heading blocks 合并为一个 passage
4. formula block 单独成 passage（不混入段落）
5. table block 单独成 passage（不混入段落）
6. 空文本 blocks（text.strip() == ""）跳过
7. 太短的 passage（< 50 chars）跳过，产生 `WarningItem(code="PASSAGE_TOO_SHORT")`
8. 太长的 passage（> 2000 chars）按句子边界切分
9. section 缺失时用 "unknown"，不直接阻断
10. passage_id 按序分配（p001, p002, ...）

**输出**: `PassageIndex`

### Claim 提取算法

**输入**: `PassageIndex.passages`

**算法**（初版不用 LLM，基于 section + keyword + 句子规则）:
1. 遍历每个 passage
2. heading 不生成 claim
3. 空文本不生成 claim
4. 根据 section + 关键词判断 claim_type
5. claim_id 生成: `{paper_id}:claim:{n}` (递增)
6. claim_text 从 passage 中提取相关句子（不复制整段）
7. evidence_ref = `{paper_id}:{first_block_id}`
8. quote_or_summary 截取前 200 chars
9. confidence 基于 section 类型和关键词匹配度
10. semantic_support: DIRECT_QUOTE / PARAPHRASE / REASONABLE_INFERENCE / INSUFFICIENT_EVIDENCE
11. 无法判断时必须 INSUFFICIENT_EVIDENCE 或跳过
12. 不允许 "This block belongs to method section" 这种伪 claim

### BM25 EvidenceRetriever

**当前不使用向量库、不联网、不用 LLM、不新增依赖。**

- simple overlap 不考虑 IDF / 词频 / 文档长度
- BM25 解决以上所有问题，纯 Python 实现约 30 行
- 无匹配返回空，不编造 evidence
- min_score = 0.5 为默认阈值，可调
- top_k = 5 为默认返回数

## 11. 错误/失败策略

| 错误 | 行为 |
|------|------|
| 无 passages 提取 | `WarningItem(code="NO_PASSAGES")` |
| 无 claims 提取 | `WarningItem(code="NO_CLAIMS")` |
| claim 无匹配 passage | `evidence_type = INSUFFICIENT_EVIDENCE` |
| passage 太短 (< 50 chars) | 跳过 |

## 12. 测试要求

### PassageIndex 测试

| 测试 | 断言 |
|------|------|
| test_passage_ids_stable_and_sequential | passage_ids are "p001", "p002", "p003" |
| test_passage_groups_blocks_by_section | abstract blocks in same passage, method block in different |
| test_passage_formula_standalone | formula block in its own passage |
| test_passage_table_standalone | table block in its own passage |
| test_passage_skips_empty_blocks | empty text blocks skipped |
| test_passage_too_short_skipped | < 50 chars → skipped + warning |
| test_passage_too_long_split | > 2000 chars → split at sentence boundary |
| test_passage_index_schema_round_trip | PassageIndex serialize → deserialize preserves all fields |

### ClaimEvidence 测试

| 测试 | 断言 |
|------|------|
| test_claim_extractor_no_heading_claims | heading 不产生 claim |
| test_claim_extractor_method_section | at least one claim with claim_type == "METHOD" |
| test_claim_extractor_result_section | at least one claim with claim_type == "RESULT" |
| test_claim_extractor_formula_context | at least one claim with claim_type == "FORMULA_CONTEXT" |
| test_claim_evidence_v2_backward_compatible | v1 字段不变，v2 字段默认空 |
| test_claim_evidence_schema_round_trip | ClaimEvidenceV2 serialize → deserialize preserves all fields |

### BM25 / EvidenceRetriever 测试

| 测试 | 断言 |
|------|------|
| test_evidence_retriever_finds_relevant | 输入 claim → 返回相关 passage |
| test_evidence_retriever_unrelated_returns_empty | 不相关 claim → 空列表 |
| test_bm25_exact_match_scores_high | 完全匹配 claim-passage 对得分 > 0.8 |
| test_bm25_unrelated_scores_low | 不相关 claim-passage 对得分 < 0.1 |
| test_bm25_prefers_specific_over_generic | 包含论文特有术语的 passage 得分高于通用 passage |
| test_bm25_length_normalization | 长 passage 不因长度获得不公平高分 |
| test_bm25_empty_query_returns_empty | 空 query 返回空列表 |

### EvidencePack 测试

| 测试 | 断言 |
|------|------|
| test_evidence_pack_filters_insufficient | INSUFFICIENT_EVIDENCE claims excluded |
| test_evidence_pack_token_budget | total_tokens within budget |
| test_evidence_pack_groups_by_claim_type | claims grouped correctly |

### Artifact round-trip 测试

| 测试 | 断言 |
|------|------|
| test_passage_index_json_round_trip | passage_index.json serialize → deserialize |
| test_claim_evidence_json_round_trip | claim_evidence.json serialize → deserialize |
| test_evidence_index_v1_compat | old evidence_index.json still loads |

### 全局规则

- Evidence 结构检查不能替代验收。M2.2 验收必须使用真实 PDF 输入，验证 evidence chain 完整性
- 不新增依赖

## 13. 验收标准

- PassageIndex 正确构建 passages
- ClaimEvidenceV2 正确提取 claims
- BM25 能检索到相关 passages
- evidence_index.json v1 兼容
- 真实验收必须验证 evidence_ref 可追溯（通过 real PDF e2e eval）

## 14. 当前实现状态

- PassageIndex 已实现（passage_index.py）
- ClaimEvidenceV2 / claim_evidence.json 已实现（claim_extractor.py）
- EvidenceRetriever / BM25 已实现（retriever.py）
- EvidencePack 已实现（evidence_pack.py）
- evidence_index v1 wrapper 保留（grounding.py）
- pipeline 已写入 passage_index.json + claim_evidence.json + evidence_index.json
- 测试已覆盖：30+ tests
- evidence_ref 前端跳转未实现
- embedding retriever / vector DB 未实现

## 15. External Reference Implementation Notes

- **Reference source**: ARIS `tools/verify_papers.py`, `skills/research-lit/SKILL.md` (result-to-claim / paper-claim-audit)
- **Reference use**: STRATEGY_BORROW
- **Borrowed behavior**: Source discipline; verification_status; no-hallucinated-paper discipline; claim must trace back to evidence
- **ResearchSensei-owned target**: `passage_index.json`, `claim_evidence.json`, `evidence_index.json`, `EvidencePack`
- **Schema / artifact impact**: `ClaimEvidence.passage_id`, `ClaimEvidence.evidence_ref`, `ClaimEvidence.semantic_support`, `EvidencePackItem.claim_id`, `EvidencePackItem.passage_id`
- **Boundary**: ARIS primarily verifies paper-level authenticity. ResearchSensei must do passage-level evidence_ref. Paper-level verified cannot replace passage-level evidence.
- **Validation implication**: `ClaimEvidence.passage_id` must exist in PassageIndex. `evidence_ref` must be traceable. Core claims without `passage_id` cannot enter trusted explanation.

## 16. 当前未解决问题

- passage 分段策略（按 section 还是按 paragraph count）需要实测
- claim_type 判断准确性（关键词匹配 vs 位置启发式）需要实测
- BM25 min_score 和 top_k 具体值需要实测调优
- passage 切分的句子边界检测方案
- ClaimExtractor 的规则复杂度需要实测
- EvidenceRetriever 二次 validation 规则

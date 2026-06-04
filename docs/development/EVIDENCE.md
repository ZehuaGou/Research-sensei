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
| PaperQA | passage retrieval | github.com/Future-House/paper-qa | REFERENCE_ONLY | 否 | — | 参考 chunk/retrieve 思路 |
| ARIS result-to-claim | claim audit | github.com/wanshuiyin/Auto-claude-code-research-in-sleep | REFERENCE_ONLY | 否 | — | 参考 claim-evidence binding |
| OpenScholar | citation accuracy | 未确认 repo | REFERENCE_ONLY | 否 | — | 参考 citation accuracy |

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

## 4. 当前代码位置

- `src/researchsensei/grounding.py` — `build_evidence_index()`
- `src/researchsensei/schemas/evidence.py` — `ClaimEvidence`, `EvidenceIndex`
- 当前 evidence 是 block-level：一个 block 对应一个 evidence entry

## 5. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `DocumentIngestion` / `DocumentBlock` |
| 输出 | 升级后的 `evidence_index.json`（向后兼容） |
| 每个 claim 必须 | 能回指原始 block/passage |

## 6. Artifact

v2 精读链路新增 3 个 artifact：

| artifact | 用途 | schema_version |
|----------|------|----------------|
| `passage_index.json` | PassageIndex，passage 级文档表示 | v2 |
| `claim_evidence.json` | ClaimEvidence v2，含 passage_id / claim_type / semantic_support | v2 |
| `evidence_index.json` | v1 兼容 wrapper，保留旧字段 | v1（无 schema_version 时默认 v1） |

- `evidence_index.json` 保留 v1 兼容，旧测试可继续读取。
- `claim_evidence.json` 承载 v2 字段，audit 和 Phase 12 读取此文件。
- `passage_index.json` 持久化 passage 构建结果，audit 和前端 evidence 跳转依赖此文件。
- 旧 artifact 缺少 `schema_version` 时按 v1 读取。
- additive 字段通过 Pydantic 默认值兼容。

## 7. 核心类和方法签名

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
    evidence_refs: list[str] = Field(default_factory=list)  # 保留 block 级 evidence_ref
    source_block_types: list[str] = Field(default_factory=list)  # block.type 列表
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
    source_sentence: str = ""    # 原文句子
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

DATASET / METRIC 暂不作为独立 claim_type，先归入 RESULT 或后续扩展。

### 命名规范

| 标识 | 格式 | 示例 |
|------|------|------|
| passage_id | `p{nnn}` | p001, p002, p003 |
| claim_id | `{paper_id}:claim:c{nnn}` | paper123:claim:c001 |
| evidence_ref | 保留 block 级引用 | paper123:b003 |
| ClaimEvidence | 同时保留 passage_id + evidence_ref | passage_id="p002", evidence_ref="paper123:b003" |

### semantic_support 值

| 值 | 含义 |
|----|------|
| DIRECT_QUOTE | claim 可直接由原文句子支持 |
| PARAPHRASE | claim 是原文的忠实改写 |
| REASONABLE_INFERENCE | 根据上下文合理推断 |
| INSUFFICIENT_EVIDENCE | 证据不足 |

## 8. Passage 构建算法

**输入**: `DocumentIngestion.blocks`

**算法**:
1. 遍历 blocks，按 section 分组
2. heading blocks 不合并到 passage（只标记 section 边界）
3. 同一 section 的连续 non-heading blocks 合并为一个 passage
4. formula block 单独成 passage（不混入段落）
5. table block 单独成 passage（不混入段落）
6. 空文本 blocks（text.strip() == ""）跳过
7. 太短的 passage（< 50 chars）跳过，产生 `WarningItem(code="PASSAGE_TOO_SHORT", message="...")`
8. 太长的 passage（> 2000 chars）按句子边界切分
9. section 缺失时用 "unknown"，不直接阻断
10. passage_id 按序分配（p001, p002, ...）
11. block_ids 保存该 passage 包含的所有 block_id
12. evidence_refs 保留所有 block 级 evidence_ref
13. normalized_text = text.lower().strip()
14. 如果无 passages 可提取，产生 `WarningItem(code="NO_PASSAGES", message="...")`

**输出**: `PassageIndex`

## 9. Claim 提取算法

**输入**: `PassageIndex.passages`

**算法**（初版不用 LLM，基于 section + keyword + 句子规则）:
1. 遍历每个 passage
2. heading 不生成 claim
3. 空文本不生成 claim
4. 根据 section + 关键词判断 claim_type:
   - Abstract + "propose/present/introduce/develop" → CONTRIBUTION
   - Method section + "we propose/our method/framework/model" → METHOD
   - Experiment/Result section + "improve/outperform/achieve/reduce" → RESULT
   - limitation/future work section → LIMITATION
   - formula block 或含 "loss/objective/equation/optimize" → FORMULA_CONTEXT
5. claim_id 生成: `{paper_id}:claim:{n}` (递增)
6. claim_text 从 passage 中提取相关句子（不复制整段）
7. evidence_ref = `{paper_id}:{first_block_id}`
8. quote_or_summary 截取前 200 chars
9. confidence 基于 section 类型和关键词匹配度
10. semantic_support: DIRECT_QUOTE（直接引用）/ PARAPHRASE（改写）/ REASONABLE_INFERENCE（推断）/ INSUFFICIENT_EVIDENCE（不足）
11. 无法判断时必须 INSUFFICIENT_EVIDENCE 或跳过
12. 不允许 "This block belongs to method section" 这种伪 claim

## 10. Artifact 策略

**选择**: v2 新增 `passage_index.json` 和 `claim_evidence.json`，`evidence_index.json` 保留 v1 兼容 wrapper。

**理由**:
- ResearchSensei 是 artifact-driven 系统，重要中间结果应可审计、可复现、可调试
- audit 需要独立读取 passage 构建结果，不能依赖重跑算法
- 前端 evidence 跳转需要 passage 层信息
- `ClaimEvidence.passage_id` 不能指向不存在的运行时对象
- 质量测试需要直接检查 passage 分段
- `evidence_index.json` 保留 v1 兼容，旧测试不破坏
- 下游（paper_card, formula_card, teaching_card）不需要改代码就能继续工作
- `claim_evidence.json` 承载 v2 字段，audit 和 Phase 12 读取此文件

**artifact versioning**:
- `passage_index.json` 和 `claim_evidence.json` 写 `schema_version="v2"`
- `evidence_index.json` 保留 v1（无 schema_version 时默认 v1）
- additive 字段通过 Pydantic 默认值兼容

## 11. 错误/失败策略

| 错误 | 行为 |
|------|------|
| 无 passages 提取 | `WarningItem(code="NO_PASSAGES", message="...")` |
| 无 claims 提取 | `WarningItem(code="NO_CLAIMS", message="...")` |
| claim 无匹配 passage | `evidence_type = INSUFFICIENT_EVIDENCE` |
| passage 太短 (< 50 chars) | 跳过 |

## 12. 测试断言

| 测试 | 断言 |
|------|------|
| test_passage_ids_stable_and_sequential | passage_ids are "p001", "p002", "p003" |
| test_passage_groups_blocks_by_section | abstract blocks in same passage, method block in different |
| test_claim_extractor_no_heading_claims | heading 不产生 claim |
| test_claim_extractor_method_section | at least one claim with claim_type == "METHOD" |
| test_claim_extractor_result_section | at least one claim with claim_type == "RESULT" |
| test_claim_extractor_formula_context | at least one claim with claim_type == "FORMULA_CONTEXT" |
| test_claim_evidence_v2_backward_compatible | v1 字段不变，v2 字段默认空 |
| test_evidence_retriever_finds_relevant | 输入 claim → 返回相关 passage |
| test_evidence_retriever_unrelated_returns_empty | 不相关 claim → 空列表 |
| test_bm25_exact_match_scores_high | 完全匹配 claim-passage 对得分 > 0.8 |
| test_bm25_unrelated_scores_low | 不相关 claim-passage 对得分 < 0.1 |
| test_bm25_prefers_specific_over_generic | 包含论文特有术语的 passage 得分高于通用 passage |
| test_bm25_length_normalization | 长 passage 不因长度获得不公平高分 |
| test_bm25_empty_query_returns_empty | 空 query 返回空列表 |

## 13. Hard-Fail

- 只有 block-level（无 passage-level）
- 无 claim extraction
- 修改 parser 或 pipeline
- 真实网络 / LLM 在默认测试
- 现有测试破坏

## 14. EvidenceRetriever 初版策略

**当前不使用向量库、不联网、不用 LLM、不新增依赖。**

### 为什么用 BM25 而不是 simple overlap

- simple overlap 不考虑 IDF（高频词 "the"/"model" 和低频词 "anomaly" 权重一样）
- simple overlap 不考虑词频（出现 10 次和 1 次得分一样）
- simple overlap 不考虑文档长度（50 词 passage 和 500 词 passage 同样 overlap 比例得分一样）
- BM25 解决以上所有问题，纯 Python 实现约 30 行

### BM25 实现

```python
import math
from collections import Counter
import re

def tokenize(text: str) -> list[str]:
    """Lowercase, split on whitespace/punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())

def compute_idf(corpus_tokens: list[list[str]]) -> dict[str, float]:
    """Compute IDF for each term in the corpus."""
    n = len(corpus_tokens)
    doc_freq: Counter = Counter()
    for tokens in corpus_tokens:
        doc_freq.update(set(tokens))
    return {
        term: math.log((n - df + 0.5) / (df + 0.5) + 1)
        for term, df in doc_freq.items()
    }

def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avg_dl: float,
    idf: dict[str, float],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """BM25 scoring function."""
    doc_len = len(doc_tokens)
    tf = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt not in tf or qt not in idf:
            continue
        numerator = tf[qt] * (k1 + 1)
        denominator = tf[qt] + k1 * (1 - b + b * doc_len / avg_dl)
        score += idf[qt] * numerator / denominator
    return score
```

### EvidenceRetriever

```python
class EvidenceRetrievalResult(SenseiModel):
    passage: Passage
    score: float

class EvidenceRetriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75, min_score: float = 0.5, top_k: int = 5): ...
    def retrieve(self, claim_text: str, index: PassageIndex) -> list[EvidenceRetrievalResult]: ...
```

**规则**:
- 无匹配返回空，不编造 evidence
- min_score = 0.5 为默认阈值，可调
- top_k = 5 为默认返回数
- IDF 在 PassageIndex 上预计算，不每次 retrieve 重算

### 测试断言

| 测试 | 断言 |
|------|------|
| test_bm25_exact_match_scores_high | 完全匹配 claim-passage 对得分 > 0.8 |
| test_bm25_unrelated_scores_low | 不相关 claim-passage 对得分 < 0.1 |
| test_bm25_prefers_specific_over_generic | 包含论文特有术语的 passage 得分高于通用 passage |
| test_bm25_length_normalization | 长 passage 不因长度获得不公平高分 |
| test_bm25_empty_query_returns_empty | 空 query 返回空列表 |

## 16. 验收标准

- PassageIndex 正确构建 passages
- ClaimEvidenceV2 正确提取 claims
- BM25 能检索到相关 passages
- evidence_index.json v1 兼容
- 默认测试不联网、不真实调用 LLM

## 17. 当前实现状态

- 代码已实现：PassageIndex, ClaimEvidenceV2, BM25 EvidenceRetriever, EvidencePack
- pipeline 已写入 passage_index.json + claim_evidence.json
- 测试已覆盖：30+ tests
- evidence_ref 跳转未实现

## 18. 当前未解决问题

- passage 分段策略（按 section 还是按 paragraph count）需要实测
- claim_type 判断准确性（关键词匹配 vs 位置启发式）需要实测
- BM25 min_score 和 top_k 具体值需要实测调优
- passage 切分的句子边界检测方案
- ClaimExtractor 的规则复杂度需要实测
- EvidenceRetriever 二次 validation 规则

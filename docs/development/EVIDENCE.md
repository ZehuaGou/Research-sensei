# Evidence 模块

---

## 1. 模块目标

从 block-level evidence 升级到 passage/claim-level evidence，使每个解释能回指具体 claim 而非整个 block。

## 2. 非目标

- 不用 LLM 做 claim extraction
- 不用向量数据库
- 不新增依赖

## 3. 外部项目调研

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

- `evidence_index.json` 格式向后兼容（v1 字段不变，v2 字段可选）

## 7. 核心类和方法签名

```python
class Passage(SenseiModel):
    passage_id: str
    block_ids: list[str]
    section: str
    text: str
    normalized_text: str

class PassageIndex(SenseiModel):
    paper_id: str
    passages: list[Passage]
    warnings: list[WarningItem] = []

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

class ClaimExtractor:
    def extract(self, passages: list[Passage]) -> list[ClaimEvidence]: ...

class EvidenceRetriever:
    def retrieve(self, claim: str, index: PassageIndex) -> list[Passage]: ...
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
4. 空文本 blocks（text.strip() == ""）跳过
5. 太短的 passage（< 50 chars）跳过，产生 `WarningItem(code="PASSAGE_TOO_SHORT", message="...")`
6. 太长的 passage（> 2000 chars）按句子边界切分
7. passage_id 按序分配（p001, p002, ...）
8. block_ids 保存该 passage 包含的所有 block_id
9. normalized_text = text.lower().strip()
10. 如果无 passages 可提取，产生 `WarningItem(code="NO_PASSAGES", message="...")`

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

**选择**: 升级 `evidence_index.json`（向后兼容），不新增独立文件。

**理由**:
- 现有 `EvidenceIndex` schema 已有 `claims: list[ClaimEvidence]`
- `ClaimEvidence` 新增 v2 可选字段（passage_id, claim_type, semantic_support）
- v1 字段不变，现有测试不破坏
- 下游（paper_card, formula_card, teaching_card）不需要改代码就能继续工作
- PassageIndex 可以作为中间数据结构，不一定要持久化为独立 artifact

## 10. 错误/失败策略

| 错误 | 行为 |
|------|------|
| 无 passages 提取 | `WarningItem(code="NO_PASSAGES", message="...")` |
| 无 claims 提取 | `WarningItem(code="NO_CLAIMS", message="...")` |
| claim 无匹配 passage | `evidence_type = INSUFFICIENT_EVIDENCE` |
| passage 太短 (< 50 chars) | 跳过 |

## 11. 测试断言

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

## 12. Hard-Fail

- 只有 block-level（无 passage-level）
- 无 claim extraction
- 修改 parser 或 pipeline
- 真实网络 / LLM 在默认测试
- 现有测试破坏

## 13. EvidenceRetriever 初版策略

**当前不使用向量库、不联网、不用 LLM。**

```python
def tokenize(text: str) -> list[str]:
    """Lowercase, split on whitespace, remove punctuation."""
    import re
    return re.findall(r"[a-z0-9]+", text.lower())

def lexical_score(claim_text: str, passage: Passage) -> float:
    """Score = overlap / claim_token_count."""
    claim_tokens = set(tokenize(claim_text))
    passage_tokens = set(tokenize(passage.text))
    if not claim_tokens:
        return 0.0
    overlap = len(claim_tokens & passage_tokens)
    return overlap / len(claim_tokens)

def retrieve(claim_text: str, index: PassageIndex, top_k: int = 5, min_score: float = 0.2) -> list[Passage]:
    """Retrieve passages relevant to a claim."""
    scored = [(p, lexical_score(claim_text, p)) for p in index.passages]
    scored = [(p, s) for p, s in scored if s >= min_score]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, s in scored[:top_k]]
```

**规则**:
- 无匹配返回空，不编造 evidence
- min_score = 0.2 为默认阈值，可调
- top_k = 5 为默认返回数

## 14. 当前未解决问题

- passage 分段策略（按 section 还是按 paragraph count）需要实测
- claim_type 判断准确性（关键词匹配 vs 位置启发式）需要实测
- EvidenceRetriever 阈值和评分策略需要实测调优
- 是否需要把 PassageIndex 持久化为独立 artifact

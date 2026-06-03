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
- **机制**: 将论文切分为 passages → embedding → 检索相关 passages → 基于 passages 生成 citation-backed answer
- **对本模块的用处**: passage retrieval 的 chunk/retrieve 思路可借鉴；citation-backed answer 的 prompt 结构可参考
- **当前是否直接接入**: 否 — PaperQA 是 QA 系统，不是教学系统；依赖较重（需要 embedding model）
- **借鉴的设计**: passage 分段策略、relevance ranking、citation 注入 prompt

### OpenScholar

- **机制**: passage-level retrieval + citation accuracy 评估
- **对本模块的用处**: citation accuracy 评估方法可参考
- **当前是否直接接入**: 否 — 主要是 benchmark，不是工具

### ARIS result-to-claim / paper-claim-audit

- **机制**: result-to-claim 判断实验结果是否支持论文声明；paper-claim-audit 用零上下文审计验证论文数字
- **对本模块的用处**: claim extraction 的分类思想可借鉴；evidence_ref 校验规则可参考
- **当前是否直接接入**: 否 — 只参考设计

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

## 8. Passage 从 blocks 怎么构建

- 同一 section 的连续 blocks 合并为一个 passage
- heading blocks 不合并到 passage（只标记 section 边界）
- 空文本 blocks 跳过
- passage_id 按序分配（p001, p002, ...）

## 9. Claim 怎么从 passage 提取

- Abstract 中含 "propose / present / introduce / develop" → CONTRIBUTION
- Method section 中含 "we propose / our method / framework / model" → METHOD
- Experiment/Result section 中含 "improve / outperform / achieve / reduce" → RESULT
- limitation/future work section → LIMITATION
- formula block 或含 "loss / objective / equation / optimize" → FORMULA_CONTEXT
- heading 不生成 claim
- 空文本不生成 claim
- 不允许 claim_text 是 "This block belongs to ..."

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

## 13. 当前未解决问题

- passage 分段策略（按 section 还是按 paragraph count）
- claim_type 判断准确性（关键词匹配 vs 位置启发式）
- EvidenceRetriever 是否用 TF-IDF 还是更简单的关键词匹配

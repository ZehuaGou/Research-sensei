# ResearchSensei Design

---

## 1. 项目定位

ResearchSensei 是论文研读导师系统，帮助研究生真正读懂论文。

**是**：论文研读导师、公式解释器、科研思维训练系统、导师追问准备系统、evidence-constrained paper understanding system。

**不是**：普通摘要器、自动写论文系统、自动做科研系统、RAG 问答机器人、ARIS clone。

---

## 2. 技术路线

- Vue 3 前端保留，不重写
- Python / FastAPI / Pydantic 后端
- `backend/` 冻结，只作迁移参考
- 新功能只走 `src/researchsensei/`
- JSON artifact 驱动链路
- mock-first 测试

---

## 3. 核心架构

```
Product Layer     → Vue / FastAPI / workspace / job / artifact / Pydantic / mock tests
Parser Layer      → ParserAdapter interface, LightweightParser fallback, optional external parsers
Evidence Layer    → PassageIndex, ClaimExtractor, ClaimEvidence, EvidenceRetriever
Paper Understanding → paper_card, formula_cards, teaching_cards, evidence-constrained LLM
Direction Layer   → query_plan, candidate_pool, filtered_candidates, reading_plan
Audit Layer       → explanation audit, formula audit, evidence audit, reviewer independence
```

---

## 4. Artifact 链路

### 单篇论文

```
source_status.json → parsed_document.json → evidence_index.json
→ paper_skeleton.json → paper_card.json → formula_cards.json → teaching_cards.json
```

### 方向搜索

```
query_plan.json → candidate_pool.json → filtered_candidates.json → reading_plan.json
```

---

## 5. 外部项目复用原则

- 不为了复用而复用
- 不整包迁移 ARIS
- 不默认接入重依赖
- 引入前必须做 reuse gate
- 默认 pytest 不联网、不调 LLM

| 项目 | 决策 |
|------|------|
| ARIS | REFERENCE_ONLY — 参考 audit chain / reviewer independence |
| PaperQA | OPTIONAL_ADAPTER — 参考 passage retrieval |
| OpenScholar | REFERENCE_ONLY — 参考 citation accuracy |
| STORM | REFERENCE_ONLY — 参考 outline / multi-perspective |
| Docling / Nougat / Marker / MinerU | OPTIONAL_ADAPTER — 可选 parser |
| Unstructured | NOT_USE |

---

## 6. 当前真实状态

- Phase 1-11 = baseline infrastructure complete (281 tests)
- Phase 6 evidence = block-level，不是 claim-level
- Phase 8-10 = rule-based baseline，不是导师级讲解
- Phase 11 = direction pipeline v1，不是完整 literature review
- Phase 12 = frozen

---

## 7. 阶段路线

| 阶段 | 内容 |
|------|------|
| Phase 1-11 | baseline complete |
| Paper Understanding 升级 | ParserAdapter + PassageIndex + ClaimEvidence + LLM + Quality Benchmark |
| Phase 12 | Patterns + Drill（冻结，需 Paper Understanding 升级完成） |
| Phase 13+ | Direction Map / Frontend / Advisor / Reliability / Benchmark / Deploy |

---

## 8. 禁止事项

1. 不允许直接进入 Phase 12
2. 不允许把 rule-based baseline 称为导师级讲解
3. 不允许把 block-level evidence 称为 claim-level grounding
4. 不允许无 evidence 生成解释
5. 不允许默认测试真实联网或真实 LLM
6. 不允许未经 reuse gate 新增依赖

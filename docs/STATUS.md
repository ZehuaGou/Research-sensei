# ResearchSensei Status

---

## 1. 当前总判断

- 主链路 v1 已阶段性封版（详见 docs/MAIN_CHAIN_V1_REVIEW.md）
- 不是最终产品
- Phase 12 仍冻结
- 当前不应该继续碎片化小步开发
- 后续应按模块闭环推进

---

## 2. 当前阶段已完成内容

### Pipeline 主链路：已阶段完成

- ParserAdapter 接入 SinglePaperIngestionRunner
- PassageIndex 生成并写入 passage_index.json
- ClaimEvidenceV2 生成并写入 claim_evidence.json
- EvidenceRetriever / BM25 已实现（runtime only）
- EvidencePack runtime builder 已实现
- isolated LLM v2 builders（fail-closed，不 fallback）
- pipeline v2 path（SUCCESS / DEGRADED_STRUCTURAL / BLOCKED_UNDERSTANDING）
- UnderstandingStatus + DownstreamGates + EvidencePackSummary
- QualityAuditor 已接入 pipeline
- quality_report.json 写入所有非 FAILED run
- audit BLOCK 可覆盖 v2 SUCCESS/DEGRADED
- API gating（/understanding_status + /cards + /artifacts debug-only）
- BASELINE_ONLY / BLOCKED 不返回 cards
- 481 backend tests passing

### Frontend：部分完成

- UploadView 已对齐 /api/v1/documents/parse
- LearningWorkspaceView 已对齐 /understanding_status + /cards
- StatusBanner 组件已实现并有测试（7 tests）
- BASELINE_ONLY / BLOCKED 不展示 cards
- DEGRADED 显示降级提示
- Phase 12 tabs 显示"未开放"
- LearningWorkspaceView / UploadView 测试尚未完成

### Audit：结构性 audit 已完成，质量型 audit 未完成

- F-1 到 F-6 结构性规则已实现
- candidate audit 语义已写清
- formula-heavy / raw-copy / generic-output 未完成

### Evidence：主链路已完成，evidence_ref 跳转未完成

- passage_index.json / claim_evidence.json / evidence_index.json 职责清晰
- EvidencePack 不持久化
- EvidencePackSummary 写入 UnderstandingStatus
- evidence_ref 原文跳转尚未实现

---

## 3. 模块总控矩阵

| 模块 | 文档状态 | 代码状态 | 测试状态 | 当前结论 | 阶段完成 |
|------|---------|---------|---------|---------|---------|
| Parser / ParserAdapter | 已完成 | 已完成 | 已完成 | 可用 | ✅ 已阶段完成 |
| PassageIndex | 已完成 | 已完成 | 已完成 | 可用 | ✅ 已阶段完成 |
| ClaimEvidenceV2 | 已完成 | 已完成 | 已完成 | 可用 | ✅ 已阶段完成 |
| EvidenceRetriever / BM25 | 已完成 | 已完成 | 已完成 | runtime only | ✅ 已阶段完成 |
| EvidencePack | 已完成 | 已完成 | 已完成 | runtime only | ✅ 已阶段完成 |
| baseline card builders | 已完成 | 已完成 | 已完成 | rule-based fallback | ✅ 已阶段完成 |
| LLM v2 builders | 已完成 | 已完成 | 已完成 | fail-closed | ✅ 已阶段完成 |
| UnderstandingStatus | 已完成 | 已完成 | 已完成 | 5 状态 + DownstreamGates | ✅ 已阶段完成 |
| QualityAuditor / QualityReport | 已完成 | 已完成 | 已完成 | F-1 到 F-6 | ✅ 已阶段完成 |
| Pipeline | 已完成 | 已完成 | 已完成 | baseline + v2 path | ✅ 已阶段完成 |
| API gating | 已完成 | 已完成 | 已完成 | /understanding_status + /cards | ✅ 已阶段完成 |
| Frontend Upload | 已完成 | 已完成 | 未完成 | 已对齐 API，缺测试 | ⚠️ 部分完成 |
| Frontend LearningWorkspace | 已完成 | 已完成 | 未完成 | 已对齐 API，缺测试 | ⚠️ 部分完成 |
| Frontend tests (StatusBanner) | 已完成 | 已完成 | 已完成 | 7 tests | ✅ 已阶段完成 |
| Frontend tests (页面级) | 文档有 | 未开始 | 未开始 | 无 | ❌ 未开始 |
| Real LLM integration | 文档有 | 未开始 | 未开始 | 无 | ❌ 未开始 |
| Docling parser adapter | 文档有 | 未开始 | 未开始 | 无 | ❌ 未开始 |
| evidence_ref 跳转 | 文档有 | 未开始 | 未开始 | 无 | ❌ 未开始 |
| Debug/admin 鉴权 | 文档有 | 未开始 | 未开始 | 无 | ❌ 未开始 |
| Phase 12 | 冻结中 | 冻结中 | 冻结中 | 不可使用 | 🔒 冻结中 |

---

## 4. 当前主要差距

- Real LLM smoke 未做（v2 path 从未用真实 LLM 跑过）
- Docling parser adapter 未做
- evidence_ref 原文跳转未做
- Frontend 页面级测试不足（LearningWorkspaceView / UploadView 无测试）
- Audit 质量规则不足（formula-heavy / raw-copy / generic-output 未实现）
- Debug/admin 鉴权未做（当前用 SENSEI_DEBUG 环境变量）
- Phase 12 冻结
- 完整产品还未完成

---

## 5. 下一阶段推荐顺序

### P0：先做

1. **Frontend Testing 模块闭环**
   - StatusBanner 已完成
   - 下一步补 LearningWorkspaceView status gating 测试
   - 再补 UploadView upload flow 测试
   - 完成后才算 Frontend Testing 第一阶段完成

2. **Real LLM smoke 方案讨论**
   - 先讨论 env / model / cost / failure handling
   - 不直接调用真实 LLM

### P1：近期做

- Real LLM smoke 实现
- DoclingParserAdapter
- Audit 质量规则增强（formula-heavy / raw-copy / generic-output）
- /quality_report debug endpoint
- Debug/admin 鉴权

### P2：后置

- evidence_ref 跳转
- e2e 测试
- Phase 12 解冻准备

---

## 6. 当前禁止事项

- 不进入 Phase 12
- 不再碎片化一个小点一个 commit，除非是 bugfix
- 不新增大依赖，除非先讨论；已新增的前端测试依赖是 Vitest / Vue Test Utils / jsdom
- 不真实调用 LLM，除非先完成 smoke 方案
- 不把 BASELINE_ONLY 当最终导师级理解
- 不把 DEGRADED_STRUCTURAL 当完整导师级解释
- 不通过 /artifacts 给普通前端取数据

---

## 7. 下一步唯一建议

下一步建议不是继续加新功能，而是完成 Frontend Testing 模块闭环：

- LearningWorkspaceView status gating 测试
- UploadView upload flow 测试
- npm test / npm build
- pytest
- 模块 review

---

## 8. 测试和 commit

- backend pytest: 481 passed
- frontend npm test: 7 passed (StatusBanner)
- frontend npm run build: 成功
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

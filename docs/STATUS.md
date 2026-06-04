# ResearchSensei Status

---

## 1. 当前总判断

- 主链路 v1 已阶段性封版（详见 docs/MAIN_CHAIN_V1_REVIEW.md）
- 不是最终产品
- 当前处于设计文档和开发文档整理阶段
- 暂停继续代码开发
- 下一步是逐模块补详细开发文档
- 不再按 Phase 推进，不再碎片化推进

---

## 2. 模块总控表

| 编号 | 模块 | 文档状态 | 代码状态 | 测试状态 | 当前结论 | 下一步 |
|------|------|---------|---------|---------|---------|--------|
| M1 | 论文搜索、获取与阅读计划 | ✅ M1_LITERATURE_SEARCH.md | ✅ 基础闭环完成 | ✅ 已测试 | M1.1-M1.5 基础闭环已打通 | Semantic Scholar / Crossref 后补 |
| M1.1 | 搜索规划 | ✅ | ✅ QueryPlanner | ✅ | 已阶段完成 | — |
| M1.2 | 多源检索 | ✅ | ⚠️ arXiv/OpenAlex 已实现 | ⚠️ | 部分完成 | Semantic Scholar / Crossref 后补 |
| M1.3 | 论文原始材料获取 | ✅ | ✅ PaperSourceResolver | ✅ | 基础 source resolution 已实现；不解析论文内容 | 真实 source/PDF 获取 adapter 后补 |
| M1.4 | 去重评分 | ✅ | ✅ SelectionService | ✅ | 已阶段完成 | — |
| M1.5 | 阅读计划 | ✅ | ✅ DirectionRunner | ✅ | 已阶段完成 | — |
| M2 | 单篇论文解析、精读与可信讲解 | ✅ 5 个子文档 | ✅ 已实现 | ✅ 已测试 | 已阶段完成 | — |
| M2.1 | 解析 | ✅ M2_1_PARSER.md | ✅ ParserAdapter + LightweightParser | ✅ | 已阶段完成 | Docling adapter 后补 |
| M2.2 | 证据链路 | ✅ M2_2_EVIDENCE.md | ✅ PassageIndex + ClaimEvidenceV2 + BM25 | ✅ | 已阶段完成 | evidence_ref 跳转后补 |
| M2.3 | 讲解生成 | ✅ M2_3_PAPER_UNDERSTANDING.md | ✅ baseline + v2 builders + live smoke | ✅ | 已阶段完成；real LLM smoke 入口已实现 | 持续扩大真实样例 |
| M2.4 | 质量审计 | ✅ M2_4_AUDIT_QUALITY.md | ✅ QualityAuditor F-1 到 F-6 | ✅ | 已阶段完成 | 质量规则增强后补 |
| M2.5 | 状态门控 | ✅ M2_5_FULL_PIPELINE.md | ✅ UnderstandingStatus + DownstreamGates | ✅ | 已阶段完成 | — |
| M3 | 接口与前端展示 | ✅ M3_FRONTEND_RENDER.md | ⚠️ 部分完成 | ⚠️ 部分测试 | 部分完成 | 页面级测试补完 |
| M3.1 | 后端 API | ✅ | ✅ /understanding_status + /cards | ✅ | 已阶段完成 | /quality_report 后补 |
| M3.2 | 上传页面 | ✅ | ✅ UploadView | ❌ 缺测试 | 部分完成 | 补 UploadView 测试 |
| M3.3 | 学习工作区 | ✅ | ✅ LearningWorkspaceView | ❌ 缺测试 | 部分完成 | 补 LearningWorkspaceView 测试 |
| M3.4 | 状态提示 | ✅ | ✅ StatusBanner | ✅ 7 tests | 已阶段完成 | — |
| M3.5 | 调试入口 | ✅ | ✅ /artifacts debug-only | ✅ | 已阶段完成 | debug 鉴权后补 |
| M4 | 互动式学习与长期记忆 | ✅ M4_INTERACTIVE_LEARNING.md | ❌ 未实现 | ❌ 未测试 | 文档已设计，代码未实现 | — |
| M4.1 | 选中内容解释 | ✅ | ❌ | ❌ | 文档已设计 | — |
| M4.2 | 符号与公式解释 | ✅ | ❌ | ❌ | 文档已设计 | — |
| M4.3 | 上下文追问 | ✅ | ❌ | ❌ | 文档已设计 | — |
| M4.4 | 导师式追问与研究训练 | ✅ | ❌ | ❌ | 文档已设计 | — |
| M4.5 | 知识库与长期记忆 | ✅ | ❌ | ❌ | 文档已设计 | — |
| M4.6 | 记忆优先检索 | ✅ | ❌ | ❌ | 文档已设计 | — |
| M5 | 工程可靠性与测试保障 | ✅ M5_ENGINEERING_RELIABILITY.md | ⚠️ 部分完成 | ⚠️ 部分测试 | 部分完成 | — |
| M5.1 | 后端测试 | ✅ | ✅ 481 tests | ✅ | 已阶段完成 | — |
| M5.2 | 前端测试 | ✅ | ⚠️ StatusBanner only | ⚠️ | 部分完成 | 补页面级测试 |
| M5.3 | LLM smoke / 成本 | ✅ | ✅ tests_live + scripts/run_live_eval.py | ✅ opt-in | 已实现受控 live eval；不进入默认 pytest | 增加更多真实样例和定价配置 |
| M5.4 | 缓存 | ✅ | ✅ ResponseCache | ✅ | 已阶段完成 | — |
| M5.5 | 安全 | ✅ | ❌ | ❌ | 文档已补齐，secret scan 工具未接入 | 接入 gitleaks / pre-commit |
| M5.6 | Debug/admin | ⚠️ | ⚠️ SENSEI_DEBUG only | ⚠️ | 部分完成 | 鉴权后补 |
| M5.7 | CI | ✅ | ❌ | ❌ | 文档已补齐，CI 未配置 | 配置 CI / release check |

---

## 3. 当前主要差距

- M4 互动式学习文档已设计、代码未实现
- Real LLM smoke 已有受控入口，但真实样例数量仍少
- Docling parser adapter 未做
- evidence_ref 原文跳转未做
- Frontend 页面级测试不足
- Audit 质量规则不足
- Debug/admin 鉴权未做
- 完整产品还未完成

---

## 4. 下一步推进顺序

按 M1 → M2 → M3 → M4 → M5 推进。每个模块先检查文档完整性，再考虑代码。

### M1 论文搜索、获取与阅读计划

- M1.1-M1.5 基础闭环已打通：query_plan → candidate_pool → source_resolution → filtered_candidates → reading_plan
- M1.3 当前只做候选论文 source metadata/status resolution，不做 M2 论文解析
- Semantic Scholar / Crossref、真实联网 source 获取、实际下载策略仍按后续 adapter 补充

### M2 单篇论文解析、精读与可信讲解

- M2.3 已接入 real LLM smoke：`tests_live/test_m2_real_llm_smoke.py` 与 `scripts/run_live_eval.py`
- 默认测试仍不真实调用 LLM；live eval 必须显式设置 `RUN_LLM_TESTS=1` 和 `RESEARCHSENSEI_LIVE_EVAL=1`
- 当前 live smoke 使用小型 synthetic paper，验证 parser/evidence/v2 builders/QualityAuditor/UnderstandingStatus
- 真实模型输出可能触发 DEGRADED_STRUCTURAL；必须以 live report 为准，不得伪装 SUCCESS

### M3 接口与前端展示

- 检查 M3.1-M3.5 开发文档是否完整
- 特别检查 UploadView / LearningWorkspaceView 页面级测试要求
- 不直接写代码

### M4 互动式学习与长期记忆

- M4 是正式一级模块
- 当前文档待完善，代码未实现
- 先完善 M4.1-M4.6 开发文档、测试要求、验收标准
- 当前不进入代码实现

### M5 工程可靠性与测试保障

- M5.3 已实现 opt-in live eval，输出 `reports/live_eval/live_eval_report.json`
- `reports/live_eval/` 已加入 `.gitignore`，报告、工作目录、下载物不得提交
- M5 仍是全局工程保障，不替代 M1-M4 子模块测试

---

## 5. 开发与测试规则

- 后续按 M1 → M5 推进
- 每个 Mx.y 子模块都必须独立测试（unit + failure-path + schema/artifact）
- 一级模块完成后必须做集成测试
- 每次提交后必须跑全项目基础回归（pytest + frontend build + frontend test）
- M5 是全局测试与工程保障模块，不是"最后测试模块"
- 不允许跳过子模块测试进入下一个子模块

---

## 6. 当前禁止事项

- M4 当前不进入代码开发
- 不再碎片化一个小点一个 commit，除非是 bugfix
- 不新增大依赖，除非先讨论
- 不真实调用 LLM，除非先完成 smoke 方案
- 不把 BASELINE_ONLY 当最终导师级理解
- 不把 DEGRADED_STRUCTURAL 当完整导师级解释
- 不通过 /artifacts 给普通前端取数据

---

## 7. 测试和 commit

- backend pytest: 481 passed
- frontend npm test: 7 passed (StatusBanner)
- frontend npm run build: 成功
- commit: 以 `git rev-parse --short HEAD` 为准，不在 STATUS.md 固化记录

# ResearchSensei Status

---

## 1. 当前总判断

- 项目有文档体系和 489 mock tests，但真实产品能力不足
- **没有任何模块通过真实端到端验收（REAL_E2E_VERIFIED）**
- **没有任何模块达到 PRODUCTION_READY**
- 不能把 mock 测试通过写成模块完成
- 不能把 synthetic markdown 测试写成真实论文验证
- 不能把自写薄 wrapper 写成成熟搜索能力
- 成熟项目（arxiv.py / pyalex / Docling / Semantic Scholar）接入不足
- 全项目状态以本文件为准

---

## 2. 状态等级定义

| 等级 | 含义 |
|------|------|
| NOT_STARTED | 无代码、无文档 |
| DOC_ONLY | 有文档、无代码 |
| MOCK_TESTED | 有代码、mock 测试通过、无真实验收 |
| THIN_WRAPPER_ONLY | 代码只是对单个 API/库的薄封装，无成熟项目接入 |
| LIVE_SEARCH_VERIFIED | 真实联网搜索已验证 |
| REAL_API_VERIFIED | 真实 API（非搜索）已验证 |
| REAL_PDF_VERIFIED | 真实 PDF 下载 + 解析已验证 |
| REAL_LLM_VERIFIED | 真实 LLM 调用 + 输出验证已通过 |
| REAL_FRONTEND_BACKEND_VERIFIED | 真实前后端联调已验证 |
| REAL_E2E_VERIFIED | 真实端到端（搜索→PDF→解析→LLM→审计→展示）已验证 |
| PRODUCTION_READY | 可用于生产环境 |

---

## 3. 模块总控表

| 编号 | 模块 | 文档状态 | 代码状态 | 测试状态 | 当前真实状态 | 下一步 |
|------|------|---------|---------|---------|-------------|--------|
| M1 | 论文搜索、获取与阅读计划 | ✅ | ⚠️ | ⚠️ | THIN_WRAPPER_ONLY | 修复 PDF URL 提取、接入成熟库 |
| M1.1 | 搜索规划 | ✅ | ✅ | ⚠️ | MOCK_TESTED：QueryPlanner 存在，中文→英文学术 query 真实验收不足 | 真实中文 query 验收 |
| M1.2 | 多源检索 | ✅ | ⚠️ | ⚠️ | THIN_WRAPPER_ONLY：arXiv/OpenAlex 自写 wrapper，Semantic Scholar/Crossref/Unpaywall 未接入 | 接入 arxiv.py / pyalex / Semantic Scholar |
| M1.3 | 论文原始材料获取 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：metadata resolution 存在，真实 PDF 获取未通过 | 真实 PDF 获取 |
| M1.4 | 去重评分 | ✅ | ✅ | ⚠️ | MOCK_TESTED：本地去重评分存在，真实候选质量未验收 | 真实候选验收 |
| M1.5 | 阅读计划 | ✅ | ✅ | ⚠️ | MOCK_TESTED：reading_plan 可生成，真实 A_READ→PDF→M2 未跑通 | 真实 e2e 跑通 |
| M2 | 单篇论文解析、精读与可信讲解 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：无真实 PDF e2e 通过 | 真实 PDF e2e 验证 |
| M2.1 | 解析 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：PyMuPDF get_text 基础解析，真实论文解析质量未验证 | 评估 Docling 接入 |
| M2.2 | 证据链路 | ✅ | ✅ | ⚠️ | MOCK_TESTED：证据链路存在，依赖真实 parser 质量，未真实验收 | 真实 PDF 验证 |
| M2.3 | 讲解生成 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：真实 LLM 有调用记录，但 synthetic markdown，不等于真实论文验收 | 修复 JSON 解析、真实 PDF 验证 |
| M2.4 | 质量审计 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：F-1 到 F-6 结构检查存在，内容正确性审计未实现 | F-7+ 内容检查 |
| M2.5 | 状态门控 | ✅ | ✅ | ⚠️ | MOCK_TESTED：状态门控存在，真实 PDF e2e 未通过 | 真实 e2e 验证 |
| M3 | 接口与前端展示 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：API/前端代码存在，无真实前后端联调 | 真实 PDF 上传 smoke |
| M3.1 | 后端 API | ✅ | ✅ | ⚠️ | MOCK_TESTED：API 端点存在，真实 PDF 上传 smoke 未通过 | 真实上传 smoke |
| M3.2 | 上传页面 | ✅ | ✅ | ❌ | MOCK_TESTED：UploadView 存在，页面级/真实上传验收缺失 | 页面级测试 |
| M3.3 | 学习工作区 | ✅ | ✅ | ❌ | MOCK_TESTED：LearningWorkspaceView 存在，页面级/真实展示验收缺失 | 页面级测试 |
| M3.4 | 状态提示 | ✅ | ✅ | ⚠️ | MOCK_TESTED：StatusBanner 7 tests，仅组件级 mock | 真实展示验收 |
| M3.5 | 调试入口 | ✅ | ✅ | ⚠️ | MOCK_TESTED：debug endpoints 存在，正式鉴权未实现 | 正式鉴权 |
| M4 | 互动式学习与长期记忆 | ✅ | ❌ | ❌ | DOC_ONLY：无代码 | M4 依赖 M2/M3 完成 |
| M4.1 | 选中内容解释 | ✅ | ❌ | ❌ | DOC_ONLY：无代码、无测试、无真实 LLM 验收 | — |
| M4.2 | 符号与公式解释 | ✅ | ❌ | ❌ | DOC_ONLY：无代码、无测试、无真实 LLM 验收 | — |
| M4.3 | 上下文追问 | ✅ | ❌ | ❌ | DOC_ONLY：无代码、无测试、无真实 LLM 验收 | — |
| M4.4 | 导师式追问与研究训练 | ✅ | ❌ | ❌ | DOC_ONLY：无代码、无测试、无真实 LLM 验收 | — |
| M4.5 | 知识库与长期记忆 | ✅ | ❌ | ❌ | DOC_ONLY：无代码、无测试、无真实 LLM 验收 | — |
| M4.6 | 记忆优先检索 | ✅ | ❌ | ❌ | DOC_ONLY：无代码、无测试、无真实 LLM 验收 | — |
| M5 | 工程可靠性与测试保障 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：快速回归存在，真实验收未通过 | secret scan + CI |
| M5.1 | 后端测试 | ✅ | ✅ | ⚠️ | MOCK_TESTED：489 tests，不代表真实产品能力 | — |
| M5.2 | 前端测试 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：7 frontend tests，仅 StatusBanner | 页面级测试 |
| M5.3 | LLM smoke / 成本 | ✅ | ⚠️ | ⚠️ | MOCK_TESTED：live eval 框架存在，real_pdf_e2e failed | 修复 M1 PDF 获取、跑通真实 e2e |
| M5.4 | 缓存 | ✅ | ✅ | ⚠️ | MOCK_TESTED：ResponseCache 基础实现，真实缓存收益未验证 | — |
| M5.5 | 安全 | ✅ | ❌ | ❌ | DOC_ONLY：secret scan 文档有，工具未接入 | 接入 gitleaks / pre-commit |
| M5.6 | Debug/admin | ⚠️ | ⚠️ | ⚠️ | MOCK_TESTED：SENSEI_DEBUG only，正式 admin 鉴权未实现 | 正式鉴权 |
| M5.7 | CI | ✅ | ❌ | ❌ | DOC_ONLY：CI 文档有，GitHub Actions 未配置 | 配置 CI |

---

## 4. 当前主要差距

- M1 PDF 获取不可用：arXiv 超时、OpenAlex 无 PDF URL，阻塞 M2 真实验证
- M2 无真实 PDF 验证：只用 synthetic markdown，parser 太弱
- M2.3 teaching_cards 真实 LLM JSON 解析失败
- M2.4 审计只查结构不查内容：F-7+ 全部未实现
- M3 无真实前后端联调
- M4 零代码
- 成熟项目零接入：arxiv.py / pyalex / Docling / Semantic Scholar 全部未接入
- 无 CI、无 secret scan

---

## 5. 下一步整改路线

按优先级排列：

1. **M1.2 修复真实多源搜索**：修复 OpenAlex pdf_url 提取、修复 arXiv 超时、接入 arxiv.py / pyalex / Semantic Scholar。验收：live eval M1 返回 ≥1 个有 pdf_url 的候选。
2. **M1.3 真实 PDF 获取**：至少一个真实 PDF 下载成功。验收：real_pdf_e2e 的 real_pdf_download=True。
3. **M2.1 真实 PDF parser 能力**：评估 Docling 接入。验收：真实论文 PDF 解析后 passage 覆盖率可接受。
4. **M2.3 修复真实 LLM JSON 解析稳定性**。验收：mimo-v2.5-pro 输出 JSON 解析成功率 100%。
5. **M2.4 补内容正确性审计 F-7+**。验收：raw-copy / generic-output / formula-heavy 检测可触发。
6. **M3 真实 PDF 上传 → 后端处理 → 前端展示 smoke**。验收：上传真实小 PDF，前端显示 StatusBanner + cards。
7. **M5 secret scan + CI**。验收：gitleaks 接入 + GitHub Actions 配置。

---

## 6. 开发与测试规则

- 后续按 M1 → M5 推进
- 每个 Mx.y 子模块都必须独立测试（unit + failure-path + schema/artifact）
- 一级模块完成后必须做集成测试
- 每次提交后必须跑全项目基础回归（pytest + frontend build + frontend test）
- M5 是全局测试与工程保障模块，不是"最后测试模块"
- 不允许跳过子模块测试进入下一个子模块
- 模块完成 = 快速回归通过 + 真实验收通过
- mock 测试只能证明代码局部逻辑没坏，不能证明产品可用

---

## 7. 当前禁止事项

- M4 当前不进入代码开发
- 不再碎片化一个小点一个 commit，除非是 bugfix
- 不新增大依赖，除非先讨论
- 不把 mock 测试通过写成模块完成
- 不把 synthetic markdown 测试写成真实论文验证
- 不把 BASELINE_ONLY 当最终导师级理解
- 不把 DEGRADED_STRUCTURAL 当完整导师级解释
- 不通过 /artifacts 给普通前端取数据

---

## 8. 测试结果

- backend pytest: 489 passed（全部 mock）
- frontend npm test: 7 passed (StatusBanner)
- frontend npm run build: 成功
- live eval: M1 passed（arXiv 超时）、M2 passed（synthetic）、real_pdf_e2e failed
- 真实验收：无任何模块通过 REAL_E2E_VERIFIED

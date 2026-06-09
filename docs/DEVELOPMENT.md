# ResearchSensei Development

---

## 0. 模块与产品能力关系

`docs/DESIGN.md` 是纲领设计文档。`docs/DEVELOPMENT.md` 是开发规范入口。M1-M5 开发文档必须服从 DESIGN。

M1-M5 是正式工程模块。产品能力可以跨模块，但不另设编号。

| 产品能力 | 主要涉及模块 |
|---------|------------|
| 方向探索 | M1, M2, M3, M4, M5 |
| 单篇论文精读 | M2, M3, M4, M5 |
| 论文搜索和获取 | M1, M3, M5 |
| Seed paper expansion | M1, M2, M3, M4, M5 |
| 互动学习 | M4, M2, M3, M5 |
| 长期记忆 | M4, M5 |

---

## 1. 通用开发规则

- 只改授权文件
- 不改旧 `backend/`
- 不改 `frontend/`，除非明确授权
- 不随意新增依赖；新增依赖必须先讨论、写清用途、通过测试
- 不提交 `.env` / key / 缓存 / 大文件 / PDF / live report
- 所有 warnings 必须是 `list[WarningItem]`，禁止 `list[str]`
- 测试必须检查 `warning.code` 和 `warning.message`
- 新模块或新 adapter 开发前必须完成复用评估；未写清候选项目、license、安装复杂度、GPU/本地模型需求、可复用 CLI/API/函数、接入方式和替代方案，不允许写业务代码。
- 第三方能力必须通过 adapter 接入，不能把 ResearchSensei 改成 ARIS / DeepXiv / MinerU / Marker / PaperQA 的 clone。
- `canonical_paper.md` 是 M1→M2 的核心工程契约。M1 负责原始材料归一化和 canonical Markdown 生成；M2.1 只读取、校验并转换 canonical Markdown，不直接绕过 M1 面对混乱原始 PDF / LaTeX / HTML。
- 不允许把某个 parser 的成功报告当作泛化成功。每次 parser 主线变更，必须做 unseen paper blind eval。
- 不允许为某篇论文写 special-case。section inference、heading detection 等逻辑必须通用。
- Llama 只能做 structure refinement，不能改公式 LaTeX / bbox / page / paper metadata。如果 Llama 越权修改这些字段，必须 BLOCKED。
- 外部 parser 接入必须通过 adapter，不能直接调用内部 API。
- heavy model / GPU / VLM 测试进入 optional/live/manual，但主契约必须设计完整。
- `.venv`、model weights、HF cache、API key 不允许提交。
- MinerU2.5-Pro (mineru-vl-utils + opendatalab/MinerU2.5-Pro-2604-1.2B) 是新主线 primary parser。当前代码中的 MinerUPdfAdapter 使用旧 magic_pdf CLI (magic_pdf.tools.common.do_parse)，两者不等价。文档和代码必须区分清楚。

### M1 v2 canonical parser invariants

- MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser.
- magic_pdf/do_parse is not an equivalent implementation.
- Marker is fallback/audit baseline.
- Ollama is an optional structured refiner.
- Ollama must not modify latex, bbox, page, or source identity.
- M1 gate blocks all-formulas-in-Abstract, section contradiction, source mismatch, and missing latex/crop/overlay.

### 测试体系

全项目测试策略：真实优先。mock/fake/skip 不是模块完成依据。缺 key、缺网络、额度不足、API 限流、PDF 下载失败不能被汇报为真实验收通过。

默认测试必须包含稳定的小样本真实链路，例如：搜索或加载一篇真实论文、生成 `canonical_paper.md`、M2 读取 canonical Markdown、生成基础 paper_card。重 OCR、GPU parser、批量 pix2tex、MinerU/Marker 全流程、DeepXiv live、大批量方向探索属于 manual / nightly / optional 运行策略，不阻塞默认快速回归。

涉及 LLM 的模块完成验收必须真实调用 LLM。涉及搜索的完成验收必须真实联网。涉及 PDF/source 的完成验收必须真实下载或读取材料。涉及前后端的完成验收必须真实 API / 真实联调。默认回归与 live/nightly 验收必须在报告中明确区分。

**模块完成 = 真实验收通过。** 不允许把 mock 测试通过写成模块完成。不允许把 skip 写成 pass。不允许缺 API key / 缺网络时仍然汇报"真实验收通过"。

---

## 2. 开发流程硬要求

- 每个一级模块和重要子模块的开发文档，都必须包含"可复用开源项目 / 外部服务调研表"。
- 没有完成这个调研表，不允许进入该模块代码开发。
- 代码实现必须对照模块文档。
- 测试和验收必须按模块执行。
- 每个模块实现前，Codex 必须先读取对应开发文档中的 `## External Projects / Adapter Candidates` 小节。
- 如果开发文档写了 `RESEARCH_REQUIRED`，Codex 不能直接实现，必须先做 research-only 调研，并明确可复用文件/函数/CLI、license、运行依赖、Windows/本地部署风险。
- 如果开发文档写了 `OPTIONAL_ADAPTER`，Codex 不能深度耦合，只能通过 adapter 接口接入，核心 schema/artifact/gate 不得依赖该工具不可替换。
- 如果开发文档写了 `STRATEGY_BORROW`，Codex 只能借鉴流程、字段、失败处理和测试方式，不能复制成 runtime dependency。
- 如果开发文档写了 `DO_NOT_USE`，Codex 不允许接入。
- 不能把 ResearchSensei 改成任何外部项目的 clone。
- 所有借鉴必须写清具体来源文件/函数/CLI，不能写空泛"参考某项目"。

---

## 3. 模块文档索引

### M1 论文搜索、获取与阅读计划

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M1.1 搜索规划 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/query/` |
| M1.2 多源检索 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/acquisition/` |
| M1.3 下载 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/source_resolver.py` |
| M1.4 材料归一化与 canonical_paper.md | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/materials/` |
| M1.5 去重评分 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/selection/` |
| M1.6 阅读计划 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/direction/` |

### M2 单篇论文解析、精读与可信讲解

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M2.1 canonical input reader / validator | [M2_1_PARSER.md](development/M2_1_PARSER.md) | `src/researchsensei/parser/`, `src/researchsensei/ingestion/` |
| M2.2 证据链路 | [M2_2_EVIDENCE.md](development/M2_2_EVIDENCE.md) | `src/researchsensei/evidence/`, `src/researchsensei/grounding.py` |
| M2.3 讲解生成 | [M2_3_PAPER_UNDERSTANDING.md](development/M2_3_PAPER_UNDERSTANDING.md) | `src/researchsensei/paper_card.py`, `*_v2.py` |
| M2.4 质量审计 | [M2_4_AUDIT_QUALITY.md](development/M2_4_AUDIT_QUALITY.md) | `src/researchsensei/audit/` |
| M2.5 状态门控 | [M2_5_FULL_PIPELINE.md](development/M2_5_FULL_PIPELINE.md), [M2_3_PAPER_UNDERSTANDING.md](development/M2_3_PAPER_UNDERSTANDING.md) | `src/researchsensei/ingestion/pipeline.py` |

### M3 接口与前端展示

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M3.1 后端 API | [M3_FRONTEND_RENDER.md](development/M3_FRONTEND_RENDER.md) | `src/researchsensei/web/` |
| M3.2 上传页面 | [M3_FRONTEND_RENDER.md](development/M3_FRONTEND_RENDER.md) | `frontend/src/views/UploadView.vue` |
| M3.3 学习工作区 | [M3_FRONTEND_RENDER.md](development/M3_FRONTEND_RENDER.md) | `frontend/src/views/LearningWorkspaceView.vue` |
| M3.4 状态提示 | [M3_FRONTEND_RENDER.md](development/M3_FRONTEND_RENDER.md) | `frontend/src/components/StatusBanner.vue` |
| M3.5 调试入口 | [M3_FRONTEND_RENDER.md](development/M3_FRONTEND_RENDER.md) | `src/researchsensei/web/app.py` |

### M4 互动式学习与长期记忆

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M4.1 选中内容解释 | [M4_INTERACTIVE_LEARNING.md](development/M4_INTERACTIVE_LEARNING.md) | 未实现 |
| M4.2 符号与公式解释 | [M4_INTERACTIVE_LEARNING.md](development/M4_INTERACTIVE_LEARNING.md) | 未实现 |
| M4.3 上下文追问 | [M4_INTERACTIVE_LEARNING.md](development/M4_INTERACTIVE_LEARNING.md) | 未实现 |
| M4.4 导师式追问与研究训练 | [M4_INTERACTIVE_LEARNING.md](development/M4_INTERACTIVE_LEARNING.md) | 未实现 |
| M4.5 知识库与长期记忆 | [M4_INTERACTIVE_LEARNING.md](development/M4_INTERACTIVE_LEARNING.md) | 未实现 |
| M4.6 记忆优先检索 | [M4_INTERACTIVE_LEARNING.md](development/M4_INTERACTIVE_LEARNING.md) | 未实现 |

### M5 工程可靠性与测试保障

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M5.1 后端测试 | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | `tests/` |
| M5.2 前端测试 | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | `frontend/src/components/tests/` |
| M5.3 LLM smoke / 成本 | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | 未实现 |
| M5.4 缓存 | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | `src/researchsensei/llm/response_cache.py` |
| M5.5 安全 | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | 未实现 |
| M5.6 Debug/admin | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | 未实现 |
| M5.7 CI | [M5_ENGINEERING_RELIABILITY.md](development/M5_ENGINEERING_RELIABILITY.md) | 未实现 |

---

## 4. 测试粒度规则

测试必须分三层，不允许"先写完所有代码，最后再统一测试"。

### 第一层：子模块测试 Mx.y

每个 Mx.y 子模块都必须有自己的测试设计、测试用例和验收标准。

开发顺序必须是：

子模块文档 → 子模块代码 → 子模块单元测试 → 子模块失败路径测试 → 子模块验收 → 再进入下一个子模块

每个子模块必须有：
- schema/artifact round-trip tests
- 真实验收测试（涉及外部服务 / LLM / PDF 的模块必须有）
- API tests（如果涉及 API）
- Vitest tests（如果涉及 frontend，必须真实后端联调）

每个子模块完成后必须跑：
- 快速回归：`python -m pytest -q`
- 真实验收：`RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1 python scripts/run_live_eval.py`
- 公式链路默认小样本真实测试：1 篇真实论文、1 个真实公式区域、真实 formula detection output (MarkerDocumentFormulaDetector or MinerU25ProAdapter)、`canonical_paper.md` 写入、M2 读取该 formula block。FormulaOCRAdapter 仅在 unresolved formula crops 时作为 fallback 触发。
- 公式链路重测试：多论文、多公式批量 OCR、GPU parser、MinerU/Marker 全流程、pix2tex 批量识别，标记为 manual / nightly / optional。

### 第二层：一级模块集成测试

每个一级模块 M1-M5 完成时，需要做一级模块集成测试，验证子模块之间的 artifact 流转和状态传递。

### 第三层：全项目回归测试

每次完成一个子模块或一级模块后，都必须跑全项目基础回归：

```
python -m pytest -q
cd frontend && npm run build && npm test
```

### 禁止事项

- 不允许先写完一整个大模块，最后再测
- 不允许先写完所有代码，最后再统一测试
- 不允许跳过子模块测试进入下一个子模块
- M5 不替代 M1-M4 的业务模块测试

---

## 5. 模块文档统一模板

每个模块文档必须包含：

1. 模块目标
2. 非目标
3. `External Projects / Adapter Candidates`
4. 当前代码位置
5. 输入输出
6. artifact
7. 核心类和方法签名
8. 错误/失败策略
9. 测试断言
10. hard-fail
11. 当前未解决问题
12. 当前实现状态，必须区分 IMPLEMENTED、DOC_DESIGNED、NOT_IMPLEMENTED

### External Projects / Adapter Candidates 模板

每个 M1-M5 开发文档必须包含同名小节，并使用此固定表头：

| 项目 | 对应模块 | 具体能力 | 可复用文件/函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状态 |
|---|---|---|---|---|---|---|---|
| — | — | — | — | DIRECT_DEPENDENCY / OPTIONAL_ADAPTER / STRATEGY_BORROW / DO_NOT_USE | — | — | IMPLEMENTED / DOC_DESIGNED / RESEARCH_REQUIRED / NOT_IMPLEMENTED |

`接入方式` 只能使用：
- `DIRECT_DEPENDENCY`
- `OPTIONAL_ADAPTER`
- `STRATEGY_BORROW`
- `DO_NOT_USE`

`当前状态` 只能使用：
- `IMPLEMENTED`
- `DOC_DESIGNED`
- `RESEARCH_REQUIRED`
- `NOT_IMPLEMENTED`

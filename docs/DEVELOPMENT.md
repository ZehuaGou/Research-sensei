# ResearchSensei Development

---

## 1. 通用开发规则

- 只改授权文件
- 不改旧 `backend/`
- 不改 `frontend/`，除非明确授权
- 不随意新增依赖；新增依赖必须先讨论、写清用途、通过测试
- 默认 pytest 不联网，不真实 LLM
- HTTP 测试用 `httpx.MockTransport`
- LLM 测试用 `MockLLMClient`
- 不提交 `.env` / key / 缓存 / 大文件
- 所有 warnings 必须是 `list[WarningItem]`，禁止 `list[str]`
- 测试必须检查 `warning.code` 和 `warning.message`

---

## 2. 开发流程硬要求

- 每个一级模块和重要子模块的开发文档，都必须包含"可复用开源项目 / 外部服务调研表"。
- 没有完成这个调研表，不允许进入该模块代码开发。
- 代码实现必须对照模块文档。
- 测试和验收必须按模块执行。

---

## 3. 模块文档索引

### M1 论文搜索、获取与阅读计划

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M1.1 搜索规划 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/query/` |
| M1.2 多源检索 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/acquisition/` |
| M1.3 下载 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/source_resolver.py` |
| M1.4 去重评分 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/selection/` |
| M1.5 阅读计划 | [M1_LITERATURE_SEARCH.md](development/M1_LITERATURE_SEARCH.md) | `src/researchsensei/direction/` |

### M2 单篇论文解析、精读与可信讲解

| 子模块 | 开发文档 | 代码位置 |
|--------|---------|---------|
| M2.1 解析 | [M2_1_PARSER.md](development/M2_1_PARSER.md) | `src/researchsensei/parser/`, `src/researchsensei/ingestion/` |
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
- unit tests
- failure-path tests
- schema/artifact round-trip tests（如果涉及）
- API tests（如果涉及 API）
- Vitest tests（如果涉及 frontend）
- LLM 子模块默认用 fake/mock client，不真实调用
- 外部服务子模块默认用 mock transport

每个子模块完成后必须跑基础回归：`python -m pytest -q`

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
3. 可复用开源项目 / 外部服务调研表
4. 当前代码位置
5. 输入输出
6. artifact
7. 核心类和方法签名
8. 错误/失败策略
9. 测试断言
10. hard-fail
11. 当前未解决问题

### 可复用开源项目 / 外部服务调研表模板

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| — | — | — | — | — | — | — |

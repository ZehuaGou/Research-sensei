# ResearchSensei Development

---

## 1. 通用开发规则

- 只改授权文件
- 不改旧 `backend/`
- 不改 `frontend/`，除非明确授权
- 不随意新增依赖；新增依赖必须先讨论、写清用途、通过测试；当前已新增前端测试依赖：Vitest / Vue Test Utils / jsdom
- 默认 pytest 不联网，不真实 LLM
- HTTP 测试用 `httpx.MockTransport`
- LLM 测试用 `MockLLMClient`
- 不提交 `.env` / key / 缓存 / 大文件
- 不写 Claude 贡献者信息
- 所有 warnings 必须是 `list[WarningItem]`，禁止 `list[str]`
- 测试必须检查 `warning.code` 和 `warning.message`

---

## 2. 模块文档索引

| 文档 | 内容 |
|------|------|
| [development/PARSER.md](development/PARSER.md) | ParserAdapter / LightweightParser / 外部 parser 调研 |
| [development/EVIDENCE.md](development/EVIDENCE.md) | PassageIndex / ClaimEvidence / ClaimExtractor / EvidenceRetriever |
| [development/PAPER_UNDERSTANDING.md](development/PAPER_UNDERSTANDING.md) | EvidencePack / understanding_status / fail-closed / LLM 校验 |
| [development/LITERATURE_SEARCH.md](development/LITERATURE_SEARCH.md) | QueryPlanner / adapters / SelectionService / DirectionRunner |
| [development/AUDIT_QUALITY.md](development/AUDIT_QUALITY.md) | QualityReport / hard-fail / 检测算法 / 外部 audit 调研 |
| Workspace / JobStore | 归属 Pipeline / Engineering Reliability 模块，详见 FULL_PIPELINE.md 和 ENGINEERING_RELIABILITY.md |
| [development/FRONTEND_RENDER.md](development/FRONTEND_RENDER.md) | Vue 前端约束 / artifact 展示规则 / 非 SUCCESS 不展示 |
| [development/ENGINEERING_RELIABILITY.md](development/ENGINEERING_RELIABILITY.md) | 测试规范 / cache / artifact versioning / security |
| [development/FULL_PIPELINE.md](development/FULL_PIPELINE.md) | 单篇链路 / 方向链路 / 状态传递 / 失败规则 |

---

## 3. 模块文档固定结构

每个模块文档必须包含：

1. 模块目标
2. 非目标
3. 外部项目调研
4. 当前代码位置
5. 输入输出
6. artifact
7. 核心类和方法签名
8. 错误/失败策略
9. 测试断言
10. hard-fail
11. 当前未解决问题

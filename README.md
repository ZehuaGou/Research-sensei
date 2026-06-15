# ResearchSensei / 研读导师 / 读博模拟器

多能力科研学习与训练系统。帮助用户建立研究方向框架、搜索和筛选论文、可信精读单篇论文、理解公式和方法机制、形成学习卡片、比较多篇论文关系、接受导师式追问训练，并沉淀长期记忆。正式模块为 M1-M5。

## 核心设计文档

- [docs/DESIGN.md](docs/DESIGN.md) — 纲领设计文档、产品定位、三个入口、M1-M5 职责、artifact 链路
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 开发规范总入口
- [docs/STATUS.md](docs/STATUS.md) — 模块总控表与当前进度

## 模块开发文档

### M1 — Literature Search, Direction Exploration, And Seed Expansion

- [docs/development/M1_LITERATURE_SEARCH.md](docs/development/M1_LITERATURE_SEARCH.md) — 搜索规划、多源检索、去重评分、阅读计划、方向框架、seed expansion

### M2 — Single Paper Deep Reading & Survey Deep Reading

- [docs/development/M2_1_PARSER.md](docs/development/M2_1_PARSER.md) — M2.1 文档解析
- [docs/development/M2_2_EVIDENCE.md](docs/development/M2_2_EVIDENCE.md) — M2.2 证据链路
- [docs/development/M2_3_PAPER_UNDERSTANDING.md](docs/development/M2_3_PAPER_UNDERSTANDING.md) — M2.3 讲解生成
- [docs/development/M2_4_AUDIT_QUALITY.md](docs/development/M2_4_AUDIT_QUALITY.md) — M2.4 质量审计
- [docs/development/M2_5_FULL_PIPELINE.md](docs/development/M2_5_FULL_PIPELINE.md) — M2.5 单篇/方向链路编排

### M3 — API / Frontend (DirectionWorkspace, PaperWorkspace, SeedExpansionPanel)

- [docs/development/M3_FRONTEND_RENDER.md](docs/development/M3_FRONTEND_RENDER.md) — 前端渲染、状态展示、API 规则

### M4 — Interactive Learning & Long-term Memory

- [docs/development/M4_INTERACTIVE_LEARNING.md](docs/development/M4_INTERACTIVE_LEARNING.md) — 选中内容解释、符号与公式解释、导师式追问、研究训练、论文知识库、长期记忆

### M5 — Engineering Reliability

- [docs/development/M5_ENGINEERING_RELIABILITY.md](docs/development/M5_ENGINEERING_RELIABILITY.md) — 真实测试、CI、安全、密钥、成本、工程可靠性

## 辅助文档

- [docs/GLOSSARY.md](docs/GLOSSARY.md) — 术语表
- [docs/MODULE_CONTRACTS.md](docs/MODULE_CONTRACTS.md) — 模块输入输出契约
- [docs/REUSE_REPORT.md](docs/REUSE_REPORT.md) — 外部项目复用决策
- [docs/REVIEW_CHECKLIST.md](docs/REVIEW_CHECKLIST.md) — 提交/验收检查清单

## 历史归档

- [docs/TECHNICAL_DISCUSSION.md](docs/TECHNICAL_DISCUSSION.md) — 历史技术讨论，不作为当前开发依据
- [docs/MAIN_CHAIN_V1_REVIEW.md](docs/MAIN_CHAIN_V1_REVIEW.md) — 历史封版记录（归档）

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

## 测试

```bash
python -m pytest -q
```

当前验收策略：真实优先。涉及 LLM / 搜索 / PDF / 前后端联调的模块，验收必须跑真实链路。mock/fake/skip 不作为模块完成依据。

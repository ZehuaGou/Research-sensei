# ResearchSensei / 研读导师

科研论文理解与思维框架训练系统。帮助用户真正读懂论文、理解公式、形成科研思维、回答导师追问。

## 核心设计文档

- [docs/DESIGN.md](docs/DESIGN.md) — 产品设计、用户流程、artifact 链路
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 开发规范总入口
- [docs/STATUS.md](docs/STATUS.md) — 模块总控表与当前进度

## 模块开发文档

### M1 — Literature Search

- [docs/development/M1_LITERATURE_SEARCH.md](docs/development/M1_LITERATURE_SEARCH.md) — 搜索规划、多源检索、去重评分、阅读计划

### M2 — Single Paper Understanding

- [docs/development/M2_1_PARSER.md](docs/development/M2_1_PARSER.md) — M2.1 文档解析
- [docs/development/M2_2_EVIDENCE.md](docs/development/M2_2_EVIDENCE.md) — M2.2 证据链路
- [docs/development/M2_3_PAPER_UNDERSTANDING.md](docs/development/M2_3_PAPER_UNDERSTANDING.md) — M2.3 讲解生成
- [docs/development/M2_4_AUDIT_QUALITY.md](docs/development/M2_4_AUDIT_QUALITY.md) — M2.4 质量审计
- [docs/development/M2_5_FULL_PIPELINE.md](docs/development/M2_5_FULL_PIPELINE.md) — M2.5 单篇/方向链路编排

### M3 — API / Frontend

- [docs/development/M3_FRONTEND_RENDER.md](docs/development/M3_FRONTEND_RENDER.md) — 前端渲染、状态展示、API 规则

### M4 — Interactive Learning

- [docs/development/M4_INTERACTIVE_LEARNING.md](docs/development/M4_INTERACTIVE_LEARNING.md) — 选中内容解释、符号与公式解释、导师式追问、研究训练、论文知识库、长期记忆、memory-first retrieval、token 节省

### M5 — Engineering Reliability

- [docs/development/M5_ENGINEERING_RELIABILITY.md](docs/development/M5_ENGINEERING_RELIABILITY.md) — artifact versioning、缓存、CI、安全、debug API

## 辅助文档

- [docs/GLOSSARY.md](docs/GLOSSARY.md) — 术语表
- [docs/MODULE_CONTRACTS.md](docs/MODULE_CONTRACTS.md) — 模块输入输出边界
- [docs/REUSE_REPORT.md](docs/REUSE_REPORT.md) — 外部项目复用决策
- [docs/REVIEW_CHECKLIST.md](docs/REVIEW_CHECKLIST.md) — 提交/验收检查清单

## 历史归档

- [docs/TECHNICAL_DISCUSSION.md](docs/TECHNICAL_DISCUSSION.md) — 历史技术讨论，不作为当前开发依据
- [docs/MAIN_CHAIN_V1_REVIEW.md](docs/MAIN_CHAIN_V1_REVIEW.md) — 主链路 v1 封版记录

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

默认测试不联网、不调 LLM。

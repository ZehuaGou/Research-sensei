# ResearchSensei / 研读导师

科研论文理解与思维框架训练系统。帮助用户真正读懂论文、理解公式、形成科研思维、回答导师追问。

## 文档

- [docs/DESIGN.md](docs/DESIGN.md) — 项目设计
- [docs/STATUS.md](docs/STATUS.md) — 当前进度
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 开发规范总入口
- [docs/development/PARSER.md](docs/development/PARSER.md) — Parser 模块
- [docs/development/EVIDENCE.md](docs/development/EVIDENCE.md) — Evidence 模块
- [docs/development/PAPER_UNDERSTANDING.md](docs/development/PAPER_UNDERSTANDING.md) — Paper Understanding 模块
- [docs/development/LITERATURE_SEARCH.md](docs/development/LITERATURE_SEARCH.md) — Literature Search 模块
- [docs/development/AUDIT_QUALITY.md](docs/development/AUDIT_QUALITY.md) — Audit / Quality 模块

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

# ResearchSensei / 研读导师

科研论文理解与思维框架训练系统。帮助用户真正读懂论文、理解公式、形成科研思维、回答导师追问。

## 文档

- [docs/DESIGN.md](docs/DESIGN.md) — 项目设计
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — 开发规范
- [docs/STATUS.md](docs/STATUS.md) — 当前进度

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

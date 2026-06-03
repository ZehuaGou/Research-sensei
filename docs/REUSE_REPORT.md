# ResearchSensei Reuse Report

> **Canonical docs**: See `docs/DESIGN.md` and `docs/DEVELOPMENT.md`.

Last updated: 2026-06-03

## Global Rule

ResearchSensei must not reimplement mature infrastructure when a reliable open-source project, official API, or reusable library can be wrapped through an adapter. All third-party tools must remain replaceable.

## External Project Decisions

| Project | Decision | Reason |
|---------|----------|--------|
| ARIS | REFERENCE_ONLY | 参考 audit chain / reviewer independence, 不整包接入 |
| PaperQA | OPTIONAL_ADAPTER | 参考 passage retrieval / citation-backed answer |
| OpenScholar | REFERENCE_ONLY | 参考 citation accuracy |
| ResearchPilot | REFERENCE_ONLY | 参考 structured findings |
| STORM | REFERENCE_ONLY | 参考 outline / multi-perspective questioning |
| Docling | OPTIONAL_ADAPTER | 可选 parser adapter |
| Nougat | OPTIONAL_ADAPTER | 可选 parser adapter |
| Marker | OPTIONAL_ADAPTER | 可选 parser adapter |
| MinerU | OPTIONAL_ADAPTER | 可选 parser adapter |
| Unstructured | NOT_USE | 通用不够学术 |
| GROBID | OPTIONAL_ADAPTER | 可选 PDF 解析 |
| GPT-Researcher | NOT_USE | 不适合教学场景 |
| PaperQA2 | OPTIONAL_ADAPTER | 参考 passage retrieval |
| paper-search-mcp | OPTIONAL_ADAPTER | 可选搜索 adapter |

## Decision Categories

- **DIRECT_DEPENDENCY**: Install as project dependency
- **DIRECT_ADAPTER**: Wrap as adapter, default available
- **OPTIONAL_ADAPTER**: Wrap as adapter, user must install
- **REFERENCE_ONLY**: Learn from design, do not import code
- **NOT_USE**: Explicitly not used

## Current Dependencies

fastapi, httpx, httpx-sse, jinja2, pymupdf, python-multipart, python-dotenv, pydantic, uvicorn, aiosqlite (declared but unused).

## Replacement Policy

Every adapter must accept httpx.Client via dependency injection for testing. Every LLM call must go through llm/client.py. Default pytest must not use real network or real LLM.

所有第三方工具必须保持可替换，不允许把核心流程锁死在单个不可控依赖上。

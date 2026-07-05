# ResearchSensei Reuse Report

> **Canonical docs**: See `docs/DESIGN.md`, `docs/DEVELOPMENT.md`, `docs/development/`.

Last updated: 2026-07-05

## Global Rule

ResearchSensei must not reimplement mature infrastructure when a reliable open-source project, official API, or reusable library can be wrapped through an adapter. All third-party tools must remain replaceable.

## External Project Decisions

| Project | Decision | Reason |
|---------|----------|--------|
| ARIS | REFERENCE_ONLY | 鍙傝€?audit chain / reviewer independence, 涓嶆暣鍖呮帴鍏?|
| PaperQA | OPTIONAL_ADAPTER | 鍙傝€?passage retrieval / citation-backed answer |
| OpenScholar | REFERENCE_ONLY | 鍙傝€?citation accuracy |
| ResearchPilot | REFERENCE_ONLY | 鍙傝€?structured findings |
| STORM | REFERENCE_ONLY | 鍙傝€?outline / multi-perspective questioning |
| Docling | OPTIONAL_ADAPTER | 鍙€?parser adapter |
| Nougat | OPTIONAL_ADAPTER | 鍙€?parser adapter |
| Marker | OPTIONAL_ADAPTER | 鍙€?parser adapter |
| MinerU | OPTIONAL_ADAPTER | 鍙€?parser adapter |
| Unstructured | NOT_USE | 閫氱敤涓嶅瀛︽湳 |
| GROBID | OPTIONAL_ADAPTER | 鍙€?PDF 瑙ｆ瀽 |
| GPT-Researcher | NOT_USE | 涓嶉€傚悎鏁欏鍦烘櫙 |
| PaperQA2 | OPTIONAL_ADAPTER | 鍙傝€?passage retrieval |
| paper-search-mcp | DIRECT_DEPENDENCY | Default M1 multi-source paper discovery dependency, wrapped by `PaperSearchMcpAdapter` |
| flashrank | DIRECT_DEPENDENCY | Default M1 local semantic reranker for paper-candidate download queue selection |
| Google-Scholar-MCP-Server | NOT_USE | Replaced by PaperSearch MCP; direct Scholar scraping was blocked/CAPTCHA-prone and is no longer a ResearchSensei default |

## Decision Categories

- **DIRECT_DEPENDENCY**: Install as project dependency
- **DIRECT_ADAPTER**: Wrap as adapter, default available
- **OPTIONAL_ADAPTER**: Wrap as adapter, user must install
- **REFERENCE_ONLY**: Learn from design, do not import code
- **NOT_USE**: Explicitly not used

## Current Dependencies

fastapi, httpx, httpx-sse, jinja2, pymupdf, python-multipart, python-dotenv, pydantic, uvicorn, paper-search-mcp, flashrank, aiosqlite (declared but unused).

## Replacement Policy

Every adapter must accept httpx.Client via dependency injection for testing. Every LLM call must go through llm/client.py. Default pytest must not use real network or real LLM.

鎵€鏈夌涓夋柟宸ュ叿蹇呴』淇濇寔鍙浛鎹紝涓嶅厑璁告妸鏍稿績娴佺▼閿佹鍦ㄥ崟涓笉鍙帶渚濊禆涓娿€?

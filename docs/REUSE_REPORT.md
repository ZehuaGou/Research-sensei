# ResearchSensei Reuse Report

This report records where ResearchSensei reuses external tools and where it
keeps a project-owned contract. External systems are replaceable adapters, not
the authority for source identity, evidence, quality status, or user-facing
cards.

## Decision Labels

- `OPTIONAL_ADAPTER`: useful behind a stable ResearchSensei interface and safe
  to replace when maintenance, availability, or licensing changes.
- `REFERENCE_ONLY`: consulted for architecture or workflow ideas but not a
  runtime dependency.
- `PROJECT_OWNED`: schemas, gates, provenance, and product behavior maintained
  in this repository.

## Tool Assessment

| Tool | Decision | Maintained boundary |
|---|---|---|
| paper-search-mcp | `OPTIONAL_ADAPTER` | Broad metadata discovery. ResearchSensei owns normalization, deterministic relevance, legal full-text resolution, source status, and selection gates. |
| OpenCode Server | `OPTIONAL_ADAPTER` | Local attachment/session control plane. ResearchSensei owns run state, evidence and failure semantics. |
| OpenCode Go | `OPTIONAL_ADAPTER` | Model provider for page vision and tutoring. Vision and tutor models are configured independently. |
| PyMuPDF | `OPTIONAL_ADAPTER` | Deterministic PDF validation, page text and rendering; it does not invent semantic claims. |
| FlashRank | `OPTIONAL_ADAPTER` | Candidate reranking signal. Deterministic task/concept relevance gates remain authoritative. |
| ccswitch | `OPTIONAL_ADAPTER` | Compatibility route only. Direct OpenCode Go does not require it. |

## Project-Owned Contracts

ResearchSensei keeps the following surfaces independent of any single external
tool:

- candidate, source-resolution, evidence, card, and status schemas;
- deterministic relevance coverage and intent-mismatch penalties;
- legal/OA full-text verification and `pdf_ready` download confirmation;
- QualityAuditor, FSA-5, `source_latex`, and `/cards` gates;
- claim-level evidence binding, formula provenance and source-only lookup;
- local job, paper-library, and bounded Paper Tutor-memory persistence;
- typed Chinese PaperWorkspace behavior.

## 替换原则

任何 `OPTIONAL_ADAPTER` 都必须可以在不改变上述项目自有契约的前提下替换。
替换搜索、解析、排序或 LLM 提供方时，先增加契约测试，再切换依赖注入；不得把
外部工具的临时字段直接升级为 ResearchSensei 的来源、证据或成功状态。

## Verification Boundary

Offline fixtures verify deterministic behavior and failure handling. They do
not prove current network access, provider credentials, publisher availability,
or live LLM quality. Live checks remain opt-in and must be recorded as
`NOT_LIVE_VERIFIED` when unavailable.

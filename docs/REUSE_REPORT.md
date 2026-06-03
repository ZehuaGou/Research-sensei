# ResearchSensei Reuse Report

Last updated: 2026-06-02

## Global Rule: No Rebuilding Mature Wheels

ResearchSensei must not reimplement mature infrastructure when a reliable open-source project, official API, or reusable library can be wrapped through an adapter.

中文规则摘要：所有第三方工具都必须保持可替换，不允许把核心流程锁死在单个不可控依赖上。

Before starting any new major Phase, the agent must:

1. Read the governing documents listed in the current project instructions.
2. Identify the Phase problem and module boundary.
3. Search or verify mature projects, official APIs, and reusable libraries for that Phase.
4. Evaluate each candidate using the full checklist in this report.
5. Update this `docs/REUSE_REPORT.md`.
6. Only then decide whether code development may continue.

If this report is not updated for the new Phase, business code for that Phase is not authorized.

## Non-Negotiable Reuse Boundaries

ResearchSensei does not self-build mature external infrastructure:

- paper search, multi-source aggregation, PDF download, DOI backfill, deduplication;
- PDF parsing, paper section extraction, formula rendering, citation parsing;
- generic RAG, vector retrieval, evidence-style QA;
- workflow orchestration, chart rendering, template engines;
- spaced repetition algorithms;
- LLM/RAG evaluation frameworks.

ResearchSensei may self-build the parts that are specific to this product:

- Teach-Me Engine;
- Formula Tutor;
- Research Pattern Library;
- PhD Thinking Scaffold;
- Learning Card Schema;
- Direction Curator Rules;
- Chinese-first learning card organization;
- contextual advisor behavior when no mature project satisfies the teaching requirement.

Even for these self-built areas, existing projects must be checked first and recorded here.

## Required Phase Start Output

At the start of every major Phase, before writing business code, the agent must output:

1. Problem solved by this Phase.
2. Open-source projects or APIs searched/evaluated.
3. Which tools will be reused.
4. Which tools are reference-only.
5. Which tools are not used and why.
6. Whether new dependencies are needed.
7. Whether adapters are needed.
8. Whether code development may continue.

## Candidate Evaluation Checklist

Every evaluated candidate must include:

| Field | Requirement |
|---|---|
| Problem solved | What capability the tool/API provides |
| Use decision | `DIRECT_DEPENDENCY` / `OPTIONAL_ADAPTER` / `REFERENCE_ONLY` / `NOT_USE` |
| License | SPDX or project-stated license; unknown license blocks adoption |
| GitHub stars/activity | Must be verified online when selecting a new dependency |
| Recent commits | Must be verified online when selecting a new dependency |
| Issues status | Must be checked for severe unresolved maintenance/security issues |
| Install complexity | Simple pip/npm/uvx, Docker, Java service, GPU model download, etc. |
| Windows support | Required for this local Windows-first project unless optional |
| Local deployment | Whether it works without a managed cloud backend |
| GPU need | Must be explicit |
| Paid API need | Must be explicit |
| Chinese suitability | Good / partial / poor / irrelevant |
| Replaceability | Easy / medium / hard; hard requires stronger justification |
| Safety | File/network/prompt/security considerations |
| Reuse risk | Maintenance, license, API changes, lock-in, flaky output |
| Alternatives | At least one substitute when possible |
| Final decision for this Phase | Adopt / defer / reject |

Dynamic fields such as stars, recent commits, and issue status must be freshly verified with web/GitHub lookup for the Phase being started. If verification is blocked by rate limit or network failure, mark the candidate as `UNVERIFIED` and do not introduce it as a hard dependency.

## Adapter Rule

Third-party tools must be integrated through a narrow adapter boundary.

Not allowed:

- importing third-party APIs deeply throughout product logic;
- making core flow unrecoverable if one vendor/tool fails;
- adding dependencies without recording license and installation notes;
- adding real network tests to default pytest.

Allowed:

- optional adapters with structured outputs;
- mocked adapter tests;
- graceful degraded states;
- replacing one adapter with another without changing core schemas.

## Phase-Specific Reuse Targets

### Query / Acquisition

Candidates to evaluate before any new work:

- GPT-Researcher;
- paper-search-mcp;
- arXiv API;
- Semantic Scholar API;
- OpenAlex API;
- Crossref API;
- Papers With Code;
- Google Scholar MCP;
- GitHub Search.

Decision rule:

- Search/acquisition only outputs metadata, sources, and candidate pools.
- It must not generate teaching cards.
- It must not download every result by default.
- It must not self-build a crawler when existing adapters can do the job.

### Source Resolver

Candidates to evaluate before new resolver expansion:

- arXiv API / arXiv deterministic PDF/source URLs;
- httpx or requests for safe HTTP client behavior;
- platform-safe path handling from Python standard library;
- optional download safety helpers if needed.

Decision rule:

- Source resolver only obtains material and writes `source_status.json`.
- It does not parse the document.
- It does not search papers.
- Network tests must use mocks.

Current Phase 5 decision:

| Candidate | Problem solved | Use decision | License | Stars/activity | Recent commits | Issues status | Install complexity | Windows | Local | GPU | Paid API | Chinese | Replaceability | Safety | Risk | Alternatives | Final decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Python `pathlib` / `shutil` | Local file path resolution and copying | DIRECT_DEPENDENCY | Python standard library | N/A | N/A | N/A | built-in | yes | yes | no | no | irrelevant | easy | must guard traversal | path mistakes can leak files | OS APIs | Adopted |
| httpx | HTTP PDF download with timeout and mockable transport | DIRECT_DEPENDENCY | BSD-3-Clause, already project dependency | UNVERIFIED for this update | UNVERIFIED | UNVERIFIED | pip dependency already present | yes | yes | no | no | irrelevant | medium | enforce scheme, size, type checks | API changes; download misuse | requests, aiohttp | Adopted |
| arXiv deterministic PDF URL | Convert arXiv ID/URL to PDF URL | OPTIONAL_ADAPTER | arXiv service terms, not a code dependency | N/A | N/A | N/A | no package | yes | yes | no | no | irrelevant | easy | validate ID and mock downloads | URL patterns can change | arXiv API package | Adopted minimal deterministic adapter |
| arXiv API package | Metadata/source lookup | OPTIONAL_ADAPTER | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | pip package likely simple | likely | yes | no | no | irrelevant | easy | network API, rate limits | unnecessary for Phase 5 minimal resolver | httpx direct endpoint | Defer |
| aria2 / wget-like downloaders | Robust large-file download | NOT_USE | varies | UNVERIFIED | UNVERIFIED | UNVERIFIED | extra binary | uncertain | yes | no | no | irrelevant | medium | external binary risks | too heavy for Phase 5 | httpx | Not used |

### Ingestion

Candidates to evaluate before expanding parsing:

- PyMuPDF;
- Docling;
- Marker;
- MinerU;
- GROBID;
- Nougat;
- LaTeX source parser.

Decision rule:

- ResearchSensei may keep PyMuPDF as a lightweight fallback.
- Structured PDF parsing should prefer Docling/Marker/MinerU/GROBID adapters.
- OCR/GPU-heavy tools must be optional.
- Parser failures must produce warnings/degraded states, not fabricated content.

### Grounding / RAG

Candidates to evaluate before Phase 6 or any grounding expansion:

- PaperQA / PaperQA2;
- LlamaIndex;
- LangChain;
- Chroma;
- Qdrant;
- sentence-transformers;
- BGE embeddings.

Decision rule:

- Grounding only produces evidence and evidence status.
- It does not produce teaching text.
- It must preserve evidence references and degraded states.
- If using embeddings/RAG, all network/model calls must be mockable in default tests.

## Phase 6 Reuse Evaluation - Grounding And Paper Skeleton

Verification date: 2026-06-02.

Scope note: this is the migration Phase 6 requested for the current backend rewrite: grounding/evidence base plus `paper_skeleton` base. It maps to the full development document's grounding/skeleton scope, not the later learning-card generation scope. This phase must not enter teaching, formula tutoring, direction maps, drill, advisor, or real LLM calls.

Problem solved:

- Convert existing `DocumentIngestion.blocks` into a stable `EvidenceIndex`.
- Preserve section-level, paragraph-level, and formula-nearby evidence references.
- Build a first `PaperSkeleton` with evidence status and degradation flags.
- Mark unsupported or missing claims as `INSUFFICIENT_EVIDENCE` or equivalent degraded status.
- Keep default tests deterministic and offline.

Candidates checked:

| Candidate | GitHub / official | Problem solved | Use decision | License | Stars/activity | Recent commits | Issues status | Install complexity | Windows | Local | GPU | Paid API | Chinese | Replaceability | Safety | Risk | Alternatives | Final decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PaperQA / PaperQA2 | [Future-House/paper-qa](https://github.com/Future-House/paper-qa) | Scientific-paper RAG, evidence gathering, cited answers, metadata/retraction-aware workflows | REFERENCE_ONLY now; OPTIONAL_ADAPTER later | Apache-2.0 | 8.6k stars; active scientific RAG project | Recent commits observed Mar 20, 2026 | 132 open issues | `pip install paper-qa>=5`; Python 3.11+; heavier RAG stack | likely yes, but dependency stack must be tested | yes with local models; defaults can use hosted models | optional for local embeddings/LLM | optional; default OpenAI/LiteLLM config may require keys | partial; supports non-English per README, but Chinese quality depends on model/embedding | medium | Parses user files and sends prompts to LLM if enabled; adapter must isolate inputs and citations | Too broad for current no-LLM skeleton phase; can take over answer generation if integrated too deeply | LlamaIndex, LangChain, custom adapter over existing evidence index | Do not add dependency in Phase 6. Use as reference for cited evidence and consider later `PaperEvidenceQAAdapter`. |
| LlamaIndex | [run-llama/llama_index](https://github.com/run-llama/llama_index) / [docs](https://developers.llamaindex.ai/) | RAG framework, indexing, document agents, integrations, optional LlamaParse | REFERENCE_ONLY now; OPTIONAL_ADAPTER later | MIT | 49.8k stars; very active | Recent commits observed May 29, 2026 | 178 open issues | modular but can grow quickly; many integrations | yes in normal Python use | yes for OSS core; LlamaParse is external service | no for core; depends on chosen models | optional depending on parser/model/provider | partial; depends on embeddings/models | medium | RAG pipelines can hide evidence scoring and prompt behavior if not adapter-bound | Framework sprawl; unnecessary for deterministic evidence index | PaperQA, LangChain, Chroma/Qdrant plus custom core | Defer. Useful later for RAG/context/query engines, not for Phase 6 rule evidence. |
| LangChain | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) / [docs](https://docs.langchain.com/) | Agent and LLM application framework, integrations, orchestration helpers | REFERENCE_ONLY | MIT | 138k stars; very active | Recent commits observed Jun 1, 2026 | 438 open issues; GitHub shows 8 security/quality signals | simple install, but broad dependency surface | yes in normal Python use | yes for OSS packages | no for framework; depends on chosen models | optional depending on provider | partial; depends on model/embedding | medium | Prompt/tool integrations must not leak keys or raw papers | Too broad; could reintroduce architecture coupling | LlamaIndex, PaperQA, direct small adapters | Do not introduce in Phase 6. Reference only for future adapter patterns. |
| Chroma | [chroma-core/chroma](https://github.com/chroma-core/chroma) / [docs](https://docs.trychroma.com/) | Local/in-process or client-server vector database for semantic retrieval | OPTIONAL_ADAPTER later | Apache-2.0 | 28.2k stars; active | Recent commits observed Jun 1, 2026 | 296 open issues | `pip install chromadb`; local persistence possible | yes likely; Windows Docker/client details to test before hard dep | yes | no | no; cloud optional | irrelevant; embeddings decide language | easy/medium | Local vector DB stores paper text; path/data retention must be explicit | Unneeded until embeddings exist; version churn | Qdrant, LanceDB, FAISS, SQLite FTS | Defer. No embedding retrieval in Phase 6. |
| Qdrant | [qdrant/qdrant](https://github.com/qdrant/qdrant) / [docs](https://qdrant.tech/) | Production vector database and search engine | OPTIONAL_ADAPTER later | Apache-2.0 | 31.6k-31.7k stars; active; latest release v1.18.1 May 22, 2026 | Recent commits observed May 22, 2026 | 432-433 open issues; 1 security/quality signal visible | Docker server or Python client; heavier than Chroma for local prototype | client yes; server via Docker likely | yes, Docker/local server | optional for indexing acceleration, not required | no; cloud optional | irrelevant; embeddings decide language | medium | Server security/auth must be configured; README warns default Docker command is insecure | Operational overhead for local single-user Phase 6 | Chroma, LanceDB, FAISS | Defer. Strong candidate for later scalable RAG, not current skeleton. |
| sentence-transformers | [huggingface/sentence-transformers](https://github.com/huggingface/sentence-transformers) / [docs](https://sbert.net/) | Local embeddings, retrieval, reranking, semantic search | OPTIONAL_ADAPTER later | Apache-2.0 | 18.7k-18.8k stars; active | Recent commits observed May 11, 2026 | 1.3k open issues | `pip install sentence-transformers`; model downloads required | yes likely; model/runtime must be tested | yes | no for small CPU models; GPU optional | no | good if using multilingual/BGE models | easy/medium | Model downloads and `trust_remote_code` must be controlled | Adds model storage and runtime variance; not needed for rule evidence | FlagEmbedding/BGE, OpenAI-compatible embeddings, Transformers | Defer. Use only when semantic retrieval is needed. |
| BGE / FlagEmbedding | [FlagOpen/FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding) / [BGE docs](https://www.bge-model.com/) | BGE embedding/reranker toolkit; strong multilingual and Chinese retrieval options | OPTIONAL_ADAPTER later | MIT | 11.8k stars; active | Recent commits observed Apr 2, 2026 | 879 open issues | Python package/model downloads; some models heavy | likely yes but must test | yes | optional; larger models benefit from GPU | no | good; repo includes Chinese docs | medium | Model provenance and resource use must be explicit | Heavy for Phase 6; issue volume high | sentence-transformers, hosted embeddings | Defer. Strong future local Chinese embedding option, not current evidence skeleton. |
| Docling | [docling-project/docling](https://github.com/docling-project/docling) | Document parsing, advanced PDF understanding, unified document representation | OPTIONAL_ADAPTER later | MIT | 60.8k stars; very active | Recent commits observed May 28, 2026 | 866 open issues | pip/uv; parser stack larger than PyMuPDF | likely yes, but parser dependencies must be tested | yes | no for many features; depends on models/features | no | partial; parsing should handle many formats, language quality depends on OCR/models | medium | Treat parsed PDF/HTML as untrusted; sanitize outputs | Parser quality affects skeleton, but this phase already has blocks; adding parser now expands scope | PyMuPDF, GROBID, MinerU, Marker | Do not add in Phase 6. Keep as future ingestion adapter. |
| Marker | [datalab-to/marker](https://github.com/datalab-to/marker) | Converts PDF/docs to markdown/JSON/HTML/chunks; equations/tables/OCR | REFERENCE_ONLY; NOT_USE as hard dependency | GPL-3.0 code; model weights use modified AI Pubs Open Rail-M with commercial limits | 35.6k-35.7k stars; active | Recent commits observed May 5, 2026 | 344 open issues | `pip install marker-pdf`; PyTorch/model weights; optional LLM mode | likely possible but must test | yes | CPU/GPU/MPS supported; GPU recommended for throughput | optional; LLM mode may use Gemini/Ollama | good if OCR supports chosen language; depends on model | hard if coupled | GPL and model-license implications; untrusted document processing | License/commercial restrictions block hard dependency without explicit review | Docling, MinerU, GROBID | Do not introduce in Phase 6. Reference parser ideas only. |
| MinerU | [opendatalab/MinerU](https://github.com/opendatalab/MinerU) | High-accuracy document parsing to Markdown/JSON with formula/table/OCR support | REFERENCE_ONLY now; OPTIONAL_ADAPTER after license review | Custom MinerU Open Source License based on Apache-2.0, not standard SPDX | 66.1k stars; very active | Recent commits observed Jun 1, 2026 | 11 open issues visible | `uv pip install -U "mineru[all]"`; large models/resources | Windows supported with constraints | yes; offline/private deployment supported | CPU supported for pipeline; GPU/VLM options need 4GB-8GB+ VRAM | no for local; online/API options exist | strong; Chinese README and 109-language OCR | medium/hard | Custom license and heavy local runtime; untrusted document processing | Too heavy and license not standard for current phase | Docling, GROBID, PyMuPDF | Defer. Promising ingestion adapter after legal/resource review, not Phase 6. |
| GROBID | [grobidOrg/grobid](https://github.com/grobidOrg/grobid) / [docs](https://grobid.readthedocs.io/) | Scholarly PDF metadata/fulltext/reference extraction to structured TEI | OPTIONAL_ADAPTER later | Apache-2.0 | 4.9k stars; active | Recent commits observed May 30, 2026 | 312 open issues | Java service/Docker; operational setup required | via Java/Docker; must test | yes | no | no | partial; strongest for scholarly structure, not Chinese teaching | medium | Service boundary must sandbox PDFs; TEI conversion must be validated | Operational overhead; may be overkill for Phase 6 blocks | Docling, S2ORC doc2json, PyMuPDF | Defer. Useful for future citation/section evidence quality. |
| STORM | [stanford-oval/storm](https://github.com/stanford-oval/storm) | Multi-perspective research and report generation with citations | REFERENCE_ONLY | MIT | 28.3k stars; high interest | Recent commits observed Jan 15, 2025 | 57 open issues | Python app with LLM/search dependencies | likely, but not current target | partial; depends on external search/LLM | no framework GPU need | likely, because web/LLM/search providers | partial; depends on model/search | easy/medium | Search/LLM prompt outputs must be evidence-checked | Not an evidence extractor; less active | GPT-Researcher, PaperQA, custom direction curator | Reference only for future direction/survey organization, not Phase 6. |
| scispaCy | [allenai/scispacy](https://github.com/allenai/scispacy) | Scientific/biomedical NLP, abbreviation detection, entity linking | REFERENCE_ONLY | Apache-2.0 | 1.9k-2k stars | Recent commits observed Dec 4, 2025 | 35 open issues | pip plus separate model downloads; biomedical focus | likely yes | yes | optional for SciBERT model | no | poor/partial for Chinese and non-biomedical papers | easy | Model downloads and entity linker KB size/security must be controlled | Domain-specific, not general paper skeleton | spaCy, SciBERT, custom rules | Reference only; not suitable as Phase 6 core. |
| S2ORC doc2json | [allenai/s2orc-doc2json](https://github.com/allenai/s2orc-doc2json) | Scientific paper JSON schema and Grobid/LaTeX/JATS conversion utilities | REFERENCE_ONLY | Apache-2.0 | 467 stars; small project | Recent commit recency not fully verified from static page; repo shows only 48 commits | 7 open issues | Conda/Python 3.8 era; requires GROBID for PDFs | possible but dated | yes | no | no | partial | easy/medium | Depends on GROBID and older setup scripts | Dated setup; not needed if current schemas are stable | GROBID, Docling, Papermage | Reference only for schema ideas and citation/section layout. |
| PaperMage | [allenai/papermage](https://github.com/allenai/papermage) | Scientific paper document representation with spans/boxes/entities | REFERENCE_ONLY / NOT_USE as dependency | Apache-2.0 | 796 stars | Latest release Mar 17, 2024; README warns irregular maintenance | 27 open issues | Conda/PyPI extras; predictors/visualizers can be heavy | likely but not guaranteed | yes | optional depending predictors | no | partial | medium | Research prototype; untrusted PDF parsing | Maintainers state they are unlikely to maintain regularly | Docling, GROBID, MinerU | Do not depend on it. Reference its span/entity representation ideas only. |

Phase decision:

- DIRECT_DEPENDENCY: none for Phase 6.
- OPTIONAL_ADAPTER, deferred: PaperQA/PaperQA2, LlamaIndex, Chroma, Qdrant, sentence-transformers, BGE/FlagEmbedding, Docling, GROBID, MinerU after license review.
- REFERENCE_ONLY: LangChain, STORM, scispaCy, S2ORC doc2json, PaperMage, Marker parser ideas.
- NOT_USE as hard dependency now: Marker because GPL/model-license implications; PaperMage because maintainers warn it is a research prototype with irregular maintenance; all RAG/vector/embedding tools because the current phase does not need semantic retrieval or LLM evidence QA.
- New dependencies for Phase 6: none recommended.
- Required adapter now: no third-party adapter required. If code proceeds, implement internal, deterministic `GroundingService` and `SkeletonService` over existing schemas only.
- Code development authorized after this reuse gate: yes, but only for lightweight grounding/evidence index and paper skeleton artifacts, with offline tests.

Why Phase 6 should not introduce these tools now:

- The current input is already `DocumentIngestion.blocks`; the phase is about evidence bookkeeping and skeleton contracts, not high-recall semantic retrieval.
- RAG tools require embeddings and/or LLM calls, which would violate the current "no real LLM" phase goal unless heavily mocked.
- Vector stores add operational surface before the product has stable evidence schemas.
- High-quality parsers improve upstream ingestion, but expanding parsing belongs to a future ingestion adapter phase, not current grounding logic.
- A rule-based evidence index is easier to validate: every evidence reference can be checked against an existing block ID, section ID, page, and character span.

Tools delayed to later phases:

- PaperQA/PaperQA2: future `PaperEvidenceQAAdapter` for "where did the paper say this claim" and contradiction checks.
- LlamaIndex or LangChain: future RAG/context orchestration only if a narrow adapter proves useful.
- Chroma or Qdrant: future vector store adapter once embeddings and interactive retrieval are authorized.
- sentence-transformers/BGE: future local embedding adapter; BGE is especially relevant for Chinese and multilingual retrieval.
- Docling/GROBID/MinerU: future parser adapters to improve block quality, citation extraction, formulas, and structured sections.
- STORM: future reference for multi-perspective direction/survey organization, not evidence grounding.

Final recommended implementation route for Phase 6:

1. Consume only existing `DocumentIngestion.blocks` and `SourceStatus`.
2. Generate `evidence_index.json` with section, paragraph, formula-nearby, figure/table-nearby, and degraded evidence entries.
3. Generate `paper_skeleton.json` using deterministic section-title and keyword heuristics first.
4. For each skeleton field, attach `evidence_refs`, `evidence_status`, and `degraded_flags`.
5. If evidence is missing, mark the field as `INSUFFICIENT_EVIDENCE`; do not infer facts from title/abstract alone.
6. Add tests for missing sections, missing formulas, broken evidence refs, abstract-only input, and path-safe artifact reading.
7. Do not add RAG, embeddings, vector DBs, or parser expansion until a later reuse gate authorizes them.

## Phase 7 Reuse Evaluation - LLM Infrastructure

Verification date: 2026-06-02.

Scope note: this is the migration Phase 7 for the current backend rewrite. It provides LLM client, prompt builder, response cache, token budget, and JSON output validation. It does NOT enter teaching, card generation, formula tutoring, direction maps, drill, advisor, render, or frontend changes. Default pytest must not make real LLM calls.

Problem solved:

- Provide a unified `LLMClient` that calls any OpenAI-compatible endpoint.
- Support `authorization: Bearer` and `api-key` header authentication (MiMo, DeepSeek, generic).
- Support `chat` (plain text), `chat_json` (structured JSON with markdown-stripping and repair), and `chat_stream` (SSE streaming).
- Provide a `PromptBuilder` with system/context/evidence/user-question sections and instruction isolation.
- Provide an in-memory `ResponseCache` with SHA256 keys, TTL, version invalidation, and content-hash support.
- Provide a `TokenBudget` estimator for input length checking before LLM calls.
- All LLM calls must be mockable in default tests; no real API keys required.
- API key values must never appear in logs, responses, artifacts, or test output.

Old code migration source: `backend/llm/client.py`, `backend/llm/prompt_builder.py`, `backend/llm/response_cache.py`, `backend/config.py` (ModelGateway).

Candidates checked:

| Candidate | Problem solved | Use decision | License | Stars/activity | Recent commits | Issues status | Install complexity | Windows | Local | GPU | Paid API | Chinese | Replaceability | Safety | Risk | Alternatives | Final decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| httpx (existing) | HTTP client for OpenAI-compatible chat/completions endpoint | DIRECT_DEPENDENCY | BSD-3-Clause | already installed v0.28.1 | N/A | N/A | already present | yes | yes | no | no | irrelevant | easy | must redact API keys from error messages | already project dependency | requests, aiohttp | Adopted. Already used by source resolver; sufficient for sync/async chat, streaming via httpx-sse. |
| httpx-sse (existing) | SSE streaming for chat_stream | DIRECT_DEPENDENCY | MIT | already installed v0.0.14+ | N/A | N/A | already present | yes | yes | no | no | irrelevant | easy | SSE data must be validated as JSON | already project dependency | raw httpx line-by-line parsing | Adopted. Already installed; used by old backend/llm/client.py. |
| pydantic (existing) | JSON output validation and schema enforcement | DIRECT_DEPENDENCY | MIT | already installed v2.13.4 | N/A | N/A | already present | yes | yes | no | no | irrelevant | easy | extra="forbid" must be enforced | already project dependency | dataclasses, attrs | Adopted. Core schema boundary; use `model_validate_json()` for LLM output. |
| Old backend/llm/client.py | LLM client with chat/chat_json/chat_stream, api-key auth, markdown stripping | MIGRATE_AND_ADAPT | N/A (project code) | N/A | N/A | N/A | no new install | yes | yes | no | no | irrelevant | easy | API key redaction already implemented | imports backend.schemas; needs rewrite to use researchsensei.schemas | rewrite from scratch | Migrate. Core logic is clean httpx-based; adapt imports and add mock mode. |
| Old backend/llm/prompt_builder.py | Prompt templates with system/context/evidence/user sections, instruction isolation | MIGRATE_AND_ADAPT | N/A (project code) | N/A | N/A | N/A | no new install | yes | yes | no | no | Chinese-first | easy | user question must be instruction-isolated | imports InteractiveContextPackage from old schemas; teaching/formula/drill prompts are Phase 8+ scope | rewrite from scratch | Migrate core PromptBuilder class; teaching/formula/drill prompts deferred to later phases. |
| Old backend/llm/response_cache.py | In-memory LLM response cache with SHA256 keys, TTL, version invalidation | MIGRATE_AS_IS | N/A (project code) | N/A | N/A | N/A | no new install | yes | yes | no | no | irrelevant | easy | cache keys must not contain API keys | no external dependencies; clean dataclass design | rewrite from scratch | Migrate. Minimal adaptation needed; add content_hash support. |
| OpenAI Python SDK | Official OpenAI client with type-safe chat, streaming, JSON mode | NOT_USE | Apache-2.0 | 25k+ stars; very active | active | many open issues | pip install openai; pulls httpx, pydantic, anyio, jiter, distro | yes | yes | no | yes (OpenAI pricing) | partial | medium | SDK sends requests to provider; must not log API key | Adds provider lock-in surface; httpx already sufficient for OpenAI-compatible API | httpx direct, LiteLLM | Do not introduce. httpx is already installed and sufficient for OpenAI-compatible endpoints. The SDK adds dependency surface without solving a problem httpx cannot. |
| LiteLLM | Unified multi-provider LLM gateway with 100+ provider support | NOT_USE | MIT | 21k+ stars; very active | active | 900+ open issues; dependency-heavy | pip install litellm; very heavy dependency tree (100+ MB); pulls openai, anthropic, google-generativeai, boto3, transformers, etc. | yes | likely | no | optional depending provider | partial | medium | Provider keys and prompts must be isolated; proxy mode adds attack surface | Too heavy for Phase 7; dependency conflicts reported; adds operational complexity before product needs multi-provider | httpx direct, OpenAI SDK | Do not introduce. Phase 7 only needs OpenAI-compatible endpoints; httpx handles this. LiteLLM is a strong candidate for later when multiple non-OpenAI-compatible providers are needed. |
| tenacity | Python retry library with exponential backoff, stop conditions, retry predicates | OPTIONAL_ADAPTER later | Apache-2.0 | 370+ stars; mature/stable | low activity (stable library) | few issues | pip install tenacity; very lightweight | yes | yes | no | no | irrelevant | easy | retry must not retry on auth errors or invalid input | Low risk; but adds dependency for simple retry loop | simple retry decorator, asyncio retry | Defer. Phase 7 can implement a simple retry wrapper (3 attempts, exponential backoff) without a library. Revisit if retry logic grows complex. |
| tiktoken | OpenAI's BPE tokenizer for token counting | OPTIONAL_ADAPTER later | MIT | 13k+ stars; active | active | some issues | pip install tiktoken; Rust-backed, moderate install size | yes | yes | no | no | irrelevant | easy | tokenizer encoding must match provider; DeepSeek uses different vocab than OpenAI | Approximate for non-OpenAI models (DeepSeek ~10-20% error); adds model-specific encoding config | character-based estimation, transformers | Defer. Phase 7 uses character-based token estimation (4 chars ≈ 1 token). Revisit when real LLM integration needs accurate budgeting. |
| diskcache | Disk-backed cache with SQLite index | NOT_USE | Apache-2.0 | 3.6k stars; mature | low activity (stable) | few issues | pip install diskcache; lightweight | yes | yes | no | no | irrelevant | medium | Cache files must be in controlled directory | Unnecessary; in-memory cache sufficient for Phase 7; workspace file JSON already available for persistence | in-memory dict, SQLite via existing aiosqlite | Do not introduce. In-memory ResponseCache is sufficient; if persistence is needed later, use existing workspace file JSON or SQLite. |

Old `backend/llm` migration assessment:

| Old file | Migratable content | Adaptation needed | Deferred content |
|---|---|---|---|
| `backend/llm/client.py` | `LLMClient` class: `chat()`, `chat_json()`, `chat_stream()`, `_headers()` auth logic, markdown code block stripping, JSON repair | Import path: `backend.schemas.ModelProviderConfig` → `researchsensei.core.config.ModelProviderConfig`. Add mock mode. Add `httpx_sse` import path. | None; all core logic is Phase 7 scope. |
| `backend/llm/prompt_builder.py` | `PromptBuilder` class: `SYSTEM_INSTRUCTION`, `build_interactive_prompt()` section layout, instruction isolation marker | Remove `InteractiveContextPackage` dependency (old schema). Simplify to accept plain dicts or new schema types. | `build_teaching_prompt()`, `build_formula_prompt()`, `build_drill_prompt()`, `build_pattern_prompt()` — these are Phase 8+ scope. |
| `backend/llm/response_cache.py` | `ResponseCache` class: `key()`, `get()`, `set()`, `invalidate_version()`, `invalidate_prefix()`, `invalidate_all()`, `CacheEntry` dataclass | None needed; pure Python, no external dependencies. Add `content_hash` parameter to `key()`. | None. |
| `backend/config.py` | `ModelGateway` class: sync `chat_json()`, `test_connection()`, `_friendly_error()`, `_redact()` | Already migrated as `ModelProviderConfig` in `src/researchsensei/core/config.py`. Gateway logic merges into new `LLMClient`. | `test_connection()` can be a method on `LLMClient`. |

Phase decision:

- DIRECT_DEPENDENCY: httpx (existing), httpx-sse (existing), pydantic (existing)
- MIGRATE_AND_ADAPT: backend/llm/client.py, backend/llm/prompt_builder.py, backend/llm/response_cache.py
- OPTIONAL_ADAPTER, deferred: tenacity (retry), tiktoken (token counting)
- NOT_USE: OpenAI Python SDK, LiteLLM, diskcache
- New dependencies for Phase 7: none recommended
- Required adapter now: no third-party adapter required. Implement internal `LLMClient`, `PromptBuilder`, `ResponseCache`, `TokenBudget` using existing httpx + pydantic + httpx-sse.
- Code development authorized after this reuse gate: yes

Why these decisions:

1. **httpx is sufficient**: The project already uses httpx for source resolver. OpenAI-compatible endpoints are standard REST APIs with JSON bodies. httpx handles sync/async, timeouts, headers, and with httpx-sse handles streaming. No need for the OpenAI SDK.

2. **LiteLLM is too heavy**: Phase 7 only needs OpenAI-compatible endpoints (DeepSeek, MiMo, generic). LiteLLM's 100+ MB dependency tree and 900+ open issues add risk without solving a current problem. Revisit when non-OpenAI-compatible providers are needed.

3. **Old code is clean and migratable**: The backend/llm code uses httpx directly, has clean separation, and already handles the auth header variants (Bearer vs api-key). Migration is primarily import path changes.

4. **Simple retry beats tenacity**: A 3-attempt exponential backoff wrapper is ~20 lines of code. Adding tenacity for this is premature optimization. Revisit if retry logic grows complex (circuit breaker, per-error-type policies).

5. **Character estimation beats tiktoken**: For Phase 7, a simple `len(text) / 4` estimation is sufficient for token budget checks. tiktoken adds model-specific encoding config and is inaccurate for DeepSeek's tokenizer anyway. Revisit when real LLM integration needs precise budgeting.

6. **In-memory cache is sufficient**: Phase 7's ResponseCache doesn't need disk persistence. If needed later, the workspace store already supports file JSON writes.

Final recommended implementation route for Phase 7:

1. Create `src/researchsensei/llm/__init__.py`, `client.py`, `types.py`, `prompt_builder.py`, `response_cache.py`, `token_budget.py`.
2. Migrate `LLMClient` from `backend/llm/client.py` with adapted imports and mock mode.
3. Migrate `ResponseCache` from `backend/llm/response_cache.py` as-is.
4. Migrate `PromptBuilder` core (system/context/evidence/user sections, instruction isolation) from `backend/llm/prompt_builder.py`; defer teaching/formula/drill prompts.
5. Add `TokenBudget` with character-based estimation.
6. Add `LLMTypes` for `ChatMessage`, `ChatResponse`, `LLMConfig` schemas.
7. All tests mock; no real API keys; API key redaction tested.
8. Add mock LLM client that returns configurable responses for testing downstream consumers.

## Phase 8 Reuse Evaluation - Evidence-Constrained Paper Card JSON v1

Verification date: 2026-06-02.

Scope note: this is the migration Phase 8 for the current backend rewrite. It generates a structured `paper_card.json` from existing artifacts (`parsed_document.json`, `evidence_index.json`, `paper_skeleton.json`) using Phase 7 LLM infrastructure. All claims must be evidence-constrained. This phase does NOT enter HTML rendering, formula deep explanation, teaching five-layer engine, drill, advisor, direction map, RAG, or real LLM default tests.

Problem solved:

- Convert `paper_skeleton.json` + `evidence_index.json` into a structured `paper_card.json`.
- Each key claim in the card must reference an `evidence_ref` from the evidence index.
- Uncertain content must be labeled `UNVERIFIED`, `INSUFFICIENT_EVIDENCE`, or `NEEDS_HUMAN_CHECK`.
- LLM may summarize/rewrite only within evidence constraints; no free-form generation.
- Provide both rule-based (no LLM) and LLM-enhanced paths.
- Default tests must be fully mockable; no real LLM calls.

Candidates checked:

| Candidate | Problem solved | Use decision | License | Notes |
|---|---|---|---|---|
| Old `backend/understanding.py` | LLM-based skeleton generation with fallback | REFERENCE_ONLY | N/A (project code) | LLM prompt structure is useful reference. Fallback is too template-y (`"需要上传全文后分析"`). Does NOT enforce evidence_ref binding. Must be rewritten, not migrated. |
| Old `backend/teaching.py` | LLM-based paper card generation with fallback | REFERENCE_ONLY | N/A (project code) | LLM prompt for `thirty_second`/`five_minute`/`deep_dive` is useful reference. Fallback is shallow (`"待分析"`). Does NOT bind claims to evidence. Must be rewritten, not migrated. |
| Old `backend/schemas.py` TeachingCard | Schema for paper card output | REFERENCE_ONLY | N/A (project code) | Has `thirty_second`, `five_minute`, `deep_dive`, `evidence_status`. Good starting point but needs `evidence_refs` field and per-claim evidence binding. |
| Pydantic (existing) | Schema validation for paper_card.json | DIRECT_DEPENDENCY | MIT, already installed | Sufficient. Use `model_validate_json()` with `extra="forbid"`. |
| Phase 7 LLM infrastructure | Mock LLM for card generation | DIRECT_DEPENDENCY | N/A (already implemented) | `MockLLMClient`, `PromptBuilder`, `ResponseCache`, `TokenBudget` all ready. |
| PaperQA / PaperQA2 | Scientific RAG for evidence gathering | NOT_USE | Apache-2.0 | Not needed. Phase 8 consumes existing `evidence_index.json`; no RAG needed. Defer to interactive/RAG phase. |
| LlamaIndex | RAG framework | NOT_USE | MIT | Not needed. Phase 8 is card generation from existing artifacts, not retrieval. Defer. |
| LangChain | Agent/LLM framework | NOT_USE | MIT | Not needed. Too broad. Defer. |

Old code migration assessment:

| Old file | Useful reference | What to keep | What to discard |
|---|---|---|---|
| `backend/understanding.py` | LLM prompt structure for skeleton fields | Prompt pattern: "分析这篇论文，提取核心骨架" + JSON schema | Fallback logic (too template-y), no evidence_ref binding, `print()` for warnings |
| `backend/teaching.py` | LLM prompt for thirty_second/five_minute/deep_dive | Prompt pattern: "根据论文骨架生成教学卡片" + JSON output format | Fallback logic (shallow), no evidence binding, `print()` for warnings |
| `backend/schemas.py` TeachingCard | Field names: `thirty_second`, `five_minute`, `deep_dive`, `evidence_status` | Field structure | Missing `evidence_refs` per claim, missing `warnings` field |

Phase decision:

- DIRECT_DEPENDENCY: Pydantic (existing), Phase 7 LLM infrastructure (existing)
- REFERENCE_ONLY: backend/understanding.py, backend/teaching.py, backend/schemas.py TeachingCard
- NOT_USE: PaperQA, LlamaIndex, LangChain
- New dependencies for Phase 8: none
- Required adapter now: no third-party adapter required. Implement internal `PaperCardBuilder` using existing schemas + Phase 7 LLM infra.
- Code development authorized after this reuse gate: yes

Why these decisions:

1. **Old understanding/teaching code must be rewritten, not migrated**: The old code does not enforce evidence_ref binding. The fallbacks are template-y placeholders. The LLM prompts are useful as reference patterns but need evidence-constrained redesign.

2. **Phase 8 is card generation, not RAG**: The input is already-produced artifacts. No retrieval or embedding is needed. PaperQA/LlamaIndex/LangChain are all deferred.

3. **Pydantic is sufficient**: The existing schema system with `extra="forbid"` and validators can fully constrain `paper_card.json`.

4. **Phase 7 LLM infra is ready**: `MockLLMClient` provides deterministic testing. `PromptBuilder` provides section isolation. No new LLM tooling needed.

5. **Evidence constraint is the key differentiator**: Unlike the old `TeachingService` which just copies skeleton fields, the new `PaperCardBuilder` must bind every claim to an `evidence_ref` and mark unsupported claims as degraded.

Final recommended implementation route for Phase 8:

1. Create `src/researchsensei/schemas/cards.py` with `PaperCard` schema including `evidence_refs` per claim and `warnings`.
2. Create `src/researchsensei/paper_card.py` with `build_paper_card()` that consumes `paper_skeleton.json` + `evidence_index.json`.
3. Rule-based path: extract key claims from skeleton, bind to evidence_refs, mark unsupported as `INSUFFICIENT_EVIDENCE`.
4. LLM-enhanced path (optional, mock in tests): use `PromptBuilder` + `MockLLMClient` to generate `thirty_second`/`five_minute` summaries within evidence constraints.
5. Integrate into `SinglePaperIngestionRunner` to write `paper_card.json` as 5th artifact.
6. Add API endpoint or extend existing artifacts endpoint to serve `paper_card.json`.
7. All tests mock; no real LLM calls; evidence_ref binding tested.

## Phase 9 Reuse Evaluation - Formula Card JSON v1

Verification date: 2026-06-02.

Scope note: this is the migration Phase 9 for the current backend rewrite. It generates structured `formula_card.json` from existing artifacts (`parsed_document.json`, `evidence_index.json`, `paper_skeleton.json`). Each formula explanation must be evidence-constrained. This phase does NOT enter HTML rendering, teaching five-layer engine, drill, advisor, direction map, RAG, or real LLM default tests.

Problem solved:

- Extract formula blocks from `parsed_document.json`.
- For each formula, generate a structured `formula_card.json` with: purpose, symbols, terms, numeric example, remove effect, weight sensitivity, plain summary.
- Every formula explanation must bind to an `evidence_ref` from the evidence index.
- If formula blocks are absent or nearby text is insufficient, mark as `FORMULA_UNAVAILABLE` or `INSUFFICIENT_EVIDENCE`.
- Provide both rule-based (no LLM) and LLM-enhanced paths.
- Default tests must be fully mockable; no real LLM calls.

Candidates checked:

| Candidate | Problem solved | Use decision | License | Notes |
|---|---|---|---|---|
| Old `backend/formula.py` | LLM-based formula explanation with fallback | REFERENCE_ONLY | N/A (project code) | LLM prompt ("把 LaTeX 公式讲清楚") is useful reference. Fallback is too generic ("这个公式想把论文的核心机制变成可优化目标"). Does NOT bind explanations to evidence. Must be rewritten, not migrated. |
| Old `backend/schemas.py` FormulaCard | Schema for formula card output | REFERENCE_ONLY | N/A (project code) | Has `formula_ref`, `formula_latex`, `problem`, `symbols`, `numeric_example`, `remove_effect`, `weight_change_effect`, `plain_summary`, `evidence_status`. Good field structure. Missing `evidence_refs` list and `warnings`. |
| Old `backend/schemas.py` FormulaSymbol | Schema for formula symbol explanation | REFERENCE_ONLY | N/A (project code) | Has `symbol`, `meaning`, `role`. Clean and reusable. |
| Pydantic (existing) | Schema validation for formula_card.json | DIRECT_DEPENDENCY | MIT, already installed | Sufficient. Use `model_validate_json()` with `extra="forbid"`. |
| Phase 7 LLM infrastructure | Mock LLM for formula enhancement | DIRECT_DEPENDENCY | N/A (already implemented) | `MockLLMClient`, `PromptBuilder`, `ResponseCache`, `TokenBudget` all ready. |
| Marker / MinerU / GROBID / Docling | Better formula extraction from PDF | NOT_USE | Various | Not needed for Phase 9. Current `LightweightIngestionService` already extracts formula blocks from .md/.txt. PDF formula extraction quality improvement belongs to a future ingestion adapter phase. Phase 9 consumes existing `BlockType.FORMULA` blocks only. |
| MathJax / KaTeX | LaTeX formula rendering in HTML | NOT_USE | Various | Not needed for Phase 9. Phase 9 outputs JSON only. LaTeX rendering belongs to the render/frontend phase. |
| SymPy | Symbolic math for formula analysis | OPTIONAL_ADAPTER later | BSD-3-Clause | Could be used for symbol parsing and term analysis. Defer to Phase 9+ if rule-based symbol extraction proves insufficient. |

Old code migration assessment:

| Old file | Useful reference | What to keep | What to discard |
|---|---|---|---|
| `backend/formula.py` | LLM prompt pattern: "把 LaTeX 公式讲清楚" + 6-point analysis (symbols, terms, remove effect, weight sensitivity, numeric example, summary) | Prompt structure for LLM-enhanced path | Fallback logic (too generic), `print()` for warnings, no evidence binding |
| `backend/schemas.py` FormulaCard | Field names: `formula_ref`, `formula_latex`, `problem`, `symbols`, `numeric_example`, `remove_effect`, `weight_change_effect`, `plain_summary` | Field structure, FormulaSymbol schema | Missing `evidence_refs`, `warnings`, `confidence` |
| `backend/llm/prompt_builder.py` `build_formula_prompt()` | 6-point formula analysis prompt | Prompt pattern | Standalone prompt, needs integration with evidence context |

Phase decision:

- DIRECT_DEPENDENCY: Pydantic (existing), Phase 7 LLM infrastructure (existing)
- REFERENCE_ONLY: backend/formula.py, backend/schemas.py FormulaCard/FormulaSymbol
- OPTIONAL_ADAPTER, deferred: SymPy (symbolic math analysis)
- NOT_USE: Marker, MinerU, GROBID, Docling (ingestion adapter, not Phase 9), MathJax/KaTeX (render, not Phase 9)
- New dependencies for Phase 9: none
- Required adapter now: no third-party adapter required. Implement internal `FormulaCardBuilder` using existing schemas + Phase 7 LLM infra.
- Code development authorized after this reuse gate: yes

Why these decisions:

1. **Old formula code must be rewritten, not migrated**: The old `FormulaService._fallback()` returns generic explanations that don't reference the actual paper content. The LLM path doesn't bind explanations to evidence refs. Must be rebuilt with evidence constraints.

2. **Phase 9 consumes existing formula blocks, not parser improvements**: The `LightweightIngestionService` already extracts `BlockType.FORMULA` blocks with `raw_latex` and `text`. Improving formula extraction quality (e.g., better LaTeX parsing from PDF) belongs to a future ingestion adapter phase.

3. **MathJax/KaTeX belong to render phase**: Phase 9 outputs JSON. LaTeX rendering is a presentation concern for the render/frontend phase.

4. **SymPy is optional and deferred**: Rule-based symbol extraction (regex on LaTeX) may be sufficient. SymPy can be added later if symbolic analysis is needed.

5. **Evidence constraint is the key differentiator**: Unlike the old `FormulaService` which returns generic explanations, the new `FormulaCardBuilder` must bind every explanation to evidence from the parsed document.

Final recommended implementation route for Phase 9:

1. Create `FormulaCard` and `FormulaSymbol` schemas in `src/researchsensei/schemas/cards.py` (extend existing file).
2. Create `src/researchsensei/formula_card.py` with `build_formula_cards()`.
3. Rule-based path: extract `BlockType.FORMULA` blocks, regex-parse symbols, bind to evidence from nearby text blocks.
4. LLM-enhanced path (optional, mock in tests): use `PromptBuilder` with 6-point formula analysis prompt, constrain output to evidence.
5. Integrate into `SinglePaperIngestionRunner` to write `formula_cards.json` as 6th artifact.
6. All tests mock; no real LLM calls; evidence_ref binding tested; FORMULA_UNAVAILABLE degradation tested.

## Phase 10 Reuse Evaluation - Teaching Card JSON v1

Verification date: 2026-06-02.

Scope note: this is the migration Phase 10 for the current backend rewrite. It generates structured `teaching_cards.json` implementing the "五层讲解法" (five-layer teaching method). All explanations must be evidence-constrained. This phase does NOT enter HTML rendering, drill, advisor, direction map, RAG, or real LLM default tests.

Problem solved:

- Generate structured teaching cards from existing artifacts (`parsed_document.json`, `evidence_index.json`, `paper_skeleton.json`, `paper_card.json`, `formula_cards.json`).
- Implement five-layer teaching method:
  1. 人话版 (plain language explanation)
  2. 类比版 (analogy)
  3. 最小公式版 (minimal formula version)
  4. 小数字例子版 (small numeric example)
  5. 论文作用版 (role in paper)
- Every explanation must bind to an `evidence_ref` from the evidence index.
- If evidence is insufficient, mark as `INSUFFICIENT_EVIDENCE` or `NEEDS_HUMAN_CHECK`.
- Provide both rule-based (no LLM) and LLM-enhanced paths.
- Default tests must be fully mockable; no real LLM calls.

Candidates checked:

| Candidate | Problem solved | Use decision | License | Notes |
|---|---|---|---|---|
| Old `backend/teaching.py` | LLM-based teaching card generation with fallback | REFERENCE_ONLY | N/A (project code) | LLM prompt ("根据论文骨架生成教学卡片") is useful reference. Fallback is shallow ("问题" for thirty_second). Only has 3 layers (thirty_second, five_minute, deep_dive), not 5. Does NOT bind to evidence. Must be rewritten, not migrated. |
| Old `backend/schemas.py` TeachingCard | Schema for teaching card output | REFERENCE_ONLY | N/A (project code) | Has `thirty_second`, `five_minute`, `deep_dive`, `evidence_status`. Good starting point but needs 5-layer structure and evidence_refs. |
| Old `backend/llm/prompt_builder.py` `build_teaching_prompt()` | Teaching prompt template | REFERENCE_ONLY | N/A (project code) | Prompt pattern: "先直觉，再公式，再数字例子". Useful reference for LLM-enhanced path. |
| Pydantic (existing) | Schema validation for teaching_cards.json | DIRECT_DEPENDENCY | MIT, already installed | Sufficient. Use `model_validate_json()` with `extra="forbid"`. |
| Phase 7 LLM infrastructure | Mock LLM for teaching enhancement | DIRECT_DEPENDENCY | N/A (already implemented) | `MockLLMClient`, `PromptBuilder`, `ResponseCache`, `TokenBudget` all ready. |
| Anki / py-fsrs / spaced repetition | Spaced repetition scheduling | NOT_USE | Various | Not needed for Phase 10. Teaching card generation is content creation, not scheduling. Spaced repetition belongs to the drill/review phase (Phase 12+). |
| STORM / tutoring agents | Multi-perspective research and report generation | NOT_USE | MIT | Not needed. Phase 10 is single-paper teaching card generation, not multi-perspective research. Reference only for future direction/survey work. |

Old code migration assessment:

| Old file | Useful reference | What to keep | What to discard |
|---|---|---|---|
| `backend/teaching.py` | LLM prompt: "根据论文骨架生成教学卡片" + "先直觉，再公式，再数字例子" | Prompt structure for LLM-enhanced path | Fallback logic (shallow), `print()` for warnings, no evidence binding, only 3 layers |
| `backend/schemas.py` TeachingCard | Field names: `thirty_second`, `five_minute`, `deep_dive` | Field structure concept | Only 3 layers, missing analogy and paper-role layers, missing evidence_refs |
| `backend/llm/prompt_builder.py` `build_teaching_prompt()` | Teaching prompt template | Prompt pattern for "先直觉，再公式，再数字例子" | Standalone prompt, needs integration with evidence context |

Phase decision:

- DIRECT_DEPENDENCY: Pydantic (existing), Phase 7 LLM infrastructure (existing)
- REFERENCE_ONLY: backend/teaching.py, backend/schemas.py TeachingCard, backend/llm/prompt_builder.py build_teaching_prompt()
- NOT_USE: Anki/py-fsrs (spaced repetition, defer to drill phase), STORM/tutoring agents (too broad)
- New dependencies for Phase 10: none
- Required adapter now: no third-party adapter required. Implement internal `TeachingCardBuilder` using existing schemas + Phase 7 LLM infra.
- Code development authorized after this reuse gate: yes

Why these decisions:

1. **Old teaching code must be rewritten, not migrated**: The old `TeachingService` only has 3 layers (thirty_second, five_minute, deep_dive). The new design requires 5 layers. The fallback is shallow and doesn't reference actual paper content. No evidence binding.

2. **Anki/spaced repetition belongs to drill phase**: Phase 10 is about content creation (teaching cards), not scheduling (when to review). Spaced repetition is a Phase 12+ concern.

3. **Phase 7 LLM infra is ready**: `MockLLMClient` provides deterministic testing. `PromptBuilder` provides section isolation. No new LLM tooling needed.

4. **Evidence constraint is the key differentiator**: Unlike the old `TeachingService` which just copies skeleton fields, the new `TeachingCardBuilder` must bind every explanation to evidence and mark unsupported claims as degraded.

Final recommended implementation route for Phase 10:

1. Create `TeachingCard` schema in `src/researchsensei/schemas/cards.py` with 5-layer structure.
2. Create `src/researchsensei/teaching_card.py` with `build_teaching_cards()`.
3. Rule-based path: extract key concepts from skeleton + paper_card + formula_cards, generate conservative 5-layer explanations, bind to evidence.
4. LLM-enhanced path (optional, mock in tests): use `PromptBuilder` with "先直觉，再公式，再数字例子" prompt, constrain output to evidence.
5. Integrate into `SinglePaperIngestionRunner` to write `teaching_cards.json` as 7th artifact.
6. All tests mock; no real LLM calls; evidence_ref binding tested; INSUFFICIENT_EVIDENCE degradation tested.

## Phase 11 Reuse Evaluation - Query / Acquisition / Selection / Reading Plan v1

Verification date: 2026-06-02.

Scope note: this is the migration Phase 11 for the current backend rewrite. It implements the direction learning entry point: user input → query plan → candidate pool → reading plan. This phase does NOT enter batch paper pipeline, direction map, multi-paper paper_card, HTML rendering, drill, advisor, RAG, or real network/LLM default tests.

Problem solved:

- Accept user research direction input.
- Generate structured query plan (direction_zh, direction_en, core_terms, related_terms, exclude_terms, search_intents).
- Search arXiv and OpenAlex for candidate papers.
- Build candidate pool with metadata (title, authors, year, venue, abstract, citation_count, arxiv_id, doi, pdf_url).
- Score, deduplicate, classify, and rank candidates.
- Generate reading plan with A_READ / B_SKIM / C_REFERENCE / D_IGNORE priorities.
- Output `candidate_pool.json` and `reading_plan.json`.
- Default tests must be fully mockable; no real network calls.

Candidates checked:

| Candidate | Problem solved | Use decision | License | Notes |
|---|---|---|---|---|
| Old `backend/query.py` | LLM-based query understanding with fallback | REFERENCE_ONLY | N/A (project code) | LLM prompt ("分析用户的研究方向") is useful reference. Fallback is simple (just uses query as-is). Good starting point but needs adaptation to new schema imports. |
| Old `backend/acquisition.py` | Multi-source paper search (arXiv, OpenAlex, paper-search-mcp) | REFERENCE_ONLY | N/A (project code) | arXiv and OpenAlex search logic is useful reference. paper-search-mcp via subprocess is fragile. Uses `ThreadPoolExecutor` for parallel search. Good structure but needs adapter pattern. |
| Old `backend/selection.py` | Scoring, dedup, role classification, reading plan generation | REFERENCE_ONLY | N/A (project code) | Scoring breakdown is well-structured and explainable. Role classification is domain-specific (time series anomaly detection). Needs generalization. Good reference for `scoring_breakdown` structure. |
| arXiv API | Paper search via Atom API | DIRECT_ADAPTER | arXiv terms of service | No API key needed. Returns title/authors/abstract/pdf_url/arxiv_id. Already referenced in old acquisition.py. Well-known public API. |
| OpenAlex API | Open metadata, citation counts | DIRECT_ADAPTER | CC0 public domain | No API key needed. Returns title/authors/year/venue/abstract/citation_count/doi. Already referenced in old acquisition.py. Strong for citation data. |
| Semantic Scholar API | Citation count, venue, paper metadata | OPTIONAL_ADAPTER later | ODC-By | Requires API key for bulk access. Rate-limited. Good for citation enrichment but not needed for Phase 11 minimal viable search. Defer to citation enrichment phase. |
| Crossref | DOI / publication metadata | OPTIONAL_ADAPTER later | CC0 public domain | No API key needed but rate-limited without polite pool. Good for DOI resolution. Not needed for Phase 11 minimal search. Defer. |
| Papers With Code | code_url / github_repo | OPTIONAL_ADAPTER later | MIT | No API key needed. Good for code availability. Not needed for Phase 11 minimal search. Defer. |
| GPT-Researcher | Web research agent | NOT_USE | Apache-2.0 | Too heavy for Phase 11. Adds LLM/web dependencies. Reference only for future direction research. |
| Google Scholar MCP | Google Scholar search | REFERENCE_ONLY | Varies | Unstable, may violate ToS. Use only as reference for search result structure. |
| GitHub Search | Paper code search | NOT_USE | N/A | Not needed for Phase 11. Defer to code adapter phase. |
| Pydantic (existing) | Schema validation | DIRECT_DEPENDENCY | MIT, already installed | Sufficient for QueryPlan, CandidatePaper, ReadingPlan schemas. |
| Phase 7 LLM infrastructure | Mock LLM for query understanding | DIRECT_DEPENDENCY | N/A (already implemented) | `MockLLMClient`, `PromptBuilder` ready for query planner. |

Old code migration assessment:

| Old file | Useful reference | What to keep | What to discard |
|---|---|---|---|
| `backend/query.py` | LLM prompt for direction analysis, fallback logic | Query understanding pattern, language detection | `print()` for warnings, old schema imports |
| `backend/acquisition.py` | arXiv Atom API parsing, OpenAlex search, parallel execution | arXiv/OpenAlex search functions, `ThreadPoolExecutor` pattern | paper-search-mcp subprocess (fragile), old schema imports |
| `backend/selection.py` | Scoring breakdown structure, role classification, reading plan generation | `ScoringBreakdown` fields, `_venue_prestige()`, `build_reading_plan()` | Domain-specific relevance logic (time series anomaly detection), old schema imports |

Phase decision:

- DIRECT_ADAPTER: arXiv API (no key needed), OpenAlex API (no key needed)
- DIRECT_DEPENDENCY: Pydantic (existing), Phase 7 LLM infrastructure (existing)
- REFERENCE_ONLY: backend/query.py, backend/acquisition.py, backend/selection.py, Google Scholar MCP
- OPTIONAL_ADAPTER, deferred: Semantic Scholar (citation enrichment), Crossref (DOI resolution), Papers With Code (code availability)
- NOT_USE: GPT-Researcher (too heavy), GitHub Search (not needed)
- New dependencies for Phase 11: none (httpx already installed for API calls)
- Required adapter now: yes, arXiv and OpenAlex adapters (thin httpx wrappers)
- Code development authorized after this reuse gate: yes

Why these decisions:

1. **arXiv and OpenAlex are the minimal viable search stack**: Both are free, no API key needed, and already referenced in old acquisition.py. They provide title/authors/abstract/citation_count/arxiv_id/doi/pdf_url.

2. **Old code is good reference but needs rewriting**: The old code imports from `backend.schemas` and uses `print()` for warnings. The selection scoring is domain-specific. Need to adapt to new schema imports and generalize.

3. **Semantic Scholar/Crossref/Papers With Code are deferred**: They add API key management and rate limiting. Phase 11 can work with just arXiv + OpenAlex.

4. **GPT-Researcher is too heavy**: Adds LLM/web dependencies. Not needed for Phase 11's focused search.

5. **Selection scoring should be explainable**: The old `ScoringBreakdown` structure is good. Keep the weighted scoring approach with transparent breakdown.

Final recommended implementation route for Phase 11:

1. Create `src/researchsensei/query/` module with `QueryPlanner` (rule-based + LLM-enhanced).
2. Create `src/researchsensei/acquisition/` module with `ArxivAdapter` and `OpenAlexAdapter`.
3. Create `src/researchsensei/selection/` module with `SelectionService` (scoring, dedup, role classification).
4. Create schemas: `QueryPlan`, `CandidatePaper`, `CandidatePool`, `ReadingPlan`, `ScoringBreakdown`.
5. All search adapters use httpx with mock transport in tests.
6. Integration: user input → query plan → candidate pool → reading plan → output JSON files.
7. All tests mock; no real network calls; scoring breakdown tested.

### Render / Frontend

Current decision:

- Keep Vue 3 + Vite + TypeScript + Pinia + TailwindCSS + KaTeX.
- Do not switch to React.
- If adding UI components, prefer mature Vue ecosystem packages.

Candidates to evaluate before new render/frontend work:

- KaTeX / MathJax;
- Mermaid;
- D3 if graph interaction is needed;
- Vue component libraries only when they reduce real complexity.

### LLM Layer

Candidates to evaluate before new LLM work:

- OpenAI-compatible clients;
- LiteLLM;
- httpx-based thin client;
- retry/cache/streaming libraries.

Decision rule:

- No real LLM calls in default pytest.
- API keys never enter logs.
- Business logic must not call provider HTTP APIs directly.
- Provider differences must be hidden behind an adapter.

### Teaching / Formula / Drill / Advisor

Candidates to evaluate before self-building:

- tutoring/paper-reading open-source agents;
- STORM-style outline/question generation projects;
- formula derivation helpers such as SymPy;
- spaced repetition libraries such as py-fsrs;
- prompt evaluation tools such as promptfoo/Ragas.

Decision rule:

- If no mature project can satisfy "teach the user to understand and defend the paper", ResearchSensei may self-build core teaching logic.
- Formula rendering is never self-built.
- Formula computation may use SymPy when parseable.
- Drill scheduling should prefer py-fsrs or another reviewed algorithm.

## Existing Dependency Snapshot

This table records current project-level dependencies already present or recently added. Dynamic GitHub fields are not substitutes for Phase-specific verification.

| Dependency | Current role | Decision | Notes |
|---|---|---|---|
| FastAPI | Backend API framework | DIRECT_DEPENDENCY | Standard API layer; upload uses `UploadFile = File(...)` |
| python-multipart | FastAPI multipart upload support | DIRECT_DEPENDENCY | Required for standard file upload |
| httpx | HTTP client and mocked network tests | DIRECT_DEPENDENCY | Used by source resolver; tests use `MockTransport` |
| Pydantic | Schema validation | DIRECT_DEPENDENCY | Core schema boundary |
| PyMuPDF | PDF fallback text extraction | DIRECT_DEPENDENCY | Lightweight fallback, not high-quality structure parser |
| python-dotenv | Environment loading | DIRECT_DEPENDENCY | Keys must be redacted from logs |
| pytest / pytest-asyncio | Tests | DIRECT_DEPENDENCY | Default pytest must not require live network/server |
| Jinja2 | Legacy/template rendering dependency | DIRECT_DEPENDENCY | Current focus is backend API; frontend remains Vue |
| uvicorn | ASGI server | DIRECT_DEPENDENCY | Runtime server |
| aiosqlite | Existing async SQLite dependency | DIRECT_DEPENDENCY | Current migrated JobStore uses sqlite3 sync; keep until reviewed |

## Phase 12 Reuse Evaluation - Patterns + Drill Card JSON v1

Problem solved:

- `patterns` module: classify a paper's research innovation into one of 9 predefined patterns (Representation, Objective, Structure, Generation, Retrieval/Memory, Reasoning/Planning, Causal/Counterfactual, Evaluation, System Pipeline). Output: `pattern_cards.json`.
- `drill` module: generate recall/review/transfer questions and advisor probes from paper_card + formula_cards + pattern_cards. Output: `drill_cards.json`.

**Scope note**: `docs/PHASE_MAPPING.md` recommends Phase 12 = patterns + drill. The original dev doc (`03_FULL_IMPLEMENTATION_PLAN.md`) maps Phase 12 to "engineering reliability" (断点续跑/日志/缓存/安全). This discrepancy has been flagged. The reuse gate below follows the PHASE_MAPPING.md recommendation as the authoritative migration document.

Candidates checked:

| Candidate | Problem solved | Use decision | License | Notes |
|---|---|---|---|---|
| backend/patterns.py | PatternCard generation (rule-based + LLM) | REFERENCE_ONLY | N/A | Old backend code; 53 lines; uses PromptBuilder.build_pattern_prompt + LLMClient.chat_json; fallback to hardcoded Chinese. Good reference for schema and prompt design. Must not import directly. |
| backend/drill.py | DrillCard generation (rule-based + LLM) | REFERENCE_ONLY | N/A | Old backend code; 60 lines; uses PromptBuilder.build_drill_prompt + LLMClient.chat_json; fallback to hardcoded Chinese. Good reference for schema and prompt design. Must not import directly. |
| backend/schemas.py PatternCard/DrillCard | Schema definitions | REFERENCE_ONLY | N/A | Old PatternCard(card_id, pattern_id, definition, signals, transfer_template) and DrillCard(card_id, target, recall_questions, advisor_questions, error_attribution_prompts). Migrate to new schemas/cards.py. |
| py-fsrs | Spaced repetition scheduling | OPTIONAL_ADAPTER | MIT | Deferred from Phase 11; only needed if drill scheduling is implemented. Phase 12 drill is JSON generation only, no scheduling. Keep deferred. |
| promptfoo / Ragas | LLM output evaluation | NOT_USE | MIT / Apache-2.0 | Not needed for Phase 12; rule-based + mock LLM tests sufficient. |
| instructor | Structured LLM output | NOT_USE | MIT | Not needed; existing parse_llm_json + Pydantic model_validate_json already handles structured output. |
| networkx | Graph algorithms | NOT_USE | BSD-3 | Not needed for pattern classification or drill generation. |

Phase decision:

- **DIRECT_REUSE**:
  - `src/researchsensei/llm/client.py` (MockLLMClient for testing, LLMClient for LLM-enhanced path)
  - `src/researchsensei/llm/prompt_builder.py` (PromptBuilder for building pattern/drill prompts)
  - `src/researchsensei/llm/response_cache.py` (ResponseCache for caching LLM responses)
  - `src/researchsensei/llm/token_budget.py` (TokenBudget for prompt size estimation)
  - `src/researchsensei/schemas/base.py` (SenseiModel base)
  - `src/researchsensei/schemas/cards.py` (existing card schemas; will add PatternCard, DrillCard)
  - `src/researchsensei/schemas/skeleton.py` (PaperSkeleton - primary input to both modules)
  - `src/researchsensei/schemas/evidence.py` (ClaimEvidence, EvidenceIndex - evidence binding)
  - `src/researchsensei/grounding.py` (evidence_ref validation)
  - `src/researchsensei/workspace/store.py` (WorkspaceStore for artifact writing)
  - `src/researchsensei/ingestion/pipeline.py` (SinglePaperIngestionRunner - integration point)
  - Phase 8-10 card builder pattern: rule-based + LLM-enhanced + fallback + evidence binding

- **DIRECT_ADAPTER**: None needed. Patterns and drill are internal modules, not external API adapters.

- **DIRECT_DEPENDENCY**:
  - FastAPI (existing)
  - Pydantic (existing)
  - httpx (existing)
  - pytest / pytest-asyncio (existing)

- **REFERENCE_ONLY**:
  - `backend/patterns.py` — prompt design, fallback content, PatternCard schema
  - `backend/drill.py` — prompt design, fallback content, DrillCard schema
  - `backend/schemas.py` — PatternCard/DrillCard field definitions
  - `backend/pipeline.py` — integration pattern (build_paper_learning_bundle)

- **OPTIONAL_ADAPTER**:
  - py-fsrs (spaced repetition) — deferred; drill generation does not require scheduling

- **NOT_USE**:
  - promptfoo/Ragas (evaluation frameworks)
  - instructor (structured output)
  - networkx (graph algorithms)
  - New dependencies: none needed

- **New dependencies**: NONE. All required infrastructure already exists.
- **Adapters**: None needed.
- **Code development authorized**: YES (pending scope confirmation)

## Phase Gate Template

Copy this block into the report before starting a new Phase:

```markdown
## Phase X Reuse Evaluation - <phase name>

Problem solved:

Candidates checked:

| Candidate | Problem solved | Use decision | License | Stars/activity | Recent commits | Issues status | Install complexity | Windows | Local | GPU | Paid API | Chinese | Replaceability | Safety | Risk | Alternatives | Final decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ... | ... | DIRECT_DEPENDENCY / OPTIONAL_ADAPTER / REFERENCE_ONLY / NOT_USE | ... | ... | ... | ... | ... | yes/no | yes/no | yes/no | yes/no | ... | easy/medium/hard | ... | ... | ... | ... |

Phase decision:

- Reuse:
- Reference only:
- Not use:
- New dependencies:
- Adapters:
- Code development authorized: yes/no
```

## Security Notes

- LaTeX/PDF/HTML tools must be treated as untrusted input processors.
- Path traversal must be tested.
- External URLs must validate scheme, content type, and size.
- PDF scripts are not executed.
- HTML must be sanitized before rendering user or paper text.
- Prompt injection tests are required before any LLM-facing phase.
- API keys must not appear in logs, responses, artifacts, or tests.

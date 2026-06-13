# Parser 模块（M2.1）

---

## 1. 模块目标

M2.1 的目标是读取 M1 输出的 `canonical_paper.md`，校验 canonical front matter、section、paragraph、formula block，并转换成 M2 evidence pipeline 可用的 `DocumentIngestion` / `DocumentBlock`。

当前已有 ParserAdapter / LightweightParserAdapter 代码属于历史 PDF-focused / md/txt/pdf 解析能力。新的工程目标是 canonical input reader / validator。原始 PDF / LaTeX / HTML / DeepXiv / parser output 的 material normalization 前移到 M1。

## 2. 非目标

- 不直接接入 Docling / Nougat / Marker / MinerU 执行原始材料归一化；这些属于 M1 material normalization adapter
- 不新增依赖
- 不改变现有 parser 行为，除非明确迁移到 canonical reader
- web / frontend 不直接依赖 ParserAdapter
- 不执行 formula detection / FormulaOCRAdapter (these are M1 responsibilities)
- 不把 `parser_latex`、`ocr_latex`、`reconstructed` 冒充 `source_latex`

## 3. 产品流程位置

M2.1 是单篇论文理解的第一步：M1 生成 `canonical_paper.md` → M2.1 读取和校验 canonical input → M2.1 生成结构化文档 → M2.2 构建证据链路。

ParserAdapter 已接入 SinglePaperIngestionRunner（pipeline）。

职责拆分：

| 职责 | 归属 | 状态 |
|---|---|---|
| PDF / LaTeX / HTML / DeepXiv material normalization (fallback) | M1 | IMPLEMENTED |
| Body pipeline: MarkItDown / PyMuPDF / Marker text | M1 | IMPLEMENTED |
| Formula pipeline: MarkerDocumentFormulaDetector + FormulaCropper | M1 | IMPLEMENTED |
| FormulaMerger: body sections + formula slots → canonical_paper.md | M1 | IMPLEMENTED |
| MarkerDocumentFormulaDetector (build_document → Equation blocks) | M1 | IMPLEMENTED |
| FormulaCropper (PyMuPDF crop with padding) | M1 | IMPLEMENTED |
| FormulaOCRAdapter (pix2tex) | M1 | FALLBACK_ONLY (interface exists, model not integrated; used for unresolved formula crops only) |
| MinerU25ProAdapter (MinerU2.5-Pro via mineru-vl-utils) | M1 | IMPLEMENTED / UNIT_TESTED / REAL_E2E_VERIFIED |
| RuleBasedStructureRefiner + optional OllamaSectionRefiner | M1 | IMPLEMENTED / UNIT_TESTED; Ollama OPTIONAL_NOT_DEFAULT |
| M1 Quality Gate | M1 | IMPLEMENTED / UNIT_TESTED |
| `canonical_paper.md` generation | M1 | IMPLEMENTED |
| 读取 `canonical_paper.md` | M2.1 | DOC_DESIGNED / NOT_IMPLEMENTED |
| 校验 canonical front matter | M2.1 | DOC_DESIGNED / NOT_IMPLEMENTED |
| 解析 Markdown section / paragraph / formula blocks | M2.1 | DOC_DESIGNED / NOT_IMPLEMENTED |
| 生成 evidence-ready `DocumentBlock` | M2.1 | DOC_DESIGNED / NOT_IMPLEMENTED |
| 现有 md/txt/pdf LightweightParserAdapter | M2.1 legacy/current code | IMPLEMENTED |

## External Projects / Adapter Candidates

| 项目 | 对应模块 | 具体能力 | 可复用文件/函数/CLI | 接入方式 | 是否默认依赖 | 风险 | 当前状态 |
|---|---|---|---|---|---|---|---|
| LaTeXML | M1 material normalization / M2.1 canonical input source | LaTeX -> XML/HTML/MathML/JATS/TEI，保留 source_latex / MathML 结构 | `latexml`, `latexmlpost` CLI；必须调研 XML/HTML/MathML 输出字段和错误码 | OPTIONAL_ADAPTER | 否 | 安装复杂，Windows/Perl 依赖，宏展开可能失败 | RESEARCH_REQUIRED |
| pylatexenc / LatexWalker | M1 material normalization | 轻量 LaTeX AST、section、formula、citation 提取 | `pylatexenc.latexwalker.LatexWalker`, node traversal APIs | OPTIONAL_ADAPTER | 否 | 宏复杂时能力有限；不能替代完整 LaTeX 编译 | RESEARCH_REQUIRED |
| Pandoc | M1 material normalization | LaTeX / Markdown / HTML 格式转换 | `pandoc` CLI, JSON AST; 必须调研 math block / citation 输出格式 | OPTIONAL_ADAPTER | 否 | 外部二进制；公式/引用 fidelity 依赖输入质量 | RESEARCH_REQUIRED |
| MinerU | M1 material normalization | PDF/image 解析、公式转 LaTeX、表格、OCR、JSON/Markdown | MinerU CLI / API / JSON output；必须调研 formula bbox、Markdown、table 输出和 RTX 4060 8GB 可运行性 | OPTIONAL_ADAPTER | 否 | 依赖重；GPU/显存/模型下载；Windows 稳定性需验证 | RESEARCH_REQUIRED |
| Marker | M1 material normalization | PDF -> Markdown/JSON/HTML，equations、inline math、tables | Marker CLI / JSON / chunks output；必须调研 equation blocks、bbox、license 约束 | OPTIONAL_ADAPTER | 否 | GPL-3.0 / 模型许可；不能作为默认依赖 | RESEARCH_REQUIRED |
| Nougat | M1 material normalization | academic PDF -> MMD / Mathpix Markdown | `nougat` CLI, `.mmd` output；必须调研失败检测、公式输出、模型要求 | OPTIONAL_ADAPTER | 否 | 模型老、GPU 依赖、失败检测不稳定 | RESEARCH_REQUIRED |
| pix2tex / LaTeX-OCR | M1 FormulaOCRAdapter | 公式图片 -> LaTeX | `pix2tex` CLI / Python API；必须调研 image input、timeout、confidence/beam 输出 | OPTIONAL_ADAPTER | 否 | 不定位 bbox；只负责公式图像识别；GPU/模型依赖 | RESEARCH_REQUIRED |
| PyMuPDF | M1 material normalization / formula crop support | PDF 页面渲染、bbox crop、文本提取、低置信 fallback | `fitz.open`, `page.get_text`, `page.get_pixmap`, clipping/crop APIs | DIRECT_DEPENDENCY | 是 | 不识别 LaTeX 公式；fallback 不能产生高置信 formula_card | IMPLEMENTED |
| GROBID | M1 material normalization | metadata、references、citation contexts、TEI XML | GROBID service API / TEI XML；必须调研 references/citation context endpoints | OPTIONAL_ADAPTER | 否 | Java/service 依赖；不是主公式 parser | RESEARCH_REQUIRED |

## 4.5 Canonical Reader Priority

M2.1 must read `canonical_paper.md`. It no longer chooses raw-source parsers as the primary path.

1. **CanonicalPaperReader** — reads YAML front matter and Markdown body.
2. **CanonicalPaperValidator** — validates required fields, section structure, `m2_ready`, formula origin, and degradation status.
3. **CanonicalBlockBuilder** — converts sections, paragraphs, tables, figures, and formulas into `DocumentBlock`.
4. **FormulaBlockReader** — preserves `formula_id`, `formula_latex`, `formula_origin`, `formula_bbox`, `formula_page`, context, OCR status, and explanation status.

MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser. Marker is fallback/audit baseline. M1 primary-route acceptance evidence is in `reports/m1_canonical_acceptance/`.

MinerU25ProAdapter, MarkerDocumentFormulaDetector (fallback), FormulaCropper, OllamaSectionRefiner, StructureRefiner, and FormulaOCRAdapter (fallback for unresolved crops) are M1 material normalization components. M2.1 validates their canonical output.

Ollama is an optional structured refiner. Ollama must not modify latex, bbox, page, or source identity. M1 gate blocks all-formulas-in-Abstract, section contradiction, source mismatch, missing latex/crop/overlay, and dense raw-only formulas before M2.1 may accept `canonical_paper.md` for formula understanding.

## 5. 外部项目调研（详细）

### CanonicalPaperReader

- **Priority**: primary M2.1 input reader
- **Input**: `canonical_paper.md`
- **Responsible for**: YAML front matter parsing, Markdown section parsing, formula block metadata preservation, `m2_ready` validation
- **Output**: `ParserResult` / `DocumentIngestion` / `DocumentBlock`
- **Failure**: missing canonical file, malformed YAML, missing `paper_id/title/source_type/canonicalization_status`, `m2_ready=false`, formula block without `origin`
- **Decision**: DOC_DESIGNED / NOT_IMPLEMENTED.

### LaTeXSourceParser

- **Priority**: M1 material normalization adapter
- **Input**: `latex_source_path`, `latex_main_file`, `latex_aux_files`
- **Responsible for**: section/subsection hierarchy, equations and display formulas, inline formulas, labels/refs/citations, bibliography/bibtex files, theorem/algorithm/table environments, formula source text
- **Candidate tools**:
  - **LaTeXML**: candidate for LaTeX → XML/HTML/MathML/JATS/TEI conversion. Preferred for semantic XML/HTML/MathML if install/runtime is acceptable.
  - **pylatexenc / LatexWalker**: candidate for lightweight LaTeX AST parsing. Preferred for lightweight extraction of sections/formulas/citations if LaTeXML is too heavy.
  - **Pandoc**: candidate for LaTeX → Markdown/HTML conversion.
- **Decision**: OPTIONAL_ADAPTER, DOC_DESIGNED / NOT_IMPLEMENTED. LaTeX source parsing writes `canonical_paper.md` in M1, not raw M2 parser output.

### Docling

- **GitHub**: `docling-project/docling`
- **主要能力**: 多格式文档解析，支持 PDF/DOCX/PPTX/XLSX/HTML/images/LaTeX/plain text
- **核心表示**: 统一 `DoclingDocument` 表示
- **导出格式**: Markdown / HTML / DocTags / lossless JSON
- **典型调用**: `DocumentConverter().convert(source)` → `result.document.export_to_markdown()`
- **安装复杂度**: 中等（`pip install docling`）
- **是否适合默认依赖**: 否 — 依赖和集成面较大，保持 OPTIONAL_ADAPTER
- **Adapter output mapping**: `DoclingDocument` / Markdown / JSON → `canonical_paper.md` sections and formula blocks in M1
- **当前状态**: DOC_DESIGNED / NOT_IMPLEMENTED

### Marker

- **GitHub**: `datalab-to/marker`
- **主要能力**: PDF 转 Markdown / JSON / chunks / HTML，支持 tables / forms / equations / inline math / links / references / code blocks
- **输出格式**: Markdown / JSON / chunks / HTML
- **可选 LLM 模式**: 有，但 Marker LLM 增强不在 M2.1 默认路径中
- **许可证风险**: 代码 GPL-3.0，模型许可另有限制，商用/分发前必须确认
- **是否适合默认依赖**: 否 — 许可证和依赖风险，不适合默认依赖
- **Adapter output mapping**: Marker JSON / chunks → `canonical_paper.md` sections and formula blocks in M1
- **当前状态**: DOC_DESIGNED / NOT_IMPLEMENTED

### MinerU

- **GitHub**: `opendatalab/MinerU`
- **主要能力**: PDF/image/DOCX/PPTX/XLSX 解析，公式转 LaTeX、表格转 HTML、OCR、FastAPI/Gradio、CPU/GPU/MPS
- **输出格式**: Markdown、按阅读顺序排序的 JSON、中间格式
- **安装复杂度**: 较重
- **优先级**: 首选 PDF-only parser，用于公式/表格密集论文
- **必须评估**: 是否可在 RTX 4060 8GB VRAM 上运行、inline/display formula 输出、table 输出、section hierarchy、速度和内存
- **Adapter output mapping**: MinerU JSON / Markdown → `canonical_paper.md` sections, formula bbox, table blocks in M1
- **当前状态**: DOC_DESIGNED / NOT_IMPLEMENTED

### GROBID

- **GitHub**: `kermitt2/grobid`
- **主要能力**: PDF 元数据提取、参考文献解析、引用上下文
- **输出格式**: TEI XML
- **优先级**: 用于 metadata/references/citation contexts，不足以单独支撑深度阅读
- **Adapter output mapping**: GROBID TEI → canonical references / citation contexts in M1
- **当前状态**: DOC_DESIGNED / NOT_IMPLEMENTED

### PyMuPDF

- **文档**: `pymupdf.readthedocs.io`
- **主要能力**: PDF 文本提取
- **优先级**: fallback only，不能产生高置信 formula_cards
- **限制**: 不做 LaTeX 公式识别，不做结构化 section 解析

### Nougat

- **GitHub**: `facebookresearch/nougat`
- **主要能力**: academic document PDF parser，擅长 LaTeX math 和 tables
- **输出格式**: `.mmd` / Mathpix Markdown 风格
- **安装**: `pip install nougat-ocr`
- **风险**: GPU / PyTorch / 模型依赖，失败检测有不稳定可能
- **是否适合当前接入**: 否 — 需要 GPU，不适合默认安装
- **Adapter output mapping**: `.mmd` → `canonical_paper.md` formula blocks and sections in M1
- **当前状态**: DOC_DESIGNED / NOT_IMPLEMENTED

## 6. 当前代码位置

- `src/researchsensei/parser/adapter.py` — `ParserAdapter` abstract base
- `src/researchsensei/parser/lightweight_adapter.py` — `LightweightParserAdapter`
- `src/researchsensei/ingestion/lightweight.py` — `LightweightIngestionService`
- `src/researchsensei/schemas/document.py` — `ParserResult`, `ParseMetadata`, `DocumentBlock`
- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner`（ParserAdapter 注入点）

## 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `canonical_paper.md`, `str paper_id` |
| 输出 | `ParserResult`（包含 `DocumentIngestion` + `ParseMetadata`） |
| 不生成 paper_id | 调用者传入 |
| 不写 artifact | 只返回 ParserResult |
| 不更新 job | — |
| 不调用 LLM | — |
| 不联网 | — |

Required front matter:
- `paper_id`
- `title`
- `authors`
- `year`
- `venue`
- `source_type`
- `source_confidence`
- `canonicalization_status`
- `parser_used`
- `m2_ready`
- `degradation_reason`

Blocked input:
- missing front matter
- malformed YAML
- `source_type == metadata_only`
- `m2_ready=false` without explicit override
- formula block without `origin`
- canonical body missing both abstract and body text

## 8. Artifact

- ParserAdapter 本身不直接写 artifact。
- `parsed_document.json` 由 pipeline / workspace 写入。
- `canonical_paper.md` is retained as the M1 input artifact and must be referenced by `parsed_document.json`.
- Parser 层新增字段必须兼容旧 `parsed_document.json`。
- artifact 应显式 `schema_version="v2"`；旧 artifact 无 `schema_version` 时按 v1 读取。
- additive 字段通过默认值兼容，不需要 migration。

### canonical reader constraints

- M2.1 primary path is `canonical_paper.md`.
- M2.1 cannot bypass M1 to read raw PDF / LaTeX / HTML / DeepXiv.
- All external parser/layout/OCR outputs must already be represented in canonical Markdown by M1.
- M2.1 cannot silently repair missing formula origin.
- Invalid canonical input must produce `BLOCKED_UNDERSTANDING`.

### 2026-06-14 implementation update

- Implemented canonical bundle ingestion in `src/researchsensei/m2/full_pipeline.py`.
- CLI entry: `python scripts/m2_run_understanding.py --mode full --input-dir <m1_dir> --output-dir <m2_dir>`.
- The full path reads only M1 artifacts through `M1ArtifactReader`; it does not read or mutate raw PDF.
- M1 formula slot fields propagated into `DocumentBlock`: `formula_id`, `formula_latex`, `formula_origin`, `formula_bbox`, `formula_page`, `formula_context_before`, `formula_context_after`, `formula_ocr_status`, `formula_explanation_status`, crop path, overlay path, source, and risk flags.
- Suppressed M1 layout noise before evidence construction: repeated page headers, page-number footers, author footers, funding/front-matter affiliation blocks.
- Current real verification: `2312_01729v1` M1 PASS -> M2 full SUCCESS with real Mimo LLM and QualityAuditor.
- Remaining limitation: this is verified on one current clean paper; multi-paper MinerU acceptance and survey-paper behavior remain pending.

## 9. Schema / 数据结构

### ParseMetadata / ParserResult

```python
class ParseMetadata(SenseiModel):
    parser_name: str
    parser_version: str = ""
    source_format: str = ""
    page_count: int = 0
    extra: dict = Field(default_factory=dict)
    # source-aware fields
    parser_input_type: str = "canonical_paper.md"
    parser_adapter: str = "canonical_paper_reader"
    formula_fidelity: str = "unknown"  # source_latex | parser_latex | ocr_latex | reconstructed | unknown
    source_level_formula_available: bool = False
    latex_parse_status: str = "not_applicable"  # not_applicable | parsed | partial | failed
    latex_parse_warnings: list[str] = Field(default_factory=list)
    canonicalization_status: str = ""
    m2_ready: bool = False
    degradation_reason: list[WarningItem] = Field(default_factory=list)

class ParserResult(SenseiModel):
    document: DocumentIngestion
    metadata: ParseMetadata
```

### DocumentBlock 扩展字段

```python
class DocumentBlock(SenseiModel):
    # 现有字段不变
    block_id: str
    type: BlockType
    text: str
    evidence_ref: str
    section: str = ""
    page: int | None = None
    normalized_text: str = ""
    offset_start: int = 0
    offset_end: int = 0
    raw_latex: str = ""
    # 新增 Optional 字段（向后兼容）
    bbox: tuple[float, float, float, float] | None = None
    table_html: str = ""
    figure_caption: str = ""
    reference_entries: list[str] = Field(default_factory=list)
    formula_id: str = ""
    formula_latex: str = ""
    formula_origin: str = ""  # source_latex | parser_latex | ocr_latex | reconstructed | unknown
    formula_bbox: tuple[float, float, float, float] | None = None
    formula_page: int | None = None
    formula_context_before: str = ""
    formula_context_after: str = ""
    formula_ocr_status: str = ""
    formula_explanation_status: str = ""
    # M1 pipeline fields (consumed from canonical_paper.md front matter / formula_slots.json)
    block_source: str = ""           # mineru25pro | marker_document | ocr | latex_source
    section_confidence: str = ""     # high | medium | low
    risk_flags: list[str] = Field(default_factory=list)  # SECTION_CONTRADICTION, ABSTRACT_OVERLOAD, etc.
    crop_path: str = ""              # path to cropped formula image
    overlay_path: str = ""           # path to overlay image
    parse_quality_status: str = ""   # PASS | DEGRADED | BLOCKED
    fallback_used: bool = False      # true if Marker fallback was used instead of MinerU
    llama_refined: bool = False      # true if LlamaSectionRefiner was applied
    mineru_available: bool = False   # true if MinerU2.5-Pro was available
    structure_audit_status: str = "" # PASS | WARNING | BLOCKED
```

### ParserAdapter

```python
from abc import ABC, abstractmethod
from pathlib import Path

class ParserAdapter(ABC):
    @abstractmethod
    def supports(self, source: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> ParserResult:
        raise NotImplementedError
```

```python
class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None: ...
    def supports(self, source: Path) -> bool: ...
    def parse(self, source: Path, paper_id: str) -> ParserResult: ...
    # 内部调用 self.ingestion.ingest_path(source, paper_id)
    # 返回 ParserResult(document=document, metadata=ParseMetadata(parser_name="lightweight"))
```

## 10. 错误/失败策略

| 错误 | 行为 |
|------|------|
| 不支持的文件类型 | `supports()` 返回 False |
| 源文件不存在 | 沿用 LightweightIngestionService 行为 |
| 空文件 | `degraded=True`, `NO_TEXT_EXTRACTED` |
| PDF 解析失败 | `degraded=True`, `PDF_PARSE_FAILED` |
| canonical_paper.md 缺失 | `BLOCKED_UNDERSTANDING`, `CANONICAL_INPUT_MISSING` |
| front matter 缺必填字段 | `BLOCKED_UNDERSTANDING`, `CANONICAL_FRONT_MATTER_INVALID` |
| m2_ready=false | `BLOCKED_UNDERSTANDING`, `M2_NOT_READY` |
| metadata_only 输入 | `BLOCKED_UNDERSTANDING`, `METADATA_ONLY_NOT_ALLOWED` |
| formula block 缺 origin | `DEGRADED_STRUCTURAL` 或 `BLOCKED_UNDERSTANDING`，取决于是否影响核心公式 |
| formula_origin unknown | 允许正文证据链，详细公式推导 blocked |
| HIGH risk in risk_flags | `BLOCKED_UNDERSTANDING`, quality gate failed |
| section_contradiction in risk_flags | `BLOCKED_UNDERSTANDING` or `DEGRADED_STRUCTURAL` depending on severity |
| formula_latex_empty | `BLOCKED_UNDERSTANDING` for core formulas |
| source_mismatch | `BLOCKED_UNDERSTANDING`, wrong paper |
| parse_quality_status=BLOCKED | `BLOCKED_UNDERSTANDING` |
| canonical_quality_status != PASS | `BLOCKED_UNDERSTANDING` or degraded mode |
| fallback_used=true | INFO level, does not block M2 but must be recorded |
| llama_refined=true | INFO level, must record model name and JSON valid count |

## 11. 测试要求

### ParserAdapter 接口测试

| 测试 | 断言 |
|------|------|
| test_parser_adapter_is_abstract | ParserAdapter() raises TypeError |
| test_parser_adapter_requires_subclass | cannot instantiate without implementing abstract methods |

### LightweightParserAdapter 测试

| 测试 | 断言 |
|------|------|
| test_lightweight_adapter_supports_md_txt_pdf | .md/.txt/.pdf → True; .markdown/.docx → False |
| test_lightweight_adapter_returns_parser_result | result is ParserResult, document is DocumentIngestion |
| test_lightweight_adapter_matches_original_output | output matches LightweightIngestionService |
| test_lightweight_adapter_propagates_degraded | broken PDF → degraded=True, warning code |
| test_lightweight_adapter_uses_injected_service | injected service called correctly |
| test_lightweight_adapter_does_not_write_artifacts | no json files created |

### Schema round-trip 测试

| 测试 | 断言 |
|------|------|
| test_parser_result_json_round_trip | ParserResult serialize → deserialize preserves all fields |
| test_parse_metadata_defaults | default values correct |
| test_document_block_new_fields_round_trip | bbox/table_html/figure_caption/reference_entries preserved |
| test_document_block_new_fields_backward_compatible | old JSON without new fields → defaults |

### Pipeline 集成测试

| 测试 | 断言 |
|------|------|
| test_parser_adapter_injected_into_runner | runner uses adapter correctly |
| test_unsupported_source_marks_job_failed | unsupported file type → job status FAILED or degraded |

### CanonicalPaperReader / Validator 测试

| 测试 | 断言 |
|------|------|
| test_canonical_reader_reads_front_matter | reads required YAML fields |
| test_canonical_reader_builds_sections | Markdown sections become DocumentBlock sections |
| test_canonical_reader_preserves_formula_block | formula_id/formula_latex/formula_origin/page/bbox preserved |
| test_canonical_reader_blocks_metadata_only | source_type=metadata_only → BLOCKED_UNDERSTANDING |
| test_canonical_reader_blocks_missing_origin | formula block without origin → degraded or blocked |
| test_canonical_reader_blocks_m2_not_ready | m2_ready=false → BLOCKED_UNDERSTANDING |
| test_formula_origin_round_trip | source_latex/parser_latex/ocr_latex/reconstructed/unknown preserved |
| test_formula_ocr_status_round_trip | formula_ocr_status preserved |

### 全局规则

- Parser 接口 / schema round-trip 可以作为本地结构检查，但不能作为 M2.1 验收
- M2.1 验收必须使用 M1 生成的真实 `canonical_paper.md` 输入，验证 parsed_document.json、warning、degraded 状态、parser metadata、formula_origin
- 不调用 LLM（parser 不需要 LLM）

## 12. 验收标准

- ParserAdapter 接口抽象，不绑定具体 parser
- LightweightParserAdapter 输出与原 LightweightIngestionService 一致
- CanonicalPaperReader 读取 `canonical_paper.md`
- CanonicalPaperValidator 校验 front matter、m2_ready、formula_origin
- CanonicalBlockBuilder 输出 evidence-ready DocumentBlock
- ParserResult 包含 DocumentIngestion + ParseMetadata
- DocumentBlock 扩展字段向后兼容
- 外部 parser 不能直接写 artifact
- 真实验收必须走 M1 canonicalization → M2.1 canonical reader；PDF-focused path 只能证明当前 legacy/parser 能力，不能证明 canonical input reader 完成

## 13. 当前实现状态

- 代码已实现：ParserAdapter, LightweightParserAdapter, ParserResult, ParseMetadata
- DocumentBlock 已扩展 Optional 字段（bbox, table_html, figure_caption, reference_entries）
- pipeline 已接入（ParserAdapter 注入 SinglePaperIngestionRunner）
- 测试已覆盖：11+ tests
- 当前未实现：CanonicalPaperReader, CanonicalPaperValidator, CanonicalBlockBuilder
- 当前未实现：formula_id/formula_latex/formula_origin/formula_bbox/formula_page/formula_context_before/formula_context_after/formula_ocr_status/formula_explanation_status 全链路
- DoclingParserAdapter 未实现
- 外部 parser / OCR / layout detector 均为 DOC_DESIGNED / NOT_IMPLEMENTED adapter，归属 M1 material normalization

## 14. External Reference Implementation Notes

- **Reference source**: ARIS `skills/research-lit/SKILL.md` (paper reading flow), `skills/idea-discovery/SKILL.md` (reference paper summary)
- **Reference use**: DO_NOT_REUSE for parser, EVALUATE_OTHER_PROJECTS for parser quality
- **Borrowed behavior**: Only borrows "title / abstract / intro / method overview" initial reading order
- **ResearchSensei-owned target**: `parsed_paper.json`, `section_blocks`, `passage_blocks`, `formula_blocks`
- **Schema / artifact impact**: DocumentBlock fields (block_id, type, text, section, bbox, table_html, figure_caption, reference_entries, formula_id, formula_latex, formula_origin, formula_ocr_status)
- **Boundary**: ARIS is not a dedicated parser. ARIS cannot replace canonical input reader. Docling / Marker / MinerU / DeepXiv belong to M1 adapter evaluation and must write canonical Markdown before M2.
- **Validation implication**: M2.1 validation must use real M1-generated `canonical_paper.md`. Synthetic markdown is not acceptance. Must output section / passage / formula structure.

## 15. Survey Paper Support

M2.1 Parser should support two types of papers:

### Ordinary Research Paper

Parser preserves:
- sections
- passages
- formulas
- tables
- figures
- datasets
- baselines
- compared_methods
- limitation_statements
- future_work_statements
- method_family_clues

### Survey / Review Paper

Parser additionally preserves:
- taxonomy_sections
- method_family_sections
- survey_tables
- reference_clusters
- historical_or_chronological_sections

Status: NOT_IMPLEMENTED

## 16. 当前未解决问题

- Docling 本地样例验证需要哪些论文
- 外部 parser 映射细节（DoclingDocument / Marker JSON / MinerU JSON / DeepXiv structured output → canonical_paper.md）
- 重依赖隔离策略（Docling/MinerU 的依赖不污染主项目）
- ParserAdapter 接口是否需要 `supports()` 还是只靠构造函数选择
- CanonicalPaperReader 是否沿用 ParserAdapter 抽象，还是独立 `CanonicalInputReader` 接口

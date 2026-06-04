# Parser 模块（M2.1）

---

## 1. 模块目标

设计 ParserAdapter interface，包装现有 parser 为 default adapter，为未来接入高质量外部 parser 留接口。

## 2. 非目标

- 不接入 Docling / Nougat / Marker / MinerU（只留接口）
- 不新增依赖
- 不改变现有 parser 行为
- web / frontend 不直接依赖 ParserAdapter

## 3. 产品流程位置

M2.1 是单篇论文理解的第一步：用户上传论文 → M2.1 解析为结构化文档 → M2.2 构建证据链路。

ParserAdapter 已接入 SinglePaperIngestionRunner（pipeline）。

## 4. 可复用开源项目 / 外部服务调研

| 项目 | 用途 | GitHub / 官网 | 接入方式 | 是否默认依赖 | 风险 | 当前结论 |
|------|------|---------------|----------|--------------|------|----------|
| Docling | 多格式文档解析 | github.com/docling-project/docling | OPTIONAL_ADAPTER | 否 | 依赖较重 | 第一个候选外部 parser |
| MinerU | PDF/image 解析 | github.com/opendatalab/MinerU | OPTIONAL_ADAPTER | 否 | 依赖重 | 暂不接入 |
| Marker | PDF 转 Markdown | github.com/datalab-to/marker | OPTIONAL_ADAPTER | 否 | GPL-3.0 license | 暂不接入 |
| Nougat | 学术 PDF 解析 | github.com/facebookresearch/nougat | OPTIONAL_ADAPTER | 否 | GPU 依赖 | 暂不接入 |

未完成调研不得进入代码开发。

## 5. 外部项目调研（详细）

### Docling

- **GitHub**: `docling-project/docling`
- **主要能力**: 多格式文档解析，支持 PDF/DOCX/PPTX/XLSX/HTML/images/LaTeX/plain text
- **核心表示**: 统一 `DoclingDocument` 表示
- **导出格式**: Markdown / HTML / DocTags / lossless JSON
- **典型调用**: `DocumentConverter().convert(source)` → `result.document.export_to_markdown()`
- **安装复杂度**: 中等（`pip install docling`）
- **是否适合当前接入**: 否 — 依赖和集成面较大，先保持 optional adapter
- **未来 adapter 映射**: `DoclingDocument` / Markdown / JSON → `DocumentIngestion.blocks`

### Marker

- **GitHub**: `datalab-to/marker`
- **主要能力**: PDF 转 Markdown / JSON / chunks / HTML，支持 tables / forms / equations / inline math / links / references / code blocks
- **输出格式**: Markdown / JSON / chunks / HTML
- **可选 LLM 模式**: 有，但默认测试不能用真实 LLM
- **许可证风险**: 代码 GPL-3.0，模型许可另有限制，商用/分发前必须确认
- **是否适合当前接入**: 否 — 许可证和依赖风险，不适合默认依赖
- **未来 adapter 映射**: Marker JSON / chunks → `DocumentIngestion.blocks`

### MinerU

- **GitHub**: `opendatalab/MinerU`
- **主要能力**: PDF/image/DOCX/PPTX/XLSX 解析，公式转 LaTeX、表格转 HTML、OCR、FastAPI/Gradio、CPU/GPU/MPS
- **输出格式**: Markdown、按阅读顺序排序的 JSON、中间格式
- **安装复杂度**: 较重
- **是否适合当前接入**: 否 — 能力强但系统复杂，先作为 optional parser backend
- **未来 adapter 映射**: MinerU JSON / Markdown → `DocumentIngestion.blocks`

### Nougat

- **GitHub**: `facebookresearch/nougat`
- **主要能力**: academic document PDF parser，擅长 LaTeX math 和 tables
- **输出格式**: `.mmd` / Mathpix Markdown 风格
- **安装**: `pip install nougat-ocr`
- **风险**: GPU / PyTorch / 模型依赖，失败检测有不稳定可能
- **是否适合当前接入**: 否 — 需要 GPU，不适合默认安装
- **未来 adapter 映射**: `.mmd` → `DocumentIngestion.blocks`，公式块尽量保留

## 6. 当前代码位置

- `src/researchsensei/parser/adapter.py` — `ParserAdapter` abstract base
- `src/researchsensei/parser/lightweight_adapter.py` — `LightweightParserAdapter`
- `src/researchsensei/ingestion/lightweight.py` — `LightweightIngestionService`
- `src/researchsensei/schemas/document.py` — `ParserResult`, `ParseMetadata`, `DocumentBlock`
- `src/researchsensei/ingestion/pipeline.py` — `SinglePaperIngestionRunner`（ParserAdapter 注入点）

## 7. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `Path source`, `str paper_id` |
| 输出 | `ParserResult`（包含 `DocumentIngestion` + `ParseMetadata`） |
| 不生成 paper_id | 调用者传入 |
| 不写 artifact | 只返回 ParserResult |
| 不更新 job | — |
| 不调用 LLM | — |
| 不联网 | — |

## 8. Artifact

- ParserAdapter 本身不直接写 artifact。
- `parsed_document.json` 由 pipeline / workspace 写入。
- Parser 层新增字段必须兼容旧 `parsed_document.json`。
- v2 artifact 应显式 `schema_version="v2"`；旧 artifact 无 `schema_version` 时按 v1 读取。
- additive 字段通过默认值兼容，不需要 migration。

### 外部 parser 约束

- 所有外部 parser 都必须通过 `ParserAdapter` 输出 `ParserResult`
- 外部 parser 不能直接写 artifact，不能绕过 `DocumentIngestion`
- 外部 parser 的结构化输出（bbox、table_html 等）通过 `DocumentBlock` 扩展字段保留

## 9. Schema / 数据结构

### ParseMetadata / ParserResult

```python
class ParseMetadata(SenseiModel):
    parser_name: str
    parser_version: str = ""
    source_format: str = ""
    page_count: int = 0
    extra: dict = Field(default_factory=dict)

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

### 全局规则

- 快速回归可使用 mock，不作为模块验收依据
- 真实验收必须使用真实 PDF 输入（不能只用 synthetic markdown）
- 不调用 LLM（parser 不需要 LLM）

## 12. 验收标准

- ParserAdapter 接口抽象，不绑定具体 parser
- LightweightParserAdapter 输出与原 LightweightIngestionService 一致
- ParserResult 包含 DocumentIngestion + ParseMetadata
- DocumentBlock 扩展字段向后兼容
- 外部 parser 不能直接写 artifact
- 真实验收必须真实解析 PDF（通过 real PDF e2e eval）

## 13. 当前实现状态

- 代码已实现：ParserAdapter, LightweightParserAdapter, ParserResult, ParseMetadata
- DocumentBlock 已扩展 Optional 字段（bbox, table_html, figure_caption, reference_entries）
- pipeline 已接入（ParserAdapter 注入 SinglePaperIngestionRunner）
- 测试已覆盖：11+ tests
- DoclingParserAdapter 未实现
- 外部 parser 仍是 optional adapter

## 14. 当前未解决问题

- Docling 本地样例验证需要哪些论文
- 外部 parser 映射细节（DoclingDocument → DocumentIngestion.blocks）
- 重依赖隔离策略（Docling/MinerU 的依赖不污染主项目）
- ParserAdapter 接口是否需要 `supports()` 还是只靠构造函数选择

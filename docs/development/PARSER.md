# Parser 模块

---

## 1. 模块目标

设计 ParserAdapter interface，包装现有 parser 为 default adapter，为未来接入高质量外部 parser 留接口。

## 2. 非目标

- 不接入 Docling / Nougat / Marker / MinerU（只留接口）
- 不新增依赖
- 不改变现有 parser 行为
- 不改 pipeline / web / frontend / backend

## 3. 外部项目调研

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

## 4. 当前代码位置

- `src/researchsensei/ingestion/lightweight.py` — `LightweightIngestionService`
- 入口方法：`ingest_path(path: str | Path, paper_id: str | None = None) -> DocumentIngestion`
- 支持：`.md`, `.txt`, `.pdf`
- 降级：不支持的文件类型 → `degraded=True`, `UNSUPPORTED_FILE_TYPE`
- PDF 失败 → `degraded=True`, `PDF_PARSE_FAILED`
- 空文件 → `degraded=True`, `NO_TEXT_EXTRACTED`

## 5. 输入输出

| 项 | 值 |
|----|-----|
| 输入 | `Path source`, `str paper_id` |
| 输出 | `DocumentIngestion` |
| 不生成 paper_id | 调用者传入 |
| 不写 artifact | 只返回 DocumentIngestion |
| 不更新 job | — |
| 不调用 LLM | — |
| 不联网 | — |

## 6. Artifact

- 不新增 artifact
- 不修改现有 artifact 格式
- `parsed_document.json` 格式不变

## 7. 核心类和方法签名

```python
# src/researchsensei/parser/adapter.py
from abc import ABC, abstractmethod
from pathlib import Path
from researchsensei.schemas.document import DocumentIngestion

class ParserAdapter(ABC):
    @abstractmethod
    def supports(self, source: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion:
        raise NotImplementedError
```

```python
# src/researchsensei/parser/lightweight_adapter.py
class LightweightParserAdapter(ParserAdapter):
    def __init__(self, ingestion: LightweightIngestionService | None = None) -> None: ...
    def supports(self, source: Path) -> bool: ...
    def parse(self, source: Path, paper_id: str) -> DocumentIngestion: ...
```

## 8. 错误/失败策略

| 错误 | 行为 |
|------|------|
| 不支持的文件类型 | `supports()` 返回 False |
| 源文件不存在 | 沿用 LightweightIngestionService 行为 |
| 空文件 | `degraded=True`, `NO_TEXT_EXTRACTED` |
| PDF 解析失败 | `degraded=True`, `PDF_PARSE_FAILED` |

## 9. 测试断言

**test_parser_adapter_is_abstract**
- Arrange: import ParserAdapter
- Act: call ParserAdapter()
- Assert: raises TypeError

**test_lightweight_adapter_supports_md_txt_pdf**
- Arrange: create LightweightParserAdapter
- Act: call supports() on paper.md, paper.txt, paper.pdf, paper.MD, paper.TXT, paper.PDF, paper.markdown, paper.docx
- Assert: first six return True, paper.markdown is False, paper.docx is False

**test_lightweight_adapter_matches_original_output**
- Arrange: create tmp markdown file with abstract/method/experiments/formula, create LightweightIngestionService, create LightweightParserAdapter
- Act: original = service.ingest_path(path, paper_id="p1"), adapted = adapter.parse(path, paper_id="p1")
- Assert: paper_id equal, detected_language equal, degraded equal, warning count equal, warning code/message equal, block count equal, each block block_id/type/section/text/evidence_ref equal

**test_lightweight_adapter_json_round_trip**
- Arrange: parse tmp markdown
- Act: model_dump_json then model_validate_json
- Assert: paper_id/block count/degraded/warnings preserved

**test_lightweight_adapter_does_not_write_artifacts**
- Arrange: create tmp source file
- Act: adapter.parse(...)
- Assert: no *.json artifact files created, no workspace/runs directory created, adapter only returns DocumentIngestion

**test_lightweight_adapter_uses_injected_service**
- Arrange: create fake service with ingest_path(), inject into LightweightParserAdapter
- Act: call parse
- Assert: fake service called once, path and paper_id passed correctly, returned object is fake result

**test_lightweight_adapter_propagates_degraded**
- Arrange: create broken PDF bytes
- Act: adapter.parse(...)
- Assert: result.degraded is True, warning code contains PDF_PARSE_FAILED or PYMUPDF_MISSING

## 10. Hard-Fail

- 新增依赖
- 修改现有 ingestion
- 输出不兼容
- 测试只测字段存在、不比较内容
- 默认 pytest 真实联网 / LLM

## 11. 当前未解决问题

- 已完成初步 GitHub README 级调研；正式接入前仍需本地安装验证和样例 PDF 对比
- ParserAdapter 接口是否需要 `supports()` 还是只靠构造函数选择

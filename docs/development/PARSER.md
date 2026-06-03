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

- **GitHub**: `ds4sd/docling`
- **主要能力**: PDF/layout/table/structured document conversion，支持多种文档格式
- **输出格式**: 结构化 JSON（pages, blocks, tables, figures）
- **安装复杂度**: 中等（pip install docling）
- **是否适合当前接入**: 否 — 依赖较重，当前只需 Markdown/TXT/PDF fallback
- **未来接入方式**: 通过 ParserAdapter 接口，`DoclingParserAdapter(ParserAdapter)` 实现 `supports()` 和 `parse()`

### Marker

- **GitHub**: `VikParuchuri/marker`
- **主要能力**: PDF/Markdown 转换，速度较快
- **输出格式**: Markdown 文本
- **安装复杂度**: 较轻量
- **是否适合当前接入**: 否 — 输出是 Markdown，需要额外解析成 blocks
- **未来接入方式**: 通过 ParserAdapter 接口

### MinerU

- **GitHub**: `opendatalab/MinerU`
- **主要能力**: PDF 解析/OCR/layout 分析
- **输出格式**: 结构化 JSON
- **安装复杂度**: 较重
- **是否适合当前接入**: 否 — 依赖重
- **未来接入方式**: 通过 ParserAdapter 接口

### Nougat

- **GitHub**: `facebookresearch/nougat`
- **主要能力**: scientific PDF / math-aware parsing
- **输出格式**: Markdown（含 LaTeX 公式）
- **安装复杂度**: 需要 GPU
- **是否适合当前接入**: 否 — 需要 GPU，不适合默认安装
- **未来接入方式**: 通过 ParserAdapter 接口

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

| 测试 | 断言 |
|------|------|
| test_parser_adapter_is_abstract | `ParserAdapter()` raises TypeError |
| test_lightweight_adapter_supports_md_txt_pdf | .md/.txt/.pdf=True, .MD/.TXT/.PDF=True, .markdown/.docx=False |
| test_lightweight_adapter_matches_original_output | 字段逐个比较：paper_id, detected_language, degraded, warnings, blocks |
| test_lightweight_adapter_json_round_trip | dump → validate round-trip |
| test_lightweight_adapter_does_not_write_artifacts | 无 *.json 文件写入 |
| test_lightweight_adapter_uses_injected_service | 注入的 service 被调用 |
| test_lightweight_adapter_propagates_degraded | broken PDF → degraded=True, PDF_PARSE_FAILED |

## 10. Hard-Fail

- 新增依赖
- 修改现有 ingestion
- 输出不兼容
- 测试只测字段存在、不比较内容
- 默认 pytest 真实联网 / LLM

## 11. 当前未解决问题

- 外部 parser 项目未真正调研安装方式和输出格式
- ParserAdapter 接口是否需要 `supports()` 还是只靠构造函数选择

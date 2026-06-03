# ResearchSensei v0.5

## 安装与测试环境

本项目使用项目级虚拟环境，避免把依赖安装到全局 Python 或 conda 环境。

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

FastAPI 标准文件上传接口依赖 `python-multipart`，该依赖已记录在 `pyproject.toml`，不要只做本机临时安装。

`.venv/` 已加入 `.gitignore`，不要提交虚拟环境目录。

ResearchSensei 是一个本地单用户科研理解训练系统。它不是论文摘要器，而是面向“还没有稳定科研思维框架的人读博”的学习工作台：先筛出少量高质量论文，再把全文证据、论文骨架、公式、科研模式和导师追问串成可复述、可迁移的学习闭环。

## 当前架构

新架构的主包在 `src/researchsensei/`。旧 `research_sensei/` 暂时保留为迁移来源，不再作为 v0.5 的主要扩展入口。

核心流水线：

```text
方向模式:
query -> acquisition -> selection -> source_resolver -> ingestion
      -> grounding -> understanding -> teaching/formula/pattern/drill
      -> render -> interactive

单篇模式:
PDF/LaTeX/text -> ingestion -> grounding -> understanding
               -> cards -> interactive
```

## v0.5 已落地内容

- `docs/`：产品需求、复用报告、模块契约、实施计划、验收标准、评审清单、术语表。
- `src/researchsensei/schemas.py`：统一 Pydantic 契约。
- `query`：把用户问题转成 `QueryPlan`。
- `selection`：把候选论文转成带角色、质量评分、阅读优先级的 `ReadingPlan`。
- `ingestion`：把文本解析成统一 `DocumentBlock`。
- `grounding`：生成 `EvidenceIndex`，明确证据类型。
- `understanding`：生成 `PaperSkeleton`。
- `teaching/formula/pattern/drill`：生成论文卡、公式卡、模式卡和训练卡。
- `interactive/context/llm`：追问时携带当前卡片、选中文本、证据块和历史摘要，不发送整篇论文。
- `render/web`：三栏学习工作台基础页面和 FastAPI 入口。
- `pipeline.py`：最小垂直闭环协调器。
- `outputs/sample/`：`Attention Is All You Need` 黄金样例骨架。

## 运行

```powershell
pytest -q
python -m researchsensei.web.run
```

默认地址：

```text
http://127.0.0.1:8765
```

## 复用边界

ResearchSensei 不自研成熟基础设施：

- 论文搜索、多源聚合、PDF 下载、DOI 回填、去重；
- PDF 解析、章节抽取、公式渲染、文献引用解析；
- 通用 RAG、向量检索、证据型 QA；
- 工作流编排、图表渲染、HTML 模板引擎；
- 间隔复习算法、LLM/RAG 评测框架。

本项目自研的是学习与科研思维框架：

- Teach-Me Engine；
- Formula Tutor；
- Research Pattern Library；
- PhD Thinking Scaffold；
- Learning Card Schema；
- Direction Curator Rules；
- 交互追问上下文协议。

## 配置

现有配置仍在 `config/` 和 `.env` 中。v0.5 后续会把旧配置迁移到统一 `ConfigService`，并继续支持 DeepSeek、MiMo 和任意 OpenAI-compatible provider。

常用启动参数保持：

```toml
[server]
host = "127.0.0.1"
port = 8765
reload = false
```

## 验收重点

第一版不是“看起来能生成文本”就算合格，而是必须满足：

- A_READ 不超过规则上限，弱相关论文不进入深读；
- 每个事实性 claim 都能回连 evidence 或标注需要人工核验；
- 公式卡包含符号、每项作用、小数字例子、删项影响；
- 追问时带上下文包，不把整篇论文塞进 prompt；
- UI 以左目录、中学习区、右追问区为核心；
- 黄金样例可用于回归检查。

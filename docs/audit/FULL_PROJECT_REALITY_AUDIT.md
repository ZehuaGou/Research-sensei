# ResearchSensei 全项目现实审计

> 审计日期：2026-06-04
> 审计基准：commit f4431f7
> 审计方法：代码阅读 + grep 扫描 + 真实 live eval 运行 + 人工判断

---

## 状态等级定义

| 等级 | 含义 |
|------|------|
| NOT_STARTED | 无代码、无文档 |
| DOC_ONLY | 有文档、无代码 |
| MOCK_TESTED | 有代码、mock 测试通过、无真实验收 |
| THIN_WRAPPER_ONLY | 代码只是对单个 API/库的薄封装，无成熟项目接入 |
| LIVE_SEARCH_VERIFIED | 真实联网搜索已验证 |
| REAL_API_VERIFIED | 真实 API（非搜索）已验证 |
| REAL_PDF_VERIFIED | 真实 PDF 下载 + 解析已验证 |
| REAL_LLM_VERIFIED | 真实 LLM 调用 + 输出验证已通过 |
| REAL_FRONTEND_BACKEND_VERIFIED | 真实前后端联调已验证 |
| REAL_E2E_VERIFIED | 真实端到端（搜索→PDF→解析→LLM→审计→展示）已验证 |
| PRODUCTION_READY | 可用于生产环境 |

---

## 总表

| 模块 | 文档承诺 | 实际代码 | 成熟项目接入 | 真实验收 | 当前真实状态 | 主要问题 | 整改优先级 |
|------|---------|---------|-------------|---------|-------------|---------|-----------|
| M1 | 多源检索 + 阅读计划 | arXiv/OpenAlex 薄 wrapper | 无成熟库接入 | arXiv 超时、OpenAlex 无 PDF URL | THIN_WRAPPER_ONLY | 无 PDF URL、arXiv 超时、无 Semantic Scholar/Crossref | P1 |
| M2 | PDF 解析 + LLM 讲解 + 审计 | PyMuPDF get_text + 单次 LLM prompt + 结构性审计 | PyMuPDF（基础） | synthetic markdown 通过、真实 PDF e2e 失败 | MOCK_TESTED | parser 太弱、无真实 PDF 验证、审计只查结构不查内容 | P0 |
| M3 | 前后端展示 + API gating | FastAPI endpoints + Vue 组件 | 无 | 无真实前后端联调 | MOCK_TESTED | 无真实 PDF 上传 smoke、无页面级测试 | P1 |
| M4 | 互动学习 + 长期记忆 | 无代码 | 无 | 无 | DOC_ONLY | 纯文档设计 | P3 |
| M5 | 工程保障 + 真实验收 | live eval 框架 + 489 mock tests | pytest/Vitest | live eval 部分通过 | MOCK_TESTED | 真实 PDF e2e 失败、无 CI、无 secret scan | P1 |

---

## 一、全项目结论

### 当前项目是否偏玩具化

**是。** 项目有完整的文档体系和 mock 测试覆盖，但真实能力严重不足：

1. **M1 搜索**：arXiv adapter 超时，OpenAlex adapter 不返回 PDF URL。真实搜索无法获取可下载的论文。
2. **M2 解析**：parser 只是 PyMuPDF `get_text()` + 正则 heading 检测。无法处理表格、公式、图片、复杂排版。
3. **M2 LLM**：单次 prompt、单次解析、无 chain-of-thought。teaching_cards 在真实 LLM 上出现 JSON 解析失败。
4. **M2 审计**：F-1 到 F-6 只查结构性引用完整性，不查内容正确性。F-7+ 全部未实现。
5. **M3 前端**：无真实前后端联调。无真实 PDF 上传 smoke。
6. **M4**：纯文档，零代码。
7. **M5**：live eval 框架存在但真实 PDF e2e 失败。

### 最大方向性问题

1. **成熟项目零接入**：arXiv 用自写 httpx wrapper（不用 arxiv.py）、OpenAlex 用自写 httpx wrapper（不用 pyalex）、parser 用 PyMuPDF get_text()（不用 Docling）、LLM 用自写 httpx wrapper（不用 LangChain/LlamaIndex）。所有"参考"项目都没有真正接入。
2. **mock 测试冒充完成**：489 tests 全部通过，但没有一个测试证明真实论文能被正确处理。
3. **文档状态夸大**：STATUS.md 写"已阶段完成"的模块，实际上只有 mock 测试通过。

### 是否存在文档状态夸大

**是。** STATUS.md 中：
- M1 写"基础闭环完成"，但 arXiv 超时、OpenAlex 无 PDF URL
- M2 写"已阶段完成"，但无真实 PDF 验证
- M2.3 写"real LLM smoke 入口已实现"，但只用 synthetic markdown
- M3 写"部分完成"，但无真实前后端联调

### 是否存在 mock 通过冒充完成

**是。** 489 tests 全部是 mock/fake，没有任何一个证明：
- 真实论文 PDF 能被正确解析
- 真实 LLM 输出质量合格
- 真实前后端能联调

### 是否存在成熟项目只写未接入

**是。** 以下项目在文档中写了"REFERENCE_ONLY"或"只借鉴"，但代码中零引用：
- PaperQA / paper-qa
- STORM
- ARIS / Auto-claude-code-research-in-sleep
- Semantic Scholar
- Crossref
- Docling
- Marker
- arxiv.py
- pyalex
- Unpaywall

---

## 二、M1 审计

### 文档承诺

- 多源论文检索（arXiv + OpenAlex + Semantic Scholar + Crossref）
- 论文原始材料获取（LaTeX source → PDF → metadata-only）
- 去重评分
- 阅读计划生成
- 真实联网验收

### 实际代码

| 子模块 | 实际实现 | 问题 |
|--------|---------|------|
| M1.1 QueryPlanner | LLM query planning + 逗号分割 fallback | fallback 不能翻译中文、不能生成 related_terms |
| M1.2 ArxivAdapter | httpx + xml.etree 自写 wrapper | **arXiv API 超时**，无 rate limit、无 retry、无 arxiv.py |
| M1.2 OpenAlexAdapter | httpx + JSON 自写 wrapper | **不返回 pdf_url**，无 pyalex、无 citation graph |
| M1.3 PaperSourceResolver | 纯 metadata URL 构建 | **不下载 PDF**，只记录 URL |
| M1.3 SourceResolver | httpx PDF 下载 | 有下载能力，但 M1 不调用 |
| M1.4 SelectionService | 本地去重 + 评分 | 功能完整 |
| M1.5 DirectionRunner | 编排器 | 功能完整 |

### 成熟项目接入情况

| 项目 | 状态 | 说明 |
|------|------|------|
| arxiv.py | 未接入 | 自写 httpx wrapper 替代 |
| pyalex | 未接入 | 自写 httpx wrapper 替代 |
| Semantic Scholar | 未接入 | 文档写了 OPTIONAL_ADAPTER |
| Crossref / habanero | 未接入 | 文档写了 OPTIONAL_ADAPTER |
| Unpaywall | 未接入 | 未提及 |
| PaperQA | 未接入 | 文档写了 REFERENCE_ONLY |
| GPT Researcher | 未接入 | 未提及 |

### 真实验收情况

- M1 live search：arXiv 超时（0 结果），OpenAlex 返回 3 个候选但全部无 pdf_url
- 真实 PDF 下载：**失败**（无候选有 pdf_url 或 arxiv_id）
- M1 → M2 衔接：**不可能**（无 PDF 可供 M2 解析）

### 当前真实状态

**THIN_WRAPPER_ONLY**

- arXiv adapter 是自写薄 wrapper，且超时
- OpenAlex adapter 是自写薄 wrapper，且不返回 PDF URL
- 无成熟库接入
- 真实搜索无法获取可下载论文

### 主要缺口

1. arXiv adapter 超时（可能是 httpx timeout 太短或 arXiv API 限流）
2. OpenAlex adapter 不提取 pdf_url（OpenAlex API 有 open_access.pdf_url 字段，代码没取）
3. 无 Semantic Scholar / Crossref adapter
4. 无 Unpaywall DOI → PDF 解析
5. PaperSourceResolver 不下载 PDF
6. 无成熟库（arxiv.py / pyalex）接入

### 整改优先级

**P1** — 不解决 M1 PDF 获取问题，M2 无法真实验证。

---

## 三、M2 审计

### 文档承诺

- 真实 PDF 解析为结构化文档
- 证据链路（PassageIndex → ClaimEvidence → EvidencePack）
- LLM 生成 paper/formula/teaching cards
- QualityAuditor 质量审计
- understanding_status 门控
- fail-closed 策略

### 实际代码

| 子模块 | 实际实现 | 问题 |
|--------|---------|------|
| M2.1 LightweightIngestionService | PyMuPDF `get_text()` + 正则 heading | **极弱**：无表格、无公式、无图片、无 layout |
| M2.1 ParserAdapter | 接口 + LightweightParserAdapter | 接口设计好，但实现太弱 |
| M2.2 PassageIndex | section 分段 + 合并 | 依赖 parser 质量 |
| M2.2 ClaimExtractor | 关键词 + section 启发式 | 无 LLM claim extraction |
| M2.2 BM25 EvidenceRetriever | 自实现 BM25 | 功能可用 |
| M2.2 EvidencePack | 过滤 + token budget | 功能可用 |
| M2.3 paper_card_v2 | 单次 LLM prompt + JSON parse | teaching_cards 真实 LLM JSON 解析失败 |
| M2.3 formula_card_v2 | 单次 LLM prompt | 依赖 parser 公式提取质量 |
| M2.3 teaching_card_v2 | 单次 LLM prompt | **真实 LLM 输出 JSON 解析失败** |
| M2.4 QualityAuditor | F-1 到 F-6 结构性检查 | **不查内容正确性**，F-7+ 全部未实现 |
| M2.5 pipeline | 编排器 | 功能完整 |

### 成熟项目接入情况

| 项目 | 状态 | 说明 |
|------|------|------|
| PyMuPDF | 已接入（基础） | 只用 get_text()，未用高级功能 |
| Docling | 未接入 | 文档写了 OPTIONAL_ADAPTER |
| Marker | 未接入 | 文档写了 OPTIONAL_ADAPTER（GPL 风险） |
| PaperQA | 未接入 | 文档写了 REFERENCE_ONLY |
| LlamaIndex | 未接入 | 未提及 |

### 真实验收情况

- Synthetic markdown：通过（但 synthetic 不是真实论文）
- 真实 PDF：**未验证**（M1 无法提供 PDF）
- 真实 LLM：mimo-v2.5-pro 调用 3 次，teaching_cards JSON 解析失败
- QualityAuditor：只查结构引用，不查内容质量
- understanding_status：DEGRADED_STRUCTURAL（因 teaching_cards 失败）

### 当前真实状态

**MOCK_TESTED**

- Mock 测试覆盖完整
- Synthetic markdown 通过
- 真实 LLM 部分通过（teaching_cards 失败）
- 真实 PDF 未验证
- 审计只查结构不查内容

### 主要缺口

1. Parser 太弱（PyMuPDF get_text 无法处理真实论文）
2. 无真实 PDF 端到端验证
3. teaching_cards 真实 LLM JSON 解析不稳定
4. QualityAuditor F-7+ 全部未实现（无内容正确性检查）
5. 无 Docling / 成熟 parser 接入
6. formula_is_core 判断未实现

### 整改优先级

**P0** — M2 是产品核心，当前真实能力不足。

---

## 四、M3 审计

### 文档承诺

- 后端 API（/parse, /understanding_status, /cards, /artifacts）
- 前端展示（UploadView, LearningWorkspaceView, StatusBanner）
- 状态门控（BASELINE_ONLY/BLOCKED/DEGRADED/SUCCESS）
- 真实前后端联调

### 实际代码

| 子模块 | 实际实现 | 问题 |
|--------|---------|------|
| M3.1 API endpoints | FastAPI 实现 | 功能完整 |
| M3.2 UploadView | Vue 组件 | 无测试 |
| M3.3 LearningWorkspaceView | Vue 组件 | 无测试 |
| M3.4 StatusBanner | Vue 组件 | 7 tests（mock） |
| M3.5 /artifacts | debug-only | 功能完整 |

### 成熟项目接入情况

无外部项目接入需求。

### 真实验收情况

- 后端 API：端点存在，但无真实 PDF 上传 smoke
- 前端：无页面级测试，无真实前后端联调
- StatusBanner：7 mock tests 通过

### 当前真实状态

**MOCK_TESTED**

- API 端点代码存在
- 前端组件代码存在
- 无真实前后端联调验证
- 无真实 PDF 上传 → 状态展示验证

### 主要缺口

1. 无真实 PDF 上传 smoke
2. 无 UploadView 页面级测试
3. 无 LearningWorkspaceView 页面级测试
4. 无真实前后端联调验证
5. /quality_report endpoint 未实现

### 整改优先级

**P1** — M3 依赖 M2 的真实输出，M2 解决后 M3 才能真实验证。

---

## 五、M4 审计

### 文档承诺

- 选中内容解释
- 符号与公式解释
- 上下文追问
- 导师式追问与研究训练
- 长期记忆
- 记忆优先检索

### 实际代码

**零代码。** 全部是文档设计。

### 成熟项目接入情况

| 项目 | 状态 | 说明 |
|------|------|------|
| STORM | 未接入 | 文档写了 REFERENCE_ONLY |
| PaperQA | 未接入 | 文档写了 REFERENCE_ONLY |
| MemGPT / Letta | 未接入 | 文档写了 REFERENCE_ONLY |

### 真实验收情况

无。没有任何代码可以验收。

### 当前真实状态

**DOC_ONLY**

### 主要缺口

1. 零代码实现
2. 无 API
3. 无 schema 实现
4. 无 memory persistence
5. 无 retrieval logic
6. 无 advisor question generation
7. 无前端集成
8. 无测试

### 整改优先级

**P3** — M4 依赖 M2/M3 完成后才有意义。

---

## 六、M5 审计

### 文档承诺

- 真实验收体系
- live eval 框架
- secret scan
- CI
- debug/admin 鉴权
- 缓存策略

### 实际代码

| 子模块 | 实际实现 | 问题 |
|--------|---------|------|
| M5.1 后端测试 | 489 mock tests | 全部 mock，无真实验收 |
| M5.2 前端测试 | 7 mock tests | 只有 StatusBanner |
| M5.3 live eval | live_eval.py + run_live_eval.py + tests_live/ | 真实 PDF e2e 失败 |
| M5.4 ResponseCache | 基础实现 | 功能可用 |
| M5.5 secret scan | 未实现 | 无工具接入 |
| M5.6 debug/admin | SENSEI_DEBUG 环境变量 | 无正式鉴权 |
| M5.7 CI | 未实现 | 无 CI 配置 |

### 真实验收情况

- 默认 pytest：489 passed（全部 mock）
- live eval M1：arXiv 超时、OpenAlex 返回 3 无 PDF 候选
- live eval M2：通过（synthetic markdown + 真实 LLM，teaching_cards JSON 失败）
- live eval 真实 PDF e2e：**失败**（无候选有 pdf_url）
- frontend build：成功
- npm test：7 passed

### 当前真实状态

**MOCK_TESTED**（框架存在但真实验证失败）

### 主要缺口

1. 真实 PDF e2e 失败
2. 无 CI
3. 无 secret scan
4. 无正式 admin 鉴权
5. live eval skip 逻辑已严格化但真实验证跑不通

### 整改优先级

**P1** — live eval 框架已存在，需要让真实验证跑通。

---

## 七、成熟项目调研

### 实际调研了哪些项目

以下项目在文档中有调研记录（GitHub README 级）：
- arxiv.py, pyalex, Semantic Scholar, Crossref/habanero, Unpaywall
- Docling, Marker, PyMuPDF, MinerU, Nougat
- PaperQA, STORM, ARIS, GPT Researcher
- LangChain, LlamaIndex, MemGPT/Letta

### 建议立即接入

| 项目 | 理由 | 接入方式 |
|------|------|---------|
| arxiv.py | 替代自写 httpx wrapper，自带 rate limit、retry、PDF URL | pip install arxiv |
| pyalex | 替代自写 httpx wrapper，自带 pdf_url 提取、citation graph | pip install pyalex |
| Semantic Scholar API | 补充 citation count、venue metadata | 直接 API 调用 |
| Docling | 替代 PyMuPDF get_text()，支持 layout/table/formula | pip install docling（依赖重，optional） |

### 建议后置接入

| 项目 | 理由 |
|------|------|
| Crossref/habanero | DOI metadata，优先级低于 Semantic Scholar |
| Unpaywall | DOI → OA PDF URL，优先级低于 arXiv PDF |
| Marker | GPL-3.0 许可证风险 |

### 不建议接入

| 项目 | 理由 |
|------|------|
| LangChain | 过重，当前只需要 httpx wrapper |
| LlamaIndex | 过重，当前不需要 RAG 框架 |
| GPT Researcher | 目标不同（自动科研 vs 论文理解） |
| MemGPT/Letta | M4 未开始，后置 |

### 只参考具体算法

| 项目 | 参考点 |
|------|--------|
| PaperQA | evidence-constrained prompt 设计 |
| STORM | multi-perspective questioning（M4） |
| ARIS | reviewer independence、audit chain |

---

## 八、测试结果

### 快速回归

```
python -m pytest -q → 489 passed
frontend npm run build → 成功 (354ms)
frontend npm test → 7 passed
```

### 真实验收

```
RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 RESEARCHSENSEI_LIVE_EVAL=1
python scripts/run_live_eval.py → exit code 4

M1 live: passed（arXiv 超时 0 结果，OpenAlex 3 结果无 PDF URL）
M2 real LLM: passed（synthetic markdown，teaching_cards JSON 解析失败但降级通过）
real PDF e2e: failed（"No candidate with pdf_url or arxiv_id found."）
```

### 真实验收失败原因

1. arXiv adapter 超时（0 结果返回）
2. OpenAlex adapter 不提取 pdf_url
3. 因此无候选有 pdf_url 或 arxiv_id
4. 真实 PDF e2e 无法执行

---

## 九、状态修正

### 被降级的模块

| 模块 | 旧状态 | 新状态 | 理由 |
|------|--------|--------|------|
| M1 | 基础闭环完成 | THIN_WRAPPER_ONLY | arXiv 超时、OpenAlex 无 PDF URL |
| M2 | 已阶段完成 | MOCK_TESTED | 无真实 PDF 验证、审计只查结构 |
| M2.3 | real LLM smoke 入口已实现 | MOCK_TESTED | 只用 synthetic markdown |
| M3 | 部分完成 | MOCK_TESTED | 无真实前后端联调 |
| M5.3 | 已实现受控 live eval | MOCK_TESTED | 真实 PDF e2e 失败 |

### 仍只是 MOCK_TESTED 的模块

M2, M2.1, M2.2, M2.3, M2.4, M2.5, M3, M3.1, M3.2, M3.3, M3.4, M5, M5.1, M5.2, M5.3

### 仍只是 DOC_ONLY 的模块

M4, M4.1, M4.2, M4.3, M4.4, M4.5, M4.6

### 达到 REAL_* 的模块

无。没有任何模块通过真实端到端验证。

---

## 十、安全

- 是否发现 API key 泄露：**否**（.env 在 .gitignore，live eval 有 _redact_report）
- 是否发现 PDF/live report/大文件被提交：**否**（.gitignore 覆盖）
- git status --short：干净（审计报告为新增文件）

---

## 十一、下一步整改路线

### P0：解决 M1 PDF 获取（阻塞 M2 真实验证）

1. **修复 OpenAlex adapter 提取 pdf_url**：OpenAlex API 返回 `open_access.pdf_url` 字段，当前代码未提取
2. **修复 arXiv adapter 超时问题**：增加 timeout、retry，或接入 arxiv.py
3. **接入 Semantic Scholar API**：补充 citation count 和 PDF URL
4. **验收标准**：`RUN_LIVE_TESTS=1 python scripts/run_live_eval.py` M1 返回至少 1 个有 pdf_url 的候选

### P0：解决 M2 真实 PDF 端到端

5. **用真实 PDF 跑通 M2 pipeline**：下载一个 arXiv PDF → parser → evidence → LLM → audit → status
6. **修复 teaching_cards JSON 解析**：当前 mimo-v2.5-pro 输出中文 JSON 解析失败
7. **验收标准**：`RUN_LIVE_TESTS=1 RUN_LLM_TESTS=1 python scripts/run_live_eval.py` real_pdf_e2e status=passed

### P1：增强 M2 能力

8. **评估 Docling 接入**：替代 PyMuPDF get_text()，提升 PDF 解析质量
9. **验收标准**：真实论文 PDF 解析后 passage 覆盖率 > 80%

### P1：M3 真实前后端联调

10. **真实 PDF 上传 → 后端处理 → 前端展示 smoke**
11. **验收标准**：上传真实小 PDF，前端显示 StatusBanner + cards

### P2：M5 工程保障

12. **接入 gitleaks secret scan**
13. **配置 GitHub Actions CI**

### P3：M4 设计完善

14. **M4 文档细化后评估实现优先级**

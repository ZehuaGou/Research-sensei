# ResearchSensei Design

---

## 1. 产品定位

ResearchSensei / 读博模拟器 是一个多能力科研学习与训练系统。

它不是普通论文摘要器，不是单篇论文卡片生成器，不是单纯方向地图工具，不是自动写论文系统，也不是 ARIS clone。

它的目标是帮助用户在科研学习过程中：

- 建立研究方向框架；
- 找到综述、代表论文和可精读论文；
- 可信精读单篇论文；
- 理解公式、符号和方法机制；
- 理解多篇论文之间的演进关系；
- 通过前端形成方向页和论文页；
- 进行论文级、方向级和上下游扩展互动；
- 接受导师式追问和研究训练；
- 沉淀长期记忆。

正式模块体系为 M1 → M2 → M3 → M4 → M5。产品能力可以跨模块，但不另设编号。

---

## 2. 设计原则

### evidence-constrained

LLM 容易编造。每个解释必须可追踪到论文中的具体证据（evidence_ref）。没有证据的解释不能输出。

### fail-closed

宁可不输出，也不输出低可信解释。论文理解失败时标记 BLOCKED_UNDERSTANDING，不生成垃圾卡片。

### baseline is not final

规则 baseline（rule-based builders）是诊断工具，不是最终导师级理解。不能冒充高质量解释。

### 不重复造轮子

ResearchSensei 不优先自研所有能力。每个模块在设计和实现前，都要优先调研 GitHub 开源项目、论文工具、成熟库和外部 API。能稳定复用的优先复用；不能直接复用的，也要学习其接口设计、数据结构、失败处理和测试方式。

### adapter-first

外部 parser / retrieval / audit 能力必须通过 adapter 接入，不能深度耦合。

### real-validation-first

涉及 LLM、联网搜索、PDF 下载、PDF 解析、前后端联调的模块，验收必须跑真实链路。mock/fake/skip 不作为模块完成依据。缺 key、缺网络、API 限流、PDF 下载失败、LLM JSON 解析失败，不能汇报为真实验收通过。

---

## 3. 三个产品入口

### 入口 1：Direction Exploration Page

用户输入研究方向，例如：

- 时间序列异常检测
- 图异常检测
- 多模态大模型
- 扩散模型

系统默认行为：

1. 优先搜索高质量综述；
2. 如果找不到合格综述，再执行 staged multi-source search；
3. 生成方向框架、方法族、技术阶段、代表论文、推荐阅读顺序。

输出：survey_candidates, direction_landscape, method_families, chronology_stages, landscape_anchors, recommended_reading_order, papers that can be sent to M2。

### 入口 2：Paper Deep Reading Page

用户可以：

- 上传 PDF
- 输入论文标题
- 输入 DOI
- 输入 arXiv ID
- 输入 arXiv URL
- 输入 PDF URL
- 输入 publisher URL

系统默认行为：

1. 定位论文；
2. 下载或接收 best available source；如果只有 PDF，再进入 PDF 解析路径；
3. 验证是否同一篇论文；
4. 进入 M2 单篇精读。

输出：paper_card, formula_cards, teaching_cards, evidence_refs, quality_report, understanding_status。

### 入口 3：Seed Paper Expansion

用户在论文精读页点击"查找这篇论文的上下游 / 相关综述 / 后续改进"。

系统默认行为：

1. 围绕当前论文调用 M1；
2. 查找引用论文、被引论文、相关综述、同路线论文、后续改进论文；
3. 形成局部论文关系图。

输出：seed_expansion_result, upstream_papers, downstream_papers, related_surveys, follow_up_papers, paper_relation_graph。

---

## 4. M1-M5 模块职责

| 编号 | 模块 | 职责 |
|------|------|------|
| M1 | 论文搜索、综述优先、方向探索、最佳原始材料获取、材料归一化、阅读计划、seed paper expansion | 搜索、验证、best available source 获取、筛选、排序、生成阅读计划和方向框架，并把原始 PDF / LaTeX / HTML / DeepXiv / parser output 归一化为 M2 主输入 `canonical_paper.md` |
| M2 | 单篇论文精读、综述论文精读、证据链、公式/符号/方法机制讲解 | 读取和校验 `canonical_paper.md`，转换为 evidence-ready blocks，构建证据链路、讲解生成、质量审计、状态门控 |
| M3 | 前端展示，包括 DirectionWorkspace、PaperWorkspace、SeedExpansionPanel | 后端 API、前端状态展示、debug 入口 |
| M4 | 互动学习，包括 paper-level、direction-level、seed-expansion interaction，以及导师式追问和长期记忆 | 选中解释、追问、训练、知识库、记忆检索 |
| M5 | 真实测试、CI、安全、密钥、成本、工程可靠性 | 测试、安全、缓存、debug/admin、CI、成本控制 |

---

## 4.5 Source-Aware Acquisition and Parsing

M1 的职责不只是搜索和下载 PDF，而是完成高质量文献发现、多源验证、best available source 获取、原始材料归一化，并输出 M2 的统一主输入 `canonical_paper.md`。

**M1 canonicalization pipeline**:
1. Search / metadata acquisition
2. Candidate verification
3. Quality ranking
4. Best available source resolution
5. Source download
6. Material normalization:
   - **MinerU2.5-Pro adapter** (PRIMARY): `mineru-vl-utils` + `opendatalab/MinerU2.5-Pro-2604-1.2B` → DocumentBlock
   - **RuleBasedStructureRefiner** (always): section assignment, heading normalization, risk detection
   - **OllamaSectionRefiner** (optional, default OFF): LLM-based section refinement
   - **CanonicalBuilder**: `canonical_paper.md`, `formula_slots.json`, visual audit
   - **Fallback** (when MinerU unavailable): MaterialNormalizer (MarkItDown/PyMuPDF + MarkerDocumentFormulaDetector)
7. `canonical_paper.md` generation
8. M1 Quality Gate: source/title, bbox/crop/overlay, latex/canonical match, section_contradiction, abstract_formula_overload
9. `m2_ready` gate

MinerU2.5-Pro via mineru-vl-utils is the primary M1 parser. Marker is fallback/audit baseline. PyMuPDF/MarkItDown are lightweight fallback/debug. Ollama is optional, default OFF, and must not modify latex/bbox/page/source identity. M1 gate blocks: all-formulas-in-Abstract, section contradiction, source/title mismatch, missing latex/crop/overlay, dense raw-only formulas. References formulas are excluded from formula understanding.

**M1 source priority**:
1. LaTeX source / arXiv source
2. structured HTML / XML / DeepXiv structured output
3. PDF parser output
4. low-confidence text fallback
5. metadata only

`metadata only` 不能进入 M2。M1 不要求所有论文最终变成真实 LaTeX；统一目标是 `canonical_paper.md`。如果 source 是 LaTeX，公式可标记为 `source_latex`；如果来自 parser / OCR / reconstruction，必须标明来源，不能冒充原始 LaTeX。

**canonical_paper.md contract**:

```yaml
---
paper_id:
title:
authors:
year:
venue:
source_type:
source_confidence:
canonicalization_status:
parser_used:
m2_ready:
degradation_reason:
# parser pipeline
primary_parser:                 # "mineru25pro" | "marker_document" (fallback)
fallback_used:
llama_refined:
mineru_available:
# formula pipeline
formula_detector:
formula_slot_count:
formula_crop_count:
mineru_latex_count:
marker_latex_count:
ocr_latex_count:
raw_formula_text_count:
unresolved_formula_count:
canonical_quality_status:
---
```

正文应尽量包含 Title、Abstract、Introduction、Related Work、Method、Experiments、Conclusion、References。缺失 section 必须保留降级状态，不用空内容伪装完整论文。

公式块必须保留来源和位置：

````markdown
<!-- formula_id: formula_001 | origin: parser_latex | section: Method | page: 4 | bbox: [108.75,339.54,288.07,370.48] | ocr_status: not_required | final_origin: parser_latex -->
```latex
\mathcal{L} = ...
```
````

Unresolved formula (no reliable LaTeX):

````markdown
<!-- formula_id: formula_002 | origin: unresolved | section: Experiments | page: 7 | bbox: [50.0,200.0,300.0,230.0] | ocr_status: not_required | final_origin: unresolved | unresolved_reason: no_latex_from_any_source -->
{{FORMULA:formula_002 unresolved}}
````

`formula_origin` 取值固定为 `source_latex`、`parser_latex`、`ocr_latex`、`raw_formula_text`、`unresolved`。

**MarkerDocumentFormulaDetector**:
- 使用 Marker `converter.build_document()` 访问内部 Document，获取 Equation blocks with bbox。
- 输出：FormulaSlot 列表（page, bbox, polygon, block_type, marker_text, marker_latex）。
- 关键发现：`MarkdownOutput` 和 `JSONRenderer` 都不保留 Equation blocks；只有 `build_document()` 提供位置数据。
- 失败条件：Marker 超时、无 Equation blocks、bbox 越界。
- 当前状态：IMPLEMENTED。

**FormulaCropper**:
- 输入：PDF path + FormulaSlot with bbox。
- 使用 PyMuPDF (`fitz.Rect(bbox)` → `page.get_pixmap(clip=rect, dpi=200)`) 裁剪公式区域。
- 输出：裁剪后的 formula image 保存到 `formula_crops/`。
- 当前状态：IMPLEMENTED。

**OCR strategy (NOT automatic)**:
- 仅当 Marker block 有 bbox 但无可靠 LaTeX 时触发。
- OCR 结果标记为 `ocr_latex`，永远不标记为 `source_latex`。
- 候选实现：pix2tex / LaTeX-OCR。
- 当前状态：BLOCKED（pix2tex 模型下载失败）。

M2 的职责不是直接面对混乱原始输入。M2.1 是 canonical input reader / validator，只读取 `canonical_paper.md`，校验 front matter、section、paragraph、formula blocks，然后转换为 `DocumentBlock` 和 evidence-ready blocks。

**M2.1 gate**:
- 输入：`canonical_paper.md` 和 M1 写入的 source/canonicalization status。
- 输出：`parsed_document.json`、formula blocks、warnings、`BLOCKED_UNDERSTANDING` / `DEGRADED_STRUCTURAL` / `SUCCESS` 状态。
- hard fail：front matter 缺少 paper_id/title/source_type/canonicalization_status/m2_ready，公式块缺少 origin，metadata only 输入，或 `m2_ready=false` 且无人工 override。
- 当前状态：DOC_DESIGNED / NOT_IMPLEMENTED。

M2 公式解释基于 `canonical_paper.md` 中的 formula block，不直接绕过 M1 去读原始 PDF。解释置信规则：`source_latex` 可高置信解释；`parser_latex` 可解释但必须保留 parser warning；`ocr_latex` 可解释但必须标注 OCR 来源；`reconstructed` 只能作为推测解释；`unknown` 不能做详细公式推导。

---

## 5. M1-M5 不是单向流水线

- M1 可以独立从方向入口启动。
- M2 可以独立从上传 / 标题 / DOI / URL 启动。
- M1 可以把论文送入 M2 精读。
- M2 也可以反向触发 M1 做 seed paper expansion。
- M3 负责展示 M1 / M2 / M4 的结果。
- M4 同时支持 paper-level interaction、direction-level interaction、seed-expansion interaction。
- M5 负责真实测试、安全、成本和工程可靠性，不替代 M1-M4 的业务验收。

---

## 6. 子模块索引

### M1

| 子模块 | 职责 |
|--------|------|
| M1.1 用户问题与搜索规划 | QueryPlanner |
| M1.2 多源论文检索 | Search Adapters / Acquisition |
| M1.3 best available source 获取 | Source Resolver / Source Fetch |
| M1.4 材料归一化与 canonical_paper.md 生成 | Material Normalization / Canonical Paper Generation |
| M1.5 候选论文去重与评分 | Candidate Selection / Verification / Relevance |
| M1.6 阅读计划与方向框架 | Reading Plan / Direction Landscape |

### M2

| 子模块 | 职责 |
|--------|------|
| M2.1 canonical input reader 与 evidence-ready block builder | CanonicalPaperReader / CanonicalBlockBuilder |
| M2.2 证据链路构建 | Evidence / Grounding |
| M2.3 论文理解与讲解生成 | Paper Understanding / Teaching |
| M2.4 质量审计与可信控制 | Audit / Quality |
| M2.5 理解状态与结果门控 | UnderstandingStatus / Gates |

### M3

| 子模块 | 职责 |
|--------|------|
| M3.1 后端 API | API endpoints |
| M3.2 上传与任务页面 | Upload / Job UI |
| M3.3 学习工作区 | Learning Workspace |
| M3.4 状态提示与卡片展示 | StatusBanner / Cards |
| M3.5 调试入口与 raw artifact 限制 | Debug / Artifacts Gating |

### M4

| 子模块 | 职责 |
|--------|------|
| M4.1 选中内容解释 | Selection Explain |
| M4.2 符号与公式解释 | Symbol / Formula Explain |
| M4.3 上下文追问 | Interactive Q&A |
| M4.4 导师式追问与研究训练 | Advisor-style Questioning / Research Drill |
| M4.5 论文知识库与长期记忆 | PaperMemory / SessionContext |
| M4.6 记忆优先检索与 token 节省 | Memory-first Retrieval |

### M5

| 子模块 | 职责 |
|--------|------|
| M5.1 后端测试 | pytest |
| M5.2 前端测试 | Vitest |
| M5.3 真实 LLM smoke 与成本控制 | LLM Smoke / Cost |
| M5.4 缓存与复用 | Cache |
| M5.5 安全与密钥扫描 | Secret Scan |
| M5.6 Debug/admin 权限 | Debug/Admin |
| M5.7 CI 与发布检查 | CI / Release Check |

---

## 7. Artifact 链路

### 单篇论文精读（M2）

```
source_status.json
→ canonical_paper.md
→ parsed_document.json
→ passage_index.json
→ claim_evidence.json
→ evidence_index.json (v1 兼容)
→ paper_skeleton.json
→ paper_card.json / formula_cards.json / teaching_cards.json
→ understanding_status.json
→ quality_report.json
```

### 方向探索（M1 Direction Exploration）

```
query_plan.json → survey_candidates.json → direction_landscape.json → reading_plan.json
```

### 聚焦获取（M1 Focused Acquisition）

```
query_plan.json → candidate_pool.json → filtered_candidates.json → source_resolution.json → canonical_paper.md → reading_plan.json
```

### Seed Paper Expansion（M1）

```
seed_paper_metadata → paper_relation_graph.json → seed_expansion_result.json
```

---

## 8. 当前未实现能力归属

| 能力 | 归属模块 | 当前状态 |
|------|---------|---------|
| Direction Exploration Mode | M1 | DOC_DESIGNED, NOT_IMPLEMENTED |
| Focused Acquisition Mode | M1 | REAL_E2E_VERIFIED |
| Seed Paper Expansion Mode | M1 | DOC_DESIGNED, NOT_IMPLEMENTED |
| Source-aware acquisition (LaTeX/HTML priority) | M1.3 | DOC_DESIGNED, NOT_IMPLEMENTED |
| canonical_paper.md pipeline | M1 / M2.1 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M1 material normalization | M1.3 | DOC_DESIGNED, NOT_IMPLEMENTED |
| FormulaRegionDetector | M1 formula detection | SUPERSEDED by MinerU25ProAdapter (primary) and MarkerDocumentFormulaDetector (fallback) |
| FormulaOCRAdapter / pix2tex adapter | M1 formula OCR (fallback only) | interface exists, model not integrated; fallback for unresolved crops only |
| DeepXiv structured adapter | M1 material normalization | DOC_DESIGNED, NOT_IMPLEMENTED |
| Survey Deep Reading | M2 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M2 canonical input reader / validator | M2.1 | DOC_DESIGNED, NOT_IMPLEMENTED |
| LaTeXSourceParser | M1 material normalization | DOC_DESIGNED, NOT_IMPLEMENTED |
| MinerUAdapter / MarkerAdapter / DoclingAdapter | M1 material normalization | DOC_DESIGNED, NOT_IMPLEMENTED |
| Source-aware parser selection | M1 material normalization | DOC_DESIGNED, NOT_IMPLEMENTED |
| evidence_ref 原文跳转 | M2.2 / M3 | DOC_DESIGNED, NOT_IMPLEMENTED |
| DirectionWorkspace | M3 | DOC_DESIGNED, NOT_IMPLEMENTED |
| PaperWorkspace full real validation | M3 | PARTIAL_CODE, REAL_PAGE_VALIDATION_MISSING |
| SeedExpansionPanel | M3 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M4 paper-level interaction | M4 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M4 direction-level interaction | M4 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M4 seed-expansion interaction | M4 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M4 long-term memory | M4.5 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M4 advisor training | M4.4 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M5 real LLM smoke / live eval | M5.3 | PARTIAL_CODE, NOT_FULLY_VERIFIED |
| M5 cost control | M5.3 | DOC_DESIGNED, PARTIAL_CODE |
| M5 secret scan | M5.5 | DOC_DESIGNED, NOT_IMPLEMENTED |
| M5 CI / release check | M5.7 | DOC_DESIGNED, NOT_IMPLEMENTED |
| Debug/admin 鉴权 | M5.6 | DOC_DESIGNED, NOT_IMPLEMENTED |
| /quality_report endpoint | M3.1 / M5.6 | DOC_DESIGNED, NOT_IMPLEMENTED |

---

## 9. 为什么不是 ARIS

ARIS 做的是自动科研：idea discovery → experiment → paper writing → rebuttal。目标是帮研究者做科研。

ResearchSensei 做的是教人读懂论文、理解方向、训练科研思维。目标是帮学生建立科研能力。

两者目标完全不同。只参考 ARIS 的：
- audit chain（5 层审计）
- reviewer independence（审计者独立于生成者）
- claim audit（零上下文验证）

不整包迁移 ARIS。

---

## 10. 为什么保留 Vue / FastAPI / Pydantic

- Vue 3 前端已有基础，重写成本高收益低
- FastAPI 适合 API、schema 校验
- Pydantic 适合 artifact JSON 驱动链路
- 旧 `backend/` 冻结，新功能只走 `src/researchsensei/`

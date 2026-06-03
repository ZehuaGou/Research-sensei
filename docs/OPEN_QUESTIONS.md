# OPEN QUESTIONS

## 1. Phase 编号与原始开发文档的差异

- **问题**：当前迁移路线的 Phase 编号已和原始开发文档 `03_FULL_IMPLEMENTATION_PLAN.md` 存在差异。
- **影响**：后续 Agent 如果只按旧编号执行，会误判当前阶段，跳过必要步骤或重复实现。
- **当前临时处理**：以 `docs/PROGRESS.md` 和 `docs/MIGRATION_PLAN.md` 为准。
- **需要用户确认**：已完成，见 `docs/PHASE_MAPPING.md`。

## 2. Phase 7 范围待确认

- **问题**：原始文档中 Phase 6 = 学习卡片生成，Phase 7 = HTML 渲染。但当前迁移路线中 Phase 6 = grounding/evidence + paper_skeleton，Phase 7 范围未定。
- **影响**：如果直接按旧文档进入 card/render，会跳过 LLM 基础设施和 teaching 引擎的前置工作。
- **当前临时处理**：Phase 7 暂不进入 teaching/card/render，等待范围确认。
- **需要用户确认**：Phase 7 应优先做 LLM 基础设施（client/prompt/mock），还是直接做 card 生成？
- **已解决**：确认 Phase 7 = LLM 基础设施。见 `docs/PHASE_MAPPING.md` 和 `docs/REUSE_REPORT.md`。

## 3. LLM 基础设施时机

- **问题**：Phase 3 在迁移路线中跳过了 LLM client/prompt/cache 的实现（原计划在 Phase 3，实际推迟）。
- **影响**：后续 card 生成、teaching、advisor 等都需要 LLM 层。
- **当前临时处理**：Phase 6 全程无 LLM 调用，纯规则引擎。
- **需要用户确认**：LLM 基础设施是否应在进入 card/teaching 之前作为独立 Phase 完成？
- **已解决**：确认 Phase 7 独立完成 LLM 基础设施，不与 card/teaching 混合。

## 4. 真实 LLM 测试策略

- **问题**：何时引入真实 LLM 调用的集成测试？
- **影响**：mock 测试无法验证 prompt 质量和输出格式。
- **当前临时处理**：所有测试 mock。
- **需要用户确认**：是否在 LLM 基础设施 Phase 中引入可选的真实 LLM 测试（标记 `@pytest.mark.live`）？

## 5. Phase 9 范围：formula 还是 render

- **问题**：原文档 Phase 6 包含 formula 讲解卡，原文档 Phase 7 包含 HTML 渲染。当前路线两者都未安排。
- **影响**：formula 是"把论文讲懂"的核心能力之一，render 是用户看到结果的必要环节。
- **当前临时处理**：Phase 9 候选为 formula 或 render，待确认。
- **需要用户确认**：Phase 9 优先做 formula 讲解卡还是 HTML render？
- **已解决**：确认 Phase 9 = Formula Card JSON v1。render 延后到 Phase 14。见 `docs/PHASE_MAPPING.md` 和 `docs/REUSE_REPORT.md`。

## 6. teaching 五层法的实现策略

- **问题**：原文档的 teaching 五层法（30 秒 / 5 分钟 / 深挖 / 类比 / 数字例子）需要真实 LLM 调用才能产出高质量内容。
- **影响**：如果 Phase 10 做 teaching，需要决定是纯规则版还是 LLM 版。
- **当前临时处理**：Phase 8 的 paper_card 已有 one_sentence_summary，可作为 teaching 的 30 秒层。
- **需要用户确认**：teaching 是否等真实 LLM 测试策略确定后再实现？
- **已解决**：确认 Phase 10 = Teaching Card JSON v1，五层讲解法，rule-based + LLM-enhanced（mock）。见 `docs/PHASE_MAPPING.md` 和 `docs/REUSE_REPORT.md`。

## 7. query/acquisition/selection 搜索链路的依赖

- **问题**：搜索链路需要外部 API（arXiv/OpenAlex/Semantic Scholar），涉及 reuse gate 和 Adapter 设计。
- **影响**：这是方向学习流程的入口，但依赖外部服务。
- **当前临时处理**：安排在 Phase 11，未开始 reuse gate。
- **需要用户确认**：搜索链路是否需要在 formula/teaching 之前实现？
- **已解决**：确认 Phase 11 = Query / Acquisition / Selection / Reading Plan v1。arXiv + OpenAlex 作为 DIRECT_ADAPTER。Semantic Scholar/Crossref/Papers With Code 延后。见 `docs/PHASE_MAPPING.md` 和 `docs/REUSE_REPORT.md`。

## 8. Phase 10 teaching card rule-based 内容质量问题

- **问题**：rule-based builder 的 core_idea/method_overview 的 human_explanation 是公式文本而非人话解释。`_infer_paper_role()` 返回泛泛模板。
- **影响**：用户看到的"人话版"是原始公式，违反"不能输出空泛解释"的要求。
- **当前临时处理**：标记为 HIGH，建议在进入 Phase 11 前修复。
- **需要用户确认**：是否在 Phase 11 开始前修复 H1（~10 行代码），还是带着进入 Phase 11？
- **详细审计**：见 `docs/PHASE_10_REVIEW.md`。
- **已解决**：已修复。`_is_formula_heavy()` 检测公式密集文本并降级，`_infer_paper_role()` 使用具体语言，新增 7 个内容质量测试。见 `docs/PHASE_10_REVIEW.md`。

## 9. Phase 12 范围存在文档冲突

- **问题**：`docs/PHASE_MAPPING.md` 建议 Phase 12 = patterns + drill（旧 Phase 6 子模块），但原始开发文档 `03_FULL_IMPLEMENTATION_PLAN.md` 定义 Phase 12 = 工程可靠性（断点续跑/日志/缓存/安全测试）。
- **影响**：如果不确认范围，可能实现错误的模块。
- **当前处理结论**：以 `docs/PHASE_MAPPING.md`（迁移路线权威文档）为准，Phase 12 = patterns + drill。工程可靠性推迟到后续 Phase。Phase 12 reuse gate 已完成，P0 quality tests 已补充。进入代码开发前需最终确认范围。

## 10. arXiv ID 去重规则

- **问题**：arXiv ID `2301.12345v1` 和 `2301.12345v2` 是否应视为同一篇论文？
- **当前实现**：`_normalize_arxiv_id()` 剥离 `arXiv:` 前缀和 `vN` 版本后缀，不同版本合并为同一篇论文。保留先出现或元数据更完整者。
- **理由**：阅读计划场景下，同一论文的不同版本（v1/v2）通常是小修，用户不需要分别阅读。
- **风险**：如果 v1 和 v2 有重大内容差异（如新增实验），合并可能丢失信息。
- **状态**：已实现，已测试。如需调整可修改 `_normalize_arxiv_id()`。

## 11. 是否引入 ParserAdapter

- **问题**：当前 PDF 解析用 PyMuPDF fallback，质量低。是否引入 Docling/Nougat/Marker 作为 optional adapter？
- **当前倾向**：引入 ParserAdapter interface，LightweightParser 作为 default，Docling/Nougat/Marker 作为 optional adapter。
- **风险**：optional adapter 需要用户自行安装，增加使用门槛。
- **状态**：待确认。详见 `docs/RESEARCHSENSEI_TECH_ROUTE_REVIEW.md`。

## 12. 是否引入 PaperQA-style EvidenceRetriever

- **问题**：当前 evidence 是 block-level，不够精确。是否引入 passage-level retrieval？
- **当前倾向**：升级 evidence_index 为 passage-level，不直接引入 PaperQA。
- **状态**：待确认。

## 13. 是否引入 ARIS-style audit gate

- **问题**：当前 explanation 和 audit 没有分离。是否参考 ARIS 的 reviewer independence 设计？
- **当前倾向**：参考 ARIS 的 reviewer independence 和 assurance contract，但不整包接入。
- **状态**：待确认。

## 14. Phase 12 是否继续冻结

- **问题**：Phase 12 (patterns + drill) 是否在 route reset 完成前继续冻结？
- **当前决定**：Phase 12 continues frozen until Phase 11.6-11.9 complete and quality gates pass. Accepted unless user overrides.
- **状态**：accepted unless user overrides.

## 15. 哪些外部项目进入 optional adapter shortlist

- **问题**：哪些外部项目值得作为 optional adapter？
- **当前 shortlist**：Docling、Nougat、Marker（Parser Layer）；PaperQA（Evidence Layer，参考设计）。
- **状态**：待确认。

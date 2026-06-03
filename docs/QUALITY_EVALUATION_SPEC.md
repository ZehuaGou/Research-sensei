# ResearchSensei Quality Evaluation Specification

版本: v1.0
日期: 2026-06-03
状态: 设计稿，待人工确认

---

## 1. 质量评价体系总览

ResearchSensei 的目标不是"能生成 JSON"，而是"帮助用户真正读懂论文"。

因此质量评价必须覆盖三个层次：

| 层次 | 含义 | 当前覆盖 |
|------|------|----------|
| L1: Schema Validity | JSON 能反序列化、字段非空 | 已覆盖 (pytest) |
| L2: Structural Quality | artifact 链路完整、evidence_ref 有效、降级正确 | 部分覆盖 |
| L3: Content Quality | 解释忠实原文、公式讲解准确、非模板化、有科研思维 | 未覆盖 |

本文档定义 L2/L3 层的质量指标、评分标准和测试建议。

---

## 2. 质量指标定义

### A. Groundedness / 证据绑定 (20 分)

衡量标准：每个核心解释是否能回指 evidence_ref，是否避免无证据推断。

| 分值 | 标准 |
|------|------|
| 5 | 所有核心 claim 有 evidence_ref，且 ref 存在于 evidence_index |
| 4 | 绝大部分 claim 有 ref，个别边缘 claim 降级为 UNVERIFIED |
| 3 | 部分 claim 有 ref，部分标 NEEDS_HUMAN_CHECK |
| 2 | 多个核心 claim 缺 ref，但标了 INSUFFICIENT_EVIDENCE |
| 1 | 核心 claim 无 ref 且未降级 |
| 0 | 编造 evidence_ref 或伪造证据类型 |

### B. Faithfulness / 忠实原文 (20 分)

衡量标准：是否没有编造贡献、实验、结论；是否没有把公式含义解释错。

| 分值 | 标准 |
|------|------|
| 5 | 所有解释可追溯到原文 block，无编造 |
| 4 | 极少数推断标为 REASONABLE_INFERENCE |
| 3 | 存在少量未标注的推断，但不涉及核心结论 |
| 2 | 存在编造的实验结果或贡献描述 |
| 1 | 核心结论与原文矛盾 |
| 0 | 大量编造，输出与原文无关 |

### C. Explainability / 可理解性 (15 分)

衡量标准：是否用人话解释；是否说明"为什么这样做"；是否不是简单复制原文。

| 分值 | 标准 |
|------|------|
| 5 | 人话版真正通俗，非专业读者能理解；解释了 why |
| 4 | 人话版基本可读，偶有术语未解释 |
| 3 | 人话版部分复制原文，但关键点有解释 |
| 2 | 人话版大量复制原文，缺乏解释 |
| 1 | 人话版等于原文或等于公式 |
| 0 | 人话版为空或 UNKNOWN |

### D. Formula Teaching Quality / 公式讲解质量 (15 分)

衡量标准：是否解释符号、作用、输入输出；是否避免 human_explanation = 公式文本。

| 分值 | 标准 |
|------|------|
| 5 | 符号逐个解释，说明作用、输入输出、去除影响、数字例子 |
| 4 | 符号和作用有解释，缺数字例子 |
| 3 | 有基本解释但部分符号未覆盖 |
| 2 | 解释过于泛泛（"该公式用于优化"） |
| 1 | human_explanation 直接是公式文本 |
| 0 | 公式卡为空或编造符号含义 |

### E. Research Thinking / 科研思维 (15 分)

衡量标准：是否讲清核心假设、创新点与代价、适用边界。

| 分值 | 标准 |
|------|------|
| 5 | 清楚说明假设、创新点、代价、适用边界、可能追问点 |
| 4 | 覆盖假设和创新点，缺适用边界 |
| 3 | 有基本描述但缺乏深度分析 |
| 2 | 只描述"做了什么"，不解释"为什么"和"代价" |
| 1 | 输出为泛泛模板（"本文提出一种有效方法"） |
| 0 | 与论文无关 |

### F. Advisor-Readiness / 导师追问准备 (10 分)

衡量标准：追问是否具体、基于证据、包含风险提醒。

| 分值 | 标准 |
|------|------|
| 5 | 问题针对论文具体方法/假设/实验，答案可回指 evidence，有 risk_note |
| 4 | 问题具体，答案基于证据，缺 risk_note |
| 3 | 问题基本相关但偏泛 |
| 2 | 问题模板化（"论文提出了什么方法？"） |
| 1 | 问题与论文无关 |
| 0 | 无追问 |

### G. Non-Genericness / 非模板化 (10 分)

衡量标准：输出是否贴合具体论文，是否包含论文特有术语。

| 分值 | 标准 |
|------|------|
| 5 | 输出包含论文特有术语、任务、机制、数据集名称 |
| 4 | 大部分贴合，个别字段为模板 |
| 3 | 部分贴合，部分为通用模板 |
| 2 | 大部分为通用模板 |
| 1 | 几乎全部为模板句 |
| 0 | 输出与论文完全无关 |

### H. Uncertainty Handling / 不确定性处理 (5 分)

衡量标准：不确定内容是否正确降级。

| 分值 | 标准 |
|------|------|
| 5 | 所有不确定项标 NEEDS_HUMAN_CHECK/INSUFFICIENT_EVIDENCE，confidence 合理 |
| 4 | 绝大部分正确降级，个别遗漏 |
| 3 | 部分降级，部分未标注 |
| 2 | 大量未标注的不确定内容 |
| 1 | 把不确定内容标为确定 |
| 0 | 伪造 confidence 值 |

---

## 3. 评分汇总与阈值

### 总分构成 (100 分)

| 维度 | 分值 | 权重 |
|------|------|------|
| A. Groundedness | 20 | 证据绑定 |
| B. Faithfulness | 20 | 忠实原文 |
| C. Explainability | 15 | 可理解性 |
| D. Formula Teaching | 15 | 公式讲解 |
| E. Research Thinking | 15 | 科研思维 |
| F. Advisor-Readiness | 10 | 追问准备 |
| G. Non-Genericness | 10 | 非模板化 |
| H. Uncertainty Handling | 5 | 不确定性 |
| **总计** | **110** | 按 100 分归一化 |

### 阈值

| 等级 | 分数范围 | 含义 |
|------|----------|------|
| PASS | ≥ 80 | 质量合格，可进入下一阶段 |
| WARNING | 60-79 | 质量有风险，需人工抽查 |
| FAIL | < 60 | 质量不合格，必须修复 |

### Hard-Fail 条件 (任一触发直接 FAIL)

以下任何一条触发，无论总分多少，直接判定 FAIL：

1. **HF-1: 无证据编造** — 核心 claim 无 evidence_ref 且未标降级
2. **HF-2: 公式当人话** — teaching_card 的 human_explanation 大段复制公式文本 (>50% 公式字符)
3. **HF-3: 公式解释错误** — formula_card 的符号含义与原文矛盾
4. **HF-4: 缺 evidence_ref** — paper_card 的 core_idea 或 problem 无 evidence_ref
5. **HF-5: 明显模板化** — 输出不含任何论文特有术语（标题词、方法名、数据集名）
6. **HF-6: 与原文无关** — 输出内容与输入论文的主题明显不符

---

## 4. 自动化质量测试建议

### A. Grounding Tests

| 测试 | 文件 | 检查内容 |
|------|------|----------|
| test_card_evidence_refs_exist_in_index | test_quality_grounding.py | 所有 card 的 evidence_ref 必须存在于 evidence_index |
| test_core_claims_have_evidence_ref | test_quality_grounding.py | paper_card 的 core_idea/problem/method 必须有 evidence_ref |
| test_no_evidence_triggers_degradation | test_quality_grounding.py | 空 evidence_index 时，card 的 evidence_status 必须为 INSUFFICIENT_EVIDENCE |
| test_evidence_ref_format_valid | test_quality_grounding.py | evidence_ref 格式必须是 `{paper_id}:{block_id}` |

### B. Anti-Hallucination Tests

| 测试 | 文件 | 检查内容 |
|------|------|----------|
| test_no_fabricated_accuracy | test_quality_hallucination.py | mock paper 无实验结果时，不能出现 "accuracy", "F1", "SOTA" |
| test_no_fabricated_dataset | test_quality_hallucination.py | mock paper 无数据集时，不能出现 "ImageNet", "CIFAR" 等 |
| test_no_fabricated_formula | test_quality_hallucination.py | mock paper 无公式时，formula_cards 应为空或 FORMULA_UNAVAILABLE |
| test_formula_not_copied_as_explanation | test_quality_hallucination.py | teaching_card 的 human_explanation 不应是公式文本的 >50% |

### C. Formula Quality Tests

| 测试 | 文件 | 检查内容 |
|------|------|----------|
| test_formula_card_has_symbols | test_quality_formula.py | formula_card 的 symbols 列表非空 |
| test_formula_card_has_role | test_quality_formula.py | formula_card 的 purpose 不为 UNKNOWN |
| test_formula_heavy_triggers_conservative | test_quality_formula.py | 公式密集文本触发 conservative fallback，confidence ≤ 0.3 |
| test_formula_heavy_adds_warning | test_quality_formula.py | 公式密集文本添加 FORMULA_HEAVY_TEXT_NEEDS_HUMAN_EXPLANATION warning |

### D. Non-Generic Tests

| 测试 | 文件 | 检查内容 |
|------|------|----------|
| test_output_contains_paper_keywords | test_quality_genericness.py | 输出必须包含输入论文的标题词或方法名 |
| test_no_generic_templates | test_quality_genericness.py | 输出不能只包含 "本文提出一种有效方法" 等模板句 |
| test_selection_reason_specific | test_quality_genericness.py | reading_plan 的 selection_reason 不能全部相同 |
| test_paper_role_explanation_specific | test_quality_genericness.py | teaching_card 的 paper_role_explanation 不能全部为同一模板 |

### E. Advisor Drill Tests (Phase 12+)

| 测试 | 文件 | 检查内容 |
|------|------|----------|
| test_drill_questions_are_specific | test_quality_drill.py (Phase 12) | drill 问题必须包含论文特有术语 |
| test_drill_questions_not_generic | test_quality_drill.py (Phase 12) | drill 问题不能是 "论文提出了什么方法？" |
| test_drill_has_risk_note | test_quality_drill.py (Phase 12) | 不确定问题必须有 risk_note |

### F. Artifact Chain Quality Smoke

| 测试 | 文件 | 检查内容 |
|------|------|----------|
| test_full_chain_produces_all_artifacts | test_quality_smoke.py | 用 fixture paper 跑完整链路，7 个 artifact 全存在 |
| test_full_chain_json_readable | test_quality_smoke.py | 所有 artifact JSON 可反序列化 |
| test_full_chain_no_hard_fail | test_quality_smoke.py | 检查 6 个 hard-fail 条件 |
| test_full_chain_confidence_reasonable | test_quality_smoke.py | 所有 confidence 在 0-1 范围，降级项 confidence ≤ 0.5 |

---

## 5. Fixture Paper 设计

### Fixture 1: 普通方法论文 (fixture_method_paper.md)

用途：测试 paper_card + teaching_cards 的基本质量。

```markdown
# Graph Neural Network for Time Series Anomaly Detection

## Abstract

We propose GraphAD, a graph neural network approach for detecting anomalies
in multivariate time series. Our method constructs a sensor dependency graph
and uses graph convolution to capture inter-sensor correlations. We evaluate
on SWaT and WADI datasets, achieving 95.2% F1-score on SWaT.

## 1. Introduction

Current methods treat each sensor independently, missing cross-sensor
dependencies that are critical for anomaly detection in industrial systems.

## 2. Method

### 2.1 Graph Construction

We build an adjacency matrix A from sensor correlation coefficients.
The graph convolution layer computes: H^(l+1) = σ(D^(-1/2) A D^(-1/2) H^(l) W^(l))

### 2.2 Anomaly Scoring

The reconstruction error e_t = ||x_t - x̂_t||^2 is used as anomaly score.
A threshold θ is set at the 95th percentile of training errors.

## 3. Experiments

Dataset: SWaT (51 sensors, 11 days), WADI (123 sensors, 16 days).
Baselines: LSTM-based detector, Isolation Forest, PCA-based method.
Result: GraphAD achieves 95.2% F1 on SWaT, outperforming LSTM (89.1%).

## 4. Limitations

Our method assumes static graph structure, which may not hold for
dynamically changing sensor relationships. The threshold θ requires
manual tuning per dataset.
```

预期检查点：
- paper_card 的 core_idea 应提到 "graph convolution" 和 "sensor dependency"
- paper_card 的 problem 应提到 "treat each sensor independently"
- teaching_card 的 human_explanation 不应是公式文本
- formula_card 应解释 H^(l+1) 公式的符号
- evidence_ref 应指向 abstract/method/experiment blocks

### Fixture 2: 公式密集论文 (fixture_formula_heavy.md)

用途：测试 formula_cards 质量 + formula-heavy fallback。

```markdown
# Variational Autoencoder with Structured Latent Space

## Abstract

We propose StructVAE, a variational autoencoder that enforces cluster
structure in the latent space using a mixture of Gaussians prior.

## 1. Method

### 1.1 Objective

The ELBO loss is: L = E_q[log p(x|z)] - β * KL(q(z|x) || p(z))
where p(z) = Σ π_k N(μ_k, σ_k^2) is a Gaussian mixture prior.

### 1.2 Reparameterization

We use the reparameterization trick: z = μ + σ * ε, where ε ~ N(0, I).
The KL divergence has closed form: KL = 0.5 * Σ(σ^2 + μ^2 - 1 - log σ^2)

### 1.3 Cluster Assignment

The posterior cluster assignment: p(k|x) = π_k * N(z|μ_k, σ_k^2) / Σ π_j * N(z|μ_j, σ_j^2)

## 2. Experiments

We evaluate on MNIST and Fashion-MNIST for clustering quality.
NMI score: 0.82 on MNIST, outperforming standard VAE (0.65).
```

预期检查点：
- formula_cards 应有 3 个公式卡 (ELBO, reparameterization, cluster assignment)
- 每个 formula_card 的 symbols 应解释 z, μ, σ, ε, β, KL
- teaching_card 的 human_explanation 不应直接是 "L = E_q[log p(x|z)] - β * KL(...)"
- formula-heavy 检测应触发 conservative fallback
- confidence 应降低到 ≤ 0.3

### Fixture 3: 信息不足论文 (fixture_minimal.md)

用途：测试不编造、不确定性处理、fallback。

```markdown
# A Novel Approach to Protein Folding

## Abstract

We propose a new method for protein structure prediction. Our approach
uses deep learning to predict contact maps from amino acid sequences.
Preliminary results suggest improvement over existing methods.
```

预期检查点：
- paper_card 的 experiments 应为 UNKNOWN 或 INSUFFICIENT_EVIDENCE
- paper_card 的 core_idea 应降级 (INSUFFICIENT_EVIDENCE)
- formula_cards 应为空或 FORMULA_UNAVAILABLE
- teaching_card 的 confidence 应 ≤ 0.3
- 不能编造 accuracy、dataset name、baseline name
- 应有 warning: METHOD_SECTION_MISSING, EXPERIMENT_SECTION_MISSING

---

## 6. 当前项目质量缺口分析

### Phase 8: paper_card

| 检查项 | 当前状态 | 缺口 |
|--------|----------|------|
| Schema validity | 已测 | 无 |
| Evidence ref 绑定 | 已测 (test_paper_card_builder.py) | 无 |
| LLM fallback | 已测 | 无 |
| 解释质量 (human_explanation 是否有意义) | **未测** | 需要 non-generic test |
| core_idea 是否包含论文特有术语 | **未测** | 需要 keyword test |
| 空输入时是否正确降级 | 已测 | 无 |

### Phase 9: formula_cards

| 检查项 | 当前状态 | 缺口 |
|--------|----------|------|
| Schema validity | 已测 | 无 |
| Symbol extraction | 已测 | 无 |
| LLM fallback | 已测 | 无 |
| 符号解释是否准确 | **未测** | 需要 formula accuracy test |
| human_explanation 是否避免公式文本 | **部分覆盖** | Phase 10 有 _is_formula_heavy test，但 Phase 9 缺 |
| FORMULA_UNAVAILABLE 降级 | 已测 | 无 |

### Phase 10: teaching_cards

| 检查项 | 当前状态 | 缺口 |
|--------|----------|------|
| Schema validity | 已测 | 无 |
| Five-layer completeness | 已测 | 无 |
| Evidence binding | 已测 | 无 |
| human_explanation 非公式文本 | **已测** (7 个内容质量测试) | 无 |
| paper_role_explanation 非模板化 | **已测** | 无 |
| 空内容降级 | 已测 | 无 |
| 五层内容是否真正有区分度 | **未测** | 需要 differentiation test |

### Phase 11: reading_plan

| 检查项 | 当前状态 | 缺口 |
|--------|----------|------|
| Schema validity | 已测 | 无 |
| Scoring breakdown | 已测 | 无 |
| A_READ ≤ 12 | 已测 | 无 |
| 三路去重 | 已测 | 无 |
| selection_reason 是否具体 | **未测** | 需要 non-generic test |
| 评分是否可解释 | **未测** | 需要 scoring consistency test |

### 总结

**当前测试覆盖 L1 (Schema) 和部分 L2 (Structural)，但 L3 (Content Quality) 基本未覆盖。**

Phase 10 的 7 个内容质量测试是唯一触及 L3 的测试，但只覆盖了 teaching_card 的 human_explanation 公式检测。

---

## 7. 建议的质量测试补全计划

### 立即补 (Phase 12 前)

| 测试 | 优先级 | 理由 |
|------|--------|------|
| test_quality_grounding.py (4 tests) | P0 | 证据绑定是核心安全机制 |
| test_quality_hallucination.py (4 tests) | P0 | 防编造是核心信任基础 |
| test_quality_formula.py (4 tests) | P0 | 公式讲解是核心差异化能力 |
| test_quality_smoke.py (4 tests) | P0 | 全链路质量门禁 |

**预计 16 个测试，覆盖 6 个 hard-fail 条件。**

### Phase 12 前或同时补

| 测试 | 优先级 | 理由 |
|------|--------|------|
| test_quality_genericness.py (4 tests) | P1 | 防模板化 |
| fixture_method_paper.md | P1 | 质量 smoke 的基础 |
| fixture_formula_heavy.md | P1 | 公式质量测试基础 |
| fixture_minimal.md | P1 | 降级测试基础 |

### Phase 12 后补

| 测试 | 优先级 | 理由 |
|------|--------|------|
| test_quality_drill.py (Phase 12) | P2 | drill 质量需 Phase 12 实现后 |
| 多论文 fixture (direction chain) | P2 | direction 链路质量需 Phase 12+ |

---

## 8. 执行建议

### 进入 Phase 12 前是否建议先补质量测试

**建议补 P0 测试 (16 个) 后再进入 Phase 12。** 理由：

1. 质量测试是 Phase 8-11 的"验收门"，当前只有"能跑"的证明，没有"讲得好"的证明
2. P0 测试覆盖 6 个 hard-fail 条件，是系统可信度的基础
3. 补测试不修改业务代码，风险极低
4. Phase 12 (patterns/drill) 会新增 card 类型，如果基础质量门禁不健全，新 card 也可能有质量问题

### 执行顺序建议

1. 确认本文档 (QUALITY_EVALUATION_SPEC.md)
2. 创建 3 个 fixture paper
3. 实现 P0 质量测试 (16 个)
4. 运行全量 pytest 确认无 regression
5. 然后进入 Phase 12

### 与现有测试的关系

质量测试**不替代**现有测试。现有测试覆盖 L1 (Schema) + 部分 L2 (Structural)，质量测试覆盖 L2/L3 (Content Quality)。两者互补。

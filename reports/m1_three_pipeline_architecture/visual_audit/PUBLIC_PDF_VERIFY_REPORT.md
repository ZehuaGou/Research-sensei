# PUBLIC_PDF_VERIFY_REPORT

**Generated**: 2026-06-09
**Total FormulaSlots**: 43

---

## 1. Overview

| paper | title_verified | public_pdf_url | formula_count | crop_exists | overlay_exists | latex_match | canonical_match | section_trusted | public_pdf_context_found |
|-------|---------------|---------------|:-------------:|:-----------:|:--------------:|:-----------:|:---------------:|:---------------:|:------------------------:|
| paper_1 | YES_WITH_BAD_METADATA | https://arxiv.org/pdf/2110.02642 | 9 | 9/9 | 5/9 | 9/9 | 9/9 | 9/9 | 9/9 |
| paper_2 | YES_WITH_BAD_METADATA | https://arxiv.org/pdf/2104.03466 | 16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 |
| paper_3 | YES | https://arxiv.org/pdf/2510.18998 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 0/18 | 17/18 |

---

## 2. Per-Paper Detail

### paper_1 — 2110.02642

- **title_from_report**: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy
- **title_from_pdf_metadata**: 
- **title_from_pdf_body**: ANOMALY TRANSFORMER: TIME SERIES ANOMALY
- **title_verified**: YES_WITH_BAD_METADATA
- **title_detail**: body text matches but metadata is ''
- **public_pdf_url**: https://arxiv.org/pdf/2110.02642
- **formula_count**: 9
- **crop_exists**: 9/9
- **overlay_exists**: 5/9
- **latex_non_empty**: 9/9
- **marker_vs_final_match**: 9/9
- **final_vs_canonical_match**: 9/9
- **trusted_section**: 9/9
- **polluted_section**: 0/9
- **public_pdf_context_found**: 9/9

### paper_2 — W3184127157

- **title_from_report**: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT
- **title_from_pdf_metadata**: 
- **title_from_pdf_body**: Learning Graph Structures with Transformer for
- **title_verified**: YES_WITH_BAD_METADATA
- **title_detail**: body text matches but metadata is ''
- **public_pdf_url**: https://arxiv.org/pdf/2104.03466
- **formula_count**: 16
- **crop_exists**: 16/16
- **overlay_exists**: 16/16
- **latex_non_empty**: 16/16
- **marker_vs_final_match**: 16/16
- **final_vs_canonical_match**: 16/16
- **trusted_section**: 16/16
- **polluted_section**: 0/16
- **public_pdf_context_found**: 16/16

### paper_3 — 2510.18998

- **title_from_report**: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection
- **title_from_pdf_metadata**: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version
- **title_from_pdf_body**: An Encode-then-Decompose Approach to
- **title_verified**: YES
- **title_detail**: metadata matches
- **public_pdf_url**: https://arxiv.org/pdf/2510.18998
- **formula_count**: 18
- **crop_exists**: 18/18
- **overlay_exists**: 18/18
- **latex_non_empty**: 18/18
- **marker_vs_final_match**: 18/18
- **final_vs_canonical_match**: 18/18
- **trusted_section**: 0/18
- **polluted_section**: 11/18
- **public_pdf_context_found**: 17/18

---

## 3. Full Formula Verification Table

| # | paper | formula_id | page | section | crop | overlay | marker_latex | final_latex | canonical | origin | public_ctx | trusted | polluted |
|---|-------|-----------|-----:|---------|------|---------|-------------|------------|-----------|--------|-----------|---------|----------|
| 1 | paper_1 | formula_001 | 3 | Unknown | Y | Y | `\begin{split} \mathcal{Z}^{l} ...` | `\begin{split} \mathcal{Z}^{l} ...` | Y | parser_latex | Y | Y | N |
| 2 | paper_1 | formula_002 | 3 | Unknown | Y | Y | `\mathcal{Q}, \mathcal{K}, \mat...` | `\mathcal{Q}, \mathcal{K}, \mat...` | Y | parser_latex | Y | Y | N |
| 3 | paper_1 | formula_003 | 4 | Unknown | Y | Y | `\operatorname{AssDis}(\mathcal...` | `\operatorname{AssDis}(\mathcal...` | Y | parser_latex | Y | Y | N |
| 4 | paper_1 | formula_004 | 4 | Unknown | Y | Y | `\mathcal{L}_{Total}(\widehat{\...` | `\mathcal{L}_{Total}(\widehat{\...` | Y | parser_latex | Y | Y | N |
| 5 | paper_1 | formula_005 | 4 | Unknown | Y | Y | `\mathcal{L}_{Total}(\widehat{\...` | `\mathcal{L}_{Total}(\widehat{\...` | Y | parser_latex | Y | Y | N |
| 6 | paper_1 | formula_006 | 5 | Unknown | Y | N | `AnomalyScore(\mathcal{X}) = So...` | `AnomalyScore(\mathcal{X}) = So...` | Y | parser_latex | Y | Y | N |
| 7 | paper_1 | formula_007 | 14 | Unknown | Y | N | `\begin{aligned} &1: \ \mathcal...` | `\begin{aligned} &1: \ \mathcal...` | Y | parser_latex | Y | Y | N |
| 8 | paper_1 | formula_008 | 15 | Unknown | Y | N | `\mathcal{C}_{AD} = \text{Softm...` | `\mathcal{C}_{AD} = \text{Softm...` | Y | parser_latex | Y | Y | N |
| 9 | paper_1 | formula_009 | 15 | Unknown | Y | N | `\mathcal{X}` | `\mathcal{X}` | Y | parser_latex | Y | Y | N |
| 10 | paper_2 | formula_001 | 3 | Related Work | Y | Y | `z^{i,j} = \underset{c \in \{0,...` | `z^{i,j} = \underset{c \in \{0,...` | Y | parser_latex | Y | Y | N |
| 11 | paper_2 | formula_002 | 3 | Related Work | Y | Y | `z_c^{i,j} = \frac{\exp((\log \...` | `z_c^{i,j} = \frac{\exp((\log \...` | Y | parser_latex | Y | Y | N |
| 12 | paper_2 | formula_003 | 3 | Related Work | Y | Y | `\mathbf{x}_{i}' = \sum_{j \in ...` | `\mathbf{x}_{i}' = \sum_{j \in ...` | Y | parser_latex | Y | Y | N |
| 13 | paper_2 | formula_004 | 4 | Method | Y | Y | `\mathcal{L}_s = \sum_{1 \le i,...` | `\mathcal{L}_s = \sum_{1 \le i,...` | Y | parser_latex | Y | Y | N |
| 14 | paper_2 | formula_005 | 4 | Method | Y | Y | `\frac{QK^T}{\sqrt{d_k}}` | `\frac{QK^T}{\sqrt{d_k}}` | Y | parser_latex | Y | Y | N |
| 15 | paper_2 | formula_006 | 5 | Method | Y | Y | `MultiHead(\mathbf{Q}, \mathbf{...` | `MultiHead(\mathbf{Q}, \mathbf{...` | Y | parser_latex | Y | Y | N |
| 16 | paper_2 | formula_007 | 5 | Method | Y | Y | `head_i = Attention(\mathbf{Q}W...` | `head_i = Attention(\mathbf{Q}W...` | Y | parser_latex | Y | Y | N |
| 17 | paper_2 | formula_008 | 5 | Method | Y | Y | `Attention(S, V) = Softmax(S)V` | `Attention(S, V) = Softmax(S)V` | Y | parser_latex | Y | Y | N |
| 18 | paper_2 | formula_009 | 5 | Method | Y | Y | `\mathbf{A}^{(1)}, \mathbf{A}^{...` | `\mathbf{A}^{(1)}, \mathbf{A}^{...` | Y | parser_latex | Y | Y | N |
| 19 | paper_2 | formula_010 | 5 | Method | Y | Y | `\mathbf{X}^{(1)} \in \mathcal{...` | `\mathbf{X}^{(1)} \in \mathcal{...` | Y | parser_latex | Y | Y | N |
| 20 | paper_2 | formula_011 | 6 | Method | Y | Y | `\mathcal{L}_{mse} = \frac{1}{M...` | `\mathcal{L}_{mse} = \frac{1}{M...` | Y | parser_latex | Y | Y | N |
| 21 | paper_2 | formula_012 | 6 | Method | Y | Y | `\hat{\mathbf{y}}^{(t)} = \sum_...` | `\hat{\mathbf{y}}^{(t)} = \sum_...` | Y | parser_latex | Y | Y | N |
| 22 | paper_2 | formula_013 | 6 | Method | Y | Y | `\tilde{x} = \frac{x - \min X_{...` | `\tilde{x} = \frac{x - \min X_{...` | Y | parser_latex | Y | Y | N |
| 23 | paper_2 | formula_014 | 6 | Method | Y | Y | `Precision = \frac{TP}{TP + FP}` | `Precision = \frac{TP}{TP + FP}` | Y | parser_latex | Y | Y | N |
| 24 | paper_2 | formula_015 | 6 | Method | Y | Y | `Recall = \frac{TP}{TP + FN}` | `Recall = \frac{TP}{TP + FN}` | Y | parser_latex | Y | Y | N |
| 25 | paper_2 | formula_016 | 6 | Method | Y | Y | `F1 = 2 \times \frac{\text{Prec...` | `F1 = 2 \times \frac{\text{Prec...` | Y | parser_latex | Y | Y | N |
| 26 | paper_3 | formula_001 | 2 | Training Data Clean Time Series
Contaminated Time Series | Y | Y | `I(X,Y) = \sum_{x \in X} \sum_{...` | `I(X,Y) = \sum_{x \in X} \sum_{...` | Y | parser_latex | Y | N | N |
| 27 | paper_3 | formula_002 | 2 | Training Data Clean Time Series
Contaminated Time Series | Y | Y | `I_{\text{UBA}}(X,Y) \triangleq...` | `I_{\text{UBA}}(X,Y) \triangleq...` | Y | parser_latex | Y | N | N |
| 28 | paper_3 | formula_003 | 2 | Training Data Clean Time Series
Contaminated Time Series | Y | Y | `q(x/y) = \frac{p(x)}{Z(y)}e^{f...` | `q(x/y) = \frac{p(x)}{Z(y)}e^{f...` | Y | parser_latex | Y | N | N |
| 29 | paper_3 | formula_004 | 3 | Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco | Y | Y | `\mathbf{H}_{t:t+B} = \frac{\ma...` | `\mathbf{H}_{t:t+B} = \frac{\ma...` | Y | parser_latex | Y | N | Y |
| 30 | paper_3 | formula_005 | 3 | A time series T = ⟨s1, s2, . . . , sN⟩is a sequence of N
time-ordered observatio | Y | Y | `\mathbf{H}_{\text{emb}} = \mat...` | `\mathbf{H}_{\text{emb}} = \mat...` | Y | parser_latex | Y | N | Y |
| 31 | paper_3 | formula_006 | 3 | A time series T = ⟨s1, s2, . . . , sN⟩is a sequence of N
time-ordered observatio | Y | Y | `\mathbf{Q} = \mathbf{W}_{\math...` | `\mathbf{Q} = \mathbf{W}_{\math...` | Y | parser_latex | Y | N | Y |
| 32 | paper_3 | formula_007 | 3 | Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco | Y | Y | `\mathbf{Y}_1 = \mathbf{W}_{\te...` | `\mathbf{Y}_1 = \mathbf{W}_{\te...` | Y | parser_latex | Y | N | Y |
| 33 | paper_3 | formula_008 | 3 | Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco | Y | Y | `\mathbf{Y}_{2} = \mathbf{Y}_{1...` | `\mathbf{Y}_{2} = \mathbf{Y}_{1...` | Y | parser_latex | Y | N | Y |
| 34 | paper_3 | formula_009 | 3 | Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco | Y | Y | `\mathbf{Y}_3 = \mathbf{W}_2 \c...` | `\mathbf{Y}_3 = \mathbf{W}_2 \c...` | Y | parser_latex | Y | N | Y |
| 35 | paper_3 | formula_010 | 4 | Y1 = Wmult · [Y1
1, . . . , YM
1 ]⊤
(7) | Y | Y | `\begin{aligned} \mathbf{Y}_{\t...` | `\begin{aligned} \mathbf{Y}_{\t...` | Y | parser_latex | Y | N | Y |
| 36 | paper_3 | formula_011 | 4 | Var[Y1] + ϵ
· γ2 + β2
(8) | Y | Y | `\mathcal{L}_{aux} = \/\text{sh...` | `\mathcal{L}_{aux} = \/\text{sh...` | Y | parser_latex | Y | N | N |
| 37 | paper_3 | formula_012 | 5 | Add & Norm | Y | Y | `\begin{aligned} \mathbf{Y}_{\t...` | `\begin{aligned} \mathbf{Y}_{\t...` | Y | parser_latex | N | N | N |
| 38 | paper_3 | formula_013 | 5 | (b) EDAD Achitecture
(a) Attention Module | Y | Y | `\mathcal{L}_{\text{sta}} = \/\...` | `\mathcal{L}_{\text{sta}} = \/\...` | Y | parser_latex | Y | N | N |
| 39 | paper_3 | formula_014 | 5 | (b) EDAD Achitecture
(a) Attention Module | Y | Y | `I_{\text{InfoNCE}} = \mathbb{E...` | `I_{\text{InfoNCE}} = \mathbb{E...` | Y | parser_latex | Y | N | N |
| 40 | paper_3 | formula_015 | 5 | 2
and Yaux ∈RB× d | Y | Y | `f_{\theta}(\mathbf{Y}, \mathbf...` | `f_{\theta}(\mathbf{Y}, \mathbf...` | Y | parser_latex | Y | N | Y |
| 41 | paper_3 | formula_016 | 5 | 2
and Yaux ∈RB× d | Y | Y | `\mathcal{L}_{\text{reg}} = \/\...` | `\mathcal{L}_{\text{reg}} = \/\...` | Y | parser_latex | Y | N | Y |
| 42 | paper_3 | formula_017 | 5 | Laux = ∥shuffle(Y) −ˆYaux∥2
F
(11) | Y | Y | `\mathcal{L} = \lambda_1 \cdot ...` | `\mathcal{L} = \lambda_1 \cdot ...` | Y | parser_latex | Y | N | Y |
| 43 | paper_3 | formula_018 | 6 | Lsta = ∥Y −ˆYsta∥2
F −Iθ(Y, Ysta)
(13) | Y | Y | `\mathcal{AS}(\mathbf{s}_i) = -...` | `\mathcal{AS}(\mathbf{s}_i) = -...` | Y | parser_latex | Y | N | Y |

---

## 4. High-Risk Items

| priority | paper | formula_id | reason | what_to_check |
|----------|-------|-----------|--------|---------------|
| HIGH | paper_1 | formula_006 | OVERLAY_MISSING | Overlay file not found |
| HIGH | paper_1 | formula_007 | OVERLAY_MISSING | Overlay file not found |
| HIGH | paper_1 | formula_008 | OVERLAY_MISSING | Overlay file not found |
| HIGH | paper_1 | formula_009 | OVERLAY_MISSING | Overlay file not found |
| HIGH | paper_3 | formula_004 | SECTION_POLLUTED | Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' contains formula text |
| HIGH | paper_3 | formula_005 | SECTION_POLLUTED | Section 'A time series T = ⟨s1, s2, . . . , sN⟩is a sequence of N
time-ordered observatio' contains formula text |
| HIGH | paper_3 | formula_006 | SECTION_POLLUTED | Section 'A time series T = ⟨s1, s2, . . . , sN⟩is a sequence of N
time-ordered observatio' contains formula text |
| HIGH | paper_3 | formula_007 | SECTION_POLLUTED | Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' contains formula text |
| HIGH | paper_3 | formula_008 | SECTION_POLLUTED | Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' contains formula text |
| HIGH | paper_3 | formula_009 | SECTION_POLLUTED | Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' contains formula text |
| HIGH | paper_3 | formula_010 | SECTION_POLLUTED | Section 'Y1 = Wmult · [Y1
1, . . . , YM
1 ]⊤
(7)' contains formula text |
| HIGH | paper_3 | formula_015 | SECTION_POLLUTED | Section '2
and Yaux ∈RB× d' contains formula text |
| HIGH | paper_3 | formula_016 | SECTION_POLLUTED | Section '2
and Yaux ∈RB× d' contains formula text |
| HIGH | paper_3 | formula_017 | SECTION_POLLUTED | Section 'Laux = ∥shuffle(Y) −ˆYaux∥2
F
(11)' contains formula text |
| HIGH | paper_3 | formula_018 | SECTION_POLLUTED | Section 'Lsta = ∥Y −ˆYsta∥2
F −Iθ(Y, Ysta)
(13)' contains formula text |

---

## 5. Risk Summary

- **HIGH**: 15
- **MEDIUM**: 18
- **LOW**: 3
- **Total**: 36

### MEDIUM Priority

1. **paper_3/formula_001** — SECTION_UNKNOWN: Section 'Training Data Clean Time Series
Contaminated Time Series' is not trusted
1. **paper_3/formula_002** — SECTION_UNKNOWN: Section 'Training Data Clean Time Series
Contaminated Time Series' is not trusted
1. **paper_3/formula_003** — SECTION_UNKNOWN: Section 'Training Data Clean Time Series
Contaminated Time Series' is not trusted
1. **paper_3/formula_004** — SECTION_UNKNOWN: Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' is not trusted
1. **paper_3/formula_005** — SECTION_UNKNOWN: Section 'A time series T = ⟨s1, s2, . . . , sN⟩is a sequence of N
time-ordered observatio' is not trusted
1. **paper_3/formula_006** — SECTION_UNKNOWN: Section 'A time series T = ⟨s1, s2, . . . , sN⟩is a sequence of N
time-ordered observatio' is not trusted
1. **paper_3/formula_007** — SECTION_UNKNOWN: Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' is not trusted
1. **paper_3/formula_008** — SECTION_UNKNOWN: Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' is not trusted
1. **paper_3/formula_009** — SECTION_UNKNOWN: Section 'Given a time series T
= ⟨s1, s2, . . . , sN⟩, we aim at
computing an anomaly sco' is not trusted
1. **paper_3/formula_010** — SECTION_UNKNOWN: Section 'Y1 = Wmult · [Y1
1, . . . , YM
1 ]⊤
(7)' is not trusted
1. **paper_3/formula_011** — SECTION_UNKNOWN: Section 'Var[Y1] + ϵ
· γ2 + β2
(8)' is not trusted
1. **paper_3/formula_012** — SECTION_UNKNOWN: Section 'Add & Norm' is not trusted
1. **paper_3/formula_013** — SECTION_UNKNOWN: Section '(b) EDAD Achitecture
(a) Attention Module' is not trusted
1. **paper_3/formula_014** — SECTION_UNKNOWN: Section '(b) EDAD Achitecture
(a) Attention Module' is not trusted
1. **paper_3/formula_015** — SECTION_UNKNOWN: Section '2
and Yaux ∈RB× d' is not trusted
1. **paper_3/formula_016** — SECTION_UNKNOWN: Section '2
and Yaux ∈RB× d' is not trusted
1. **paper_3/formula_017** — SECTION_UNKNOWN: Section 'Laux = ∥shuffle(Y) −ˆYaux∥2
F
(11)' is not trusted
1. **paper_3/formula_018** — SECTION_UNKNOWN: Section 'Lsta = ∥Y −ˆYsta∥2
F −Iθ(Y, Ysta)
(13)' is not trusted

### LOW Priority

1. **paper_1/(paper-level)** — BAD_PDF_METADATA: body text matches but metadata is ''. Content is correct, metadata is bad.
1. **paper_2/(paper-level)** — BAD_PDF_METADATA: body text matches but metadata is ''. Content is correct, metadata is bad.
1. **paper_3/formula_012** — PUBLIC_PDF_CONTEXT_NOT_FOUND: Could not match nearby text in public PDF

---

## 6. Source/Title Mismatch Alert

No source/title mismatches detected.

---

## 7. M1 Review Status

All papers pass source/title verification. No blocks.

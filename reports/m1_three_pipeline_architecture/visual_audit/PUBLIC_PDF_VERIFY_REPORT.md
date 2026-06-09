# PUBLIC_PDF_VERIFY_REPORT

**Generated**: 2026-06-09
**Total FormulaSlots**: 37

---

## 1. Overview

| paper | title_verified | public_pdf_url | formula_count | crop_exists | overlay_exists | latex_match | canonical_match | section_trusted | public_pdf_context_found |
|-------|---------------|---------------|:-------------:|:-----------:|:--------------:|:-----------:|:---------------:|:---------------:|:------------------------:|
| paper_1 | PARTIAL | https://arxiv.org/pdf/2112.14436 | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| paper_2 | TITLE_MISMATCH | https://arxiv.org/pdf/2104.03466 | 16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 | 16/16 |
| paper_3 | YES | https://arxiv.org/pdf/2510.18998 | 18 | 18/18 | 18/18 | 18/18 | 18/18 | 18/18 | 17/18 |

---

## 2. Per-Paper Detail

### paper_1 — 2112.14436

- **title_from_report**: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy
- **title_from_pdf**: Monte Carlo EM for Deep Time Series Anomaly Detection
- **title_verified**: PARTIAL
- **public_pdf_url**: https://arxiv.org/pdf/2112.14436
- **formula_count**: 3
- **crop_exists**: 3/3
- **overlay_exists**: 3/3
- **latex_non_empty**: 3/3
- **marker_vs_final_match**: 3/3
- **final_vs_canonical_match**: 3/3
- **trusted_section**: 3/3
- **polluted_section**: 0/3
- **public_pdf_context_found**: 3/3

### paper_2 — W3184127157

- **title_from_report**: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT
- **title_from_pdf**: 1
- **title_verified**: TITLE_MISMATCH
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
- **title_from_pdf**: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version
- **title_verified**: YES
- **public_pdf_url**: https://arxiv.org/pdf/2510.18998
- **formula_count**: 18
- **crop_exists**: 18/18
- **overlay_exists**: 18/18
- **latex_non_empty**: 18/18
- **marker_vs_final_match**: 18/18
- **final_vs_canonical_match**: 18/18
- **trusted_section**: 18/18
- **polluted_section**: 0/18
- **public_pdf_context_found**: 17/18

---

## 3. Full Formula Verification Table

| # | paper | formula_id | page | section | crop | overlay | marker_latex | final_latex | canonical | origin | public_ctx | trusted | polluted |
|---|-------|-----------|-----:|---------|------|---------|-------------|------------|-----------|--------|-----------|---------|----------|
| 1 | paper_1 | formula_001 | 1 | Introduction | Y | Y | `p(\mathbf{x}/z) = \begin{cases...` | `p(\mathbf{x}/z) = \begin{cases...` | Y | parser_latex | Y | Y | N |
| 2 | paper_1 | formula_002 | 2 | Method | Y | Y | `p(\mathbf{x}_t/z_t=0) = p_{\th...` | `p(\mathbf{x}_t/z_t=0) = p_{\th...` | Y | parser_latex | Y | Y | N |
| 3 | paper_1 | formula_003 | 2 | Method | Y | Y | `p(\mathbf{x}_t/z_t=1) = p^-(\m...` | `p(\mathbf{x}_t/z_t=1) = p^-(\m...` | Y | parser_latex | Y | Y | N |
| 4 | paper_2 | formula_001 | 3 | Related Work | Y | Y | `z^{i,j} = \underset{c \in \{0,...` | `z^{i,j} = \underset{c \in \{0,...` | Y | parser_latex | Y | Y | N |
| 5 | paper_2 | formula_002 | 3 | Related Work | Y | Y | `z_c^{i,j} = \frac{\exp((\log \...` | `z_c^{i,j} = \frac{\exp((\log \...` | Y | parser_latex | Y | Y | N |
| 6 | paper_2 | formula_003 | 3 | Related Work | Y | Y | `\mathbf{x}_{i}' = \sum_{j \in ...` | `\mathbf{x}_{i}' = \sum_{j \in ...` | Y | parser_latex | Y | Y | N |
| 7 | paper_2 | formula_004 | 4 | Method | Y | Y | `\mathcal{L}_s = \sum_{1 \le i,...` | `\mathcal{L}_s = \sum_{1 \le i,...` | Y | parser_latex | Y | Y | N |
| 8 | paper_2 | formula_005 | 4 | Method | Y | Y | `\frac{QK^T}{\sqrt{d_k}}` | `\frac{QK^T}{\sqrt{d_k}}` | Y | parser_latex | Y | Y | N |
| 9 | paper_2 | formula_006 | 5 | Method | Y | Y | `MultiHead(\mathbf{Q}, \mathbf{...` | `MultiHead(\mathbf{Q}, \mathbf{...` | Y | parser_latex | Y | Y | N |
| 10 | paper_2 | formula_007 | 5 | Method | Y | Y | `head_i = Attention(\mathbf{Q}W...` | `head_i = Attention(\mathbf{Q}W...` | Y | parser_latex | Y | Y | N |
| 11 | paper_2 | formula_008 | 5 | Method | Y | Y | `Attention(S, V) = Softmax(S)V` | `Attention(S, V) = Softmax(S)V` | Y | parser_latex | Y | Y | N |
| 12 | paper_2 | formula_009 | 5 | Method | Y | Y | `\mathbf{A}^{(1)}, \mathbf{A}^{...` | `\mathbf{A}^{(1)}, \mathbf{A}^{...` | Y | parser_latex | Y | Y | N |
| 13 | paper_2 | formula_010 | 5 | Method | Y | Y | `\mathbf{X}^{(1)} \in \mathcal{...` | `\mathbf{X}^{(1)} \in \mathcal{...` | Y | parser_latex | Y | Y | N |
| 14 | paper_2 | formula_011 | 6 | Method | Y | Y | `\mathcal{L}_{mse} = \frac{1}{M...` | `\mathcal{L}_{mse} = \frac{1}{M...` | Y | parser_latex | Y | Y | N |
| 15 | paper_2 | formula_012 | 6 | Method | Y | Y | `\hat{\mathbf{y}}^{(t)} = \sum_...` | `\hat{\mathbf{y}}^{(t)} = \sum_...` | Y | parser_latex | Y | Y | N |
| 16 | paper_2 | formula_013 | 6 | Method | Y | Y | `\tilde{x} = \frac{x - \min X_{...` | `\tilde{x} = \frac{x - \min X_{...` | Y | parser_latex | Y | Y | N |
| 17 | paper_2 | formula_014 | 6 | Method | Y | Y | `Precision = \frac{TP}{TP + FP}` | `Precision = \frac{TP}{TP + FP}` | Y | parser_latex | Y | Y | N |
| 18 | paper_2 | formula_015 | 6 | Method | Y | Y | `Recall = \frac{TP}{TP + FN}` | `Recall = \frac{TP}{TP + FN}` | Y | parser_latex | Y | Y | N |
| 19 | paper_2 | formula_016 | 6 | Method | Y | Y | `F1 = 2 \times \frac{\text{Prec...` | `F1 = 2 \times \frac{\text{Prec...` | Y | parser_latex | Y | Y | N |
| 20 | paper_3 | formula_001 | 2 | Introduction | Y | Y | `I(X,Y) = \sum_{x \in X} \sum_{...` | `I(X,Y) = \sum_{x \in X} \sum_{...` | Y | parser_latex | Y | Y | N |
| 21 | paper_3 | formula_002 | 2 | Introduction | Y | Y | `I_{\text{UBA}}(X,Y) \triangleq...` | `I_{\text{UBA}}(X,Y) \triangleq...` | Y | parser_latex | Y | Y | N |
| 22 | paper_3 | formula_003 | 2 | Introduction | Y | Y | `q(x/y) = \frac{p(x)}{Z(y)}e^{f...` | `q(x/y) = \frac{p(x)}{Z(y)}e^{f...` | Y | parser_latex | Y | Y | N |
| 23 | paper_3 | formula_004 | 3 | Method | Y | Y | `\mathbf{H}_{t:t+B} = \frac{\ma...` | `\mathbf{H}_{t:t+B} = \frac{\ma...` | Y | parser_latex | Y | Y | N |
| 24 | paper_3 | formula_005 | 3 | Method | Y | Y | `\mathbf{H}_{\text{emb}} = \mat...` | `\mathbf{H}_{\text{emb}} = \mat...` | Y | parser_latex | Y | Y | N |
| 25 | paper_3 | formula_006 | 3 | Method | Y | Y | `\mathbf{Q} = \mathbf{W}_{\math...` | `\mathbf{Q} = \mathbf{W}_{\math...` | Y | parser_latex | Y | Y | N |
| 26 | paper_3 | formula_007 | 3 | Method | Y | Y | `\mathbf{Y}_1 = \mathbf{W}_{\te...` | `\mathbf{Y}_1 = \mathbf{W}_{\te...` | Y | parser_latex | Y | Y | N |
| 27 | paper_3 | formula_008 | 3 | Method | Y | Y | `\mathbf{Y}_{2} = \mathbf{Y}_{1...` | `\mathbf{Y}_{2} = \mathbf{Y}_{1...` | Y | parser_latex | Y | Y | N |
| 28 | paper_3 | formula_009 | 3 | Method | Y | Y | `\mathbf{Y}_3 = \mathbf{W}_2 \c...` | `\mathbf{Y}_3 = \mathbf{W}_2 \c...` | Y | parser_latex | Y | Y | N |
| 29 | paper_3 | formula_010 | 4 | Method | Y | Y | `\begin{aligned} \mathbf{Y}_{\t...` | `\begin{aligned} \mathbf{Y}_{\t...` | Y | parser_latex | Y | Y | N |
| 30 | paper_3 | formula_011 | 4 | Method | Y | Y | `\mathcal{L}_{aux} = \/\text{sh...` | `\mathcal{L}_{aux} = \/\text{sh...` | Y | parser_latex | Y | Y | N |
| 31 | paper_3 | formula_012 | 5 | Method | Y | Y | `\begin{aligned} \mathbf{Y}_{\t...` | `\begin{aligned} \mathbf{Y}_{\t...` | Y | parser_latex | N | Y | N |
| 32 | paper_3 | formula_013 | 5 | Method | Y | Y | `\mathcal{L}_{\text{sta}} = \/\...` | `\mathcal{L}_{\text{sta}} = \/\...` | Y | parser_latex | Y | Y | N |
| 33 | paper_3 | formula_014 | 5 | Method | Y | Y | `I_{\text{InfoNCE}} = \mathbb{E...` | `I_{\text{InfoNCE}} = \mathbb{E...` | Y | parser_latex | Y | Y | N |
| 34 | paper_3 | formula_015 | 5 | Method | Y | Y | `f_{\theta}(\mathbf{Y}, \mathbf...` | `f_{\theta}(\mathbf{Y}, \mathbf...` | Y | parser_latex | Y | Y | N |
| 35 | paper_3 | formula_016 | 5 | Method | Y | Y | `\mathcal{L}_{\text{reg}} = \/\...` | `\mathcal{L}_{\text{reg}} = \/\...` | Y | parser_latex | Y | Y | N |
| 36 | paper_3 | formula_017 | 5 | Method | Y | Y | `\mathcal{L} = \lambda_1 \cdot ...` | `\mathcal{L} = \lambda_1 \cdot ...` | Y | parser_latex | Y | Y | N |
| 37 | paper_3 | formula_018 | 6 | Method | Y | Y | `\mathcal{AS}(\mathbf{s}_i) = -...` | `\mathcal{AS}(\mathbf{s}_i) = -...` | Y | parser_latex | Y | Y | N |

---

## 4. High-Risk Items

| priority | paper | formula_id | reason | what_to_check |
|----------|-------|-----------|--------|---------------|
| LOW | paper_3 | formula_012 | PUBLIC_PDF_CONTEXT_NOT_FOUND | Could not match nearby text in public PDF |

---

## 5. Manual Check Recommendations

### LOW Priority

1. **paper_3/formula_012** — PUBLIC_PDF_CONTEXT_NOT_FOUND: Could not match nearby text in public PDF

---

## 6. TITLE_MISMATCH Alert

**paper_2**: TITLE MISMATCH DETECTED!
- title_from_report: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT
- title_from_pdf: 1
- public_pdf_url: https://arxiv.org/pdf/2104.03466
- Action required: Verify that the local source.pdf matches the intended paper.

# PUBLIC_PDF_VERIFY_MAP

**Generated**: 2026-06-09
**Total FormulaSlots**: 43

## Paper Sources

### paper_1
- paper_id: 2110.02642
- title_from_report: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy
- title_from_pdf_metadata: 
- title_from_pdf_body: ANOMALY TRANSFORMER: TIME SERIES ANOMALY
- title_verified: **YES_WITH_BAD_METADATA**
- title_detail: body text matches but metadata is ''
- arxiv_id: 2110.02642
- public_pdf_url: https://arxiv.org/pdf/2110.02642
- source_pdf_path: reports\m1_parser_review\paper_1\source.pdf

### paper_2
- paper_id: W3184127157
- title_from_report: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT
- title_from_pdf_metadata: 
- title_from_pdf_body: Learning Graph Structures with Transformer for
- title_verified: **YES_WITH_BAD_METADATA**
- title_detail: body text matches but metadata is ''
- arxiv_id: 2104.03466
- public_pdf_url: https://arxiv.org/pdf/2104.03466
- source_pdf_path: reports\m1_parser_review\paper_2\source.pdf

### paper_3
- paper_id: 2510.18998
- title_from_report: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection
- title_from_pdf_metadata: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version
- title_from_pdf_body: An Encode-then-Decompose Approach to
- title_verified: **YES**
- title_detail: metadata matches
- arxiv_id: 2510.18998
- public_pdf_url: https://arxiv.org/pdf/2510.18998
- source_pdf_path: reports\m1_parser_review\paper_3\source.pdf

## Verification Table

| paper | formula_id | page | section | crop | overlay | marker_latex | final_latex | canonical_match | origin | public_ctx |
|-------|-----------|-----:|---------|------|---------|-------------|------------|-----------------|--------|-----------|
| paper_1 | formula_001 | 3 | Method | YES | YES | `\begin{split} \mathcal{Z}^{l} &= \text{L` | `\begin{split} \mathcal{Z}^{l} &= \text{L` | YES | parser_latex | YES |
| paper_1 | formula_002 | 3 | Method | YES | YES | `\mathcal{Q}, \mathcal{K}, \mathcal{V}, \` | `\mathcal{Q}, \mathcal{K}, \mathcal{V}, \` | YES | parser_latex | YES |
| paper_1 | formula_003 | 4 | Method | YES | YES | `AssDis(\mathcal{P}, \mathcal{S}; \mathca` | `AssDis(\mathcal{P}, \mathcal{S}; \mathca` | YES | parser_latex | YES |
| paper_1 | formula_004 | 4 | Method | YES | YES | `\mathcal{L}_{\text{Total}}(\widehat{\mat` | `\mathcal{L}_{\text{Total}}(\widehat{\mat` | YES | parser_latex | YES |
| paper_1 | formula_005 | 4 | Method | YES | YES | `\mathcal{L}_{Total}(\widehat{\mathcal{X}` | `\mathcal{L}_{Total}(\widehat{\mathcal{X}` | YES | parser_latex | YES |
| paper_1 | formula_006 | 5 | Method | YES | YES | `\mathcal{X}` | `\mathcal{X}` | YES | parser_latex | YES |
| paper_1 | formula_007 | 14 | Conclusion | YES | YES | `\begin{aligned} &1: \ \mathcal{P}' = \te` | `\begin{aligned} &1: \ \mathcal{P}' = \te` | YES | parser_latex | YES |
| paper_1 | formula_008 | 15 | Conclusion | YES | YES | `\mathcal{C}_{AD} = \text{Softmax}(-\text` | `\mathcal{C}_{AD} = \text{Softmax}(-\text` | YES | parser_latex | YES |
| paper_1 | formula_009 | 15 | Conclusion | YES | YES | `\mathcal{X}` | `\mathcal{X}` | YES | parser_latex | YES |
| paper_2 | formula_001 | 3 | Related Work | YES | YES | `z^{i,j} = \underset{c \in \{0,1\}}{\arg ` | `z^{i,j} = \underset{c \in \{0,1\}}{\arg ` | YES | parser_latex | YES |
| paper_2 | formula_002 | 3 | Related Work | YES | YES | `z_c^{i,j} = \frac{\exp((\log \pi_c^{i,j}` | `z_c^{i,j} = \frac{\exp((\log \pi_c^{i,j}` | YES | parser_latex | YES |
| paper_2 | formula_003 | 3 | Method | YES | YES | `\mathbf{x}_{i}' = \sum_{j \in \mathcal{N` | `\mathbf{x}_{i}' = \sum_{j \in \mathcal{N` | YES | parser_latex | YES |
| paper_2 | formula_004 | 4 | Method | YES | YES | `\mathcal{L}_s = \sum_{1 \le i, j \le M, ` | `\mathcal{L}_s = \sum_{1 \le i, j \le M, ` | YES | parser_latex | YES |
| paper_2 | formula_005 | 4 | Method | YES | YES | `\frac{QK^T}{\sqrt{d_k}}` | `\frac{QK^T}{\sqrt{d_k}}` | YES | parser_latex | YES |
| paper_2 | formula_006 | 5 | Method | YES | YES | `MultiHead(\mathbf{Q}, \mathbf{K}, \mathb` | `MultiHead(\mathbf{Q}, \mathbf{K}, \mathb` | YES | parser_latex | YES |
| paper_2 | formula_007 | 5 | Method | YES | YES | `head_i = Attention(\mathbf{Q}W_i^Q, \mat` | `head_i = Attention(\mathbf{Q}W_i^Q, \mat` | YES | parser_latex | YES |
| paper_2 | formula_008 | 5 | Method | YES | YES | `Attention(S, V) = Softmax(S)V` | `Attention(S, V) = Softmax(S)V` | YES | parser_latex | YES |
| paper_2 | formula_009 | 5 | Method | YES | YES | `\mathbf{A}^{(1)}, \mathbf{A}^{(2)}` | `\mathbf{A}^{(1)}, \mathbf{A}^{(2)}` | YES | parser_latex | YES |
| paper_2 | formula_010 | 5 | Method | YES | YES | `\mathbf{X}^{(1)} \in \mathcal{R}^{n \tim` | `\mathbf{X}^{(1)} \in \mathcal{R}^{n \tim` | YES | parser_latex | YES |
| paper_2 | formula_011 | 6 | Method | YES | YES | `\mathcal{L}_{mse} = \frac{1}{M} \sum_{t=` | `\mathcal{L}_{mse} = \frac{1}{M} \sum_{t=` | YES | parser_latex | YES |
| paper_2 | formula_012 | 6 | Method | YES | YES | `\hat{\mathbf{y}}^{(t)} = \sum_{i=1}^{M} ` | `\hat{\mathbf{y}}^{(t)} = \sum_{i=1}^{M} ` | YES | parser_latex | YES |
| paper_2 | formula_013 | 6 | Method | YES | YES | `\tilde{x} = \frac{x - \min X_{train}}{\m` | `\tilde{x} = \frac{x - \min X_{train}}{\m` | YES | parser_latex | YES |
| paper_2 | formula_014 | 6 | Method | YES | YES | `Precision = \frac{TP}{TP + FP}` | `Precision = \frac{TP}{TP + FP}` | YES | parser_latex | YES |
| paper_2 | formula_015 | 6 | Method | YES | YES | `Recall = \frac{TP}{TP + FN}` | `Recall = \frac{TP}{TP + FN}` | YES | parser_latex | YES |
| paper_2 | formula_016 | 6 | Method | YES | YES | `F1 = 2 \times \frac{\text{Precision} \ti` | `F1 = 2 \times \frac{\text{Precision} \ti` | YES | parser_latex | YES |
| paper_3 | formula_001 | 2 | Introduction | YES | YES | `I(X,Y) = \sum_{x \in X} \sum_{y \in Y} \` | `I(X,Y) = \sum_{x \in X} \sum_{y \in Y} \` | YES | parser_latex | YES |
| paper_3 | formula_002 | 2 | Introduction | YES | YES | `I_{\text{UBA}}(X,Y) \triangleq \mathbb{E` | `I_{\text{UBA}}(X,Y) \triangleq \mathbb{E` | YES | parser_latex | YES |
| paper_3 | formula_003 | 2 | Introduction | YES | YES | `q(x/y) = \frac{p(x)}{Z(y)}e^{f(x,y)}` | `q(x/y) = \frac{p(x)}{Z(y)}e^{f(x,y)}` | YES | parser_latex | YES |
| paper_3 | formula_004 | 3 | Method | YES | YES | `\mathbf{H}_{t:t+B} = \frac{\mathbf{s}_{t` | `\mathbf{H}_{t:t+B} = \frac{\mathbf{s}_{t` | YES | parser_latex | YES |
| paper_3 | formula_005 | 3 | Related Work | YES | YES | `\mathbf{H}_{\text{emb}} = \mathbf{W}_{\t` | `\mathbf{H}_{\text{emb}} = \mathbf{W}_{\t` | YES | parser_latex | YES |
| paper_3 | formula_006 | 3 | Related Work | YES | YES | `\mathbf{Q} = \mathbf{W}_{\mathbf{Q}} \cd` | `\mathbf{Q} = \mathbf{W}_{\mathbf{Q}} \cd` | YES | parser_latex | YES |
| paper_3 | formula_007 | 3 | Method | YES | YES | `\mathbf{Y}_1 = \mathbf{W}_{\text{mult}} ` | `\mathbf{Y}_1 = \mathbf{W}_{\text{mult}} ` | YES | parser_latex | YES |
| paper_3 | formula_008 | 3 | Method | YES | YES | `\mathbf{Y}_{2} = \mathbf{Y}_{1} + \frac{` | `\mathbf{Y}_{2} = \mathbf{Y}_{1} + \frac{` | YES | parser_latex | YES |
| paper_3 | formula_009 | 3 | Method | YES | YES | `\mathbf{Y}_3 = \mathbf{W}_2 \cdot \text{` | `\mathbf{Y}_3 = \mathbf{W}_2 \cdot \text{` | YES | parser_latex | YES |
| paper_3 | formula_010 | 4 | Method | YES | YES | `\begin{aligned} \mathbf{Y}_{\text{sta}}^` | `\begin{aligned} \mathbf{Y}_{\text{sta}}^` | YES | parser_latex | YES |
| paper_3 | formula_011 | 4 | Method | YES | YES | `\mathcal{L}_{aux} = \/\text{shuffle}(\ma` | `\mathcal{L}_{aux} = \/\text{shuffle}(\ma` | YES | parser_latex | YES |
| paper_3 | formula_012 | 5 | Method | YES | YES | `\begin{aligned} \mathbf{Y}_{\text{sta}}^` | `\begin{aligned} \mathbf{Y}_{\text{sta}}^` | YES | parser_latex | NO |
| paper_3 | formula_013 | 5 | Method | YES | YES | `\mathcal{L}_{\text{sta}} = \/\mathbf{Y} ` | `\mathcal{L}_{\text{sta}} = \/\mathbf{Y} ` | YES | parser_latex | YES |
| paper_3 | formula_014 | 5 | Method | YES | YES | `I_{\text{InfoNCE}} = \mathbb{E}_{\mathbb` | `I_{\text{InfoNCE}} = \mathbb{E}_{\mathbb` | YES | parser_latex | YES |
| paper_3 | formula_015 | 5 | Method | YES | YES | `f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\text` | `f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\text` | YES | parser_latex | YES |
| paper_3 | formula_016 | 5 | Method | YES | YES | `\mathcal{L}_{\text{reg}} = \/\mathbf{Y}'` | `\mathcal{L}_{\text{reg}} = \/\mathbf{Y}'` | YES | parser_latex | YES |
| paper_3 | formula_017 | 5 | Method | YES | YES | `\mathcal{L} = \lambda_1 \cdot \mathcal{L` | `\mathcal{L} = \lambda_1 \cdot \mathcal{L` | YES | parser_latex | YES |
| paper_3 | formula_018 | 6 | Method | YES | YES | `\mathcal{AS}(\mathbf{s}_i) = -I_{\theta}` | `\mathcal{AS}(\mathbf{s}_i) = -I_{\theta}` | YES | parser_latex | YES |
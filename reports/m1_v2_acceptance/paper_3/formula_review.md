# Formula Review: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy

## Formula Statistics

| type | count |
| ---- | ----: |
| source_latex | 0 |
| mineru_latex/parser_latex | 9 |
| ocr_latex | 0 |
| raw_formula_text | 0 |
| unknown | 0 |
| canonical FormulaBlock total | 9 |

## Formula Samples (from canonical paper)

| id | origin | is_latex | confidence | source_parser | content |
| -- | ------ | -------- | ---------: | ------------- | ------- |
| formula_001 | parser_latex | True | 0.80 | marker_document | \begin{split} \mathcal{Z}^{l} &= \text{Layer-Norm} \Big( \text{Anomaly-Attention}(\mathcal{X}^{l-1}) + \mathcal{X}^{l-1} \Big) \\ \mathcal{X}^{l} &= \text{Layer-Norm} \Big( \text{F |
| formula_002 | parser_latex | True | 0.80 | marker_document | \mathcal{Q}, \mathcal{K}, \mathcal{V}, \sigma = \mathcal{X}^{l-1}W_{\mathcal{Q}}^{l}, \mathcal{X}^{l-1}W_{\mathcal{K}}^{l}, \mathcal{X}^{l-1}W_{\mathcal{V}}^{l}, \mathcal{X}^{l-1}W |
| formula_003 | parser_latex | True | 0.80 | marker_document | AssDis(\mathcal{P}, \mathcal{S}; \mathcal{X}) = \left[\frac{1}{L} \sum_{l=1}^{L} \left( KL(\mathcal{P}_{i,:}^{l} || \mathcal{S}_{i,:}^{l}) + KL(\mathcal{S}_{i,:}^{l} || \mathcal{P} |
| formula_004 | parser_latex | True | 0.80 | marker_document | \mathcal{L}_{\text{Total}}(\widehat{\mathcal{X}}, \mathcal{P}, \mathcal{S}, \lambda; \mathcal{X}) = \|\mathcal{X} - \widehat{\mathcal{X}}\|_{F}^{2} - \lambda \times \|\text{AssDis} |
| formula_005 | parser_latex | True | 0.80 | marker_document | \mathcal{L}_{Total}(\widehat{\mathcal{X}}, \mathcal{P}, \mathcal{S}_{detach}, -\lambda; \mathcal{X}) |
| formula_006 | parser_latex | True | 0.80 | marker_document | \mathcal{X} |
| formula_007 | parser_latex | True | 0.80 | marker_document | \begin{aligned} &1: \ \mathcal{P}' = \texttt{Mean}(\mathcal{P}, \texttt{dim}=1) \\ &2: \ \mathcal{S}' = \texttt{Mean}(\mathcal{S}, \texttt{dim}=1) \\ &3: \ \mathcal{R}' = \texttt{K |
| formula_008 | parser_latex | True | 0.80 | marker_document | \mathcal{C}_{AD} = \text{Softmax}(-\text{AssDis}(\mathcal{P}, \mathcal{S}; \mathcal{X}), \text{dim=0}) |
| formula_009 | parser_latex | True | 0.80 | marker_document | \mathcal{X} |

## Core Formula Coverage

- Prior-Association: FOUND_TEXT
- Series-Association: FOUND_TEXT
- AssDis(P,S;X): FOUND_LATEX
- AnomalyScore: FOUND_TEXT

## Raw Formula Text Check

OK: no raw_formula_text blocks
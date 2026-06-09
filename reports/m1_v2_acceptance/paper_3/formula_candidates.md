# Formula Candidates: Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy

| id | page | section | origin | is_latex | content |
| -- | ---: | ------- | ------ | -------- | ------- |
| formula_001 | 3 | Method | parser_latex | True | \begin{split} \mathcal{Z}^{l} &= \text{Layer-Norm} \Big( \text{Anomaly-Attention}(\mathcal{X}^{l-1}) + \mathcal{X}^{l-1} \Big) \\ \mathcal{X}^{l} &= \text{Layer-Norm} \Big( \text{Feed-Forward}(\mathcal{Z}^{l}) + \mathcal |
| formula_002 | 3 | Method | parser_latex | True | \mathcal{Q}, \mathcal{K}, \mathcal{V}, \sigma = \mathcal{X}^{l-1}W_{\mathcal{Q}}^{l}, \mathcal{X}^{l-1}W_{\mathcal{K}}^{l}, \mathcal{X}^{l-1}W_{\mathcal{V}}^{l}, \mathcal{X}^{l-1}W_{\sigma}^{l} |
| formula_003 | 4 | Method | parser_latex | True | AssDis(\mathcal{P}, \mathcal{S}; \mathcal{X}) = \left[\frac{1}{L} \sum_{l=1}^{L} \left( KL(\mathcal{P}_{i,:}^{l} || \mathcal{S}_{i,:}^{l}) + KL(\mathcal{S}_{i,:}^{l} || \mathcal{P}_{i,:}^{l}) \right) \right]_{i=1,\dots,N |
| formula_004 | 4 | Method | parser_latex | True | \mathcal{L}_{\text{Total}}(\widehat{\mathcal{X}}, \mathcal{P}, \mathcal{S}, \lambda; \mathcal{X}) = \|\mathcal{X} - \widehat{\mathcal{X}}\|_{F}^{2} - \lambda \times \|\text{AssDis}(\mathcal{P}, \mathcal{S}; \mathcal{X})\ |
| formula_005 | 4 | Method | parser_latex | True | \mathcal{L}_{Total}(\widehat{\mathcal{X}}, \mathcal{P}, \mathcal{S}_{detach}, -\lambda; \mathcal{X}) |
| formula_006 | 5 | Method | parser_latex | True | \mathcal{X} |
| formula_007 | 14 | Conclusion | parser_latex | True | \begin{aligned} &1: \ \mathcal{P}' = \texttt{Mean}(\mathcal{P}, \texttt{dim}=1) \\ &2: \ \mathcal{S}' = \texttt{Mean}(\mathcal{S}, \texttt{dim}=1) \\ &3: \ \mathcal{R}' = \texttt{KL}\Big((\mathcal{P}', \mathcal{S}'), \te |
| formula_008 | 15 | Conclusion | parser_latex | True | \mathcal{C}_{AD} = \text{Softmax}(-\text{AssDis}(\mathcal{P}, \mathcal{S}; \mathcal{X}), \text{dim=0}) |
| formula_009 | 15 | Conclusion | parser_latex | True | \mathcal{X} |
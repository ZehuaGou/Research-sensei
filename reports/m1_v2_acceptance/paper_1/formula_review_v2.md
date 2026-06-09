# Formula Review: Monte Carlo EM for Deep Time Series Anomaly Detection

## Formula Statistics

| type | count |
| ---- | ----: |
| source_latex | 0 |
| mineru_latex/parser_latex | 41 |
| ocr_latex | 0 |
| raw_formula_text | 13 |
| unknown | 0 |
| canonical FormulaBlock total | 54 |

## Formula Samples (from canonical paper)

| id | origin | is_latex | confidence | source_parser | content |
| -- | ------ | -------- | ---------: | ------------- | ------- |
| fc_1 | parser_latex | True | 0.80 | marker_document | p(\mathbf{x}|z) = \begin{cases} p^+(\mathbf{x}) & \text{if } z = 0\\ p^-(\mathbf{x}) & \text{if } z = 1, \end{cases} |
| fc_2 | parser_latex | True | 0.80 | marker_document | p(\mathbf{x}_t|z_t=0) = p_{\theta}^+(\mathbf{x}_t) \tag{2} |
| fc_3 | parser_latex | True | 0.80 | marker_document | p(\mathbf{x}_t|z_t=1) = p^-(\mathbf{x}_t) \tag{3} |
| fc_4 | parser_latex | True | 0.80 | marker_document | \mathbf{x} |
| fc_5 | parser_latex | True | 0.80 | marker_document | p(\mathbf{x}) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x}) |
| fc_6 | parser_latex | True | 0.80 | marker_document | p^+(\mathbf{x}) |
| fc_7 | parser_latex | True | 0.80 | marker_document | p^+ |
| fc_8 | parser_latex | True | 0.80 | marker_document | p(z=0)=\alpha |
| fc_9 | parser_latex | True | 0.80 | marker_document | p(z=1)=1-\alpha |
| fc_10 | parser_latex | True | 0.80 | marker_document | p(\mathbf{x}) = \sum_z p(\mathbf{x}|z)p(z) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x}) |
| fc_11 | parser_latex | True | 0.80 | marker_document | p(z|\mathbf{x}) |
| fc_12 | parser_latex | True | 0.80 | marker_document | \mathbf{y}^+ \sim p^+(\cdot) |
| fc_13 | parser_latex | True | 0.80 | marker_document | z \sim \text{Bernoulli}(1-\alpha) |
| fc_14 | parser_latex | True | 0.80 | marker_document | \mathbf{x} = \mathbf{I}[z=0]\,\mathbf{y}^+ + \mathbf{I}[z=1]\,\mathbf{y}^- |
| fc_15 | parser_latex | True | 0.80 | marker_document | \mathbf{y}^+ |

## Core Formula Coverage

- p(x|z): FOUND_LATEX
- p(xt|zt=0): FOUND_LATEX
- p(zt+1|zt): FOUND_LATEX
- ELBO: MISSING: not present in parsed formula blocks or copied parser text

## Raw Formula Text Check

OK: fc_42 uses raw_formula_text and leaves latex empty
OK: fc_43 uses raw_formula_text and leaves latex empty
OK: fc_44 uses raw_formula_text and leaves latex empty
OK: fc_45 uses raw_formula_text and leaves latex empty
OK: fc_46 uses raw_formula_text and leaves latex empty
OK: fc_47 uses raw_formula_text and leaves latex empty
OK: fc_48 uses raw_formula_text and leaves latex empty
OK: fc_49 uses raw_formula_text and leaves latex empty
OK: fc_50 uses raw_formula_text and leaves latex empty
OK: fc_51 uses raw_formula_text and leaves latex empty
OK: fc_52 uses raw_formula_text and leaves latex empty
OK: fc_53 uses raw_formula_text and leaves latex empty
OK: fc_54 uses raw_formula_text and leaves latex empty
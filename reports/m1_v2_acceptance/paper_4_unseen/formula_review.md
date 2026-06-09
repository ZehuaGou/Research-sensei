# Formula Review: MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection

## Formula Statistics

| type | count |
| ---- | ----: |
| source_latex | 0 |
| mineru_latex/parser_latex | 11 |
| ocr_latex | 0 |
| raw_formula_text | 0 |
| unknown | 0 |
| canonical FormulaBlock total | 11 |

- m2_ready_for_formula_understanding: True
- formula_understanding_reasons: none
- raw_only_formula_dense: False

## Formula Samples (from canonical paper)

| id | origin | is_latex | confidence | source_parser | content |
| -- | ------ | -------- | ---------: | ------------- | ------- |
| b0041 | parser_latex | True | 0.90 | mineru25pro | v _ {i, t} ^ {s} = P (m _ {i} \rightarrow q _ {t} ^ {s}) = \frac {e x p (\langle m _ {i} , q _ {t} ^ {s} \rangle / \tau)}{\sum_ {p = 1} ^ {L} e x p (\langle m _ {i} , q _ {p} ^ {s} |
| b0043 | parser_latex | True | 0.90 | mineru25pro | \psi = \sigma \left(U _ {\psi} m _ {i} + W _ {\psi} \sum_ {t = 1} ^ {L} v _ {i, t} ^ {s} q _ {t} ^ {s}\right), \tag {2} \ |
| b0044 | parser_latex | True | 0.90 | mineru25pro | m _ {i} \leftarrow (1 - \psi) \circ m _ {i} + \psi \circ \sum_ {t = 1} ^ {L} v _ {i, t} ^ {s} q _ {t} ^ {s}, \tag {3} \ |
| b0047 | parser_latex | True | 0.90 | mineru25pro | w _ {t, i} ^ {s} = P (q _ {t} ^ {s} \rightarrow m _ {i}) = \frac {e x p (\langle m _ {i} , q _ {t} ^ {s} \rangle / \tau)}{\sum_ {j = 1} ^ {M} e x p (\langle m _ {j} , q _ {t} ^ {s} |
| b0049 | parser_latex | True | 0.90 | mineru25pro | \tilde {q} _ {t} ^ {s} = \sum_ {i ^ {\prime} = 1} ^ {M} w _ {t, i ^ {\prime}} ^ {s} m _ {i ^ {\prime}}. \tag {5} \ |
| b0054 | parser_latex | True | 0.90 | mineru25pro | L _ {r e c} = \frac {1}{N} \sum_ {s = 1} ^ {N} \left\| X ^ {s} - \hat {X} ^ {s} \right\| _ {2} ^ {2}. \tag {6} \ |
| b0056 | parser_latex | True | 0.90 | mineru25pro | L _ {e n t r} = \frac {1}{N} \sum_ {s = 1} ^ {N} \sum_ {t = 1} ^ {L} \sum_ {i = 1} ^ {M} - w _ {t, i} ^ {s} \log (w _ {t, i} ^ {s}). \tag {7} \ |
| b0058 | parser_latex | True | 0.90 | mineru25pro | L = L _ {r e c} + \lambda L _ {e n t r}, \tag {8} \ |
| b0069 | parser_latex | True | 0.90 | mineru25pro | L S D (q _ {t} ^ {s}, m) = \| q _ {t} ^ {s} - m _ {t} ^ {s, p o s} \| _ {2} ^ {2} \tag {9} \ |
| b0070 | parser_latex | True | 0.90 | mineru25pro | I S D (X _ {t,:} ^ {s}, \hat {X} _ {t,:} ^ {s}) = \left\| X _ {t,:} ^ {s} - \hat {X} _ {t,:} ^ {s} \right\| _ {2} ^ {2} \tag {10} \ |
| b0072 | parser_latex | True | 0.90 | mineru25pro | A (X ^ {s}) = \text { softmax } \left([ L S D (q _ {t} ^ {s}, m) |

## Core Formula Coverage

- Gated memory: FOUND_TEXT
- anomaly score: FOUND_TEXT
- bi-dimensional deviation: FOUND_TEXT
- K-means: FOUND_TEXT

## Raw Formula Text Check

OK: no raw_formula_text blocks
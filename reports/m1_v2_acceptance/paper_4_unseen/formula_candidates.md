# Formula Candidates: MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection

| id | page | section | origin | is_latex | content |
| -- | ---: | ------- | ------ | -------- | ------- |
| b0041 | 4 | Unknown | parser_latex | True | v _ {i, t} ^ {s} = P (m _ {i} \rightarrow q _ {t} ^ {s}) = \frac {e x p (\langle m _ {i} , q _ {t} ^ {s} \rangle / \tau)}{\sum_ {p = 1} ^ {L} e x p (\langle m _ {i} , q _ {p} ^ {s} \rangle / \tau)}, \tag {1} \ |
| b0043 | 4 | Unknown | parser_latex | True | \psi = \sigma \left(U _ {\psi} m _ {i} + W _ {\psi} \sum_ {t = 1} ^ {L} v _ {i, t} ^ {s} q _ {t} ^ {s}\right), \tag {2} \ |
| b0044 | 4 | Unknown | parser_latex | True | m _ {i} \leftarrow (1 - \psi) \circ m _ {i} + \psi \circ \sum_ {t = 1} ^ {L} v _ {i, t} ^ {s} q _ {t} ^ {s}, \tag {3} \ |
| b0047 | 4 | Unknown | parser_latex | True | w _ {t, i} ^ {s} = P (q _ {t} ^ {s} \rightarrow m _ {i}) = \frac {e x p (\langle m _ {i} , q _ {t} ^ {s} \rangle / \tau)}{\sum_ {j = 1} ^ {M} e x p (\langle m _ {j} , q _ {t} ^ {s} \rangle / \tau)}, \tag {4} \ |
| b0049 | 4 | Unknown | parser_latex | True | \tilde {q} _ {t} ^ {s} = \sum_ {i ^ {\prime} = 1} ^ {M} w _ {t, i ^ {\prime}} ^ {s} m _ {i ^ {\prime}}. \tag {5} \ |
| b0054 | 5 | Unknown | parser_latex | True | L _ {r e c} = \frac {1}{N} \sum_ {s = 1} ^ {N} \left\| X ^ {s} - \hat {X} ^ {s} \right\| _ {2} ^ {2}. \tag {6} \ |
| b0056 | 5 | Unknown | parser_latex | True | L _ {e n t r} = \frac {1}{N} \sum_ {s = 1} ^ {N} \sum_ {t = 1} ^ {L} \sum_ {i = 1} ^ {M} - w _ {t, i} ^ {s} \log (w _ {t, i} ^ {s}). \tag {7} \ |
| b0058 | 5 | Unknown | parser_latex | True | L = L _ {r e c} + \lambda L _ {e n t r}, \tag {8} \ |
| b0069 | 6 | Unknown | parser_latex | True | L S D (q _ {t} ^ {s}, m) = \| q _ {t} ^ {s} - m _ {t} ^ {s, p o s} \| _ {2} ^ {2} \tag {9} \ |
| b0070 | 6 | Unknown | parser_latex | True | I S D (X _ {t,:} ^ {s}, \hat {X} _ {t,:} ^ {s}) = \left\| X _ {t,:} ^ {s} - \hat {X} _ {t,:} ^ {s} \right\| _ {2} ^ {2} \tag {10} \ |
| b0072 | 6 | Unknown | parser_latex | True | A (X ^ {s}) = \text { softmax } \left([ L S D (q _ {t} ^ {s}, m) |
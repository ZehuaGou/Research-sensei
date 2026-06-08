# Formula Review: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection

## Formula Statistics

| type | count |
| ---- | ----: |
| source_latex | 0 |
| parser_latex | 0 |
| ocr_latex | 0 |
| raw_formula_text | 18 |
| unknown | 0 |
| canonical FormulaBlock total | 18 |

## Formula Samples (from canonical paper)

| id | origin | is_latex | confidence | source_parser | content |
| -- | ------ | -------- | ---------: | ------------- | ------- |
| fc_1 | raw_formula_text | False | 0.30 | markitdown | her, we make no assumptions about whether anomalies =E p(x,y) [f(x,y)]−E p(y) [logZ(y)] |
| fc_2 | raw_formula_text | False | 0.30 | markitdown | I(X,Y)= P(x,y)log (1) |
| fc_3 | raw_formula_text | False | 0.30 | markitdown | have also S=softmax √ |
| fc_4 | raw_formula_text | False | 0.30 | markitdown | uses RNNs to detect anomalies AS(s i )=−I θ (Y,Y aux ) (18) by forecasting over long sequences of data; (7) MAD-GAN [34] |
| fc_5 | raw_formula_text | False | 0.30 | markitdown | prior associations |
| fc_6 | raw_formula_text | False | 0.30 | markitdown | AnomalyScore |
| fc_7 | raw_formula_text | False | 0.30 | pymupdf | X, Z(y) = Ep(x) |
| fc_8 | raw_formula_text | False | 0.30 | pymupdf | Hemb K = WK · Hemb |
| fc_9 | raw_formula_text | False | 0.30 | pymupdf | Hemb S = softmax |
| fc_10 | raw_formula_text | False | 0.30 | pymupdf | More specifically, Y = [Ysta, Yaux], where Ysta ∈RB× d |
| fc_11 | raw_formula_text | False | 0.30 | pymupdf | YI sta = identity(Ysta) |
| fc_12 | raw_formula_text | False | 0.30 | pymupdf | YS aux = shuffle(Yaux) |
| fc_13 | raw_formula_text | False | 0.30 | pymupdf | YS sta = shuffle(Ysta) |
| fc_14 | raw_formula_text | False | 0.30 | pymupdf | YI aux = identity(Yaux) |
| fc_15 | raw_formula_text | False | 0.30 | pymupdf | IInfoNCE = EP(Y,Ysta)[fθ(Y, Ysta)]−EP(Ysta)[EP(Y)[efθ(Y,Ysta)]] |

## Core Formula Coverage

- Prior-Association: FOUND_RAW_TEXT
- Series-Association: FOUND_RAW_TEXT
- AssDis(P,S;X): MISSING: not present in MarkItDown, PyMuPDF, Marker, or canonical text
- AnomalyScore(X): FOUND_RAW_TEXT
- mutual information: FOUND_TEXT

## Raw Formula Text Check

OK: fc_1 uses raw_formula_text and leaves latex empty
OK: fc_2 uses raw_formula_text and leaves latex empty
OK: fc_3 uses raw_formula_text and leaves latex empty
OK: fc_4 uses raw_formula_text and leaves latex empty
OK: fc_5 uses raw_formula_text and leaves latex empty
OK: fc_6 uses raw_formula_text and leaves latex empty
OK: fc_7 uses raw_formula_text and leaves latex empty
OK: fc_8 uses raw_formula_text and leaves latex empty
OK: fc_9 uses raw_formula_text and leaves latex empty
OK: fc_10 uses raw_formula_text and leaves latex empty
OK: fc_11 uses raw_formula_text and leaves latex empty
OK: fc_12 uses raw_formula_text and leaves latex empty
OK: fc_13 uses raw_formula_text and leaves latex empty
OK: fc_14 uses raw_formula_text and leaves latex empty
OK: fc_15 uses raw_formula_text and leaves latex empty
OK: fc_16 uses raw_formula_text and leaves latex empty
OK: fc_17 uses raw_formula_text and leaves latex empty
OK: fc_18 uses raw_formula_text and leaves latex empty
# Parser Comparison: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection

## Basic Info
- title: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection
- paper_id: 2510.18998
- source_pdf_path: reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/2510.18998/source.pdf
- selected_parser: pymupdf
- parser_selection_reason: Good quality
- parser_quality_score: 87.6
- canonical_quality_status: DEGRADED
- degradation_reason: Body text has elevated garbled-line ratio
- canonical_paper_path: reports/m1_parser_review/paper_3/canonical_paper.md

## Parser Quality Table

| parser | overall_score | output_length | section_count | long_concat_count | spacing_quality | cid_token_count | formula_candidate_count | garbled_line_ratio | selected | reason |
| ------ | ------------: | ------------: | ------------: | ----------------: | --------------: | --------------: | ----------------------: | -----------------: | -------- | ------ |
| markitdown_pdf | 45.4 | 142665 | 0 | 193 | 1.000 | 10 | 3 | 0.030 | NO | Severe concatenation (193 long words) |
| pymupdf | 87.6 | 86460 | 0 | 0 | 1.000 | 0 | 10 | 0.371 | YES | Good quality |
| marker_pdf | 0.0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0.000 | NO | skipped_by_policy |

## Text Excerpt Comparison

### MarkItDown Excerpt
```text
An Encode-then-Decompose Approach to
Unsupervised Time Series Anomaly Detection on
Contaminated Training Data–Extended Version
Buang Zhang1, Tung Kieu2, Xiangfei Qiu1, Chenjuan Guo1, Jilin Hu1
Aoying Zhou1, Christian S. Jensen2, Bin Yang1
1School of Data Science & Engineering, East China Normal University, Shanghai, China
2Department of Computer Science, Aalborg University, Aalborg, Denmark
1{buazhang, xfqiu}@stu.ecnu.edu.cn, 1{cjguo, jlhu, ayzhou, byang}@dase.ecnu.edu.cn, 2{tungkvt,csj}@cs.aau.dk
Abstract—Timeseriesanomalydetectionisimportantinmod- Stable features Auxiliary features
ern large-scale systems and is applied in a variety of domains Reconstructed
time series
to analyze and monitor the operation of diverse systems. Unsu-
Decomposer
pervised approaches have received widespread interest, as they
Stable Auxiliary
do not require anomaly labels during training, thus avoiding Decod
```

### PyMuPDF Excerpt
```text
An Encode-then-Decompose Approach to
Unsupervised Time Series Anomaly Detection on
Contaminated Training Data–Extended Version
Buang Zhang1, Tung Kieu2, Xiangfei Qiu1, Chenjuan Guo1, Jilin Hu1
Aoying Zhou1, Christian S. Jensen2, Bin Yang1
1School of Data Science & Engineering, East China Normal University, Shanghai, China
2Department of Computer Science, Aalborg University, Aalborg, Denmark
1{buazhang, xfqiu}@stu.ecnu.edu.cn, 1{cjguo, jlhu, ayzhou, byang}@dase.ecnu.edu.cn, 2{tungkvt,csj}@cs.aau.dk
Abstract—Time series anomaly detection is important in mod-
ern large-scale systems and is applied in a variety of domains
to analyze and monitor the operation of diverse systems. Unsu-
pervised approaches have received widespread interest, as they
do not require anomaly labels during training, thus avoiding
potentially high costs and having wider applications. Among
these, autoencoders have re
```

### Marker Excerpt
```text
marker skipped by policy
```

### Selected Canonical Excerpt
```text
---
paper_id: 2510.18998
title: "An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection"
source_type: PDF
source_confidence: medium
canonicalization_status: degraded
canonical_quality_status: DEGRADED
parser_used: pymupdf
m2_ready: true
degradation_reason: "Body text has elevated garbled-line ratio"
parser_candidates: ['pymupdf', 'markitdown_pdf']
selected_parser: pymupdf
parser_quality_score: 87.6
parser_selection_reason: "Good quality"
parser_quality_details:
  pymupdf:
    overall_score: 87.6
    output_length: 86460
    section_count: 0
    long_concat_count: 0
    spacing_quality: 1.0
    cid_token_count: 0
    formula_candidate_count: 10
    garbled_line_ratio: 0.371
    reason: Good quality
  markitdown_pdf:
    overall_score: 45.4
    output_length: 142665
    section_count: 0
    long_concat_count: 193
    spacing_quality: 1.0
    cid_token_count: 10
   
```
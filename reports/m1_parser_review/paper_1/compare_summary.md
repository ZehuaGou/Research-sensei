# Parser Comparison: Monte Carlo EM for Deep Time Series Anomaly Detection

## Basic Info
- title: Monte Carlo EM for Deep Time Series Anomaly Detection
- paper_id: 2112.14436
- source_pdf_path: reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/2112.14436/source.pdf
- selected_parser: marker_pdf
- parser_selection_reason: Good quality
- parser_quality_score: 100.0
- canonical_quality_status: PASS
- degradation_reason: none
- canonical_paper_path: reports/m1_parser_review/paper_1/canonical_paper.md

## Parser Quality Table

| parser | overall_score | output_length | section_count | long_concat_count | spacing_quality | cid_token_count | formula_candidate_count | garbled_line_ratio | selected | reason |
| ------ | ------------: | ------------: | ------------: | ----------------: | --------------: | --------------: | ----------------------: | -----------------: | -------- | ------ |
| markitdown_pdf | 39.4 | 46347 | 0 | 210 | 0.931 | 3 | 0 | 0.008 | NO | Severe concatenation (210 long words) |
| pymupdf | 78.9 | 22392 | 0 | 0 | 1.000 | 0 | 0 | 0.056 | NO | Good quality |
| marker_pdf | 100.0 | 24571 | 12 | 0 | 1.000 | 0 | 91 | 0.026 | YES | Good quality |

## Text Excerpt Comparison

### MarkItDown Excerpt
```text
|     | Monte |     | Carlo                  | EM for | Deep | Time Series    | Anomaly      |     | Detection |     |     |     |
| --- | ----- | --- | ---------------------- | ------ | ---- | -------------- | ------------ | --- | --------- | --- | --- | --- |
|     |       |     | Franc¸ois-XavierAubet1 |        |      | DanielZu¨gner2 | JanGasthaus1 |     |           |     |     |     |
Abstract
(explicitlyorimplicitly)assumeaccesstonominaldatacan
oftenalsosuccessfullybeappliedtomixeddatabyassum-
Timeseriesdataareoftencorruptedbyoutliersor
ingitisnominal,aslongastheproportionofanomaliesis
| otherkindsofanomalies. |     |     | Identifyingtheanoma- |     |     |     |     |     |     |     |     |     |
| ---------------------- | --- | --- | -------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
1202 ceD 92  ]GL.sc[  1v63441.2112:viXra
lous points can be a goal on
```

### PyMuPDF Excerpt
```text
Monte Carlo EM for Deep Time Series Anomaly Detection
Franc¸ois-Xavier Aubet 1 Daniel Z¨ugner 2 Jan Gasthaus 1
Abstract
Time series data are often corrupted by outliers or
other kinds of anomalies. Identifying the anoma-
lous points can be a goal on its own (anomaly
detection), or a means to improving performance
of other time series tasks (e.g. forecasting). Re-
cent deep-learning-based approaches to anomaly
detection and forecasting commonly assume that
the proportion of anomalies in the training data
is small enough to ignore, and treat the unlabeled
data as coming from the nominal data distribu-
tion. We present a simple yet effective technique
for augmenting existing time series models so
that they explicitly account for anomalies in the
training data. By augmenting the training data
with a latent anomaly indicator variable whose
distribution is inferred while training the under-
ly
```

### Marker Excerpt
```text
# Monte Carlo EM for Deep Time Series Anomaly Detection

#### Franc¸ois-Xavier Aubet <sup>1</sup> Daniel Zugner ¨ <sup>2</sup> Jan Gasthaus <sup>1</sup>

# Abstract

Time series data are often corrupted by outliers or other kinds of anomalies. Identifying the anomalous points can be a goal on its own (anomaly detection), or a means to improving performance of other time series tasks (e.g. forecasting). Recent deep-learning-based approaches to anomaly detection and forecasting commonly assume that the proportion of anomalies in the training data is small enough to ignore, and treat the unlabeled data as coming from the nominal data distribution. We present a simple yet effective technique for augmenting existing time series models so that they explicitly account for anomalies in the training data. By augmenting the training data with a latent anomaly indicator variable whose distribution 
```

### Selected Canonical Excerpt
```text
---
paper_id: 2112.14436
title: "Monte Carlo EM for Deep Time Series Anomaly Detection"
source_type: PDF
source_confidence: medium
canonicalization_status: success
canonical_quality_status: PASS
parser_used: marker_pdf
m2_ready: true
parser_candidates: ['marker_pdf', 'pymupdf', 'markitdown_pdf']
selected_parser: marker_pdf
parser_quality_score: 100.0
parser_selection_reason: "Good quality"
parser_quality_details:
  marker_pdf:
    overall_score: 100.0
    output_length: 24571
    section_count: 12
    long_concat_count: 0
    spacing_quality: 1.0
    cid_token_count: 0
    formula_candidate_count: 91
    garbled_line_ratio: 0.026
    reason: Good quality
  pymupdf:
    overall_score: 78.9
    output_length: 22392
    section_count: 0
    long_concat_count: 0
    spacing_quality: 1.0
    cid_token_count: 0
    formula_candidate_count: 0
    garbled_line_ratio: 0.056
    reason: Good quali
```
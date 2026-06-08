# Parser Comparison: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT

## Basic Info
- title: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT
- paper_id: W3184127157
- source_pdf_path: reports/live_eval/work/m1/workspace/runs/m1-live/source_pdfs/W3184127157/source.pdf
- selected_parser: pymupdf
- parser_selection_reason: Good quality
- parser_quality_score: 100.0
- canonical_quality_status: DEGRADED
- degradation_reason: Method repaired by moving trailing reference entries to References
- canonical_paper_path: reports/m1_parser_review/paper_2/canonical_paper.md

## Parser Quality Table

| parser | overall_score | output_length | section_count | long_concat_count | spacing_quality | cid_token_count | formula_candidate_count | garbled_line_ratio | selected | reason |
| ------ | ------------: | ------------: | ------------: | ----------------: | --------------: | --------------: | ----------------------: | -----------------: | -------- | ------ |
| markitdown_pdf | 52.3 | 82147 | 1 | 152 | 1.000 | 10 | 18 | 0.035 | NO | Severe concatenation (152 long words) |
| pymupdf | 100.0 | 62834 | 4 | 0 | 1.000 | 0 | 19 | 0.132 | YES | Good quality |
| marker_pdf | 0.0 | 0 | 0 | 0 | 1.000 | 0 | 0 | 0.000 | NO | skipped_by_policy |

## Text Excerpt Comparison

### MarkItDown Excerpt
```text
1
Learning Graph Structures with Transformer for
Multivariate Time Series Anomaly Detection in IoT
Zekai Chen, Student Member, IEEE, Dingshuo Chen, Xiao Zhang, Member, IEEE, Zixuan Yuan,
and Xiuzhen Cheng, Fellow, IEEE
Abstract—Many real-world IoT systems, which include a Inthiswork,wefocusonanomalydetectionformultivariate
varietyofinternet-connectedsensorydevices,producesubstantial time series [8] as a copious amount of IoT sensors in many
amounts of multivariate time series data. Meanwhile, vital IoT
real-life scenarios consecutively generate substantial volumes
infrastructureslikesmartpowergridsandwaterdistributionnet-
oftimeseriesdata.Forinstance,inaSecureWaterDistribution
worksarefrequentlytargetedbycyber-attacks,makinganomaly
detectionanimportantstudytopic.Modelingsuchrelatednessis, (WADI) system [9], multiple sensing measurements such as
nevertheless, unavoidable for any efficient
```

### PyMuPDF Excerpt
```text
1
Learning Graph Structures with Transformer for
Multivariate Time Series Anomaly Detection in IoT
Zekai Chen, Student Member, IEEE, Dingshuo Chen, Xiao Zhang, Member, IEEE, Zixuan Yuan,
and Xiuzhen Cheng, Fellow, IEEE
Abstract—Many real-world IoT systems, which include a
variety of internet-connected sensory devices, produce substantial
amounts of multivariate time series data. Meanwhile, vital IoT
infrastructures like smart power grids and water distribution net-
works are frequently targeted by cyber-attacks, making anomaly
detection an important study topic. Modeling such relatedness is,
nevertheless, unavoidable for any efﬁcient and effective anomaly
detection system, given the intricate topological and nonlinear
connections that are originally unknown among sensors. Further-
more, detecting anomalies in multivariate time series is difﬁcult
due to their temporal dependency and stoch
```

### Marker Excerpt
```text
marker skipped by policy
```

### Selected Canonical Excerpt
```text
---
paper_id: W3184127157
title: "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT"
source_type: PDF
source_confidence: medium
canonicalization_status: degraded
canonical_quality_status: DEGRADED
parser_used: pymupdf
m2_ready: true
degradation_reason: "Method repaired by moving trailing reference entries to References"
parser_candidates: ['pymupdf', 'markitdown_pdf']
selected_parser: pymupdf
parser_quality_score: 100.0
parser_selection_reason: "Good quality"
parser_quality_details:
  pymupdf:
    overall_score: 100.0
    output_length: 62834
    section_count: 4
    long_concat_count: 0
    spacing_quality: 1.0
    cid_token_count: 0
    formula_candidate_count: 19
    garbled_line_ratio: 0.132
    reason: Good quality
  markitdown_pdf:
    overall_score: 52.3
    output_length: 82147
    section_count: 1
    long_concat_count: 152
    spac
```
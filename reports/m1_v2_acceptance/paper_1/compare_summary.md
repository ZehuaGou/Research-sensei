# Parser Comparison: Monte Carlo EM for Deep Time Series Anomaly Detection

## Basic Info
- title: Monte Carlo EM for Deep Time Series Anomaly Detection
- paper_id: paper_1
- source_pdf_path: source.pdf
- selected_parser: marker_document
- parser_selection_reason: Marker fallback selected because it produced real parser_latex FormulaBlocks for this review case.
- parser_quality_score: 100.000
- canonical_quality_status: DEGRADED
- degradation_reason: none
- canonical_paper_path: canonical_paper.md

## Parser Quality Table

| parser | overall_score | output_length | section_count | long_concat_count | spacing_quality | cid_token_count | formula_candidate_count | garbled_line_ratio | selected | reason |
| ------ | ------------: | ------------: | ------------: | ----------------: | --------------: | --------------: | ----------------------: | -----------------: | -------- | ------ |
| marker_pdf | 100.000 | 24571 | 12 | 0 | 1.000 | 0 | 91 | 0.026 | YES | Good quality |
| pymupdf | 78.900 | 22392 | 0 | 0 | 1.000 | 0 | 0 | 0.056 | NO | Good quality |
| markitdown_pdf | 39.400 | 46347 | 0 | 210 | 0.931 | 3 | 0 | 0.008 | NO | Severe concatenation (210 long words) |
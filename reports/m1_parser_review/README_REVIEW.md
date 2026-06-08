# M1 Parser Review Bundle

This bundle is generated for M1 canonical parser review only. It excludes reports from git.

Marker policy: ordinary live eval keeps marker_enabled=false with trigger_mode=never. The review bundle may use cached Marker output for paper_1; paper_2 and paper_3 include skipped_by_policy files.

| paper | selected_parser | parser_score | canonical_quality_status | m2_ready | reason |
| ----- | --------------- | -----------: | ------------------------ | -------- | ------ |
| paper_1 | marker_pdf | 100.0 | PASS | True | Good quality |
| paper_2 | pymupdf | 100.0 | DEGRADED | True | Method repaired by moving trailing reference entries to References |
| paper_3 | pymupdf | 87.6 | DEGRADED | True | Body text has elevated garbled-line ratio |

Generated in 15.8s.
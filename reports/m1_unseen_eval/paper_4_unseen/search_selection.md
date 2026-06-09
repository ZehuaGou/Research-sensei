# Paper Selection for paper_4_unseen

## Search Query

`time series anomaly detection transformer`

Sources: OpenAlex API (relevance_score desc, from_publication_date:2023-06-01, is_oa:true)

## Top 10 Candidates

| # | Title | Year | Citations | Source | PDF Available | Selected |
|---|-------|------|-----------|--------|:---:|:---:|
| 1 | Are Transformers Effective for Time Series Forecasting? | 2023 | 2565 | AAAI | YES | NO — forecasting, not anomaly detection |
| 2 | Transformers in Time Series: A Survey | 2023 | 987 | IJCAI | YES | NO — survey paper |
| 3 | Deep Learning for Time Series Anomaly Detection: A Survey | 2024 | 391 | ACM Computing Surveys | YES | NO — survey paper |
| 4 | **MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection** | 2023 | 28 | arXiv | YES | **YES** |
| 5 | Anomaly Detection in Time Series Data Using Reversible Instance Normalized Anomaly Transformer | 2023 | 19 | Sensors | YES | NO — only 8 pages, fewer equations expected |
| 6 | AnomalyBERT: Self-Supervised Transformer for Time Series Anomaly Detection | 2023 | 16 | arXiv | YES | BACKUP — tried if MEMTO fails |
| 7 | Multivariate Time Series Anomaly Detection Based on Spatial-Temporal Network and Transformer | 2024 | 9 | CMC | YES | NO — lower citations |
| 8 | TiTAD: Time-Invariant Transformer for Multivariate Time Series Anomaly Detection | 2025 | 6 | Electronics | YES | NO — very recent, fewer citations |
| 9 | TCF-Trans: Temporal Context Fusion Transformer for Anomaly Detection in Time Series | 2023 | 5 | Sensors | YES | NO — fewer equations expected |
| 10 | DDMT: Denoising Diffusion Mask Transformer Models for Multivariate Time Series Anomaly Detection | 2023 | — | arXiv | YES | BACKUP |

## Selection: MEMTO (arXiv 2312.02530)

**Why MEMTO:**
- Directly addresses multivariate time series anomaly detection with transformers
- 17 pages — substantial paper with room for many display equations
- 70 potential equation lines detected across pages 3-6, 8-9, 14-15
- 28 citations — established enough to be non-trivial
- Public arXiv PDF available
- Not one of the existing 3 papers (Anomaly Transformer, Learning Graph Structures, Encode-then-Decompose)
- Seoul National University — credible institution

**Risk factors:**
- May have complex multi-column layout that challenges parser
- Memory-guided architecture may have novel equation formats
- 17 pages is longer than paper_1 (20) and paper_2 (8) — tests parser robustness

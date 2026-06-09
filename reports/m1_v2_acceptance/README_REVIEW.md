# M1 v2 Acceptance Report

Default route decision: MinerU2.5-Pro + RuleBasedStructureRefiner is the primary M1 route when MinerU cached/live output is available. Marker remains fallback/audit baseline. Ollama remains optional and disabled by default because the cached paper_4_unseen evaluation recorded JSON valid=0 / invalid=17, so it did not improve section/context quality reliably.

Current local Ollama smoke (qwen2.5:0.5b, 12 paper_4 blocks, timeout 20s): available=True, JSON valid=0, invalid=1, timeout=1, changed_by_count=0. This confirms Ollama remains optional/off by default.

Marker default policy: marker_enabled=false, trigger_mode=never for ordinary live eval; review/heavy modes may opt in with timeout and skipped_by_policy/timeout_degraded reporting.

Formula dense pages are computed by scanning each PDF page with PyMuPDF text extraction and math-token density, not from selected_text guesses.

## Papers

| paper | parser | status | m2_ready | formulas | latex | raw_text | high_risk | coverage |
| ----- | ------ | ------ | -------- | -------: | ----: | -------: | --------: | -------- |
| paper_1 | marker_document | DEGRADED | True | 54 | 41 | 13 | 0 | p(x|z)=FOUND_LATEX; p(xt|zt=0)=FOUND_LATEX; p(zt+1|zt)=FOUND_LATEX; ELBO=MISSING: not present in parsed formula blocks or copied parser text |
| paper_2 | pymupdf | DEGRADED | True | 26 | 0 | 26 | 0 | Gumbel-softmax=FOUND_RAW_TEXT; Attention(Q,K,V)=FOUND_RAW_TEXT; MultiHead(Q,K,V)=FOUND_RAW_TEXT; Influence Propagation=FOUND_TEXT |
| paper_3 | pymupdf | PASS | True | 9 | 9 | 0 | 0 | Prior-Association=FOUND_TEXT; Series-Association=FOUND_TEXT; AssDis(P,S;X)=FOUND_LATEX; AnomalyScore=FOUND_TEXT |
| paper_4_unseen | mineru25pro | PASS | True | 11 | 11 | 0 | 0 | Gated memory=FOUND_TEXT; anomaly score=FOUND_TEXT; bi-dimensional deviation=FOUND_TEXT; K-means=FOUND_TEXT |
| paper_5_unseen | pymupdf | DEGRADED | True | 129 | 0 | 129 | 0 | TranAD=FOUND_RAW_TEXT; transformer=FOUND_RAW_TEXT; anomaly score=MISSING: not present in parsed formula blocks or copied parser text; self-conditioning=FOUND_RAW_TEXT |

## Route Comparison

- A MinerU2.5-Pro + RuleBasedStructureRefiner: selected as default when available; paper_4_unseen had 11 formulas distributed Method=8 / Experiments=3 / Abstract=0 in the cached spike.
- B MinerU2.5-Pro + RuleBasedStructureRefiner + Ollama structured refiner: not selected by default; Ollama native /api/chat JSON schema path is implemented, but cached live eval was JSON valid=0 / invalid=17.
- C Marker fallback/audit baseline: retained for parser_latex fallback and visual audit comparison; not primary after all-formulas-in-Abstract blind failure.
- D PyMuPDF/MarkItDown fallback/debug: allowed for review/debug artifacts, raw_formula_text must stay raw_formula_text and is never written as LaTeX.

## New Unseen Selection

- paper_5_unseen uses TranAD from the existing M1 live_eval auto search/download directory. It is a 15-page transformer anomaly-detection method paper and is not one of paper_1/2/3 or paper_4 MEMTO.
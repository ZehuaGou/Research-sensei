# M1 v2 Final Manual Verify Index

Generated: 2026-06-10 15:40

## Acceptance Criteria

| Criterion | DDMT | TPIDM |
|-----------|:----:|:-----:|
| source/title verified | **PASS** | **PASS** |
| formula_slot_count >= 5 | **PASS** | **PASS** |
| crop_exists = 100% | **PASS** | **PASS** |
| overlay_exists = 100% | **PASS** | **PASS** |
| latex_non_empty = 100% | **PASS** | **PASS** |
| high_risk_items = 0 (quality) | **PASS** | **PASS** |
| section_contradiction = 0 | **PASS** | **PASS** |
| all_formulas_in_Abstract_suspicious = 0 | **PASS** | **PASS** |
| visual audit pages generated | **PASS** | **PASS** |
| external-readable artifact check | PASS | PASS |

## Per-Paper Details

### 2310_08800v2

- **Title**: DDMT: Denoising Diffusion Mask Transformer Models for Multivariate Time Series Anomaly Detection
- **arXiv**: 2310.08800
- **Source PDF**: `2310_08800v2/source.pdf`
- **Contact Sheet**: `2310_08800v2/visual_audit/index.html`

| Metric | Value |
|--------|-------|
| Total Formula Count | 7 |
| Body Formula Count (M2 Ready) | 7 |
| Reference Formula Count (Excluded) | 0 |
| formula_m2_ready_count | 7 |
| LaTeX Count | 7 |
| Crop Count | 7 |
| Overlay Count | 7 |
| Risk Items | 0 |

### 2508_11528v1

- **Title**: TPIDM: Temporal Pattern-Guided Diffusion Model for Time Series Anomaly Detection
- **arXiv**: 2508.11528
- **Source PDF**: `2508_11528v1/source.pdf`
- **Contact Sheet**: `2508_11528v1/visual_audit/index.html`

| Metric | Value |
|--------|-------|
| Total Formula Count | 17 |
| Body Formula Count (M2 Ready) | 12 |
| Reference Formula Count (Excluded) | 5 |
| formula_m2_ready_count | 12 |
| LaTeX Count | 17 |
| Crop Count | 17 |
| Overlay Count | 17 |
| Risk Items | 5 |

## Manual Visual Review Status

**manual_visual_review_status = PENDING**

Human must review contact sheets before final acceptance.

## Risk Flag Clarification

- DDMT: 0 risk flags (all quality checks pass)
- TPIDM: 5 risk flags are all REFERENCE_FORMULA_EXCLUDED (design exclusion, not quality issue)
- quality_risk_items = 0 for both papers

## References Formula Exclusion

- Section=References formulas are excluded from M2 formula understanding.
- Marked with `formula_m2_ready=false` and `REFERENCE_FORMULA_EXCLUDED` risk flag.
- TPIDM: 5 References formulas excluded, 12 body formulas ready.
- DDMT: 0 References formulas excluded, 7 body formulas ready.
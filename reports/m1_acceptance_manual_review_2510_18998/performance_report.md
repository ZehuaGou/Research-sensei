# M1 Performance Report

Generated: 2026-06-11 18:56

## Status Summary

| Gate | Status |
|------|--------|
| Machine quality gate | **PASS** |
| GPU path | **PASS** |
| Performance gate | **WARNING** |
| Manual visual verification | **PENDING** |

**Note**: M1 is NOT fully verified until all gates pass AND manual visual verification is complete.

## Paper

- Title: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version
- arXiv: 2510.18998
- Pages: 15

## Device

- Requested: auto
- Actual: **cuda**
- GPU used: True
- GPU name: NVIDIA GeForce RTX 4060 Laptop GPU

## Timing

- Full parse: 2683.486s
- Seconds/page: 178.9

## Output

- Blocks: 361
- Formula slots: 26
- Quality: PASS
- M2 ready: True

## Warnings

- **seconds_per_page=179 > 120s threshold**
- **seconds_per_page=179 > 120s threshold**

## Conclusion

Machine quality gate passed, but performance gate has warnings. M1 can be used for manual review but not recommended for batch processing.
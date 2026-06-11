# M1 Performance Diagnosis

Generated: 2026-06-11 16:02

## Current Performance

- Backend: transformers
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU (8188 MB)
- device_mode_actual: cuda
- Parse elapsed: 2683s (44.7 min)
- Pages: 15
- Seconds/page: 178.9
- Performance gate: **WARNING (>120s/page)**

## Analysis

MinerU2.5-Pro is running on GPU (NVIDIA GeForce RTX 4060 Laptop GPU) via the `transformers` backend. Each page takes ~179 seconds, which exceeds the 120s/page warning threshold. This means the full M1 pipeline takes ~45 minutes for a 15-page paper.

The GPU is being used (confirmed by device_mode_actual=cuda and GPU memory allocation), but the per-page cost is high due to the two-step inference process (layout detection + OCR/formula extraction per region).

## Suitability

- **Manual review / single paper**: Acceptable. 45 minutes is tolerable for one-off acceptance.
- **Batch processing**: Not recommended at current speed. 15 pages × 179s = 2685s per paper. 100 papers would take ~75 hours.

## Optimization Directions

1. **vLLM backend**: Evaluate if `mineru-vl-utils` supports vLLM for faster inference.
2. **Reduce render_scale**: Current default is 2.0. Lowering to 1.5 or 1.0 reduces image size and inference time.
3. **Page-level cache**: Cache layout detection results to avoid re-processing unchanged pages.
4. **Selective parsing**: Only run full MinerU on pages with formula candidates (from prescreen).
5. **Batch/async page pipeline**: Process multiple pages in parallel if GPU memory allows.
6. **Per-page profiling**: Record each page's layout + OCR time to identify slow pages.
7. **Model quantization**: If supported, use INT8/FP16 quantized model for faster inference.
# M1 Device Diagnosis Report

Generated: 2026-06-11T13:37:03.671901

## System

- Python: 3.13.9 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 19:09:58) [MSC v.1929 64 bit (AMD64)]
- OS: Windows 11 (AMD64)

## GPU / CUDA

- torch installed: True
- torch version: 2.12.0+cu126
- CUDA available: **True**
- CUDA version: 12.6
- GPU name: NVIDIA GeForce RTX 4060 Laptop GPU
- GPU memory total: 8188 MB
- GPU memory allocated: 0 MB

## nvidia-smi

- Available: True
- NVIDIA GeForce RTX 4060 Laptop GPU: 8188MB total, 6878MB free, 60C, 0% util

## Dependencies

- transformers: v4.57.6
- accelerate: v1.13.0
- mineru-vl-utils: v1.0.4

## CUDA Issues

- None

## 3-Layer GPU Status

| Layer | Description | Status |
|-------|-------------|--------|
| 1 | Hardware GPU (nvidia-smi) | YES |
| 2 | PyTorch CUDA available | YES |
| 3 | CPU-only build | NO |

## Recommendation

GPU available (NVIDIA GeForce RTX 4060 Laptop GPU, 8188MB). MinerU should use GPU. Use --device-mode=auto or cuda.
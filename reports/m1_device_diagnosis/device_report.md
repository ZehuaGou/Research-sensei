# M1 Device Diagnosis Report

Generated: 2026-06-11T10:42:31.479512

## System

- Python: 3.13.9 | packaged by Anaconda, Inc. | (main, Oct 21 2025, 19:09:58) [MSC v.1929 64 bit (AMD64)]
- OS: Windows 11 (AMD64)

## GPU / CUDA

- torch installed: True
- torch version: 2.12.0+cpu
- CUDA available: **False**
- CUDA version: None
- GPU name: None
- GPU memory total: None MB
- GPU memory allocated: None MB

## nvidia-smi

- Available: True
- NVIDIA GeForce RTX 4060 Laptop GPU: 8188MB total, 6878MB free, 58C, 0% util

## Dependencies

- transformers: v4.57.6
- accelerate: v1.13.0
- mineru-vl-utils: v1.0.4

## CUDA Issues

- PyTorch installed but CUDA version is None (CPU-only build)

## Recommendation

CUDA not available. MinerU will run on CPU (very slow). Check NVIDIA driver and PyTorch CUDA build.
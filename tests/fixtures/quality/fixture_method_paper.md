# GraphAD: Graph Neural Network for Time Series Anomaly Detection

## Abstract

We propose GraphAD, a graph neural network approach for detecting anomalies
in multivariate time series. Our method constructs a sensor dependency graph
and uses graph convolution to capture inter-sensor correlations. We evaluate
on SWaT and WADI datasets, achieving 95.2% F1-score on SWaT.

## 1. Introduction

Current methods treat each sensor independently, missing cross-sensor
dependencies that are critical for anomaly detection in industrial systems.

## 2. Method

### 2.1 Graph Construction

We build an adjacency matrix A from sensor correlation coefficients.
The graph convolution layer computes: H' = sigma(D^{-1/2} A D^{-1/2} H W)

### 2.2 Anomaly Scoring

The reconstruction error e_t = ||x_t - x_hat_t||^2 is used as anomaly score.
A threshold theta is set at the 95th percentile of training errors.

## 3. Experiments

Dataset: SWaT (51 sensors, 11 days), WADI (123 sensors, 16 days).
Baselines: LSTM-based detector, Isolation Forest, PCA-based method.
Result: GraphAD achieves 95.2% F1 on SWaT, outperforming LSTM (89.1%).

## 4. Limitations

Our method assumes static graph structure, which may not hold for
dynamically changing sensor relationships. The threshold theta requires
manual tuning per dataset.

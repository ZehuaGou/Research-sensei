# Section Samples: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection

## Abstract sample

Time series anomaly detection is important in mod-
ern large-scale systems and is applied in a variety of domains
to analyze and monitor the operation of diverse systems. Unsu-
pervised approaches have received widespread interest, as they
do not require anomaly labels during training, thus avoiding
potentially high costs and having wider applications. Among
these, autoencoders have received extensive attention. They use
reconstruction errors from compressed representations to define
anomaly scores. However, representations learned by autoen-
coders are sensitive to anomalies in training time series, causing
reduced accuracy. We propose a novel encode-then-decompose
paradigm, where we decompose the encoded representation
into stable and auxiliary representations, thereby enhancing
the robustness when training with contaminated time series. In
addition, we propose a novel mutual information based metric
to replace the reconstruction errors for identifying anomalies.
Our proposal demonst

## Introduction sample

Time-ordered data, known as time series, from a variety
of embedded sensors has become the foundation for the
continuous monitoring and management of large-scale sys-
tems across a variety of domains such as healthcare [70],
finance [4], logistics [78], manufacturing [71], and natural
sciences [33]. Time series anomaly detection, an important
branch of time series analysis, constitutes fundamental func-
tionality in data analytics, data management, and data mining.
Time series anomaly detection is receiving increasing attention
in academia and industry, with numerous applications that
include system maintenance [53], network intrusion moni-
toring [55], and credit card fraud detection [74]. The lack
of labeled data and the diversity of anomalies combine to
make the problem of identifying anomalies challenging and
to limit the applicability of methods that require supervision.
This has spurred research on unsupervised methods, leading
to promising results.
Recent neural network based me

## Method sample

We first present an overview of the Encode-then-Decompose
Anomaly Detection (EDAD) framework that efficiently de-
composes a learned hidden time series representation into
stable and auxiliary representations. Next, we present the
objective function, which is based on representation closeness
and mutual information. This function aims to enable robust
training, to contend settings with contaminated training data.
A. Framework Overview
An overview of the framework is shown in Figure 2. The
proposed framework consists of two stages, covering offline
training and online detection. In the offline training stage, the
model training is performed on time series datasets that may
3
Time series
Data
preprocessing
EDAD
Trained
EDAD
Anomaly
scores
Testing
Training
use trained model
Offline training stage
Online detection stage
Figure 2: Framework pipeline. The data preprocessing component is
shared by the offline training and online detection stages.
already include anomalies. In the online detec

## Experiments sample

A. Experimental Settings
1) Datasets: We conduct experiments on eight real-world
datasets that span a wide range of domains, such as manu-
facturing, natural sciences, and healthcare: (1) Pooled Server
Metrics (PSM) [2] is collected from EBAY servers and
records the server monitoring metrics; (2) Soil Moisture Active
Passive (SMAP) [23] is collected by NASA and presents
soil samples and telemetry information from the Mars explo-
ration project; (3) Secure Water Treatment (SWAT) [41] is
collected from a water treatment process in an infrastructure
for research on cyber-security; (4) Mars Science Laboratory
(MSL) [31] is collected by NASA and shows the state of
the sensors in the Mars exploration project; (5) NIPSTS-
SWAN (SWAN) [31] is extracted from solar photospheric
vector magnetograms in Spaceweather HMI Active Region
Patch series; (6) KDD21 [47] is a composite dataset released
for a SIGKDD 2021 competition; (7) Numenta Anomaly
Benchmark (NAB) [3] comprises labeled time series data 

## Conclusion sample

We propose EDAD for unsupervised time series anomaly
detection. The framework addresses a key problem in
autoencoder-based anomaly detection methods: their high
vulnerability to contaminated training data. The framework
decomposes the latent representation into stable features and
auxiliary features that comprise long-term patterns and point-
wise patterns, respectively, rather than blindly reconstructing
the time series. A mutual information criterion is integrated
into the decomposition to support the robustness of the
framework. Experimental studies show that the framework is
effective and can outperform strong baselines and state-of-the-
art methods.
In future research, it is of interest to study anomaly detec-
tion in different settings, such as binary-value settings [77],
semi-supervised settings [35], time series of location-related
information [17], continual learning settings [73], and concept
drift settings [62], [69]. It is also of interest to study different
approaches such

## References sample

[1] E. Abdelaleem, I. Nemenman, and K. M. Martini, “Deep variational mul-
tivariate information bottleneck - A framework for variational losses,”
CoRR, vol. abs/2310.03311, 2023.
[2] A. Abdulaal, Z. Liu, and T. Lancewicki, “Practical approach to asyn-
chronous multivariate time series anomaly detection and localization,”
in Proceedings of the ACM SIGKDD International Conference on
Knowledge Discovery and Data Mining (SIGKDD), 2021, pp. 2485–
2494.
[3] S. Ahmad, A. Lavin, S. Purdy, and Z. Agha, “Unsupervised real-time
anomaly detection for streaming data,” Neurocomputing, vol. 262, pp.
134–147, 2017.
13
[4] C. Bachelard, A. Chalkis, V. Fisikopoulos, and E. P. Tsigaridas, “Ran-
domized geometric tools for anomaly detection in stock markets,” in
Proceedings of the International Conference on Artificial Intelligence
and Statistics (AISTATS), 2023, pp. 9400–9416.
[5] P. Bachman, R. D. Hjelm, and W. Buchwalter, “Learning representations
by maximizing mutual information across views,” in Proc

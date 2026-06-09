# Section Samples: TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data

## Abstract sample

Efficient anomaly detection and diagnosis in multivariate time-

series data is of great importance for modern industrial applications.

However, building a system that is able to quickly and accurately

pinpoint anomalous observations is a challenging problem. This is

due to the lack of anomaly labels, high data volatility and the de-

mands of ultra-low inference times in modern applications. Despite

the recent developments of deep learning approaches for anomaly

detection, only a few of them can address all of these challenges.

In this paper, we propose TranAD, a deep transformer network

based sequence encoders to swiftly perform inference with the

knowledge of the broader temporal trends in the data. TranAD uses

feature extraction and adversarial training to gain stability. Addi-

tionally, model-agnostic meta learning (MAML) allows us to train

the model using limited data. Extensive empirical studies on six pub-

licly available datasets demonstrate that TranAD can outperform

## Introduction sample

Modern IT operations generate enormous amounts of high dimen-

sional sensor data used for continuous monitoring and proper func-

tioning of large-scale datasets. Traditionally, data mining experts

have studied and highlighted data that do not follow usual trends

to report faults. Such reports have been crucial for system man-

agement models for reactive fault tolerance and robust database

design [47]. However, with the advent of big-data analytics and

deep learning, this problem has become of interest to data mining

researchers and to aid experts in handling increasing amounts of

data. One particular use case is in artificial intelligence for Industry-

4.0 databases, with a specific focus on service reliability [38] that

has automated fault detection, recovery and management of mod-

ern systems. Detecting data-faults, or any type of behavior not

conforming to the expected trends, is an active research discipline

referred to as anomaly detection in multivariate time series [11].

Many data-driven industries, including ones related to distributed

computing, Internet of Things (IoT), robotics and urban resource

management [4, 46] are now adopting machine learning based

## Related Work sample

for multivariate anomaly detection and diagnosis. A performance

Time series anomaly detection is a long-studied problem in the

VLDB community. The prior literature works on two types of time-

series data: univariate and multivariate. For the former, various

## Method sample

mance with data and time-efficient training. Specifically, TranAD

increases F1 scores by up to 17%, reducing training times by up to

99% compared to the baselines.

1

Challenges. The problem of anomaly detection is becoming

creasing data modality [18, 28, 54]. In particular, the increasing

number of sensors and devices in contemporary IoT platforms with

increasing data volatility creates the requirement for significant

amounts of data for accurate inference. However, due to the rising

federated learning paradigm with geographically distant clusters,

synchronizing databases across devices is expensive, causing lim-

ited data availability for training [48, 57]. Further, next-generation

applications need ultra-fast inference speeds for quick recovery and

optimal Quality of Service (QoS) [6, 49, 50]. Time-series databases

are generated using several engineering artifacts (servers, robots,

etc.) that interact with the environment, humans or other systems.

As a result, the data often displays both stochastic and temporal

trends [45]. It thus becomes crucial to distinguish outliers due to

stochasticity and only pinpoint observations that do not adhere to

the observed temporal trends. Moreover, the lack of labeled data

and anomaly diversity makes the problem challenging as we cannot

use supervised learning models, which have shown to be effective

in other areas of data mining [12]. Finally, it is not only impor-

tant to detect anomalies but also the root causes, i.e., the specific

data sources leading to abnormal behavior [23]. This complicates

the problem f

## Experiments sample

𝑦= ∨

𝑖𝑦𝑖.

(14)

Thus, we label the current timestamp anomalous if any of the 𝑚

dimensions is anomalous (lines 5-6 in Alg. 2). Figure 2 illustrates

this process for a sample time-series.

SMD dataset (details in Section 4.1). We show the time-series, the

heads) and focus scores for the first six dimensions of the dataset.

It is apparent that the focus scores are highly correlated with the

peaks and noise in the data. There is also a high correlation of focus

scores across dimensions. For timestamps with sudden changes in

the time-series, focus scores are higher. Further, the model gives

series where the deviations are higher. This allows the model to

specifically detect anomalies in each dimension individually, with

the contextual trend of the complete sequence as a prior.

4

NDT [20] (with autoencoder implementation from openGauss [30]),

DAGMM [65], OmniAnomaly [45], MSCRED [60], MAD-GAN [29],

embedding implementation from GraphAn [9]) . For more details

64GB RAM, Nvidia RTX 3080 and Windows 11 OS.

Table 1: Dataset Statistics

Dataset

Train

Test

Dimensions

Anomalies (%)

NAB

4033

4033

1 (6)

0.92

UCR

1600

5900

1 (4)

1.88

MBA

100000

100000

2 (8)

0.14

SMAP

135183

427617

25 (55)

13.13

MSL

58317

73729

55 (3)

10.72

SWaT

496800

449919

51 (1)

11.98

WADI

1048571

172801

123 (1)

5.99

SMD

708405

708420

38 (4)

4.16

MSDS

146430

146430

10 (1)

5.37

we use early-stopping criteria to train TranAD, i.e., we stop the

training process once the validation accuracy starts to decrease.

4.1

Datasets

summarize their characteristic

## Conclusion sample

We present a transformer based anomaly detection model (TranAD)

that can detect and diagnose anomalies for multivariate time-series

data. The transformer based encoder-decoder allows quick model

training and high detection performance for a variety of datasets

considered in this work. TranAD leverages self-conditioning and

adversarial training to amplify errors and gain training stability.

Moreover, meta-learning allows it to be able to identify data trends

even with limited data. Specifically, TranAD achieves an improve-

ment of 17% and 11% for F1 score on complete and limited training

data, respectively. It is also able to correctly identify root causes for

models. It is able to achieve this with up to 99% lower training times

## References sample

[1] Hossein Abbasimehr, Mostafa Shabani, and Mohsen Yousefi. 2020. An optimized

model using LSTM network for demand forecasting. Computers & industrial

engineering 143 (2020), 106435.

[2] Subutai Ahmad, Alexander Lavin, Scott Purdy, and Zuha Agha. 2017. Unsuper-

vised real-time anomaly detection for streaming data. Neurocomputing 262 (2017),

134–147.

[3] Chuadhry Mujeeb Ahmed, Venkata Reddy Palleti, and Aditya P Mathur. 2017.

WADI: a water distribution testbed for research in the design of secure cyber

physical systems. In Proceedings of the 3rd International Workshop on Cyber-

Physical Systems for Smart Water Networks. 25–28.

[4] Julien Audibert, Pietro Michiardi, Frédéric Guyard, Sébastien Marti, and Maria A

Zuluaga. 2020. USAD: UnSupervised Anomaly Detection on Multivariate Time

Series. In Proceedings of the 26th ACM SIGKDD International Conference on Knowl-

edge Discovery & Data Mining. 3395–3404.

[5] Tharindu R Bandaragoda, Kai Ming Ting, David Albrecht, Fei Tony Liu, and

Jonathan R Wells. 2014. Efficient anomaly detection by isolation using near-

est neighbour ensemble. In 2014 IEEE International Conference on Data Mining

Workshop. IEEE, 698–705.

[6] Julian Bellendorf and Zoltán Ádám Mann. 2020. Classification of optimization

problems in fog computing. Future Generation Computer Systems 107 (2020),

158–176.

[7] Nejc Bezak, Mitja Brilly, and Mojca Šraj. 2014. Comparison between the peaks-

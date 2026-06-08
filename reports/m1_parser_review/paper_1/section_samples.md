# Section Samples: Monte Carlo EM for Deep Time Series Anomaly Detection

## Abstract sample

Time series data are often corrupted by outliers or other kinds of anomalies. Identifying the anomalous points can be a goal on its own (anomaly detection), or a means to improving performance of other time series tasks (e.g. forecasting). Recent deep-learning-based approaches to anomaly detection and forecasting commonly assume that the proportion of anomalies in the training data is small enough to ignore, and treat the unlabeled data as coming from the nominal data distribution. We present a simple yet effective technique for augmenting existing time series models so that they explicitly account for anomalies in the training data. By augmenting the training data with a latent anomaly indicator variable whose distribution is inferred while training the underlying model using Monte Carlo EM, our method simultaneously infers anomalous points while improving model performance on nominal data. We demonstrate the effectiveness of the approach by combining it with a simple feed-forward for

## Introduction sample

In many time series anomaly detection applications one only has access to unlabeled data. This data is usually mostly nominal but may contain some (unlabeled) anomalies. Examples of this setting are e.g. the widely used anomaly detection benchmarks SMAP, MSL [\(Hundman et al.,](#page-5-0) [2018\)](#page-5-0), and SMD [\(Su et al.,](#page-5-0) [2019\)](#page-5-0).
This "true" unsupervised setting with *mixed* data can be contrasted with the "nominal-only" setting, where one assumes access to "clean" nominal data. In practice, techniques that
*Proceedings of the* 38 th *International Conference on Machine Learning*, PMLR 139, 2021. Copyright 2021 by the author(s).
(explicitly or implicitly) assume access to nominal data can often also successfully be applied to mixed data by assuming it is nominal, as long as the proportion of anomalies is sufficiently small., they are however biased by training on some anomalous data.
While some time series anomaly detection model rely on the one class 

## Method sample

Forecasting or reconstruction models are designed to learn a model of  $p^+(\cdot)$  but are typically trained directly on the observed time series  $\mathbf{x}_{1:T}$ . We propose to learn the model
of  $p^+(\cdot)$  only from  $\mathbf{y}_{1:T}^+$  by inferring  $z_{1:T} \sim p^z(z_{1:T})$  on the training set. This way we can train the model only on the observed points that are normal, the ones that are equal to  $\mathbf{y}_{1:T}^+$ . Depending on the model, the anomalous points can be treated as missing or the normal point can be inferred.
#### 3.1. Models
Each of the three latent time series is modeled with a probabilistic model: a parametrized model  $p_{\theta}^+$  of the nominal data  $\mathbf{y}_{1:T}^+$ , a fixed model  $p^-$  to model the anomalous data  $\mathbf{y}_{1:T}^-$ , and a model  $p^z$  of the indicator time series  $z_{1:T}$ .
Nominal Data Model Many existing deep anomaly detection methods aim to model the nominal data (e.g. (Shipmon et al., 2017; Zhao et al., 20

## Experiments sample

We make our code available with an illustration notebook. <sup>1</sup>
**Model** We evaluate our approach with a simple forecasting model on both anomaly detection and forecasting tasks. We show the performance of the model when trained in a standard way and when trained with our procedure, which we call our procedure Latent Anomaly Indicator (LAI). We use a simple Multi-Layer Perceptron (MLP) model to parametrise the mean and the variance of a predictive Gaussian distribution. It takes as input the last 25 points.
**Datasets** For the anomaly detection evaluation, we use the **Yahoo** dataset, published by Yahoo labs.<sup>2</sup> It consists of 367 real and synthetic time series, divided into four subsets (A1-A4) with varying level of difficulty. The length of the series vary from 700 to 1700 observations. Labels are available for all the series. We use the last 50% of the time points of each of the time series as test set, like (Ren et al., 2019) did, and split the rest in 40% traini

## Conclusion sample

We present LAI, a method that can be used to wrap any probabilistic time series model to perform anomaly detection without being impacted by unlabeled anomalies in the training set. We present the details of the approach and propose preliminary empirical results on commonly used
#### Monte Carlo EM for Deep Time Series Anomaly Detection
public benchmark datasets. The approach seems to greatly help both for anomaly detection tasks and for training a forecasting model on a contaminated training set.
One can extend this work by wrapping other bigger models such as OmniAnomaly [\(Su et al.,](#page-5-0) [2019\)](#page-5-0) or state-of-the-art forecasting models [\(Benidis et al.,](#page-5-0) [2020\)](#page-5-0). Finally, with our current method at inference time, one has to decide at each incoming point if it is to be replaced or not, one could use particles which would mimic the Monte Carlo approach of the training time.

## References sample

- Benidis, K., Rangapuram, S. S., Flunkert, V., Wang, B., Maddix, D., Turkmen, C., Gasthaus, J., Bohlke-Schneider, M., Salinas, D., Stella, L., et al. Neural forecasting: Introduction and literature overview. *arXiv preprint arXiv:2004.10240*, 2020.
- Carmona, C., Aubet, F.-X., Flunkert, V., and Gasthaus, J. Neural contextual anomaly detection for time series. 2021.
- Dheeru, D. and Taniskidou, E. K. electricity: hourly time series of the electricity consumption of 370 customers, 2017. URL <http://archive.ics.uci.edu/ml>.
- Ehrlich, E., Callot, L., and Aubet, F.-X. Spliced binnedpareto distribution for robust modeling of heavy-tailed time series. *arXiv preprint arXiv:2106.10952*, 2021.
- Fraley, C. and Raftery, A. E. How many clusters? Which clustering method? Answers via model-based cluster analysis. *The Computer Journal*, 41(8):578–588, 1998.
- Hundman, K., Constantinou, V., Laporte, C., Colwell, I., and Soderstrom, T. Detecting spacecraft anomalies using lstms and nonparametric dy

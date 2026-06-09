---
paper_id: 2112.14436
title: "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy"
authors:
  - "Yuxuan Zhang"
  - "Ihor Kats"
  - "Dmitrii Khizbullin"
  - "Yun Yang"
year: 2022
venue: "ICML 2022"
source_type: pdf
source_confidence: 0.8
canonicalization_status: success
canonical_quality_status: PASS
parser_used: pymupdf
m2_ready: true
formula_slot_count: 3
formula_crop_count: 3
parser_latex_count: 3
---

# Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy

## Abstract

Time series data are often corrupted by outliers or
other kinds of anomalies. Identifying the anoma-
lous points can be a goal on its own (anomaly
detection), or a means to improving performance
of other time series tasks (e.g. forecasting). Re-
cent deep-learning-based approaches to anomaly
detection and forecasting commonly assume that
the proportion of anomalies in the training data
is small enough to ignore, and treat the unlabeled
data as coming from the nominal data distribu-
tion. We present a simple yet effective technique
for augmenting existing time series models so
that they explicitly account for anomalies in the
training data. By augmenting the training data
with a latent anomaly indicator variable whose
distribution is inferred while training the under-
lying model using Monte Carlo EM, our method
simultaneously infers anomalous points while im-
proving model performance on nominal data. We
demonstrate the effectiveness of the approach by
combining it with a simple feed-forward forecast-
ing model. We investigate how anomalies in the
train set affect the training of forecasting models,
which are commonly used for time series anomaly
detection, and show that our method improves the
training of the model.

## Introduction

In many time series anomaly detection applications one only
has access to unlabeled data. This data is usually mostly
nominal but may contain some (unlabeled) anomalies. Ex-
amples of this setting are e.g. the widely used anomaly
detection benchmarks SMAP, MSL (Hundman et al., 2018),
and SMD (Su et al., 2019).
This “true” unsupervised setting with mixed data can be con-
trasted with the “nominal-only” setting, where one assumes
access to “clean” nominal data. In practice, techniques that
1 AWS AI Labs 2Technical University of Munich. Correspon-
dence to: Franc¸ois-Xavier Aubet <aubetf@amazon.com>.
Proceedings of the 38 th International Conference on Machine
Learning, PMLR 139, 2021. Copyright 2021 by the author(s).
(explicitly or implicitly) assume access to nominal data can
often also successfully be applied to mixed data by assum-
ing it is nominal, as long as the proportion of anomalies is
sufﬁciently small., they are however biased by training on
some anomalous data.
While some time series anomaly detection model rely on the
one class classiﬁcation paradigm which does not suffer from
this assumption (Shen et al., 2020; Carmona et al., 2021),
the vast majority of the current time series anomaly detec-
tion methods are either forecasting methods (Shipmon et al.,
2017; Zhao et al., 2020) or reconstruction methods (Su et al.,
2019; Xu et al., 2018; Park et al., 2018; Zhang et al., 2019).
Forecasting methods detect anomalies as deviations of ob-
servations from predictions, while reconstruction methods
declare observations that deviate from the reconstruction
as anomalous. In both cases, a probabilistic model of the
observed data is assumed and its parameters are learned.
However, by training the model on the observed data which
contains both normal and anomalous data points, the model
ultimately learns the wrong data distribution. Ehrlich et al.
(2021) propose an approach to make the model robust to
the anomalous points, still the aim is to learn the distri-
bution of both the normal and the anomalous points. We
propose to address this issue using a simple technique based
on latent indicator variables that can readily be combined
with existing probabilistic anomaly detection approaches.
By using latent indicator variables to explicitly infer which
observations in the training set are anomalous, we can sub-
sequently suitably account for the anomalous observations
while training the probabilistic model.
Probabilistic models that use latent (unobserved) indica-
tor variables to explicitly distinguish between nominal and
anomalous data points are well-established in the context
of robust mixture models (e.g. Fraley & Raftery, 1998)
and classical time series models (e.g. Wang et al., 2018).
However, these techniques have not yet been utilized in the
context of recent advances in deep anomaly detection and
time series modeling, presumably due to the (perceived)
increased complexity of the required probabilistic infer-
ence and training procedure. We show that combining la-
tent anomaly indicators with a Monte Carlo Expectation-
Maximization (EM) (Wei & Tanner, 1990) training proce-
dure, results in a simple yet effective technique that can be
combined with (almost) all existing deep anomaly detection
arXiv:2112.14436v1  [cs.LG]  29 Dec 2021
Monte Carlo EM for Deep Time Series Anomaly Detection
and time series forecasting techniques.
We demonstrate the effectiveness of our approach with a
simple model for anomaly detection on the Yahoo anomaly
detection dataset and on the electricity dataset for forecast-
ing from a noisy training set.

### Formula Slots

<!-- formula_id: formula_001 | origin: parser_latex | section: Introduction | page: 1 | bbox: [108.75, 339.5390625, 288.0703125, 370.4765625] | ocr_status: cropped | section_confidence: high | section_source: heading_above | section_reason: exact_match: introduction -->
```latex
p(\mathbf{x}|z) = \begin{cases} p^+(\mathbf{x}) & \text{if } z = 0\\ p^-(\mathbf{x}) & \text{if } z = 1, \end{cases}
```

## Related Work

For non-time series data, one common approach of formal-
izing the notion of anomalies is to assume that the observed
data is generated by a mixture model (Ruff et al., 2020):
each observation x is drawn from the mixture distribution
p(x) = αp+(x) + (1 −α)p−(x), where p+(x) is the dis-
tribution of the nominal data and p−(x) the anomalous data
distribution. Typically one assumes a ﬂexible parametrized
distribution for p+ and a broad, unspeciﬁc distribution for
p−(e.g. a uniform distribution over the extent of the data).
This mixture distribution can equivalently be written us-
ing a binary indicator latent variable z taking value 0 with
probability p(z = 0) = α and value 1 with probability
p(z = 1) = 1 −α, and specifying the conditional distribu-
tion
p(x|z) =
(
p+(x)
if z = 0
p−(x)
if z = 1,
(1)
so that p(x) = P
z p(x|z)p(z) = αp+(x) + (1 −α)p−(x).
In this setup, anomaly detection can be performed by infer-
ring the posterior distribution p(z|x) (and thresholding it if
a hard choice is desired). Yet another way of representing
the same model is generatively: ﬁrst, draw y+ ∼p+(·),
y−∼p−(·), and z ∼Bernoulli(1 −α), and then set
x = I[z = 0] y+ + I[z = 1] y−, i.e. the observation x
is equal to y+ if it is nominal (z = 1) and equal to y−oth-
erwise. Introducing the additional latent variables y+ and
y−is unnecessary in the IID setting, but becomes useful in
the time series setting described next.
In time series setting, where the the observations are time
series x1:T = x1, . . . , xT that exhibit temporal dependen-
cies, and anomalies are time points or regions within these
time series, we have one anomaly indicator variable zt
corresponding to each time point xt.
Like before, the
nominal data is drawn from a parametrized probabilistic
model p+
θ (y1:T ), and the anomalies are generated from
a ﬁxed model p−(y1:T ). For time series data, the mix-
ture data model then amounts to drawing y+
1:T ∼p+(·),
y−
1:T ∼p−(·), and z1:T ∼pz(z1:T ), and setting xt =
I[zt = 0] y+
t + I[zt = 1] y−
t .

## Method

Forecasting or reconstruction models are designed to learn
a model of p+(·) but are typically trained directly on the
observed time series x1:T . We propose to learn the model
of p+(·) only from y+
1:T by inferring z1:T ∼pz(z1:T ) on
the training set. This way we can train the model only on
the observed points that are normal, the ones that are equal
to y+
1:T . Depending on the model, the anomalous points can
be treated as missing or the normal point can be inferred.
3.1. Models
Each of the three latent time series is modeled with a prob-
abilistic model: a parametrized model p+
θ of the nominal
data y+
1:T , a ﬁxed model p−to model the anomalous data
y−
1:T , and a model pz of the indicator time series z1:T .
Nominal Data Model
Many existing deep anomaly detec-
tion methods aim to model the nominal data (e.g. (Shipmon
et al., 2017; Zhao et al., 2020; Su et al., 2019; Xu et al.,
2018; Park et al., 2018; Zhang et al., 2019; Ehrlich et al.,
2021)), and any of them can be used to model y+, the latent
nominal time series. Our method is agnostic to the type of
model used, so that it can be combined with any probabilis-
tic time series model, be it a deep or shallow probabilistic
forecasting method, a reconstruction method, or any other
type of model. We call the model of the latent normal time
series p+
θ , which is parametrised by a set of parameters θ.
In our experiments we demonstrate the general setup by
modeling p+(y+
1:T ) with a simple deep probabilistic fore-
casting model. We decompose p(y+
1:T ) into the telescop-
ing product p(y+
0 ) QT
t=0 p(y+
t+1|y+
t:0) and, making an l-th
order Markov assumption, approximate it with a network
p(y+
t+1|y+
t:t−l) = N(fθ(yt:t−l), gθ(yt:t−l)) taking as input
the last l time points.
Anomalous Data Model
A simple model can be used to
model p−, it does not need to take into account the time
component as there are typically few anomalous points. It
can be modeled with a mixture of Gaussian distributions for
example, with the risk of over-ﬁtting to the few anomalies
of the train set. We simply model p−with a uniform distri-
bution over the domain of the training data, not assuming
any prior on the kind of anomalies that we may expect.
Anomaly Indicator Model
We model the latent anomaly
indicator with a Hidden Markov Model (HMM) with two
states, state zt = 0 corresponds to the point being normal
and state zt = 1 corresponds to the point being anomalous.
Any kind of time series model parameterizing a Bernoulli
distribution can be used to model the latent anomaly indica-
tors, we pick an HMM as it encodes basic time dependencies
while staying a simple model.
If it is available, prior knowledge about the dataset can be
used to initialise the transition matrix. The expected length
of anomalous windows can be used to initialise the transition
probability p(zt+1 = 1|zt = 1). The expected percentage
Monte Carlo EM for Deep Time Series Anomaly Detection
of anomalous points in the dataset can be used to initialise
the transition probability p(zt+1 = 1|zt = 0).
3.2. Training
Our training procedure follows Monte Carlo EM (Wei &
Tanner, 1990). In the E-step we infer pz(z1:T ). In the
M-step we sample from pz(z1:T ), using these samples to
update p+
θ and the transition matrix of the HMM. Algorithm
1 sketches this procedure.
Algorithm 1 Monte Carlo EM for Latent Anomaly Indicator
Input: Observed time series x1:T , model to be trained p+
θ
1 for e ∈{1, . . . , numb epochs} do
// E-step:
2
→infer pz(z1:T )
// M-step:
3
for s ∈{1, . . . , numb samples} do
4
→sample indicator time series zs from pz(z1:T )
5
→perform one epoch of p+
θ on x¬zs where the
points at sampled anomalous indices are replaced
6
end
7
→update the transition matrix of the HMM
8 end
3.2.1. E-STEP
We infer pz(z1:T ) by using the standard forward-backward
algorithm for HMMs, using the following distributions:
p(xt|zt = 0) = p+
θ (xt)
(2)
p(xt|zt = 1) = p−(xt)
(3)
and p(zt+1|zt) is given by the HMM transition matrix.
3.2.2. M-STEP
We want to train p+(·) only from y+
1:T . As most models may
not allow for an analytical update using x1:T and z1:T , we
propose to a Monte Carlo approximation of the expectation
under pz(z1:T ). We draw multiple samples from pz(z1:T )
giving us possible normal points on which p+
θ can be trained.
Each path sampled gives us a set of observed points that can
be considered as coming from the normal data distribution
p+. We maximise the probability of these points under p+
θ ,
treating the points coming from p−points as missing.
Depending on the choice of model for p+
θ , one may not
be able to simply ignore anomalous points and they would
have to be imputed. For deep forecasting or reconstruction
models for example the model has to be given an input for
each time point. In these cases, we propose to impute the
point with the forecast or reconstruction obtained from p+
θ
at the last M-step. This way, we use p+
θ to infer the time
points of y+
1:T that were not observed. With this method we
can recover the full y+
1:T time series and train p+
θ on it.
Depending on the choice of model for p−, one can update it
using the points that are sampled as coming from y−
1:T .
We can update the transition matrix of the HMM with the
classical M-step. The average number of transitions from
one state to the next in the samples from pz(z1:T ) become
the new transition probabilities.
3.3. Inference
At inference time, we propose to use the HMM to perform
ﬁltering on z and infer if incoming points are more likely to
be drawn from p+ or p−. If an incoming point xt is more
likely to be coming from p−it can be treated as missing
or replaced with a sample from p+
θt or by its mode. This
way we ensure that the trained model is only used on points
coming from y+
1:T .

### Formula Slots

<!-- formula_id: formula_002 | origin: parser_latex | section: Method | page: 2 | bbox: [123.0, 420.0, 290.25, 432.0] | ocr_status: cropped | section_confidence: high | section_source: heading_above | section_reason: exact_match: method -->
```latex
p(\mathbf{x}_t|z_t=0) = p_{\theta}^+(\mathbf{x}_t) \tag{2}
```

<!-- formula_id: formula_003 | origin: parser_latex | section: Method | page: 2 | bbox: [123.1171875, 436.5, 289.5, 447.8203125] | ocr_status: cropped | section_confidence: high | section_source: heading_above | section_reason: exact_match: method -->
```latex
p(\mathbf{x}_t|z_t=1) = p^-(\mathbf{x}_t) \tag{3}
```

## Experiments

We make our code available with an illustration notebook. 1
Model
We evaluate our approach with a simple forecast-
ing model on both anomaly detection and forecasting tasks.
We show the performance of the model when trained in a
standard way and when trained with our procedure, which
we call our procedure Latent Anomaly Indicator (LAI).
We use a simple Multi-Layer Perceptron (MLP) model to
parametrise the mean and the variance of a predictive Gaus-
sian distribution. It takes as input the last 25 points.
Datasets
For the anomaly detection evaluation, we use the
Yahoo dataset, published by Yahoo labs.2 It consists of 367
real and synthetic time series, divided into four subsets (A1-
A4) with varying level of difﬁculty. The length of the series
vary from 700 to 1700 observations. Labels are available for
all the series. We use the last 50% of the time points of each
of the time series as test set, like (Ren et al., 2019) did, and
split the rest in 40% training and 10% validation set. We
evaluate the performance of the model using the adjusted F1
score proposed by Xu et al. (2018) and subsequently used
in other work.
In addition, we evaluate the method on forecasting tasks
using the commonly used electricity dataset (Dheeru &
Taniskidou, 2017), composed of 370 time series of 133k
points each. Given the length of the dataset, we sub-sample
it by a factor 10. We select the last 50% of the points of
1https://github.com/Francois-Aubet/gluon-
ts/blob/monte carlo em masking notebook/src/
gluonts/nursery/anomaly detection/Monte-Car
lo-EM-for-Time-Series-Anomaly-Detection-de
mo-notebook.ipynb
2https://webscope.sandbox.yahoo.com/catal
og.php?datatype=s&did=70
Monte Carlo EM for Deep Time Series Anomaly Detection
(a) The ﬁt of a simple MLP without LAI.
(b) The ﬁt of a simple MLP with LAI.
(c) The time series of latent anomaly indicator p(zt = 1).
Figure 1. We ﬁt a MLP on this simple synthetic time series with
anomalies. (a) shows the ﬁt of the model trained in a conventional
way, (b) shows the ﬁt of the model trained as we propose to, (c)
show the inferred p(z1:T ) distribution at the end of the training.
each time series for testing. We scale each time series using
the median and inter-quartile range on the train set.
4.1. Visualization on synthetic data
Figure 1 visualizes the advantage of the method on a simple
sinusoidal time series with the simple MLP for p+
θ . We
generate a synthetic time series and inject outliers in it. We
observe that our approach allows to train the model p+
θ while
ignoring the outliers in the data, whereas the outliers heavily
inﬂuence the model trained conventionally. We observe
from ﬁgure 1c that the model is able to infer accurately
which of the training points are likely to be anomalous.
4.2. Time series anomaly detection
Table 1 shows the F1 score of the model with and without
LAI on the different subsets of the Yahoo dataset. We train
one MLP on each of the time series and average the F1
scores obtained on the different time series of the subset.
We observe that using our approach greatly improves the
performance of the model.
Table 1. F1 score on the different subsets of the Yahoo dataset.
Model
A1
A2
A3
A4
MLP
33.64
53.28
63.25
47.30
MLP + LAI
41.84
87.26
87.91
61.62
In addition to the improved F1 score, we compare the in-
ferred anomalous points on the training set with the actual
labeled anomalous points. Table 2 shows the F1 score on the
training set when using the anomaly indicator as anomaly
score. We observe that our method allows to ﬁnd accurately
the anomalies present in the training set. While the training
and test sets are different, we propose that the higher F1 on
the train set is due to the fact that the model can use the
whole training set to infer if a point is anomalous, and not
only the past points.
Table 2. F1 score on the training set the different subsets of the
Yahoo dataset using the inferred p(zt = 1) as anomaly score.
Model
A1
A2
A3
A4
MLP + LAI
59.48
94.02
81.89
73.77
4.3. Forecasting using a corrupted train set
Our method can be used more generally to train a forecast-
ing model on a forecasting dataset containing anomalies.
We take the electricity forecasting dataset and inject point
outliers in the training set so that about 0.4% of the training
point have an added or subtracted spike. Table 3 shows the
mean absolute error (MAE) on the test set in the setting
where the original train set is used and in the setting where
the noisy train set is used. We see that using our method
allows to reduce signiﬁcantly the increase in error from
the outliers in the training set, only 0.0146 increase in the
mean absolute error versus 0.0542 when training the model
normally.
Table 3. MAE on electricity with and without injecting point out-
liers in the train set
Model
electricity
electricity + outliers
MLP
0.1551
0.2092
MLP + LAI
0.1558
0.1704

## Conclusion

We present LAI, a method that can be used to wrap any
probabilistic time series model to perform anomaly detec-
tion without being impacted by unlabeled anomalies in the
training set. We present the details of the approach and
propose preliminary empirical results on commonly used
Monte Carlo EM for Deep Time Series Anomaly Detection
public benchmark datasets. The approach seems to greatly
help both for anomaly detection tasks and for training a
forecasting model on a contaminated training set.
One can extend this work by wrapping other bigger models
such as OmniAnomaly (Su et al., 2019) or state-of-the-art
forecasting models (Benidis et al., 2020). Finally, with our
current method at inference time, one has to decide at each
incoming point if it is to be replaced or not, one could use
particles which would mimic the Monte Carlo approach of
the training time.
Monte Carlo EM for Deep Time Series Anomaly Detection

## Other

Monte Carlo EM for Deep Time Series Anomaly Detection
Franc¸ois-Xavier Aubet 1 Daniel Z¨ugner 2 Jan Gasthaus 1

## References

Benidis, K., Rangapuram, S. S., Flunkert, V., Wang,
B., Maddix, D., Turkmen, C., Gasthaus, J., Bohlke-
Schneider, M., Salinas, D., Stella, L., et al.
Neural
forecasting: Introduction and literature overview. arXiv
preprint arXiv:2004.10240, 2020.
Carmona, C., Aubet, F.-X., Flunkert, V., and Gasthaus,
J. Neural contextual anomaly detection for time series.
2021.
Dheeru, D. and Taniskidou, E. K. electricity: hourly time
series of the electricity consumption of 370 customers,
2017. URL http://archive.ics.uci.edu/ml.
Ehrlich, E., Callot, L., and Aubet, F.-X. Spliced binned-
pareto distribution for robust modeling of heavy-tailed
time series. arXiv preprint arXiv:2106.10952, 2021.
Fraley, C. and Raftery, A. E. How many clusters? Which
clustering method? Answers via model-based cluster
analysis. The Computer Journal, 41(8):578–588, 1998.
Hundman, K., Constantinou, V., Laporte, C., Colwell, I.,
and Soderstrom, T. Detecting spacecraft anomalies us-
ing lstms and nonparametric dynamic thresholding. In
Proceedings of the 24th ACM SIGKDD international con-
ference on knowledge discovery & data mining, pp. 387–
395, 2018.
Park, D., Hoshi, Y., and Kemp, C. C. A multimodal anomaly
detector for robot-assisted feeding using an lstm-based
variational autoencoder. IEEE Robotics and Automation
Letters, 3(3):1544–1551, 2018.
Ren, H., Xu, B., Wang, Y., Yi, C., Huang, C., Kou, X.,
Xing, T., Yang, M., Tong, J., and Zhang, Q. Time-series
anomaly detection service at microsoft. In Proceedings
of the 25th ACM SIGKDD International Conference on
Knowledge Discovery & Data Mining, pp. 3009–3017,
2019.
Ruff, L., Kauffmann, J. R., Vandermeulen, R. A., Montavon,
G., Samek, W., Kloft, M., Dietterich, T. G., and M¨uller,
K.-R. A unifying review of deep and shallow anomaly
detection. arXiv preprint arXiv:2009.11732, 2020.
Shen, L., Li, Z., and Kwok, J. Timeseries anomaly detection
using temporal hierarchical one-class network. Advances
in Neural Information Processing Systems, 33, 2020.
Shipmon, D. T., Gurevitch, J. M., Piselli, P. M., and Ed-
wards, S. T. Time series anomaly detection; detection
of anomalous drops with limited features and sparse ex-
amples in noisy highly periodic data. arXiv preprint
arXiv:1708.03665, 2017.
Su, Y., Zhao, Y., Niu, C., Liu, R., Sun, W., and Pei, D.
Robust anomaly detection for multivariate time series
through stochastic recurrent neural network. In Proceed-
ings of the 25th ACM SIGKDD International Conference
on Knowledge Discovery & Data Mining, pp. 2828–2837,
2019.
Wang, H., Li, H., Fang, J., and Wang, H. Robust Gaus-
sian Kalman ﬁlter with outlier detection. IEEE Signal
Processing Letters, 25(8):1236–1240, 2018.
Wei, G. C. and Tanner, M. A. A monte carlo implemen-
tation of the em algorithm and the poor man’s data aug-
mentation algorithms. Journal of the American statistical
Association, 85(411):699–704, 1990.
Xu, H., Chen, W., Zhao, N., Li, Z., Bu, J., Li, Z., Liu, Y.,
Zhao, Y., Pei, D., Feng, Y., et al. Unsupervised anomaly
detection via variational auto-encoder for seasonal kpis
in web applications. In Proceedings of the 2018 World
Wide Web Conference, pp. 187–196, 2018.
Zhang, C., Song, D., Chen, Y., Feng, X., Lumezanu, C.,
Cheng, W., Ni, J., Zong, B., Chen, H., and Chawla,
N. V. A Deep Neural Network for Unsupervised Anomaly
Detection and Diagnosis in Multivariate Time Series
Data. Proceedings of the AAAI Conference on Artiﬁ-
cial Intelligence, 33:1409–1416, jul 2019. ISSN 2374-
3468.
doi: 10.1609/aaai.v33i01.33011409.
URL
www.aaai.orghttps://aaai.org/ojs/ind
ex.php/AAAI/article/view/3942.
Zhao, H., Wang, Y., Duan, J., Huang, C., Cao, D., Tong, Y.,
Xu, B., Bai, J., Tong, J., and Zhang, Q. Multivariate time-
series anomaly detection via graph attention network.
arXiv preprint arXiv:2009.02040, 2020.

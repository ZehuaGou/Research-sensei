---
paper_id: 2510_18998
title: "An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version"
source_type: pdf
source_confidence: high
canonicalization_status: success
canonical_quality_status: PASS
primary_parser: mineru25pro
fallback_used: false
m2_ready: true
m2_ready_for_formula_understanding: true
formula_slot_count: 26
mineru_latex_count: 26
raw_formula_text_count: 0
raw_only_formula_dense: false
section_contradiction_count: 0
all_formulas_in_Abstract_suspicious: false
source_pdf_path: "source.pdf"
formula_crop_count: 26
formula_overlay_count: 26
formula_slot_count: 26
mineru_available: true
mineru_raw_payload_backend: "transformers"
mineru_raw_payload_cuda_available: true
mineru_raw_payload_device_mode_actual: "cuda"
mineru_raw_payload_device_mode_requested: "auto"
mineru_raw_payload_elapsed_seconds: 2683.486
mineru_raw_payload_gpu_memory_total_mb: 8188
mineru_raw_payload_gpu_name: "NVIDIA GeForce RTX 4060 Laptop GPU"
mineru_raw_payload_load_seconds: 6.972
mineru_raw_payload_model: "opendatalab/MinerU2.5-Pro-2604-1.2B"
mineru_raw_payload_model_load_backend: "transformers"
mineru_raw_payload_pages: 15
mineru_raw_payload_pages_per_second: 0.006
mineru_raw_payload_parser: "mineru25pro"
mineru_raw_payload_present: true
mineru_raw_payload_seconds_per_page: 178.9
mineru_raw_payload_total_blocks: 361
ollama_changed_by_count: 0
ollama_enabled: false
ollama_json_invalid: 0
ollama_json_valid: 0
ollama_retry_count: 0
ollama_timeout_count: 0
parser_runtime_seconds: 2692.088
primary_parser: "mineru25pro"
runtime_seconds: 1.841
---

# An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version

## Introduction

Time-ordered data, known as time series, from a variety of embedded sensors has become the foundation for the continuous monitoring and management of large-scale systems across a variety of domains such as healthcare  \( [70] \) , finance  \( [4] \) , logistics  \( [78] \) , manufacturing  \( [71] \) , and natural sciences  \( [33] \) . Time series anomaly detection, an important branch of time series analysis, constitutes fundamental functionality in data analytics, data management, and data mining. Time series anomaly detection is receiving increasing attention in academia and industry, with numerous applications that include system maintenance  \( [53] \) , network intrusion monitoring  \( [55] \) , and credit card fraud detection  \( [74] \) . The lack of labeled data and the diversity of anomalies combine to make the problem of identifying anomalies challenging and to limit the applicability of methods that require supervision. This has spurred research on unsupervised methods, leading to promising results.

Recent neural network based methods for time series anomaly detection achieve strong performance on challenging datasets [26]. These methods are able to learn long-term, nonlinear temporal relationships in the data, outperforming

existing “shallow” methods based on similarity search [9], [11], [56] and density-based clustering [14]. Among the neural network based methods, a commonly used paradigm adopts an encoder-decoder mechanism, that first compresses time series into a compact, hidden representation, and then reconstructs the time series from the hidden representation, as illustrated in Figure 1(a). This paradigm employs a so-called autoencoder (AE) [42], which imposes an information bottleneck [1] that encourages the compact latent representation to capture only the most representative patterns of the input time series, while disregarding fluctuations in the time series. Although autoencoders achieve impressive accuracy, they face the following two limitations.

Compress-then-Reconstruct paradigm: AEs employ a Compress-then-Reconstruct paradigm, as shown in Figure 1(a). The training time series \(\mathcal{T}\) are often required to be fully clean, i.e., without anomalies, such that the bottleneck representation captures the most essential, normal patterns. When the training time series includes anomalies, they may pollute the bottleneck representation such that it also captures anomalous patterns, thus adversely affecting anomaly detection, i.e., causing some anomalies to have small reconstruction

1

Table I: Comparison of Autoencoder vs. Encode-then-Decompose Anomaly Detection, where MI denotes mutual information.

<table><tr><td></td><td>AutoEncoder</td><td>EDAD</td></tr><tr><td>Paradigm</td><td>Compress-then-Reconstruct</td><td>Encode-then-Decompose</td></tr><tr><td>Outlier Scores</td><td>Reconstruction Errors</td><td>MI(Y, \( Y_{aux} \))</td></tr><tr><td>Training Loss</td><td>Reconstruction Errors</td><td>MI(Y, \( Y_{sta} \)) + Closeness</td></tr><tr><td>Training Data</td><td>Clean Time Series</td><td>Contaminated Time Series</td></tr></table>

errors. A more robust paradigm that is able to better deal with contaminated training data is desirable.

Symmetric design of loss functions and anomaly scores: The Compress-then-Reconstruct paradigm often uses a symmetric design of the training loss functions and anomaly scores, i.e., both rely on reconstruction errors. This works well if the training data is clean. However, this symmetric design is problematic when training with contaminated time series. Specifically, during training, we still aim to minimize the reconstruction errors between the input time series T and the reconstructed time series  \( \hat{T} \) . If T already includes anomalies, minimizing the training loss drives the autoencoder to learn a bottleneck representation that also captures anomalous patterns caused by anomalies. Thus, in the testing phase, the reconstruction errors for some anomalies may be small and thus difficult to detect. To conclude, this symmetric design causes a problem—training with contaminated data reduces the detection accuracy. This calls for means to avoid this problem.

To address the two limitations, we propose an Encode-then-Decompose Anomaly Detection (EDAD) framework. EDAD employs a novel “Encode-then-Decompose” paradigm with an asymmetric design of loss functions and anomaly scores, where effective mutual information based metrics are proposed to enhance the robustness w.r.t. contaminated training data.

Encode-then-Decompose paradigm: We propose an Encode-then-Decompose paradigm that aims to improve robustness to training with contaminated time series data. Instead of using a single bottleneck representation to capture the information of input time series, we decompose a single representation into two—one representing stable patterns and the other representing auxiliary patterns. This design aims to separate abnormal patterns in contaminated time series from normal patterns, to achieve better robustness than the Compress-then-Reconstruct paradigm.

The proposed decomposition occurs in the latent representation space, which we call a “deep” decomposition, whereas existing time series decompositions often work on the time series themselves, which we refer to as “shallow” decompositions  \( [18] \) ,  \( [61] \) ,  \( [72] \) . Specifically, deep decomposition separates the encoded latent representation into two components: stable features and auxiliary features. The stable features capture shared, invariant patterns across the time series, while the auxiliary features reflect local variations and noise. Importantly, the latent space–constructed through attention modules with linear embedding layers–preserves the

original temporal dependencies [79]. The proposed deep decomposition is achieved by a novel design of shuffle strategies along the time dimension, i.e., randomly changing the time order of the elements in learned representations. Consequently, shuffling the order of data points in this latent space effectively corresponds to shuffling their order in the original data, albeit indirectly. More specifically, the features that are insensitive to shuffling are stable features, whereas the features that are sensitive to shuffling are auxiliary features. This implies that stable features exhibit consistent patterns over time and are not prone to unpredictable fluctuations. In contrast, auxiliary features are sensitive to temporal order, making them effective for capturing localized, short-term patterns, and noise in the time series. This design is fully unsupervised and parameter-free, thus enabling unsupervised anomaly detection when training with unlabeled, contaminated time series data.

Asymmetric design of loss functions and anomaly scores: The proposed Encode-then-Decompose paradigm's decomposition of time series representations into stable features and auxiliary features facilitates an asymmetric design. Instead of using reconstruction errors, we use mutual information as a novel and important metric when designing the training loss and computing anomaly scores. During training, we consider two aspects to guide the framework's learning. First, the auxiliary representation  \( Y_{aux} \) , which represents point-wise features, is sensitive to shuffling, and the stable representation  \( Y_{sta} \) , which represents long-term features such as trend and seasonalities, is insensitive to the shuffling. Second, the stable representation,  \( Y_{sta} \) , and the original hidden representation before decomposition, Y, have large mutual information. This is because the stable representation  \( Y_{sta} \)  captures the majority of the normal patterns in Y according to our definition of stable. During testing, we use the point-wise mutual information between  \( Y_{aux} \)  and Y to obtain anomaly scores because  \( Y_{aux} \)  captures unexpected variations in time series. If Y and  \( Y_{aux} \)  have low mutual information, a time series point is likely to be an anomaly. In summary, the Encode-then-Decompose paradigm facilitates separation between training loss and anomaly scores, thus enabling an asymmetric design.

Table I summarizes key differences between the existing vs. the proposed paradigm. To the best of our knowledge, this is the first study to propose a deep decomposition paradigm for unsupervised time series anomaly detection using mutual information. In summary, the contributions of the paper are as follows. (i) We propose a novel Encode-then-Decompose paradigm to distinguish between long-term patterns (stable features) and short-term patterns (auxiliary features), thus mitigating the negative effects of training on contaminated data. (ii) We propose a latent space point-wise mutual information criterion for anomaly detection and form an asymmetric pipeline with a decomposition framework to improve robustness. We also introduce a novel loss function to train the framework using mutual information. (iii) We report on extensive experiments on eight benchmark datasets using multiple metrics to assess the effectiveness of the proposal and offer detailed insight into its performance characteristics.

2

The rest of the paper is organized as follows. Section II covers preliminaries. Section III details the proposal. Section IV reports on the experimental study, Section V covers related work, and Section VI concludes.

## Related Work

### II. PRELIMINARIES

### A. Time Series

A time series \(\mathcal{T} = \langle \mathbf{s}_1, \mathbf{s}_2, \ldots, \mathbf{s}_N \rangle\) is a sequence of \(N\) time-ordered observations, where each observation \(\mathbf{s}_i \in \mathbb{R}^D\) is collected at a specific time step. If \(D = 1\), \(\mathcal{T}\) is univariate. If \(D > 1\), \(\mathcal{T}\) is multivariate (or multidimensional).

### B. Time Series Anomaly Detection

Given a time series  \( \mathcal{T} = \langle s_{1}, s_{2}, \ldots, s_{N} \rangle \) , we aim at computing an anomaly score  \( \mathcal{AS}(s_{i}) \)  for each observation  \( s_{i} \)  such that the higher  \( \mathcal{AS}(s_{i}) \)  is, the more likely it is that  \( s_{i} \)  is an anomaly. We focus on the unsupervised anomaly detection problem, as no labels (neither for anomalies nor for normal data) are used during training. This follows the definition of “unsupervised” commonly adopted in prior studies [26], [58], [75]. In contrast, semi-supervised anomaly detection assumes access to a small number of labeled normal and/or anomalous instances, which is not the case in our work. Further, we make no assumptions about whether anomalies are point or collective anomalies. If the anomaly scores of continuous observations are high, these observations can be considered as a collective anomaly. As discussed in Section I, in the Compress-then-Reconstruct paradigm, reconstruction errors are used as anomaly scores; in the proposed Encode-then-Decompose paradigm, latent space point-wise mutual information between an encoded representation and auxiliary features is used for defining anomaly scores, which we will detail in Section III.

### C. Mutual Information Estimation for High-Dimensional Data

Mutual information (MI) measures the statistical dependency between random variables. Formally, given random variables \( X \) and \( Y \), the MI between \( X \) and \( Y \), denoted as \( I(X,Y) \), is defined as follows.

<!-- formula_id: formula_001 | origin: mineru_latex | section: Related Work | page: 3 | bbox: [0.13, 0.666, 0.491, 0.705] | source: mineru25pro | block_id: b0037 -->
```latex
I (X, Y) = \sum_ {x \in X} \sum_ {y \in Y} \mathbb {P} (x, y) \log \left(\frac {\mathbb {P} (x , y)}{\mathbb {P} (x) \mathbb {P} (y)}\right) \tag {1}
```

Here, \(\mathbb{P}(x,y)\) indicate the joint distribution, and \(\mathbb{P}(x)\) and \(\mathbb{P}(y)\) are the marginal distributions of \(X\) and \(Y\) obtained through a marginalization process. Note that in the context of time series, both \(X\) and \(Y\) are continuous variables.

Conceptually, MI quantifies the amount of shared information between a pair of random variables, which measures the uncertainty in one variable if the knowledge of the other variable is provided, and vice versa. In other words, the higher the MI value is, the more information the two random variables share—knowing one random variable thus reduces the uncertainty of the other random variable to a large extent. In contrast, if random variables X and Y are independent, they do not share any information, and knowing one random

variable does not reduce the uncertainty of the other random variable, thus making their MI equal to 0.

In this paper, we need to compute the mutual information between timestamps of time series in a latent space. Generally, the representation of timestamps in the latent space can be considered as a high-dimensional vector. Classical mutual information estimation methods are intractable for such vectors [30]. The estimation of mutual information on large-scale data or high-dimensional variables remains challenging.

With the recent advances in mutual information estimation, accurate estimators of mutual information between high-dimensional variables are available. By introducing variational bounds and inequalities, the problem of directly estimating density ratios has been transformed into estimating an optimization problem.

Specifically, we can use the following unnormalized version of the Barber and Agakov approximation  \( I_{\mathrm{UBA}}(X,Y) \)  to approximate the mutual information  \( I(X,Y) \)  between random variables X and Y [52].

<!-- formula_id: formula_002 | origin: mineru_latex | section: Related Work | page: 3 | bbox: [0.504, 0.37, 0.927, 0.439] | source: mineru25pro | block_id: b0044 -->
```latex
\begin{array}{l} I _ {\mathrm{UBA}} (X, Y) \triangleq \mathbb {E} _ {p (x, y)} [ \log q (x | y) ] + h (X) \\ = \mathbb {E} _ {p (x, y)} [ \log p (x) - \log Z (y) + f (x, y) ] + h (X) \\ = \mathbb {E} _ {p (x, y)} [ f (x, y) ] - \mathbb {E} _ {p (y)} [ \log Z (y) ] \tag {2} \\ \end{array}
```

Here, \( h(X) = -\mathbb{E}_{p(x)}[\log (p(x))] \) is the differential entropy of \( X \), \( Z(y) = E_{p(x)}\left[e^{f(x,y)}\right] \), and \( q(x|y) \) denotes the conditional probability of \( X \) given \( Y \), which is defined as follows.

<!-- formula_id: formula_003 | origin: mineru_latex | section: Related Work | page: 3 | bbox: [0.637, 0.498, 0.921, 0.531] | source: mineru25pro | block_id: b0046 -->
```latex
q (x | y) = \frac {p (x)}{Z (y)} e ^ {f (x, y)} \tag {3}
```

Here, \( q(x|y) \) is considered as an energy function in system [13], \( e^{f(x,y)} \) is a tilting function, \( f(x,y): \mathcal{X} \times \mathcal{Y} \to \mathbb{R} \) is a critic function aiming to distinguish whether the \( x \) and \( y \) come from the same joint distribution, and \( Z(y) \) is the associated partition function.

If we use different techniques to deal with the factor in Equation 2, we get a variety of different variational mutual information estimators, including MINE [7], NWJ [7], InfoNCE [66], and JSD [22].

Time Series Anomaly Detection. Many time series anomaly detection approaches exist, including traditional statistical methods, classical machine learning algorithms [14], [56], and modern deep learning methods. Traditional statistical methods detect anomalies by applying an auto-regression mechanism [15], [20], [40]. These methods are easy to implement and deploy. However, their accuracy is relatively low. Classical machine algorithms can be categorized into similarity-based and density-based methods. In similarity-based methods, time series subsequences are compared. The most different subsequences are likely to be anomalies. Senin et al. [56] converted time series subsequences into characters and used grammar rules to detect anomalies. In density-based methods, time series subsequences are grouped into clusters. Clusters with low density are then considered as anomalies. Breunig et al. [14] propose Local Outlier Factor (LOF), which considers the local density of clusters and is able to detect local outliers effectively. Sequeira and Zaki [57] cluster time series subsequences into a fixed number of clusters using a \(k\)-medoids algorithm. Classical machine learning algorithms do not consider time series-specific temporal information, so they cannot be applied well in practical scenarios.

Deep learning based time series anomaly detection methods are used widely in many applications such as object monitoring [80], network analysis [39], robotics [48], and human behaviors analysis [28]. While diffusion-based models have recently shown impressive performance for generative models in terms of reconstruction quality, they are not intensively used in time series anomaly detection, and they also incur substantial computational costs. Crucially, our framework is orthogonal to the backbone choice. Thus, the proposed Encode-then-Decompose paradigm could be integrated with diffusion models. The latest methods include AnomalyTrans [76], which measures the strength of correlations between observations in time series, and DCdetector [77], which achieves impressive performance using a contrastive learning approach with a dual attention component. However, AnomalyTrans and DCdetector do not perform the encode-then-decompose mechanism like us. The most relevant study to our proposal is Robust Autoencoders (RAEs) [81], which decomposes a dataset into clean and anomalous components. The main difference between RAEs and EDAD is that RAEs fail to handle temporal information and thus cannot work on time series. Further, RAEs decompose the data in the original space rather than in the latent representation space, as EDAD does. EDAD also

integrates mutual information to better support decomposition. To the best of our knowledge, EDAD is the first time series anomaly detection method that decomposes the latent variable to achieve robustness.

Mutual Information. Mutual information measures the relationship between statistical variables. Mutual information plays a role in many applications in a wide range of domains. Early approaches typically use nonparametric models for estimating mutual information [30], such as kernel density estimation methods that use kernel functions to estimate the probability density function of data. Deep neural networks and representation learning [66] are being employed increasingly for mutual information estimation to cater to the demands posed by the expanding scale and complexity of contemporary datasets, as well as the need for representation optimization. Notable instances of this approach include Barber-Agakov [6], mutual information neural estimator (MINE) [7], and M-estimators [44]. Existing studies use mutual information to measure the relationship between variables in supervised learning problems where labeled data is available. To the best of our knowledge, our proposal is the first to use mutual information for unsupervised time series anomaly detection.

## Method

### III. METHODOLOGY

We first present an overview of the Encode-then-Decompose Anomaly Detection (EDAD) framework that efficiently decomposes a learned hidden time series representation into stable and auxiliary representations. Next, we present the objective function, which is based on representation closeness and mutual information. This function aims to enable robust training, to contend settings with contaminated training data.

### A. Framework Overview

An overview of the framework is shown in Figure 2. The proposed framework consists of two stages, covering offline training and online detection. In the offline training stage, the model training is performed on time series datasets that may

3

already include anomalies. In the online detection stage, the trained model is used for detecting anomalies.

The data preprocessing component is shared by the offline training and online detection. This component adopts an established technique [25], [58] and applies the dimension independence strategy, which is the state-of-the-art method for time series [79]. This strategy assumes that the dimensions of a time series do not share information. Thus, it disregards correlations between dimensions. When applying the dimension independence strategy, the model is forced to capture long-term temporal dependencies within each channel and preventing it from trivially inferring a variable's value based solely on other channels. Prior studies [38], [45] have also reported that the independence-channel setting usually outperforms cross-channel modeling. In other words, the dimension independence strategy can be considered as a consolidation and temporal augmentation method. We apply the dimension independence strategy as follows. A multivariate time series \(\mathcal{T} \in \mathbb{R}^{N \times D}\) is treated as \(D\) univariate time series \(\mathcal{T}_j \in \mathbb{R}^{N \times 1}, j = 1,2,\ldots,D\). The univariate time series are each standardized and partitioned into overlapping subsequences by using a sliding window of length \(B\). Then, the resulting sequences of length \(B\), are fed into the model for training. Here, we propose EDAD, which is explained in the following parts. After training, the learned models are then employed for online anomaly detection. Specifically, each sequence is preprocessed by the data preprocessing component and then fed into the trained EDAD model that outputs an anomaly score for each observation in the series.

### B. Network Architecture

We propose a novel encoder-decomposer based architecture as the backbone of the EDAD framework, as illustrated in Figure 3.

The framework comprises two components—an encoder and a decomposer. The encoder encompasses an attention module. The decomposer encompasses two modules—stable feature module and auxiliary feature module. The preprocessed time series are input into a normalizing layer to perform instance normalization [65], defined as follows.

<!-- formula_id: formula_004 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.148, 0.836, 0.492, 0.872] | source: mineru25pro | block_id: b0061 -->
```latex
\mathbf {H} _ {t: t + B} = \frac {\mathbf {s} _ {t : t + B} - \mathbb {E} [ \mathbf {s} _ {t : t + B} ]}{\sqrt {\operatorname{Var} [ \mathbf {s} _ {t : t + B} ] + \epsilon}} \cdot \gamma_ {1} + \beta_ {1} \tag {4}
```

Here, the  \( \gamma_{1} \)  and  \( \beta_{1} \)  are learnable parameter vectors, and  \( E[s_{t:t+B}] \)  and  \( Var[s_{t:t+B}] \)  are the expectation and variance

of a time series subsequences, respectively. The output of Equation 4 for  \( s_{t:t+B} \)  is  \( H_{t:t+B} \) . However, for simplicity, we omit  \( t:t+B \)  in the following.

1) Attention Module: The reason for using attention mechanisms is twofold. First, attention mechanisms offer high parallelism and the ability to capture long-range dependencies. Second, in contrast to AE with compression mechanisms, we aim to learn fine-grained representations for each timestamp without any compression along the time dimension. The output of the normalization layer is then fed to a linear embedding layer in the attention module, resulting in the projected vectors  \( H_{emb} \in R^{d} \) .

<!-- formula_id: formula_005 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.649, 0.259, 0.921, 0.275] | source: mineru25pro | block_id: b0065 -->
```latex
\mathbf {H} _ {\mathrm{emb}} = \mathbf {W} _ {\mathrm{emb}} \cdot \mathbf {H} \tag {5}
```

Here,  \( W_{emb} \)  is the weight matrix of the linear embedding layer.

Subsequently, self-attention operations are performed as follows.

<!-- formula_id: formula_006 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.626, 0.338, 0.746, 0.355] | source: mineru25pro | block_id: b0068 -->
```latex
\mathbf {Q} = \mathbf {W} _ {\mathbf {Q}} \cdot \mathbf {H} _ {\text { emb }}
```

<!-- formula_id: formula_007 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.629, 0.358, 0.746, 0.373] | source: mineru25pro | block_id: b0069 -->
```latex
\mathbf {K} = \mathbf {W} _ {\mathbf {K}} \cdot \mathbf {H} _ {\text { emb }}
```

<!-- formula_id: formula_008 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.629, 0.377, 0.921, 0.399] | source: mineru25pro | block_id: b0070 -->
```latex
\mathbf {V} = \mathbf {W} _ {\mathbf {V}} \cdot \mathbf {H} _ {\text {emb}} \tag {6}
```

<!-- formula_id: formula_009 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.633, 0.394, 0.804, 0.429] | source: mineru25pro | block_id: b0071 -->
```latex
\mathbf {S} = \operatorname{softmax} \left(\frac {\mathbf {Q} \cdot \mathbf {K} ^ {\top}}{\sqrt {d}}\right)
```

<!-- formula_id: formula_010 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.622, 0.431, 0.705, 0.445] | source: mineru25pro | block_id: b0072 -->
```latex
\mathbf {Y} _ {1} = \mathbf {S} \cdot \mathbf {V}
```

Here, \(\mathbf{W}_{\mathbf{Q}} \in \mathbb{R}^{d \times d}\), \(\mathbf{W}_{\mathbf{K}} \in \mathbb{R}^{d \times d}\), and \(\mathbf{W}_{\mathbf{V}} \in \mathbb{R}^{d \times d}\) are projection matrices for query, key, and value, respectively. In the specific implementation, we employ a multi-head self-attention mechanism, assuming a total of \(M\) heads producing \(M\) outputs \([\mathbf{Y}_1^1, \ldots, \mathbf{Y}_1^M]\), where each attention head operates in a \(\frac{d}{M}\) dimensional space. Then, the outputs of the \(M\) attention heads are concatenated and projected with a linear transformation, as shown in Equation 7.

<!-- formula_id: formula_011 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.609, 0.596, 0.921, 0.615] | source: mineru25pro | block_id: b0074 -->
```latex
\mathbf {Y} _ {1} = \mathbf {W} _ {\text { mult }} \cdot \left[ \mathbf {Y} _ {1} ^ {1}, \dots , \mathbf {Y} _ {1} ^ {M} \right] ^ {\top} \tag {7}
```

Here, \(\mathbf{W}_{\mathrm{mult}}\) is a learnable parameter to conduct the linear transformation.

The output of multi-head self-attention is then fed to an addition and normalization layer to conduct a residual connection and normalization as shown in Equation 8.

<!-- formula_id: formula_012 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.584, 0.706, 0.921, 0.743] | source: mineru25pro | block_id: b0077 -->
```latex
\mathbf {Y} _ {2} = \mathbf {Y} _ {1} + \frac {\mathbf {Y} _ {1} - \mathbb {E} [ \mathbf {Y} _ {1} ]}{\sqrt {\operatorname{Var} [ \mathbf {Y} _ {1} ] + \epsilon}} \cdot \gamma_ {2} + \beta_ {2} \tag {8}
```

Here, the \(\gamma_{2}\) and \(\beta_{2}\) are learnable parameter vectors, \(\mathbb{E}[\mathbf{Y}_1]\) and \(\mathrm{Var}[\mathbf{Y}_1]\) are the expectation and variance of matrix \(\mathbf{Y}_1\).

The output of the addition and normalizing layer is fed to a multi-layer perceptron (MLP) to conduct a sequence of k linear transformations. We use an MLP with two linear layers and the ReLU activation function.

<!-- formula_id: formula_013 | origin: mineru_latex | section: Method | page: 4 | bbox: [0.613, 0.853, 0.921, 0.871] | source: mineru25pro | block_id: b0080 -->
```latex
\mathbf {Y} _ {3} = \mathbf {W} _ {2} \cdot \operatorname{ReLU} \left(\mathbf {W} _ {1} \cdot \mathbf {Y} _ {2}\right) \tag {9}
```

Here,  \( W_{1} \)  and  \( W_{2} \)  are the learnable weight matrices of the MLP. Finally, the output  \( Y_{3} \)  of the MLP is fed into the second

4

addition and normalization layer, where the computation is similar to that in the first addition and normalization layer, to obtain Y (see Equation 8).

2) Stable and Auxiliary Feature Modules: The output of the attention module, Y, is partitioned into two parts, and each part is fed into one of the two modules—the stable feature module and the auxiliary feature module. Stable features capture shared, invariant information across the time series, while auxiliary features capture local variations and noise. Figure 3(c) shows these two modules.

More specifically, \(\mathbf{Y} = [\mathbf{Y}_{\mathrm{sta}},\mathbf{Y}_{\mathrm{aux}}]\), where \(\mathbf{Y}_{\mathrm{sta}}\in \mathbb{R}^{B\times \frac{d}{2}}\) and \(\mathbf{Y}_{\mathrm{aux}}\in \mathbb{R}^{B\times \frac{d}{2}}\) represent the separated representations that will be fed into the stable and auxiliary modules, respectively.

To facilitate the model's effective learning of these two representations, we have designed both the stable feature module and the auxiliary feature module. The stable features of a time series are the features that span many time steps to represent long-term patterns of the time series. In contrast, the auxiliary features of a time series are the features that only span a few time steps to represent short-term patterns or changes in individual observations of the time series.

To be able to distinguish between stable features and the auxiliary features, we first define two operations—a shuffle operation and an identity operation, which are used in both modules. The shuffle operation, shuffle(·), performs random shuffling along the time dimension. The identity operation, identity(·), represents no change to the input. The shuffle operation is applied along the time dimension within each subsequence window, while all feature dimensions are treated separately. This ensures that the temporal order of data points is manipulated, allowing us to distinguish between stable features (insensitive to shuffling) and auxiliary features (sensitive to shuffling). We proceed to elaborate on the auxiliary module

and the stable module.

Auxiliary Module: In the auxiliary module, we apply an identity operation to  \( Y_{sta} \)  and perform a shuffle operation on  \( Y_{aux} \) . Since the auxiliary features contain information related to specific timestamps, the shuffling of auxiliary features affects the final output sequence. Thus, we apply a shuffle operation to the input feature Y, and the auxiliary features  \( Y_{aux} \)  to maintain consistency. By doing so, we aim to emphasize that the auxiliary features are strongly affected by shuffling because auxiliary features are associated with individual data points. When we modify the order of data points, we emphasize the prominent features of every single data point. Due to the complementary nature of stable features and auxiliary features, we concatenate the two types of features and project the concatenated feature space back to the original latent space. This way,  \( Y_{aux} \)  can capture rapidly changing features.

<!-- formula_id: formula_014 | origin: mineru_latex | section: Method | page: 5 | bbox: [0.606, 0.653, 0.755, 0.67] | source: mineru25pro | block_id: b0095 -->
```latex
\mathbf {Y} _ {\mathrm{sta}} ^ {I} = \text { identity } (\mathbf {Y} _ {\mathrm{sta}})
```

<!-- formula_id: formula_015 | origin: mineru_latex | section: Method | page: 5 | bbox: [0.605, 0.673, 0.921, 0.69] | source: mineru25pro | block_id: b0096 -->
```latex
\mathbf {Y} _ {\text { aux }} ^ {S} = \text { shuffle } (\mathbf {Y} _ {\text { aux }}) \tag {10}
```

<!-- formula_id: formula_016 | origin: mineru_latex | section: Method | page: 5 | bbox: [0.605, 0.692, 0.824, 0.711] | source: mineru25pro | block_id: b0097 -->
```latex
\hat {\mathbf {Y}} _ {\mathrm{aux}} = \mathrm{concat} (\mathbf {Y} _ {\mathrm{sta}} ^ {I}, \mathbf {Y} _ {\mathrm{aux}} ^ {S}) \cdot \mathbf {W} _ {p}
```

Then, we formulate the auxiliary loss that measures the closeness between the two representations, as follows.

<!-- formula_id: formula_017 | origin: mineru_latex | section: Method | page: 5 | bbox: [0.61, 0.761, 0.921, 0.78] | source: mineru25pro | block_id: b0099 -->
```latex
\mathcal {L} _ {\text { aux }} = \| \text { shuffle } (\mathbf {Y}) - \hat {\mathbf {Y}} _ {\text { aux }} \| _ {\mathcal {F}} ^ {2} \tag {11}
```

Stable Module: By definition, stable features remain relatively stable over a long period. Therefore a random perturbation of the stable features at a particular timestamp i, denoted as  \( Y_{sta,i}^{S} \) , should be interchangeable with its pre-perturbation stable feature  \( Y_{sta,i} \) . Therefore, in the stable feature module, we only shuffle  \( Y_{sta} \)  while keeping  \( Y_{aux} \)  unchanged. By doing this, we aim to emphasize that the stable features are persistent and cannot be changed by shuffling because they are contained

5

in long sequences. Finally, after concatenating these two types of features, we apply a projection to obtain the projected representation  \( \hat{Y}_{sta} \) .

<!-- formula_id: formula_018 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.174, 0.118, 0.316, 0.136] | source: mineru25pro | block_id: b0103 -->
```latex
\mathbf {Y} _ {\mathrm{sta}} ^ {S} = \text { shuffle } (\mathbf {Y} _ {\mathrm{sta}})
```

<!-- formula_id: formula_019 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.174, 0.138, 0.49, 0.155] | source: mineru25pro | block_id: b0104 -->
```latex
\mathbf {Y} _ {\text { aux }} ^ {I} = \text { identity } (\mathbf {Y} _ {\text { aux }}) \tag {12}
```

<!-- formula_id: formula_020 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.179, 0.158, 0.395, 0.177] | source: mineru25pro | block_id: b0105 -->
```latex
\hat {\mathbf {Y}} _ {\mathrm{sta}} = \mathrm{concat} (\mathbf {Y} _ {\mathrm{sta}} ^ {S}, \mathbf {Y} _ {\mathrm{aux}} ^ {I}) \cdot \mathbf {W} _ {p}
```

The stable feature module lacks the self-supervisory information (i.e., shuffle) compared to the auxiliary module, which considers the shuffled Y as self-supervisory information. Using a loss function like the one used in the auxiliary module (Equation 11) makes it susceptible to learning a trivial solution that simply copies Y, resulting in meaningless stable features. To avoid this issue, we follow the infomax principle [8], to maximize the mutual information between the input and output. Specifically,  \( Y_{sta} \)  contains the normal modes of Y, so they should have a substantial amount of shared information. We then incorporate the training process of the mutual information estimator into the stable feature module to advocate maximizing the mutual information between Y and  \( Y_{sta} \) , denoted as  \( I_{\theta}(\mathbf{Y}, \mathbf{Y}_{\mathrm{sta}}) \) . The final loss of the stable feature module is then defined as shown in Equation 13.

<!-- formula_id: formula_021 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.165, 0.423, 0.49, 0.442] | source: mineru25pro | block_id: b0107 -->
```latex
\mathcal {L} _ {\mathrm{sta}} = \left\| \mathbf {Y} - \hat {\mathbf {Y}} _ {\mathrm{sta}} \right\| _ {\mathcal {F}} ^ {2} - I _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}) \tag {13}
```

Here,  \( I_{\theta}(\cdot) \)  is the mutual information estimator parameterized by  \( \theta \) . We can choose a specific estimator among many existing ones. We choose InfoNCE as defined in Equation 14 as the default estimator due to its excellent performance as reported in recent studies [7], [22]. Later, we compare it empirically with other estimators (see Section IV-C2).

<!-- formula_id: formula_022 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.076, 0.562, 0.5, 0.594] | source: mineru25pro | block_id: b0109 -->
```latex
I _ {\text {InfoNCE}} = \mathbb {E} _ {\mathbb {P} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}})} \left[ f _ {\theta} \left(\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}\right) \right] - \mathbb {E} _ {\mathbb {P} \left(\mathbf {Y} _ {\mathrm{sta}}\right)} \left[ \mathbb {E} _ {\mathbb {P} (\mathbf {Y})} \left[ e ^ {f _ {\theta} \left(\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}\right)} \right] \right] \tag {14}
```

Here,  \( f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\mathrm{sta}}) \)  is separable critic function defined as shown in Equation 15.

<!-- formula_id: formula_023 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.172, 0.64, 0.49, 0.658] | source: mineru25pro | block_id: b0111 -->
```latex
f _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}) = \phi_ {\theta} (\mathbf {Y}) ^ {\top} \phi_ {\theta} (\mathbf {Y} _ {\mathrm{sta}}), \tag {15}
```

where \(\phi_{\theta}(\cdot)\) is a non-linear transformation function such as a feed-forward neural network.

By proposing the loss function in Equation 13, we aim to achieve three targets. First, the MI measures the statistical dependency between latent representations and input data, offering greater robustness to the separation of the stable features from the original embedded features. Reconstruction error primarily captures point-wise deviations between input and output, which can be unreliable when anomalies are partially reconstructed—especially in the presence of contaminated training data. The MI can avoid the stable features converging into the contamination representation by also considering the number of observations. Because the number of anomalies is small, the anomalies even with large magnitudes cannot affect the MI severely. In this case,  \( Y_{sta} \)  encodes stable features of the time series, and short-term anomalies are less likely to distort

this distribution. Second, this can be seen as introducing the maximization of MI into representation learning, a principle used widely [8], [22]. This approach effectively prevents the model from learning trivial features. Third, it adds the critic function  \( f_{\theta}(\cdot) \)  into the training process. This function is considered as a contrastive loss to provide self-supervisory information to the loss.

### C. Regularization

We observe that both the stable and auxiliary feature modules are parameterized. Further, both modules are fed the output of the encoder, i.e., the stable features and auxiliary features. As a result, both modules share the parameters of the encoder for learning. However, these two types of features represent approximately orthogonal objectives, which can easily lead to conflicting parameter updates [51]. We address this challenge by introducing a teacher-student architecture that serves as a form of consistency regularization [32]. This design encourages the shared encoder parameters to evolve more smoothly and coherently, despite the presence of competing learning signals. Figure 4 illustrates the regularization process. Specifically, we make two copies of EDAD, where the decomposer is disabled and only the encoder is enabled, to serve as a teacher model and a student model. The student model is updated directly via gradient descent and is responsible for learning from the data at each training step [54]. In contrast, the teacher model maintains an exponential moving average of the student's parameters [59]. This design provides a smoother and more stable representation space that reduces the variance introduced by frequent student updates, thereby improving the reliability of mutual information estimation. We use \(\omega\) and \(\psi\) to represent the parameters of the student model and the teacher model, respectively. When computing the consistency regularization, we directly obtain the projected representation from the output representation of the encoder \(\mathbf{Y}'\) through the projection matrix \(\mathbf{W}_p\). The consistency regularization for the student model and the teacher model is computed as shown in Equation 16.

<!-- formula_id: formula_024 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.6, 0.643, 0.921, 0.663] | source: mineru25pro | block_id: b0117 -->
```latex
\mathcal {L} _ {\text { reg }} = \| \mathbf {Y} _ {\omega} ^ {\prime} \cdot \mathbf {W} _ {p} - \mathbf {Y} _ {\psi} ^ {\prime} \cdot \mathbf {W} _ {p} \| _ {\mathcal {F}} ^ {2} \tag {16}
```

Here,  \( Y_{\omega}^{\prime} \)  represents the output representation of the student model, and  \( Y_{\psi}^{\prime} \)  represents the output representation of the teacher model. This way, EDAD is enabled to utilize highly shared weights to partition the features of the time series into two parts, thereby increasing the robustness of the model training.

### D. Objective Function

The overall loss is the weighted sum of the auxiliary reconstruction loss (Equation 11), the stable reconstruction loss (Equation 13), and the regularization (Equation 16).

<!-- formula_id: formula_025 | origin: mineru_latex | section: Method | page: 6 | bbox: [0.591, 0.841, 0.921, 0.858] | source: mineru25pro | block_id: b0121 -->
```latex
\mathcal {L} = \lambda_ {1} \cdot \mathcal {L} _ {\mathrm{sta}} + \lambda_ {2} \cdot \mathcal {L} _ {\mathrm{aux}} + \lambda_ {3} \cdot \mathcal {L} _ {\mathrm{reg}} \tag {17}
```

Hyperparameters  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \)  control the trade-off between the objective function terms. We investigate the sensitivity to  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \)  in the experimental study.

6

### E. Anomaly Scores

We have shaped EDAD to enforce it on learning the stable features by augmenting the stable feature learning with the MI module. The remaining information related to individual observations and short-term patterns is maintained in the auxiliary features. Therefore, the shared information between the original features Y and the auxiliary features  \( Y_{aux} \)  can be used to identify anomalies, which are also related to individual observations and short-term patterns. This enables an “asymmetric” design of the loss function used for training and the definition of anomaly scores.

Given a time series subsequence, we can calculate an anomaly score as the point-wise mutual information between its encoded representation Y and the corresponding auxiliary representation  \( Y_{aux} \) .

Due to the choice of different mutual information estimators, the critic function  \(  f_{\theta}(\cdot)  \)  (see Equation 13) may not necessarily be proportional to  \(  \frac{\mathbb{P}(\mathbf{Y}, \mathbf{Y}_{\mathrm{aux}})}{\mathbb{P}(\mathbf{Y})\mathbb{P}(\mathbf{Y}_{\mathrm{aux}})}  \)  when tightening the lower bound [63], so it cannot be used alone to compute the anomaly scores. Therefore, we employ the entire estimator's forward pass. Let  \( I_{\theta} \)  be the mutual information estimator parameterized by  \( \theta \) . Then, we can compute the anomaly score for each data point  \( s_{i} \)  as follows.

<!-- formula_id: formula_026 | origin: mineru_latex | section: Method | page: 7 | bbox: [0.198, 0.589, 0.49, 0.607] | source: mineru25pro | block_id: b0130 -->
```latex
\mathcal {A} \mathcal {S} (\mathbf {s} _ {i}) = - I _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\text {aux}}) \tag {18}
```

A high score indicates that the input Y and  \( Y_{aux} \)  share less information. Since  \( Y_{aux} \)  includes only short-term variations,  \( s_{i} \)  is more likely to be anomalous.

## Experiments

### A. Experimental Settings

1) Datasets: We conduct experiments on eight real-world datasets that span a wide range of domains, such as manufacturing, natural sciences, and healthcare: (1) Pooled Server Metrics (PSM) [2] is collected from EBAY servers and records the server monitoring metrics; (2) Soil Moisture Active Passive (SMAP) [23] is collected by NASA and presents soil samples and telemetry information from the Mars exploration project; (3) Secure Water Treatment (SWAT) [41] is collected from a water treatment process in an infrastructure for research on cyber-security; (4) Mars Science Laboratory (MSL) [31] is collected by NASA and shows the state of the sensors in the Mars exploration project; (5) NIPSTS-SWAN (SWAN) [31] is extracted from solar photospheric

vector magnetograms in Spaceweather HMI Active Region Patch series; (6) KDD21 [47] is a composite dataset released for a SIGKDD 2021 competition; (7) Numenta Anomaly Benchmark (NAB) [3] comprises labeled time series data from diverse sources, encompassing AWS server metrics, online ad click rates, real-time traffic data, and Twitter mentions of major publicly traded firms; (8) Supraventricular Arrhythmia Database (SVDB) [43] includes 78 half-hour ECG recordings that supplement supraventricular arrhythmias in the MIT-BIH Arrhythmia Database. The eight datasets encompass both multivariate and univariate time series. We acknowledge that datasets such as SWaT, SMAP, and MSL have known limitations, including high anomaly density, inconsistent labels, long anomaly windows, and unrealistic distributions. These issues are discussed in TimeSeAD [68]. Nevertheless, these datasets are widely used in the time-series anomaly detection literature, which motivated our decision to include them in our experiments. We provide statistical information on the experimental datasets in Table II, including the dimensionality of each dataset, its length, and the proportion of anomalies.

2) Baselines: We compare EDAD with thirteen strong and well-known anomaly detection methods. To be comprehensive, we include neural network based anomaly detection methods as well as traditional anomaly detection methods with good performance and published in top venues. Specifically, we include eleven methods: (1) OC-SVM [60] learns a boundary that encompasses the normal data while leaving anomalies outside the boundary; (2) IForest [37] uses an ensemble of isolation trees to detect anomalies; (3) DAGMM [82] integrates a GMM and AE to model the distribution of multidimensional data; (4) Series2Graph [10] is an anomaly detection algorithm that transforms time series into graph structures; (5) SAND [12] is an anomaly detection algorithm designed for streaming data. It identifies anomalous patterns by clustering input data sequences; (6) LSTM-AD [23] uses RNNs to detect anomalies by forecasting over long sequences of data; (7) MAD-GAN [34] employs GAN to recognize anomalies by reconstructing testing samples from the latent space; (8) TranAD [64] utilizes transformer models to infer anomalies by considering broader temporal trends in the data; (9) GDN [19] integrates GNNs and meta-learning with past and recent information to enable anomaly detection; (10) OmniAnomaly [58] integrates GRUs and VAEs to learn robust representations of time series data; (11) IMdiffusion [16] combines time series imputation and diffusion models to achieve robust anomaly detection. (12) AnomalyTrans [76] models prior associations and series associations to capture the association discrepancies; (13) DCdetector [77] detects time series anomalies using robust representations based on contrastive learning. Note that we use the publicly available implementations from the authors of the above methods.

3) Metrics: We use standard metrics for anomaly detection, including Precision \((P)\), Recall \((R)\), F1-score \((F1)\), Area Under the Precision-Recall Curve \((A - PR)\), and Area Under the Receiver Operating Characteristic Curve \((A - ROC)\) [36]. In addition, we report Volume-under-the-Surface of Precision-Recall

7

Table II: Dataset statistics.

<table><tr><td>Dataset</td><td>Dimension</td><td>Average Length</td><td>Anomaly Ratio (%)</td></tr><tr><td>PSM</td><td>25</td><td>220,322</td><td>27.8</td></tr><tr><td>SMAP</td><td>25</td><td>562,800</td><td>12.8</td></tr><tr><td>SWAT</td><td>51</td><td>944,919</td><td>12.0</td></tr><tr><td>MSL</td><td>55</td><td>132,046</td><td>10.5</td></tr><tr><td>SWAN</td><td>38</td><td>120,000</td><td>32.6</td></tr><tr><td>KDD21</td><td>1</td><td>77,415</td><td>10.67</td></tr><tr><td>NAB</td><td>1</td><td>6,301</td><td>2.67</td></tr><tr><td>SVDB</td><td>1</td><td>230,400</td><td>4.68</td></tr></table>

(V-PR) and Volume-under-the-Surface of Receiver Operating Characteristic (V-ROC) [46] to alleviate bias stemming from threshold selections and provide an alternative evaluation perspective on anomaly detection methods, utilizing continuous buffer regions [47]. Each metric offers valuable information.

4) Implementation Details: We implement the proposed framework and baselines by utilizing PyTorch [49] and Scikit-learn 0.24 [50] in Python 3.10. All experiments were executed on a cluster server, which runs Linux Ubuntu 18.04.6 LTS. The server is equipped with an NVIDIA Tesla-A800 GPU with two 64-core AMD CPUs and 512 GiB RAM. The source code is available at https://github.com/zhangbububu/EDAD/.

5) Hyperparameter Settings: Following recent studies [64], [76], [77], the dimensionality \(d\) of the hidden layer is set to 256, the number of encoder layers is set to 3, the number of heads \(M\) in the multi-head attention is set to 8, and the window of the input model \(B\) is set to 100. By doing this we ensure a similar backbone and the fairness of comparison. We set the anomaly ratio to \(1\%\) so that the \(1\%\) of the data points with the highest anomaly scores are anomalies [76]. We use the InfoNCE [66] with separable critics as the mutual information estimator. In addition, we use the Adam optimizer [29] with a learning rate of \(5 \times 10^{-4}\) for model training. Early stopping is adopted in the training process.

To tune  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \) , we vary each of  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \)  among 0.1, 0.5, 1, 2, and 3. After getting the results for all combinations of  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \) , we identify the median result and use the corresponding hyperparameter setting as the default setting. We do not use the best result because, in unsupervised settings, we have no labeled data to enable identifying the best result. Further, we conduct experiments to study the sensitivity of different  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \)  in Section IV-C7. To do so, we vary a chosen hyperparameter in its range while fixing the other hyperparameters to their default values. We also study the effect of window size B in Section IV-C8.

For the other baselines, we use the hyperparameter settings recommended in existing studies if provided. Otherwise, we randomly vary parameters in specific methods, such as the kernel degree in OC-SVM. Then, we report the median of multiple runs using different hyperparameters.

### B. Experimental Results

1) Overall results: We report on the performance of the proposed EDAD and the baselines on all datasets in terms of all metrics—see Table III. We also report average results (see AVERAGE). The top 3 best results for each metric are

highlighted in blue. We observe that the proposed framework achieves the top 3 highest accuracies on most datasets. According to the average results, EDAD achieves the highest P, R, F1, V-PR, and V-ROC, and it achieves the top 3 highest A-PR and A-ROC. This indicates the strong performance of EDAD as well as significant improvements of EDAD over the baselines.

To justify whether the accuracy improvements of the proposed methods EDAD over the baselines are statistically significant, we conduct t-tests to test the significance of the proposed methods against baselines. We consider a null hypothesis  \( H_{0} \)  that the mean of the anomaly scores of our methods is similar to the mean of the anomaly scores of baselines, and an alternative hypothesis  \( H_{1} \)  that the mean of the anomaly scores of our methods is different from the mean of the anomaly scores of baselines. After performing the t-test, we get a p-value, which is smaller than 0.001. This shows strong evidence to reject the null hypothesis  \( H_{0} \) , which in turn suggests that our models have statistically outperformed baselines.

Finally, we acknowledge that it is unrealistic for a single method to be able to outperform all other methods across all datasets and metrics. In other words, there is no one-size-fits-all solution. Thus, it is unrealistic to expect our proposed method EDAD to outperform all baselines in all 56 testing cases (8 datasets × 7 metrics). Among the 56 cases and when compared to 11 other methods, the proposed EDAD is best in 26 cases, and second-best in 9 cases, as shown in Table IV. The state-of-the-art method DCdetector is best in only 2 cases and 2nd best in 18 cases. The Compress-the-Reconstruct based method LSTM-AD is best in 5 cases and 2nd best in 2 cases. This clearly shows that EDAD achieves superior performance.

### C. Ablation Study

1) Effect of Components: We proceed to assess the effectiveness of each individual module in EDAD. For brevity, we only report average results over the eight datasets, as shown in Table V. The results show that EDAD achieves the top 3 highest accuracy when all modules are fully incorporated. If we only include a single feature module, the model with the auxiliary feature module (w/o stable feature module) can yield a better average accuracy when compared to the counterpart with the stable feature module. This suggests that the inclusion of the auxiliary feature, serving as an indicator for calculating anomaly scores, improves EDAD's performance. The regularization is less important than the stable feature and the auxiliary feature modules. However, integrating the regularization into EDAD can improve the performance further. In summary, the empirical findings underscore the importance of each module in EDAD.

2) Effect of Mutual Information Estimators: We study the effect of different mutual information estimators. This experiment aims to characterize accurately the quality of a specific mutual information estimator, which, in turn, facilitates the accurate detection of outliers. Table V compares our default estimator InfoNCE and the state-of-the-art estimators NWJ [44], MINE [7], and JSD [52]. The results show that InfoNCE

8

Table III: P, R, F1, A-PR, A-ROC, V-PR, and V-ROC of anomaly detection methods. The top three highest accuracies are highlighted in blue, where the best and the runner-up results are in bold and underlined text, respectively.

<table><tr><td rowspan="2">Method</td><td colspan="7">PSM</td><td colspan="7">SMAP</td><td colspan="7">SWAT</td></tr><tr><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td></tr><tr><td>OC-SVM</td><td>0.627</td><td>0.706</td><td>0.664</td><td>0.417</td><td>0.619</td><td>0.369</td><td>0.531</td><td>0.512</td><td>0.578</td><td>0.543</td><td>0.101</td><td>0.392</td><td>0.113</td><td>0.518</td><td>0.419</td><td>0.478</td><td>0.447</td><td>0.126</td><td>0.657</td><td>0.133</td><td>0.477</td></tr><tr><td>IForest</td><td>0.627</td><td>0.924</td><td>0.834</td><td>0.334</td><td>0.542</td><td>0.334</td><td>0.541</td><td>0.523</td><td>0.590</td><td>0.555</td><td>0.121</td><td>0.487</td><td>0.135</td><td>0.499</td><td>0.492</td><td>0.449</td><td>0.470</td><td>0.093</td><td>0.345</td><td>0.129</td><td>0.424</td></tr><tr><td>DAGMM</td><td>0.934</td><td>0.700</td><td>0.801</td><td>0.430</td><td>0.647</td><td>0.354</td><td>0.515</td><td>0.864</td><td>0.567</td><td>0.685</td><td>0.135</td><td>0.561</td><td>0.123</td><td>0.468</td><td>0.861</td><td>0.530</td><td>0.656</td><td>0.207</td><td>0.710</td><td>0.241</td><td>0.538</td></tr><tr><td>Series2Graph</td><td>0.906</td><td>0.893</td><td>0.899</td><td>0.546</td><td>0.471</td><td>0.313</td><td>0.512</td><td>0.903</td><td>0.689</td><td>0.782</td><td>0.114</td><td>0.584</td><td>0.137</td><td>0.492</td><td>0.855</td><td>0.809</td><td>0.831</td><td>0.161</td><td>0.280</td><td>0.247</td><td>0.392</td></tr><tr><td>SAND</td><td>0.931</td><td>0.861</td><td>0.895</td><td>0.415</td><td>0.479</td><td>0.401</td><td>0.542</td><td>0.927</td><td>0.826</td><td>0.874</td><td>0.154</td><td>0.455</td><td>0.146</td><td>0.502</td><td>0.867</td><td>0.713</td><td>0.782</td><td>0.142</td><td>0.343</td><td>0.179</td><td>0.463</td></tr><tr><td>LSTM-AD</td><td>0.769</td><td>0.896</td><td>0.828</td><td>0.537</td><td>0.714</td><td>0.523</td><td>0.526</td><td>0.894</td><td>0.781</td><td>0.833</td><td>0.142</td><td>0.579</td><td>0.122</td><td>0.458</td><td>0.861</td><td>0.832</td><td>0.846</td><td>0.094</td><td>0.405</td><td>0.101</td><td>0.250</td></tr><tr><td>MAD-GAN</td><td>0.986</td><td>0.772</td><td>0.866</td><td>0.524</td><td>0.687</td><td>0.451</td><td>0.601</td><td>0.678</td><td>0.603</td><td>0.638</td><td>0.103</td><td>0.423</td><td>0.118</td><td>0.459</td><td>0.791</td><td>0.542</td><td>0.643</td><td>0.139</td><td>0.317</td><td>0.113</td><td>0.350</td></tr><tr><td>TranAD</td><td>0.950</td><td>0.895</td><td>0.922</td><td>0.511</td><td>0.665</td><td>0.352</td><td>0.571</td><td>0.822</td><td>0.850</td><td>0.836</td><td>0.113</td><td>0.416</td><td>0.156</td><td>0.425</td><td>0.702</td><td>0.726</td><td>0.714</td><td>0.126</td><td>0.323</td><td>0.235</td><td>0.356</td></tr><tr><td>GDN</td><td>0.875</td><td>0.838</td><td>0.856</td><td>0.438</td><td>0.657</td><td>0.355</td><td>0.475</td><td>0.907</td><td>0.612</td><td>0.731</td><td>0.096</td><td>0.375</td><td>0.112</td><td>0.414</td><td>0.171</td><td>0.058</td><td>0.086</td><td>0.119</td><td>0.312</td><td>0.113</td><td>0.351</td></tr><tr><td>OmniAnomaly</td><td>0.883</td><td>0.744</td><td>0.808</td><td>0.419</td><td>0.627</td><td>0.439</td><td>0.522</td><td>0.924</td><td>0.819</td><td>0.869</td><td>0.097</td><td>0.378</td><td>0.113</td><td>0.417</td><td>0.814</td><td>0.843</td><td>0.828</td><td>0.121</td><td>0.338</td><td>0.113</td><td>0.351</td></tr><tr><td>IMdiffusion</td><td>0.975</td><td>0.875</td><td>0.923</td><td>0.345</td><td>0.569</td><td>0.337</td><td>0.545</td><td>0.923</td><td>0.889</td><td>0.906</td><td>0.113</td><td>0.468</td><td>0.131</td><td>0.506</td><td>0.932</td><td>0.876</td><td>0.903</td><td>0.129</td><td>0.544</td><td>0.157</td><td>0.503</td></tr><tr><td>AnomalyTrans</td><td>0.969</td><td>0.978</td><td>0.973</td><td>0.396</td><td>0.298</td><td>0.277</td><td>0.486</td><td>0.935</td><td>0.994</td><td>0.964</td><td>0.171</td><td>0.595</td><td>0.157</td><td>0.509</td><td>0.891</td><td>0.992</td><td>0.939</td><td>0.071</td><td>0.179</td><td>0.109</td><td>0.434</td></tr><tr><td>DCdetector</td><td>0.973</td><td>0.985</td><td>0.979</td><td>0.462</td><td>0.481</td><td>0.276</td><td>0.490</td><td>0.955</td><td>0.988</td><td>0.970</td><td>0.151</td><td>0.580</td><td>0.147</td><td>0.502</td><td>0.932</td><td>0.996</td><td>0.963</td><td>0.157</td><td>0.604</td><td>0.149</td><td>0.507</td></tr><tr><td>EDAD (ours)</td><td>0.978</td><td>0.984</td><td>0.981</td><td>0.517</td><td>0.669</td><td>0.382</td><td>0.549</td><td>0.970</td><td>0.974</td><td>0.972</td><td>0.147</td><td>0.599</td><td>0.149</td><td>0.535</td><td>0.938</td><td>1.000</td><td>0.968</td><td>0.172</td><td>0.571</td><td>0.334</td><td>0.512</td></tr><tr><td rowspan="2">Method</td><td colspan="7">MSL</td><td colspan="7">SWAN</td><td colspan="7">KDD21</td></tr><tr><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td></tr><tr><td>OC-SVM</td><td>0.602</td><td>0.873</td><td>0.713</td><td>0.185</td><td>0.593</td><td>0.207</td><td>0.663</td><td>0.474</td><td>0.498</td><td>0.486</td><td>0.326</td><td>0.501</td><td>0.318</td><td>0.509</td><td>0.173</td><td>0.625</td><td>0.271</td><td>0.022</td><td>0.502</td><td>0.025</td><td>0.657</td></tr><tr><td>IForest</td><td>0.541</td><td>0.863</td><td>0.665</td><td>0.173</td><td>0.570</td><td>0.191</td><td>0.649</td><td>0.570</td><td>0.598</td><td>0.583</td><td>0.379</td><td>0.487</td><td>0.375</td><td>0.440</td><td>0.309</td><td>0.607</td><td>0.410</td><td>0.042</td><td>0.561</td><td>0.039</td><td>0.631</td></tr><tr><td>DAGMM</td><td>0.894</td><td>0.637</td><td>0.744</td><td>0.159</td><td>0.566</td><td>0.171</td><td>0.650</td><td>0.436</td><td>0.391</td><td>0.412</td><td>0.471</td><td>0.472</td><td>0.349</td><td>0.403</td><td>0.213</td><td>0.558</td><td>0.308</td><td>0.015</td><td>0.698</td><td>0.032</td><td>0.621</td></tr><tr><td>Series2Graph</td><td>0.937</td><td>0.898</td><td>0.917</td><td>0.176</td><td>0.533</td><td>0.193</td><td>0.608</td><td>0.745</td><td>0.609</td><td>0.670</td><td>0.401</td><td>0.381</td><td>0.343</td><td>0.467</td><td>0.151</td><td>0.593</td><td>0.241</td><td>0.018</td><td>0.484</td><td>0.030</td><td>0.622</td></tr><tr><td>SAND</td><td>0.875</td><td>0.817</td><td>0.845</td><td>0.194</td><td>0.569</td><td>0.188</td><td>0.656</td><td>0.837</td><td>0.575</td><td>0.682</td><td>0.396</td><td>0.370</td><td>0.393</td><td>0.478</td><td>0.218</td><td>0.642</td><td>0.325</td><td>0.016</td><td>0.499</td><td>0.033</td><td>0.623</td></tr><tr><td>LSTM-AD</td><td>0.858</td><td>0.828</td><td>0.842</td><td>0.188</td><td>0.616</td><td>0.214</td><td>0.693</td><td>0.474</td><td>0.211</td><td>0.292</td><td>0.454</td><td>0.463</td><td>0.329</td><td>0.471</td><td>0.215</td><td>0.550</td><td>0.309</td><td>0.013</td><td>0.444</td><td>0.030</td><td>0.618</td></tr><tr><td>MAD-GAN</td><td>0.723</td><td>0.772</td><td>0.746</td><td>0.190</td><td>0.599</td><td>0.209</td><td>0.675</td><td>0.921</td><td>0.589</td><td>0.718</td><td>0.495</td><td>0.501</td><td>0.422</td><td>0.478</td><td>0.100</td><td>0.615</td><td>0.172</td><td>0.019</td><td>0.264</td><td>0.029</td><td>0.634</td></tr><tr><td>TranAD</td><td>0.890</td><td>0.931</td><td>0.910</td><td>0.193</td><td>0.515</td><td>0.217</td><td>0.578</td><td>0.939</td><td>0.579</td><td>0.716</td><td>0.477</td><td>0.499</td><td>0.311</td><td>0.382</td><td>0.097</td><td>0.595</td><td>0.167</td><td>0.036</td><td>0.327</td><td>0.030</td><td>0.623</td></tr><tr><td>GDN</td><td>0.933</td><td>0.687</td><td>0.791</td><td>0.191</td><td>0.603</td><td>0.211</td><td>0.674</td><td>0.928</td><td>0.528</td><td>0.735</td><td>0.485</td><td>0.474</td><td>0.424</td><td>0.478</td><td>0.102</td><td>0.615</td><td>0.175</td><td>0.015</td><td>0.276</td><td>0.028</td><td>0.631</td></tr><tr><td>OmniAnomaly</td><td>0.886</td><td>0.859</td><td>0.872</td><td>0.189</td><td>0.601</td><td>0.213</td><td>0.679</td><td>0.834</td><td>0.461</td><td>0.594</td><td>0.472</td><td>0.503</td><td>0.454</td><td>0.456</td><td>0.102</td><td>0.619</td><td>0.175</td><td>0.018</td><td>0.690</td><td>0.029</td><td>0.641</td></tr><tr><td>IMdiffusion</td><td>0.919</td><td>0.961</td><td>0.940</td><td>0.160</td><td>0.531</td><td>0.179</td><td>0.594</td><td>0.932</td><td>0.566</td><td>0.597</td><td>0.292</td><td>0.481</td><td>0.429</td><td>0.477</td><td>0.290</td><td>0.591</td><td>0.389</td><td>0.015</td><td>0.655</td><td>0.031</td><td>0.611</td></tr><tr><td>AnomalyTrans</td><td>0.930</td><td>0.893</td><td>0.911</td><td>0.215</td><td>0.583</td><td>0.216</td><td>0.682</td><td>0.907</td><td>0.474</td><td>0.622</td><td>0.222</td><td>0.257</td><td>0.402</td><td>0.490</td><td>0.097</td><td>0.595</td><td>0.167</td><td>0.010</td><td>0.578</td><td>0.020</td><td>0.619</td></tr><tr><td>DCdetector</td><td>0.892</td><td>0.867</td><td>0.879</td><td>0.193</td><td>0.572</td><td>0.206</td><td>0.683</td><td>0.951</td><td>0.595</td><td>0.732</td><td>0.286</td><td>0.411</td><td>0.346</td><td>0.494</td><td>0.304</td><td>0.708</td><td>0.425</td><td>0.015</td><td>0.723</td><td>0.023</td><td>0.616</td></tr><tr><td>EDAD (ours)</td><td>0.931</td><td>0.961</td><td>0.946</td><td>0.197</td><td>0.619</td><td>0.194</td><td>0.677</td><td>0.980</td><td>0.593</td><td>0.739</td><td>0.326</td><td>0.501</td><td>0.434</td><td>0.512</td><td>0.310</td><td>0.740</td><td>0.437</td><td>0.017</td><td>0.693</td><td>0.035</td><td>0.633</td></tr><tr><td rowspan="2">Method</td><td colspan="7">NAB</td><td colspan="7">SVDB</td><td colspan="7">AVERAGE</td></tr><tr><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td><td>P</td><td>R</td><td>F1</td><td>A-PR</td><td>A-ROC</td><td>V-PR</td><td>V-ROC</td></tr><tr><td>OC-SVM</td><td>0.437</td><td>0.983</td><td>0.605</td><td>0.336</td><td>0.483</td><td>0.311</td><td>0.614</td><td>0.462</td><td>0.986</td><td>0.629</td><td>0.239</td><td>0.526</td><td>0.230</td><td>0.663</td><td>0.463</td><td>0.716</td><td>0.545</td><td>0.219</td><td>0.534</td><td>0.213</td><td>0.579</td></tr><tr><td>IForest</td><td>0.765</td><td>0.774</td><td>0.769</td><td>0.146</td><td>0.434</td><td>0.230</td><td>0.627</td><td>0.812</td><td>0.732</td><td>0.770</td><td>0.171</td><td>0.594</td><td>0.212</td><td>0.651</td><td>0.580</td><td>0.692</td><td>0.632</td><td>0.182</td><td>0.503</td><td>0.206</td><td>0.558</td></tr><tr><td>DAGMM</td><td>0.501</td><td>0.589</td><td>0.541</td><td>0.360</td><td>0.450</td><td>0.304</td><td>0.647</td><td>0.621</td><td>0.635</td><td>0.628</td><td>0.104</td><td>0.360</td><td>0.215</td><td>0.661</td><td>0.666</td><td>0.576</td><td>0.597</td><td>0.235</td><td>0.558</td><td>0.224</td><td>0.563</td></tr><tr><td>Series2Graph</td><td>0.798</td><td>0.829</td><td>0.813</td><td>0.218</td><td>0.547</td><td>0.326</td><td>0.625</td><td>0.745</td><td>0.917</td><td>0.822</td><td>0.163</td><td>0.327</td><td>0.205</td><td>0.625</td><td>0.755</td><td>0.780</td><td>0.747</td><td>0.225</td><td>0.451</td><td>0.224</td><td>0.543</td></tr><tr><td>SAND</td><td>0.730</td><td>0.900</td><td>0.806</td><td>0.249</td><td>0.456</td><td>0.251</td><td>0.639</td><td>0.755</td><td>0.847</td><td>0.798</td><td>0.187</td><td>0.427</td><td>0.226</td><td>0.662</td><td>0.768</td><td>0.773</td><td>0.751</td><td>0.219</td><td>0.450</td><td>0.227</td><td>0.571</td></tr><tr><td>LSTM-AD</td><td>0.733</td><td>0.821</td><td>0.775</td><td>0.242</td><td>0.411</td><td>0.261</td><td>0.638</td><td>0.803</td><td>0.877</td><td>0.838</td><td>0.144</td><td>0.456</td><td>0.230</td><td>0.658</td><td>0.701</td><td>0.725</td><td>0.695</td><td>0.227</td><td>0.511</td><td>0.226</td><td>0.539</td></tr><tr><td>MAD-GAN</td><td>0.736</td><td>0.898</td><td>0.809</td><td>0.165</td><td>0.317</td><td>0.246</td><td>0.632</td><td>0.619</td><td>0.924</td><td>0.741</td><td>0.117</td><td>0.282</td><td>0.227</td><td>0.657</td><td>0.694</td><td>0.714</td><td>0.667</td><td>0.219</td><td>0.424</td><td>0.227</td><td>0.561</td></tr><tr><td>TranAD</td><td>0.743</td><td>0.920</td><td>0.822</td><td>0.123</td><td>0.587</td><td>0.246</td><td>0.629</td><td>0.610</td><td>0.884</td><td>0.722</td><td>0.105</td><td>0.508</td><td>0.223</td><td>0.632</td><td>0.719</td><td>0.798</td><td>0.726</td><td>0.211</td><td>0.480</td><td>0.221</td><td>0.525</td></tr><tr><td>GDN</td><td>0.753</td><td>0.928</td><td>0.831</td><td>0.115</td><td>0.651</td><td>0.248</td><td>0.632</td><td>0.618</td><td>0.923</td><td>0.740</td><td>0.198</td><td>0.575</td><td>0.225</td><td>0.654</td><td>0.661</td><td>0.649</td><td>0.618</td><td>0.207</td><td>0.490</td><td>0.215</td><td>0.539</td></tr><tr><td>OmniAnomaly</td><td>0.740</td><td>0.920</td><td>0.820</td><td>0.213</td><td>0.652</td><td>0.243</td><td>0.633</td><td>0.625</td><td>0.938</td><td>0.750</td><td>0.162</td><td>0.284</td><td>0.227</td><td>0.657</td><td>0.726</td><td>0.775</td><td>0.715</td><td>0.211</td><td>0.509</td><td>0.229</td><td>0.545</td></tr><tr><td>IMdiffusion</td><td>0.915</td><td>0.846</td><td>0.879</td><td>0.260</td><td>0.638</td><td>0.245</td><td>0.631</td><td>0.719</td><td>0.924</td><td>0.809</td><td>0.217</td><td>0.415</td><td>0.193</td><td>0.624</td><td>0.826</td><td>0.816</td><td>0.793</td><td>0.191</td><td>0.538</td><td>0.213</td><td>0.561</td></tr><tr><td>AnomalyTrans</td><td>0.743</td><td>0.920</td><td>0.822</td><td>0.227</td><td>0.302</td><td>0.219</td><td>0.615</td><td>0.811</td><td>0.865</td><td>0.837</td><td>0.225</td><td>0.320</td><td>0.197</td><td>0.571</td><td>0.785</td><td>0.839</td><td>0.779</td><td>0.192</td><td>0.389</td><td>0.200</td><td>0.551</td></tr><tr><td>DCdetector</td><td>0.915</td><td>0.996</td><td>0.954</td><td>0.228</td><td>0.605</td><td>0.207</td><td>0.616</td><td>0.633</td><td>0.892</td><td>0.853</td><td>0.213</td><td>0.550</td><td>0.190</td><td>0.563</td><td>0.842</td><td>0.878</td><td>0.844</td><td>0.213</td><td>0.566</td><td>0.193</td><td>0.559</td></tr><tr><td>EDAD (ours)</td><td>0.919</td><td>0.997</td><td>0.956</td><td>0.262</td><td>0.661</td><td>0.290</td><td>0.636</td><td>0.828</td><td>0.933</td><td>0.877</td><td>0.231</td><td>0.532</td><td>0.248</td><td>0.668</td><td>0.857</td><td>0.898</td><td>0.860</td><td>0.232</td><td>0.606</td><td>0.258</td><td>0.590</td></tr></table>

performs best, slightly ahead of JSD. This is because both estimators are part of the contrastive variational bounds family and treat mutual information estimation as a classification task-distinguishing joint samples from marginal ones. InfoNCE is a special case of JSD under a specific contrastive loss, and

both optimize similar objectives with different bias-variance trade-offs. While their empirical performance is often comparable, JSD tends to be more sensitive to hyperparameters and initialization, which may affect its robustness. In addition, NWJ and MINE can also suffer from instability due to their reliance

9

Table IV: Overall ranking of anomaly detection methods.

<table><tr><td>Method</td><td>1st</td><td>2nd</td><td>3rd</td></tr><tr><td>OC-SVM</td><td>3</td><td>8</td><td>3</td></tr><tr><td>IForest</td><td>3</td><td>2</td><td>2</td></tr><tr><td>DAGMM</td><td>4</td><td>2</td><td>2</td></tr><tr><td>Series2Graph</td><td>4</td><td>1</td><td>3</td></tr><tr><td>SAND</td><td>0</td><td>1</td><td>5</td></tr><tr><td>LSTM-AD</td><td>3</td><td>3</td><td>3</td></tr><tr><td>MAD-GAN</td><td>3</td><td>3</td><td>3</td></tr><tr><td>TranAD</td><td>1</td><td>3</td><td>3</td></tr><tr><td>GDN</td><td>0</td><td>4</td><td>2</td></tr><tr><td>OmniAnomaly</td><td>2</td><td>3</td><td>1</td></tr><tr><td>IMdiffusion</td><td>1</td><td>4</td><td>5</td></tr><tr><td>AnomalyTrans</td><td>4</td><td>2</td><td>9</td></tr><tr><td>DCdetector</td><td>2</td><td>15</td><td>10</td></tr><tr><td>EDAD (ours)</td><td>26</td><td>9</td><td>10</td></tr></table>

Table V: P, R, F1, A-PR, A-ROC, V-PR, and V-ROC of variants of EDAD averaged over the nine datasets. The second block represents the estimator, and the third block represents the critic function. The symbol  \( \circ \)  indicates that we use the corresponding estimator/critic function instead of the default one. The top three highest accuracies are highlighted with blue, where the best and the runner-up results are in bold and underline text, respectively.

<table><tr><td>Method</td><td>\( P \)</td><td>\( R \)</td><td>\( F1 \)</td><td>\( A-PR \)</td><td>\( A-ROC \)</td><td>\( V-PR \)</td><td>\( V-ROC \)</td></tr><tr><td>EDAD (ours)</td><td>0.817</td><td>0.841</td><td>0.829</td><td>0.206</td><td>0.569</td><td>0.225</td><td>0.567</td></tr><tr><td>w/o Stable module</td><td>0.805</td><td>0.845</td><td>0.810</td><td>0.200</td><td>0.568</td><td>0.229</td><td>0.557</td></tr><tr><td>w/o Auxiliary module</td><td>0.790</td><td>0.826</td><td>0.797</td><td>0.191</td><td>0.561</td><td>0.212</td><td>0.541</td></tr><tr><td>w/o Regularization</td><td>0.807</td><td>0.826</td><td>0.806</td><td>0.210</td><td>0.558</td><td>0.222</td><td>0.566</td></tr><tr><td>○ NWJ</td><td>0.804</td><td>0.841</td><td>0.810</td><td>0.205</td><td>0.562</td><td>0.214</td><td>0.555</td></tr><tr><td>○ JSD</td><td>0.814</td><td>0.845</td><td>0.808</td><td>0.208</td><td>0.562</td><td>0.227</td><td>0.553</td></tr><tr><td>○ MINE</td><td>0.816</td><td>0.828</td><td>0.813</td><td>0.198</td><td>0.559</td><td>0.217</td><td>0.570</td></tr><tr><td>○ Bilinear</td><td>0.808</td><td>0.836</td><td>0.808</td><td>0.205</td><td>0.573</td><td>0.215</td><td>0.561</td></tr><tr><td>○ Concatenated</td><td>0.813</td><td>0.838</td><td>0.805</td><td>0.199</td><td>0.569</td><td>0.215</td><td>0.565</td></tr></table>

on unbounded log density ratios.

3) Effect of Critic Functions: While the estimators of mutual information are crucial in EDAD, there is still a significant interaction between the critic function  \( f_{\theta}(\cdot) \)  and the estimators. The design of the critic function determines its ability to distinguish between joint and marginal distributions. In the next experiment, we consider three commonly used critic functions, including bilinear critics [52], concatenated critics [22], and separable critics [5]. Bilinear critics employ a bilinear function. Concatenated critics combine different inputs and employ a neural network to process them. Separable critics process input data in a separable manner, thus reducing computational complexity. Table V compares our default separable critic function and the two other critic functions, finding that the default separable critics perform the best. This result aligns with findings in the literature [63].

4) Contamination Robustness: We aim to evaluate the robustness of a method at different levels of contamination. To enable this experiment, we modify a proportion of the original observations and consider the modified observations as anomalies [21], [24]. We vary the anomaly ratio among 1%, 2%, 4%, 6%, 8%, 10%, and 20%. For brevity, we conduct experiments on two datasets: SWAT and SVDB, and we compare EDAD with two methods: 1) LSTM-AE, which is a reconstruction-based method employing a Compressthen-Reconstruct paradigm, and 2) DCdetector, which is a robust anomaly detection method. We acknowledge that injected anomalies may not fully reflect the complexity of

Table VI: Effect of model dimensionality on training time (minutes per epoch).

<table><tr><td>d</td><td>EDAD</td><td>DCdetector</td><td>LSTM-AD</td></tr><tr><td>128</td><td>1.06</td><td>1.07</td><td>1.28</td></tr><tr><td>256</td><td>1.21</td><td>3.04</td><td>1.61</td></tr><tr><td>512</td><td>1.82</td><td>10.94</td><td>2.41</td></tr><tr><td>1024</td><td>3.64</td><td>41.64</td><td>4.55</td></tr></table>

Table VII: Effect of model dimensionality on on memory cost (GB).

<table><tr><td>d</td><td>EDAD</td><td>DCdetector</td><td>LSTM-AD</td></tr><tr><td>128</td><td>3.0</td><td>3.9</td><td>2.7</td></tr><tr><td>256</td><td>3.3</td><td>6.5</td><td>5.0</td></tr><tr><td>512</td><td>4.4</td><td>7.6</td><td>9.4</td></tr><tr><td>1024</td><td>6.4</td><td>10.1</td><td>18.4</td></tr></table>

noise found in real-world contaminated data. However, they still serve as a useful proxy for evaluating the robustness of anomaly detection methods. Figure 5 shows the experimental results. We observe that DCdetector performs well with a competitive result due to its ability to learn robust representations by using contrastive learning. However, DCdetector achieves an inferior performance to EDAD. This demonstrates that DCdetector is less robust than EDAD. The results show that EDAD outperforms LSTM-AE w.r.t. all metrics. When the contamination ratio increases, EDAD maintains good performance w.r.t. all metrics. In contrast, LSTM-AE tends to exhibit serious drops in performance. This suggests that EDAD is able to work on contaminated data with performance that is insensitive to the level of contamination.

5) Runtime Analysis: To study the deployment potential of EDAD, we compare its runtime (i.e., online detection time) with two methods in previous experiments: DCdetector and LSTM-AD. First, we determine the runtime on each dataset. Then, we report the average runtime over all datasets. To achieve fair comparisons, we keep the dimensionality of the hidden states d the same across the methods. We also observe that the runtime mainly comes from the offline training time. Table VI reports the time needed (in minutes) to finish one training epoch. The highest results are highlighted with bold text.

The training time results show that EDAD performs the fastest, whereas DCdetector runs much slower. This is because DCdetector has a dual attention component whereas EDAD employs only a single attention. Further, the results show that EDAD is able to train in a very short time. The online detection time of EDAD is small, i.e., less than 0.1 second, making it applicable to online anomaly detection in streaming settings.

6) Memory Analysis: We study the memory consumption of EDAD and compare it with the memory consumption of two methods in previous experiments: DCdetector and LSTM-AD. First, we determine the memory consumption on each dataset. Then, we report the average memory consumption over all datasets. To achieve fair comparisons, we keep the dimensionality of the hidden states d the same across the methods. Table VII shows the RAM (in GB) used by the methods for training. The best results are highlighted with bold text.

10

We observe that EDAD consumes the least memory in most cases except the case d = 128, and DCdetector consumes the most memory. This is because DCdetector has a dual attention component whereas EDAD only uses single attention. This suggests that EDAD is able to perform on low-cost off-the-shelf computers. This enables the use of EDAD in many different resource-limited environments.

7) Effect of \(\lambda_{1}\), \(\lambda_{2}\), and \(\lambda_{3}\): We study the sensitivity of the hyperparameters \(\lambda_{1}\), \(\lambda_{2}\), and \(\lambda_{3}\) in the objective function of EDAD (see Eq. 25). Specifically, we vary one \(\lambda\) among 0.1, 0.5, 1, 2, and 3 while keeping the other two fixed at 1 to investigate the sensitivity to the hyper-parameter. Figure 6 shows the results. First, \(\lambda_{3}\) controls the strength of the regularization loss. In most cases, as it increases, the model's performance decreases gradually. This indicates that an excessively high regularization strength can hinder representation learning. Second, \(\lambda_{1}\) and \(\lambda_{2}\) control the trade-off between the two novel modules in EDAD. They mutually learn different features in

the representations of time series. We observe that when the weights of the two modules are approximately equal, the model achieves the best performance in most cases. This is evidence that the stable and auxiliary modules are equally important and indispensable components of EDAD.

8) Effect of window size B: We study the effect of window size B. More specifically, we vary B among 10, 25, 50, 100, and 200 to investigate the sensitivity to B. Figure 7 shows the experimental results. We observe that when B increases, the model's performance increases gradually and becomes stable with  \( B \geq 50 \) . In many cases, the model's performance achieves the peak with B = 100. Then, the model's performance starts to decrease with B > 100. This observation aligns with existing studies [58], [75], where they claim that deep anomaly detection methods frequently achieve the best accuracy with B is set around 100.

11

### D. Visualization

In order to offer a more comprehensible and intuitive illustration of how our method excels in detecting diverse anomalies within time series data, we intentionally designed and generated various types of anomaly sequences. The primary aim was to visually showcase the model's proficiency in identifying anomalies across different categories. Building upon the categorization of anomaly types as summarized in the work by Lai et al. [31], we subjected our method to the assessment of five specific anomaly types: global, contextual, shapelet, seasonal, and trend. Figure 8 visualizes the detection results. While the figure is adapted from Lai et al., it accurately reflects the characteristics observed by using our proposed method, which is why we chose to include it. The results demonstrate that our proposed framework can detect different types of anomalies. This offers evidence of the effectiveness of our approach and its capability to work on practical problems where different anomaly types occur.

Next, we empirically analyze stable and auxiliary features to further illustrate and understand their sensitivity. Figure 9 visualizes the distribution of stable and auxiliary features for

a toy dataset in two separate low-dimensional spaces using t-SNE [67]. Note that we use the same axis scale for the visualization of auxiliary features and the visualization of stable features. It is clear that the distribution of auxiliary features is more dispersed than that of stable features. Recall that we use different strategies in the proposed stable module and auxiliary module, which leads to different representations. For stable features, we assume that the normal pattern in the time series is persistent and is the normal form of the data, so the distribution of stable features is relatively concentrated. For auxiliary features, they contain noise and anomalies related to timestamps, and this randomness results in the features being relatively dispersed. Furthermore, Figure 10 illustrates

12

how the distributions of stable and auxiliary features evolve across training epochs, again visualized with t-SNE. Initially, the stable and auxiliary features exhibit similar distributions. However, as the training progresses, the distinction between these two feature types becomes increasingly pronounced. By the final stages of training, the auxiliary feature representation provides a clearer separation between normal instances and anomalies, whereas the stable feature representation fails to distinguish them.

## Conclusion

We propose EDAD for unsupervised time series anomaly detection. The framework addresses a key problem in autoencoder-based anomaly detection methods: their high vulnerability to contaminated training data. The framework decomposes the latent representation into stable features and auxiliary features that comprise long-term patterns and pointwise patterns, respectively, rather than blindly reconstructing the time series. A mutual information criterion is integrated into the decomposition to support the robustness of the framework. Experimental studies show that the framework is effective and can outperform strong baselines and state-of-the-art methods.

In future research, it is of interest to study anomaly detection in different settings, such as binary-value settings  \( [77] \) , semi-supervised settings  \( [35] \) , time series of location-related information  \( [17] \) , continual learning settings  \( [73] \) , and concept drift settings  \( [62] \) ,  \( [69] \) . It is also of interest to study different approaches such as ensemble learning  \( [26] \)  and explainability  \( [27] \)  to further improve anomaly detection accuracy.

## References

[1] E. Abdelaleem, I. Nemenman, and K. M. Martini, “Deep variational multivariate information bottleneck - A framework for variational losses,” CoRR, vol. abs/2310.03311, 2023.

[2] A. Abdulaal, Z. Liu, and T. Lancewicki, “Practical approach to asynchronous multivariate time series anomaly detection and localization,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2021, pp. 2485–2494.

[3] S. Ahmad, A. Lavin, S. Purdy, and Z. Agha, “Unsupervised real-time anomaly detection for streaming data,” Neurocomputing, vol. 262, pp. 134–147, 2017.

13

[4] C. Bachelard, A. Chalkis, V. Fisikopoulos, and E. P. Tsigaridas, “Randomized geometric tools for anomaly detection in stock markets,” in Proceedings of the International Conference on Artificial Intelligence and Statistics (AISTATS), 2023, pp. 9400–9416.

[5] P. Bachman, R. D. Hjelm, and W. Buchwalter, “Learning representations by maximizing mutual information across views,” in Proceedings of the Conference on Neural Information Processing Systems (NeurIPS), 2019, pp. 15509–15519.

[6] D. Barber and F. V. Agakov, “Information maximization in noisy channels,” in Proceedings of the Conference on Neural Information Processing Systems (NeurIPS), 2003, pp. 201–208.

[7] M. I. Belghazi, A. Baratin, S. Rajeswar, S. Ozair, Y. Bengio, R. D. Hjelm, and A. C. Courville, “Mutual information neural estimation,” in Proceedings of the International Conference on Machine Learning (ICML), 2018, pp. 530–539.

[8] A. J. Bell and T. J. Sejnowski, “An information-maximization approach to blind separation and blind deconvolution,” Neural Comput., vol. 7, no. 6, pp. 1129–1159, 1995.

[9] P. Boniol, M. Linardi, F. Roncallo, and T. Palpanas, “Automated anomaly detection in large sequences,” in Proceedings of the IEEE International Conference on Data Engineering (ICDE), 2020, pp. 1834–1837.

[10] P. Boniol and T. Palpanas, “Series2Graph: Graph-based subsequence anomaly detection for time series,” Proc. VLDB Endow., vol. 13, no. 12, pp. 1821–1834, 2020.

[11] P. Boniol, J. Paparrizos, Y. Kang, T. Palpanas, R. S. Tsay, A. J. Elmore, and M. J. Franklin, “Theseus: Navigating the labyrinth of time-series anomaly detection,” Proc. VLDB Endow., vol. 15, no. 12, pp. 3702–3705, 2022.

[12] P. Boniol, J. Paparrizos, T. Palpanas, and M. J. Franklin, “SAND: Streaming subsequence anomaly detection,” Proc. VLDB Endow., vol. 14, no. 10, pp. 1717–1729, 2021.

[13] M. Brereton, “A modern course in statistical physics,” Phys. Bull., vol. 27, no. 3, pp. 84–84, 1981.

[14] M. M. Breunig, H. Kriegel, R. T. Ng, and J. Sander, “LOF: identifying density-based local outliers,” in Proceedings of the ACM SIGMOD International Conference on Management of Data (SIGMOD), 2000, pp. 93–104.

[15] C. Chatfield, “The Holt-Winters forecasting procedure,” Appl. Stat., vol. 27, no. 3, p. 264, Jan 1978.

[16] Y. Chen, C. Zhang, M. Ma, Y. Liu, R. Ding, B. Li, S. He, S. Rajmohan, Q. Lin, and D. Zhang, “Imdiffusion: Imputed diffusion models for multivariate time series anomaly detection,” Proc. VLDB Endow., vol. 17, no. 3, pp. 359–372, 2023.

[17] R. Cirstea, B. Yang, C. Guo, T. Kieu, and S. Pan, “Towards spatiotemporal aware traffic time series forecasting,” in Proceedings of the IEEE International Conference on Data Engineering (ICDE), 2022, pp. 2900–2913.

[18] W. P. Cleveland and G. C. Tiao, “Decomposition of seasonal time series: A model for the census x-11 program,” J. Am. Stat. Assoc., vol. 71, no. 355, pp. 581–587, 1976.

[19] A. Deng and B. Hooi, “Graph neural network-based anomaly detection in multivariate time series,” in Proceedings of the AAAI Conference on Artificial Intelligence (AAAI), 2021, pp. 4027–4035.

[20] Z. Du, L. Ma, H. Li, Q. Li, G. Sun, and Z. Liu, “Network traffic anomaly detection based on wavelet analysis,” in Proceedings of the IEEE/ACIS International Conference on Software Engineering, Management and Applications (SERA), 2018, pp. 94–101.

[21] M. Goswami, C. I. Challu, L. Callot, L. Minorics, and A. Kan, “Unsupervised model selection for time series anomaly detection,” in Proceedings of the International Conference on Learning Representations (ICLR), 2023.

[22] R. D. Hjelm, A. Fedorov, S. Lavoie-Marchildon, K. Grewal, P. Bachman, A. Trischler, and Y. Bengio, “Learning deep representations by mutual information estimation and maximization,” in Proceedings of the International Conference on Learning Representations (ICLR), 2019.

[23] K. Hundman, V. Constantinou, C. Laporte, I. Colwell, and T. Söderström, “Detecting spacecraft anomalies using LSTMs and nonparametric dynamic thresholding,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2018, pp. 387–395.

[24] Y. Jeong, E. Yang, J. H. Ryu, I. Park, and M. Kang, “AnomalyBERT: Self-supervised transformer for time series anomaly detection using data degradation scheme,” CoRR, vol. abs/2305.04468, 2023.

[25] T. Kieu, B. Yang, C. Guo, R. Cirstea, Y. Zhao, Y. Song, and C. S. Jensen, "Anomaly detection in time series with robust variational quasi-recurrent autoencoders," in Proceedings of the IEEE International Conference on Data Engineering (ICDE), 2022, pp. 1342-1354.

[26] T. Kieu, B. Yang, C. Guo, and C. S. Jensen, “Outlier detection for time series with recurrent autoencoder ensembles,” in Proceedings of the International Joint Conferences on Artificial Intelligence (IJCAI), 2019, pp. 2725–2732.

[27] T. Kieu, B. Yang, C. Guo, C. S. Jensen, Y. Zhao, F. Huang, and K. Zheng, "Robust and explainable autoencoders for unsupervised time series outlier detection," in Proceedings of the IEEE International Conference on Data Engineering (ICDE), 2022, pp. 3038-3050.

[28] T. Kieu, B. Yang, and C. S. Jensen, "Outlier detection for multidimensional time series using deep neural networks," in Proceedings of the IEEE International Conference on Mobile Data Management (MDM), 2018, pp. 125-134.

[29] D. P. Kingma and J. Ba, "Adam: A method for stochastic optimization," in Proceedings of the International Conference on Learning Representations (ICLR), 2015.

[30] A. Kraskov, H. Stögbauer, and P. Grassberger, “Estimating mutual information,” Phys. Rev. E, vol. 69, pp. 66 138–66 154, 2004.

[31] K. Lai, D. Zha, J. Xu, Y. Zhao, G. Wang, and X. B. Hu, “Revisiting time series outlier detection: Definitions and benchmarks,” in Proceedings of the Conference on Neural Information Processing Systems (NeurIPS), 2021.

[32] S. Laine and T. Aila, “Temporal ensembling for semi-supervised learning,” in Proceedings of the International Conference on Learning Representations (ICLR), 2017.

[33] A. Lerner, D. E. Shasha, Z. Wang, X. Zhao, and Y. Zhu, “Fast algorithms for time series with applications to finance, physics, music, biology, and other suspects,” in Proceedings of the ACM SIGMOD International Conference on Management of Data (SIGMOD), 2004, pp. 965–968.

[34] D. Li, D. Chen, B. Jin, L. Shi, J. Goh, and S. Ng, “MAD-GAN: multivariate anomaly detection for time series data with generative adversarial networks,” in Proceedings of the International Conference on Artificial Neural Networks (ICANN), 2019, pp. 703–716.

[35] S. Li, X. Ji, E. Dobriban, O. Sokolsky, and I. Lee, “PAC-Wrap: Semi-supervised PAC anomaly detection,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2022, pp. 945–955.

[36] Z. Li, Y. Zhao, J. Han, Y. Su, R. Jiao, X. Wen, and D. Pei, “Multivariate time series anomaly detection and interpretation using hierarchical intermetric and temporal embedding,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2021, pp. 3220–3230.

[37] F. T. Liu, K. M. Ting, and Z. Zhou, “Isolation forest,” in Proceedings of the IEEE International Conference on Data Mining (ICDM), 2008, pp. 413–422.

[38] Y. Liu, T. Hu, H. Zhang, H. Wu, S. Wang, L. Ma, and M. Long, "itransformer: Inverted transformers are effective for time series forecasting," in Proceedings of the International Conference on Learning Representations (ICLR), 2024.

[39] T. Luo and S. G. Nagarajan, "Distributed anomaly detection using autoencoder neural networks in WSN for IoT," in Proceedings of the IEEE International Conference on Communications (ICC), 2018, pp. 1-6.

[40] A. Mahimkar, Z. Ge, J. Wang, J. Yates, Y. Zhang, J. Emmons, B. Huntley, and M. Stockert, "Rapid detection of maintenance induced changes in service performance," in Proceedings of the International Conference on Emerging Networking EXperiments and Technologies (CoNEXT), 2011, pp. 1-12.

[41] A. P. Mathur and N. O. Tippenhauer, “SWaT: A water treatment testbed for research and training on ICS security,” in Proceedings of the International Workshop on Cyber-physical Systems for Smart Water Networks (CySWater), 2016, pp. 31–36.

[42] U. Michelucci, “An introduction to autoencoders,” CoRR, vol. abs/2201.03898, 2022.

[43] G. Moody and R. Mark, “The impact of the MIT-BIH arrhythmia database,” IEEE Eng. Med. Biol. Mag., p. 45–50, 2001.

[44] X. Nguyen, M. J. Wainwright, and M. I. Jordan, “Estimating divergence functionals and the likelihood ratio by convex risk minimization,” IEEE Trans. Inf. Theory, vol. 56, no. 11, pp. 5847–5861, 2010.

[45] Y. Nie, N. H. Nguyen, P. Sinthong, and J. Kalagnanam, “A time series is worth 64 words: Long-term forecasting with transformers,” in Pro-

14

ceedings of the International Conference on Learning Representations (ICLR), 2023.

[46] J. Paparrizos, P. Boniol, T. Palpanas, R. Tsay, A. J. Elmore, and M. J. Franklin, “Volume under the surface: A new accuracy evaluation measure for time-series anomaly detection,” Proc. VLDB Endow., vol. 15, no. 11, pp. 2774–2787, 2022.

[47] J. Paparrizos, Y. Kang, P. Boniol, R. S. Tsay, T. Palpanas, and M. J. Franklin, “TSB-UAD: an end-to-end benchmark suite for univariate time-series anomaly detection,” Proc. VLDB Endow., vol. 15, no. 8, pp. 1697–1711, 2022.

[48] D. Park, Z. M. Erickson, T. Bhattacharjee, and C. C. Kemp, “Multimodal execution monitoring for anomaly detection during robot manipulation,” in Proceedings of the IEEE International Conference on Robotics and Automation (ICRA), 2016, pp. 407–414.

[49] A. Paszke, S. Gross, F. Massa, A. Lerer, J. Bradbury, G. Chanan, T. Killeen, Z. Lin, N. Gimelshein, L. Antiga, A. Desmaison, A. Köpf, E. Z. Yang, Z. DeVito, M. Raison, A. Tejani, S. Chilamkurthy, B. Steiner, L. Fang, J. Bai, and S. Chintala, "Pytorch: An imperative style, high-performance deep learning library," in Proceedings of the Conference on Neural Information Processing Systems (NeurIPS), 2019, pp. 8024-8035.

[50] F. Pedregosa, G. Varoquaux, A. Gramfort, V. Michel, B. Thirion, O. Grisel, M. Blondel, P. Prettenhofer, R. Weiss, V. Dubourg, J. Vander-Plas, A. Passos, D. Cournapeau, M. Brucher, M. Perrot, and E. Duchesnay, “Scikit-learn: Machine learning in python,” J. Mach. Learn. Res., vol. 12, pp. 2825–2830, 2011.

[51] J. Peng, J. Zhang, C. Li, G. Wang, X. Liang, and L. Lin, “Pi-NAS: Improving neural architecture search by reducing supernet training consistency shift,” in Proceedings of the IEEE International Conference on Computer Vision (ICCV), 2021, pp. 12334–12344.

[52] B. Poole, S. Ozair, A. van den Oord, A. A. Alemi, and G. Tucker, "On variational bounds of mutual information," in Proceedings of the International Conference on Machine Learning (ICML), 2019, pp. 5171-5180.

[53] J. Ramakrishnan, E. Shaabani, C. Li, and M. A. Sustik, “Anomaly detection for an e-commerce pricing system,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2019, pp. 1917–1926.

[54] S. Ruder, “An overview of gradient descent optimization algorithms,” CoRR, vol. abs/1609.04747, 2016.

[55] R. Sekar, A. Gupta, J. Frullo, T. Shanbhag, A. Tiwari, H. Yang, and S. Zhou, “Specification-based anomaly detection: A new approach for detecting network intrusions,” in Proceedings of the ACM Conference on Computer and Communications Security (CCS), 2002, pp. 265–274.

[56] P. Senin, J. Lin, X. Wang, T. Oates, S. Gandhi, A. P. Boedihardjo, C. Chen, and S. Frankenstein, “Time series anomaly discovery with grammar-based compression,” in Proceedings of the International Conference on Extending Database Technology (EDBT), 2015, pp. 481–492.

[57] K. Sequeira and M. J. Zaki, “ADMIT: Anomaly-based data mining for intrusions,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2002, pp. 386–395.

[58] Y. Su, Y. Zhao, C. Niu, R. Liu, W. Sun, and D. Pei, “Robust anomaly detection for multivariate time series through stochastic recurrent neural network,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2019, pp. 2828–2837.

[59] A. Tarvainen and H. Valpola, “Mean teachers are better role models: Weight-averaged consistency targets improve semi-supervised deep learning results,” in Proceedings of the Conference on Neural Information Processing Systems (NeurIPS), 2017, pp. 1195–1204.

[60] D. M. J. Tax and R. P. W. Duin, “Support vector data description,” Mach. Learn., vol. 54, no. 1, pp. 45–66, 2004.

[61] M. Theodosiou, “Forecasting monthly and quarterly time series using stl decomposition,” Int. J. Forecast., vol. 27, no. 4, pp. 1178–1195, 2011.

[62] H. Tian, N. L. D. Khoa, A. Anaissi, Y. Wang, and F. Chen, “Concept drift adaption for online anomaly detection in structural health monitoring,” in Proceedings of the ACM International Conference on Information and Knowledge Management (CIKM), 2019, pp. 2813–2821.

[63] M. Tschannen, J. Djolonga, P. K. Rubenstein, S. Gelly, and M. Lucic, "On mutual information maximization for representation learning," in Proceedings of the International Conference on Learning Representations (ICLR), 2020.

[64] S. Tuli, G. Casale, and N. R. Jennings, “TranAD: Deep transformer networks for anomaly detection in multivariate time series data,” Proc. VLDB Endow., vol. 15, no. 6, pp. 1201–1214, 2022.

[65] D. Ulyanov, A. Vedaldi, and V. S. Lempitsky, “Instance normalization: The missing ingredient for fast stylization,” CoRR, vol. abs/1607.08022, 2016.

[66] A. van den Oord, Y. Li, and O. Vinyals, “Representation learning with contrastive predictive coding,” CoRR, vol. abs/1807.03748, 2018.

[67] L. Van der Maaten and G. Hinton, “Visualizing data using t-SNE,” J. Mach. Learn Res., vol. 9, no. 11, 2008.

[68] D. Wagner, T. Michels, F. C. F. Schulz, A. Nair, M. Rudolph, and M. Kloft, “Timesead: Benchmarking deep multivariate time-series anomaly detection,” Trans. Mach. Learn. Res., vol. 2023, 2023.

[69] C. Wang, Z. Zhuang, Q. Qi, J. Wang, X. Wang, H. Sun, and J. Liao, "Drift doesn't matter: Dynamic decomposition with diffusion reconstruction for unstable multivariate time series anomaly detection," in Conference on Neural Information Processing Systems (NeurIPS), 2023.

[70] H. Wang, Z. Luo, J. W. L. Yip, C. Ye, and M. Zhang, “ECGGAN: A framework for effective and interpretable electrocardiogram anomaly detection,” in Proceedings of the ACM SIGKDD Conference on Knowledge Discovery and Data Mining (SIGKDD), 2023, pp. 5071–5081.

[71] X. Wang, J. Lin, N. Patel, and M. W. Braun, “A self-learning and online algorithm for time series anomaly detection, with application in CPU manufacturing,” in Proceedings of the ACM International Conference on Information and Knowledge Management (CIKM), 2016, pp. 1823–1832.

[72] M. West, “Time series decomposition,” Biometrika, vol. 84, no. 2, pp. 489–494, 1997.

[73] F. Wiewel and B. Yang, “Continual learning for anomaly detection with variational autoencoder,” in Proceedings of the IEEE International Conference on Acoustics, Speech, and Signal Processing (ICASSP), 2019, pp. 3837–3841.

[74] F. Xiao, Y. Wu, M. Zhang, G. Chen, and B. C. Ooi, “MINT: detecting fraudulent behaviors from time-series relational data,” Proc. VLDB Endow., vol. 16, no. 12, pp. 3610–3623, 2023.

[75] H. Xu, W. Chen, N. Zhao, Z. Li, J. Bu, Z. Li, Y. Liu, Y. Zhao, D. Pei, Y. Feng, J. Chen, Z. Wang, and H. Qiao, “Unsupervised anomaly detection via variational auto-encoder for seasonal KPIs in web applications,” in Proceedings of the ACM Web Conference (WWW), 2018, pp. 187–196.

[76] J. Xu, H. Wu, J. Wang, and M. Long, “Anomaly Transformer: Time series anomaly detection with association discrepancy,” in Proceedings of the International Conference on Learning Representations (ICLR), 2022, pp. 1–20.

[77] Y. Yang, C. Zhang, T. Zhou, Q. Wen, and L. Sun, “DCdetector: Dual attention contrastive representation learning for time serifes anomaly detection,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2023, pp. 3033–3045.

[78] J. Yi, H. Yan, H. Wang, J. Yuan, and Y. Li, “Deepsta: A spatial-temporal attention network for logistics delivery timely rate prediction in anomaly conditions,” in Proceedings of the ACM International Conference on Information and Knowledge Management (CIKM), 2023, pp. 4916–4922.

[79] A. Zeng, M. Chen, L. Zhang, and Q. Xu, “Are transformers effective for time series forecasting?” in Proceedings of the AAAI Conference on Artificial Intelligence (AAAI), 2023, pp. 11121–11128.

[80] Y. Zhao, B. Deng, C. Shen, Y. Liu, H. Lu, and X. Hua, “Spatio-temporal autoencoder for video anomaly detection,” in Proceedings of the ACM Multimedia Conference (MM), 2017, pp. 1933–1941.

[81] C. Zhou and R. C. Paffenroth, “Anomaly detection with robust deep autoencoders,” in Proceedings of the ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (SIGKDD), 2017, pp. 665–674.

[82] B. Zong, Q. Song, M. R. Min, W. Cheng, C. Lumezanu, D. Cho, and H. Chen, “Deep autoencoding gaussian mixture model for unsupervised anomaly detection,” in Proceedings of the International Conference on Learning Representations (ICLR), 2018.

15

## Unknown

arXiv:2510.18998v1 [cs.LG] 21 Oct 2025

### An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data-Extended Version

Buang Zhang \( ^{1} \) , Tung Kieu \( ^{2} \) , Xiangfei Qiu \( ^{1} \) , Chenjuan Guo \( ^{1} \) , Jilin Hu \( ^{1} \)

Aoying Zhou \( ^{1} \) , Christian S. Jensen \( ^{2} \) , Bin Yang \( ^{1} \)

\( ^{1} \) School of Data Science & Engineering, East China Normal University, Shanghai, China

\( ^{2} \) Department of Computer Science, Aalborg University, Aalborg, Denmark

\( ^{1}\{buazhang, xfqiu\}@stu.ecnu.edu.cn, ^{1}\{cjguo, jlhu, ayzhou, byang\}@dase.ecnu.edu.cn, ^{2}\{tungkvt, csj\}@cs.aau.dk \)

Abstract—Time series anomaly detection is important in modern large-scale systems and is applied in a variety of domains to analyze and monitor the operation of diverse systems. Unsupervised approaches have received widespread interest, as they do not require anomaly labels during training, thus avoiding potentially high costs and having wider applications. Among these, autoencoders have received extensive attention. They use reconstruction errors from compressed representations to define anomaly scores. However, representations learned by autoencoders are sensitive to anomalies in training time series, causing reduced accuracy. We propose a novel encode-then-decompose paradigm, where we decompose the encoded representation into stable and auxiliary representations, thereby enhancing the robustness when training with contaminated time series. In addition, we propose a novel mutual information based metric to replace the reconstruction errors for identifying anomalies. Our proposal demonstrates competitive or state-of-the-art performance on eight commonly used multi- and univariate time series benchmarks and exhibits robustness to time series with different contamination ratios.

---
paper_id: 2407_06849
title: "TeVAE: A Variational Autoencoder Approach for Discrete Online Anomaly Detection in Variable-state Multivariate Time-series Data"
source_type: pdf
source_confidence: high
canonicalization_status: success
canonical_quality_status: PASS
primary_parser: mineru25pro
fallback_used: false
m2_ready: true
m2_ready_for_formula_understanding: true
formula_slot_count: 40
mineru_latex_count: 40
raw_formula_text_count: 0
raw_only_formula_dense: false
section_contradiction_count: 0
all_formulas_in_Abstract_suspicious: false
source_pdf_path: "source.pdf"
formula_crop_count: 40
formula_overlay_count: 40
formula_slot_count: 40
mineru_available: true
mineru_raw_payload_backend: "transformers"
mineru_raw_payload_elapsed_seconds: 16570.615
mineru_raw_payload_load_seconds: 30.697
mineru_raw_payload_model: "opendatalab/MinerU2.5-Pro-2604-1.2B"
mineru_raw_payload_pages: 20
mineru_raw_payload_parser: "mineru25pro"
mineru_raw_payload_present: true
mineru_raw_payload_total_blocks: 307
ollama_changed_by_count: 0
ollama_enabled: false
ollama_json_invalid: 0
ollama_json_valid: 0
ollama_retry_count: 0
ollama_timeout_count: 0
parser_runtime_seconds: 16602.573
primary_parser: "mineru25pro"
runtime_seconds: 3.026
---

# TeVAE: A Variational Autoencoder Approach for Discrete Online Anomaly Detection in Variable-state Multivariate Time-series Data

## Abstract

As attention to recorded data grows in the realm of automotive testing and manual evaluation reaches its limits, there is a growing need for automatic online anomaly detection. This real-world data is complex in many ways and requires the modelling of testee behaviour. To address this, we propose a temporal variational autoencoder (TeVAE) that can detect anomalies with minimal false positives when trained on unlabelled data. Our approach also avoids the bypass phenomenon and introduces a new method to remap individual windows to a continuous time series. Furthermore, we propose metrics to evaluate the detection delay and root-cause capability of our approach and present results from experiments on a real-world industrial data set. When properly configured, TeVAE flags anomalies only 6% of the time wrongly and detects 65% of anomalies present. It also has the potential to perform well with a smaller training and validation subset but requires a more sophisticated threshold estimation method.

## Introduction

Anomaly detection in time-series data has emerged as a common problem with a variety of real-world applications, from the medical field  \( [16] \)  to high-performance computing  \( [24] \) . Findings from the field of anomaly detection are also of particular interest to the modern automotive industry. This industry is very diverse, including, for example, manufacturing, prototyping and testing. Furthermore, a car is a complex structure that can be segmented into different subsystems, one of them being the powertrain, which includes all components required for longitudinal dynamics. The powertrain is an important subsystem, as it is something a customer interacts with when driving or being driven. Therefore, testing the powertrain is an integral part of the wider automotive powertrain development and is undertaken at different stages of development. Each of these stages is composed of many integration levels. These integration levels range from powertrain sub-component testing, such as the electric drive unit (EDU) controller or high-voltage battery (HVB) management system, to whole vehicle powertrain testing. For each integration level there is a special type of controlled environment, called a test bench. The use-case in this paper is on an endurance powertrain test bench, where the EDU and HVB on their own are tested under different conditions and loads for longer periods to simulate wear over time. Given the costly maintenance and upkeep costs of such test benches, it is desirable to keep

Preprint. Under review.

downtime at a minimum and to avoid faulty records. Also, it is desirable to detect problems early to prevent damage to the testee. Online time-series anomaly detection is especially relevant, as it can provide timely insights into potentially harming behaviour that deviates from the norm.

Applying anomaly detection to this real-world use case is especially challenging due to its complexity and highly dynamic setup. During powertrain testing several sensors record signals over time, leading to data in the form of multivariate time series. These signals not only have correlations within themselves over time but also between each other. In addition to that, some of the signals recorded also feature variable-state behaviour, meaning the same test done at different times will yield slightly different data. This is due to certain channels like the battery signals presenting slightly different behaviour depending on how warm or charged the battery is. All these characteristics exclude the use of simpler statistical models as they are not compatible with all of the mentioned data properties.

Given that evaluation is currently done manually by inspection, it is not feasible to analyse every single test, also evaluation tends to be delayed, only being undertaken days after the test is recorded, hence there is a clear need for automatic, fast and unsupervised evaluation methodology which can flag anomalous behaviour before the next testing procedure is started.

To achieve this, we propose a temporal multi-head attention-based variational autoencoder (TeVAE). TeVAE consists of a bidirectional long short-term memory (BiLSTM) variational autoencoder architecture that maps a time-series window into a temporal latent distribution  \( [17] \)   \( [24] \) . Also, a multi-head attention (MA) mechanism is added to further enhance the sampled latent matrix before it is passed on to the decoder. As shown in the ablation study, this approach avoids the so-called bypassed phenomenon  \( [3] \) , which is the first contribution. Furthermore, this paper offers a unique methodology for the reverse-window process. It is used for remapping the fixed-length windows the model is trained on to continuous variable-length sequences, i.e. time series. Moreover, we propose a set of metrics apt to online time-series anomaly detection that is not only interpretable and simple but is also compatible with discrete time-series anomaly detection. Lastly, the root-cause capability of TeVAE is investigated, for which a new metric, the root-cause precision, is also proposed.

This paper is structured as follows: First, a short background is provided in Section 2 on the powertrain testing methodology specific to this use case, as well as the theory behind VAEs and MA mechanisms. Then, related work in variational autoencoder-based time-series anomaly detection is presented in Section 3, followed by an in-depth introduction of the real-world data set and the approach we propose in Section 4. Then, several experiments testing different aspects of the proposed method are conducted and discussed in Section 5, along with the final results. Finally, conclusions from this work are drawn and an outlook into future work is provided in Section 6. The source code for the data pre-processing, model training as well as evaluation can be found under https://github.com/lcs-crr/TeVAE.

## Related Work

### 2 Background

### 2.1 Real-world Application: Automotive Powertrain Testing

During endurance testing a portfolio of different drive cycles is run, where a drive cycle is a standardised driving pattern characterised by the vehicle speed, which enables repeatability. For this type of testing, the portfolio consists exclusively of proprietary drive cycles, which differ from the public drive cycles used, for example, for vehicle fuel/energy consumption certification. The reason why proprietary drive cycles are used for endurance runs is that they allow for more extensive loading of the powertrain.

Given the presence of a battery in the testee, some time has to be dedicated to battery soaking (sitting idle) and charging. These procedures are also standardised using soaking and charging cycles, respectively, although, for the intents and purposes of this paper, they are omitted. What is left in the portfolio are eight dynamic drive cycles representing short, long, fast, slow and dynamic trips ranging from 5 to 30 minutes. Modelling the testee behaviour is further complicated through variable-state behaviour. This means that two measurements of the same drive cycle done one after another will look different, depending on initial states. A measurement is defined as an instance of a drive cycle and is in the form of a multivariate time series or sequence. Variable-state behaviour can be categorised into short-term reversible and long-term irreversible. On the one hand, there are channels like the battery temperature or state of charge (SoC) that contribute to the short-term reversible kind since the battery heats up and discharges as it is used. On the other hand, processes like battery ageing, also known as

2

Table 1: Channels (features) chosen for modelling testee behaviour [7]. Indices correspond to Figure 1.

<table><tr><td>Index</td><td>Name</td></tr><tr><td>1</td><td>Vehicle Speed</td></tr><tr><td>2</td><td>EDU Torque</td></tr><tr><td>3</td><td>Left Axle Torque</td></tr><tr><td>4</td><td>Right Axle Torque</td></tr><tr><td>5</td><td>EDU Current</td></tr><tr><td>6</td><td>EDU Voltage</td></tr><tr><td>7</td><td>HVB Current</td></tr><tr><td>8</td><td>HVB Voltage</td></tr><tr><td>9</td><td>HVB Temperature</td></tr><tr><td>10</td><td>HVB State of Charge</td></tr><tr><td>11</td><td>EDU Rotor Temperature</td></tr><tr><td>12</td><td>EDU Stator Temperature</td></tr><tr><td>13</td><td>Inverter Temperature</td></tr></table>

the state of health (SoH), contribute to long-term irreversible behaviour, which is not considered and modelled in this use-case.

On powertrain test benches, there are several control methods to ensure the testee maintains the given drive cycle, i.e. the vehicle speed profile. In this particular test bench, the regulation is done by the acceleration pedal position and the EDU revolutions per minute (rpm).

### 2.2 Data Set

To enable the development of anomaly detection methodology that can deal with the above-mentioned challenges, a data set is created using the data for one of the testees. This real-world data set \(\mathcal{D}\) consists of thousands measurement files, each of variable length and containing hundreds of (many redundant or empty) channels. The training subset \(\mathcal{D}^{\mathrm{train}}\) consists of \(M = 2785\) unlabelled time series such that \(\mathcal{D}^{\mathrm{train}} = [\mathcal{S}_1,\dots,\mathcal{S}_m,\)

\( \ldots, S_{M}] \) . Note that each time series in  \( D^{train} \)  has variable length  \( T_{m} \)  and dimensionality  \( d_{D} \) , such that  \( S_{m} \in R^{T_{m} \times d_{D}} \) . For this work, a list of representative  \( d_{D} = 13 \)  channels is hand-picked in consultation with the test bench engineers. The chosen features along with their indices are as shown in Table 1.

The testing subset \(\mathcal{D}^{\mathrm{test}}\) consists of \(N\) labelled time series such that \(\mathcal{D}^{\mathrm{test}} = [\mathcal{S}_1,\dots,\mathcal{S}_n,\dots,\mathcal{S}_N]\), where each time series in \(\mathcal{D}^{\mathrm{test}}\) has variable length \(T_{n}\) and dimensionality \(d_{\mathcal{D}}\), such that \(\mathcal{S}_n\in \mathbb{R}^{T_n\times dp}\). The labelled anomaly-free portion of the testing subset \(\mathcal{D}^{\mathrm{test}}\) accounts for \(N_{\mathrm{af}} = 698\) measurements, where a measurement is considered anomaly-free when the testee behaviour conforms to the norm.

Due to the absence of labelled anomalies in the dataset, realistic anomalous events are intentionally simulated and recorded following the advice of test bench engineers. To this end, four anomaly types are recorded. Every anomaly type is recorded for every drive cycle at least once, leading to  \( N_{a} = 47 \)  anomalous measurements that are all used as the labelled anomalous portion of the testing subset  \( D^{test} \) . Hence  \( D^{test} \)  is made up of N = 745 measurements, representing an anomaly ratio of around  \( N_{a}/N = 6.3\% \) , however in reality this value is estimated to be much lower. This amount of anomalous data in relation to anomaly-free data is used as it approximately matches the anomaly ratio in public data sets [15, 1, 11, 24] and because the data set is not large enough to create a larger anomaly-free test subset.

In the first type, the virtual wheel diameter is changed, such that the resulting vehicle speed deviates from the norm. The wheel diameter is a parameter as resistances are connected to the shafts rather than actual wheels. This accounts for 16 time-series anomalies and the only channel that demonstrates anomalous behaviour is the vehicle speed, since:

<!-- formula_id: formula_001 | origin: mineru_latex | section: Related Work | page: 3 | bbox: [0.45, 0.861, 0.825, 0.875] | source: mineru25pro | block_id: b0049 -->
```latex
v _ {\text { vehicle }} = r \cdot \omega \tag {1}
```

where \( r \) is the wheel radius and \( \omega \) the angular velocity of the drive shaft. Logically, the anomalous behaviour is most visible at higher speeds.

3

A plot of one anomaly-free (black) and one wheel-diameter anomalous (red) measurement is shown in Figure 1. Visual inspection may suggest that the red plot is trivial to detect given the large deviation in the EDU and HVB voltage, temperature and state of charge compared to the black plot. However, this deviation is in fact normal and to be expected since they depend on how charged the battery is and on how much the battery is used previous to the current measurement. This variable-state behaviour makes anomalies much harder to detect than those in public data sets with such behaviour.

In the case of the next anomaly type, the recuperation level is turned from maximum to zero, hence the minimum EDU torque is always non-negative and the HVB SoC experiences a higher drop in SoC. Hence, some deviation should be visible in the EDU torque, left and right axle torques and in the HVB state of charge. This anomaly type accounts for another eight time-series anomalies.

For the following anomaly, the HVB is swapped for a battery simulator, where the HVB voltage behaviour deviates from a real battery. Considering that operation works by requesting a given amount of power, a different voltage behaviour will also result in a change in current, since power P is the product of voltage across the battery V and the current I:

<!-- formula_id: formula_002 | origin: mineru_latex | section: Related Work | page: 4 | bbox: [0.462, 0.814, 0.825, 0.83] | source: mineru25pro | block_id: b0070 -->
```latex
P = V \cdot I \tag {2}
```

Therefore, this type of anomaly will be evident in the HVB and EDU voltage channels, as well as the respective current channels, representing 15 time-series anomalies.

The inverter and EDU share a cooling loop, whose cooling capacity is reduced at the beginning or middle of the measurement for the last type of anomaly. This leads to, for example, higher EDU rotor, EDU stator and inverter temperatures than normal. For three of the sequences the capacity

4

is reduced at the midpoint of the measurement, whereas another five sequences are recorded with reduced cooling capacity from the very beginning.

Clearly this data set consists of several discrete time series. This is in contrast to continuous anomaly detection, which is defined as detecting anomalies in a process that exists for a longer continuous time period without breaks and is the most common type present in public data sets. This includes monitoring applications like in water distribution  \( [15, 1] \)  or server machines  \( [24] \) . Use cases of continuous anomaly detection tend to consist of a singular longer time series which contains anomaly-free and anomalous sub-sequences within it. On the other hand, we define discrete anomaly detection as detecting anomalies in chunks of processes that happen independently of each other, such as automotive test benches, where several tests may occur one after another but are not temporally contiguous and hence provide a multivariate time series for each test. Here the testees are not monitored over a longer period of time, but rather the measured time series are evaluated as they are being recorded. Arguably, analysis of heartbeat rhythms could be considered a discrete anomaly detection problem if applied generically to a number of test subjects, rather than individually, as the training and testing subsets each likely consist of multiple time series from different subjects. Therefore, data sets for discrete anomaly detection consist of several anomaly-free and anomalous time series, where a given anomalous time series may be entirely anomalous or only partly.

Given that some channels (such as torque) are sampled much faster than others (like temperature and SoC), a common sampling rate of 2Hz is chosen. Channels sampled slower than 2Hz are linearly interpolated, which is considered permissible due to the lower amplitude resolution of those channels. Channels sampled faster than 2Hz are passed through a low-pass filter with a cut-off frequency of 1Hz and then resampled to 2Hz, as is consistent with the Whittaker–Nyquist–Shannon theorem  \( [23] \) . Then, the measurements are z-score normalised, i.e. transformed such that the mean for each channel lies at 0 and the standard deviation at 1. Lastly, the measurements are windowed to create a set of fixed-length sub-sequences, or windows. The reasoning behind using windows rather than entire sequences is that most of the dynamic processes in the time-series data are fairly fast and hence only have short-term effect that lasts for a small period of time. Modelling entire variable-length sequences would be possible but much of the model learning capacity would be wasted on internal state mechanisms carrying information for longer periods of time than necessary. This therefore allows for more efficient model training on windows that are only as long as they need to be to represent all present dynamics in the time-series data. To find the effect length of the slowest dynamics an autocorrelation analysis is undertaken for each of the drive cycles and each of the features within them. This is in contrast to approaches taken in literature, which treat window size as a hyperparameter that is tuned. It is unclear how hyperparameter tuning can be undertaken outside of a supervised problem, hence it is assumed that in the real world, this process would not be possible. An autocorrelation analysis yields the correlation between the time series and a range of lagged versions of the time series for a specified number of lags and does not require labels. An example of an autocorrelation plot for an arbitrary measurement and arbitrary channel is shown in Figure 2. As is evident, the autocorrelation decreases with the number of lags, which is consistent with theory as dynamic effects dampen with time. Therefore, the slowest dynamics present that is

5

still significant is at the lag where the autocorrelation intersects the confidence interval. The window size is therefore the slowest dynamic present in any channel in all sequences. For computational efficiency, the window size w is then set as the smallest power of two larger than the largest lag, in this case, w = 256 time steps or 128 seconds. Each window overlaps its preceding and succeeding windows by half a window, i.e. the shift between windows is w/2 = 128 time steps, in order to reduce computational load compared to a shift of one time step.

In an operative environment, it is desirable to find out whether the previously recorded sequence had any problems to analyse before the next measurement is recorded. Also, a model that performs as well as possible with as little data as possible translates to faster deployment. Good performance is indicated by a model that can detect as many anomalies as possible and rarely labels anomaly-free measurements wrongly. To investigate the required training subset size of the model, it is trained with 1h, 8h, 64h, and 512h of dynamic testing time, which corresponds to the first 6, 44, 348, and 2785 measurements, respectively. The results are also represented in Section 5. In each of the above-mentioned cases, the unlabelled training subset  \( D^{train} \)  is further split into a training (80%) and a validation (20%) subsets.

### 2.3 Variational Autoencoders

The variational autoencoder [12][21] is a generative model that structurally resembles an autoencoder, but is theoretically derived from variational Bayesian statistics. As opposed to the regular deterministic autoencoder, the VAE uses the evidence lower bound (ELBO), which is a lower bound approximation of the so-called log evidence \(\log p_{\theta}(\mathbf{X})\), as its objective function. The ELBO, Equation 3, can be expressed as the reconstruction log-likelihood and the negative Kullback-Leibler Divergence \((D_{\mathrm{KL}})\) between the approximate posterior \(\mathsf{q}_{\phi}(\mathbf{Z}|\mathbf{X})\) and the prior \(p_0(\mathbf{Z})\), which is typically assumed to be a Gaussian distribution [10]. The training data does not have to follow a Gaussian distribution since the latent distribution is a nonlinear mapping of the training data.

<!-- formula_id: formula_003 | origin: mineru_latex | section: Related Work | page: 6 | bbox: [0.375, 0.463, 0.826, 0.499] | source: mineru25pro | block_id: b0084 -->
```latex
\begin{array}{l} \mathcal {L} _ {\theta , \phi} (\mathbf {X}) = \mathbb {E} _ {\mathbf {Z} \sim q _ {\phi} (\mathbf {Z} | \mathbf {X})} \left[ \log p _ {\theta} (\mathbf {X} | \mathbf {Z}) \right] \tag {3} \\ - D _ {\mathrm{KL}} \left(q _ {\phi} (\mathbf {Z} | \mathbf {X}) \mid \mid p _ {\theta} (\mathbf {Z})\right) \\ \end{array}
```

where \(\mathbf{Z} \in \mathbb{R}^{w \times d_{\mathbf{Z}}}\) is the sampled latent matrix and \(\mathbf{X} \in \mathbb{R}^{w \times d_{\mathcal{D}}}\) is the input window. \(w\) refers to the window length, whereas \(d_{\mathcal{D}}\) and \(d_{\mathbf{Z}}\) refer to the data set and latent matrix dimensionality, respectively. Gradient-based optimisation minimises an objective function and the goal is the maximisation of the ELBO, hence the final loss function is defined as the negative of Equation 3, shown in Equation 4.

<!-- formula_id: formula_004 | origin: mineru_latex | section: Related Work | page: 6 | bbox: [0.435, 0.566, 0.826, 0.582] | source: mineru25pro | block_id: b0086 -->
```latex
\mathcal {L} _ {\mathrm{VAE}} = - \mathcal {L} _ {\theta , \phi} (\mathbf {X}) \tag {4}
```

Finally, to enable the backpropagation through the otherwise intractable gradient of the ELBO, the reparametrisation trick [12] is applied, shown in Equation 5. This is one of the reasons for the use of a Gaussian distribution as the latent distribution, although any distribution type from the "location-scale" type can be used [12], like a Laplace distribution.

<!-- formula_id: formula_005 | origin: mineru_latex | section: Related Work | page: 6 | bbox: [0.44, 0.655, 0.825, 0.671] | source: mineru25pro | block_id: b0088 -->
```latex
\mathbf {Z} = \boldsymbol {\mu} _ {\mathbf {Z}} + \epsilon \cdot \boldsymbol {\sigma} _ {\mathbf {Z}} \tag {5}
```

where \(\epsilon \sim \mathcal{N}(0,1)\) and \((\mu_{\mathbf{Z}},\log \sigma_{\mathbf{Z}}^{2}) = q_{\phi}(\mathbf{X})\).

### 2.4 Multi-head Attention Mechanism

To simplify the explanation of MA as employed in this work, multi-head self-attention (MS) will be explained instead with the small difference between MA and MS being pointed out at the end.

MS consists of two different concepts: self-attention and its multi-head extension. Self-attention is nothing more than scaled dot-product attention [25] where the key, query and value are the same. The scaled dot-product attention score is the softmax [4] of the product between query matrix \(\mathbf{Q}\) and key matrix \(\mathbf{K}\) which is scaled by \(\sqrt{d_{\mathbf{K}}}\). The product between the attention score and the value matrix \(\mathbf{V}\) yields the context matrix \(\mathbf{C}\), as shown in Equation 6.

<!-- formula_id: formula_006 | origin: mineru_latex | section: Related Work | page: 6 | bbox: [0.408, 0.839, 0.826, 0.88] | source: mineru25pro | block_id: b0093 -->
```latex
\mathbf {C} = \text { Softmax } \left(\frac {\mathbf {Q} \mathbf {K} ^ {T}}{\sqrt {d _ {\mathbf {K}}}}\right) \mathbf {V} \tag {6}
```

Compared to recurrent or convolutional layers, self-attention offers a variety of benefits, such as the reduction of computational complexity, as well as an increased amount of operations that can be

6

parallelised [25]. Also, self-attention inherits an advantage over Bahdanau-style attention [2] from the underlying scaled dot-product attention mechanism: it can run efficiently in matrix multiplication manner [25].

Multi-head self-attention then allows the attention model to attend to different representation subspaces [25], in addition to learning useful projections rather than it being a stateless transformation [6]. This is achieved using weight matrices  \( W_{i}^{Q} \) ,  \( W_{i}^{K} \) ,  \( W_{i}^{V} \) , which contain trainable parameters and are unique for each head i, as shown in Equation 7.

<!-- formula_id: formula_007 | origin: mineru_latex | section: Related Work | page: 7 | bbox: [0.342, 0.206, 0.826, 0.226] | source: mineru25pro | block_id: b0098 -->
```latex
\mathbf {Q} _ {i} = \mathbf {Q} \mathbf {W} _ {i} ^ {Q} \quad \mathbf {K} _ {i} = \mathbf {K} \mathbf {W} _ {i} ^ {K} \quad \mathbf {V} _ {i} = \mathbf {V} \mathbf {W} _ {i} ^ {V} \tag {7}
```

Once the query, key and value matrices are linearly transformed via the weight matrices, the context matrix  \( C_{i} \)  for each head i is computed using Equation 8.

<!-- formula_id: formula_008 | origin: mineru_latex | section: Related Work | page: 7 | bbox: [0.4, 0.267, 0.826, 0.309] | source: mineru25pro | block_id: b0100 -->
```latex
\mathbf {C} _ {i} = \text { Softmax } \left(\frac {\mathbf {Q} _ {i} \mathbf {K} _ {i} ^ {T}}{\sqrt {d _ {\mathbf {K}}}}\right) \mathbf {V} _ {i} \tag {8}
```

Then, for h heads, the different context matrices are concatenated and linearly transformed again via the weight matrix  \( W^{O} \) , resulting in the multi-head context matrix  \( C \in R^{w \times d_{Z}} \) , Equation 9.

<!-- formula_id: formula_009 | origin: mineru_latex | section: Related Work | page: 7 | bbox: [0.427, 0.353, 0.826, 0.372] | source: mineru25pro | block_id: b0102 -->
```latex
\mathbf {C} = \left[ \mathbf {C} _ {1}, \dots , \mathbf {C} _ {h} \right] \mathbf {W} ^ {O} \tag {9}
```

The underlying mechanism of MA is identical to MS, with the only difference being that \(\mathbf{K} = \mathbf{Q} \neq \mathbf{V}\). Essentially, MA finds which time steps correlate most with each other inside a given input window and weighs the time steps in context matrix \(\mathbf{C}\) accordingly. The benefit of this alteration is discussed in Section 4.

TeVAE belongs to the so-called generative model class, which encompasses both variational autoencoders, as well as generative adversarial networks. This section focuses solely on the work on VAE proposed in the context of time-series anomaly detection.

In time-series anomaly detection literature, the only other model that uses the combination of a VAE and an attention mechanism is by [18]. For the purpose of our paper, it is referred to as variational self-attention VAE (VS-VAE). Their approach consists of a BiLSTM encoder and decoder, where, for an input window of length \( w \), the \( t = w \) encoder hidden states of each direction are passed on to the variational self-attention (VS) mechanism [3]. The resulting context vector is then concatenated with the sampled latent vector and then passed on to the decoder. The author claims that applying VS to the VAE model solves the bypass phenomenon, however, no evidence for this claim is provided.

The first published time-series anomaly detection approach based on VAE is LSTM-VAE [17]. One of the contributions is its use of a dynamic prior, i.e.  \( \mathcal{N}(\mu_{p},1) \) , rather than a static one, i.e.  \( \mathcal{N}(0,1) \) . In addition to that, they introduce a state-based threshold estimation method consisting of a support-vector regressor (SVR), which maps the latent distribution parameters  \( (\mu_{\mathbf{z}},\sigma_{\mathbf{z}}) \)  to the resulting anomaly score using the validation data. Hence, the dynamic threshold can be obtained through Equation 10.

<!-- formula_id: formula_010 | origin: mineru_latex | section: Related Work | page: 7 | bbox: [0.414, 0.72, 0.825, 0.735] | source: mineru25pro | block_id: b0108 -->
```latex
\eta_ {t} = \mathrm{SVR} (\mu_ {\mathbf {z}, t}, \sigma_ {\mathbf {z}, t}) + c \tag {10}
```

where c is a pre-defined constant to control sensitivity.

OmniAnomaly [24] attempts to create a temporal connection between latent distributions by applying a linear Gaussian state space model to them. For the purpose of this paper, it is abbreviated to OmniA. Also, it concatenates the last gated recurrent unit (GRU) hidden state with the latent vector sampled in the previous time step. In addition to that, it uses planar normalising flow [20] by applying K transformations to the latent vector in order to approximate a non-Gaussian posterior, as shown in Equation 11.

<!-- formula_id: formula_011 | origin: mineru_latex | section: Related Work | page: 7 | bbox: [0.389, 0.842, 0.826, 0.861] | source: mineru25pro | block_id: b0111 -->
```latex
f ^ {k} \left(\mathbf {z} _ {t} ^ {k - 1}\right) = \mathbf {u} \tanh \left(\mathbf {w} \mathbf {z} _ {t} ^ {k - 1}\right) + \mathbf {b} \tag {11}
```

where u, w and b are trainable parameters.

A simplified VAE architecture [19] based on BiLSTM layers is also proposed. For the purpose of our paper, it is called Wasserstein VAE (W-VAE). Unlike its predecessor [18], it drops the attention

7

mechanism but provides contributions elsewhere. It offers two strategies to detect anomalies based on the VAE outputs. The first involves clustering the space characterised by the mean parameter of the latent distribution into two clusters and labelling the larger one as normal. This strategy has a few weaknesses: it cannot be used in an operative environment as it requires some sort of history of test windows to form the clusters and it assumes that there are always anomalous samples present. The second strategy finds the Wasserstein similarity measure between the latent mean space mapping of the test window in question and the respective mapping \( i \) resulting from a representative data subset, such as the validation subset. Equation 12 shows how the Wasserstein similarity measure is computed

<!-- formula_id: formula_012 | origin: mineru_latex | section: Related Work | page: 8 | bbox: [0.335, 0.208, 0.826, 0.227] | source: mineru25pro | block_id: b0116 -->
```latex
W _ {i} \left(\mathbf {z} _ {\text {test}}, \mathbf {z} _ {i}\right) = \left\| \mu_ {\mathbf {z} _ {\text {test}}} - \mu_ {\mathbf {z} _ {i}} \right\| _ {2} ^ {2} + \left\| \Sigma_ {\mathbf {z} _ {\text {test}}} ^ {1 / 2} - \Sigma_ {\mathbf {z} _ {i}} ^ {1 / 2} \right\| _ {F} ^ {2} \tag {12}
```

where the first term represents the L2-Norm between the mean distribution parameters resulting from the test window and each point of the representative subset. The second term represents the Frobenius norm between the covariance matrix resulting from the test window and each point of the representative subset.

Sliding-window convolutional variational autoencoder (SWCVAE) [5] is the first that applies convolutional neural networks (CNN) to VAEs for multivariate time-series anomaly detection. Peculiarly, 2D CNN layers are used with the justification of being able to process the input both spatially and temporally. We, however, doubt the ability of the model to properly detect anomalies through spatial processing, as a kernel moving along the feature axis can only capture features adjacent to each other. To create a continuous anomaly score from windows they append the last value of each window to the previous one. For the purpose of this paper, this process is referred to as last-type reverse-windowing.

Smoothness-inducing sequential VAE (SISVAE) [14] tries to improve the modelling robustness by the addition of a smoothing term in the loss function which contributes to the reduction of sudden changes in the reconstructed signal, making it less sensitive to noisy time steps.

As part of the variational autoencoder-based selective prediction (VASP) framework  \( [22] \) , a variational autoencoder architecture is proposed to increase the robustness of time-series prediction when faced with anomalies. While the main contribution is attributed to the framework itself, not the VAE, it should be noted that during inference only the mean parameter of the latent distribution is passed to the decoder.

FedAnomaly [29] first extends time-series anomaly detection to a federated learning setting, which may be relevant in use cases involving large amounts of data or strict privacy settings. Other than being the first VAE based on convolutional GRU layers, the contributions of this paper lie exclusively within the federated framework. Results show that as a single entity, it performs better than in a federated scenario.

Other than a feature selection procedure based on the Kolmogorow-Smirnow test, the lightweight LSTM-VAE (LW-VAE) [8] offers no significant contributions besides being relatively parameter-light.

## Method

### 4 Proposed Approach

### 4.1 Overview

To detect anomalies in multivariate time-series data, we propose a variational autoencoder architecture consisting of BiLSTM layers. The model architecture is illustrated in Figure 3. During training, the encoder \( q_{\phi} \), parameterised by \( \phi \), maps input window \( \mathbf{X} \) to a temporal distribution with parameters \( \mu_{\mathbf{Z}} \) and \( \log \sigma_{\mathbf{Z}}^{2} \) in the forward pass, Equation 13.

<!-- formula_id: formula_013 | origin: mineru_latex | section: Method | page: 8 | bbox: [0.424, 0.761, 0.826, 0.779] | source: mineru25pro | block_id: b0126 -->
```latex
\left(\boldsymbol {\mu} _ {\mathbf {Z}}, \log \boldsymbol {\sigma} _ {\mathbf {Z}} ^ {2}\right) = q _ {\phi} (\mathbf {X}) \tag {13}
```

Given the latent distribution parameters  \( \mu_{Z} \)  and  \( \log \sigma_{Z}^{2} \) , the latent matrix is sampled from the resulting distribution, as shown in Equation 14. Note that the covariance is not modelled, hence  \( \sigma_{Z} \)  only contains the diagonal of the covariance matrix.

<!-- formula_id: formula_014 | origin: mineru_latex | section: Method | page: 8 | bbox: [0.421, 0.829, 0.826, 0.846] | source: mineru25pro | block_id: b0128 -->
```latex
\mathbf {Z} \sim \mathcal {N} \left(\boldsymbol {\mu} _ {\mathbf {Z}}, \operatorname{diag} \left(\boldsymbol {\sigma} _ {\mathbf {Z}}\right)\right) \tag {14}
```

Then, the input window \(\mathbf{X}\) is linearly transformed to obtain the query matrices \(\mathbf{Q}_i\) and key matrices \(\mathbf{K}_i\) for each head \(i\). Likewise, the sampled latent matrix \(\mathbf{Z}\) is also transformed to the value matrix \(\mathbf{V}_i\), as shown in Equation 15.

<!-- formula_id: formula_015 | origin: mineru_latex | section: Method | page: 8 | bbox: [0.344, 0.894, 0.826, 0.914] | source: mineru25pro | block_id: b0130 -->
```latex
\mathbf {Q} _ {i} = \mathbf {X} \mathbf {W} _ {i} ^ {Q} \quad \mathbf {K} _ {i} = \mathbf {X} \mathbf {W} _ {i} ^ {K} \quad \mathbf {V} _ {i} = \mathbf {Z} \mathbf {W} _ {i} ^ {V} \tag {15}
```

8

To output the context matrix \(\mathbf{C}_i\) for each head \(i\), the softmax of the through \(\sqrt{d_{\mathbf{K}}}\) normalised query and key product is multiplied with the value matrix, Equation 16.

<!-- formula_id: formula_016 | origin: mineru_latex | section: Method | page: 9 | bbox: [0.4, 0.125, 0.826, 0.165] | source: mineru25pro | block_id: b0133 -->
```latex
\mathbf {C} _ {i} = \text { Softmax } \left(\frac {\mathbf {Q} _ {i} \mathbf {K} _ {i} ^ {T}}{\sqrt {d _ {\mathbf {K}}}}\right) \mathbf {V} _ {i} \tag {16}
```

The final context matrix \(\mathbf{C}\) is the result of the linearly-transformed concatenation of each head-specific context matrix \(\mathbf{C}_i\), as expressed in Equation 17.

<!-- formula_id: formula_017 | origin: mineru_latex | section: Method | page: 9 | bbox: [0.427, 0.203, 0.826, 0.221] | source: mineru25pro | block_id: b0135 -->
```latex
\mathbf {C} = \left[ \mathbf {C} _ {1}, \dots , \mathbf {C} _ {h} \right] \mathbf {W} ^ {O} \tag {17}
```

The decoder  \( p_{\theta} \) , parameterised by  \( \theta \) , then maps the context matrix C to  \( \mu_{X} \)  and  \( \log \sigma_{X}^{2} \) , as shown in Equation 18. These can then be used to parametrise output distribution  \( \mathcal{N}(\mu_{X}, \text{diag}(\sigma_{X})) \) .

<!-- formula_id: formula_018 | origin: mineru_latex | section: Method | page: 9 | bbox: [0.423, 0.259, 0.826, 0.276] | source: mineru25pro | block_id: b0137 -->
```latex
\left(\boldsymbol {\mu} _ {\mathbf {X}}, \log \sigma_ {\mathbf {X}} ^ {2}\right) = p _ {\theta} (\mathbf {C}) \tag {18}
```

Mapping the output to a distribution rather than a deterministic vector allows TeVAE to model uncertainty, which is assumed to be normally distributed.

### 4.2 Inference Mode

Despite the generative capabilities of VAEs, TeVAE does not leverage generation for anomaly detection. Rather than sampling a latent matrix as shown in Equation 14 during inference, sampling is disabled and only \(\mu_{\mathbf{Z}}\) is taken as the input for the multi-head attention mechanism, like in [22]. Equation 14, therefore, is replaced by Equation 19 for the forward pass.

<!-- formula_id: formula_019 | origin: mineru_latex | section: Method | page: 9 | bbox: [0.469, 0.41, 0.826, 0.426] | source: mineru25pro | block_id: b0141 -->
```latex
\mathbf {Z} = \mu_ {\mathbf {Z}} \tag {19}
```

This not only accelerates inference by eliminating the sampling process but is also empirically found to be a good approximation of an averaged latent matrix if it were sampled several times like in [18]. The TeVAE layout during inference is shown in Figure 3, where the traced arrow designates the information flow from the encoder to the MA mechanism.

Anomalies are by definition very rare events, hence an ideal anomaly detector only flags measurements very rarely but accurately. In the powertrain test bench scenario an algorithm is preferred that only flags a sequence it is sure is an anomaly, in other words, an algorithm that outputs very few to no false positives. A high false positive count would lead to a lot of stoppages and therefore lost testing time and additional cost. Of course, the vast majority of measurements evaluated will be anomaly-free hence it is paramount to classify them correctly, naturally leading to a high precision value. Also, there is no automatic evaluation methodology currently running at test benches, other than rudimentary rule-based methods, therefore a solution that plugs into the existing system that automatically detects some or most anomalies undetectable by rules-based approaches can already lead to time and cost savings. To achieve this, the threshold  \( \tau \)  is set as the maximum negative log-likelihood observed when the model is fed with unlabelled validation data.

9

### 4.4 Bypass Phenomenon

VAE, when combined with an attention mechanism, can exhibit a behaviour called the bypass phenomenon [3]. When the bypass phenomenon happens the latent path between encoder and decoder is bypassed and information flow occurs mostly or exclusively through the attention mechanism, as it has deterministic access to the encoder hidden states and therefore avoids regularisation through the  \( D_{KL} \)  term. In an attempt to avoid this, [3] propose variational attention, which, like the VAE, maps the input to a distribution rather than a deterministic vector. Applied to natural language processing, [3] demonstrate that this leads to a diversified generated portfolio of sentences, indicating alleviation of the bypassing phenomenon. As previously mentioned, only [18] applies this insight in the anomaly detection domain, however, they do not present any evidence that it alleviates the bypass phenomenon in their work. TeVAE on the other hand, cannot suffer from the bypass phenomenon in the sense that information flow ignores the latent variational path between encoder and decoder since the MA mechanism requires the value matrix V from the encoder to output the context matrix. Assuming the bypass phenomenon also applies to a case where information flow ignores the attention mechanism, one could claim that TeVAE is not immune. To disprove this claim, the attention mechanism is removed from the model in an ablation study to see if anomaly detection performance remains the same. In this case, V = Z is instead directly input into the decoder. If it drops, it is evidence of the contribution of the attention mechanism to the model performance and hence is not bypassed. The results for this ablation study are shown and discussed in Section 5.

### 4.5 Reverse-window Process

Since the model is trained to reconstruct fixed-length windows, the same applies during inference. However, to decide whether a given measurement sequence  \( S_{n} \in R^{T_{n} \times d_{D}} \)  is anomalous, a continuous reconstruction of the measurement is required. A trivial way to do so would be to window the input measurement  \( S_{n} \)  using a shift of 1, input the windows into the model and chain the last time step from each output window to obtain a continuous sequence [5]. Considering the BiLSTM nature of the encoder and decoder, the first and last time steps of a window can only be computed given the states from one direction, making these values, in theory, less accurate, however. To overcome this, we propose averaging matching time steps in overlapping windows, which is called mean-type reverse-window method. This is done by pre-allocating an array with NaN values, filling it, and taking the mean for each time step while ignoring the NaN values, as depicted in Figure 4. This process and the general anomaly detection process are described in Algorithm 1. The input for this process is the output distribution parameters  \( (\boldsymbol{\mu}_{\mathbf{X}}, \log \sigma_{\mathbf{X}}^{2}) \) , so it essentially averages the distributions and hence can only be applied to the mean and variance parameters. Consider the distributions  \( \mathcal{N}(\mu_{x}, \sigma_{x}^{2}) \)  and  \( \mathcal{N}(\mu_{y}, \sigma_{y}^{2}) \) , both assumed to be independent and normally distributed. The sum of both distributions results in normal distribution  \( \mathcal{N}(\mu_{x+y}, \sigma_{x+y}^{2}) \) , obtained as shown in Equation 20 [13].

<!-- formula_id: formula_020 | origin: mineru_latex | section: Method | page: 10 | bbox: [0.367, 0.845, 0.825, 0.865] | source: mineru25pro | block_id: b0154 -->
```latex
\mu_ {x + y} = \mu_ {x} + \mu_ {y} \quad \sigma_ {x + y} ^ {2} = \sigma_ {x} ^ {2} + \sigma_ {y} ^ {2} \tag {20}
```

Therefore, the standard deviation of the resulting distribution \(\sigma_{x + y}\) is characterised by Equation 21.

<!-- formula_id: formula_021 | origin: mineru_latex | section: Method | page: 10 | bbox: [0.431, 0.891, 0.826, 0.917] | source: mineru25pro | block_id: b0156 -->
```latex
\sigma_ {x + y} = \sqrt {\sigma_ {x} ^ {2} + \sigma_ {y} ^ {2}} \tag {21}
```

10

### Algorithm 1 Anomaly Detection Process

Input: Sequence \(S_{n}\in \mathbb{R}^{T_{n}\times d_{\mathcal{D}}}\), Threshold \(\tau\)

Result: Label \(l_{n}\) for sequence \(\mathcal{S}_n\)

<!-- formula_id: formula_022 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.14, 0.348, 0.152] | source: mineru25pro | block_id: b0161 -->
```latex
n _ {\text { windows }} \leftarrow T _ {n} - w + 1
```

<!-- formula_id: formula_023 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.153, 0.468, 0.168] | source: mineru25pro | block_id: b0162 -->
```latex
\mu_ {\mathbf {X}, \text { temp }} \leftarrow \text { zeros } (n _ {\text { windows }}, T _ {n}, d _ {\mathcal {D}}) + \text { NaN }
```

<!-- formula_id: formula_024 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.169, 0.468, 0.184] | source: mineru25pro | block_id: b0163 -->
```latex
\sigma_ {\mathbf {X}, \text { temp }} ^ {2} \leftarrow \text { zeros } (n _ {\text { windows }}, T _ {n}, d _ {\mathcal {D}}) + \text { NaN }
```

for \(i = 1\to n_{\mathrm{windows}}\) do

<!-- formula_id: formula_025 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.216, 0.199, 0.331, 0.212] | source: mineru25pro | block_id: b0165 -->
```latex
\mathbf {X} \leftarrow \mathcal {S} [ i: w + i ]
```

<!-- formula_id: formula_026 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.217, 0.212, 0.366, 0.227] | source: mineru25pro | block_id: b0166 -->
```latex
(\boldsymbol {\mu} _ {\mathbf {Z}}, \log \boldsymbol {\sigma} _ {\mathbf {Z}} ^ {2}) \leftarrow q _ {\phi} (\mathbf {X})
```

<!-- formula_id: formula_027 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.217, 0.227, 0.35, 0.24] | source: mineru25pro | block_id: b0167 -->
```latex
\mathbf {C} \leftarrow \operatorname{MA} (\mathbf {X}, \mathbf {X}, \boldsymbol {\mu} _ {\mathbf {Z}})
```

<!-- formula_id: formula_028 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.217, 0.24, 0.366, 0.255] | source: mineru25pro | block_id: b0168 -->
```latex
\left(\boldsymbol {\mu} _ {\mathbf {X}}, \log \boldsymbol {\sigma} _ {\mathbf {X}} ^ {2}\right) \leftarrow p _ {\theta} (\mathbf {C})
```

<!-- formula_id: formula_029 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.216, 0.255, 0.388, 0.269] | source: mineru25pro | block_id: b0169 -->
```latex
\boldsymbol {\mu} _ {\mathbf {X}, \text { temp }} [ i, i: i + w ] \leftarrow \boldsymbol {\mu} _ {\mathbf {X}}
```

<!-- formula_id: formula_030 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.216, 0.269, 0.389, 0.286] | source: mineru25pro | block_id: b0170 -->
```latex
\sigma_ {\mathbf {X}, \text { temp }} ^ {2} [ i, i: i + w ] \leftarrow \sigma_ {\mathbf {X}} ^ {2}
```

end for

<!-- formula_id: formula_031 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.299, 0.372, 0.314] | source: mineru25pro | block_id: b0172 -->
```latex
\boldsymbol {\mu} _ {\mathcal {S}} \leftarrow \text { nanmean } (\boldsymbol {\mu} _ {\mathbf {X}, \text { temp }}, 0)
```

<!-- formula_id: formula_032 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.314, 0.372, 0.331] | source: mineru25pro | block_id: b0173 -->
```latex
\sigma_ {S} ^ {2} \leftarrow \text { nanmean } (\sigma_ {\mathbf {X}, \text { temp }} ^ {2}, 0)
```

<!-- formula_id: formula_033 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.332, 0.366, 0.346] | source: mineru25pro | block_id: b0174 -->
```latex
\mathbf {s} _ {n} \leftarrow - \log p \left(\boldsymbol {\mu} _ {\mathcal {S}}, \boldsymbol {\sigma} _ {\mathcal {S}} \mid \mathcal {S} _ {n}\right)
```

<!-- formula_id: formula_034 | origin: mineru_latex | section: Method | page: 11 | bbox: [0.191, 0.347, 0.319, 0.359] | source: mineru25pro | block_id: b0175 -->
```latex
l _ {n} \leftarrow \max \left(\mathbf {s} _ {n}\right) > \tau
```

▷ Find the total number of windows in sequence

\(\triangleright\) Pre-allocate NaN array to assign all windows to

▷ Pre-allocate NaN array to assign all windows to

▷ Iterate through total number of windows

▷ Assign current window

▷ Input window into encoder

▷ Input window and mean parameter into MA

▷ Input context matrix into decoder

▷ Assign mean parameter to pre-allocated array

▷ Assign variance parameter to pre-allocated array

▷ Take nanmean along axis 0

▷ Take nanmean along axis 0

\(\triangleright\) Obtain continuous negative log-likelihood (anomaly score)

▷ Compare maximum value in anomaly score with threshold

Therefore, to take the mean of the distributions the log variance  \( \log \sigma_{X}^{2} \)  is converted to the variance  \( \sigma_{X}^{2} \) , averaged, and then converted to the standard deviation  \( \sigma_{X} \) .

With a continuous mean  \( \mu_{S} \)  and standard deviation  \( \sigma_{S} \) , the continuous negative log-likelihood, i.e. the anomaly score s, is computed for the respective measurement. A comparison between the mean, last and first reverse-window process is provided in Section 5.

The theoretical delay  \( \delta_{theory} \)  associated with each of the reverse-window processes can be discussed ahead of Section 5, however.  \( \delta_{theory} \)  is defined as the intrinsic delay introduced by each reverse-windowing method. To illustrate the theoretical delay  \( \delta_{theory} \), it is plotted against time t to demonstrate the delay for each of the reverse-window processes, shown in Figure 5. For the last-type reverse-window method during 0 < t < w, no time steps can be evaluated until a full window can be formed, streamed and evaluated, introducing a theoretical delay  \( \delta_{theory} = w \). This property is intrinsic to approaches based on fixed-length windows rather than variable-length sequences. At time step t = w, however, all time steps 0 < t < w are evaluated and output at the same time. For w < t < T, however, the last time step of each window corresponds the current real-world time step, i.e.  \( \delta_{theory} = 0 \)  for w < t < T. As mentioned above, the lack of evaluation until t = w is natural to any window-based approach and hence the first-type and mean-type reverse-window methods show the same behaviour. In contrast to last-type reverse-windowing, however, these methods only output the first value of each window i.e. evaluation is  \( \delta_{theory} = w \)  time steps behind for 0 < t < T - w. At t = T, though, the time steps T - w < t < T are all output at the same time, meaning that  \( \delta_{theory} = 0 \)  and no extra time is needed for evaluation after streaming ends. It should be noted, however, that in online time-series anomaly detection the last-type reverse-window method is in theory faster than the other two types. Consider a sub-sequence anomaly starting at time step  \( w + 2 \), designated by the red line in Figure 5. Apart from the time required for inference, the last-type reverse-window method can detect the anomaly without a theoretical delay  \( \delta_{theory} \), during w < t < T, whereas the other two methods can only detect the anomaly  \( \delta_{theory} = w \)  time steps later. For 0 < t < T - w, a theoretical delay of  \( \delta_{theory} = w \)  time steps is, therefore, the absolute best that first-type and mean-type reverse-windowing can achieve, however, while the best delay the first-type can achieve is  \( \delta_{theory} = 0 \), it will be higher in reality, perhaps higher than w time steps.

### 4.6 Root-cause Analysis

Once a measurement is predicted to be anomalous it is of great benefit if context is provided, like what channel had the biggest impact on the prediction. Depending on what subsystem within the system the anomaly originates, it may affect a different number of channels, in some cases even all. Some attempts to provide root-cause functionality are made in literature.

11

The first known to the authors is proposed by [28]. The approach does not use time series but instead, the resulting correlation matrices and the anomaly score is given as the difference between the input and reconstructed correlation matrices. Hence, as a mean of providing root-cause information they rank each channel by the number of high anomaly scores for every other channel. Root-cause identification is then quantified by the recall for the top k channels, in this case three, although little information on how exactly this is calculated is provided. Another issue with this metric is that is not parameter-free, since k needs to be set manually. Furthermore, the method used is specific to approaches using the same type of correlation matrices, which is rare in literature.

Approaches using the negative log-likelihood as the anomaly score obtain it from a multivariate output distribution with a diagonal covariance. While the resulting anomaly score is a univariate time series, it is referred to as multivariate anomaly score for now due to its origin in a multivariate output distribution. [24] propose decomposing the anomaly score into anomaly scores for each channel, by splitting the multivariate output distribution into  \( d_{D} \)  univariate output distributions. The resulting anomaly scores for each of the  \( d_{D} \)  channels are referred to as univariate anomaly scores due to their origin in  \( d_{D} \)  univariate output distributions. To find the channel that contributed most to a detection, the highest univariate anomaly score is assumed to be the root cause.

In this work, the methodology proposed by  \( [24] \)  is used to find the channels that contribute most to a detection. To this end, the method is slightly adapted, given the online premise of the use case. Rather than considering the univariate anomaly scores as time series for root cause analysis, the first time step of the multivariate anomaly score above the threshold is used. Then, for that time step, the highest univariate anomaly score is assumed as the contributing channel.

## Experiments

### 5 Results

### 5.1 Setup

The encoder and decoder both consist of two BiLSTM layers, with the outer ones having 512 hidden- and cell-state sizes and the inner ones 256. All other parameters are left as the default in the TensorFlow API.

During training only, input windows are corrupted using Gaussian noise using 0.01 standard deviation to increase robustness [26].

Key factors that are investigated in Section 5 are given a default value which applies to all experiments unless otherwise specified. These factors are training and validation subset size, which is set to 512h, reverse-window method, where the mean-type is used, the latent dimension size, which is set to \( d_{\mathbf{Z}} = 64 \), the MA mechanism, which is set up as proposed in [25] with a head count of \( h = 8 \) and a key dimension size \( d_{\mathbf{K}} = \lfloor d_{\mathcal{D}} / h \rfloor = 1 \).

The optimiser used is the AMSGrad optimiser with the default parameters in the TensorFlow API.

Cyclical  \( D_{KL} \)  annealing is applied to the training of TeVAE, to avoid the  \( D_{KL} \)  vanishing problem [9]. The  \( D_{KL} \)  vanishing problem occurs when regularisation is too strong at the beginning of training, i.e. the Kullback-Leibler divergence term has a larger magnitude in relation to the reconstruction term.

12

Cyclical  \( D_{KL} \)  annealing allows the model to weigh the Kullback-Leibler divergence lower than the reconstruction term in a cyclical manner through a weight  \( \beta \) . This callback is configured with a grace period of 25 epochs, where  \( \beta \)  is linearly increased from 0 to  \( 10^{-8} \) . After the grace period,  \( \beta \)  is set to  \( 10^{-8} \)  and is gradually increased linearly to  \( 10^{-2} \)  throughout the following 25 epochs, representing one loss cycle. This loss cycle is repeated until the training stops.

All priors in this work are set as standard Gaussian distributions, i.e.  \( p = \mathcal{N}(0, 1) \) .

To prevent overfitting, early stopping is implemented. It works by monitoring the negative log-likelihood component of the validation loss during training and stopping if it does not improve for 250 epochs. Logically, the model weights at the lowest validation negative log-likelihood are saved.

Given the stochastic nature of the VAEs, the chosen seed can impact the anomaly detection performance as it can lead to a different local minimum during training, hence all tests are done with three different seeds and are shown in form of the standard deviation after every performance metric.

Training is done on a workstation configured with an NVIDIA RTX A6000 GPU. The library used for model training is TensorFlow 2.10.1 on Python 3.10 on Windows 10 Enterprise LTSC version 21H2.

### 5.2 Online Evaluation Metrics

The results provided are given in the form of the calibrated and uncalibrated anomaly detection performance, i.e. with and without consideration of threshold  \( \tau \) , respectively. Recall that the threshold used is the maximum negative log-likelihood obtained from the validation set. The basis for all metrics are the number of true positives  \( N_{tp} \) , number of false negatives  \( N_{fn} \)  and number of false positives  \( N_{fp} \) .

As discussed in Section 1, a testing subset in discrete time-series anomaly detection problem has three types of time series: entirely normal, time-series anomalies and sub-sequence anomalies. Since anomalies are considered rare events, the number of anomaly-free time series  \( N_{af} \)  within  \( D^{test} \)  is much larger than the number of time-series anomalies  \( N_{ts} \)  and sub-sequence anomalies  \( N_{ss} \) , such that  \( N_{af} >> N_{ts} + N_{ss} = N_{a} \)  and  \( N = N_{af} + N_{ts} + N_{ss} \) . In the case of anomaly-free time series and time-series anomalies, traditional labels can easily be applied. An anomaly-free time series can be labelled as true negative or false positive and a time-series anomaly can be labelled as true positive or false negative. For partially anomalous time series, i.e. where the anomalous behaviour occupies a contiguous subset of time steps within the time series, it can be labelled as a true positive or a false negative, but also as a false positive, which occurs when an algorithm flags a time step early. Formally, this is the case when the first flagged time step is far enough ahead of the first ground-truth time step that the model cannot have had access to it. As is evident, the proposed metrics can only be applied to discrete time-series data sets where anomalous time series have at most one contiguous ground-truth anomalous sub-sequence of any length. Also, ensuring each time series contains at most one contiguous anomaly avoids ambiguity on how multiple sub-sequence anomalies within a time series should be detected and counted [27]. In addition to that, there can also be at most one contiguous ground-truth anomaly-free sub-sequence of any length within a sub-sequence anomalous time series, since systems that can dynamically return to anomaly-free behaviour (especially in a short amount of time) reap less benefit from automated anomaly detection than those which require human attention. Given that a predicted anomaly likely requests human attention and potentially a stoppage of the system, the adaptation of the metrics proposed above only takes into account the first predicted anomalous time step. For cases where the process may continue, there can be multiple contiguous predicted anomalous sub-sequences, hence the metrics cannot be applied.

Calibrated metrics are the precision, recall and  \( F_{1} \)  score. Precision P represents the ratio between the number of correctly identified anomalies (true positives) and the number of all positives (true and false), shown in Equation 22, recall R represents the ratio between the number of true positives and the number of all anomalies, shown in Equation 22, and  \( F_{1} \)  score represents the harmonic mean of the precision and recall, shown in Equation 22.

<!-- formula_id: formula_035 | origin: mineru_latex | section: Experiments | page: 13 | bbox: [0.304, 0.827, 0.826, 0.861] | source: mineru25pro | block_id: b0218 -->
```latex
P = \frac {N _ {\mathrm{tp}}}{N _ {\mathrm{tp}} + N _ {\mathrm{fp}}} \quad R = \frac {N _ {\mathrm{tp}}}{N _ {\mathrm{tp}} + N _ {\mathrm{fn}}} \quad F _ {1} = 2 \cdot \frac {P \cdot R}{P + R} \tag {22}
```

The theoretical maximum \( F_{1} \) score, \( F_{1,\mathrm{best}} \), is also provided to aid discussion. This represents the best possible score achievable by the approach if the ideal threshold were known, i.e. the point on the precision-recall curve that comes closest to the \( P = R = 1 \) point, though, in reality, this value is

13

not observable and hence cannot be obtained in an unsupervised manner. The precision and recall corresponding to the  \( F_{1,best} \)  score are also provided.

The uncalibrated anomaly detection performance, i.e. the performance for a range of thresholds is represented by the area under the continuous precision-recall curve  \( A_{PR}^{cont} \) , Equation 23.

<!-- formula_id: formula_036 | origin: mineru_latex | section: Experiments | page: 14 | bbox: [0.438, 0.16, 0.826, 0.193] | source: mineru25pro | block_id: b0223 -->
```latex
A _ {\mathrm{PR}} ^ {\text { cont }} = \int_ {0} ^ {1} P d R \tag {23}
```

As the integral cannot be computed for the continuous function, the area under the discrete precision-recall curve  \( A_{PR}^{disc} \)  is used which is done using the trapezoidal rule, Equation 24.

<!-- formula_id: formula_037 | origin: mineru_latex | section: Experiments | page: 14 | bbox: [0.398, 0.227, 0.826, 0.268] | source: mineru25pro | block_id: b0225 -->
```latex
A _ {\mathrm{PR}} ^ {\mathrm{disc}} = \sum_ {k = 1} ^ {K - 1} \frac {P _ {k - 1} + P _ {k}}{2} \Delta R _ {k} \tag {24}
```

where \( K \) is the number of discrete points along the precision-recall curve, \( k \) the index of discrete points along the precision-recall curve and \( \Delta R_{k} \) the sub-interval length between indices \( k \) and \( k - 1 \).

While the above metrics quantify binary anomaly detection performance, they do not provide information on the delay of detections, which plays a crucial role in online time-series anomaly detection. Therefore, we propose an additional metric, the detection delay  \( \delta \) , which represents the absolute delay between the first ground-truth anomalous time step  \( t = t_{gt} \)  and the first predicted anomalous time step  \( t = t_{p} \) . The detection delay  \( \delta \)  is only calculated for anomalous time series since in anomaly-free time series there is no first ground-truth time step  \( t = t_{gt} \) , therefore it is calculated as shown in Equation 25.

<!-- formula_id: formula_038 | origin: mineru_latex | section: Experiments | page: 14 | bbox: [0.452, 0.402, 0.825, 0.418] | source: mineru25pro | block_id: b0228 -->
```latex
\delta = \left| t _ {\mathrm{p}} - t _ {\mathrm{gt}} \right| \tag {25}
```

where, in case of a false negative,  \( t_{p} \)  is equal to the last time step of the anomalous time series. This formula not only reflects the detection delay for true positives but also punishes false negatives by applying the maximum delay possible, i.e.  \( \delta = T \) , as well as false positives by applying the "negative" delay between the first early predicted time step  \( t = t_{p} \)  and the first ground-truth time step  \( t = t_{gt} \) . For each anomalous test time series the detection delay is calculated and subsequently averaged to yield the average detection delay  \( \bar{\delta} \) , shown in equation 26.

<!-- formula_id: formula_039 | origin: mineru_latex | section: Experiments | page: 14 | bbox: [0.415, 0.506, 0.826, 0.547] | source: mineru25pro | block_id: b0230 -->
```latex
\bar {\delta} = \frac {1}{N _ {\mathrm{ts}} + N _ {\mathrm{ss}}} \sum_ {i = 1} ^ {N _ {\mathrm{ts}} + N _ {\mathrm{ss}}} \delta_ {i} \tag {26}
```

In order to evaluate TeVAE's root-cause analysis performance we propose a corresponding metric. Recall that according to the method of counting labels, anomaly-free sequences can be labelled as true negatives or false positives and time-series anomalies can be labelled as true positives or false negatives. Sub-sequence anomalies can be labelled as true positives, false negatives or false positives, where the latter occurs when an anomaly is detected before it actually occurs. To quantify whether the most relevant channel has been flagged in the case of a predicted anomalous sequence, the root-cause true positive count \( N_{\mathrm{tp}_{\mathrm{rc}}} \) and root-cause false positive count \( N_{\mathrm{fp}_{\mathrm{rc}}} \) are introduced. Clearly, the root-cause channel can only be obtained for predicted anomalous sequences, hence why there is no root-cause true negative count \( \mathrm{tn}_{\mathrm{rc}} \) or root-cause false negative count \( N_{\mathrm{fp}_{\mathrm{rc}}} \). The root-cause true positive count \( N_{\mathrm{tp}_{\mathrm{rc}}} \) represents the number of sequences labelled as true positives and the predicted root-cause channel is a subset of the list of ground-truth root-cause channels for a given anomaly type. Likewise, root-cause false positive count \( N_{\mathrm{fp}_{\mathrm{rc}}} \) represents the sum of three cases. The first case is an anomaly-free sequence labelled as a false positive, for which there are no ground-truth root-cause channels. The second case is a ground-truth time-series or sub-sequence anomaly that is labelled as a true positive, but the predicted root-cause channel is not a subset of the list of ground-truth root-cause channels for the relevant anomaly type. The third case is a ground-truth sub-sequence anomaly that is labelled as a false positive, due to a premature detection, for which there are no ground-truth root-cause channels. To aid the understanding of this concept, a diagram depicting what types of sequences can be labelled as what is shown in Table 2. As is evident, \( N_{\mathrm{tp}} + N_{\mathrm{fp}} = N_{\mathrm{tp}_{\mathrm{rc}}} + N_{\mathrm{fp}_{\mathrm{rc}}} \). To summarise the \( N_{\mathrm{tp}_{\mathrm{rc}}} \) and \( N_{\mathrm{fp}_{\mathrm{rc}}} \) figures, we propose a new metric called the root-cause precision \( P_{\mathrm{rc}} \), shown in Equation 27.

<!-- formula_id: formula_040 | origin: mineru_latex | section: Experiments | page: 14 | bbox: [0.44, 0.85, 0.826, 0.884] | source: mineru25pro | block_id: b0232 -->
```latex
P _ {\mathrm{rc}} = \frac {N _ {\mathrm{tp} _ {\mathrm{rc}}}}{N _ {\mathrm{tp}} + N _ {\mathrm{fp}}} \tag {27}
```

\( P_{rc} \) denotes the number of correctly identified root-cause channels relative to the number of total detections, true or false.

14

Table 2: Table depicting which sequence types can be classified with what detection labels and root-cause labels.

<table><tr><td colspan="2">Sequence Type</td><td colspan="2">Detection Label</td><td>Root-cause Label</td></tr><tr><td rowspan="2">Normal sequence</td><td>\( \rightarrow \)</td><td>true negative</td><td>\( \rightarrow \)</td><td>-</td></tr><tr><td>\( \downarrow \)</td><td>false positive</td><td>\( \rightarrow \)</td><td>false positive</td></tr><tr><td rowspan="3">Time-series anomaly</td><td>\( \rightarrow \)</td><td>false negative</td><td>\( \rightarrow \)</td><td>-</td></tr><tr><td>\( \downarrow \)</td><td>true positive</td><td>\( \rightarrow \)</td><td>true positive</td></tr><tr><td></td><td></td><td>\( \downarrow \)</td><td>false positive</td></tr><tr><td rowspan="4">Sub-sequence anomaly</td><td>\( \rightarrow \)</td><td>false negative</td><td>\( \rightarrow \)</td><td>-</td></tr><tr><td>\( \downarrow \)</td><td>false positive</td><td>\( \rightarrow \)</td><td>false positive</td></tr><tr><td>\( \downarrow \)</td><td>true positive</td><td>\( \rightarrow \)</td><td>true positive</td></tr><tr><td></td><td></td><td>\( \downarrow \)</td><td>false positive</td></tr></table>

### 5.3 Ablation Study

TeVAE is tested without the MA mechanism and with a direct connection from the encoder to the decoder to observe whether the absence of the MA impacts results. The anomaly detection performance of TeVAE and its counterpart without MA, henceforth referred to as NoMA model, are shown in Table 3.

Table 3:  \( F_{1} \)  score, precision P, recall R, average detection delay  \( \bar{\delta} \)  and root-cause precision  \( P_{rc} \)  using the unsupervised threshold (top half) and theoretical best threshold (bottom half), as well as the area under the precision-recall curve  \( A_{PR} \)  for NoMA and TeVAE. The best values for each metric are given in bold. The standard deviation for the different seeds are also provided.

<table><tr><td>Model</td><td>\( F_1 \)</td><td>P</td><td>R</td><td>\( A_{\text{PR}} \)</td><td colspan="2">\( \bar{\delta} \) [s]</td><td>\( P_{\text{rc}} \)</td></tr><tr><td>NoMA</td><td>0.59 ± 0.01</td><td>\( \mathbf{0.98} \pm 0.02 \)</td><td>0.42 ± 0.01</td><td>0.56 ± 0.01</td><td colspan="2">577.0 ± 5.8</td><td>\( \mathbf{0.85} \pm 0.04 \)</td></tr><tr><td>TeVAE</td><td>\( \mathbf{0.70} \pm 0.03 \)</td><td>0.92 ± 0.08</td><td>\( \mathbf{0.57} \pm 0.04 \)</td><td>\( \mathbf{0.66} \pm 0.04 \)</td><td colspan="2">\( \mathbf{418.1} \pm 17.3 \)</td><td>0.63 ± 0.18</td></tr><tr><td>NoMA</td><td>0.59 ± 0.01</td><td>\( \mathbf{1.00} \pm 0.00 \)</td><td>0.42 ± 0.01</td><td>0.56 ± 0.01</td><td colspan="2">577.2 ± 5.7</td><td>\( \mathbf{0.86} \pm 0.03 \)</td></tr><tr><td>TeVAE</td><td>\( \mathbf{0.72} \pm 0.03 \)</td><td>0.97 ± 0.04</td><td>\( \mathbf{0.58} \pm 0.06 \)</td><td>\( \mathbf{0.66} \pm 0.04 \)</td><td colspan="2">\( \mathbf{412.9} \pm 25.0 \)</td><td>0.67 ± 0.15</td></tr></table>

While the precision value of the NoMA model is slightly higher than the TeVAE, the recall value on the other hand is much lower. Overall, TeVAE has a significantly higher \( F_{1} \) score, as well as a higher theoretical maximum \( F_{1} \) score and higher uncalibrated anomaly detection performance, denoted by the \( A_{\mathrm{PR}} \) figure. Furthermore, TeVAE features a much lower average detection delay which is especially relevant for online time-series anomaly detection. In contrast to that, NoMA offers marginally higher root-cause precision. The results hence point towards an improvement brought about by the addition of the MA mechanism and therefore the bypass phenomenon can be ruled out.

### 5.4 Data Set Size Requirements

To evaluate how much data is required to train TeVAE to a point of adequate anomaly detection performance, it has been trained with 1h, 8h, 64h, and 512h of dynamic testing time. The results for this experiment are presented in Table 4.

On the one hand, as the training and validation subset increases in size, the precision value improves but on the other hand recall value decreases as the subset grows, though at a smaller scale compared to the increase in precision. This can be attributed to the fact that smaller subset sizes lead to a small validation set and therefore less data to obtain a threshold from. With a limited amount of data the validation set distribution is very different to the true data distribution, leading to a threshold that is very small and hence marks most anomalies correctly but also leads to a lot of false positives. Despite the decreasing recall, the \( F_{1} \) score increases with a growing training and validation subset size. It can also be observed that both the \( F_{1,\mathrm{best}} \) and the \( A_{\mathrm{PR}} \) reach a point of diminishing returns after 8h of dynamic testing. Given that neither metric relies on the unsupervised threshold, it indicates that it plays a large role in the \( F_{1} \) score. It further implies that the model quality remains largely the same from 8h onwards. Also, the \( F_{1} \) score seems to approach the \( F_{1,\mathrm{best}} \) score as the subset grows, also backing the fact that with a small subset size, a good threshold cannot easily be obtained.

15

Table 4:  \( F_{1} \)  score, precision P, recall R, average detection delay  \( \bar{\delta} \)  and root-cause precision  \( P_{rc} \)  using the unsupervised threshold (top half) and theoretical best threshold (bottom half), as well as the area under the precision-recall curve  \( A_{PR} \)  for the different training and validation subset sizes. The best values for each metric are given in bold. The standard deviation for the different seeds are also provided.

<table><tr><td>Size</td><td>\( F_1 \)</td><td>P</td><td>R</td><td>\( A_{\text{PR}} \)</td><td>\( \bar{\delta} \) [s]</td><td>\( P_{\text{rc}} \)</td></tr><tr><td>1h</td><td>0.20 ± 0.02</td><td>0.11 ± 0.01</td><td>0.83 ± 0.06</td><td>0.57 ± 0.02</td><td>321.1 ± 30.4</td><td>0.07 ± 0.01</td></tr><tr><td>8h</td><td>0.37 ± 0.14</td><td>0.26 ± 0.13</td><td>0.80 ± 0.06</td><td>0.69 ± 0.04</td><td>298.7 ± 29.2</td><td>0.16 ± 0.08</td></tr><tr><td>64h</td><td>0.69 ± 0.06</td><td>0.76 ± 0.15</td><td>0.66 ± 0.03</td><td>0.71 ± 0.01</td><td>371.3 ± 38.4</td><td>0.61 ± 0.15</td></tr><tr><td>512h</td><td>0.70 ± 0.03</td><td>0.92 ± 0.08</td><td>0.57 ± 0.04</td><td>0.66 ± 0.04</td><td>418.1 ± 17.3</td><td>0.63 ± 0.18</td></tr><tr><td>1h</td><td>0.61 ± 0.05</td><td>0.72 ± 0.04</td><td>0.55 ± 0.09</td><td>0.57 ± 0.02</td><td>459.9 ± 42.5</td><td>0.54 ± 0.07</td></tr><tr><td>8h</td><td>0.74 ± 0.04</td><td>0.94 ± 0.02</td><td>0.61 ± 0.06</td><td>0.69 ± 0.04</td><td>460.9 ± 35.1</td><td>0.68 ± 0.04</td></tr><tr><td>64h</td><td>0.77 ± 0.02</td><td>1.00 ± 0.00</td><td>0.62 ± 0.02</td><td>0.71 ± 0.01</td><td>418.8 ± 4.5</td><td>0.81 ± 0.05</td></tr><tr><td>512h</td><td>0.72 ± 0.03</td><td>0.97 ± 0.04</td><td>0.58 ± 0.06</td><td>0.66 ± 0.04</td><td>412.9 ± 25.0</td><td>0.67 ± 0.15</td></tr></table>

Therefore, for application on the test benches in automotive powertrain development, the largest subset size is desirable due to the higher precision value and a closer-to-ideal threshold value. When using the unsupervised threshold, the average detection delay increases with a larger training and validation subset and appears to have a relationship with the recall figure. This is due to the fact that  \( N_{tp} \)  increases and  \( N_{fn} \)  decreases accordingly, which means that the maximum delay  \( \delta = T \)  is applied more often, leading to the larger average detection delay. Lastly, the root-cause precision  \( P_{rc} \)  also appears to have a positive correlation with the precision figure. This is to be expected since a root-cause true positive can only occur when an anomaly is correctly identified. However, there is still clearly some room for improvement as  \( P_{rc} \)  is always lower than or equal to P, where in case of a perfect root-cause analysis  \( P_{rc} = P \) .

### 5.5 Reverse-window Process

To investigate the effect of the mean-type reverse-window method, it is compared with the first-type and last-type methods where the first and last values of each window are carried over, respectively, the results for which are shown in Table 5.

Table 5:  \( F_{1} \)  score, precision P, recall R, average detection delay  \( \bar{\delta} \)  and root-cause precision  \( P_{rc} \)  using the unsupervised threshold (top half) and theoretical best threshold (bottom half), as well as the area under the precision-recall curve  \( A_{PR} \)  for the different reverse-window types. The best values for each metric are given in bold. The standard deviation for the different seeds are also provided.

<table><tr><td>Type</td><td>\( F_1 \)</td><td>\( P \)</td><td>\( R \)</td><td>\( A_{\text{PR}} \)</td><td colspan="2">\( \bar{\delta} \) [s]</td><td>\( P_{\text{rc}} \)</td></tr><tr><td>first</td><td>\( 0.71 \pm 0.04 \)</td><td>\( \mathbf{0.99} \pm 0.02 \)</td><td>\( 0.55 \pm 0.05 \)</td><td>\( \mathbf{0.68} \pm 0.06 \)</td><td colspan="2">\( 517.1 \pm 6.1 \)</td><td>\( \mathbf{0.77} \pm 0.07 \)</td></tr><tr><td>last</td><td>\( \mathbf{0.72} \pm 0.01 \)</td><td>\( 0.94 \pm 0.02 \)</td><td>\( \mathbf{0.58} \pm 0.01 \)</td><td>\( 0.64 \pm 0.01 \)</td><td colspan="2">\( \mathbf{411.9} \pm 15.7 \)</td><td>\( 0.64 \pm 0.06 \)</td></tr><tr><td>mean</td><td>\( 0.70 \pm 0.03 \)</td><td>\( 0.92 \pm 0.08 \)</td><td>\( 0.57 \pm 0.04 \)</td><td>\( 0.66 \pm 0.04 \)</td><td colspan="2">\( 418.1 \pm 17.3 \)</td><td>\( 0.63 \pm 0.18 \)</td></tr><tr><td>first</td><td>\( \mathbf{0.75} \pm 0.06 \)</td><td>\( 0.95 \pm 0.04 \)</td><td>\( \mathbf{0.62} \pm 0.10 \)</td><td>\( \mathbf{0.68} \pm 0.06 \)</td><td colspan="2">\( 464.8 \pm 38.7 \)</td><td>\( \mathbf{0.70} \pm 0.10 \)</td></tr><tr><td>last</td><td>\( 0.72 \pm 0.01 \)</td><td>\( 0.94 \pm 0.02 \)</td><td>\( 0.58 \pm 0.01 \)</td><td>\( 0.64 \pm 0.01 \)</td><td colspan="2">\( \mathbf{411.9} \pm 15.7 \)</td><td>\( 0.64 \pm 0.06 \)</td></tr><tr><td>mean</td><td>\( 0.72 \pm 0.03 \)</td><td>\( \mathbf{0.97} \pm 0.04 \)</td><td>\( 0.58 \pm 0.06 \)</td><td>\( 0.66 \pm 0.04 \)</td><td colspan="2">\( 412.9 \pm 25.0 \)</td><td>\( 0.67 \pm 0.15 \)</td></tr></table>

As is evident, the calibrated and uncalibrated detection performance is very similar throughout the different methods. In terms of average detection delay, it is evident, however, that the first-type method is significantly slower than the other two methods. Interestingly, despite the capacity to detect anomalies with much lower theoretical delay for most of the time steps in the sequence, the last-type actually yielded very similar average detection delays to the mean-type. The root-cause precision is very similar for last and mean-type reverse-windowing, with first-type scoring the highest. Furthermore, the mean-type reverse-window method results in a higher computational load, though negligible.

16

### 5.6 Hyperparameter Optimisation

As part of the hyperparameter optimisation of TeVAE, a list of key dimension sizes  \( d_{K} \)  in combination with a list of latent dimension sizes  \( d_{Z} \)  is tested. Note that, given the unsupervised nature of the problem, this optimisation is not possible in a productive environment. The results depict theoretical and in reality unobservable anomaly detection performance. Alternatively, optimising for another metric like validation loss would be possible, however, there is no guarantee that said metric leads to good anomaly detection performance. Despite the larger learning capacity associated with a higher  \( d_{K} \) , the attention head concatenation is always transformed to an output matrix of dimensionality  \( d_{O} = d_{Z} \) . For the two variables, values of 1, 8, 64, and 512 are tested; the results are shown in Tables 6 and 7.

Table 6:  \( F_{1} \)  score, precision P, recall R, average detection delay  \( \bar{\delta} \)  and root-cause precision  \( P_{rc} \)  using the unsupervised threshold (top half) and theoretical best threshold (bottom half), as well as the area under the precision-recall curve  \( A_{PR} \)  for various  \( d_{K} \)  values.

<table><tr><td>\( d_{\mathbf{K}} \)</td><td>\( d_{\mathbf{Z}} \)</td><td>\( F_1 \)</td><td>\( P \)</td><td>\( R \)</td><td>\( A_{\text{PR}} \)</td><td>\( \bar{\delta} \) [s]</td><td>\( P_{\text{rc}} \)</td></tr><tr><td>1</td><td>64</td><td>\( \mathbf{0.70} \pm 0.03 \)</td><td>\( 0.92 \pm 0.08 \)</td><td>\( \mathbf{0.57} \pm 0.04 \)</td><td>\( \mathbf{0.66} \pm 0.04 \)</td><td>\( \mathbf{418.1} \pm 17.3 \)</td><td>\( 0.63 \pm 0.18 \)</td></tr><tr><td>8</td><td>64</td><td>\( 0.69 \pm 0.01 \)</td><td>\( 0.98 \pm 0.03 \)</td><td>\( 0.54 \pm 0.02 \)</td><td>\( 0.65 \pm 0.02 \)</td><td>\( 446.7 \pm 36.9 \)</td><td>\( 0.66 \pm 0.06 \)</td></tr><tr><td>64</td><td>64</td><td>\( 0.69 \pm 0.03 \)</td><td>\( \mathbf{0.99} \pm 0.02 \)</td><td>\( 0.53 \pm 0.03 \)</td><td>\( 0.64 \pm 0.02 \)</td><td>\( 457.9 \pm 18.3 \)</td><td>\( 0.71 \pm 0.01 \)</td></tr><tr><td>512</td><td>64</td><td>\( 0.66 \pm 0.06 \)</td><td>\( \mathbf{0.99} \pm 0.02 \)</td><td>\( 0.50 \pm 0.07 \)</td><td>\( 0.63 \pm 0.03 \)</td><td>\( 498.9 \pm 41.6 \)</td><td>\( \mathbf{0.78} \pm 0.01 \)</td></tr><tr><td>1</td><td>64</td><td>\( \mathbf{0.72} \pm 0.03 \)</td><td>\( 0.97 \pm 0.04 \)</td><td>\( \mathbf{0.58} \pm 0.06 \)</td><td>\( \mathbf{0.66} \pm 0.04 \)</td><td>\( 412.9 \pm 25.0 \)</td><td>\( 0.67 \pm 0.15 \)</td></tr><tr><td>8</td><td>64</td><td>\( 0.71 \pm 0.01 \)</td><td>\( 0.92 \pm 0.08 \)</td><td>\( \mathbf{0.58} \pm 0.04 \)</td><td>\( 0.65 \pm 0.02 \)</td><td>\( \mathbf{411.7} \pm 5.3 \)</td><td>\( 0.62 \pm 0.02 \)</td></tr><tr><td>64</td><td>64</td><td>\( 0.71 \pm 0.02 \)</td><td>\( 0.98 \pm 0.03 \)</td><td>\( 0.55 \pm 0.02 \)</td><td>\( 0.64 \pm 0.02 \)</td><td>\( 455.4 \pm 12.8 \)</td><td>\( 0.71 \pm 0.02 \)</td></tr><tr><td>512</td><td>64</td><td>\( 0.70 \pm 0.03 \)</td><td>\( \mathbf{0.99} \pm 0.02 \)</td><td>\( 0.54 \pm 0.04 \)</td><td>\( 0.63 \pm 0.03 \)</td><td>\( 478.5 \pm 18.4 \)</td><td>\( \mathbf{0.75} \pm 0.05 \)</td></tr></table>

Table 7:  \( F_{1} \)  score, precision P, recall R, average detection delay  \( \bar{\delta} \)  and root-cause precision  \( P_{rc} \)  using the unsupervised threshold (top half) and theoretical best threshold (bottom half), as well as the area under the precision-recall curve  \( A_{PR} \)  for various  \( d_{Z} \)  values.

<table><tr><td>\( d_{\mathbf{K}} \)</td><td>\( d_{\mathbf{Z}} \)</td><td>\( F_1 \)</td><td>\( P \)</td><td>\( R \)</td><td>\( A_{\text{PR}} \)</td><td>\( \bar{\delta} \) [s]</td><td>\( P_{\text{rc}} \)</td></tr><tr><td>1</td><td>1</td><td>\( 0.34 \pm 0.18 \)</td><td>\( \mathbf{1.00} \pm 0.00 \)</td><td>\( 0.22 \pm 0.15 \)</td><td>\( 0.42 \pm 0.11 \)</td><td>\( 690.5 \pm 106.8 \)</td><td>\( 0.74 \pm 0.15 \)</td></tr><tr><td>1</td><td>8</td><td>\( \mathbf{0.75} \pm 0.03 \)</td><td>\( 0.95 \pm 0.04 \)</td><td>\( \mathbf{0.62} \pm 0.06 \)</td><td>\( \mathbf{0.71} \pm 0.05 \)</td><td>\( \mathbf{407.8} \pm 24.1 \)</td><td>\( 0.55 \pm 0.10 \)</td></tr><tr><td>1</td><td>64</td><td>\( 0.70 \pm 0.03 \)</td><td>\( 0.92 \pm 0.08 \)</td><td>\( 0.57 \pm 0.04 \)</td><td>\( 0.66 \pm 0.04 \)</td><td>\( 418.1 \pm 17.3 \)</td><td>\( 0.63 \pm 0.18 \)</td></tr><tr><td>1</td><td>512</td><td>\( 0.70 \pm 0.05 \)</td><td>\( 0.98 \pm 0.03 \)</td><td>\( 0.55 \pm 0.05 \)</td><td>\( 0.64 \pm 0.03 \)</td><td>\( 448.9 \pm 38.0 \)</td><td>\( \mathbf{0.67} \pm 0.08 \)</td></tr><tr><td>1</td><td>1</td><td>\( 0.49 \pm 0.10 \)</td><td>\( 0.74 \pm 0.29 \)</td><td>\( 0.44 \pm 0.12 \)</td><td>\( 0.42 \pm 0.11 \)</td><td>\( 655.3 \pm 99.8 \)</td><td>\( 0.58 \pm 0.27 \)</td></tr><tr><td>1</td><td>8</td><td>\( \mathbf{0.77} \pm 0.03 \)</td><td>\( 0.94 \pm 0.05 \)</td><td>\( \mathbf{0.65} \pm 0.06 \)</td><td>\( \mathbf{0.71} \pm 0.05 \)</td><td>\( \mathbf{387.6} \pm 37.6 \)</td><td>\( 0.48 \pm 0.08 \)</td></tr><tr><td>1</td><td>64</td><td>\( 0.72 \pm 0.03 \)</td><td>\( 0.97 \pm 0.04 \)</td><td>\( 0.58 \pm 0.06 \)</td><td>\( 0.66 \pm 0.04 \)</td><td>\( 412.9 \pm 25.0 \)</td><td>\( \mathbf{0.67} \pm 0.15 \)</td></tr><tr><td>1</td><td>512</td><td>\( 0.72 \pm 0.03 \)</td><td>\( \mathbf{1.00} \pm 0.00 \)</td><td>\( 0.56 \pm 0.04 \)</td><td>\( 0.64 \pm 0.03 \)</td><td>\( 439.7 \pm 24.2 \)</td><td>\( 0.66 \pm 0.04 \)</td></tr></table>

As shown in the ablation study, the multi-head attention mechanism does positively impact anomaly detection performance, however Table 6 illustrates that once MA is implemented, the key dimensionality plays a small role, as all metrics are very comparable for all  \( d_{K} \) . When it comes to the latent dimension size  \( d_{Z} \) , it is clear that for  \( d_{Z} = d_{K} = 1 \) , the model cannot pass enough information through the two bottlenecks to yield good performance. Once  \( d_{Z} = 8 \)  is reached, the best anomaly detection performance ever observed in the experimentation is obtained, after which it drops slightly for  \( d_{Z} = 64 \)  and  \( d_{Z} = 512 \) . The same cannot be said for the root-cause precision  \( P_{rc} \) , which is lower for  \( d_{Z} = 8 \)  than for the other configurations.

### 5.7 Benchmarking

Of course, TeVAE is not the first model proposed for time-series anomaly detection. To relate its anomaly detection performance, it is compared with a series of other models based on variational autoencoders. The chosen subset of models is based on the work discussed in Section 3 which either linked source code or contained enough information for implementation. The models are implemented using hyperparameters specified in their respective publications. All models are trained on the 512h subset with early stopping, which is parameterised equally across all models. The anomaly detection process specified in Algorithm 1 is also applied to all models, along with the

17

threshold estimation method. For VASP and LW-VAE no root-cause precision  \( P_{rc} \)  is provided because the resulting anomaly scores cannot be decomposed. The results can be seen in Table 8.

Table 8:  \( F_{1} \)  score, precision P, recall R, average detection delay  \( \bar{\delta} \)  and root-cause precision  \( P_{rc} \)  using the unsupervised threshold (top half) and theoretical best threshold (bottom half), as well as the area under the precision-recall curve  \( A_{PR} \)  for competing models and TeVAE (Ours). The best values for each metric are given in bold.

<table><tr><td>Model</td><td>\( F_1 \)</td><td>P</td><td>R</td><td>\( A_{\text{PR}} \)</td><td>\( \bar{\delta} \) [s]</td><td>\( P_{\text{rc}} \)</td></tr><tr><td>VS-VAE</td><td>0.58 ± 0.07</td><td>0.90 ± 0.10</td><td>0.44 ± 0.09</td><td>0.56 ± 0.06</td><td>539.3 ± 55.0</td><td>0.71 ± 0.17</td></tr><tr><td>OmniA</td><td>0.36 ± 0.25</td><td>0.65 ± 0.46</td><td>0.25 ± 0.17</td><td>0.39 ± 0.14</td><td>729.0 ± 100.9</td><td>0.61 ± 0.43</td></tr><tr><td>W-VAE</td><td>0.46 ± 0.02</td><td>0.86 ± 0.10</td><td>0.31 ± 0.01</td><td>0.42 ± 0.04</td><td>596.9 ± 12.8</td><td>0.86 ± 0.10</td></tr><tr><td>SISVAE</td><td>0.35 ± 0.22</td><td>0.89 ± 0.08</td><td>0.25 ± 0.16</td><td>0.48 ± 0.04</td><td>665.4 ± 100.5</td><td>0.51 ± 0.36</td></tr><tr><td>VASP</td><td>0.51 ± 0.02</td><td>0.94 ± 0.00</td><td>0.35 ± 0.02</td><td>0.59 ± 0.03</td><td>581.6 ± 3.5</td><td>n/a</td></tr><tr><td>LW-VAE</td><td>0.48 ± 0.01</td><td>0.94 ± 0.00</td><td>0.33 ± 0.01</td><td>0.57 ± 0.03</td><td>585.1 ± 2.0</td><td>n/a</td></tr><tr><td>TeVAE</td><td>0.70 ± 0.03</td><td>0.92 ± 0.08</td><td>0.57 ± 0.04</td><td>0.66 ± 0.04</td><td>418.1 ± 17.3</td><td>0.76 ± 0.08</td></tr><tr><td>VS-VAE</td><td>0.62 ± 0.07</td><td>0.97 ± 0.02</td><td>0.45 ± 0.07</td><td>0.56 ± 0.06</td><td>531.3 ± 39.8</td><td>0.75 ± 0.10</td></tr><tr><td>OmniA</td><td>0.49 ± 0.12</td><td>0.72 ± 0.37</td><td>0.50 ± 0.14</td><td>0.39 ± 0.14</td><td>629.6 ± 116.3</td><td>0.62 ± 0.35</td></tr><tr><td>W-VAE</td><td>0.50 ± 0.04</td><td>0.83 ± 0.12</td><td>0.36 ± 0.04</td><td>0.42 ± 0.04</td><td>576.0 ± 37.1</td><td>0.77 ± 0.13</td></tr><tr><td>SISVAE</td><td>0.55 ± 0.04</td><td>0.95 ± 0.01</td><td>0.39 ± 0.04</td><td>0.48 ± 0.04</td><td>599.4 ± 11.0</td><td>0.88 ± 0.03</td></tr><tr><td>VASP</td><td>0.66 ± 0.03</td><td>0.80 ± 0.03</td><td>0.57 ± 0.07</td><td>0.59 ± 0.03</td><td>474.6 ± 20.1</td><td>n/a</td></tr><tr><td>LW-VAE</td><td>0.64 ± 0.02</td><td>0.78 ± 0.03</td><td>0.54 ± 0.04</td><td>0.57 ± 0.03</td><td>489.3 ± 14.2</td><td>n/a</td></tr><tr><td>TeVAE</td><td>0.72 ± 0.03</td><td>0.97 ± 0.04</td><td>0.58 ± 0.06</td><td>0.66 ± 0.04</td><td>412.9 ± 25.0</td><td>0.80 ± 0.09</td></tr></table>

As is evident, TeVAE outperforms all other models in  \( F_{1} \)  score, R,  \( A_{PR} \)  and  \( \bar{\delta} \) , while providing nearly matching the best precision result using the unsupervised threshold. As stated in Section 4 a very high precision figure is important in this type of powertrain testing, however, the reduced precision is still considered tolerable. Also, it comes at the benefit of a much higher recall figure, which is reflected in the superior  \( F_{1} \)  figure, though it still leaves room for improvement. Furthermore, the  \( F_{1,best} \)  figure, which is obtained at P = 0.97 and R = 0.58, suggests that TeVAE has the potential to achieve even higher precision without sacrificing recall if the threshold were optimised.

## Conclusion

### 6 Conclusion and Outlook

In this paper, a variational autoencoder (TeVAE) for unsupervised anomaly detection in automotive testing is proposed. Automotive testing is an especially challenging scenario due to its massive, diverse and multi-dimensional nature. In addition to that, the resulting data not only features variable states but also highly dynamic signals along with more static ones, adding to further complexity. It not only features an attention configuration that avoids the bypass phenomenon but also introduces a novel method of remapping windows to whole sequences. A number of experiments are conducted to demonstrate the online anomaly detection performance of the model, as well as to underline the benefits of key aspects introduced with the model. To this end, novel metrics are introduced to measure the detection delay, as well as the root-cause analysis capability of analysed anomaly detection approaches.

From the results obtained, TeVAE clearly benefits from the MA mechanism, indicating the avoidance of the bypass phenomenon. Moreover, the proposed approach only requires a small training and validation subset size but fails to obtain a suitable threshold, as with increasing subset size only the calibrated anomaly detection performance increases. Despite the higher theoretical delay, mean-type reverse windowing performs comparably to its last-type in both detection performance and observed average detection delay, while outperforming the first-type method, which in turn yielded higher root-cause precision than the other two methods. Also, the hyperparameter optimisation reveals that one of the least parameter-heavy configurations of the TeVAE results in the best anomaly detection performance, though it should be noted that this performance is only theoretical and not achievable in a production environment due to the unsupervised nature of the problem. In its default setting, TeVAE is only 8% of the time wrong when an anomaly is flagged and manages to discover 57% of the anomalies present in the test data set when the proposed parameter-free and unsupervised threshold is used. If the ideal threshold were known, these values improve to 3% and 58%, respectively. Lastly, it outperforms all other competing models it is compared with.

18

In the future, active learning will be investigated in the context of threshold choice in an effort to find a suitable threshold at an earlier stage.

## References

[1] Chuadhry Mujeeb Ahmed, Venkata Reddy Palleti, and Aditya P. Mathur. “WADI: A water distribution testbed for research in the design of secure cyber physical systems”. In: 3rd International Workshop on Cyber-Physical Systems for Smart Water Networks, CySWATER 2017 (2017), pp. 25–28. DOI: 10.1145/3055366.3055375.

[2] Dzmitry Bahdanau, KyungHyun Cho, and Yoshua Bengio. “Neural Machine Translation by Jointly Learning to Align and Translate”. In: International Conference on Learning Representations (ICLR). 2015.

[3] Hareesh Bahuleyan et al. “Variational Attention for Sequence-to-Sequence Models”. In: International Conference on Computational Linguistics (COLING). 2018.

[4] John S. Bridle. “Probabilistic Interpretation of Feedforward Classification Network Outputs, with Relationships to Statistical Pattern Recognition”. In: Neurocomputing. 1990, pp. 227–236. ISBN: 978-3-642-76155-3 978-3-642-76153-9.

[5] Tingting Chen et al. “Unsupervised Anomaly Detection of Industrial Robots Using Sliding-Window Convolutional Variational Autoencoder”. In: IEEE Access 8 (2020), pp. 47072–47081. DOI: 10.1109/ACCESS.2020.2977892.

[6] Francois Chollet. Deep Learning with Python. Manning Publications, 2021. ISBN: 978-1-61729-686-4.

[7] Lucas Correia et al. “MA-VAE: Multi-Head Attention-Based Variational Autoencoder Approach for Anomaly Detection in Multivariate Time-Series Applied to Automotive Endurance Powertrain Testing:” in: Conference on Neural Computation Theory and Applications (NCTA). 2023, pp. 407–418. DOI: 10.5220/0012163100003595.

[8] Daniel Fährmann et al. “Lightweight Long Short-Term Memory Variational Auto-Encoder for Multivariate Time Series Anomaly Detection in Industrial Control Systems”. In: Sensors 22.8 (2022), p. 2886. DOI: 10.3390/s22082886.

[9] Hao Fu et al. “Cyclical Annealing Schedule: A Simple Approach to Mitigating”. In: Conference of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT). 2019. DOI: 10.18653/v1/N19-1021.

[10] Ian Goodfellow, Yoshua Bengio, and Aaron Courville. Deep Learning. MIT Press, 2016. ISBN: 978-0-262-03561-3.

[11] Kyle Hundman et al. “Detecting Spacecraft Anomalies Using LSTMs and Nonparametric Dynamic Thresholding”. In: New York, NY, USA, 2018, pp. 387–395. DOI: 10.1145/3219819.3219845.

[12] Diederik P. Kingma and Max Welling. "Auto-Encoding Variational Bayes". In: International Conference on Learning Representations (ICLR). 2014.

[13] Don S. Lemons and Paul Langevin. An introduction to stochastic processes in physics: containing "On the theory of Brownian motion" by Paul Langevin, translated by Anthony Gythiel. Baltimore: Johns Hopkins University Press, 2002.

[14] Longyuan Li et al. “Anomaly Detection of Time Series With Smoothness-Inducing Sequential Variational Auto-Encoder”. In: Transactions on Neural Networks and Learning Systems 32.3 (2021), pp. 1177–1191. DOI: 10.1109/TNNLS.2020.2980749.

[15] Aditya P. Mathur and Nils Ole Tippenhauer. “SWaT: a water treatment testbed for research and training on ICS security”. In: International Workshop on Cyber-physical Systems for Smart Water Networks (CySWater). IEEE, 2016, pp. 31–36. DOI: 10.1109/CySWater.2016.7469060.

[16] Geroge Moody and Roger Mark. “The Impact of the MIT-BIH Arrhythmia Database”. In: IEEE Engineering in Med and Biology 20.3 (2001), pp. 45–50. DOI: 10.13026/C2F305.

[17] Daehyung Park, Yuuna Hoshi, and Charles C. Kemp. “A Multimodal Anomaly Detector for Robot-Assisted Feeding Using an LSTM-Based Variational Autoencoder”. In: IEEE Robotics and Automation Letters 3.3 (2018), pp. 1544–1551. DOI: 10.1109/LRA.2018.2801475.

[18] Joao Pereira and Margarida Silveira. “Unsupervised Anomaly Detection in Energy Time Series Data Using Variational Recurrent Autoencoders with Attention”. In: International Conference on Machine Learning and Applications (ICMLA). 2018. DOI: 10.1109/ICMLA.2018.00207.

19

[19] Joao Pereira and Margarida Silveira. “Unsupervised representation learning and anomaly detection in ECG sequences”. In: International Journal of Data Mining and Bioinformatics 22.4 (2019), p. 389. DOI: 10.1504/IJDMB.2019.101395.

[20] Danilo Jimenez Rezende and Shakir Mohamed. “Variational Inference with Normalizing Flows”. In: International Conference on Machine Learning (ICML). 2015. DOI: 10.5555/3045118.3045281.

[21] Danilo Jimenez Rezende, Shakir Mohamed, and Daan Wierstra. “Stochastic Backpropagation and Approximate Inference in Deep Generative Models”. In: International Conference on Machine Learning (ICML). 2014. DOI: 10.5555/3044805.3045035.

[22] Julian von Schleinitz et al. “VASP: An autoencoder-based approach for multivariate anomaly detection and robust time series prediction with application in motorsport”. In: Engineering Applications of Artificial Intelligence 104 (2021), p. 104354. DOI: 10.1016/j.engappai.2021.104354.

[23] C.E. Shannon. “Communication in the Presence of Noise”. In: Proceedings of the IRE 37.1 (1949), pp. 10–21. DOI: 10.1109/JRPROC.1949.232969.

[24] Ya Su et al. “Robust Anomaly Detection for Multivariate Time Series through Stochastic Recurrent Neural Network”. In: International Conference on Knowledge Discovery & Data Mining (KDD). 2019. DOI: 10.1145/3292500.3330672.

[25] Ashish Vaswani et al. “Attention Is All You Need”. In: Conference on Neural Information Processing Systems (NIPS). 2017. DOI: 10.5555/3295222.3295349.

[26] Pascal Vincent et al. “Extracting and composing robust features with denoising autoencoders”. In: 2008. DOI: 10.1145/1390156.1390294.

[27] Renjie Wu and Eamonn J. Keogh. “Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress”. In: IEEE Transactions on Knowledge and Data Engineering (2021), pp. 2421–2429. DOI: 10.1109/TKDE.2021.3112126.

[28] Chuxu Zhang et al. “A Deep Neural Network for Unsupervised Anomaly Detection and Diagnosis in Multivariate Time Series Data”. In: AAAI Conference on Artificial Intelligence. 2019. DOI: 10.1609/aaai.v33i01.33011409.

[29] Kai Zhang et al. “Federated Variational Learning for Anomaly Detection in Multivariate Time Series”. In: International Performance, Computing, and Communications Conference (IPCCC). 2021. DOI: 10.1109/IPCCC51483.2021.9679367.

20

## Unknown

arXiv:2407.06849v2 [cs.LG] 12 Nov 2025

### TeVAE: A Variational Autoencoder Approach for Discrete Online Anomaly Detection in Variable-state Multivariate Time-series Data

Lucas Correia

Mercedes-Benz AG

Stuttgart

Germany

lucas.correia@mercedes-benz.com

Jan-Christoph Goos

Mercedes-Benz AG

Stuttgart

Germany

Philipp Klein

Mercedes-Benz AG

Stuttgart

Germany

Thomas Bäck

Leiden University

Leiden

The Netherlands

Anna V. Kononova

Leiden University

Leiden

The Netherlands

---
paper_id: paper_2
title: "Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT"
source_type: pdf
source_confidence: high
canonicalization_status: degraded
canonical_quality_status: DEGRADED
primary_parser: pymupdf
fallback_used: false
m2_ready: false
m2_ready_for_formula_understanding: false
formula_slot_count: 26
mineru_latex_count: 0
raw_formula_text_count: 26
raw_only_formula_dense: true
section_contradiction_count: 0
all_formulas_in_Abstract_suspicious: false
formula_understanding_reason: "RAW_ONLY_FORMULA_DENSE_NO_LATEX"
source_pdf_path: "source.pdf"
all_formulas_in_Abstract_suspicious: false
bbox_count: 26
blocking_reasons: "MISSING_FORMULA_CROP; MISSING_FORMULA_OVERLAY"
canonical_match: true
crop_exists: 0
formula_count: 26
formula_understanding_reasons: "RAW_ONLY_FORMULA_DENSE_NO_LATEX"
high_risk_count: 3
latex_count: 0
low_risk_count: 0
m2_ready_for_formula_understanding: false
medium_risk_count: 3
missing_crop_count: 26
missing_overlay_count: 26
ollama_changed_by_count: 0
ollama_json_invalid: 0
ollama_json_valid: 0
ollama_retry: 0
ollama_timeout: 0
overlay_exists: 0
peak_vram_estimate: "not measured"
polluted_section_count: 0
primary_parser: "pymupdf"
raw_formula_text_count: 26
raw_only_formula_dense: true
route: "D MarkItDown/PyMuPDF fallback/debug"
runtime_device: "CPU/cached artifacts"
runtime_seconds: 0.259
section_contradiction_count: 0
warning_reasons: "MISSING_FORMULA_LATEX; RAW_ONLY_FORMULA_DENSE_NO_LATEX; FORMULA_VISUAL_REVIEW_PENDING"
---

# Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT

## Abstract

Many real-world IoT systems, which include a variety of internet-connected sensory devices, produce substantial amounts of multivariate time series data. Meanwhile, vital IoT infrastructures like smart power grids and water distribution net- works are frequently targeted by cyber-attacks, making anomaly detection an important study topic. Modeling such relatedness is, nevertheless, unavoidable for any efﬁcient and effective anomaly detection system, given the intricate topological and nonlinear connections that are originally unknown among sensors. Further- more, detecting anomalies in multivariate time series is difﬁcult due to their temporal dependency and stochasticity. This paper presented GTA, a new framework for multivariate time series anomaly detection that involves automatically learning a graph structure, graph convolution, and modeling temporal dependency using a Transformer-based architecture. The connection learning policy, which is based on the Gumbel-softmax sampling approach to learn bi-directed links among sensors directly, is at the heart of learning graph structure. To describe the anomaly information ﬂow between network nodes, we introduced a new graph convo- lution called Inﬂuence Propagation convolution. In addition, to tackle the quadratic complexity barrier, we suggested a multi- branch attention mechanism to replace the original multi-head self-attention method. Extensive experiments on four publicly available anomaly detection benchmarks further demonstrate the superiority of our approach over alternative state-of-the-arts. Codes are available at https://github.com/ZEKAICHEN/GTA. Index Terms—Multivariate time series, anomaly detection, graph learning, self-attention

## Introduction

Due to the fast rising number of Internet-connected sensory devices, the Internet of Things (IoT) infrastructure has created vast sensory data. IoT data is often characterized by its speed in terms of geographical and temporal dependency [1], [2], and it is frequently subjected to correspondingly rising abnormalities and cyberattacks [3], [4]. Many critical infrastructures constructed on top of Cyber-Physical Systems (CPS) [5], such as smart power grids, water treatment and distribution networks, transportation, and autonomous cars, are especially in need of security monitoring [6], [7], [4]. As a result, an efﬁcient and accurate anomaly detection system has great research value because it can help with continuous monitoring of fundamental controls or indicators and promptly provide notiﬁcations for any probable anomalous occurrence. Z. Chen is with the Department of Computer Science, George Washington University, Washington, DC, 20052 USA (email: zech chan@gwu.edu) Z. Yuan is with the School of Business, Rutgers University, New Jersey, 08901 USA (email: zy101@rutgers.edu) X. Zhang (corresponding author), X. Cheng and D. Chen are with School of Computer Science and Technology, Shandong University, China (emails: xiaozhang@sdu.edu.cn, xzcheng@sdu.edu.cn) In this work, we focus on anomaly detection for multivariate time series [8] as a copious amount of IoT sensors in many real-life scenarios consecutively generate substantial volumes of time series data. For instance, in a Secure Water Distribution (WADI) system [9], multiple sensing measurements such as ﬂowing meter, transmitting level, valve status, water pressure level, etc., are recorded simultaneously at each timestamp to form a multivariate time series. In this case, the central water treatment testbed is also known as an entity. It is commonly accepted to detect anomalies from the entity-level instead of the sensor-level since the overall status detection is generally worth more concern and less expensive. Predominantly, data from these sensors are highly correlated in a complex topo- logical and nonlinear fashion: for example, opening a valve would result in pressure and ﬂow rate changes, leading to further chain reactions of other sensors within the same entity following an internal mechanism. Nevertheless, the dependen- cies among sensors are initially hidden and somehow costly to access in most real-life scenarios, leading to an intuitive question of how to model such complicated relationships between sensors without knowing prior information? Recently, deep learning-based techniques have demonstrated some promising improvements in anomaly detection due to the superiority in sequence modeling over high-dimensional datasets. Generally, the existing approaches can roughly fall into two lines: reconstruction-based models (R-model) [10], [11], [12], [6], [13] and forecasting-based models (F-model) [14], [15], [8], [16], [17], [4]. For example, Auto-Encoders (AE) [10] is a popular approach for anomaly detection, which uses reconstruction error as an outlier score. More recently, Generative Adversarial Networks (GANs) [18], [19] based on reconstruction [20], [6] and RNN-based forecasting ap- proaches [8], [17] have also reported promising performance for multivariate anomaly detection. However, these methods do not explicitly learn the topological structure among sen- sors, thus leaving room for improvements in modeling high- dimensional sensor data with considerable potential inter- relationships appropriately. Graph Convolutional Networks (GCNs) [21], [22], [23], [24] have recently revealed discriminative power in learning graph representations due to their permutation-invariance, lo- cal connectivity, and compositionality [21], [25]. Graph neural networks allow each graph node to acknowledge its neigh- borhood context by propagating information through struc- tures. Recent works [17], [26], [4] then combined temporal modeling methods with GCNs to model the topological r

## Related Work

The existing literature for addressing time series anomaly detection usually can be divided into two major categories. The ﬁrst category usually modeled each time series variable independently, while the second category took into considera- tion the correlations among multivariate time series to improve the performance. A. Anomaly Detection in Univariate Time Series The anomaly detection in univariate time series has drawn many researchers’ attentions in recent years. Traditionally, the anomaly detection frameworks included two main phases: estimation phase and detection phase [28]. In estimation phase, the variable values at one timestamp or time interval can be predicted or estimated by speciﬁc algorithm. Then the estimated values were compared with real values based on dynamically adjusted thresholds to detect anomalies in detec- tion phase. For example, Zhang et. al [29] applied ARIMA to capture the linear dependencies between the future values and the past values, thus modeling the time series behavior for anomaly detection. Lu et.al [30] utilized wavelet analysis to construct the estimation model. With the development of deep learning, various neural network architectures have also been applied to anomaly detection. DeepAnt [31] was an unsupervised approach using convolutional neural network (CNN) to forecast future time series values and adopted Euclidean distance to measure the discrepancy for anomaly detection. The LSTM neural network was also widely used in modeling time series behaviors [32], [33], [6]. The LSTM- based encoder-decoder [32] reconstructed the variable values and measured the reconstruction errors for detection. B. Anomaly Detection in Multivariate Time Series In real-world scenarios, the time series data acquisition sources could be multiple [34]. Therefore, many work began to pay attention to exploiting the correlations among multiple variables to improve the accuracy of anomaly detection. Jones et.al [35] extracted statistical and smoothed trajectory (SST) features of time series and utilized a set of non-linear func- tions to model related variables to detect anomalies. Using the LSTM network as the base models to to capture the temporal correlations of time series data, MAD-GAN [6] proposed an unsupervised anomaly detection method com- bining generative adversarial networks (GAN) by considering complex dependencies amongst different time series variables. Sakurada et al. [36] conducted dimentionality reduction based on autoencoders for anomaly detection. The ODCA frame- work [37] included three parts: data preprocessing, outlier analysis, and outlier rank, which used cross correlation to translate high-dimentional data sets to one-dimentional cross- correlation function. OmniAnomaly [13] was a stochastic model to avoid potential misguiding by uncertain instances, which used stochastic variable connection and normalizing ﬂow to get reconstruction probabilities and adopted stream- ing POT with drift (DSPOT) algorithm [38] for automatic threshold selection. Senin et al. [39] proposed two algorithms 3 Fig. 1: The visualization of our proposed GTA’s architecture with l levels dilated convolution and graph convolution, 3 encoder layers, and 1 decoder layer. Generally, the input multivariate time series inputs are split into train sequences and label sequences, of which train sequences are fed into encoder while label sequences are fed to the decoder. that conducted symbolic time series discretization and used grammar reduction to compress the input sequence and com- pactly encode them with grammar rules. Those rarely used substrings in the grammar rules were regarded as anomalies. Autoregressive with exogenous inputs (ARX) and artiﬁcial neural network (ANN) [40] extracted time-series features and detected anomalous data points by conducting hypothesis testing on the extrema of residuals. To cover the shortage that the convolution and pooling operators of CNNs are deﬁned for regular grids, recent GNN [41

## Method

In most real-life scenarios of IoT, there are usually complex topological relationships between sensors where the entire entity can be seen as a graph structure. Each sensor is also viewed as a speciﬁc node in the graph. Previous methods [25],

## Experiments

A. Datasets We evaluate our method over a wide range of real-world anomaly detection datasets. SWaT [55] The Secure Water Treatment dataset is collected from a water treatment testbed for cyber-attack investigation initially launched in May 2015. The SWaT dataset collection process lasted for 11 days, with the system operated 24 hours per day such that the network trafﬁc and all the values obtained from all 51 sensors and actuators are recorded. Due to the system working ﬂow char- acteristics, there is a natural topological structure relationship between all sensing nodes. After this, a total of 41 attacks derived through an attack model considering the intent space of a CPS were launched during the last 4 days of the 2016 SWaT data collection process. As such, the overall sequential data is labeled according to normal and abnormal behaviors at each timestamp. WADI [9] Water Distribution dataset is collected from a water distribution testbed as an extension of the SWaT testbed. It consists of a total of 16 days of continuous operations with 14 days under regular operation and 2 days with attack scenarios. The entire testbed contains 123 sensors and actuators. Moreover, SMAP (Soil Moisture Active Passive satellite) and MSL (Mars Science Laboratory rover) are two public datasets published by NASA [56]. Each dataset has a training and a testing subset, and anomalies in both testing subsets have been labeled [8]. Table II and III summarises the statistics of the four datasets. In order to fair comparison with other methods, the original data samples for SWaT and WADI are downsampled to one measurement every 10 seconds by taking the median values following [4]. TABLE II: Statistical summary of datasets SWaT and WADI. Datasets SWaT WADI Feature Desc. All sensors and actuators.

51 112

41 15 Attack durations (mins) 2 ∼25 1.5 ∼30 Training size (normal data) 49619 120899 Testing size (data with attacks) 44931 17219 Anomaly rate (%) 12.14 5.75 TABLE III: Statistical summary of datasets SMAP and MSL. Datasets SMAP MSL Feature Desc. Radiation, temperature, power, etc.

25 25 Training size (normal data) 135183 58317 Testing size (data with anomalies) 427617 73729 Anomaly rate (%) 13.13 10.72 B. Experimental Setup 1) Data preprocessing: We perform a data standardization before training to improve the robustness of our model. Data preprocessing is applied on both training and testing set: ˜x = x −min Xtrain max Xtrain −min Xtrain (12) where max(Xtrain) and min(Xtrain) are the maximum value and the minimum value of the training set respectively. metrics: We adopt the standard evaluation metrics in anomaly detection tasks, namely Precision, Recall and F1 score, to evaluate the performance of our approach, in which: Precision = TP TP + FP (13) Recall = TP TP + FN (14) F1 = 2 × Precision × Recall Precision + Recall (15) where TP represents the truly detected anomalies (aka. true positives), FP stands for the falsely detected anomalies (aka. false positives), TN represents the correctly classiﬁed normal samples (aka. true negatives), and FN is the misclassiﬁed normal samples (aka. false negatives). Given the fact that 8 TABLE IV: Experimental results on SWaT and WADI. Datasets Methods Precision(%) Recall(%) F1-score PCA 24.92 21.63 0.23 KNN 7.83 7.83 0.08 FB 10.17 10.17 0.10 AE 72.63 52.63 0.61 DAGMM 27.46 69.52 0.39 LSTM-VAE 96.24 59.91 0.74 MAD-GAN 98.97 63.74 0.77 GDN 99.35 68.12 0.81 GTA∗(ours) 74.91 96.41 0.84 GTA∗∗ 94.83 88.10 0.91 SWaT ∆↑(best F1) -4.55% +29.33% +12.35% PCA 39.53 5.63 0.10 KNN 7.76 7.75 0.08 FB 8.60 8.60 0.09 AE 34.35 34.35 0.34 DAGMM 54.44 26.99 0.36 LSTM-VAE 87.79 14.45 0.25 MAD-GAN 41.44 33.92 0.37 GDN 97.50 40.19 0.57 GTA∗(ours) 74.56 90.50 0.82 GTA∗∗ 83.91 83.61 0.84 WADI ∆↑(best F1) -13.94% +108.04% +47.37% Best performance in bold. Second-best with underlines. ∗represents the results chosen by best Recall. ∗∗represents the results chosen by best F1-score. ∆↑represents the percentage increase between our best F1-score performance and the second-best method (GDN). TABLE V: Experimental results on SMAP and MSL. SMAP MSL Method Precision(%) Recall(%) F1-score Precision(%) Recall(%) F1-score KitNet 77.25 83.27 0.8014 63.12 79.36 0.7031 GAN-Li 67.10 87.06 0.7579 71.02 87.06 0.7823 LSTM-VAE 85.51 63.66 0.7298 52.57 95.46 0.6780 MAD-GAN 80.49 82.14 0.8131 85.17 89.91 0.8747 R-Models OmniAnomaly 74.16 97.76 0.8434 88.67 91.17 0.8989 LSTM-NDT 89.65 88.46 0.8905 59.44 53.74 0.5640 DAGMM 58.45 90.58 0.7105 54.12 99.34 0.7007 MTAD-GAT 89.06 91.23 0.9013 87.54 94.40 0.9084 F-Models GTA∗∗(ours) 89.11 91.76 0.9041 91.04 91.17 0.9111 Best performance in bold. Second-best with underlines. ∗∗represents the results chosen by best F1-score. in many real-world anomaly detection scenarios, it is more vital for the system to detect all the real attacks or anomalies by tolerating a few false alarms. As such, we generally give more concern to Recall and the overall F1 score instead of Precision. Considering different anomaly score thresholds may result in different metric scores, we hence report both our best Recall and F1 results (with notations ∗and ∗∗ respectively) on all datasets for a thorough comparison. Also, we adopt the point-adjust way to calculate the perfor- mance metrics following [13]. In practice, anomalous observa- tions usually occur consecutively to form contiguous anomaly segments. An alert for anomalies can be triggered within any subset of an actual anomaly window. Thus, for any observation in the ground truth anomaly segment, if it is detected as an anomaly or attack, we would consider this whole anomaly window is correctly detected and every observation point in this segment has been classiﬁed as anomalies. The observa- tions outside the ground truth anomaly segment are treated as usual. In all, we ﬁrst train our model on the training set to learn the general sequence pattern and make the forecasting on the test set for anomaly detection. 3) Baselines: We compare our GTA with a wide range of state-of-the-arts in multivariate time series anomaly detection, including: (1) r

## Conclusion

In this work, we proposed GTA, a Transformer-based frame- work for anomaly detection that uses the introduced connec- tion learning policy to automatically learn sensor dependen- cies. To simulate the information ﬂow among the sensors in the graph, we devised an unique Inﬂuence Propagation (IP) graph convolution. The inference speed of our proposed multi-branch attention technique is greatly improved without sacriﬁcing model performance. Extensive experiments on four real-world datasets demonstrated that our strategy outperformed other state-of-the-art approaches in terms of prediction accuracy. We also provided a case study to demonstrate how our approach identiﬁes the anomaly by utilizing our proposed techniques. We aim to explore more about combining this approach with the online learning strategy to land it on the mobile IoT scenarios for future work. 11

## References

[1] M. S. Mahdavinejad, M. Rezvan, M. Barekatain, P. Adibi, P. M. Barnaghi, and A. P. Sheth, “Machine learning for internet of things data analysis: A survey,” CoRR, vol. abs/1802.06305, 2018. [2] Z. Cai and Z. He, “Trading private range counting over big iot data,” in 39th IEEE International Conference on Distributed Computing Systems, ICDCS 2019, Dallas, TX, USA, July 7-10, 2019. IEEE, 2019, pp. 144– 153. [Online]. Available: https://doi.org/10.1109/ICDCS.2019.00023 [3] M. Mohammadi, A. I. Al-Fuqaha, S. Sorour, and M. Guizani, “Deep learning for iot big data and streaming analytics: A survey,” IEEE Commun. Surv. Tutorials, vol. 20, no. 4, pp. 2923–2960, 2018. [4] A. Deng and B. Hooi, “Graph neural network-based anomaly detection in multivariate time series,” in Proceedings of the 35th AAAI Conference on Artiﬁcial Intelligence, 2021. [5] Z. Cai and X. Zheng, “A private and efﬁcient mechanism for data uploading in smart cyber-physical systems,” IEEE Trans. Netw. Sci. Eng., vol. 7, no. 2, pp. 766–775, 2020. [Online]. Available: https://doi.org/10.1109/TNSE.2018.2830307 [6] D. Li, D. Chen, B. Jin, L. Shi, J. Goh, and S. Ng, “MAD-GAN: multivariate anomaly detection for time series data with generative adversarial networks,” in 28th International Conference on Artiﬁcial Neural Networks, ser. Lecture Notes in Computer Science, vol. 11730. Springer, 2019, pp. 703–716. [7] X. Zheng and Z. Cai, “Privacy-preserved data sharing towards multiple parties in industrial iots,” IEEE J. Sel. Areas Commun., vol. 38, no. 5, pp. 968–979, 2020. [Online]. Available: https: //doi.org/10.1109/JSAC.2020.2980802 [8] K. Hundman, V. Constantinou, C. Laporte, I. Colwell, and T. S¨oderstr¨om, “Detecting spacecraft anomalies using lstms and non- parametric dynamic thresholding,” in Proceedings of the 24th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining. ACM, 2018, pp. 387–395. [9] C. M. Ahmed, V. R. Palleti, and A. P. Mathur, “WADI: a water distribution testbed for research in the design of secure cyber physical systems,” in Proceedings of the 3rd International Workshop on Cyber- Physical Systems for Smart Water Networks. ACM, 2017, pp. 25–28. [10] C. C. Aggarwal, Outlier Analysis. Springer, 2013. [11] D. Park, Y. Hoshi, and C. C. Kemp, “A multimodal anomaly detector for robot-assisted feeding using an lstm-based variational autoencoder,” CoRR, vol. abs/1711.00614, 2017. [12] B. Zong, Q. Song, M. R. Min, W. Cheng, C. Lumezanu, D. Cho, and H. Chen, “Deep autoencoding gaussian mixture model for unsupervised anomaly detection,” in 6th International Conference on Learning Rep- resentations. OpenReview.net, 2018. [13] Y. Su, Y. Zhao, C. Niu, R. Liu, W. Sun, and D. Pei, “Robust anomaly detection for multivariate time series through stochastic recurrent neural network,” in Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining. ACM, 2019, pp. 2828–2837. [14] F. Angiulli and C. Pizzuti, “Fast outlier detection in high dimensional spaces,” in Principles of Data Mining and Knowledge Discovery, 6th European Conference, ser. Lecture Notes in Computer Science, vol. 2431. Springer, 2002, pp. 15–26. [15] A. Lazarevic and V. Kumar, “Feature bagging for outlier detection,” in Proceedings of the 11th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining. ACM, 2005, pp. 157–166. [16] Y. Liang, Z. Cai, J. Yu, Q. Han, and Y. Li, “Deep learning based inference of private information using embedded sensors in smart devices,” IEEE Netw., vol. 32, no. 4, pp. 8–14, 2018. [Online]. Available: https://doi.org/10.1109/MNET.2018.1700349 [17] H. Zhao, Y. Wang, J. Duan, C. Huang, D. Cao, Y. Tong, B. Xu, J. Bai, J. Tong, and Q. Zhang, “Multivariate time-series anomaly detection via graph attention network,” in 20th IEEE International Conference on Data Mining. IEEE, 2020, pp. 841–850. [18] I. J. Goodfellow, J. Pouget-Abadie, M. Mirza, B. Xu, D. Warde-Farley, S. Ozair, A. C. Courville, and Y. Bengio, “Gen

Global/Inter Scaled Dot-Product 4d2 O(4nd2 + 2n2d) Inter Global-Learned m2h + 2d2 O(2nd2 + n2d) Global Branch-Wise Mixing 4d2 1 + m2h + 2d2 2 O(4nd2 1 + n2d1 + 2nd2 2 + n2d) Both instantly predicts output elements in a generative style. Let the single-step prediction denote as ˆY ∈RM×n. We apply the Mean Square Error (MSE) between the predicted outputs ˆY and the observation Y, as the loss function to minimize: Lmse = 1 M n X t=1 ||Y(t) −ˆY(t)||2 2 (10) Similar to the loss objective, the anomalous score compares the expected value at time t to the observed value, computing an anomaly score via the deviation level as: ˆy(t) = M X i=1 ||Y(t) i −ˆY(t) i ||2 2 (11) Finally, we label a timestamp t as an anomaly if ˆy(t) exceeds a ﬁxed threshold. Since different approaches could be employed to set the threshold such as extreme value theory [38], the same anomaly detection model could result in different prediction performance with different anomaly thresholds. Thus, we apply a grid search on all possible anomaly thresholds to search for the best F1-score (with notation ∗∗) and Recall (with notation ∗) in theory and report them. and other state-of-the-arts on datasets SWaT and WADI. Each of these baselines provides a speciﬁc threshold selection method, and the reported F1-score is calculated correspondingly. Our proposed GTA signiﬁcantly outperforms all the other approaches on both datasets by achieving the best F1-score as 0.91 for SWaT and 0.84 for WADI. As- tonishingly, compared to the second-best model GDN, GTA can achieve an overall 12.35% increase and an impressive 47.47% improvement in terms of the best F1-score on these two datasets, respectively. Moreover, we have the following observations: (1) Compared to the conventional unsupervised approaches such as PCA, KNN, FB, deep learning-based tech- niques (AE, LSTM-VAE, MAD-GAN, etc.) generally have a better detection performance on both datasets. By adopting the recurrent mechanism (RNN, GRU, LSTM) in modeling long sequences and capturing the temporal context dependencies, the deep learning-based methods demonstrate superiority over the conventional methods. (2) DAGMM [12] aims to handle multivariate data without temporal information, indicating the input data contains only one observation instead of a historical time series window. Hence this approach is not suitable for temporal dependency modeling, which is crucial for multivari- ate time series anomaly detection. (3) Most existing methods are based on recurrent neural networks to capture tempo- ral dependency, including both reconstruction-based models (LSTM-VAE, OmniAnomaly, MAD-GAN) and forecasting- based models (LSTM-NDT, MTAD-GAT). Of which, LSTM- NDT [8] is a deterministic model without leveraging stochastic 1https://pytorch.org/ TABLE VI: Anomaly detection accuracy in terms of preci- sion(%), recall(%), and F1-score of GTA and its variants. SWaT WADI Prec(%) Rec(%) F1-score Prec(%) Rec(%) F1-score GTA 94.83 88.10 0.91 83.91 83.61 0.84 w/o Graph 88.64 65.73 0.75 71.25 68.23 0.70 w/o LP 89.36 72.12 0.80 79.56 77.10 0.78 w/o Attn 78.75 65.34 0.71 74.75 70.90 0.73 information for modeling the inherent stochasticity of time se- ries. LSTM-VAE [11] combines LSTM with VAE for sequence modeling; however, it ignores the temporal dependencies among latent variables. OmniAnomaly [13] was then proposed to solve this problem. Additionally, MAD-GAN [6] aims to adopt a general adversarial training fashion to reconstruct the original time series, which also uses recurrent neural networks. Nevertheless, the recurrent learning mechanism’s core properties restrict the modeling process to be sequential. Past information has to be retained through the past hidden states, limiting the long-term sequence modeling capability of the model. Transformer adopts a non-sequential learning fashion, and the powerful self-attention mechanism makes the context distance between any token of a time series shrink to one, which is of high importance to se

1 Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT Zekai Chen, Student Member, IEEE, Dingshuo Chen, Xiao Zhang, Member, IEEE, Zixuan Yuan, and Xiuzhen Cheng, Fellow, IEEE

## Unknown

<!-- formula_id: formula_001 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_1 -->
```text
However, one
L = (cid:88) logπi,j (4) mainefficiencybottleneckinself-attentionisthatthepairwise
```

<!-- formula_id: formula_002 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_2 -->
```text
QKT
Attention(Q,K,V)=Softmax( √ )V (5)
```

<!-- formula_id: formula_003 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_3 -->
```text
MultiHead(Q,K,V)=Concat(head ,··· ,head )WO
```

<!-- formula_id: formula_004 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_4 -->
```text
offbetween
head i =Attention(QW i Q,KW i K,VW i V) (7) computation efficiency and model performance, we propose
```

<!-- formula_id: formula_005 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_5 -->
```text
Testing size (data with attacks) 44931 17219
i=1 Anomaly rate (%) 12.14 5.75
```

<!-- formula_id: formula_006 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_6 -->
```text
rations with 14 days under regular operation Recall= (14)
```

<!-- formula_id: formula_007 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_7 -->
```text
Moreover, SMAP (Soil Moisture F1=2× (15)
```

<!-- formula_id: formula_008 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_8 -->
```text
argmax(logπi,j +gi,j)
```

<!-- formula_id: formula_009 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_9 -->
```text
Attention(Q,K,V)
```

<!-- formula_id: formula_010 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_10 -->
```text
Softmax( √ )
```

<!-- formula_id: formula_011 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_11 -->
```text
MultiHead(Q,K,V)
```

<!-- formula_id: formula_012 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_12 -->
```text
Attention(QW i Q,KW i K,VW i V)
```

<!-- formula_id: formula_013 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_13 -->
```text
MultiHead(X(1)
```

<!-- formula_id: formula_014 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_14 -->
```text
Attention(S,V)
```

<!-- formula_id: formula_015 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_15 -->
```text
ned as N(i) =
{j ∈V|ei,j ∈E}.
```

<!-- formula_id: formula_016 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_16 -->
```text
i,j
1
= 1 and πi,j
```

<!-- formula_id: formula_017 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_17 -->
```text
Uniform(0, 1) and computing
g = −log(−log u). We further substitute this arg max oper-
```

<!-- formula_id: formula_018 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_18 -->
```text
zi,j
c
=
exp((log πi,j
```

<!-- formula_id: formula_019 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_19 -->
```text
Attention(Q, K, V) = Softmax(QKT
```

<!-- formula_id: formula_020 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_20 -->
```text
MultiHead(Q, K, V) = Concat(head1, · · · , headh)W O
```

<!-- formula_id: formula_021 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_21 -->
```text
headi = Attention(QW Q
```

<!-- formula_id: formula_022 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_22 -->
```text
Attention(S, V) = Softmax(S)V
```

<!-- formula_id: formula_023 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_23 -->
```text
d2 and d = d1 + d2.
```

<!-- formula_id: formula_024 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_24 -->
```text
FN
(14)
F1 = 2 × Precision × Recall
```

<!-- formula_id: formula_025 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_25 -->
```text
Softmax(QKT
√dk
)
```

<!-- formula_id: formula_026 | origin: raw_formula_text | section: Unknown | page: 1 | bbox: [0.0, 0.0, 1.0, 1.0] | source: pymupdf | block_id: fc_26 -->
```text
Attention(QW Q
i , KW K
i , VW V
i )
```

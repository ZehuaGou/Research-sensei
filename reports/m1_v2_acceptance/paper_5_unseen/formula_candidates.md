# Formula Candidates: TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data

| id | page | section | origin | is_latex | content |
| -- | ---: | ------- | ------ | -------- | ------- |
| u00025 | 1 | Abstract | raw_formula_text | False | based anomaly detection and diagnosis model which uses attention- |
| u00028 | 1 | Abstract | raw_formula_text | False | focus score-based self-conditioning to enable robust multi-modal |
| u00059 | 1 | Method | raw_formula_text | False | increasingly challenging in large-scale databases due to the in- |
| u00095 | 1 | Method | raw_formula_text | False | LSTM-NDT [20] use a Long-Short-Term-Memory (LSTM) based |
| u00103 | 1 | Method | raw_formula_text | False | data-intensive, small constant size window inputs limit the detec- |
| u00114 | 2 | Method | raw_formula_text | False | cent developments of the transformer models allow single-shot in- |
| u00119 | 2 | Method | raw_formula_text | False | sequences with accuracy and training/inference times nearly ag- |
| u00136 | 2 | Method | raw_formula_text | False | using self-conditioning for robust multi-modal feature extraction |
| u00161 | 2 | Method | raw_formula_text | False | cally model the time-series distribution using various classical tech- |
| u00174 | 2 | Method | raw_formula_text | False | auto-regression based approaches are rarely used for anomaly de- |
| u00191 | 2 | Method | raw_formula_text | False | parameter-free version of time series discord discovery by itera- |
| u00193 | 2 | Method | raw_formula_text | False | diate neighbors. MERLIN is considered to be the state-of-the-art |
| u00219 | 2 | Method | raw_formula_text | False | inter-modal correlations [14]. The Omnianomaly [45] uses a sto- |
| u00228 | 3 | Method | raw_formula_text | False | The Multi-Scale Convectional Recursive Encoder-Decoder (MS- |
| u00237 | 3 | Method | raw_formula_text | False | uses a graph-attention network to model both feature and temporal |
| u00238 | 3 | Method | raw_formula_text | False | correlations and pass it through a lightweight Gated-Recurrent- |
| u00240 | 3 | Method | raw_formula_text | False | Traditionally, attention operations perform input compression us- |
| u00245 | 3 | Method | raw_formula_text | False | to MSCRED. It passes the time-series through a CNN with the out- |
| u00252 | 3 | Method | raw_formula_text | False | attention-based network architectures to improve training speeds. |
| u00259 | 3 | Method | raw_formula_text | False | uses attention-based forecasting and deviation scoring to output |
| u00268 | 3 | Method | raw_formula_text | False | to natural-language log data and not appropriate for generic con- |
| u00271 | 3 | Method | raw_formula_text | False | DAGMM, OmniAnomaly, MSCRED, MAD-GAN, USAD, MTAD- |
| u00287 | 3 | Method | raw_formula_text | False | T = {𝑥1, . . . ,𝑥𝑇}, |
| u00294 | 3 | Method | raw_formula_text | False | training series, we need to predict Y = {𝑦1, . . . ,𝑦ˆ𝑇}, where we use |
| u00295 | 3 | Method | raw_formula_text | False | 𝑦𝑡∈{0, 1} to denote whether the datapoint at the 𝑡-th timestamp |
| u00298 | 3 | Method | raw_formula_text | False | we need to predict Y = {𝑦1, . . . ,𝑦ˆ𝑇}, where 𝑦𝑡∈{0, 1}𝑚to denote |
| u00312 | 3 | Method | raw_formula_text | False | vector to prevent zero-division. Knowing the ranges a-priori, we |
| u00318 | 3 | Method | raw_formula_text | False | series T to a sequence of sliding windows W = {𝑊1, . . . ,𝑊𝑇}. |
| u00320 | 3 | Method | raw_formula_text | False | constant vector {𝑥𝑡, . . . ,𝑥𝑡} of length 𝐾−𝑡to maintain the window |
| u00333 | 3 | Method | raw_formula_text | False | window as anomalous, thus 𝑦𝑡= 1(𝑠𝑡≥𝐷). To calculate the |
| u00347 | 4 | Method | raw_formula_text | False | undergoes several attention-based transformations. Figure 1 shows |
| u00355 | 4 | Method | raw_formula_text | False | with modality 𝑚. We define scaled-dot product attention [51] of |
| u00357 | 4 | Method | raw_formula_text | False | Attention(𝑄, 𝐾,𝑉) = softmax |
| u00363 | 4 | Method | raw_formula_text | False | Here, the softmax forms the convex combination weights for the |
| u00366 | 4 | Method | raw_formula_text | False | stream neural network operations. Unlike traditional attention op- |
| u00367 | 4 | Method | raw_formula_text | False | eration, the scaled-dot product attention scales the weights by a |
| u00370 | 4 | Method | raw_formula_text | False | Self Attention [51] by first passing it through ℎ(number of heads) |
| u00371 | 4 | Method | raw_formula_text | False | feed-forward layers to get 𝑄𝑖, 𝐾𝑖and 𝑉𝑖for 𝑖∈{1, . . . ,ℎ}, and then |
| u00372 | 4 | Method | raw_formula_text | False | applying scaled-dot product attention as |
| u00373 | 4 | Method | raw_formula_text | False | MultiHeadAtt(𝑄, 𝐾,𝑉) = Concat(𝐻1, . . . , 𝐻ℎ), |
| u00374 | 4 | Method | raw_formula_text | False | where 𝐻𝑖= Attention(𝑄𝑖, 𝐾𝑖,𝑉𝑖). |
| u00376 | 4 | Method | raw_formula_text | False | Multi-Head Attention allows the model to jointly attend to informa- |
| u00392 | 4 | Method | raw_formula_text | False | 1 = LayerNorm(𝐼1 + MultiHeadAtt(𝐼1, 𝐼1, 𝐼1)), |
| u00398 | 4 | Method | raw_formula_text | False | Here, MultiHeadAtt(𝐼1, 𝐼1, 𝐼1) denotes the multi-head self attention |
| u00400 | 4 | Method | raw_formula_text | False | above operations generate attention weights using the input time- |
| u00408 | 4 | Method | raw_formula_text | False | modify the self-attention in the window encoder to mask the data |
| u00414 | 4 | Method | raw_formula_text | False | 2 = Mask(MultiHeadAtt(𝐼2, 𝐼2, 𝐼2)), |
| u00416 | 4 | Method | raw_formula_text | False | 2 = LayerNorm(𝐼2 + 𝐼1 |
| u00420 | 4 | Method | raw_formula_text | False | 2 + MultiHeadAtt(𝐼2 |
| u00427 | 4 | Method | raw_formula_text | False | keys by the window encoder for the attention operation using the |
| u00439 | 4 | Method | raw_formula_text | False | where 𝑖∈{1, 2} for the first and second decoder respectively. The |
| u00475 | 5 | Method | raw_formula_text | False | Phase 1 - Input Reconstruction. The Transformer model en- |
| u00476 | 5 | Method | raw_formula_text | False | ables us to predict the reconstruction of each input time-series win- |
| u00481 | 5 | Method | raw_formula_text | False | develop an auto-regressive inference style that predicts the recon- |
| u00485 | 5 | Method | raw_formula_text | False | mentioned previously, facilitates the attention network inside the |
| u00490 | 5 | Method | raw_formula_text | False | input window 𝑊∈IR𝐾×𝑚(with focus score 𝐹= [0]𝐾×𝑚) to a com- |
| u00492 | 5 | Method | raw_formula_text | False | 2 using context-based attention as |
| u00501 | 5 | Method | raw_formula_text | False | prior to modify the attention weights in the second phase and gives |
| u00504 | 5 | Method | raw_formula_text | False | “self-conditioning” in the rest of the paper. This two-phase auto- |
| u00507 | 5 | Method | raw_formula_text | False | the attention part of the Encoder in Figure 1, to generate an anomaly |
| u00555 | 5 | Method | raw_formula_text | False | to one (lines 7-8 in Alg. 1). Initially, the weight given to the re- |
| u00584 | 6 | Method | raw_formula_text | False | 𝑦𝑖= 1(𝑠𝑖≥POT(𝑠𝑖)) |
| u00593 | 6 | Method | raw_formula_text | False | input batches. Masked multi-head attention allows us to run this in |
| u00596 | 6 | Method | raw_formula_text | False | meta learning (MAML), a few-shot learning model for fast adap- |
| u00609 | 6 | Unknown | raw_formula_text | False | The meta-optimization is performed with a meta step-size 𝛽, over |
| u00642 | 6 | Experiments | raw_formula_text | False | 𝑦𝑖= 1(𝑠𝑖≥POT(𝑠𝑖)), |
| u00649 | 6 | Experiments | raw_formula_text | False | Impact of Attention and Focus Scores. Figure 3 visualizes |
| u00650 | 6 | Experiments | raw_formula_text | False | the attention and focus scores for the TranAD model trained on the |
| u00652 | 6 | Experiments | raw_formula_text | False | average attention weights for each window (averaged over multiple |
| u00658 | 6 | Experiments | raw_formula_text | False | higher attention weights to the specific dimensions of the time- |
| u00664 | 6 | Experiments | raw_formula_text | False | We compare TranAD with state-of-the-art models for mutlivari- |
| u00665 | 6 | Experiments | raw_formula_text | False | ate time-series anomaly detection, including MERLIN [37], LSTM- |
| u00668 | 6 | Experiments | raw_formula_text | False | USAD [4], MTAD-GAT [62], CAE-M [61] and GDN [14] (with graph |
| u00675 | 6 | Method | raw_formula_text | False | https://github.com/khundman/telemanom, |
| u00677 | 6 | Method | raw_formula_text | False | https://gitee. |
| u00678 | 6 | Method | raw_formula_text | False | com/opengauss/openGauss-AI, |
| u00680 | 6 | Method | raw_formula_text | False | https://github.com/tnakae/DAGMM, |
| u00682 | 6 | Method | raw_formula_text | False | https://github.com/NetManAIOps/OmniAnomaly, |
| u00684 | 6 | Method | raw_formula_text | False | https://github.com/7fantasysz/MSCRED, |
| u00686 | 6 | Method | raw_formula_text | False | https://github.com/ |
| u00702 | 7 | Appendix | raw_formula_text | False | Attention scores |
| u00711 | 7 | Appendix | raw_formula_text | False | Figure 3: Visualization of focus and attention scores. |
| u00712 | 7 | Appendix | raw_formula_text | False | deep-learning based approaches have already been shown to out- |
| u00722 | 7 | Appendix | raw_formula_text | False | • Number of layers in feed-forward unit of encoders = 2 |
| u00730 | 7 | Appendix | raw_formula_text | False | the OmniAnomaly baseline [45]. The only dataset-specific hyperpa- |
| u00731 | 7 | Appendix | raw_formula_text | False | rameter is the number of heads in multi-head attention, which was |
| u00845 | 8 | Experiments | raw_formula_text | False | machine-1-1, 2-1, 3-2 and 3-7. |
| u00846 | 8 | Experiments | raw_formula_text | False | (9) Multi-Source Distributed System (MSDS) Dataset: This is a re- |
| u00847 | 8 | Experiments | raw_formula_text | False | cent high-quality multi-source data composed of distributed |
| u00853 | 8 | Experiments | raw_formula_text | False | claimed to suffer from mislabeling and run-to-failure bias [55]. |
| u00862 | 8 | Experiments | raw_formula_text | False | and the rest as the test set), and call these AUC* and F1* respectively, |
| u00882 | 8 | Experiments | raw_formula_text | False | AUC, F1, AUC* and F1* scores for TranAD and baseline models for |
| u00899 | 8 | Method | raw_formula_text | False | in AUC* scores over the state-of-the-art baseline models. |
| u00901 | 8 | Method | raw_formula_text | False | not require any training data; hence, we report F1* and AUC* as |
| u00926 | 8 | Method | raw_formula_text | False | Recent models such as USAD, MTAD-GAT and GDN use atten- |
| u01413 | 9 | Method | raw_formula_text | False | does this using self-attention and performs better than GDN overall |
| u01417 | 9 | Method | raw_formula_text | False | self-conditioning on an embedding of the complete trace with posi- |
| u01418 | 9 | Method | raw_formula_text | False | tion encoding aids temporal attention, thanks to the transformer |
| u01424 | 10 | Method | raw_formula_text | False | best F1* and AUC* scores are highlighted in bold. |
| u01702 | 10 | Method | raw_formula_text | False | based on the Wilcoxon pair-wised signed-rank test (with 𝛼= 0.05) |
| u01712 | 10 | Experiments | raw_formula_text | False | individually. Multi-head attention in TranAD allows it to attend |
| u01964 | 11 | Method | raw_formula_text | False | the TranAD model without the transformer-based encoder-decoder |
| u01968 | 11 | Method | raw_formula_text | False | the adversarial loss, i.e., a single-phase inference and only the re- |
| u01972 | 11 | Experiments | raw_formula_text | False | • Replacing the transformer-based encoder-decoder has the high- |
| u01975 | 11 | Experiments | raw_formula_text | False | ing the need for the attention-based transformer for large-scale |
| u02062 | 12 | Experiments | raw_formula_text | False | Table 6: Ablation Study - F1 and F1* scores for TranAD and |
| u02088 | 12 | Method | raw_formula_text | False | w/o self-condition |
| u02133 | 12 | Method | raw_formula_text | False | w/o self-condition |
| u02178 | 12 | Method | raw_formula_text | False | w/o self-condition |
| u02247 | 13 | Conclusion | raw_formula_text | False | up to 75% of the detected anomalies, higher than the state-of-the-art |
| u02260 | 13 | Method | raw_formula_text | False | GitHub under BSD-3 licence at https://github.com/imperial- |
| u02276 | 13 | Experiments | raw_formula_text | False | values as (MinL, MaxL) = {(10, 40), (50, 60), (60, 100), (70, 100), (30, |
| u02280 | 13 | Experiments | raw_formula_text | False | https://sites.google.com/view/merlin-find-anomalies/ |
| u02482 | 14 | Experiments | raw_formula_text | False | We calculate the deviation as (𝑦−𝑥)/𝑥. The table shows that our im- |
| u02529 | 14 | Method | raw_formula_text | False | //www.cs.ucr.edu/~eamonn/time_series_data_2018/. |
| u02533 | 14 | Method | raw_formula_text | False | [15] Chelsea Finn, Pieter Abbeel, and Sergey Levine. 2017. Model-agnostic meta- |
| u02546 | 14 | Method | raw_formula_text | False | State-of-the-Art. Knowledge-Based Systems 212 (2021), 106622. |
| u02573 | 14 | Method | raw_formula_text | False | Time-Series Anomaly Detection Competition. In ACM SIGKDD International Con- |
| u02574 | 14 | Method | raw_formula_text | False | ference on Knowledge Discovery and Data Mining. https://compete.hexagon- |
| u02575 | 14 | Method | raw_formula_text | False | ml.com/practice/competition/39/. |
| u02611 | 14 | Method | raw_formula_text | False | AI-powered analytics. In European Conference on Service-Oriented and Cloud |
| u02614 | 14 | Method | raw_formula_text | False | detector for robot-assisted feeding using an LSTM-based variational autoencoder. |
| u02643 | 15 | Method | raw_formula_text | False | [47] Luan Tran, Min Y Mun, and Cyrus Shahabi. 2020. Real-time distance-based |
| u02658 | 15 | Method | raw_formula_text | False | Aidan N Gomez, Łukasz Kaiser, and Illia Polosukhin. 2017. Attention is all you |
| u02665 | 15 | Method | raw_formula_text | False | //webscope.sandbox.yahoo.com/catalog.php?datatype=s&did=70. |
| u02667 | 15 | Method | raw_formula_text | False | cessed: 2021-08-31. |
| u02694 | 15 | Method | raw_formula_text | False | Deep Anomaly Detection for Multi-Sensor Time-Series Signals. IEEE Transactions |
| u02698 | 15 | Method | raw_formula_text | False | anomaly detection via graph attention network. International Conference on Data |
| u02701 | 15 | Method | raw_formula_text | False | Eamonn Keogh. 2018. Matrix profile XI: SCRIMP++: time series motif discovery |
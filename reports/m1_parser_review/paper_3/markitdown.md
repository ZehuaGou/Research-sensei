An Encode-then-Decompose Approach to
Unsupervised Time Series Anomaly Detection on
Contaminated Training Data–Extended Version
Buang Zhang1, Tung Kieu2, Xiangfei Qiu1, Chenjuan Guo1, Jilin Hu1
Aoying Zhou1, Christian S. Jensen2, Bin Yang1
1School of Data Science & Engineering, East China Normal University, Shanghai, China
2Department of Computer Science, Aalborg University, Aalborg, Denmark
1{buazhang, xfqiu}@stu.ecnu.edu.cn, 1{cjguo, jlhu, ayzhou, byang}@dase.ecnu.edu.cn, 2{tungkvt,csj}@cs.aau.dk
Abstract—Timeseriesanomalydetectionisimportantinmod- Stable features Auxiliary features
ern large-scale systems and is applied in a variety of domains Reconstructed
time series
to analyze and monitor the operation of diverse systems. Unsu-
Decomposer
pervised approaches have received widespread interest, as they
Stable Auxiliary
do not require anomaly labels during training, thus avoiding Decoder features features Anomaly Scores:
potentially high costs and having wider applications. Among Reconstruct module module Mutual information
Decompose these, autoencoders have received extensive attention. They use
reconstruction errors from compressed representations to define
Bottleneck
Representation Anomaly Scores:
anomaly scores. However, representations learned by autoen- Reconstruct error Hidden Representation
coders are sensitive to anomalies in training time series, causing Compress Encode (w/o compression)
reduced accuracy. We propose a novel encode-then-decompose Encoder Encoder
paradigm, where we decompose the encoded representation
into stable and auxiliary representations, thereby enhancing
the robustness when training with contaminated time series. In Time series Time series
addition, we propose a novel mutual information based metric
to replace the reconstruction errors for identifying anomalies. (a) Autoencoders (AE) (b) Encode-then-Decompose Anomaly Detection (EDAD)
Our proposal demonstrates competitive or state-of-the-art per- Figure 1: Autoencoders (AE) vs. Encode-then-Decompose Anomaly
formance on eight commonly used multi- and univariate time Detection (EDAD).
series benchmarks and exhibits robustness to time series with
different contamination ratios.
I. INTRODUCTION existing “shallow” methods based on similarity search [9],
Time-ordered data, known as time series, from a variety [11],[56]anddensity-basedclustering[14].Amongtheneural
of embedded sensors has become the foundation for the networkbasedmethods,acommonlyusedparadigmadoptsan
continuous monitoring and management of large-scale sys- encoder-decoder mechanism, that first compresses time series
tems across a variety of domains such as healthcare [70], into a compact, hidden representation, and then reconstructs
finance [4], logistics [78], manufacturing [71], and natural thetimeseriesfromthehiddenrepresentation,asillustratedin
sciences [33]. Time series anomaly detection, an important Figure 1(a). This paradigm employs a so-called autoencoder
branch of time series analysis, constitutes fundamental func- (AE) [42], which imposes an information bottleneck [1] that
tionalityindataanalytics,datamanagement,anddatamining. encourages the compact latent representation to capture only
Timeseriesanomalydetectionisreceivingincreasingattention themostrepresentativepatternsoftheinputtimeseries,while
in academia and industry, with numerous applications that disregarding fluctuations in the time series. Although autoen-
include system maintenance [53], network intrusion moni- coders achieve impressive accuracy, they face the following
toring [55], and credit card fraud detection [74]. The lack two limitations.
of labeled data and the diversity of anomalies combine to Compress-then-Reconstruct paradigm: AEs employ a
make the problem of identifying anomalies challenging and Compress-then-Reconstruct paradigm, as shown in Fig-
to limit the applicability of methods that require supervision. ure 1(a). The training time series T are often required to be
This has spurred research on unsupervised methods, leading fully clean, i.e., without anomalies, such that the bottleneck
to promising results. representation captures the most essential, normal patterns.
Recent neural network based methods for time series When the training time series includes anomalies, they may
anomaly detection achieve strong performance on challenging pollute the bottleneck representation such that it also captures
datasets [26]. These methods are able to learn long-term, anomalous patterns, thus adversely affecting anomaly detec-
nonlinear temporal relationships in the data, outperforming tion,i.e.,causingsomeanomaliestohavesmallreconstruction
1
5202
tcO
12
]GL.sc[
1v89981.0152:viXra

Table I: Comparison of Autoencoder vs. Encode-then-Decompose
original temporal dependencies [79]. The proposed deep de-
Anomaly Detection, where MI denotes mutual information.
compositionisachievedbyanoveldesignofshufflestrategies
AutoEncoder EDAD along the time dimension, i.e., randomly changing the time
orderoftheelementsinlearnedrepresentations.Consequently,
Paradigm Compress-then-Reconstruct Encode-then-Decompose
shufflingtheorderofdatapointsinthislatentspaceeffectively
OutlierScores ReconstructionErrors MI(Y,Yaux)
corresponds to shuffling their order in the original data, albeit
TrainingLoss ReconstructionErrors MI(Y,Ysta)+Closeness
indirectly. More specifically, the features that are insensitive
TrainingData CleanTimeSeries ContaminatedTimeSeries
to shuffling are stable features, whereas the features that are
sensitive to shuffling are auxiliary features. This implies that
stable features exhibit consistent patterns over time and are
errors.Amorerobustparadigmthatisabletobetterdealwith
not prone to unpredictable fluctuations. In contrast, auxiliary
contaminated training data is desirable.
featuresaresensitivetotemporalorder,makingthemeffective
Symmetric design of loss functions and anomaly scores: for capturing localized, short-term patterns, and noise in the
The Compress-then-Reconstruct paradigm often uses a sym- time series. This design is fully unsupervised and parameter-
metric design of the training loss functions and anomaly free, thus enabling unsupervised anomaly detection when
scores, i.e., both rely on reconstruction errors. This works training with unlabeled, contaminated time series data.
well if the training data is clean. However, this symmetric Asymmetric design of loss functions and anomaly scores:
design is problematic when training with contaminated time The proposed Encode-then-Decompose paradigm’s decompo-
series. Specifically, during training, we still aim to minimize sition of time series representations into stable features and
the reconstruction errors between the input time series T and auxiliary features facilitates an asymmetric design. Instead
the reconstructed time series Tˆ. If T already includes anoma- of using reconstruction errors, we use mutual information as
lies, minimizing the training loss drives the autoencoder to a novel and important metric when designing the training
learn a bottleneck representation that also captures anomalous loss and computing anomaly scores. During training, we
patterns caused by anomalies. Thus, in the testing phase, the consider two aspects to guide the framework’s learning. First,
reconstruction errors for some anomalies may be small and the auxiliary representation Y , which represents point-wise
aux
thus difficult to detect. To conclude, this symmetric design features, is sensitive to shuffling, and the stable representation
causes a problem—training with contaminated data reduces Y , which represents long-term features such as trend and
sta
the detection accuracy. This calls for means to avoid this seasonalities, is insensitive to the shuffling. Second, the stable
problem. representation, Y , and the original hidden representation
sta
To address the two limitations, we propose an Encode- beforedecomposition,Y,havelargemutualinformation.This
then-DecomposeAnomalyDetection(EDAD)framework.EDAD is because the stable representation Y captures the majority
sta
employs a novel “Encode-then-Decompose” paradigm with of the normal patterns in Y according to our definition of
an asymmetric design of loss functions and anomaly scores, stable. During testing, we use the point-wise mutual informa-
whereeffectivemutualinformationbasedmetricsareproposed tion between Y and Y to obtain anomaly scores because
aux
to enhance the robustness w.r.t. contaminated training data. Y captures unexpected variations in time series. If Y
aux
Encode-then-Decomposeparadigm: WeproposeanEncode- and Y have low mutual information, a time series point
aux
then-Decompose paradigm that aims to improve robustness to is likely to be an anomaly. In summary, the Encode-then-
trainingwithcontaminatedtimeseriesdata.Insteadofusinga Decompose paradigm facilitates separation between training
single bottleneck representation to capture the information of loss and anomaly scores, thus enabling an asymmetric design.
input time series, we decompose a single representation into Table I summarizes key differences between the existing
two—onerepresentingstablepatternsandtheotherrepresent- vs. the proposed paradigm. To the best of our knowledge,
ing auxiliary patterns. This design aims to separate abnormal this is the first study to propose a deep decomposition
patterns in contaminated time series from normal patterns, to paradigm for unsupervised time series anomaly detection
achieve better robustness than the Compress-then-Reconstruct using mutual information. In summary, the contributions of
paradigm. the paper are as follows. (i) We propose a novel Encode-
The proposed decomposition occurs in the latent represen- then-Decompose paradigm to distinguish between long-term
tation space, which we call a “deep” decomposition, whereas patterns (stable features) and short-term patterns (auxiliary
existing time series decompositions often work on the time features), thus mitigating the negative effects of training on
series themselves, which we refer to as “shallow” decom- contaminated data. (ii) We propose a latent space point-wise
positions [18], [61], [72]. Specifically, deep decomposition mutual information criterion for anomaly detection and form
separates the encoded latent representation into two com- an asymmetric pipeline with a decomposition framework to
ponents: stable features and auxiliary features. The stable improverobustness.Wealsointroduceanovellossfunctionto
features capture shared, invariant patterns across the time train the framework using mutual information. (iii) We report
series, while the auxiliary features reflect local variations on extensive experiments on eight benchmark datasets using
and noise. Importantly, the latent space–constructed through multiplemetricstoassesstheeffectivenessoftheproposaland
attention modules with linear embedding layers–preserves the offer detailed insight into its performance characteristics.
2

Therestofthepaperisorganizedasfollows.SectionIIcov- variable does not reduce the uncertainty of the other random
ers preliminaries. Section III details the proposal. Section IV variable, thus making their MI equal to 0.
reports on the experimental study, Section V covers related In this paper, we need to compute the mutual information
work, and Section VI concludes. between timestamps of time series in a latent space. Gen-
erally, the representation of timestamps in the latent space
II. PRELIMINARIES
can be considered as a high-dimensional vector. Classical
A. Time Series mutualinformationestimationmethodsareintractableforsuch
vectors [30]. The estimation of mutual information on large-
A time series T = ⟨s ,s ,...,s ⟩ is a sequence of N
1 2 N
time-ordered observations, where each observation s ∈ RD scale data or high-dimensional variables remains challenging.
i
is collected at a specific time step. If D =1, T is univariate. With the recent advances in mutual information estima-
If D >1, T is multivariate (or multidimensional). tion, accurate estimators of mutual information between high-
dimensionalvariablesareavailable.Byintroducingvariational
B. Time Series Anomaly Detection bounds and inequalities, the problem of directly estimating
Given a time series T = ⟨s ,s ,...,s ⟩, we aim at density ratios has been transformed into estimating an opti-
1 2 N
computing an anomaly score AS(s ) for each observation s mization problem.
i i
such that the higher AS(s ) is, the more likely it is that s is Specifically,wecanusethefollowingunnormalizedversion
i i
an anomaly. We focus on the unsupervised anomaly detection of the Barber and Agakov approximation I UBA (X,Y) to
problem, as no labels (neither for anomalies nor for normal approximatethemutualinformationI(X,Y)betweenrandom
data) are used during training. This follows the definition variables X and Y [52].
of “unsupervised” commonly adopted in prior studies [26],
[58], [75]. In contrast, semi-supervised anomaly detection I (X,Y)≜E [logq(x|y)]+h(X)
UBA p(x,y)
assumes access to a small number of labeled normal and/or
=E [logp(x)−logZ(y)+f(x,y)]+h(X)
anomalous instances, which is not the case in our work. p(x,y)
Further, we make no assumptions about whether anomalies =E p(x,y) [f(x,y)]−E p(y) [logZ(y)]
(2)
are point or collective anomalies. If the anomaly scores of
Here,h(X)=−E [log(p(x))]isthedifferentialentropyof
continuous observations are high, these observations can be p(x)
X,Z(y)=E
(cid:2) ef(x,y)(cid:3)
,andq(x|y)denotestheconditional
considered as a collective anomaly. As discussed in Section I, p(x)
probability of X given Y, which is defined as follows.
in the Compress-then-Reconstruct paradigm, reconstruction
errors are used as anomaly scores; in the proposed Encode-
p(x)
then-Decompose paradigm, latent space point-wise mutual q(x|y)= ef(x,y) (3)
Z(y)
information between an encoded representation and auxiliary
features is used for defining anomaly scores, which we will Here, q(x|y) is considered as an energy function in sys-
detail in Section III. tem[13],ef(x,y) isatiltingfunction,f(x,y):X×Y →Risa
criticfunctionaimingtodistinguishwhetherthexandy come
C. MutualInformationEstimationforHigh-DimensionalData
from the same joint distribution, and Z(y) is the associated
Mutual information (MI) measures the statistical depen- partition function.
dency between random variables. Formally, given random
If we use different techniques to deal with the factor in
variables X and Y, the MI between X and Y, denoted as
Equation 2, we get a variety of different variational mu-
I(X,Y), is defined as follows. tual information estimators, including MINE [7], NWJ [7],
(cid:88) (cid:88)
(cid:18) P(x,y) (cid:19) InfoNCE [66], and JSD [22].
I(X,Y)= P(x,y)log (1)
P(x)P(y)
x∈Xy∈Y
III. METHODOLOGY
Here,P(x,y)indicatethejointdistribution,andP(x)andP(y) WefirstpresentanoverviewoftheEncode-then-Decompose
are the marginal distributions of X and Y obtained through Anomaly Detection (EDAD) framework that efficiently de-
a marginalization process. Note that in the context of time composes a learned hidden time series representation into
series, both X and Y are continuous variables. stable and auxiliary representations. Next, we present the
Conceptually, MI quantifies the amount of shared infor- objective function, which is based on representation closeness
mation between a pair of random variables, which measures and mutual information. This function aims to enable robust
the uncertainty in one variable if the knowledge of the other training, to contend settings with contaminated training data.
variable is provided, and vice versa. In other words, the
A. Framework Overview
higher the MI value is, the more information the two random
variables share—knowing one random variable thus reduces An overview of the framework is shown in Figure 2. The
the uncertainty of the other random variable to a large extent. proposed framework consists of two stages, covering offline
In contrast, if random variables X and Y are independent, training and online detection. In the offline training stage, the
they do not share any information, and knowing one random model training is performed on time series datasets that may
3

of a time series subsequences, respectively. The output of
Offline training stage
Training Equation 4 for s is H . However, for simplicity, we
EDAD t:t+B t:t+B
omit t:t+B in the following.
Time series Data
preprocessing use trained model 1) Attention Module: The reason for using attention mech-
Testing Trained Anomaly anisms is twofold. First, attention mechanisms offer high
Online detection stage EDAD scores parallelismandtheabilitytocapturelong-rangedependencies.
Second, in contrast to AE with compression mechanisms, we
Figure 2: Framework pipeline. The data preprocessing component is aim to learn fine-grained representations for each timestamp
shared by the offline training and online detection stages.
withoutanycompressionalongthetimedimension.Theoutput
of the normalization layer is then fed to a linear embedding
layerintheattentionmodule,resultingintheprojectedvectors
already include anomalies. In the online detection stage, the
H ∈Rd.
trained model is used for detecting anomalies. emb
The data preprocessing component is shared by the offline
H =W ·H (5)
training and online detection. This component adopts an emb emb
established technique [25], [58] and applies the dimension Here,W istheweightmatrixofthelinearembeddinglayer.
emb
independencestrategy,whichisthestate-of-the-artmethodfor Subsequently, self-attention operations are performed as
time series [79]. This strategy assumes that the dimensions of follows.
a time series do not share information. Thus, it disregards
correlations between dimensions. When applying the dimen- Q=W Q ·H emb
sion independence strategy, the model is forced to capture K=W ·H
K emb
long-term temporal dependencies within each channel and
V=W ·H
preventing it from trivially inferring a variable’s value based V e (cid:18) mb Q·K⊤(cid:19) (6)
solely on other channels. Prior studies [38], [45] have also S=softmax √
reportedthattheindependence-channelsettingusuallyoutper- d
forms cross-channel modeling. In other words, the dimension Y 1 =S·V
independence strategy can be considered as a consolidation Here, W ∈ Rd×d, W ∈ Rd×d, and W ∈ Rd×d are
Q K V
and temporal augmentation method. We apply the dimension
projection matrices for query, key, and value, respectively.
independence strategy as follows. A multivariate time series
In the specific implementation, we employ a multi-head self-
T ∈ RN×D is treated as D univariate time series T ∈
j attention mechanism, assuming a total of M heads producing
RN×1,j = 1,2,...,D. The univariate time series are each
M outputs[Y1,...,YM],whereeachattentionheadoperates
standardized and partitioned into overlapping subsequences d 1 1
by using a sliding window of length B. Then, the resulting in a dimensional space. Then, the outputs of the M
M
sequences of length B, are fed into the model for training. attention heads are concatenated and projected with a linear
Here, we propose EDAD, which is explained in the following transformation, as shown in Equation 7.
parts. After training, the learned models are then employed
for online anomaly detection. Specifically, each sequence is Y 1 =W mult ·[Y 1 1,...,Y 1 M]⊤ (7)
preprocessed by the data preprocessing component and then
Here, W is a learnable parameter to conduct the linear
fedintothetrainedEDADmodelthatoutputsananomalyscore mult
transformation.
for each observation in the series.
Theoutputofmulti-headself-attentionisthenfedtoanad-
B. Network Architecture ditionandnormalizationlayertoconductaresidualconnection
and normalization as shown in Equation 8.
Weproposeanovelencoder-decomposer basedarchitecture
as the backbone of the EDAD framework, as illustrated in Y −E[Y ]
Y =Y + 1 1 ·γ +β (8)
Figure 3. 2 1 (cid:112) 2 2
Var[Y ]+ϵ
1
The framework comprises two components—an encoder
and a decomposer. The encoder encompasses an attention Here, the γ 2 and β 2 are learnable parameter vectors, E[Y 1 ]
module. The decomposer encompasses two modules— stable and Var[Y 1 ] are the expectation and variance of matrix Y 1 .
featuremoduleandauxiliaryfeaturemodule.Thepreprocessed The output of the addition and normalizing layer is fed to
time series are input into a normalizing layer to perform a multi-layer perceptron (MLP) to conduct a sequence of k
instance normalization [65], defined as follows. linear transformations. We use an MLP with two linear layers
and the ReLU activation function.
s −E[s ]
H = t:t+B t:t+B ·γ +β (4)
t:t+B (cid:112) 1 1
Var[s t:t+B ]+ϵ Y 3 =W 2 ·ReLU(W 1 ·Y 2 ) (9)
Here, the γ and β are learnable parameter vectors, and Here, W and W are the learnable weight matrices of the
1 1 1 2
E[s ] and Var[s ] are the expectation and variance MLP.Finally,theoutputY oftheMLPisfedintothesecond
t:t+B t:t+B 3
4

|     |     |     |     | Decomposer |     |     | 1   | 2   | 3 4 | 5   | 3 1 | 2   | 5 4 |     |
| --- | --- | --- | --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Mutual Information
Add & Norm
|     |     |     |     | Stable  | Auxiliary |     |     |     |     |     |     |     |     |     |
| --- | --- | --- | --- | ------- | --------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|     |     |     |     | feature | feature   |     |     |     |     |     |     |     |     |     |
|     |     |     |     | module  | module    |     |     |     |     |     |     |     |     |     |
MLP
|     |     |     |     |     |     |     | 51       | 12  | 43 24 | 35  | 13 21 | 32  | 45 54 |                                  |
| --- | --- | --- | --- | --- | --- | --- | -------- | --- | ----- | --- | ----- | --- | ----- | -------------------------------- |
|     |     |     |     |     |     |     | ytitnedI |     |       |     |       |     |       | elffuhS eludom erutaef yrailixuA |
eludom erutaef elbatS
|     | Add & Norm |     |     |     |     |     |     | Concatenate |     |     |     | Concatenate |     |     |
| --- | ---------- | --- | --- | --- | --- | --- | --- | ----------- | --- | --- | --- | ----------- | --- | --- |
Unified
|     |     |     |     |     |     | features | 5   | 1 4 2 | 3 1 2 3 | 4 5 | 1 2 3 | 4 5 3 | 1 2 5 4 |     |
| --- | --- | --- | --- | --- | --- | -------- | --- | ----- | ------- | --- | ----- | ----- | ------- | --- |
Self-attention
|     |     |     |     |     |     |     |     | Shuffle | Identity |     | Identity | Shuffle |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ------- | -------- | --- | -------- | ------- | --- | --- |
Attention module
Q     K     V
Normalization
|     |     |     |     |     |     |     | 1   | 2   | 3 4 | 5   | 1 2 | 3   | 4 5 |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Encoder
Linear embedding
|     |     |     |     |     |     |     |     |     | 1   | 2 3 | 4   | 5   |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Time series subsequences
Unified features
(a) Attention Module (b) EDAD Achitecture (c) Stable Feature and Auxiliary Feature Modules
|     |     |     |     |     |     | Figure 3: | EDAD overview. |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --------- | -------------- | --- | --- | --- | --- | --- | --- | --- |
addition and normalization layer, where the computation is and the stable module.
similar to that in the first addition and normalization layer, to AuxiliaryModule:Intheauxiliarymodule,weapplyaniden-
obtain Y (see Equation 8). tityoperationtoY sta andperformashuffleoperationonY aux .
2) StableandAuxiliaryFeatureModules: Theoutputofthe Since the auxiliary features contain information related to
|           |         |     |                |      |     |                 | specific | timestamps, |     | the shuffling |     | of auxiliary | features | affects |
| --------- | ------- | --- | -------------- | ---- | --- | --------------- | -------- | ----------- | --- | ------------- | --- | ------------ | -------- | ------- |
| attention | module, | Y,  | is partitioned | into | two | parts, and each |          |             |     |               |     |              |          |         |
part is fed into one of the two modules–the stable feature the final output sequence. Thus, we apply a shuffle operation
|        |     |               |     |                 |     |                 | to the | input | feature | Y,  | and the | auxiliary | features | Y to |
| ------ | --- | ------------- | --- | --------------- | --- | --------------- | ------ | ----- | ------- | --- | ------- | --------- | -------- | ---- |
| module | and | the auxiliary |     | feature module. |     | Stable features |        |       |         |     |         |           |          | aux  |
capture shared, invariant information across the time series, maintain consistency. By doing so, we aim to emphasize that
while auxiliary features capture local variations and noise. theauxiliaryfeaturesarestronglyaffectedbyshufflingbecause
|        |      |             |     |          |     |     | auxiliary | features | are | associated |     | with individual | data | points. |
| ------ | ---- | ----------- | --- | -------- | --- | --- | --------- | -------- | --- | ---------- | --- | --------------- | ---- | ------- |
| Figure | 3(c) | shows these | two | modules. |     |     |           |          |     |            |     |                 |      |         |
More specifically, Y = [Y ,Y ], where Y ∈ RB×d When we modify the order of data points, we emphasize
|     |     |     |     | sta aux |     | sta | 2   |     |     |     |     |     |     |     |
| --- | --- | --- | --- | ------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
∈RB×d the prominent features of every single data point. Due to the
| andY |     | 2 representtheseparatedrepresentationsthat |     |     |     |     |     |     |     |     |     |     |     |     |
| ---- | --- | ------------------------------------------ | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
aux
willbefedintothestableandauxiliarymodules,respectively. complementarynatureofstablefeaturesandauxiliaryfeatures,
|                  |             |               |               |           |              |                 | we concatenate |        | the     | two         | types of | features | and project     | the    |
| ---------------- | ----------- | ------------- | ------------- | --------- | ------------ | --------------- | -------------- | ------ | ------- | ----------- | -------- | -------- | --------------- | ------ |
| To               | facilitate  | the model’s   |               | effective | learning     | of these two    |                |        |         |             |          |          |                 |        |
|                  |             |               |               |           |              |                 | concatenated   |        | feature | space       | back     | to the   | original latent | space. |
| representations, |             | we            | have designed | both      | the          | stable feature  |                |        |         |             |          |          |                 |        |
|                  |             |               |               |           |              |                 | This           | way, Y | aux can | capture     | rapidly  | changing | features.       |        |
| module           | and         | the auxiliary | feature       | module.   | The          | stable features |                |        |         |             |          |          |                 |        |
| of a             | time series | are           | the features  | that      | span many    | time steps      |                |        |         |             |          |          |                 |        |
|                  |             |               |               |           |              |                 |                |        | YI      | =identity(Y |          | )        |                 |        |
|                  |             |               |               |           |              |                 |                |        | sta     |             |          | sta      |                 |        |
| to represent     |             | long-term     | patterns      | of the    | time series. | In contrast,    |                |        |         |             |          |          |                 |        |
|                  |             |               |               |           |              |                 |                |        | YS      | =shuffle(Y  |          | )        |                 | (10)   |
the auxiliary features of a time series are the features that aux aux
only span a few time steps to represent short-term patterns or Yˆ =concat(YI ,YS )·W
|           |           |                |              |             |                 |              |           |         | aux       |                 | sta              | aux  | p             |      |
| --------- | --------- | -------------- | ------------ | ----------- | --------------- | ------------ | --------- | ------- | --------- | --------------- | ---------------- | ---- | ------------- | ---- |
| changes   | in        | individual     | observations | of          | the time        | series.      |           |         |           |                 |                  |      |               |      |
|           |           |                |              |             |                 |              | Then,     | we      | formulate | the             | auxiliary        | loss | that measures | the  |
| To        | be able   | to distinguish |              | between     | stable features | and the      |           |         |           |                 |                  |      |               |      |
|           |           |                |              |             |                 |              | closeness | between | the       | two             | representations, |      | as follows.   |      |
| auxiliary | features, | we             | first        | define two  | operations—a    | shuffle      |           |         |           |                 |                  |      |               |      |
| operation | and       | an identity    | operation,   | which       | are             | used in both |           |         |           |                 |                  |      |               |      |
|           |           |                |              |             |                 |              |           |         | L         | =∥shuffle(Y)−Yˆ |                  |      | ∥2            | (11) |
|           |           |                |              |             |                 |              |           |         | aux       |                 |                  |      | aux F         |      |
| modules.  | The       | shuffle        | operation,   | shuffle(·), | performs        | random       |           |         |           |                 |                  |      |               |      |
shuffling along the time dimension. The identity operation, StableModule:Bydefinition,stablefeaturesremainrelatively
identity(·), represents no change to the input. The shuffle stable over a long period. Therefore a random perturbation
operation is applied along the time dimension within each of the stable features at a particular timestamp i, denoted
subsequence window, while all feature dimensions are treated as YS , should be interchangeable with its pre-perturbation
sta,i
separately. This ensures that the temporal order of data points stable feature Y sta,i . Therefore, in the stable feature module,
is manipulated, allowing us to distinguish between stable fea- weonlyshuffleY whilekeepingY unchanged.Bydoing
|     |     |     |     |     |     |     |     |     | sta |     |     | aux |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
tures(insensitivetoshuffling)andauxiliaryfeatures(sensitive this,weaimtoemphasizethatthestablefeaturesarepersistent
toshuffling).Weproceedtoelaborateontheauxiliarymodule andcannotbechangedbyshufflingbecausetheyarecontained
5

inlongsequences.Finally,afterconcatenatingthesetwotypes this distribution. Second, this can be seen as introducing the
of features, we apply a projection to obtain the projected maximization of MI into representation learning, a principle
Yˆ
representation . used widely [8], [22]. This approach effectively prevents
sta
|     |     |     |            |     |     |     |     |     | the model | from learning | trivial | features. |     | Third, | it adds the |
| --- | --- | --- | ---------- | --- | --- | --- | --- | --- | --------- | ------------- | ------- | --------- | --- | ------ | ----------- |
|     |     | Y S | =shuffle(Y |     | )   |     |     |     |           |               |         |           |     |        |             |
s ta sta critic function f (·) into the training process. This function
θ
YI =identity(Y ) (12) is considered as a contrastive loss to provide self-supervisory
|     |     | aux |            |     | aux |     |     |     |             |              |     |     |     |     |     |
| --- | --- | --- | ---------- | --- | --- | --- | --- | --- | ----------- | ------------ | --- | --- | --- | --- | --- |
|     |     | Yˆ  | =concat(YS |     | ,YI |     |     |     | information | to the loss. |     |     |     |     |     |
|     |     | sta |            |     |     | )·W | p   |     |             |              |     |     |     |     |     |
sta aux
|           |           |                 |          |          |                     |                  |     |          | C. Regularization |                |          |        |               |     |              |
| --------- | --------- | --------------- | -------- | -------- | ------------------- | ---------------- | --- | -------- | ----------------- | -------------- | -------- | ------ | ------------- | --- | ------------ |
| The       | stable    | feature         | module   | lacks    | the                 | self-supervisory |     | in-      |                   |                |          |        |               |     |              |
|           |           |                 |          |          |                     |                  |     |          | We observe        | that both      | the      | stable | and auxiliary |     | feature mod- |
| formation |           | (i.e., shuffle) |          | compared | to                  | the auxiliary    |     | module,  |                   |                |          |        |               |     |              |
|           |           |                 |          |          |                     |                  |     |          | ules are          | parameterized. | Further, |        | both modules  |     | are fed the  |
| which     | considers | the             | shuffled | Y        | as self-supervisory |                  |     | informa- |                   |                |          |        |               |     |              |
tion. Using a loss function like the one used in the auxiliary output of the encoder, i.e., the stable features and auxiliary
|        |           |     |     |       |                |     |             |     | features. | As a result, | both | modules | share | the parameters | of  |
| ------ | --------- | --- | --- | ----- | -------------- | --- | ----------- | --- | --------- | ------------ | ---- | ------- | ----- | -------------- | --- |
| module | (Equation |     | 11) | makes | it susceptible |     | to learning |     | a         |              |      |         |       |                |     |
theencoderforlearning.However,thesetwotypesoffeatures
| trivial | solution  | that | simply | copies | Y, resulting |        | in meaningless |         |                                                         |     |     |     |     |     |     |
| ------- | --------- | ---- | ------ | ------ | ------------ | ------ | -------------- | ------- | ------------------------------------------------------- | --- | --- | --- | --- | --- | --- |
|         |           |      |        |        |              |        |                | infomax | representapproximatelyorthogonalobjectives,whichcaneas- |     |     |     |     |     |     |
| stable  | features. | To   | avoid  | this   | issue, we    | follow | the            |         |                                                         |     |     |     |     |     |     |
ilyleadtoconflictingparameterupdates[51].Weaddressthis
principle[8],tomaximizethemutualinformationbetweenthe
inputandoutput.Specifically,Y containsthenormalmodes challenge by introducing a teacher–student architecture that
sta
servesasaformofconsistencyregularization[32].Thisdesign
| of Y,        | so they | should  | have        | a   | substantial | amount   |         | of shared |            |            |         |            |     |     |             |
| ------------ | ------- | ------- | ----------- | --- | ----------- | -------- | ------- | --------- | ---------- | ---------- | ------- | ---------- | --- | --- | ----------- |
|              |         |         |             |     |             |          |         |           | encourages | the shared | encoder | parameters |     | to  | evolve more |
| information. |         | We then | incorporate |     | the         | training | process | of the    |            |            |         |            |     |     |             |
mutual information estimator into the stable feature module smoothly and coherently, despite the presence of competing
learningsignals.Figure4illustratestheregularizationprocess.
| to advocate |     | maximizing |     | the mutual | information |     | between | Y   |     |     |     |     |     |     |     |
| ----------- | --- | ---------- | --- | ---------- | ----------- | --- | ------- | --- | --- | --- | --- | --- | --- | --- | --- |
EDAD,
and Y , denoted as I (Y,Y ). The final loss of the stable Specifically, we make two copies of where the decom-
|         | sta    |     | θ            | sta |          |             |     |     |              |              |           |             |        |             |          |
| ------- | ------ | --- | ------------ | --- | -------- | ----------- | --- | --- | ------------ | ------------ | --------- | ----------- | ------ | ----------- | -------- |
|         |        |     |              |     |          |             |     |     | poser is     | disabled and | only      | the encoder | is     | enabled,    | to serve |
| feature | module | is  | then defined |     | as shown | in Equation |     | 13. |              |              |           |             |        |             |          |
|         |        |     |              |     |          |             |     |     | as a teacher | model and    | a student |             | model. | The student | model    |
=∥Y−Yˆ ∥2 is updated directly via gradient descent and is responsible for
|     |     | L sta |     | sta | −I θ | (Y,Y | sta ) | (13) |     |     |     |     |     |     |     |
| --- | --- | ----- | --- | --- | ---- | ---- | ----- | ---- | --- | --- | --- | --- | --- | --- | --- |
F learning from the data at each training step [54]. In contrast,
|       | I (·) |        |        |             |           |     |               |     | theteachermodelmaintainsanexponentialmovingaverageof |     |     |     |     |     |     |
| ----- | ----- | ------ | ------ | ----------- | --------- | --- | ------------- | --- | ---------------------------------------------------- | --- | --- | --- | --- | --- | --- |
| Here, | θ     | is the | mutual | information | estimator |     | parameterized |     |                                                      |     |     |     |     |     |     |
byθ.Wecanchooseaspecificestimatoramongmanyexisting thestudent’sparameters[59].Thisdesignprovidesasmoother
ones. We choose InfoNCE as defined in Equation 14 as the andmorestablerepresentationspacethatreducesthevariance
default estimator due to its excellent performance as reported introducedbyfrequentstudentupdates,therebyimprovingthe
in recent studies [7], [22]. Later, we compare it empirically reliability of mutual information estimation. We use ω and
with other estimators (see Section IV-C2). ψ to represent the parameters of the student model and the
|     |     |           |     |      |         |     |                |     | teacher         | model, respectively. |        | When | computing | the            | consistency |
| --- | --- | --------- | --- | ---- | ------- | --- | -------------- | --- | --------------- | -------------------- | ------ | ---- | --------- | -------------- | ----------- |
|     |     |           |     |      |         |     |                |     | regularization, | we directly          | obtain | the  | projected | representation |             |
|     | =E  |           |     |      | )]−E    | [E  | [efθ(Y,Ysta)]] |     |                 |                      |        |      |           |                |             |
| I   |     | P(Y,Ysta) | [f  | (Y,Y | P(Ysta) |     | P(Y)           |     |                 |                      |        |      |           | Y′             |             |
InfoNCE θ sta from the output representation of the encoder through the
(14)
|     |     |     |     |     |     |     |     |     | projection | matrix W | . The | consistency | regularization |     | for the |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---------- | -------- | ----- | ----------- | -------------- | --- | ------- |
p
Here,f θ (Y,Y sta )isseparablecriticfunctiondefinedasshown student model and the teacher model is computed as shown
| in Equation |     | 15.    |     |     |       |       |     |      |             |       |      |     |      |     |      |
| ----------- | --- | ------ | --- | --- | ----- | ----- | --- | ---- | ----------- | ----- | ---- | --- | ---- | --- | ---- |
|             |     |        |     |     |       |       |     |      | in Equation | 16.   |      |     |      |     |      |
|             |     | f (Y,Y |     | )=ϕ | (Y)⊤ϕ | (Y    | ),  | (15) |             | L =∥Y | ′ ·W | −Y  | ′ ·W | ∥2  |      |
|             |     | θ      | sta | θ   |       | θ sta |     |      |             | reg   | ω    | p   | ψ    | p F | (16) |
where ϕ (·) is a non-linear transformation function such as a Here, Y′ represents the output representation of the student
|     | θ   |     |     |     |     |     |     |     |     | ω   |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
feed-forward neural network. model, and Y′ represents the output representation of the
ψ
By proposing the loss function in Equation 13, we aim to teacher model. This way, EDAD is enabled to utilize highly
achieve three targets. First, the MI measures the statistical shared weights to partition the features of the time series
dependency between latent representations and input data, into two parts, thereby increasing the robustness of the model
| offering    | greater   | robustness |          | to         | the separation |           | of the         | stable   | training.      |                |        |          |            |                |           |
| ----------- | --------- | ---------- | -------- | ---------- | -------------- | --------- | -------------- | -------- | -------------- | -------------- | ------ | -------- | ---------- | -------------- | --------- |
| features    | from      | the        | original | embedded   | features.      |           | Reconstruction |          |                |                |        |          |            |                |           |
|             |           |            |          |            |                |           |                |          | D. Objective   | Function       |        |          |            |                |           |
| error       | primarily | captures   |          | point-wise | deviations     |           | between        | input    |                |                |        |          |            |                |           |
|             |           |            |          |            |                |           |                |          | The            | overall loss   | is the | weighted | sum        | of the         | auxiliary |
| and output, |           | which      | can be   | unreliable | when           | anomalies |                | are par- |                |                |        |          |            |                |           |
|             |           |            |          |            |                |           |                |          | reconstruction | loss (Equation |        | 11),     | the stable | reconstruction |           |
tiallyreconstructed–especiallyinthepresenceofcontaminated
|     |     |     |     |     |     |     |     |     | loss (Equation | 13), and | the | regularization |     | (Equation | 16). |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | -------------- | -------- | --- | -------------- | --- | --------- | ---- |
trainingdata.TheMIcanavoidthestablefeaturesconverging
| into   | the contamination |               | representation |         | by         | also | considering  | the |     |       |           |      |        |          |      |
| ------ | ----------------- | ------------- | -------------- | ------- | ---------- | ---- | ------------ | --- | --- | ----- | --------- | ---- | ------ | -------- | ---- |
|        |                   |               |                |         |            |      |              |     |     | L=λ 1 | ·L sta +λ | 2 ·L | aux +λ | 3 ·L reg | (17) |
| number | of                | observations. |                | Because | the number |      | of anomalies |     | is  |       |           |      |        |          |      |
small,theanomaliesevenwithlargemagnitudescannotaffect Hyperparameters λ , λ , and λ control the trade-offbetween
|     |     |     |     |     |     |     |     |     |     | 1   | 2   | 3   |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
theMIseverely.Inthiscase,Y encodesstablefeaturesofthe the objective function terms. We investigate the sensitivity to
sta
time series, and short-term anomalies are less likely to distort λ 1 , λ 2 , and λ 3 in the experimental study.
6

Optimized vector magnetograms in Spaceweather HMI Active Region
Exponential
Teacher EDAD moving Teacher EDAD Patch series; (6) KDD21 [47] is a composite dataset released
for a SIGKDD 2021 competition; (7) Numenta Anomaly
Time series Copy Consistency Benchmark(NAB)[3]compriseslabeledtimeseriesdatafrom
parameters Regularization
Gradient Optimized diverse sources, encompassing AWS server metrics, online
Student EDAD descent Student EDAD ad click rates, real-time traffic data, and Twitter mentions of
major publicly traded firms; (8) Supraventricular Arrhythmia
Figure 4: Regularization. Database (SVDB) [43] includes 78 half-hour ECG recordings
that supplement supraventricular arrhythmias in the MIT-BIH
Arrhythmia Database. The eight datasets encompass both
E. Anomaly Scores
multivariate and univariate time series. We acknowledge that
We have shaped EDAD to enforce it on learning the stable datasets such as SWaT, SMAP, and MSL have known lim-
features by augmenting the stable feature learning with the itations, including high anomaly density, inconsistent labels,
MI module. The remaining information related to individual long anomaly windows, and unrealistic distributions. These
observations and short-term patterns is maintained in the issues are discussed in TimeSeAD [68]. Nevertheless, these
auxiliary features. Therefore, the shared information between datasets are widely used in the time-series anomaly detection
the original features Y and the auxiliary features Y can literature, which motivated our decision to include them in
aux
be used to identify anomalies, which are also related to our experiments. We provide statistical information on the
individual observations and short-term patterns. This enables experimentaldatasetsinTableII,includingthedimensionality
an “asymmetric” design of the loss function used for training of each dataset, its length, and the proportion of anomalies.
and the definition of anomaly scores. 2) Baselines: We compare EDAD with thirteen strong and
Given a time series subsequence, we can calculate an well-knownanomalydetectionmethods.Tobecomprehensive,
anomaly score as the point-wise mutual information between we include neural network based anomaly detection methods
its encoded representation Y and the corresponding auxiliary as well as traditional anomaly detection methods with good
representation Y . performance and published in top venues. Specifically, we
aux
Due to the choice of different mutual information esti- include eleven methods: (1) OC-SVM [60] learns a boundary
mators, the critic function f (·) (see Equation 13) may not that encompasses the normal data while leaving anomalies
θ
necessarily be proportional to P(Y,Y aux ) when tightening outside the boundary; (2) IForest [37] uses an ensemble of
P(Y)P(Y ) isolationtreestodetectanomalies;(3)DAGMM[82]integratesa
aux
thelowerbound[63],soitcannotbeusedalonetocomputethe GMMandAEtomodelthedistributionofmultidimensionaldata;
anomaly scores. Therefore, we employ the entire estimator’s (4)Series2Graph[10]isananomalydetectionalgorithmthat
forward pass. Let I θ be the mutual information estimator transforms time series into graph structures; (5) SAND [12]
parameterizedbyθ.Then,wecancompute theanomalyscore is an anomaly detection algorithm designed for streaming
for each data point s i as follows. data. It identifies anomalous patterns by clustering input data
sequences; (6) LSTM-AD [23] uses RNNs to detect anomalies
AS(s i )=−I θ (Y,Y aux ) (18) by forecasting over long sequences of data; (7) MAD-GAN [34]
employs GAN to recognize anomalies by reconstructing test-
A high score indicates that the input Y and Y share less
aux ing samples from the latent space; (8) TranAD [64] utilizes
information. Since Y includes only short-term variations,
aux transformer models to infer anomalies by considering broader
s is more likely to be anomalous.
i temporal trends in the data; (9) GDN [19] integrates GNNs
and meta-learning with past and recent information to enable
IV. EXPERIMENTS
anomaly detection; (10) OmniAnomaly [58] integrates GRUs
A. Experimental Settings
and VAEs to learn robust representations of time series data;
1) Datasets: We conduct experiments on eight real-world (11) IMdiffusion [16] combines time series imputation and
datasets that span a wide range of domains, such as manu- diffusion models to achieve robust anomaly detection. (12)
facturing, natural sciences, and healthcare: (1) Pooled Server AnomalyTrans [76] models prior associations and series
Metrics (PSM) [2] is collected from EBAY servers and associations to capture the association discrepancies; (13)
recordstheservermonitoringmetrics;(2)SoilMoistureActive DCdetector [77] detects time series anomalies using robust
Passive (SMAP) [23] is collected by NASA and presents representationsbasedoncontrastivelearning.Notethatweuse
soil samples and telemetry information from the Mars explo- thepubliclyavailableimplementationsfromtheauthorsofthe
ration project; (3) Secure Water Treatment (SWAT) [41] is above methods.
collected from a water treatment process in an infrastructure 3) Metrics: Weusestandardmetricsforanomalydetection,
for research on cyber-security; (4) Mars Science Laboratory includingPrecision(P),Recall(R),F1-score(F1),AreaUnder
(MSL) [31] is collected by NASA and shows the state of the Precision-Recall Curve (A-PR), and Area Under the Re-
the sensors in the Mars exploration project; (5) NIPSTS- ceiver Operating Characteristic Curve (A-ROC) [36]. In addi-
SWAN (SWAN) [31] is extracted from solar photospheric tion, we report Volume-under-the-Surface of Precision-Recall
7

|     |     |     | Table II: | Dataset | statistics. |     |     |             |             |         |      |              |           |     |
| --- | --- | --- | --------- | ------- | ----------- | --- | --- | ----------- | ----------- | ------- | ---- | ------------ | --------- | --- |
|     |     |     |           |         |             |     |     | highlighted | in blue. We | observe | that | the proposed | framework |     |
Dataset Dimension AverageLength AnomalyRatio(%) achieves the top 3 highest accuracies on most datasets. Ac-
PSM 25 220,322 27.8 cording to the average results, EDAD achieves the highest P,
|     | SMAP | 25  | 562,800 |     | 12.8 |     |     |              |            |     |             |     |               |     |
| --- | ---- | --- | ------- | --- | ---- | --- | --- | ------------ | ---------- | --- | ----------- | --- | ------------- | --- |
|     |      |     |         |     |      |     |     | R, F1, V-PR, | and V-ROC, | and | it achieves | the | top 3 highest |     |
|     | SWAT | 51  | 944,919 |     | 12.0 |     |     |              |            |     |             |     |               |     |
MSL 55 132,046 10.5 A-PR and A-ROC. This indicates the strong performance of
SWAN 38 120,000 32.6 EDAD as well as significant improvements of EDAD over the
|     | KDD21 | 1   | 77,415 |     | 10.67 |     |     |            |     |     |     |     |     |     |
| --- | ----- | --- | ------ | --- | ----- | --- | --- | ---------- | --- | --- | --- | --- | --- | --- |
|     | NAB   | 1   | 6,301  |     | 2.67  |     |     | baselines. |     |     |     |     |     |     |
SVDB 1 230,400 4.68 To justify whether the accuracy improvements of the pro-
posedmethodsEDADoverthebaselinesarestatisticallysignifi-
cant,weconductt-teststotestthesignificanceoftheproposed
(V-PR) and Volume-under-the-Surface of Receiver Operating methods against baselines. We consider a null hypothesis
| Characteristic |     | (V-ROC) | [46] | to alleviate | bias | stemming | from |          |             |             |        |     |             |     |
| -------------- | --- | ------- | ---- | ------------ | ---- | -------- | ---- | -------- | ----------- | ----------- | ------ | --- | ----------- | --- |
|                |     |         |      |              |      |          |      | H 0 that | the mean of | the anomaly | scores | of  | our methods | is  |
threshold selections and provide an alternative evaluation per- similartothemeanoftheanomalyscoresofbaselines,andan
spective on anomaly detection methods, utilizing continuous alternativehypothesisH thatthemeanoftheanomalyscores
1
| buffer | regions | [47]. | Each metric |     | offers valuable | information. |     |                |              |     |          |      |                |     |
| ------ | ------- | ----- | ----------- | --- | --------------- | ------------ | --- | -------------- | ------------ | --- | -------- | ---- | -------------- | --- |
|        |         |       |             |     |                 |              |     | of our methods | is different |     | from the | mean | of the anomaly |     |
4) Implementation Details: We implement the proposed scores of baselines. After performing the t-test, we get a p-
frameworkandbaselinesbyutilizingPyTorch[49]andScikit-
value,whichissmallerthan0.001.Thisshowsstrongevidence
learn0.24[50]inPython3.10.Allexperimentswereexecuted to reject the null hypothesis H , which in turn suggests that
0
onaclusterserver,whichrunsLinuxUbuntu18.04.6LTS.The our models have statistically outperformed baselines.
serverisequippedwithanNVIDIATesla-A800GPUwithtwo
|     |     |     |     |     |     |     |     | Finally, | we acknowledge |     | that it is | unrealistic | for a | single |
| --- | --- | --- | --- | --- | --- | --- | --- | -------- | -------------- | --- | ---------- | ----------- | ----- | ------ |
64-core AMD CPUs and 512 GiB RAM. The source code is method to be able to outperform all other methods across all
available at https://github.com/zhangbububu/EDAD/. datasets and metrics. In other words, there is no one-size-
5) HyperparameterSettings: Followingrecentstudies[64], fits-all solution. Thus, it is unrealistic to expect our proposed
[76], [77], the dimensionality d of the hidden layer is set to method EDAD to outperform all baselines in all 56 testing
| 256, | the | number of | encoder | layers | is set | to 3, the | number |          |              |           |       |        |           |      |
| ---- | --- | --------- | ------- | ------ | ------ | --------- | ------ | -------- | ------------ | --------- | ----- | ------ | --------- | ---- |
|      |     |           |         |        |        |           |        | cases (8 | datasets × 7 | metrics). | Among | the 56 | cases and | when |
of heads M in the multi-head attention is set to 8, and the comparedto11othermethods,theproposedEDADisbestin26
window of the input model B is set to 100. By doing this we cases, and second-best in 9 cases, as shown in Table IV. The
ensurea similarbackbone andthe fairnessof comparison.We state-of-the-art method DCdetector is best in only 2 cases
set the anomaly ratio to 1% so that the 1% of the data points and2ndbestin18cases.TheCompress-the-Reconstructbased
withthehighestanomalyscoresareanomalies[76].Weusethe
|     |     |     |     |     |     |     |     | method | LSTM-AD is best | in  | 5 cases and | 2nd | best in 2 | cases. |
| --- | --- | --- | --- | --- | --- | --- | --- | ------ | --------------- | --- | ----------- | --- | --------- | ------ |
InfoNCE[66]withseparablecriticsasthemutualinformation This clearly shows that EDAD achieves superior performance.
| estimator. |          | In addition, | we  | use the   | Adam      | optimizer | [29] with |             |       |     |     |     |     |     |
| ---------- | -------- | ------------ | --- | --------- | --------- | --------- | --------- | ----------- | ----- | --- | --- | --- | --- | --- |
|            |          | 5×10−4       |     |           |           |           |           | C. Ablation | Study |     |     |     |     |     |
| a          | learning | rate of      |     | for model | training. | Early     | stopping  |             |       |     |     |     |     |     |
is adopted in the training process. 1) Effect of Components: We proceed to assess the effec-
To tune λ , λ , and λ , we vary each of λ , λ , and λ tiveness of each individual module in EDAD. For brevity, we
|     |     | 1 2 | 3   |     |     | 1   | 2   | 3   |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
among 0.1, 0.5, 1, 2, and 3. After getting the results for only report average results over the eight datasets, as shown
all combinations of λ , λ , and λ , we identify the median in Table V. The results show that EDAD achieves the top 3
|     |     |     | 1   | 2   | 3   |     |     |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
resultandusethecorrespondinghyperparametersettingasthe highest accuracy when all modules are fully incorporated.
defaultsetting.Wedonotusethebestresultbecause,inunsu- If we only include a single feature module, the model with
pervisedsettings,wehavenolabeleddatatoenableidentifying the auxiliary feature module (w/o stable feature module)
the best result. Further, we conduct experiments to study the can yield a better average accuracy when compared to the
sensitivity of different λ , λ , and λ in Section IV-C7. To counterpart with the stable feature module. This suggests that
|     |        |        | 1      | 2              | 3   |              |       |               |                  |     |          |         |                 |     |
| --- | ------ | ------ | ------ | -------------- | --- | ------------ | ----- | ------------- | ---------------- | --- | -------- | ------- | --------------- | --- |
| do  | so, we | vary a | chosen | hyperparameter |     | in its range | while |               |                  |     |          |         |                 |     |
|     |        |        |        |                |     |              |       | the inclusion | of the auxiliary |     | feature, | serving | as an indicator |     |
fixing the other hyperparameters to their default values. We forcalculatinganomalyscores,improvesEDAD’sperformance.
also study the effect of window size B in Section IV-C8. The regularization is less important than the stable feature
For the other baselines, we use the hyperparameter settings and the auxiliary feature modules. However, integrating the
recommended in existing studies if provided. Otherwise, we regularization into EDAD can improve the performance further.
| randomly |     | vary parameters |     | in specific | methods, | such | as the |             |               |          |            |     |                |     |
| -------- | --- | --------------- | --- | ----------- | -------- | ---- | ------ | ----------- | ------------- | -------- | ---------- | --- | -------------- | --- |
|          |     |                 |     |             |          |      |        | In summary, | the empirical | findings | underscore |     | the importance |     |
kernel degree in OC-SVM. Then, we report the median of of each module in EDAD.
multiple runs using different hyperparameters. 2) Effect of Mutual Information Estimators: We study the
|     |              |         |     |     |     |     |     | effect of  | different mutual | information |     | estimators. | This          | exper- |
| --- | ------------ | ------- | --- | --- | --- | --- | --- | ---------- | ---------------- | ----------- | --- | ----------- | ------------- | ------ |
| B.  | Experimental | Results |     |     |     |     |     |            |                  |             |     |             |               |        |
|     |              |         |     |     |     |     |     | iment aims | to characterize  | accurately  |     | the quality | of a specific |        |
1) Overall results: We report on the performance of the mutual information estimator, which, in turn, facilitates the
proposed EDAD and the baselines on all datasets in terms accuratedetectionofoutliers.TableVcomparesourdefaultes-
of all metrics—see Table III. We also report average results timator InfoNCE and the state-of-the-art estimators NWJ [44],
(see AVERAGE). The top 3 best results for each metric are MINE [7], and JSD [52]. The results show that InfoNCE
8

Table III: P, R, F1, A-PR, A-ROC, V-PR, and V-ROC of anomaly detection methods. The top three highest accuracies are highlighted in
blue, where the best and the runner-up results are in bold and underlined text, respectively.
| Method |     |     | PSM |     |     |     | SMAP |     |     |     |     | SWAT |     |
| ------ | --- | --- | --- | --- | --- | --- | ---- | --- | --- | --- | --- | ---- | --- |
P R F1 A-PR A-ROC V-PR V-ROC P R F1 A-PR A-ROC V-PR V-ROC P R F1 A-PR A-ROC V-PR V-ROC
OC-SVM 0.627 0.706 0.664 0.417 0.619 0.369 0.531 0.512 0.578 0.543 0.101 0.392 0.113 0.518 0.419 0.478 0.447 0.126 0.657 0.133 0.477
IForest 0.627 0.924 0.834 0.334 0.542 0.334 0.541 0.523 0.590 0.555 0.121 0.487 0.135 0.499 0.492 0.449 0.470 0.093 0.345 0.129 0.424
DAGMM 0.934 0.700 0.801 0.430 0.647 0.354 0.515 0.864 0.567 0.685 0.135 0.561 0.123 0.468 0.861 0.530 0.656 0.207 0.710 0.241 0.538
Series2Graph 0.906 0.893 0.899 0.546 0.471 0.313 0.512 0.903 0.689 0.782 0.114 0.584 0.137 0.492 0.855 0.809 0.831 0.161 0.280 0.247 0.392
SAND 0.931 0.861 0.895 0.415 0.479 0.401 0.542 0.927 0.826 0.874 0.154 0.455 0.146 0.502 0.867 0.713 0.782 0.142 0.343 0.179 0.463
LSTM-AD 0.769 0.896 0.828 0.537 0.714 0.523 0.526 0.894 0.781 0.833 0.142 0.579 0.122 0.458 0.861 0.832 0.846 0.094 0.405 0.101 0.250
MAD-GAN 0.986 0.772 0.866 0.524 0.687 0.451 0.601 0.678 0.603 0.638 0.103 0.423 0.118 0.459 0.791 0.542 0.643 0.139 0.317 0.113 0.350
TranAD 0.950 0.895 0.922 0.511 0.665 0.352 0.571 0.822 0.850 0.836 0.113 0.416 0.156 0.425 0.702 0.726 0.714 0.126 0.323 0.235 0.356
GDN
0.875 0.838 0.856 0.438 0.657 0.355 0.475 0.907 0.612 0.731 0.096 0.375 0.112 0.414 0.171 0.058 0.086 0.119 0.312 0.113 0.351
OmniAnomaly 0.883 0.744 0.808 0.419 0.627 0.439 0.522 0.924 0.819 0.869 0.097 0.378 0.113 0.417 0.814 0.843 0.828 0.121 0.338 0.113 0.351
IMdiffusion 0.975 0.875 0.923 0.345 0.569 0.337 0.545 0.923 0.889 0.906 0.113 0.468 0.131 0.506 0.932 0.876 0.903 0.129 0.544 0.157 0.503
AnomalyTrans 0.969 0.978 0.973 0.396 0.298 0.277 0.486 0.935 0.994 0.964 0.171 0.595 0.157 0.509 0.891 0.992 0.939 0.071 0.179 0.109 0.434
DCdetector 0.973 0.985 0.979 0.462 0.481 0.276 0.490 0.955 0.988 0.970 0.151 0.580 0.147 0.502 0.932 0.996 0.963 0.157 0.604 0.149 0.507
EDAD(ours) 0.978 0.984 0.981 0.517 0.669 0.382 0.549 0.970 0.974 0.972 0.147 0.599 0.149 0.535 0.938 1.000 0.968 0.172 0.571 0.334 0.512
|     |     |     | MSL |     |     |     | SWAN |     |     |     |     | KDD21 |     |
| --- | --- | --- | --- | --- | --- | --- | ---- | --- | --- | --- | --- | ----- | --- |
Method P R F1 A-PR A-ROC V-PR V-ROC P R F1 A-PR A-ROC V-PR V-ROC P R F1 A-PR A-ROC V-PR V-ROC
OC-SVM 0.602 0.873 0.713 0.185 0.593 0.207 0.663 0.474 0.498 0.486 0.326 0.501 0.318 0.509 0.173 0.625 0.271 0.022 0.502 0.025 0.657
IForest 0.541 0.863 0.665 0.173 0.570 0.191 0.649 0.570 0.598 0.583 0.379 0.487 0.375 0.440 0.309 0.607 0.410 0.042 0.561 0.039 0.631
DAGMM 0.894 0.637 0.744 0.159 0.566 0.171 0.650 0.436 0.391 0.412 0.471 0.472 0.349 0.403 0.213 0.558 0.308 0.015 0.698 0.032 0.621
Series2Graph 0.937 0.898 0.917 0.176 0.533 0.193 0.608 0.745 0.609 0.670 0.401 0.381 0.343 0.467 0.151 0.593 0.241 0.018 0.484 0.030 0.622
SAND
0.875 0.817 0.845 0.194 0.569 0.188 0.656 0.837 0.575 0.682 0.396 0.370 0.393 0.478 0.218 0.642 0.325 0.016 0.499 0.033 0.623
LSTM-AD 0.858 0.828 0.842 0.188 0.616 0.214 0.693 0.474 0.211 0.292 0.454 0.463 0.329 0.471 0.215 0.550 0.309 0.013 0.444 0.030 0.618
MAD-GAN 0.723 0.772 0.746 0.190 0.599 0.209 0.675 0.921 0.589 0.718 0.495 0.501 0.422 0.478 0.100 0.615 0.172 0.019 0.264 0.029 0.634
TranAD 0.890 0.931 0.910 0.193 0.515 0.217 0.578 0.939 0.579 0.716 0.477 0.499 0.311 0.382 0.097 0.595 0.167 0.036 0.327 0.030 0.623
GDN 0.933 0.687 0.791 0.191 0.603 0.211 0.674 0.928 0.528 0.735 0.485 0.474 0.424 0.478 0.102 0.615 0.175 0.015 0.276 0.028 0.631
OmniAnomaly
0.886 0.859 0.872 0.189 0.601 0.213 0.679 0.834 0.461 0.594 0.472 0.503 0.454 0.456 0.102 0.619 0.175 0.018 0.690 0.029 0.641
IMdiffusion 0.919 0.961 0.940 0.160 0.531 0.179 0.594 0.932 0.566 0.597 0.292 0.481 0.429 0.477 0.290 0.591 0.389 0.015 0.655 0.031 0.611
AnomalyTrans 0.930 0.893 0.911 0.215 0.583 0.216 0.682 0.907 0.474 0.622 0.222 0.257 0.402 0.490 0.097 0.595 0.167 0.010 0.578 0.020 0.619
DCdetector 0.892 0.867 0.879 0.193 0.572 0.206 0.683 0.951 0.595 0.732 0.286 0.411 0.346 0.494 0.304 0.708 0.425 0.015 0.723 0.023 0.616
EDAD(ours) 0.931 0.961 0.946 0.197 0.619 0.194 0.677 0.980 0.593 0.739 0.326 0.501 0.434 0.512 0.310 0.740 0.437 0.017 0.693 0.035 0.633
| Method |     |     | NAB |     |     |     | SVDB |     |     |     | AVERAGE |     |     |
| ------ | --- | --- | --- | --- | --- | --- | ---- | --- | --- | --- | ------- | --- | --- |
P R F1 A-PR A-ROC V-PR V-ROC P R F1 A-PR A-ROC V-PR V-ROC P R F1 A-PR A-ROC V-PR V-ROC
OC-SVM
0.437 0.983 0.605 0.336 0.483 0.311 0.614 0.462 0.986 0.629 0.239 0.526 0.230 0.663 0.463 0.716 0.545 0.219 0.534 0.213 0.579
IForest 0.765 0.774 0.769 0.146 0.434 0.230 0.627 0.812 0.732 0.770 0.171 0.594 0.212 0.651 0.580 0.692 0.632 0.182 0.503 0.206 0.558
DAGMM 0.501 0.589 0.541 0.360 0.450 0.304 0.647 0.621 0.635 0.628 0.104 0.360 0.215 0.661 0.666 0.576 0.597 0.235 0.558 0.224 0.563
Series2Graph 0.798 0.829 0.813 0.218 0.547 0.326 0.625 0.745 0.917 0.822 0.163 0.327 0.205 0.625 0.755 0.780 0.747 0.225 0.451 0.224 0.543
SAND 0.730 0.900 0.806 0.249 0.456 0.251 0.639 0.755 0.847 0.798 0.187 0.427 0.226 0.662 0.768 0.773 0.751 0.219 0.450 0.227 0.571
LSTM-AD 0.733 0.821 0.775 0.242 0.411 0.261 0.638 0.803 0.877 0.838 0.144 0.456 0.230 0.658 0.701 0.725 0.695 0.227 0.511 0.226 0.539
MAD-GAN 0.736 0.898 0.809 0.165 0.317 0.246 0.632 0.619 0.924 0.741 0.117 0.282 0.227 0.657 0.694 0.714 0.667 0.219 0.424 0.227 0.561
TranAD 0.743 0.920 0.822 0.123 0.587 0.246 0.629 0.610 0.884 0.722 0.105 0.508 0.223 0.632 0.719 0.798 0.726 0.211 0.480 0.221 0.525
GDN 0.753 0.928 0.831 0.115 0.651 0.248 0.632 0.618 0.923 0.740 0.198 0.575 0.225 0.654 0.661 0.649 0.618 0.207 0.490 0.215 0.539
OmniAnomaly 0.740 0.920 0.820 0.213 0.652 0.243 0.633 0.625 0.938 0.750 0.162 0.284 0.227 0.657 0.726 0.775 0.715 0.211 0.509 0.229 0.545
IMdiffusion 0.915 0.846 0.879 0.260 0.638 0.245 0.631 0.719 0.924 0.809 0.217 0.415 0.193 0.624 0.826 0.816 0.793 0.191 0.538 0.213 0.561
AnomalyTrans 0.743 0.920 0.822 0.227 0.302 0.219 0.615 0.811 0.865 0.837 0.225 0.320 0.197 0.571 0.785 0.839 0.779 0.192 0.389 0.200 0.551
DCdetector 0.915 0.996 0.954 0.228 0.605 0.207 0.616 0.633 0.892 0.853 0.213 0.550 0.190 0.563 0.842 0.878 0.844 0.213 0.566 0.193 0.559
EDAD(ours) 0.919 0.997 0.956 0.262 0.661 0.290 0.636 0.828 0.933 0.877 0.231 0.532 0.248 0.668 0.857 0.898 0.860 0.232 0.606 0.258 0.590
|      |     |      |     |      |     | EDAD | DCdetector | LSTM-AD |     |      |     |       |     |
| ---- | --- | ---- | --- | ---- | --- | ---- | ---------- | ------- | --- | ---- | --- | ----- | --- |
| 0.94 |     | 1.00 |     | 0.98 |     | 0.20 |            | 0.70    |     | 0.30 |     | 0.52  |     |
|      |     | 0.98 |     | 0.96 |     |      |            | 0.60    |     | 0.25 |     | 0.50  |     |
| 0.92 |     |      |     |      |     | 0.15 |            | COR-A   |     |      |     | COR-V |     |
|      |     | 0.96 |     | 1F   |     | RP-A |            |         |     | RP-V |     |       |     |
| P    |     | R    |     | 0.94 |     |      |            | 0.50    |     | 0.20 |     | 0.48  |     |
| 0.90 |     | 0.94 |     |      |     | 0.10 |            |         |     |      |     |       |     |
|      |     | 0.92 |     | 0.92 |     |      |            | 0.40    |     | 0.15 |     | 0.46  |     |
| 0.88 |     | 0.90 |     | 0.90 |     | 0.05 |            | 0.30    |     | 0.10 |     | 0.44  |     |
1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020
|     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |
| --- | ----- | --- | ----- | --- | ----- | --- | ----- | --- | ----- | --- | ----- | --- | ----- |
(a)P,SWAT. (b)R,SWAT. (c)F1,SWAT. (d)A-PR,SWAT. (e)A-ROC,SWAT. (f)V-PR,SWAT. (g)V-ROC,SWAT.
| 0.85   |     | 0.95 |     | 0.90    |     | 0.25 |     | 0.60  |     | 0.30 |     | 0.65  |     |
| ------ | --- | ---- | --- | ------- | --- | ---- | --- | ----- | --- | ---- | --- | ----- | --- |
| 0.80   |     |      |     | 0.85    |     |      |     |       |     | 0.25 |     | 0.60  |     |
|        |     | 0.90 |     |         |     | 0.20 |     | 0.50  |     |      |     |       |     |
|        |     |      |     |         |     | RP-A |     | COR-A |     | RP-V |     | COR-V |     |
| P 0.75 |     | R    |     | 1F 0.80 |     |      |     |       |     | 0.20 |     | 0.55  |     |
|        |     | 0.85 |     |         |     | 0.15 |     | 0.40  |     |      |     |       |     |
| 0.70   |     |      |     | 0.75    |     |      |     |       |     | 0.15 |     | 0.50  |     |
0.80
| 0.65 |     |     |     | 0.70 |     | 0.10 |     | 0.30 |     | 0.10 |     | 0.45 |     |
| ---- | --- | --- | --- | ---- | --- | ---- | --- | ---- | --- | ---- | --- | ---- | --- |
1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020 1 2 4 6 81020
|     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |     | CR(%) |
| --- | ----- | --- | ----- | --- | ----- | --- | ----- | --- | ----- | --- | ----- | --- | ----- |
(h)P,SVDB. (i)R,SVDB. (j)F1,SVDB. (k)A-PR,SVDB. (l)A-ROC,SVDB. (m)V-PR,SVDB. (n)V-ROC,SVDB.
|     |     |     |     |     | Figure 5: | Effect of | contamination | ratio | (CR). |     |     |     |     |
| --- | --- | --- | --- | --- | --------- | --------- | ------------- | ----- | ----- | --- | --- | --- | --- |
performs best, slightly ahead of JSD. This is because both both optimize similar objectives with different bias–variance
estimatorsarepartofthecontrastivevariationalboundsfamily trade-offs. While their empirical performance is often compa-
JSD
andtreatmutualinformationestimationasaclassificationtask- rable, tends to be more sensitive to hyperparameters and
distinguishing joint samples from marginal ones. InfoNCE is initialization,whichmayaffectitsrobustness.Inaddition,NWJ
a special case of JSD under a specific contrastive loss, and and MINE can also suffer from instability due to their reliance
9

Table IV: Overall ranking of anomaly detection methods. Table VI: Effect of model dimensionality on training time (minutes
per epoch).
|     |     | Method       |     | 1st 2nd | 3rd |     |     |      |                 |       |         |     |     |
| --- | --- | ------------ | --- | ------- | --- | --- | --- | ---- | --------------- | ----- | ------- | --- | --- |
|     |     | OC-SVM       |     | 3 8     | 3   |     |     | d    | EDAD DCdetector |       | LSTM-AD |     |     |
|     |     | IForest      |     | 3 2     | 2   |     |     |      |                 |       |         |     |     |
|     |     |              |     |         |     |     |     | 128  | 1.06            | 1.07  | 1.28    |     |     |
|     |     | DAGMM        |     | 4 2     | 2   |     |     | 256  | 1.21            | 3.04  | 1.61    |     |     |
|     |     | Series2Graph |     | 4 1     | 3   |     |     | 512  | 1.82            | 10.94 | 2.41    |     |     |
|     |     | SAND         |     | 0 1     | 5   |     |     | 1024 | 3.64            | 41.64 | 4.55    |     |     |
|     |     | LSTM-AD      |     | 3 3     | 3   |     |     |      |                 |       |         |     |     |
|     |     | MAD-GAN      |     | 3 3     | 3   |     |     |      |                 |       |         |     |     |
TableVII:Effectofmodeldimensionalityononmemorycost(GB).
|     |     | TranAD      |     | 1 3 | 3   |     |     |     |                 |     |         |     |     |
| --- | --- | ----------- | --- | --- | --- | --- | --- | --- | --------------- | --- | ------- | --- | --- |
|     |     | GDN         |     | 0 4 | 2   |     |     | d   | EDAD DCdetector |     | LSTM-AD |     |     |
|     |     | OmniAnomaly |     | 2 3 | 1   |     |     | 128 | 3.0             | 3.9 |         | 2.7 |     |
IMdiffusion
|               |           |              |                | 1 4        | 5     |             |             | 256           | 3.3 | 6.5          |      | 5.0            |      |
| ------------- | --------- | ------------ | -------------- | ---------- | ----- | ----------- | ----------- | ------------- | --- | ------------ | ---- | -------------- | ---- |
|               |           | AnomalyTrans |                | 4 2        | 9     |             |             |               |     |              |      |                |      |
|               |           |              |                |            |       |             |             | 512           | 4.4 | 7.6          |      | 9.4            |      |
|               |           | DCdetector   |                | 2 15       | 10    |             |             |               |     |              |      |                |      |
|               |           |              |                |            |       |             |             | 1024          | 6.4 | 10.1         | 18.4 |                |      |
|               |           | EDAD(ours)   |                | 26 9       | 10    |             |             |               |     |              |      |                |      |
| Table V:      | P, R, F1, | A-PR,        | A-ROC,         | V-PR, and  | V-ROC | of variants | of          |               |     |              |      |                |      |
|               |           |              |                |            |       |             | noise found | in real-world |     | contaminated |      | data. However, | they |
| EDAD averaged | over      | the          | nine datasets. | The second | block | represents  |             |               |     |              |      |                |      |
the estimator, and the third block represents the critic function. The still serve as a useful proxy for evaluating the robustness of
symbol ◦ indicates that we use the corresponding estimator/critic anomaly detection methods. Figure 5 shows the experimental
| function        | instead of    | the default | one.                | The top three | highest       | accuracies |             |                         |                 |           |          |        |              |
| --------------- | ------------- | ----------- | ------------------- | ------------- | ------------- | ---------- | ----------- | ----------------------- | --------------- | --------- | -------- | ------ | ------------ |
|                 |               |             |                     |               |               |            | results.    | We observe              | that DCdetector |           | performs |        | well with a  |
| are highlighted | with          | blue,       | where the           | best and      | the runner-up |            | results     |                         |                 |           |          |        |              |
|                 |               |             |                     |               |               |            | competitive | result due              | to its          | ability   | to learn | robust | represen-    |
| are in bold     | and underline |             | text, respectively. |               |               |            |             |                         |                 |           |          |        |              |
|                 |               |             |                     |               |               |            | tations     | by using contrastive    |                 | learning. | However, |        | DCdetector   |
| Method          |               | P           | R                   | F1 A-PR       | A-ROC         | V-PR       | V-ROC       |                         |                 |           |          |        |              |
|                 |               |             |                     |               |               |            | achieves    | an inferior performance |                 |           | to EDAD. | This   | demonstrates |
| EDAD(ours)      |               | 0.817       | 0.841 0.829         | 0.206         | 0.569         | 0.225      | 0.567       |                         |                 |           |          |        |              |
w/oStablemodule 0.805 0.845 0.810 0.200 0.568 0.229 0.557 that DCdetector is less robust than EDAD. The results show
w/oAuxiliarymodule 0.790 0.826 0.797 0.191 0.561 0.212 0.541 EDAD LSTM-AE
w/oRegularization 0.807 0.826 0.806 0.210 0.558 0.222 0.566 that outperforms w.r.t. all metrics. When the
◦NWJ 0.804 0.841 0.810 0.205 0.562 0.214 0.555 contamination ratio increases, EDAD maintains good perfor-
| ◦JSD          |     | 0.814 | 0.845 0.808 | 0.208 | 0.562 | 0.227 | 0.553        |                       |                   |           |          |             |              |
| ------------- | --- | ----- | ----------- | ----- | ----- | ----- | ------------ | --------------------- | ----------------- | --------- | -------- | ----------- | ------------ |
|               |     |       |             |       |       |       | mance w.r.t. | all metrics.          | In                | contrast, | LSTM-AE  | tends       | to exhibit   |
| ◦MINE         |     | 0.816 | 0.828 0.813 | 0.198 | 0.559 | 0.217 | 0.570        |                       |                   |           |          |             |              |
| ◦Bilinear     |     | 0.808 | 0.836 0.808 | 0.205 | 0.573 | 0.215 | 0.561        |                       |                   |           |          |             |              |
|               |     |       |             |       |       |       | serious      | drops in performance. |                   | This      | suggests |             | that EDAD is |
| ◦Concatenated |     | 0.813 | 0.838 0.805 | 0.199 | 0.569 | 0.215 | 0.565        |                       |                   |           |          |             |              |
|               |     |       |             |       |       |       | able to      | work on contaminated  |                   | data      | with     | performance | that is      |
|               |     |       |             |       |       |       | insensitive  | to the level          | of contamination. |           |          |             |              |
on unbounded log density ratios. 5) Runtime Analysis: To study the deployment potential
|           |     |        |            |       |     |            | of EDAD, | we compare | its runtime |     | (i.e., online | detection | time) |
| --------- | --- | ------ | ---------- | ----- | --- | ---------- | -------- | ---------- | ----------- | --- | ------------- | --------- | ----- |
| 3) Effect | of  | Critic | Functions: | While | the | estimators | of       |            |             |     |               |           |       |
mutual information are crucial in EDAD, there is still a sig- with two methods in previous experiments: DCdetector and
nificant interaction between the critic function f (·) and the LSTM-AD. First, we determine the runtime on each dataset.
θ
estimators. The design of the critic function determines its Then, we report the average runtime over all datasets. To
abilitytodistinguishbetweenjointandmarginaldistributions. achieve fair comparisons, we keep the dimensionality of the
|             |             |     |             |       |          |     | hidden states | d the same | across | the | methods. | We  | also observe |
| ----------- | ----------- | --- | ----------- | ----- | -------- | --- | ------------- | ---------- | ------ | --- | -------- | --- | ------------ |
| In the next | experiment, |     | we consider | three | commonly |     | used          |            |        |     |          |     |              |
critic functions, including bilinear critics [52], concatenated that the runtime mainly comes from the offline training time.
critics [22], and separable critics [5]. Bilinear critics employ Table VI reports the time needed (in minutes) to finish one
epoch.
a bilinear function. Concatenated critics combine different training The highest results are highlighted with bold
| inputsandemployaneuralnetworktoprocessthem.Separable |     |     |     |     |     |     | text. |     |     |     |     |     |     |
| ---------------------------------------------------- | --- | --- | --- | --- | --- | --- | ----- | --- | --- | --- | --- | --- | --- |
criticsprocessinputdatainaseparablemanner,thusreducing The training time results show that EDAD performs the
computationalcomplexity.TableVcomparesourdefaultsepa- fastest, whereas DCdetector runs much slower. This is be-
rable critic function and the two other critic functions, finding cause DCdetector has a dual attention component whereas
EDADemploysonlyasingleattention.Further,theresultsshow
| that the | default | separable | critics | perform | the best. | This | result |     |     |     |     |     |     |
| -------- | ------- | --------- | ------- | ------- | --------- | ---- | ------ | --- | --- | --- | --- | --- | --- |
aligns with findings in the literature [63]. that EDAD is able to train in a very short time. The online
4) Contamination Robustness: We aim to evaluate the detection time of EDAD is small, i.e., less than 0.1 second,
robustness of a method at different levels of contamination. making it applicable to online anomaly detection in streaming
| To enable | this | experiment, | we  | modify | a proportion |     | of the settings. |     |     |     |     |     |     |
| --------- | ---- | ----------- | --- | ------ | ------------ | --- | ---------------- | --- | --- | --- | --- | --- | --- |
original observations and consider the modified observations 6) Memory Analysis: We study the memory consumption
as anomalies [21], [24]. We vary the anomaly ratio among ofEDADandcompareitwiththememoryconsumptionoftwo
1%, 2%, 4%, 6%, 8%, 10%, and 20%. For brevity, we methods in previous experiments: DCdetector and LSTM-AD.
conduct experiments on two datasets: SWAT and SVDB, and First,wedeterminethememoryconsumptiononeachdataset.
we compare EDAD with two methods: 1) LSTM-AE, which Then, we report the average memory consumption over all
is a reconstruction-based method employing a Compress- datasets. To achieve fair comparisons, we keep the dimen-
then-Reconstruct paradigm, and 2) DCdetector, which is sionality of the hidden states d the same across the methods.
a robust anomaly detection method. We acknowledge that Table VII shows the RAM (in GB) used by the methods for
injected anomalies may not fully reflect the complexity of training. The best results are highlighted with bold text.
10

|      |     |      |     |      |     |      | λ1 λ2 | λ3         |     |      |     |            |     |
| ---- | --- | ---- | --- | ---- | --- | ---- | ----- | ---------- | --- | ---- | --- | ---------- | --- |
| 0.95 |     | 1.00 |     | 1.00 |     | 0.20 |       | 0.60       |     | 0.36 |     | 0.52       |     |
| 0.93 |     | 0.98 |     | 0.98 |     | 0.18 |       | COR-A 0.58 |     | 0.34 |     | COR-V 0.50 |     |
|      |     |      |     | 1F   |     | RP-A |       |            |     | RP-V |     |            |     |
| P    |     | R    |     |      |     |      |       |            |     |      |     |            |     |
| 0.91 |     | 0.96 |     | 0.96 |     | 0.16 |       | 0.56       |     | 0.32 |     | 0.48       |     |
| 0.89 |     | 0.94 |     | 0.94 |     | 0.14 |       | 0.54       |     | 0.30 |     | 0.46       |     |
0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3
|     | λ   |     | λ   |     | λ   |     | λ   |     | λ   |     | λ   |     | λ   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
(a)P,SWAT. (b)R,SWAT. (c)F1,SWAT. (d)A-PR,SWAT. (e)A-ROC,SWAT. (f)V-PR,SWAT. (g)V-ROC,SWAT.
| 0.84 |     | 0.96 |     | 0.90 |     | 0.26 |     | 0.56  |     | 0.24 |     | 0.62  |     |
| ---- | --- | ---- | --- | ---- | --- | ---- | --- | ----- | --- | ---- | --- | ----- | --- |
| 0.82 |     | 0.94 |     | 0.88 |     | 0.24 |     | 0.54  |     | 0.22 |     | 0.60  |     |
|      |     |      |     |      |     | RP-A |     | COR-A |     | RP-V |     | COR-V |     |
| P    |     | R    |     | 1F   |     |      |     |       |     |      |     |       |     |
| 0.80 |     | 0.92 |     | 0.86 |     | 0.22 |     | 0.52  |     | 0.20 |     | 0.58  |     |
| 0.78 |     | 0.90 |     | 0.84 |     | 0.20 |     | 0.50  |     | 0.18 |     | 0.56  |     |
0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3 0.10.5 1 2 3
|     | λ   |     | λ   |     | λ   |     | λ   |     | λ   |     | λ   |     | λ   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
(h)P,SVDB. (i)R,SVDB. (j)F1,SVDB. (k)A-PR,SVDB. (l)A-ROC,SVDB. (m)V-PR,SVDB. (n)V-ROC,SVDB.
|      |     |      |     |      | Figure | 6: Effect | of λ , | λ , and λ . |     |           |     |            |     |
| ---- | --- | ---- | --- | ---- | ------ | --------- | ------ | ----------- | --- | --------- | --- | ---------- | --- |
|      |     |      |     |      |        |           | 1      | 2 3         |     |           |     |            |     |
| 0.95 |     | 1.00 |     | 0.98 |        | 0.17      |        | 0.58        |     | 0.35      |     | 0.52       |     |
| 0.94 |     | 0.99 |     | 0.97 |        | RP-A 0.16 |        | COR-A 0.57  |     | RP-V 0.34 |     | COR-V 0.51 |     |
| P    |     | R    |     | 1F   |        |           |        |             |     |           |     |            |     |
| 0.93 |     | 0.98 |     | 0.96 |        | 0.15      |        | 0.56        |     | 0.33      |     | 0.50       |     |
| 0.92 |     | 0.97 |     | 0.95 |        | 0.14      |        | 0.55        |     | 0.32      |     | 0.49       |     |
102550 100 200 102550 100 200 102550 100 200 102550 100 200 102550 100 200 102550 100 200 102550 100 200
|     | B   |     | B   |     | B   |     | B   |     | B   |     | B   |     | B   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
(a)P,SWAT. (b)R,SWAT. (c)F1,SWAT. (d)A-PR,SWAT. (e)A-ROC,SWAT. (f)V-PR,SWAT. (g)V-ROC,SWAT.
| 0.84 |     | 0.94 |     | 0.89 |     | 0.24      |     | 0.54       |     | 0.26      |     | 0.68       |     |
| ---- | --- | ---- | --- | ---- | --- | --------- | --- | ---------- | --- | --------- | --- | ---------- | --- |
| 0.83 |     | 0.93 |     | 0.88 |     | RP-A 0.23 |     | COR-A 0.53 |     | RP-V 0.25 |     | COR-V 0.67 |     |
| P    |     | R    |     | 1F   |     |           |     |            |     |           |     |            |     |
| 0.82 |     | 0.92 |     | 0.87 |     | 0.22      |     | 0.52       |     | 0.24      |     | 0.66       |     |
| 0.81 |     | 0.91 |     | 0.86 |     | 0.21      |     | 0.51       |     | 0.23      |     | 0.65       |     |
102550 100 200 102550 100 200 102550 100 200 102550 100 200 102550 100 200 102550 100 200 102550 100 200
|     | B   |     | B   |     | B   |     | B   |     | B   |     | B   |     | B   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
(h)P,SVDB. (i)R,SVDB. (j)F1,SVDB. (k)A-PR,SVDB. (l)A-ROC,SVDB. (m)V-PR,SVDB. (n)V-ROC,SVDB.
|     |     |     |     |     |     | Figure | 7: Effect | of B. |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ------ | --------- | ----- | --- | --- | --- | --- | --- |
We observe that EDAD consumes the least memory in most the representations of time series. We observe that when the
cases except the case d = 128, and DCdetector consumes weights of the two modules are approximately equal, the
the most memory. This is because DCdetector has a dual model achieves the best performance in most cases. This is
attention component whereas EDAD only uses single attention. evidence that the stable and auxiliary modules are equally
This suggests that EDAD is able to perform on low-cost off- important and indispensable components of EDAD.
| the-shelf | computers.       | This | enables       | the use | of EDAD | in many |     |     |     |     |     |     |     |
| --------- | ---------------- | ---- | ------------- | ------- | ------- | ------- | --- | --- | --- | --- | --- | --- | --- |
| different | resource-limited |      | environments. |         |         |         |     |     |     |     |     |     |     |
7) Effect of λ , λ , and λ : We study the sensitivity of the 8) EffectofwindowsizeB: Westudytheeffectofwindow
|     |     | 1 2 | 3   |     |     |     |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
hyperparameters λ , λ , and λ in the objective function of size B. More specifically, we vary B among 10, 25, 50,
|     |     | 1 2 | 3   |     |     |     |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
EDAD(seeEq.25).Specifically,wevaryoneλamong0.1,0.5, 100, and 200 to investigate the sensitivity to B. Figure 7
1,2,and3whilekeepingtheothertwofixedat1toinvestigate shows the experimental results. We observe that when B
the sensitivity to the hyper-parameter. Figure 6 shows the increases, the model’s performance increases gradually and
results. First, λ controls the strength of the regularization becomes stable with B ≥ 50. In many cases, the model’s
3
loss. In most cases, as it increases, the model’s performance performance achieves the peak with B = 100. Then, the
decreases gradually. This indicates that an excessively high model’s performance starts to decrease with B > 100. This
regularizationstrengthcanhinderrepresentationlearning.Sec- observation aligns with existing studies [58], [75], where they
ond, λ and λ control the trade-off between the two novel claimthatdeepanomalydetectionmethodsfrequentlyachieve
| 1   |     | 2   |     |     |     |     |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
modules in EDAD. They mutually learn different features in the best accuracy with B is set around 100.
11

Time SeriesAnomaly
PointAnomaly
CollectiveAnomaly
|     |     |     | Contextual |     |     | Global |     | Trend | Shapelet |     | Seasonal |     |
| --- | --- | --- | ---------- | --- | --- | ------ | --- | ----- | -------- | --- | -------- | --- |
Time series
AnomalyScore
ofEDAD
Figure 8: Visualization of case study on anomalies built upon from Lai et al. [31]. Global anomalies and contextual anomalies are types
of point anomalies. Global anomalies refer to data points that significantly deviate from the normal pattern of the entire time series, while
contextual anomalies are data points that are considered abnormal only in a specific context. Shapelet anomalies, seasonal anomalies,
and trend anomalies belong to the type of collective anomaly. Shapelet anomalies refer to a subsequence within the data whose shape is
inconsistent with the normal pattern of the entire time series. Seasonal anomalies refer to abnormalities in the seasonal pattern of the data.
| Trend anomalies | are patterns |        | that contradict |     | the long-term |          | trend of | a time series. |     |     |     |     |
| --------------- | ------------ | ------ | --------------- | --- | ------------- | -------- | -------- | -------------- | --- | --- | --- | --- |
| Figure 9:       | An example   | of the | distribution    |     | of stable     | features | and      |                |     |     |     |     |
auxiliary features.
D. Visualization
| In order       | to offer        | a more     | comprehensible |        |               | and         | intuitive |                     |                    |     |                     |          |
| -------------- | --------------- | ---------- | -------------- | ------ | ------------- | ----------- | --------- | ------------------- | ------------------ | --- | ------------------- | -------- |
| illustration   | of how          | our method |                | excels | in detecting  |             | diverse   |                     |                    |     |                     |          |
| anomalies      | within time     | series     | data,          | we     | intentionally | designed    |           |                     |                    |     |                     |          |
|                |                 |            |                |        |               |             |           | Figure 10: Training | dynamics.Auxiliary |     | features and stable | features |
| and generated  | various         | types      | of anomaly     |        | sequences.    |             | The pri-  |                     |                    |     |                     |          |
|                |                 |            |                |        |               |             |           | use the same        | axis scale.        |     |                     |          |
| mary aim       | was to visually |            | showcase       | the    | model’s       | proficiency |           |                     |                    |     |                     |          |
| in identifying | anomalies       | across     | different      |        | categories.   | Building    |           |                     |                    |     |                     |          |
| upon the       | categorization  | of         | anomaly        | types  | as            | summarized  |           | in                  |                    |     |                     |          |
the work by Lai et al. [31], we subjected our method to the a toy dataset in two separate low-dimensional spaces using
assessment of five specific anomaly types: global, contextual, t-SNE [67]. Note that we use the same axis scale for the
shapelet,seasonal,andtrend.Figure8visualizesthedetection visualization of auxiliary features and the visualization of
results.WhilethefigureisadaptedfromLaietal.,itaccurately stable features. It is clear that the distribution of auxiliary
| reflects | the characteristics |     | observed | by  | using | our proposed |     |                  |                |      |                     |        |
| -------- | ------------------- | --- | -------- | --- | ----- | ------------ | --- | ---------------- | -------------- | ---- | ------------------- | ------ |
|          |                     |     |          |     |       |              |     | features is more | dispersed than | that | of stable features. | Recall |
method, which is why we chose to include it. The results that we use different strategies in the proposed stable module
demonstrate that our proposed framework can detect different andauxiliarymodule,whichleadstodifferentrepresentations.
typesofanomalies.Thisoffersevidenceoftheeffectivenessof For stable features, we assume that the normal pattern in the
our approach and its capability to work on practical problems time series is persistent and is the normal form of the data,
| where different | anomaly | types | occur. |     |     |     |     |     |     |     |     |     |
| --------------- | ------- | ----- | ------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
sothedistributionofstablefeaturesisrelativelyconcentrated.
Next, we empirically analyze stable and auxiliary features Forauxiliaryfeatures,theycontainnoiseandanomaliesrelated
to further illustrate and understand their sensitivity. Figure 9 to timestamps, and this randomness results in the features
visualizes the distribution of stable and auxiliary features for being relatively dispersed. Furthermore, Figure 10 illustrates
12

how the distributions of stable and auxiliary features evolve integratesmutualinformationtobettersupportdecomposition.
across training epochs, again visualized with t-SNE. Initially, To the best of our knowledge, EDAD is the first time series
the stable and auxiliary features exhibit similar distributions. anomalydetectionmethodthatdecomposesthelatentvariable
However, as the training progresses, the distinction between to achieve robustness.
these two feature types becomes increasingly pronounced. By Mutual Information. Mutual information measures the re-
thefinalstagesoftraining,theauxiliaryfeaturerepresentation lationship between statistical variables. Mutual information
provides a clearer separation between normal instances and plays a role in many applications in a wide range of do-
anomalies, whereas the stable feature representation fails to mains. Early approaches typically use nonparametric models
distinguish them. forestimatingmutualinformation[30],suchaskerneldensity
|     |     |     |             |     |     |     |     | estimation | methods | that | use | kernel | functions | to estimate | the |
| --- | --- | --- | ----------- | --- | --- | --- | --- | ---------- | ------- | ---- | --- | ------ | --------- | ----------- | --- |
|     |     | V.  | RELATEDWORK |     |     |     |     |            |         |      |     |        |           |             |     |
probabilitydensityfunctionofdata.Deepneuralnetworksand
| Time Series | Anomaly |     | Detection. | Many | time | series | anomaly |                |          |     |      |           |          |     |              |
| ----------- | ------- | --- | ---------- | ---- | ---- | ------ | ------- | -------------- | -------- | --- | ---- | --------- | -------- | --- | ------------ |
|             |         |     |            |      |      |        |         | representation | learning |     | [66] | are being | employed |     | increasingly |
detection approaches exist, including traditional statistical for mutual information estimation to cater to the demands
methods, classical machine learning algorithms [14], [56], posed by the expanding scale and complexity of contempo-
and modern deep learning methods. Traditional statistical rary datasets, as well as the need for representation opti-
methods detect anomalies by applying an auto-regression mization. Notable instances of this approach include Barber-
| mechanism | [15], | [20], | [40]. | These | methods | are | easy to im- |        |             |             |     |        |           |     |             |
| --------- | ----- | ----- | ----- | ----- | ------- | --- | ----------- | ------ | ----------- | ----------- | --- | ------ | --------- | --- | ----------- |
|           |       |       |       |       |         |     |             | Agakov | [6], mutual | information |     | neural | estimator |     | (MINE) [7], |
plement and deploy. However, their accuracy is relatively and M-estimators [44]. Existing studies use mutual in-
low. Classical machine algorithms can be categorized into formation to measure the relationship between variables in
similarity-based and density-based methods. In similarity- supervised learning problems where labeled data is available.
based methods, time series subsequences are compared. The To the best of our knowledge, our proposal is the first to
| most different |           | subsequences | are       | likely       | to be | anomalies.       | Senin      |            |             |     |                  |     |     |             |         |
| -------------- | --------- | ------------ | --------- | ------------ | ----- | ---------------- | ---------- | ---------- | ----------- | --- | ---------------- | --- | --- | ----------- | ------- |
|                |           |              |           |              |       |                  |            | use mutual | information |     | for unsupervised |     |     | time series | anomaly |
| et al. [56]    | converted | time         | series    | subsequences |       | into             | characters | detection. |             |     |                  |     |     |             |         |
| and used       | grammar   | rules        | to detect | anomalies.   |       | In density-based |            |            |             |     |                  |     |     |             |         |
methods, time series subsequences are grouped into clusters. VI. CONCLUSION
| Clusters | with | low density | are | then | considered | as  | anomalies. |     |     |     |     |     |     |     |     |
| -------- | ---- | ----------- | --- | ---- | ---------- | --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
Breunig et al. [14] propose Local Outlier Factor (LOF), which We propose EDAD for unsupervised time series anomaly
|           |     |               |     |          |     |         |           | detection. | The | framework |     | addresses |     | a key problem | in  |
| --------- | --- | ------------- | --- | -------- | --- | ------- | --------- | ---------- | --- | --------- | --- | --------- | --- | ------------- | --- |
| considers | the | local density | of  | clusters | and | is able | to detect |            |     |           |     |           |     |               |     |
local outliers effectively. Sequeira and Zaki [57] cluster time autoencoder-based anomaly detection methods: their high
|                     |            |      |           |         |          |          |            | vulnerability | to  | contaminated |                | training | data. | The             | framework |
| ------------------- | ---------- | ---- | --------- | ------- | -------- | -------- | ---------- | ------------- | --- | ------------ | -------------- | -------- | ----- | --------------- | --------- |
| series subsequences |            | into | a fixed   | number  | of       | clusters | using      | a             |     |              |                |          |       |                 |           |
|                     |            |      |           |         |          |          |            | decomposes    | the | latent       | representation |          | into  | stable features | and       |
| k-medoids           | algorithm. |      | Classical | machine | learning |          | algorithms |               |     |              |                |          |       |                 |           |
do not consider time series-specific temporal information, so auxiliary features that comprise long-term patterns and point-
|             |     |         |         |           |            |     |     | wise patterns, | respectively, |          | rather      | than | blindly   | reconstructing |            |
| ----------- | --- | ------- | ------- | --------- | ---------- | --- | --- | -------------- | ------------- | -------- | ----------- | ---- | --------- | -------------- | ---------- |
| they cannot | be  | applied | well in | practical | scenarios. |     |     |                |               |          |             |      |           |                |            |
|             |     |         |         |           |            |     |     | the time       | series.       | A mutual | information |      | criterion | is             | integrated |
Deeplearningbasedtimeseriesanomalydetectionmethods
|              |         |          |              |                |      |           |           | into the   | decomposition |     | to      | support | the  | robustness    | of the |
| ------------ | ------- | -------- | ------------ | -------------- | ---- | --------- | --------- | ---------- | ------------- | --- | ------- | ------- | ---- | ------------- | ------ |
| are used     | widely  | in many  | applications |                | such | as object | moni-     |            |               |     |         |         |      |               |        |
|              |         |          |              |                |      |           |           | framework. | Experimental  |     | studies | show    | that | the framework | is     |
| toring [80], | network | analysis |              | [39], robotics |      | [48],     | and human |            |               |     |         |         |      |               |        |
behaviorsanalysis[28].Whilediffusion-basedmodelshavere- effectiveandcanoutperformstrongbaselinesandstate-of-the-
art methods.
centlyshownimpressiveperformanceforgenerativemodelsin
termsofreconstructionquality,theyarenotintensivelyusedin In future research, it is of interest to study anomaly detec-
time series anomaly detection, and they also incur substantial tion in different settings, such as binary-value settings [77],
|               |     |                   |     |     |           |     |            | semi-supervised |     | settings | [35], | time | series | of location-related |     |
| ------------- | --- | ----------------- | --- | --- | --------- | --- | ---------- | --------------- | --- | -------- | ----- | ---- | ------ | ------------------- | --- |
| computational |     | costs. Crucially, |     | our | framework | is  | orthogonal |                 |     |          |       |      |        |                     |     |
to the backbone choice. Thus, the proposed Encode-then- information[17],continuallearningsettings[73],andconcept
|     |     |     |     |     |     |     |     | drift settings | [62], | [69]. | It is | also of | interest | to study | different |
| --- | --- | --- | --- | --- | --- | --- | --- | -------------- | ----- | ----- | ----- | ------- | -------- | -------- | --------- |
Decomposeparadigmcouldbeintegratedwithdiffusionmod-
els. The latest methods include AnomalyTrans [76], which approaches such as ensemble learning [26] and explainabil-
measures the strength of correlations between observations ity [27] to further improve anomaly detection accuracy.
| in time | series, | and DCdetector |     | [77], | which | achieves | im- |     |     |     |     |     |     |     |     |
| ------- | ------- | -------------- | --- | ----- | ----- | -------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
pressive performance using a contrastive learning approach REFERENCES
| with a | dual attention |     | component. | However, |     | AnomalyTrans |     |     |     |     |     |     |     |     |     |
| ------ | -------------- | --- | ---------- | -------- | --- | ------------ | --- | --- | --- | --- | --- | --- | --- | --- | --- |
[1] E.Abdelaleem,I.Nemenman,andK.M.Martini,“Deepvariationalmul-
| and DCdetector |     | do not | perform | the | encode-then-decompose |     |     |           |             |     |            |               |     |                 |          |
| -------------- | --- | ------ | ------- | --- | --------------------- | --- | --- | --------- | ----------- | --- | ---------- | ------------- | --- | --------------- | -------- |
|                |     |        |         |     |                       |     |     | tivariate | information |     | bottleneck | - A framework |     | for variational | losses,” |
mechanismlikeus.Themostrelevantstudytoourproposalis
CoRR,vol.abs/2310.03311,2023.
|     |     |     |     |     |     |     |     | [2] A. Abdulaal, |     | Z. Liu, | and T. Lancewicki, |     | “Practical | approach | to asyn- |
| --- | --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | ------- | ------------------ | --- | ---------- | -------- | -------- |
RobustAutoencoders(RAEs)[81],whichdecomposesadataset
|            |      |           |             |      |     |      |            | chronous       | multivariate |        | time series | anomaly | detection     | and        | localization,” |
| ---------- | ---- | --------- | ----------- | ---- | --- | ---- | ---------- | -------------- | ------------ | ------ | ----------- | ------- | ------------- | ---------- | -------------- |
| into clean | and  | anomalous | components. |      | The | main | difference |                |              |        |             |         |               |            |                |
|            |      |           |             |      |     |      |            | in Proceedings |              | of the | ACM         | SIGKDD  | International | Conference | on             |
|            | RAEs | EDAD      |             | RAEs |     |      |            |                |              |        |             |         |               |            |                |
between and is that fail to handle temporal Knowledge Discovery and Data Mining (SIGKDD), 2021, pp. 2485–
| information    | and            | thus | cannot  | work         | on time | series. | Further,    | 2494.         |           |        |           |        |                 |               |               |
| -------------- | -------------- | ---- | ------- | ------------ | ------- | ------- | ----------- | ------------- | --------- | ------ | --------- | ------ | --------------- | ------------- | ------------- |
|                |                |      |         |              |         |         |             | [3] S. Ahmad, | A.        | Lavin, | S. Purdy, | and Z. | Agha,           | “Unsupervised | real-time     |
| RAEs decompose |                | the  | data in | the original |         | space   | rather than |               |           |        |           |        |                 |               |               |
|                |                |      |         |              |         |         |             | anomaly       | detection | for    | streaming | data,” | Neurocomputing, |               | vol. 262, pp. |
| in the latent  | representation |      | space,  | as           | EDAD    | does.   | EDAD also   | 134–147,2017. |           |        |           |        |                 |               |               |
13

[4] C.Bachelard,A.Chalkis,V.Fisikopoulos,andE.P.Tsigaridas,“Ran- [25] T.Kieu,B.Yang,C.Guo,R.Cirstea,Y.Zhao,Y.Song,andC.S.Jensen,
domized geometric tools for anomaly detection in stock markets,” in “Anomalydetectionintimeserieswithrobustvariationalquasi-recurrent
Proceedings of the International Conference on Artificial Intelligence autoencoders,”inProceedingsoftheIEEEInternationalConferenceon
andStatistics(AISTATS),2023,pp.9400–9416. DataEngineering(ICDE),2022,pp.1342–1354.
[5] P.Bachman,R.D.Hjelm,andW.Buchwalter,“Learningrepresentations [26] T. Kieu, B. Yang, C. Guo, and C. S. Jensen, “Outlier detection for
|     |     |     |     |     |     |     |     |     |     |     |     |     |     |     | Proceedings of |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | -------------- |
bymaximizingmutualinformationacrossviews,”inProceedingsofthe time series with recurrent autoencoder ensembles,” in
ConferenceonNeuralInformationProcessingSystems(NeurIPS),2019, the International Joint Conferences on Artificial Intelligence (IJCAI),
| pp.15509–15519. |     |     |     |     |     |     |     | 2019,pp.2725–2732. |     |     |     |     |     |     |     |
| --------------- | --- | --- | --- | --- | --- | --- | --- | ------------------ | --- | --- | --- | --- | --- | --- | --- |
[6] D. Barber and F. V. Agakov, “Information maximization in noisy [27] T.Kieu,B.Yang,C.Guo,C.S.Jensen,Y.Zhao,F.Huang,andK.Zheng,
channels,” in Proceedings of the Conference on Neural Information “Robust and explainable autoencoders for unsupervised time series
outlierdetection,”inProceedingsoftheIEEEInternationalConference
ProcessingSystems(NeurIPS),2003,pp.201–208.
onDataEngineering(ICDE),2022,pp.3038–3050.
| [7] M. I. | Belghazi, | A. Baratin, | S.  | Rajeswar, | S. Ozair, | Y. Bengio, | R.  | D.  |     |     |     |     |     |     |     |
| --------- | --------- | ----------- | --- | --------- | --------- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Hjelm, and A. C. Courville, “Mutual information neural estimation,” [28] T.Kieu,B.Yang,andC.S.Jensen,“Outlierdetectionformultidimen-
in Proceedings of the International Conference on Machine Learning sional time series using deep neural networks,” in Proceedings of the
(ICML),2018,pp.530–539. IEEE International Conference on Mobile Data Management (MDM),
[8] A.J.BellandT.J.Sejnowski,“Aninformation-maximizationapproach 2018,pp.125–134.
|          |            |     |                       |     |        |          |      | [29] D.P.KingmaandJ.Ba,“Adam:Amethodforstochasticoptimization,” |     |     |     |     |     |     |     |
| -------- | ---------- | --- | --------------------- | --- | ------ | -------- | ---- | --------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
| to blind | separation | and | blind deconvolution,” |     | Neural | Comput., | vol. | 7,                                                              |     |     |     |     |     |     |     |
no.6,pp.1129–1159,1995. inProceedingsoftheInternationalConferenceonLearningRepresen-
[9] P.Boniol,M.Linardi,F.Roncallo,andT.Palpanas,“Automatedanomaly tations(ICLR),2015.
detectioninlargesequences,”inProceedingsoftheIEEEInternational [30] A. Kraskov, H. Sto¨gbauer, and P. Grassberger, “Estimating mutual
ConferenceonDataEngineering(ICDE),2020,pp.1834–1837. information,”Phys.Rev.E,vol.69,pp.66138–66154,2004.
|                |     |              |                |     |             |     |             | [31] K.Lai,D.Zha,J.Xu,Y.Zhao,G.Wang,andX.B.Hu,“Revisitingtime |     |     |     |     |     |     |     |
| -------------- | --- | ------------ | -------------- | --- | ----------- | --- | ----------- | ------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
| [10] P. Boniol | and | T. Palpanas, | “Series2Graph: |     | Graph-based |     | subsequence |                                                               |     |     |     |     |     |     |     |
seriesoutlierdetection:Definitionsandbenchmarks,”inProceedingsof
anomalydetectionfortimeseries,”Proc.VLDBEndow.,vol.13,no.12,
pp.1821–1834,2020. the Conference on Neural Information Processing Systems (NeurIPS),
| [11] P.Boniol,J.Paparrizos,Y.Kang,T.Palpanas,R.S.Tsay,A.J.Elmore, |     |     |     |     |     |     |     | 2021. |     |     |     |     |     |     |     |
| ----------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
and M. J. Franklin, “Theseus: Navigating the labyrinth of time-series [32] S. Laine and T. Aila, “Temporal ensembling for semi-supervised
|         |             |       |      |         |      |         |               | learning,” | in  | Proceedings | of the | International | Conference |     | on Learning |
| ------- | ----------- | ----- | ---- | ------- | ---- | ------- | ------------- | ---------- | --- | ----------- | ------ | ------------- | ---------- | --- | ----------- |
| anomaly | detection,” | Proc. | VLDB | Endow., | vol. | 15, no. | 12, pp. 3702– |            |     |             |        |               |            |     |             |
Representations(ICLR),2017.
3705,2022.
|                 |     |             |              |     |        |              |        | [33] A.Lerner,D.E.Shasha,Z.Wang,X.Zhao,andY.Zhu,“Fastalgorithms |     |     |     |     |     |     |     |
| --------------- | --- | ----------- | ------------ | --- | ------ | ------------ | ------ | --------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
| [12] P. Boniol, | J.  | Paparrizos, | T. Palpanas, |     | and M. | J. Franklin, | “SAND: |                                                                 |     |     |     |     |     |     |     |
Streaming subsequence anomaly detection,” Proc. VLDB Endow., for time series with applications to finance, physics, music, biology,
vol.14,no.10,pp.1717–1729,2021. andothersuspects,”inProceedingsoftheACMSIGMODInternational
ConferenceonManagementofData(SIGMOD),2004,pp.965–968.
| [13] M. Brereton, |     | “A modern | course | in statistical |     | physics,” | Phys. Bull., |             |          |     |         |              |     |        |           |
| ----------------- | --- | --------- | ------ | -------------- | --- | --------- | ------------ | ----------- | -------- | --- | ------- | ------------ | --- | ------ | --------- |
|                   |     |           |        |                |     |           |              | [34] D. Li, | D. Chen, | B.  | Jin, L. | Shi, J. Goh, | and | S. Ng, | “MAD-GAN: |
vol.27,no.3,pp.84–84,1981.
|     |     |     |     |     |     |     |     | multivariate |     | anomaly | detection | for time | series | data with | generative |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------ | --- | ------- | --------- | -------- | ------ | --------- | ---------- |
[14] M.M.Breunig,H.Kriegel,R.T.Ng,andJ.Sander,“LOF:identifying
|               |     |                  |     |                |     |            |        | adversarial | networks,” |     | in Proceedings |     | of the International |     | Conference |
| ------------- | --- | ---------------- | --- | -------------- | --- | ---------- | ------ | ----------- | ---------- | --- | -------------- | --- | -------------------- | --- | ---------- |
| density-based |     | local outliers,” |     | in Proceedings |     | of the ACM | SIGMOD |             |            |     |                |     |                      |     |            |
International Conference on Management of Data (SIGMOD), 2000, onArtificialNeuralNetworks(ICANN),2019,pp.703–716.
|     |     |     |     |     |     |     |     | [35] S. Li, | X. Ji, | E. Dobriban, |     | O. Sokolsky, | and | I. Lee, | “PAC-Wrap: |
| --- | --- | --- | --- | --- | --- | --- | --- | ----------- | ------ | ------------ | --- | ------------ | --- | ------- | ---------- |
pp.93–104.
|                    |     |                   |     |             |             |     |              | Semi-supervised |               | PAC | anomaly    | detection,” | in Proceedings |           | of the ACM |
| ------------------ | --- | ----------------- | --- | ----------- | ----------- | --- | ------------ | --------------- | ------------- | --- | ---------- | ----------- | -------------- | --------- | ---------- |
| [15] C. Chatfield, |     | “The Holt-Winters |     | forecasting | procedure,” |     | Appl. Stat., |                 |               |     |            |             |                |           |            |
|                    |     |                   |     |             |             |     |              | SIGKDD          | International |     | Conference | on          | Knowledge      | Discovery | and Data   |
vol.27,no.3,p.264,Jan1978.
Mining(SIGKDD),2022,pp.945–955.
[16] Y.Chen,C.Zhang,M.Ma,Y.Liu,R.Ding,B.Li,S.He,S.Rajmohan,
|     |     |     |     |     |     |     |     | [36] Z.Li,Y.Zhao,J.Han,Y.Su,R.Jiao,X.Wen,andD.Pei,“Multivariate |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
Q.Lin,andD.Zhang,“Imdiffusion:Imputeddiffusionmodelsformul- timeseriesanomalydetectionandinterpretationusinghierarchicalinter-
| tivariate | time | series anomaly | detection,” |     | Proc. | VLDB Endow., | vol. 17, |     |     |     |     |     |     |     |     |
| --------- | ---- | -------------- | ----------- | --- | ----- | ------------ | -------- | --- | --- | --- | --- | --- | --- | --- | --- |
metricandtemporalembedding,”inProceedingsoftheACMSIGKDD
no.3,pp.359–372,2023.
|                  |     |          |      |          |        |               |         | International |     | Conference | on Knowledge |     | Discovery | and | Data Mining |
| ---------------- | --- | -------- | ---- | -------- | ------ | ------------- | ------- | ------------- | --- | ---------- | ------------ | --- | --------- | --- | ----------- |
| [17] R. Cirstea, | B.  | Yang, C. | Guo, | T. Kieu, | and S. | Pan, “Towards | spatio- |               |     |            |              |     |           |     |             |
(SIGKDD),2021,pp.3220–3230.
| temporal | aware | traffic | time series | forecasting,” |     | in Proceedings | of the |            |         |          |        |                  |     |          |                |
| -------- | ----- | ------- | ----------- | ------------- | --- | -------------- | ------ | ---------- | ------- | -------- | ------ | ---------------- | --- | -------- | -------------- |
|          |       |         |             |               |     |                |        | [37] F. T. | Liu, K. | M. Ting, | and Z. | Zhou, “Isolation |     | forest,” | in Proceedings |
IEEEInternationalConferenceonDataEngineering(ICDE),2022,pp. of the IEEE International Conference on Data Mining (ICDM), 2008,
| 2900–2913. |     |     |     |     |     |     |     | pp.413–422. |     |     |     |     |     |     |     |
| ---------- | --- | --- | --- | --- | --- | --- | --- | ----------- | --- | --- | --- | --- | --- | --- | --- |
[18] W.P.ClevelandandG.C.Tiao,“Decompositionofseasonaltimeseries:
|     |     |     |     |     |     |     |     | [38] Y. Liu, | T. Hu, | H.  | Zhang, H. | Wu, S. | Wang, | L. Ma, | and M. Long, |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------ | ------ | --- | --------- | ------ | ----- | ------ | ------------ |
Amodelforthecensusx-11program,”J.Am.Stat.Assoc.,vol.71,no.
|     |     |     |     |     |     |     |     | “itransformer: |     | Inverted | transformers | are | effective | for time | series fore- |
| --- | --- | --- | --- | --- | --- | --- | --- | -------------- | --- | -------- | ------------ | --- | --------- | -------- | ------------ |
355,pp.581–587,1976.
|     |     |     |     |     |     |     |     | casting,” | in  | Proceedings | of the | International | Conference |     | on Learning |
| --- | --- | --- | --- | --- | --- | --- | --- | --------- | --- | ----------- | ------ | ------------- | ---------- | --- | ----------- |
[19] A.DengandB.Hooi,“Graphneuralnetwork-basedanomalydetection Representations(ICLR),2024.
inmultivariatetimeseries,”inProceedingsoftheAAAIConferenceon [39] T. Luo and S. G. Nagarajan, “Distributed anomaly detection using
ArtificialIntelligence(AAAI),2021,pp.4027–4035. autoencoder neural networks in WSN for IoT,” in Proceedings of the
[20] Z.Du,L.Ma,H.Li,Q.Li,G.Sun,andZ.Liu,“Networktrafficanomaly
|     |     |     |     |     |     |     |     | IEEE | International |     | Conference | on Communications |     | (ICC), | 2018, pp. |
| --- | --- | --- | --- | --- | --- | --- | --- | ---- | ------------- | --- | ---------- | ----------------- | --- | ------ | --------- |
detectionbasedonwaveletanalysis,”inProceedingsoftheIEEE/ACIS
1–6.
International Conference on Software Engineering, Management and [40] A.Mahimkar,Z.Ge,J.Wang,J.Yates,Y.Zhang,J.Emmons,B.Hunt-
Applications(SERA),2018,pp.94–101. ley,andM.Stockert,“Rapiddetectionofmaintenanceinducedchanges
[21] M.Goswami,C.I.Challu,L.Callot,L.Minorics,andA.Kan,“Unsuper- inserviceperformance,”inProceedingsoftheInternationalConference
visedmodelselectionfortimeseriesanomalydetection,”inProceedings on Emerging Networking EXperiments and Technologies (CoNEXT),
| of the | International | Conference |     | on Learning | Representations |     | (ICLR), |     |     |     |     |     |     |     |     |
| ------ | ------------- | ---------- | --- | ----------- | --------------- | --- | ------- | --- | --- | --- | --- | --- | --- | --- | --- |
2011,pp.1–12.
2023. [41] A. P. Mathur and N. O. Tippenhauer, “SWaT: A water treatment
[22] R.D.Hjelm,A.Fedorov,S.Lavoie-Marchildon,K.Grewal,P.Bachman, testbed for research and training on ICS security,” in Proceedings of
A.Trischler,andY.Bengio,“Learningdeeprepresentationsbymutual theInternationalWorkshoponCyber-physicalSystemsforSmartWater
informationestimationandmaximization,”inProceedingsoftheInter- Networks(CySWater),2016,pp.31–36.
nationalConferenceonLearningRepresentations(ICLR),2019.
|     |     |     |     |     |     |     |     | [42] U. | Michelucci, | “An | introduction | to  | autoencoders,” |     | CoRR, vol. |
| --- | --- | --- | --- | --- | --- | --- | --- | ------- | ----------- | --- | ------------ | --- | -------------- | --- | ---------- |
[23] K. Hundman, V. Constantinou, C. Laporte, I. Colwell, and T. So¨der- abs/2201.03898,2022.
stro¨m, “Detecting spacecraft anomalies using LSTMs and nonpara- [43] G. Moody and R. Mark, “The impact of the MIT-BIH arrhythmia
metric dynamic thresholding,” in Proceedings of the ACM SIGKDD database,”IEEEEng.Med.Biol.Mag.,p.45–50,2001.
International Conference on Knowledge Discovery and Data Mining [44] X.Nguyen,M.J.Wainwright,andM.I.Jordan,“Estimatingdivergence
(SIGKDD),2018,pp.387–395. functionalsandthelikelihoodratiobyconvexriskminimization,”IEEE
[24] Y.Jeong,E.Yang,J.H.Ryu,I.Park,andM.Kang,“AnomalyBERT: Trans.Inf.Theory,vol.56,no.11,pp.5847–5861,2010.
Self-supervisedtransformerfortimeseriesanomalydetectionusingdata [45] Y.Nie,N.H.Nguyen,P.Sinthong,andJ.Kalagnanam,“Atimeseries
degradationscheme,”CoRR,vol.abs/2305.04468,2023. is worth 64 words: Long-term forecasting with transformers,” in Pro-
14

| ceedings | of the | International | Conference |     | on Learning | Representations |     |               |            |     |       |           |          |      |             |
| -------- | ------ | ------------- | ---------- | --- | ----------- | --------------- | --- | ------------- | ---------- | --- | ----- | --------- | -------- | ---- | ----------- |
|          |        |               |            |     |             |                 |     | [64] S. Tuli, | G. Casale, | and | N. R. | Jennings, | “TranAD: | Deep | transformer |
(ICLR),2023. networksforanomalydetectioninmultivariatetimeseriesdata,”Proc.
[46] J.Paparrizos,P.Boniol,T.Palpanas,R.Tsay,A.J.Elmore,andM.J. VLDBEndow.,vol.15,no.6,pp.1201–1214,2022.
Franklin,“Volumeunderthesurface:Anewaccuracyevaluationmea- [65] D.Ulyanov,A.Vedaldi,andV.S.Lempitsky,“Instancenormalization:
sure for time-series anomaly detection,” Proc. VLDB Endow., vol. 15, Themissingingredientforfaststylization,”CoRR,vol.abs/1607.08022,
2016.
no.11,pp.2774–2787,2022.
[66] A.vandenOord,Y.Li,andO.Vinyals,“Representationlearningwith
| [47] J. Paparrizos, |     | Y. Kang, | P. Boniol, | R. S. | Tsay, T. Palpanas, | and | M. J. |     |     |     |     |     |     |     |     |
| ------------------- | --- | -------- | ---------- | ----- | ------------------ | --- | ----- | --- | --- | --- | --- | --- | --- | --- | --- |
Franklin, “TSB-UAD: an end-to-end benchmark suite for univariate contrastivepredictivecoding,”CoRR,vol.abs/1807.03748,2018.
time-seriesanomalydetection,”Proc.VLDBEndow.,vol.15,no.8,pp. [67] L. Van der Maaten and G. Hinton, “Visualizing data using t-SNE,” J.
| 1697–1711,2022. |     |     |     |     |     |     |     | Mach.LearnRes.,vol.9,no.11,2008. |         |             |     |               |     |       |             |
| --------------- | --- | --- | --- | --- | --- | --- | --- | -------------------------------- | ------- | ----------- | --- | ------------- | --- | ----- | ----------- |
|                 |     |     |     |     |     |     |     | [68] D.                          | Wagner, | T. Michels, | F.  | C. F. Schulz, | A.  | Nair, | M. Rudolph, |
[48] D.Park,Z.M.Erickson,T.Bhattacharjee,andC.C.Kemp,“Multimodal
|     |     |     |     |     |     |     |     | and | M. Kloft, | “Timesead: | Benchmarking |     | deep | multivariate | time-series |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --------- | ---------- | ------------ | --- | ---- | ------------ | ----------- |
executionmonitoringforanomalydetectionduringrobotmanipulation,”
in Proceedings of the IEEE International Conference on Robotics and anomalydetection,”Trans.Mach.Learn.Res.,vol.2023,2023.
Automation(ICRA),2016,pp.407–414. [69] C. Wang, Z. Zhuang, Q. Qi, J. Wang, X. Wang, H. Sun, and J. Liao,
[49] A. Paszke, S. Gross, F. Massa, A. Lerer, J. Bradbury, G. Chanan, “Drift doesn’t matter: Dynamic decomposition with diffusion recon-
|     |     |     |     |     |     |     |     | struction | for | unstable | multivariate | time | series | anomaly | detection,” in |
| --- | --- | --- | --- | --- | --- | --- | --- | --------- | --- | -------- | ------------ | ---- | ------ | ------- | -------------- |
T.Killeen,Z.Lin,N.Gimelshein,L.Antiga,A.Desmaison,A.Ko¨pf,
ConferenceonNeuralInformationProcessingSystems(NeurIPS),2023.
E.Z.Yang,Z.DeVito,M.Raison,A.Tejani,S.Chilamkurthy,B.Steiner,
|          |         |        |           |           |               |        |       | [70] H. Wang, | Z.  | Luo, J. W. | L. Yip, | C. Ye, | and M. | Zhang, | “ECGGAN: A |
| -------- | ------- | ------ | --------- | --------- | ------------- | ------ | ----- | ------------- | --- | ---------- | ------- | ------ | ------ | ------ | ---------- |
| L. Fang, | J. Bai, | and S. | Chintala, | “Pytorch: | An imperative | style, | high- |               |     |            |         |        |        |        |            |
performance deep learning library,” in Proceedings of the Conference frameworkforeffectiveandinterpretableelectrocardiogramanomalyde-
onNeuralInformationProcessingSystems(NeurIPS),2019,pp.8024– tection,”inProceedingsoftheACMSIGKDDConferenceonKnowledge
DiscoveryandDataMining(SIGKDD),2023,pp.5071–5081.
8035.
[71] X.Wang,J.Lin,N.Patel,andM.W.Braun,“Aself-learningandonline
| [50] F. Pedregosa, |     | G. Varoquaux, | A.  | Gramfort, | V. Michel, | B.  | Thirion, |           |     |             |         |            |      |             |        |
| ------------------ | --- | ------------- | --- | --------- | ---------- | --- | -------- | --------- | --- | ----------- | ------- | ---------- | ---- | ----------- | ------ |
|                    |     |               |     |           |            |     |          | algorithm | for | time series | anomaly | detection, | with | application | in CPU |
O.Grisel,M.Blondel,P.Prettenhofer,R.Weiss,V.Dubourg,J.Vander-
Plas,A.Passos,D.Cournapeau,M.Brucher,M.Perrot,andE.Duches- manufacturing,” in Proceedings of the ACM International Conference
nay, “Scikit-learn: Machine learning in python,” J. Mach. Learn. Res., onInformationandKnowledgeManagement(CIKM),2016,pp.1823–
1832.
vol.12,pp.2825–2830,2011.
|               |           |     |              |     |            |                  |     | [72] M. West, | “Time | series | decomposition,” |     | Biometrika, | vol. | 84, no. 2, pp. |
| ------------- | --------- | --- | ------------ | --- | ---------- | ---------------- | --- | ------------- | ----- | ------ | --------------- | --- | ----------- | ---- | -------------- |
| [51] J. Peng, | J. Zhang, | C.  | Li, G. Wang, | X.  | Liang, and | L. Lin, “Pi-NAS: |     |               |       |        |                 |     |             |      |                |
489–494,1997.
| Improving | neural | architecture | search | by  | reducing | supernet | training |                |     |          |            |     |          |             |           |
| --------- | ------ | ------------ | ------ | --- | -------- | -------- | -------- | -------------- | --- | -------- | ---------- | --- | -------- | ----------- | --------- |
|           |        |              |        |     |          |          |          | [73] F. Wiewel | and | B. Yang, | “Continual |     | learning | for anomaly | detection |
consistencyshift,”inProceedingsoftheIEEEInternationalConference
onComputerVision(ICCV),2021,pp.12334–12344. withvariationalautoencoder,”inProceedingsoftheIEEEInternational
|                |     |           |         |          |           |        |         | Conference | on  | Acoustics, | Speech, | and | Signal | Processing | (ICASSP), |
| -------------- | --- | --------- | ------- | -------- | --------- | ------ | ------- | ---------- | --- | ---------- | ------- | --- | ------ | ---------- | --------- |
| [52] B. Poole, | S.  | Ozair, A. | van den | Oord, A. | A. Alemi, | and G. | Tucker, |            |     |            |         |     |        |            |           |
2019,pp.3837–3841.
| “On | variational | bounds | of mutual | information,” | in Proceedings |     | of the |     |     |     |     |     |     |     |     |
| --- | ----------- | ------ | --------- | ------------- | -------------- | --- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
[74] F.Xiao,Y.Wu,M.Zhang,G.Chen,andB.C.Ooi,“MINT:detecting
InternationalConferenceonMachineLearning(ICML),2019,pp.5171–
|       |     |     |     |     |     |     |     | fraudulent                             | behaviors |     | from time-series |     | relational | data,” | Proc. VLDB |
| ----- | --- | --- | --- | --- | --- | --- | --- | -------------------------------------- | --------- | --- | ---------------- | --- | ---------- | ------ | ---------- |
| 5180. |     |     |     |     |     |     |     | Endow.,vol.16,no.12,pp.3610–3623,2023. |           |     |                  |     |            |        |            |
[53] J. Ramakrishnan, E. Shaabani, C. Li, and M. A. Sustik, “Anomaly [75] H. Xu, W. Chen, N. Zhao, Z. Li, J. Bu, Z. Li, Y. Liu, Y. Zhao,
detectionforane-commercepricingsystem,”inProceedingsoftheACM
|        |               |     |            |              |           |     |      | D.      | Pei, Y. Feng, | J.  | Chen, Z.    | Wang,        | and H. | Qiao,        | “Unsupervised |
| ------ | ------------- | --- | ---------- | ------------ | --------- | --- | ---- | ------- | ------------- | --- | ----------- | ------------ | ------ | ------------ | ------------- |
| SIGKDD | International |     | Conference | on Knowledge | Discovery | and | Data |         |               |     |             |              |        |              |               |
|        |               |     |            |              |           |     |      | anomaly | detection     | via | variational | auto-encoder |        | for seasonal | KPIs in       |
Mining(SIGKDD),2019,pp.1917–1926.
webapplications,”inProceedingsoftheACMWebConference(WWW),
[54] S. Ruder, “An overview of gradient descent optimization algorithms,” 2018,pp.187–196.
CoRR,vol.abs/1609.04747,2016. [76] J. Xu, H. Wu, J. Wang, and M. Long, “Anomaly Transformer: Time
[55] R. Sekar, A. Gupta, J. Frullo, T. Shanbhag, A. Tiwari, H. Yang, and seriesanomalydetectionwithassociationdiscrepancy,”inProceedings
| S. Zhou,  | “Specification-based |              | anomaly | detection:  | A      | new approach   | for |        |               |            |     |             |                 |     |         |
| --------- | -------------------- | ------------ | ------- | ----------- | ------ | -------------- | --- | ------ | ------------- | ---------- | --- | ----------- | --------------- | --- | ------- |
|           |                      |              |         |             |        |                |     | of the | International | Conference |     | on Learning | Representations |     | (ICLR), |
| detecting | network              | intrusions,” | in      | Proceedings | of the | ACM Conference |     |        |               |            |     |             |                 |     |         |
2022,pp.1–20.
onComputerandCommunicationsSecurity(CCS),2002,pp.265–274. [77] Y. Yang, C. Zhang, T. Zhou, Q. Wen, and L. Sun, “DCdetector: Dual
[56] P. Senin, J. Lin, X. Wang, T. Oates, S. Gandhi, A. P. Boedihardjo, attention contrastive representation learning for time serifes anomaly
C. Chen, and S. Frankenstein, “Time series anomaly discovery with detection,” in Proceedings of the ACM SIGKDD International Confer-
grammar-basedcompression,”inProceedingsoftheInternationalCon-
enceonKnowledgeDiscoveryandDataMining(SIGKDD),2023,pp.
ferenceonExtendingDatabaseTechnology(EDBT),2015,pp.481–492.
3033–3045.
[57] K. Sequeira and M. J. Zaki, “ADMIT: Anomaly-based data mining [78] J.Yi,H.Yan,H.Wang,J.Yuan,andY.Li,“Deepsta:Aspatial-temporal
for intrusions,” in Proceedings of the ACM SIGKDD International attentionnetworkforlogisticsdeliverytimelyratepredictioninanomaly
ConferenceonKnowledgeDiscoveryandDataMining(SIGKDD),2002, conditions,” in Proceedings of the ACM International Conference on
pp.386–395. Information and Knowledge Management (CIKM), 2023, pp. 4916–
| [58] Y.Su,Y.Zhao,C.Niu,R.Liu,W.Sun,andD.Pei,“Robustanomaly |     |     |     |     |     |     |     | 4922. |     |     |     |     |     |     |     |
| ---------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
detectionformultivariatetimeseriesthroughstochasticrecurrentneural [79] A. Zeng, M. Chen, L. Zhang, and Q. Xu, “Are transformers effective
network,”inProceedingsoftheACMSIGKDDInternationalConference fortimeseriesforecasting?”inProceedingsoftheAAAIConferenceon
onKnowledgeDiscoveryandDataMining(SIGKDD),2019,pp.2828– ArtificialIntelligence(AAAI),2023,pp.11121–11128.
2837. [80] Y.Zhao,B.Deng,C.Shen,Y.Liu,H.Lu,andX.Hua,“Spatio-temporal
[59] A. Tarvainen and H. Valpola, “Mean teachers are better role mod- autoencoderfor videoanomalydetection,” inProceedingsof theACM
els:Weight-averagedconsistencytargetsimprovesemi-superviseddeep MultimediaConference(MM),2017,pp.1933–1941.
learningresults,”inProceedingsoftheConferenceonNeuralInforma- [81] C. Zhou and R. C. Paffenroth, “Anomaly detection with robust deep
tionProcessingSystems(NeurIPS),2017,pp.1195–1204. autoencoders,”inProceedingsoftheACMSIGKDDInternationalCon-
[60] D.M.J.TaxandR.P.W.Duin,“Supportvectordatadescription,”Mach. ference on Knowledge Discovery and Data Mining (SIGKDD), 2017,
| Learn.,vol.54,no.1,pp.45–66,2004. |     |     |     |     |     |     |     | pp.665–674.   |          |     |         |           |              |     |             |
| --------------------------------- | --- | --- | --- | --- | --- | --- | --- | ------------- | -------- | --- | ------- | --------- | ------------ | --- | ----------- |
|                                   |     |     |     |     |     |     |     | [82] B. Zong, | Q. Song, | M.  | R. Min, | W. Cheng, | C. Lumezanu, |     | D. Cho, and |
[61] M.Theodosiou,“Forecastingmonthlyandquarterlytimeseriesusingstl
decomposition,”Int.J.Forecast.,vol.27,no.4,pp.1178–1195,2011. H.Chen,“Deepautoencodinggaussianmixturemodelforunsupervised
[62] H.Tian,N.L.D.Khoa,A.Anaissi,Y.Wang,andF.Chen,“Conceptdrift anomalydetection,”inProceedingsoftheInternationalConferenceon
adaptionforonlineanomalydetectioninstructuralhealthmonitoring,” LearningRepresentations(ICLR),2018.
| in Proceedings |     | of the | ACM International |     | Conference | on Information |     |     |     |     |     |     |     |     |     |
| -------------- | --- | ------ | ----------------- | --- | ---------- | -------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
andKnowledgeManagement(CIKM),2019,pp.2813–2821.
| [63] M. Tschannen,J. |        | Djolonga,P.          | K.Rubenstein, |            | S.Gelly,       | andM.       | Lucic, |     |     |     |     |     |     |     |     |
| -------------------- | ------ | -------------------- | ------------- | ---------- | -------------- | ----------- | ------ | --- | --- | --- | --- | --- | --- | --- | --- |
| “On                  | mutual | information          | maximization  | for        | representation | learning,”  | in     |     |     |     |     |     |     |     |     |
| Proceedings          |        | of the International |               | Conference | on Learning    | Representa- |        |     |     |     |     |     |     |     |     |
tions(ICLR),2020.
15
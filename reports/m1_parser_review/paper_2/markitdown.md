1
Learning Graph Structures with Transformer for
Multivariate Time Series Anomaly Detection in IoT
Zekai Chen, Student Member, IEEE, Dingshuo Chen, Xiao Zhang, Member, IEEE, Zixuan Yuan,
and Xiuzhen Cheng, Fellow, IEEE
Abstract—Many real-world IoT systems, which include a Inthiswork,wefocusonanomalydetectionformultivariate
varietyofinternet-connectedsensorydevices,producesubstantial time series [8] as a copious amount of IoT sensors in many
amounts of multivariate time series data. Meanwhile, vital IoT
real-life scenarios consecutively generate substantial volumes
infrastructureslikesmartpowergridsandwaterdistributionnet-
oftimeseriesdata.Forinstance,inaSecureWaterDistribution
worksarefrequentlytargetedbycyber-attacks,makinganomaly
detectionanimportantstudytopic.Modelingsuchrelatednessis, (WADI) system [9], multiple sensing measurements such as
nevertheless, unavoidable for any efficient and effective anomaly flowing meter, transmitting level, valve status, water pressure
detection system, given the intricate topological and nonlinear level, etc., are recorded simultaneously at each timestamp to
connectionsthatareoriginallyunknownamongsensors.Further-
form a multivariate time series. In this case, the central water
more, detecting anomalies in multivariate time series is difficult
treatment testbed is also known as an entity. It is commonly
due to their temporal dependency and stochasticity. This paper
presented GTA, a new framework for multivariate time series accepted to detect anomalies from the entity-level instead of
anomaly detection that involves automatically learning a graph the sensor-level since the overall status detection is generally
structure,graphconvolution,andmodelingtemporaldependency worth more concern and less expensive. Predominantly, data
usingaTransformer-basedarchitecture.Theconnectionlearning
from these sensors are highly correlated in a complex topo-
policy,whichisbasedontheGumbel-softmaxsamplingapproach
logical and nonlinear fashion: for example, opening a valve
to learn bi-directed links among sensors directly, is at the heart
oflearninggraphstructure.Todescribetheanomalyinformation would result in pressure and flow rate changes, leading to
flow between network nodes, we introduced a new graph convo- further chain reactions of other sensors within the same entity
lution called Influence Propagation convolution. In addition, to followinganinternalmechanism.Nevertheless,thedependen-
tackle the quadratic complexity barrier, we suggested a multi-
cies among sensors are initially hidden and somehow costly
branch attention mechanism to replace the original multi-head
to access in most real-life scenarios, leading to an intuitive
self-attention method. Extensive experiments on four publicly
available anomaly detection benchmarks further demonstrate question of how to model such complicated relationships
thesuperiorityofourapproachoveralternativestate-of-the-arts. between sensors without knowing prior information?
Codes are available at https://github.com/ZEKAICHEN/GTA. Recently,deeplearning-basedtechniqueshavedemonstrated
Index Terms—Multivariate time series, anomaly detection, some promising improvements in anomaly detection due to
graph learning, self-attention the superiority in sequence modeling over high-dimensional
datasets. Generally, the existing approaches can roughly fall
into two lines: reconstruction-based models (R-model) [10],
I. INTRODUCTION
[11], [12], [6], [13] and forecasting-based models (F-model)
DuetothefastrisingnumberofInternet-connectedsensory [14], [15], [8], [16], [17], [4]. For example, Auto-Encoders
devices,theInternetofThings(IoT)infrastructurehascreated (AE) [10] is a popular approach for anomaly detection, which
vast sensory data. IoT data is often characterized by its uses reconstruction error as an outlier score. More recently,
speed in terms of geographical and temporal dependency Generative Adversarial Networks (GANs) [18], [19] based
[1], [2], and it is frequently subjected to correspondingly on reconstruction [20], [6] and RNN-based forecasting ap-
rising abnormalities and cyberattacks [3], [4]. Many critical proaches [8], [17] have also reported promising performance
infrastructures constructed on top of Cyber-Physical Systems for multivariate anomaly detection. However, these methods
(CPS) [5], such as smart power grids, water treatment and do not explicitly learn the topological structure among sen-
distributionnetworks,transportation,andautonomouscars,are sors, thus leaving room for improvements in modeling high-
especially in need of security monitoring [6], [7], [4]. As dimensional sensor data with considerable potential inter-
a result, an efficient and accurate anomaly detection system relationships appropriately.
has great research value because it can help with continuous Graph Convolutional Networks (GCNs) [21], [22], [23],
monitoringoffundamentalcontrolsorindicatorsandpromptly [24] have recently revealed discriminative power in learning
provide notifications for any probable anomalous occurrence. graph representations due to their permutation-invariance, lo-
calconnectivity,andcompositionality[21],[25].Graphneural
Z.CheniswiththeDepartmentofComputerScience,GeorgeWashington
networks allow each graph node to acknowledge its neigh-
University,Washington,DC,20052USA(email:zech chan@gwu.edu)
Z. Yuan is with the School of Business, Rutgers University, New Jersey, borhood context by propagating information through struc-
08901USA(email:zy101@rutgers.edu) tures. Recent works [17], [26], [4] then combined temporal
X.Zhang(correspondingauthor),X.ChengandD.ChenarewithSchool
modeling methods with GCNs to model the topological rela-
of Computer Science and Technology, Shandong University, China (emails:
xiaozhang@sdu.edu.cn,xzcheng@sdu.edu.cn) tionships between sensors. Specifically, most existing graph-
2202
naJ
71
]GL.sc[
3v66430.4012:viXra

2
based approaches [25], [4] aim to learn the graph structure II. RELATEDWORK
by measuring the cosine similarity (or other distance metrics)
The existing literature for addressing time series anomaly
between sensor embeddings and defining top-K closest nodes
detection usually can be divided into two major categories.
asthesourcenode’sconnections,followedbyagraphattention
The first category usually modeled each time series variable
convolution to capture the information propagation process.
independently, while the second category took into considera-
However,wearguethat(1)dotproductsamongsensorembed-
tionthecorrelationsamongmultivariatetimeseriestoimprove
dings lead inevitably to quadratic time and space complexity
the performance.
regarding the number of sensors; (2) the tightness of spatial
distance can not entirely indicate that there exists a strong
connection in a topological structure. A. Anomaly Detection in Univariate Time Series
The anomaly detection in univariate time series has drawn
To address the problems above, we propose an innova-
tive framework named Graph Learning with Transformer for many researchers’ attentions in recent years. Traditionally,
Anomaly detection (GTA) in this paper. We devise from the the anomaly detection frameworks included two main phases:
estimationphaseanddetectionphase[28].Inestimationphase,
perspective of learning a global bi-directed graph structure
involving all sensors within the entity through a connec- the variable values at one timestamp or time interval can
tion learning policy based on the Gumbel-Softmax Sampling be predicted or estimated by specific algorithm. Then the
estimated values were compared with real values based on
trick to overcome the quadratic complexity challenge and
the limitations of top-K nearest strategy. The policy logits dynamically adjusted thresholds to detect anomalies in detec-
tion phase. For example, Zhang et. al [29] applied ARIMA
can automatically discover the hidden associations during the
to capture the linear dependencies between the future values
training process by determining whether any specific node’s
and the past values, thus modeling the time series behavior
information should flow to the other targets to achieve the
for anomaly detection. Lu et.al [30] utilized wavelet analysis
best forecasting accuracy while restricting each node’s neigh-
to construct the estimation model. With the development of
borhoods’ scope as much as possible. The discovered hidden
deep learning, various neural network architectures have also
associations are then fed into the graph convolution layers
been applied to anomaly detection. DeepAnt [31] was an
forinformationpropagationmodeling.Wethenintegratethese
unsupervised approach using convolutional neural network
graph convolution layers with different level dilated convolu-
(CNN) to forecast future time series values and adopted
tion layers to construct a hierarchical context encoding block
specificallyfortemporaldata.Whilerecurrentmechanismscan Euclidean distance to measure the discrepancy for anomaly
be naturally applied to temporal dependency modeling, it is detection. The LSTM neural network was also widely used
hard to parallelize in many mobile environments (e.g., IoT), in modeling time series behaviors [32], [33], [6]. The LSTM-
whichrequirehighcomputationefficiency.Henceweadoptthe based encoder-decoder [32] reconstructed the variable values
Transformer[27]basedarchitectureforthesequencemodeling and measured the reconstruction errors for detection.
and forecasting due to the parallel efficiency and capability of
capturing long-distance context information. We also propose B. Anomaly Detection in Multivariate Time Series
anovelmulti-branchattentionstrategytoreducethequadratic
In real-world scenarios, the time series data acquisition
complexity of original self multi-head attention.
sources could be multiple [34]. Therefore, many work began
The main contributions of our work are summarized as to pay attention to exploiting the correlations among multiple
follows: variablestoimprovetheaccuracyofanomalydetection.Jones
et.al [35] extracted statistical and smoothed trajectory (SST)
• We propose a novel and differentiable connection learn- features of time series and utilized a set of non-linear func-
ing policy to automatically learn the graph structure of tions to model related variables to detect anomalies. Using
dependency relationships between sensors. Meanwhile, the LSTM network as the base models to to capture the
eachnode’sneighborhoodfieldisrestrictedbyintegrating temporal correlations of time series data, MAD-GAN [6]
a new loss term for further inference efficiency. proposed an unsupervised anomaly detection method com-
• We introduce a novel graph convolution named Informa- bining generative adversarial networks (GAN) by considering
tion Propagation (IP) convolution to model the anomaly complexdependenciesamongstdifferenttimeseriesvariables.
influence flowing process. A multi-scale dilated convo- Sakurada et al. [36] conducted dimentionality reduction based
lution is then combined with the graph convolution to on autoencoders for anomaly detection. The ODCA frame-
form an effective hierarchical temporal context encoding work [37] included three parts: data preprocessing, outlier
block. analysis, and outlier rank, which used cross correlation to
• We propose a novel multi-branch attention mechanism translate high-dimentional data sets to one-dimentional cross-
to tackle the original multi-head attention mechanism’s correlation function. OmniAnomaly [13] was a stochastic
quadratic complexity challenge. model to avoid potential misguiding by uncertain instances,
• We conduct extensive experiments on a wide range of which used stochastic variable connection and normalizing
multivariate time series anomaly detection benchmarks flow to get reconstruction probabilities and adopted stream-
to demonstrate the superiority of our proposed approach ing POT with drift (DSPOT) algorithm [38] for automatic
over state-of-the-arts. threshold selection. Senin et al. [39] proposed two algorithms

3
Fig.1:ThevisualizationofourproposedGTA’sarchitecturewithl levelsdilatedconvolutionandgraphconvolution,3encoder
layers,and1decoderlayer.Generally,theinputmultivariatetimeseriesinputsaresplitintotrainsequencesandlabelsequences,
of which train sequences are fed into encoder while label sequences are fed to the decoder.
that conducted symbolic time series discretization and used thetotalnumberofsensorsoranydatameasuringnodewithin
grammar reduction to compress the input sequence and com- the same entity. M is also reported as the number of features
pactly encode them with grammar rules. Those rarely used or variables in some literature [6], [13], [4]. Considering
substrings in the grammar rules were regarded as anomalies. the high unbalance between normal data and anomalies, we
Autoregressive with exogenous inputs (ARX) and artificial only construct the sequence modeling process on normal data
neural network (ANN) [40] extracted time-series features and (withoutanomalies)andmakepredictionontestingdata(with
detected anomalous data points by conducting hypothesis anomalies) for anomaly detection. Specifically, we let X and
Xˆ
testing on the extrema of residuals. represent the entire normal data and data with anomalies,
To cover the shortage that the convolution and pooling respectively.Forsequencemodelingonnormaldata,weinherit
operators of CNNs are defined for regular grids, recent GNN a forecasting-based strategy to predict the time series value
|     |     |     |     |     |     | x(t) | ∈RM |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ---- | --- | --- | --- | --- | --- |
[41] generalizes CNNs to graphs that are able to encode atnexttimestept(aka.single-steptimeseriesfore-
irregular and non-Euclidean structures. GNN adopted the casting)basedonthehistoricaldatax={x(t−n),··· ,x(t−1)}
localizedspectralfiltersandusedagraphcoarseningalgorithm withaspecificwindowsizen.Therefore,givenasequenceof
to cluster similar vertices for speeding up. In this way, GNN historicalntimestepsofmultivariatecontiguousobservations
efficiently extracted the local stationary property and captured xˆ ∈ RM×n, the goal of anomaly detection is to predict the
|     |     |     |     |     |     |     |     | Rn, | yˆ(t) |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ----- | --- | --- |
thecorrelationbetweennodes.Inreal-worldIoTenvironment, output vector yˆ ∈ where ∈ {0,1} denotes binary
the graph structure modeling the correlations between sensors labels indicating whether there is an anomaly at time tick t.
| is often | not predefined | in  | advance. | Graph deviation | network |            |              |          |         |            |       |
| -------- | -------------- | --- | -------- | --------------- | ------- | ---------- | ------------ | -------- | ------- | ---------- | ----- |
|          |                |     |          |                 |         | Precisely, | our proposed | approach | returns | an anomaly | score |
(GDN) [4] learned the pairwise relationship by cosine simi- for each testing timestamp, and then the anomaly result can
larity to elaborate adjacent matrix which can be modeled as a be obtained via selecting different thresholds.
| graph. Then       | it predicted |              | the future values | by graph       | attention- |     |              |      |                     |          |     |
| ----------------- | ------------ | ------------ | ----------------- | -------------- | ---------- | --- | ------------ | ---- | ------------------- | -------- | --- |
|                   |              |              |                   |                |            | We  | also provide | some | basic graph-related | concepts | for |
| based forecasting |              | and computed | the               | absolute error | value      | to  |              |      |                     |          |     |
evaluate graph deviation score. MTAD-GAN [17] concate- better understanding formulated as follows:
| nated feature-oriented |     | and | time-oriented | graph attention | layer |     |     |     |     |     |     |
| ---------------------- | --- | --- | ------------- | --------------- | ----- | --- | --- | --- | --- | --- | --- |
tolearngraphstructureandusedbothforecasting-basedmodel Definition III.1 (Graph). A directed graph is formulated as
|                          |     |     |          |                      |       | G = | (V,E) where | V = {1,··· | ,M} is | the set of nodes, | and |
| ------------------------ | --- | --- | -------- | -------------------- | ----- | --- | ----------- | ---------- | ------ | ----------------- | --- |
| and reconstruction-based |     |     | model to | calculate integrated | loss. |     |             |            |        |                   |     |
Then automatic threshold algorithm was adopted to perform E ⊆ V × V is the set of edges, where e represents the
i,j
anomaly detection. uni-directed edge flowing from node i to node j.
III. PROBLEMSTATEMENT Definition III.2 (Node Neighborhood). Let i ∈ V denote a
In this work, we focus on the task of multivariate time node and e ∈ E denote the edge pointing from node i to
i,j
series anomaly detection. Let X(t) ∈RM denote the original nodej.TheneighborhoodofanynodeiisdefinedasN(i)=
| multivariate | time | series data | at any | timestamp t, where | M   | is {j ∈V|e | i,j ∈E}. |     |     |     |     |
| ------------ | ---- | ----------- | ------ | ------------------ | --- | ---------- | -------- | --- | --- | --- | --- |

4
(see Fig. 2). Similarly, by Gumbel-Max trick, we can sample
any pair of nodes’ connection strategy zi,j ∈{0,1}2 with:
zi,j =argmax(logπi,j +gi,j) (1)
c c
c∈{0,1}
where g ,g are i.i.d samples drawn from a standard Gumbel
0 1
distribution which can be easily sampled using inverse trans-
Fig. 2: Suppose we have 3 sensors (N ,N ,N ) of which the form sampling by drawing u∼ Uniform(0,1) and computing
1 2 3
dependenciesareyethidden.Ourconnectionlearningpolicy’s g = −log(−logu). We further substitute this argmax oper-
main idea is to use the Gumbel-Softmax Sampling strategy to ation, since it is not differentiable, with a Softmax reparam-
sample a random categorical vector for determining whether eterization trick, also known as Gumbel-Softmax trick, as:
anydirectedconnectionbetweentwonodescanbeestablished. exp((logπi,j +gi,j)/τ)
For N 1 and N 2 , if the value of P 1,2 is relatively high, it z c i,j = (cid:80) exp((lo c gπi,j c +gi,j)/τ) (2)
represents N is highly possibly pointed to N , vice versa. v v
1 2 v∈{0,1}
where c ∈ {0,1} and τ is the temperature parameter to
IV. METHODOLOGY control Gumbel-Softmax distribution’s smoothness, as the
temperature τ approaches 0, the Gumbel-Softmax distribution
Inmostreal-lifescenariosofIoT,thereareusuallycomplex
becomes identical to the one-hot categorical distribution. As
topological relationships between sensors where the entire
therandomnessofg isindependentofπ,wecannowdirectly
entity can be seen as a graph structure. Each sensor is also
optimize our gating control policy using standard gradient
viewedasaspecificnodeinthegraph.Previousmethods[25],
descent algorithms.
[4] focused on applying various distance metrics to measure
Compared to the previous graph structure learning ap-
the relations between nodes mostly by selecting the top-K
proaches, our proposed method significantly reduces the com-
closest ones as their neighbor dependencies. Different from putation complexity from O(M2) to O(1) since it requires
existing approaches, we devise a directed graph structure
no dot products among high-dimensional node embeddings.
learning policy (see Fig. 1) to automatically learn the adja-
Additionally, the graph structure learning policy is able to
cency matrix among nodes such that the network can achieve
automatically learn the global topological connections among
the maximum benefits. The core of the learning policy is
allnodes,therebyavoidingthelimitationofselectingonlythe
named Gumbel-Softmax Sampling strategy [42], [43] inspired
top-K nearest nodes as neighbors.
bythepolicylearningnetworkinmanyreinforcementlearning
methods [44], [45]. These discovered hidden associations are
B. Influence Propagation via Graph Convolution
then fed into the graph convolution layers for information
propagation modeling. We then integrate these graph convo- On top of the learned topological structure, the graph
lution layers with different level dilated convolution layers convolution block aims to further model the influence propa-
together to construct a hierarchical context encoding block gation process and update each specific node’s representation
specifically for temporal data. The outputs of the context by incorporating its neighbors’ information. Considering the
encoding block are then applied positional encoding as the characteristics of tasks such as anomaly detection, usually,
inputsofTransformer[27]forsingle-steptimeseriesforecast- the occurrence of abnormalities is due to a series of chain
ing. We also propose a global attention strategy to overcome influences caused by one or several nodes being attacked.
the quadratic computation complexity challenge of the multi- Therefore, it is intuitive for us to model the relationships
head attention mechanism. Fig. 1 further illustrates the entire between upstream and downstream nodes by capturing both
architecture in detail. temporal and spatial differences. Thus, we define our Influ-
ence Propagation (IP) convolution process concerning each
specific node and its neighborhoods by applying a node-wise
A. Gumbel-Softmax Sampling symmetric aggregating operation (cid:3) (e.g., add, mean, or max)
The sampling process of discrete data from a categori- onthedifferencesbetweennodesassociatedwithalltheedges
cal distribution is originally non-differentiable, where typical emanating from each node. The updated output of IPConv at
backpropagationindeepneuralnetworkscannotbeconducted. the i-th node is given by:
[42], [43] proposed a differentiable substitution of discrete (cid:88)
x(cid:48) = h (x ||x −x ||x +x ) (3)
random variables in stochastic computations by introducing i Θ i j j j i
Gumbel-Softmax distribution, a continuous distribution over j∈N(i)
the simplex that can approximate samples from a categorical where(cid:3)ischosenassummationinourmethod,h denotesa
Θ
distribution. In our graph learning policy with a total number neural network, i.e.MLPs (Multi-layer Perceptrons), x ∈RT
i
of M candidate nodes, we let zi,j be a binary connection represents the time series embedding of node i and || de-
controlvariableforanypairofnodesiandj withuni-directed notes the concatenation operation. We denote x −x as the
j i
probabilities from node i to node j as {πi,j,πi,j}, where differences between nodes to explicitly model the influence
0 1
πi,j +πi,j = 1 and πi,j represents the probability that there propagation delay from node j to i, captured by the value
0 1 1
exists an information flow from node i to node j in the graph differenceateachtimestampofthetimeseriesembedding.We

5
above to fully explore the temporal context modeling process
with different sequence lengths and receptive fields by setting
multi-scaledilationsizes.Specifically,asFig.3illustrates,the
bottom layer represents the multivariate time series input (for
some time t, onto which repeated dilated convolutions, with
increasing dilation rates, are applied; the filter width is again
set to equal two in the observed model). The first level block
appliesdilatedconvolutionswiththedilationrateequaltoone,
meaning that the layer applies the filter onto two adjacent
elements, x(t) and x(t+1), of the input series. The outputs
of the first-level dilated convolutions are fed into the graph
Fig. 3: Visualization of hierarchical dilated convolution com- convolution module proposed above. Then the second-level
bined with graph convolution. layer applies dilated convolutions, with the rate now set to
equaltwo,whichmeansthatthefilterisappliedontoelements
x(t) and x(t+2) (notice here that the number of parameters
also incorporate the term x i +x j with the differences to work remainsthesame,butthefilterwidthhasbeen“widened”).By
as a scale benchmark such that the model can learn the truly setting multi-scale dilation sizes with a hierarchical learning
generalized impact to the other nodes brought by anomalies style, abundant temporal representations concerning different
instead of extreme values. Intuitively, for any specific node temporal positions and sequence lengths can be effectively
i, if one of its neighbor nodes j being attacked, node i learned.
shall be severely affected sooner or later due to the restricted The hierarchical dilated convolution and the graph convo-
topological relationship. lution together form the temporal context embedding progres-
TrainingStrategyandRegularization.Graphconvolution sion where dilated convolution captures the long-term tempo-
basedonthelearneddependenciesamongsensorsonlyaggre- ral dependencies while graph convolution describes the topo-
gates the information from nodes’ neighbors without taking logical connection relationships between sensors (or nodes).
efficiency into account. Under the extreme circumstance that As a result, the final outputs have been well represented to be
all nodes are mutually connected, aggregating neighborhood theinputsofthenextforecastingprocedureusingTransformer
information adds considerable noise to each node. However, architecture.
it is preferred to form a compact sub-graph structure for
everysinglenode,inwhichredundantconnectionsareomitted
as much as possible without deteriorating the forecasting
D. More Efficient Multi-branch Transformer
accuracy. To this end, we propose a sparsity regularization
L s to enhance the compactness of each node by minimizing Transformer [27] has been widely used in sequence model-
the log-likelihood of the probability of a connection being ingduetothesuperiorcapabilityofmulti-headattentionmech-
established as anism in long-distance dependencies capturing. However, one
L = (cid:88) logπi,j (4) mainefficiencybottleneckinself-attentionisthatthepairwise
s 1 tokeninteractiondot-productionincursacomplexityofO(n2)
1≤i,j≤M,i(cid:54)=j
with respect to sequence length. To tackle this challenge, in
Furthermore, to encourage better learning convergence, the
this section, we first briefly review the background of some
connection learning policy is initialized with all nodes con-
recent development of multi-head attention mechanism and
nected. We warm up the network weights by training with
then propose a more efficient Transformer architecture based
this complete graph structure for a few epochs to provide a
on the innovative multi-branch attention mechanism which is
good starting point for the policy learning.
more computationally efficient.
Self-attention in Transformers. The vanilla multi-head
C. Hierarchical Dilated Convolution
self-attention mechanism was originally proposed by [27].
The dilated convolution [46] is widely used in sequence For a sequence of token representations X ∈ Rn×d (with
modelingduetoitspowerfulcapabilityinextractinghigh-level sequence length n and dimensionality d), the self-attention
temporal context features by capturing sequential patterns of function firstly projects them into queries Q ∈ Rn×dk, keys
time series data through standard 1D convolution filters. Set- K ∈ Rn×dk and values V ∈ Rn×dv, h times with different,
tingdifferentdilationsizelevelscandiscovertemporalpatterns learned linear projections to d , d and d dimensions, re-
k k v
withvariousrangesandhandleverylongsequences.However, spectively. Then a particular scaled dot-product attention was
choosing the right kernel size is often a challenging prob- computed to obtain the weights on the values as:
lem for convolutional operations. Some previous approaches
adopted the widely employed inception learning strategy [47] QKT
Attention(Q,K,V)=Softmax( √ )V (5)
incomputervisionwhichconcatenatestheoutputsofconvolu- d
k
tionalfilterswithdifferentkernelsizesfollowedbyaweighted
matrix.Unlikethem,weproposeahierarchicaldilatedconvo- Multi-head attention allows the model to jointly attend to in-
lution learning strategy combined with the graph convolution formation from different representation subspaces at different

6
(a) Vanilla multi-branch Trans- (b)Multi-branchTransformerwith (c) Our proposed multi-branch at-
former. global-fixed attention. tention mechanism.
Fig. 4: Different variants of efficient multi-branch attention mechanism. Right: Replacing vanilla multi-head attention with
a combination of both global-fixed attention and vanilla multi-head attention and neighborhood convolution by splitting
embeddings into multiple channels.
positions.Withaconcatenatedcomputingway,thefinaloutput alignment matrix that learns globally across all training sam-
of multi-head attention is as following: pleswhereattentionweightsarenolongerconditionedonany
input token in our architecture. By simply replacing the dot-
MultiHead(Q,K,V)=Concat(head ,··· ,head )WO
1 h production with global-learned alignment as Fig. 4 shows, the
(6)
input sequences will only be projected into value matrices. A
inwhich,histhenumberoftotalheads.Eachheadisdefined
weightedsumupofvaluesisthencalculatedusingthisglobal-
as:
learnedattention.Inordertoexploreabettertrade-offbetween
head i =Attention(QW i Q,KW i K,VW i V) (7) computation efficiency and model performance, we propose
to combine the pairwise token interactions and global-learned
where the projections are parameter matrices WQ ∈ Rd×dk,
i attention in terms of a branch-wise mixing strategy.
WK ∈Rd×dk, WV ∈Rd×dv and WO ∈Rhdv×d.
i i Branch-wise Mixing. For branch-wise mixing, the input
Global-learnedAttention.Recentresearch[48],[49]claim
sequencesaresplitintomultiplebranchesalongtheembedding
that the self-attention in Transformers can be substantially
dimension as Fig. 4 clearly describes. Different from the
simplified with trivial attentive patterns at training time: only
original two-branch architecture, we build one more branch
preservingadjacentandprevioustokensisnecessary.Theadja-
for global-learned attention. Thus,
cent positional information such as ”current token”, ”previous
token”and”nexttoken”arethekeyfeatureslearnedacrossall Attention=Concat(A(1),A(2))
layers by encoder self-attention. Instead of costly learning the
A(1) =MultiHead(X(1)) (9)
trivial pattern using massive corpus with considerable compu-
tational resources, the conventional pairwise token interaction
A(2) =Global(X(2))
attention could be replaced by a more computation-efficient
global attention pattern. In practice, manually pre-define all
where X(1) ∈Rn×d1, X(2) ∈Rn×d2 and d=d
1
+d
2
.
In our models, we only change the branch that captures
global-fixed patterns is easy to implement but can barely
theglobalcontextswhileremainingthelocalpatternextractor
cover all possible situations. To generalize the global-fixed
using either lightConv or dynamicConv [53].
attentionpatternproposedin[50],weapplyaparametermatrix
Computation Analysis. Table I lists the different model
S ∈ Rm×m (m > n) as a learnable global compatibility
variantsexploredwithinourproposedframework.Thecolumn
function across all training samples following the Synthesizer
|θ| refers to the total number of parameters in one self-
[51]. Hence, each head adds m2 parameters while reducing
attentionmodule excluding thefeed-forward layer.Obviously,
two projection matrices WQ and WK. The attention now has
comparedtotheoriginalscaleddot-production,theamountof
been as following:
computation of global-learned attention is directly reduced by
Attention(S,V)=Softmax(S)V (8) halfintermsofMult-Adds.Ourproposedmulti-branchmixing
strategyincreasestheamountofcalculationinvaryingdegrees
where S is a learnable matrix which can be randomly initial- due to the mix with scaled dot-production. However, this is
ized. a trade-off between computation complexity and model size.
Multi-branch Architecture for Transformers. [52] has More precisely, when m≤ (cid:112) 2/hd, the global attention mod-
demonstrated the effectiveness of multi-branch attention in ule is more computationally efficient than the other variants.
capturing global and local context patterns, especially under
mobile computational constraints. As Fig. 4 illustrates, this
E. Anomaly Scoring
double-branch architecture splits the original input sequences
into two pieces along the embedding channel, followed by Inspiredby[54],theoriginalmultivariatetimeseriesinputs
two attention branches: one convolution branch for extracting aresplitintotwoparts:trainingsequencesfortheencoderand
information in a restricted neighborhood and one multi-head label sequences for the decoder. The decoder receives long
attention branch for capturing long-distance dependencies. As sequence inputs, pads the target elements into zero, measures
a substitute for vanilla self-attention, we apply a task-specific the weighted attention composition of the feature map, and

7
TABLE I: Memory and computation analysis on different attention types.
AttentionType |θ| #Mult-Adds Global/Inter
ScaledDot-Product 4d2 O(4nd2+2n2d) Inter
Global-Learned m2h+2d2 O(2nd2+n2d) Global
Branch-WiseMixing 4d2
1
+m2h+2d2
2
O(4nd2
1
+n2d1+2nd2
2
+n2d) Both
instantly predicts output elements in a generative style. Let data samples for SWaT and WADI are downsampled to one
thesingle-steppredictiondenoteasYˆ ∈RM×n.Weapplythe measurement every 10 seconds by taking the median values
Mean Square Error (MSE) between the predicted outputs Yˆ following [4].
and the observation Y, as the loss function to minimize:
TABLEII:StatisticalsummaryofdatasetsSWaTandWADI.
n
L = 1 (cid:88) ||Y(t)−Yˆ(t)||2 (10)
mse M 2 Datasets SWaT WADI
t=1
Similartothelossobjective,theanomalousscorecompares Feature Desc. All sensors and actuators.
the expected value at time t to the observed value, computing # Features 51 112
# Attacks 41 15
an anomaly score via the deviation level as:
Attack durations (mins) 2 ∼ 25 1.5 ∼ 30
M Training size (normal data) 49619 120899
yˆ(t) = (cid:88) ||Y i (t)−Yˆ i (t)||2 2 (11) Testing size (data with attacks) 44931 17219
i=1 Anomaly rate (%) 12.14 5.75
Finally,welabelatimestamptasananomalyifyˆ(t) exceedsa
fixedthreshold.Sincedifferentapproachescouldbeemployed
TABLE III: Statistical summary of datasets SMAP and MSL.
tosetthethresholdsuchasextremevaluetheory[38],thesame
anomaly detection model could result in different prediction
Datasets SMAP MSL
performance with different anomaly thresholds. Thus, we
apply a grid search on all possible anomaly thresholds to Radiation, temperature,
Feature Desc.
search for the best F1-score (with notation ∗∗) and Recall power, etc.
(with notation ∗) in theory and report them. # Features 25 25
Training size (normal data) 135183 58317
Testing size (data with anomalies) 427617 73729
V. EXPERIMENTS
Anomaly rate (%) 13.13 10.72
A. Datasets
We evaluate our method over a wide range of real-world
anomaly detection datasets. SWaT [55] The Secure Water
B. Experimental Setup
Treatment dataset is collected from a water treatment testbed
1) Data preprocessing: We perform a data standardization
for cyber-attack investigation initially launched in May 2015.
before training to improve the robustness of our model. Data
The SWaT dataset collection process lasted for 11 days, with
preprocessing is applied on both training and testing set:
the system operated 24 hours per day such that the network
traffic and all the values obtained from all 51 sensors and x−minX
x˜= train (12)
actuators are recorded. Due to the system working flow char- maxX −minX
train train
acteristics, there is a natural topological structure relationship
wheremax(X )andmin(X )arethemaximumvalue
train train
between all sensing nodes. After this, a total of 41 attacks
and the minimum value of the training set respectively.
derived through an attack model considering the intent space
2) Evaluation metrics: We adopt the standard evaluation
of a CPS were launched during the last 4 days of the 2016
metrics in anomaly detection tasks, namely Precision, Recall
SWaT data collection process. As such, the overall sequential
and F1 score, to evaluate the performance of our approach, in
data is labeled according to normal and abnormal behaviors
which:
at each timestamp. WADI [9] Water Distribution dataset is TP
Precision= (13)
collected from a water distribution testbed as an extension TP+FP
of the SWaT testbed. It consists of a total of 16 days of
TP
continuous operations with 14 days under regular operation Recall= (14)
TP+FN
and 2 days with attack scenarios. The entire testbed contains
Precision×Recall
123 sensors and actuators. Moreover, SMAP (Soil Moisture F1=2× (15)
Active Passive satellite) and MSL (Mars Science Laboratory Precision+Recall
rover) are two public datasets published by NASA [56]. Each where TP represents the truly detected anomalies (aka. true
dataset has a training and a testing subset, and anomalies in positives), FP stands for the falsely detected anomalies (aka.
both testing subsets have been labeled [8]. false positives), TN represents the correctly classified normal
TableIIandIIIsummarisesthestatisticsofthefourdatasets. samples (aka. true negatives), and FN is the misclassified
In order to fair comparison with other methods, the original normal samples (aka. false negatives). Given the fact that

8
TABLE IV: Experimental results on SWaT and WADI.
Datasets Methods Precision(%) Recall(%) F1-score
PCA 24.92 21.63 0.23
KNN 7.83 7.83 0.08
FB 10.17 10.17 0.10
AE 72.63 52.63 0.61
DAGMM 27.46 69.52 0.39
LSTM-VAE 96.24 59.91 0.74
SWaT MAD-GAN 98.97 63.74 0.77
GDN 99.35 68.12 0.81
GTA∗ (ours) 74.91 96.41 0.84
GTA∗∗ 94.83 88.10 0.91
∆ (best F1) -4.55% +29.33% +12.35%
↑
PCA 39.53 5.63 0.10
KNN 7.76 7.75 0.08
FB 8.60 8.60 0.09
AE 34.35 34.35 0.34
DAGMM 54.44 26.99 0.36
LSTM-VAE 87.79 14.45 0.25
WADI MAD-GAN 41.44 33.92 0.37
GDN 97.50 40.19 0.57
GTA∗ (ours) 74.56 90.50 0.82
GTA∗∗ 83.91 83.61 0.84
∆ (best F1) -13.94% +108.04% +47.37%
↑
Best performance in bold. Second-best with underlines.
∗ represents the results chosen by best Recall.
∗∗ represents the results chosen by best F1-score.
∆ represents the percentage increase between our best F1-score
↑
performance and the second-best method (GDN).
TABLE V: Experimental results on SMAP and MSL.
SMAP MSL
Method
Precision(%) Recall(%) F1-score Precision(%) Recall(%) F1-score
KitNet 77.25 83.27 0.8014 63.12 79.36 0.7031
GAN-Li 67.10 87.06 0.7579 71.02 87.06 0.7823
R-Models LSTM-VAE 85.51 63.66 0.7298 52.57 95.46 0.6780
MAD-GAN 80.49 82.14 0.8131 85.17 89.91 0.8747
OmniAnomaly 74.16 97.76 0.8434 88.67 91.17 0.8989
LSTM-NDT 89.65 88.46 0.8905 59.44 53.74 0.5640
F-Models DAGMM 58.45 90.58 0.7105 54.12 99.34 0.7007
MTAD-GAT 89.06 91.23 0.9013 87.54 94.40 0.9084
GTA∗∗ (ours) 89.11 91.76 0.9041 91.04 91.17 0.9111
Best performance in bold. Second-best with underlines.
∗∗ represents the results chosen by best F1-score.
in many real-world anomaly detection scenarios, it is more in the ground truth anomaly segment, if it is detected as an
vital for the system to detect all the real attacks or anomalies anomaly or attack, we would consider this whole anomaly
by tolerating a few false alarms. As such, we generally give window is correctly detected and every observation point in
more concern to Recall and the overall F1 score instead this segment has been classified as anomalies. The observa-
of Precision. Considering different anomaly score thresholds tions outside the ground truth anomaly segment are treated as
may result in different metric scores, we hence report both usual. In all, we first train our model on the training set to
our best Recall and F1 results (with notations ∗ and ∗∗ learn the general sequence pattern and make the forecasting
respectively) on all datasets for a thorough comparison. on the test set for anomaly detection.
Also,weadoptthepoint-adjustwaytocalculatetheperfor- 3) Baselines: We compare our GTA with a wide range of
mancemetricsfollowing[13].Inpractice,anomalousobserva- state-of-the-arts in multivariate time series anomaly detection,
tions usually occur consecutively to form contiguous anomaly including: (1) reconstruction-based models: PCA, AE [10],
segments. An alert for anomalies can be triggered within any KitNet [57], DAGMM [12], GAN-Li [20], OmniAnomaly
subsetofanactualanomalywindow.Thus,foranyobservation [13], LSTM-VAE [11], MAD-GAN [6], and (2) forecasting-

9
basedmodels:KNN[14],FB[15],MTAD-GAT[17]andGDN TABLE VI: Anomaly detection accuracy in terms of preci-
|     |     |     |     |     |     |     |     | sion(%), | recall(%), | and | F1-score | of  | GTA | and its variants. |     |
| --- | --- | --- | --- | --- | --- | --- | --- | -------- | ---------- | --- | -------- | --- | --- | ----------------- | --- |
[4].
| 4) Training |           | Settings: | We      | implement    | our  | method | and  | all its |         |        |      |          |         |        |          |
| ----------- | --------- | --------- | ------- | ------------ | ---- | ------ | ---- | ------- | ------- | ------ | ---- | -------- | ------- | ------ | -------- |
|             |           |           |         |              |      |        |      |         |         |        | SWaT |          |         | WADI   |          |
|             |           | Pytorch1  |         |              |      |        |      | Method  |         |        |      |          |         |        |          |
| variants    | using     |           | version | 1.7.0        | with | CUDA   | 10.1 | and     |         |        |      |          |         |        |          |
|             |           |           |         |              |      |        |      |         | Prec(%) | Rec(%) |      | F1-score | Prec(%) | Rec(%) | F1-score |
| Pytorch     | Geometric | Library   |         | [58] version |      | 1.6.3. | We   | conduct |         |        |      |          |         |        |          |
all experiments on four NVIDIA Tesla P100 GPUs. For time GTA 94.83 88.10 0.91 83.91 83.61 0.84
|                     |     |              |         |            |             |         |           | w/oGraph | 88.64 |     | 65.73 | 0.75 | 71.25 | 68.23 | 0.70 |
| ------------------- | --- | ------------ | ------- | ---------- | ----------- | ------- | --------- | -------- | ----- | --- | ----- | ---- | ----- | ----- | ---- |
| series forecasting, |     | we           | set the | historical |             | window  | size      | to 60    |       |     |       |      |       |       |      |
|                     |     |              |         |            |             |         |           | w/oLP    | 89.36 |     | 72.12 | 0.80 | 79.56 | 77.10 | 0.78 |
| frames with         | a   | label series | length  | as         | 30 to       | predict | the value | at       |       |     |       |      |       |       |      |
|                     |     |              |         |            |             |         |           | w/oAttn  | 78.75 |     | 65.34 | 0.71 | 74.75 | 70.90 | 0.73 |
| next timestamp.     |     | The number   |         | of dilated | convolution |         | levels    | for      |       |     |       |      |       |       |      |
temporalcontextmodelingissetto3.Also,thegeneralmodel
inputembeddingdimensionissetto128.Fortheconventional
informationformodelingtheinherentstochasticityoftimese-
multi-head attention mechanism, the number of heads is set ries.LSTM-VAE[11]combinesLSTMwithVAEforsequence
to 8. In total, we have 3 encoder layers and 2 decoder layers modeling; however, it ignores the temporal dependencies
and the dimensional of fully connected network is set to 128 amonglatentvariables.OmniAnomaly[13]wasthenproposed
whichisequaltothemodeldimension.Additionally,weapply to solve this problem. Additionally, MAD-GAN [6] aims to
| the dropout | strategy | to  | prevent | overfitting |     | with | dropout | rate  |           |             |     |          |         |                |     |
| ----------- | -------- | --- | ------- | ----------- | --- | ---- | ------- | ----- | --------- | ----------- | --- | -------- | ------- | -------------- | --- |
|             |          |     |         |             |     |      |         | adopt | a general | adversarial |     | training | fashion | to reconstruct |     |
consistently equals to 0.05. The models are trained using the the original time series, which also uses recurrent neural
Adam optimizer with learning rate initialized as 1e−4 and networks. Nevertheless, the recurrent learning mechanism’s
β ,β
1 2 as 0.9, 0.99, respectively. A learning rate adjusting core properties restrict the modeling process to be sequential.
strategy is also applied. We train our models for up to 50 Past information has to be retained through the past hidden
epochs and early stopping strategy is applied with patience of states, limiting the long-term sequence modeling capability
10. We run each experiment for 5 trials and report the mean of the model. Transformer adopts a non-sequential learning
value. fashion, and the powerful self-attention mechanism makes the
|                 |     |         |     |     |     |     |     | context | distance   | between |      | any token  | of a | time series          | shrink   |
| --------------- | --- | ------- | --- | --- | --- | --- | --- | ------- | ---------- | ------- | ---- | ---------- | ---- | -------------------- | -------- |
|                 |     |         |     |     |     |     |     | to one, | which      | is of   | high | importance | to   | sequence             | modeling |
| C. Experimental |     | Results |     |     |     |     |     |         |            |         |      |            |      |                      |          |
|                 |     |         |     |     |     |     |     | as more | historical | data    | can  | provide    | more | pattern information. |          |
In Table IV, we show the anomaly detection accuracy in (4) Though GDN [4] is also a graph learning-based anomaly
terms of precision, recall, and F1-score, of our proposed GTA detection approach, it adopts the top-K nearest connection
method and other state-of-the-arts on datasets SWaT and strategy to model the topological graph structure among sen-
WADI. Each of these baselines provides a specific threshold sors,whichhavecertainlimitationsaswediscussedinSection
selection method, and the reported F1-score is calculated I. MTAD-GAT [17] directly utilizes the initial graph structure
correspondingly.OurproposedGTAsignificantlyoutperforms information by assuming all sensors are mutually connected,
all the other approaches on both datasets by achieving the making it a complete graph that is not suitable for many real-
| best F1-score |     | as 0.91 | for SWaT |     | and 0.84 | for | WADI. | As-              |     |     |     |     |     |     |     |
| ------------- | --- | ------- | -------- | --- | -------- | --- | ----- | ---------------- | --- | --- | --- | --- | --- | --- | --- |
|               |     |         |          |     |          |     |       | life situations. |     |     |     |     |     |     |     |
tonishingly, compared to the second-best model GDN, GTA From Table V, we can see that the overall improvements
can achieve an overall 12.35% increase and an impressive in terms of best F1-score on datasets SMAP and MSL are
47.47% improvement in terms of the best F1-score on these not as impressive as Table IV shows. We argue the main
two datasets, respectively. Moreover, we have the following difference of results between the NASA anomaly datasets
| observations: | (1) | Compared |     | to the | conventional |     | unsupervised |         |              |     |          |      |        |                     |     |
| ------------- | --- | -------- | --- | ------ | ------------ | --- | ------------ | ------- | ------------ | --- | -------- | ---- | ------ | ------------------- | --- |
|               |     |          |     |        |              |     |              | and the | Cyber-attack |     | datasets | lies | in the | features’ dependen- |     |
approachessuchasPCA,KNN,FB,deeplearning-basedtech- cies. SMAP provides measurements of the land surface soil
niques (AE, LSTM-VAE, MAD-GAN, etc.) generally have a moisture by measuring various separated attributes such as
betterdetectionperformanceonbothdatasets.Byadoptingthe radiation, temperature, computational activities, etc. Though
recurrent mechanism (RNN, GRU, LSTM) in modeling long these attributes are not entirely independent of each other,
| sequences | and | capturing | the | temporal | context |     | dependencies, |              |               |     |         |     |          |             |      |
| --------- | --- | --------- | --- | -------- | ------- | --- | ------------- | ------------ | ------------- | --- | ------- | --- | -------- | ----------- | ---- |
|           |     |           |     |          |         |     |               | the internal | relationships |     | between |     | them are | much weaker | than |
the deep learning-based methods demonstrate superiority over those within SWaT or WADI where any slight change that
the conventional methods. (2) DAGMM [12] aims to handle appears on one sensor can propagate to the whole network.
multivariate data without temporal information, indicating the Therefore, our proposed graph structure learning strategy
inputdatacontainsonlyoneobservationinsteadofahistorical might be more effective on datasets with a strong topological
| time series | window. | Hence |     | this approach |     | is not | suitable | for structure. |     |     |     |     |     |     |     |
| ----------- | ------- | ----- | --- | ------------- | --- | ------ | -------- | -------------- | --- | --- | --- | --- | --- | --- | --- |
temporaldependencymodeling,whichiscrucialformultivari-
| ate time  | series | anomaly   | detection. |          | (3) Most | existing   | methods |             |     |         |     |     |     |     |     |
| --------- | ------ | --------- | ---------- | -------- | -------- | ---------- | ------- | ----------- | --- | ------- | --- | --- | --- | --- | --- |
|           |        |           |            |          |          |            |         | D. Ablation |     | Studies |     |     |     |     |     |
| are based | on     | recurrent | neural     | networks |          | to capture |         | tempo-      |     |         |     |     |     |     |     |
ral dependency, including both reconstruction-based models To study each component of our approach’s effectiveness,
(LSTM-VAE, OmniAnomaly, MAD-GAN) and forecasting- we gradually exclude the elements to observe how the model
performancedegradesondatasetsSWaTandWADI.First,we
| based models | (LSTM-NDT, |     |     | MTAD-GAT). |     | Of which, |     | LSTM- |     |     |     |     |     |     |     |
| ------------ | ---------- | --- | --- | ---------- | --- | --------- | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
NDT[8]isadeterministicmodelwithoutleveragingstochastic study the significance of modeling the dependencies among
|     |     |     |     |     |     |     |     | sensors | using | graph | learning. | We  | directly | apply the | original |
| --- | --- | --- | --- | --- | --- | --- | --- | ------- | ----- | ----- | --------- | --- | -------- | --------- | -------- |
1https://pytorch.org/ time series as the inputs for the Transformer and make the

10
(a) Partial graph structure learned by the learning policy. (b) The attacked sensor with three other malicious sensors.
|     |     | Fig. 5: | A case study of | showing an | attack in | WADI. |     |     |     |
| --- | --- | ------- | --------------- | ---------- | --------- | ----- | --- | --- | --- |
forecasting without graph learned phase. Second, we study 1 MV 001 valve is turned on abruptly. As its outcome of
the significance of our proposed structure learning policy the first stage propagates the influence from the raw water
(LP) by substituting it with a static complete graph where transfer pump to the second stage, 2 FIT 001 PV is also
every node is bi-directionally linked to each other. Finally, vulnerable to the same malicious attack. In addition, as
to study the necessity of the Transformer-based architecture LEAK DIFF PRESSURE becomes irregular during this pro-
for sequence modeling, we substitute the Transformer with cedure,theleakingwaterpressuregrowswithoutadoubt.Our
a GRU-based recurrent neural network for forecasting. The graphlearningpolicylearnedapartialgraphinFig.5a,which
results are summarized in Table VI and provide the following almost properly depicts the topological interactions among
observations:(1)Ourproposedlearningpolicyhelpsthegraph sensors. The LEAD DIFF PRESSURE is almost related to
convolution operation by capturing only proper information every other displayed node as malicious information passes
flow with noises filtered out. (2) There is a considerable gap fromupstreamsensorstodownstreamones.Moreimportantly,
between GTA and the variant without graph learning which Fig.5bshowsourmodel’spredictedsensorcurves(bluelines)
again demonstrates the importance of topological structure against the ground truth (red lines) of sensor 1 FIT 001 PV,
modeling in handling multivariate time series anomaly detec- 2 FIT 001 PV, and 2 PIT 001 PV within the attack dura-
tion. (3) Transformer-based architecture exhibits superiority tion. The predictions of these sensors are consistently higher
in sequence modeling, where the self-attention mechanism than the ground truth, where the anomaly score increases
playsacriticalrole.Moreover,theseresultsagainconfirmthat correspondingly.Itismainlybecausetheinputtimeserieshas
every component of our method is indispensable and make been embedded with the graph structure information through
this framework powerful in multivariate time series anomaly the influence propagation convolution operation. Sensors that
detection. are not directly attacked will still be severely affected if
sensorsthatarehighlyrelatedtothemareattacked.Therefore,
|                   |                    |              |              | our model  | can         | capture this | dependency | and           | result in an |
| ----------------- | ------------------ | ------------ | ------------ | ---------- | ----------- | ------------ | ---------- | ------------- | ------------ |
| E. Graph Learning | and Case           | Study        |              |            |             |              |            |               |              |
|                   |                    |              |              | abnormal   | prediction, | which is     | vital for  | the following | anomaly      |
| By introducing    | a case study       | of an actual | attack from  | detection. |             |              |            |               |              |
| the Cyber-attack  | dataset WADI,      | we evaluate  | what a graph |            |             |              |            |               |              |
| structure would   | the graph learning | policy learn | and how this |            |             |              |            |               |              |
helps us localize and comprehend an anomaly in this section. VI. CONCLUSION
| An assault with | a period of 25.16 | minutes | was logged in the |     |     |     |     |     |     |
| --------------- | ----------------- | ------- | ----------------- | --- | --- | --- | --- | --- | --- |
WADI data collecting log, which fraudulently turned on the Inthiswork,weproposedGTA,aTransformer-basedframe-
| motorizedvalve1 | MV 001 STATUSandcausedanoverflow |     |     |          |         |           |               |            |         |
| --------------- | -------------------------------- | --- | --- | -------- | ------- | --------- | ------------- | ---------- | ------- |
|                 |                                  |     |     | work for | anomaly | detection | that uses the | introduced | connec- |
on the primary tank. It’s difficult for the operation engineers tion learning policy to automatically learn sensor dependen-
to find out the status of this valve manually because it’s still cies.Tosimulatetheinformationflowamongthesensorsinthe
within normal range. As a result, it’s not easy to spot this graph, we devised an unique Influence Propagation (IP) graph
oddity. convolution.Theinferencespeedofourproposedmulti-branch
The water distribution treatment, for example, consists attention technique is greatly improved without sacrificing
of three-state processes from the water supply, distribution modelperformance.Extensiveexperimentsonfourreal-world
network, and return water system, which are denoted as datasets demonstrated that our strategy outperformed other
P1, P2, and P3, respectively. Every sensor and actuator, in state-of-the-artapproachesintermsofpredictionaccuracy.We
every condition, is inextricably linked. The raw water inlet also provided a case study to demonstrate how our approach
valve that regulates the SUTD entering, for example, is identifies the anomaly by utilizing our proposed techniques.
representedby1 MV 001 STATUS.Because1 FIT 001 PV We aim to explore more about combining this approach with
is a downstream flow indicator transmitter of the water dis- the online learning strategy to land it on the mobile IoT
tribution, the value of 1 FIT 001 PV rises rapidly if the scenarios for future work.

11
REFERENCES
|     |     |     |     |     |     |     |     | [21] J. Zhou, | G.        | Cui, Z. | Zhang, C. | Yang,   | Z. Liu,            | and M. Sun, | “Graph     |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------- | --------- | ------- | --------- | ------- | ------------------ | ----------- | ---------- |
|     |     |     |     |     |     |     |     | neural        | networks: | A       | review of | methods | and applications,” |             | CoRR, vol. |
abs/1812.08434,2018.
| [1] M. S. | Mahdavinejad, | M.           | Rezvan,  | M.       | Barekatain, | P.           | Adibi, P. M. |                     |     |              |     |           |            |     |           |
| --------- | ------------- | ------------ | -------- | -------- | ----------- | ------------ | ------------ | ------------------- | --- | ------------ | --- | --------- | ---------- | --- | --------- |
|           |               |              |          |          |             |              |              | [22] P. Velickovic, |     | G. Cucurull, | A.  | Casanova, | A. Romero, | P.  | Lio`, and |
| Barnaghi, | and           | A. P. Sheth, | “Machine | learning |             | for internet | of things    |                     |     |              |     |           |            |     |           |
Y.Bengio,“Graphattentionnetworks,”in6thInternationalConference
dataanalysis:Asurvey,”CoRR,vol.abs/1802.06305,2018.
|     |     |     |     |     |     |     |     | onLearningRepresentations. |     |     |     | OpenReview.net,2018. |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | -------------------------- | --- | --- | --- | -------------------- | --- | --- | --- |
[2] Z.CaiandZ.He,“Tradingprivaterangecountingoverbigiotdata,”in
39thIEEEInternationalConferenceonDistributedComputingSystems, [23] F. Wu, A. H. S. Jr., T. Zhang, C. Fifty, T. Yu, and K. Q. Weinberger,
“Simplifyinggraphconvolutionalnetworks,”inProceedingsofthe36th
| ICDCS2019,Dallas,TX,USA,July7-10,2019. |     |     |     |     |     | IEEE,2019,pp.144– |     |               |     |            |     |         |           |                  |     |
| -------------------------------------- | --- | --- | --- | --- | --- | ----------------- | --- | ------------- | --- | ---------- | --- | ------- | --------- | ---------------- | --- |
|                                        |     |     |     |     |     |                   |     | International |     | Conference | on  | Machine | Learning, | ser. Proceedings | of  |
153.[Online].Available:https://doi.org/10.1109/ICDCS.2019.00023
|                   |         |                  |               |            |            |             |       | MachineLearningResearch,vol.97. |          |         |           |              | PMLR,2019,pp.6861–6871. |                |           |
| ----------------- | ------- | ---------------- | ------------- | ---------- | ---------- | ----------- | ----- | ------------------------------- | -------- | ------- | --------- | ------------ | ----------------------- | -------------- | --------- |
| [3] M. Mohammadi, |         | A. I. Al-Fuqaha, |               | S. Sorour, | and        | M. Guizani, | “Deep |                                 |          |         |           |              |                         |                |           |
|                   |         |                  |               |            |            |             |       | [24] Y. Wang,                   | Y.       | Sun, Z. | Liu, S.   | E. Sarma,    | M. M.                   | Bronstein,     | and J. M. |
| learning          | for iot | big data         | and streaming |            | analytics: | A survey,”  | IEEE  |                                 |          |         |           |              |                         |                |           |
|                   |         |                  |               |            |            |             |       | Solomon,                        | “Dynamic |         | graph CNN | for learning | on                      | point clouds,” | ACM       |
Commun.Surv.Tutorials,vol.20,no.4,pp.2923–2960,2018. Trans.Graph.,vol.38,no.5,pp.146:1–146:12,2019.
[4] A.DengandB.Hooi,“Graphneuralnetwork-basedanomalydetection
|     |     |     |     |     |     |     |     | [25] Z. Wu, | S. Pan, | G.  | Long, J. Jiang, | X.  | Chang, and | C. Zhang, | “Con- |
| --- | --- | --- | --- | --- | --- | --- | --- | ----------- | ------- | --- | --------------- | --- | ---------- | --------- | ----- |
inmultivariatetimeseries,”inProceedingsofthe35thAAAIConference
nectingthedots:Multivariatetimeseriesforecastingwithgraphneural
onArtificialIntelligence,2021.
|                |        |          |                |     |           |           |              | networks,”  | in  | Proceedings  | of        | the 26th | ACM SIGKDD   | International |       |
| -------------- | ------ | -------- | -------------- | --- | --------- | --------- | ------------ | ----------- | --- | ------------ | --------- | -------- | ------------ | ------------- | ----- |
| [5] Z. Cai     | and X. | Zheng,   | “A private     | and | efficient | mechanism | for          |             |     |              |           |          |              |               |       |
|                |        |          |                |     |           |           |              | Conference  |     | on Knowledge | Discovery | &        | Data Mining. | ACM,          | 2020, |
| data uploading |        | in smart | cyber-physical |     | systems,” | IEEE      | Trans. Netw. | pp.753–763. |     |              |           |          |              |               |       |
Sci. Eng., vol. 7, no. 2, pp. 766–775, 2020. [Online]. Available: [26] D.Cao,Y.Wang,J.Duan,C.Zhang,X.Zhu,C.Huang,Y.Tong,B.Xu,
https://doi.org/10.1109/TNSE.2018.2830307
J.Bai,J.Tong,andQ.Zhang,“Spectraltemporalgraphneuralnetwork
| [6] D. Li, | D. Chen, | B. Jin, | L. Shi, | J. Goh, | and | S. Ng, | “MAD-GAN: |     |     |     |     |     |     |     |     |
| ---------- | -------- | ------- | ------- | ------- | --- | ------ | --------- | --- | --- | --- | --- | --- | --- | --- | --- |
formultivariatetime-seriesforecasting,”inNeurIPS,2020.
| multivariate                                                | anomaly    | detection |                    | for time | series     | data with | generative    |                                                                  |     |                |            |     |            |        |             |
| ----------------------------------------------------------- | ---------- | --------- | ------------------ | -------- | ---------- | --------- | ------------- | ---------------------------------------------------------------- | --- | -------------- | ---------- | --- | ---------- | ------ | ----------- |
|                                                             |            |           |                    |          |            |           |               | [27] A.Vaswani,N.Shazeer,N.Parmar,J.Uszkoreit,L.Jones,A.N.Gomez, |     |                |            |     |            |        |             |
| adversarial                                                 | networks,” | in        | 28th International |          | Conference |           | on Artificial |                                                                  |     |                |            |     |            |        |             |
|                                                             |            |           |                    |          |            |           |               | L. Kaiser,                                                       | and | I. Polosukhin, | “Attention |     | is all you | need,” | in NeurIPS, |
| NeuralNetworks,ser.LectureNotesinComputerScience,vol.11730. |            |           |                    |          |            |           |               | 2017,pp.5998–6008.                                               |     |                |            |     |            |        |             |
Springer,2019,pp.703–716.
|              |         |               |                    |      |         |         |          | [28] A. Bla´zquez-Garc´ıa, |                    |     | A. Conde, | U. Mori, | and J.      | A. Lozano, | “A re-     |
| ------------ | ------- | ------------- | ------------------ | ---- | ------- | ------- | -------- | -------------------------- | ------------------ | --- | --------- | -------- | ----------- | ---------- | ---------- |
| [7] X. Zheng | and     | Z. Cai,       | “Privacy-preserved |      | data    | sharing | towards  |                            |                    |     |           |          |             |            |            |
|              |         |               |                    |      |         |         |          | view                       | on outlier/anomaly |     | detection | in       | time series | data,”     | CoRR, vol. |
| multiple     | parties | in industrial | iots,”             | IEEE | J. Sel. | Areas   | Commun., |                            |                    |     |           |          |             |            |            |
abs/2002.04236,2020.
| vol. | 38, no. | 5, pp. | 968–979, | 2020. | [Online]. | Available: | https: |                                                              |     |     |     |     |     |     |     |
| ---- | ------- | ------ | -------- | ----- | --------- | ---------- | ------ | ------------------------------------------------------------ | --- | --- | --- | --- | --- | --- | --- |
|      |         |        |          |       |           |            |        | [29] Y.Zhang,Z.Ge,A.G.Greenberg,andM.Roughan,“Networkanomog- |     |     |     |     |     |     |     |
//doi.org/10.1109/JSAC.2020.2980802
|     |     |     |     |     |     |     |     | raphy,” | in Proceedings |     | of the | 5th Internet | Measurement |     | Conference, |
| --- | --- | --- | --- | --- | --- | --- | --- | ------- | -------------- | --- | ------ | ------------ | ----------- | --- | ----------- |
[8] K. Hundman, V. Constantinou, C. Laporte, I. Colwell, and IMC2005,Berkeley,California,USA,October19-21,2005. USENIX
T. So¨derstro¨m, “Detecting spacecraft anomalies using lstms and non- Association,2005,pp.317–330.
| parametric | dynamic       | thresholding,” |     | in Proceedings |     | of the    | 24th ACM |         |        |                 |     |          |         |           |          |
| ---------- | ------------- | -------------- | --- | -------------- | --- | --------- | -------- | ------- | ------ | --------------- | --- | -------- | ------- | --------- | -------- |
|            |               |                |     |                |     |           |          | [30] W. | Lu and | A. A. Ghorbani, |     | “Network | anomaly | detection | based on |
| SIGKDD     | International | Conference     |     | on Knowledge   |     | Discovery | & Data   |         |        |                 |     |          |         |           |          |
waveletanalysis,”EURASIPJ.Adv.SignalProcess.,vol.2009,2009.
| Mining.   | ACM,2018,pp.387–395. |                |     |        |            |        |         |                                                              |          |     |              |         |           |         |          |
| --------- | -------------------- | -------------- | --- | ------ | ---------- | ------ | ------- | ------------------------------------------------------------ | -------- | --- | ------------ | ------- | --------- | ------- | -------- |
|           |                      |                |     |        |            |        |         | [31] M.Munir,S.A.Siddiqui,A.Dengel,andS.Ahmed,“Deepant:Adeep |          |     |              |         |           |         |          |
| [9] C. M. | Ahmed,               | V. R. Palleti, |     | and A. | P. Mathur, | “WADI: | a water |                                                              |          |     |              |         |           |         |          |
|           |                      |                |     |        |            |        |         | learning                                                     | approach | for | unsupervised | anomaly | detection | in time | series,” |
distributiontestbedforresearchinthedesignofsecurecyberphysical IEEEAccess,vol.7,pp.1991–2005,2019.
systems,”inProceedingsofthe3rdInternationalWorkshoponCyber-
|                                       |     |     |     |                |                    |     |     | [32] P. Malhotra, |             | A. Ramakrishnan, |                 | G. Anand, | L. Vig,          | P. Agarwal, | and |
| ------------------------------------- | --- | --- | --- | -------------- | ------------------ | --- | --- | ----------------- | ----------- | ---------------- | --------------- | --------- | ---------------- | ----------- | --- |
| PhysicalSystemsforSmartWaterNetworks. |     |     |     |                | ACM,2017,pp.25–28. |     |     |                   |             |                  |                 |           |                  |             |     |
|                                       |     |     |     |                |                    |     |     | G. Shroff,        | “Lstm-based |                  | encoder-decoder |           | for multi-sensor | anomaly     | de- |
| [10] C.C.Aggarwal,OutlierAnalysis.    |     |     |     | Springer,2013. |                    |     |     |                   |             |                  |                 |           |                  |             |     |
tection,”CoRR,vol.abs/1607.00148,2016.
| [11] D. Park, | Y. Hoshi, | and C. | C. Kemp, | “A  | multimodal | anomaly | detector |                  |     |                |     |               |               |     |            |
| ------------- | --------- | ------ | -------- | --- | ---------- | ------- | -------- | ---------------- | --- | -------------- | --- | ------------- | ------------- | --- | ---------- |
|               |           |        |          |     |            |         |          | [33] P. Filonov, |     | A. Lavrentyev, | and | A. Vorontsov, | “Multivariate |     | industrial |
forrobot-assistedfeedingusinganlstm-basedvariationalautoencoder,” timeserieswithcyber-attacksimulation:Faultdetectionusinganlstm-
CoRR,vol.abs/1711.00614,2017. basedpredictivedatamodel,”CoRR,vol.abs/1612.06676,2016.
[12] B. Zong, Q. Song, M. R. Min, W. Cheng, C. Lumezanu, D. Cho, and [34] A. A. Cook, G. Misirli, and Z. Fan, “Anomaly detection for iot time-
H.Chen,“Deepautoencodinggaussianmixturemodelforunsupervised
seriesdata:Asurvey,”IEEEInternetThingsJ.,vol.7,no.7,pp.6481–
| anomaly | detection,”in | 6th | InternationalConference |     |     | on LearningRep- |     |     |     |     |     |     |     |     |     |
| ------- | ------------- | --- | ----------------------- | --- | --- | --------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
6494,2020.
| resentations. | OpenReview.net,2018. |     |     |     |     |     |     |                                                                 |     |     |     |     |     |     |     |
| ------------- | -------------------- | --- | --- | --- | --- | --- | --- | --------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
|               |                      |     |     |     |     |     |     | [35] M.Jones,D.Nikovski,M.Imamura,andT.Hirata,“Exemplarlearning |     |     |     |     |     |     |     |
[13] Y.Su,Y.Zhao,C.Niu,R.Liu,W.Sun,andD.Pei,“Robustanomaly for extremely efficient anomaly detection in real-valued time series,”
detectionformultivariatetimeseriesthroughstochasticrecurrentneural DataMin.Knowl.Discov.,vol.30,no.6,pp.1427–1454,2016.
|     | Proceedings |     | of the | 25th | ACM SIGKDD |     | International |     |     |     |     |     |     |     |     |
| --- | ----------- | --- | ------ | ---- | ---------- | --- | ------------- | --- | --- | --- | --- | --- | --- | --- | --- |
network,” in [36] M.SakuradaandT.Yairi,“Anomalydetectionusingautoencoderswith
| Conference | on  | Knowledge | Discovery | &   | Data Mining. |     | ACM, 2019, |     |     |     |     |     |     |     |     |
| ---------- | --- | --------- | --------- | --- | ------------ | --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
nonlineardimensionalityreduction,”inProceedingsoftheMLSDA2014
pp.2828–2837.
|     |     |     |     |     |     |     |     | 2nd | Workshop | on Machine | Learning | for | Sensory | Data Analysis, | Gold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | -------- | ---------- | -------- | --- | ------- | -------------- | ---- |
[14] F. Angiulli and C. Pizzuti, “Fast outlier detection in high dimensional Coast,Australia,QLD,Australia,December2,2014,A.Rahman,J.D.
spaces,” in Principles of Data Mining and Knowledge Discovery, 6th Deng,andJ.Li,Eds. ACM,2014,p.4.
European Conference, ser. Lecture Notes in Computer Science, vol. [37] H. Lu, Y. Liu, Z. Fei, and C. Guan, “An outlier detection algorithm
| 2431. | Springer,2002,pp.15–26. |     |     |     |     |     |     |     |     |     |     |     |     |     |     |
| ----- | ----------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
basedoncross-correlationanalysisfortimeseriesdataset,”IEEEAccess,
| [15] A. Lazarevic | and | V. Kumar, | “Feature | bagging |     | for outlier | detection,” |     |     |     |     |     |     |     |     |
| ----------------- | --- | --------- | -------- | ------- | --- | ----------- | ----------- | --- | --- | --- | --- | --- | --- | --- | --- |
vol.6,pp.53593–53610,2018.
inProceedingsofthe11thACMSIGKDDInternationalConferenceon
|     |     |     |     |     |     |     |     | [38] A.Siffer,P.Fouque,A.Termier,andC.Largoue¨t,“Anomalydetection |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ----------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
KnowledgeDiscovery&DataMining. ACM,2005,pp.157–166. instreamswithextremevaluetheory,”inProceedingsofthe23rdACM
[16] Y. Liang, Z. Cai, J. Yu, Q. Han, and Y. Li, “Deep learning based SIGKDD International Conference on Knowledge Discovery and Data
inference of private information using embedded sensors in smart Mining. ACM,2017,pp.1067–1075.
| devices,” | IEEE | Netw., | vol. 32, | no. 4, | pp. 8–14, | 2018. | [Online]. |                |     |         |          |        |            |                    |     |
| --------- | ---- | ------ | -------- | ------ | --------- | ----- | --------- | -------------- | --- | ------- | -------- | ------ | ---------- | ------------------ | --- |
|           |      |        |          |        |           |       |           | [39] P. Senin, | J.  | Lin, X. | Wang, T. | Oates, | S. Gandhi, | A. P. Boedihardjo, |     |
Available:https://doi.org/10.1109/MNET.2018.1700349
|     |     |     |     |     |     |     |     | C. Chen, | and | S. Frankenstein, |     | “Time | series anomaly | discovery | with |
| --- | --- | --- | --- | --- | --- | --- | --- | -------- | --- | ---------------- | --- | ----- | -------------- | --------- | ---- |
[17] H.Zhao,Y.Wang,J.Duan,C.Huang,D.Cao,Y.Tong,B.Xu,J.Bai, grammar-basedcompression,”inProceedingsofthe18thInternational
J.Tong,andQ.Zhang,“Multivariatetime-seriesanomalydetectionvia ConferenceonExtendingDatabaseTechnology,EDBT2015,Brussels,
graph attention network,” in 20th IEEE International Conference on Belgium,March23-27,2015,G.Alonso,F.Geerts,L.Popa,P.Barcelo´,
DataMining. IEEE,2020,pp.841–850. J. Teubner, M. Ugarte, J. V. den Bussche, and J. Paredaens, Eds.
[18] I.J.Goodfellow,J.Pouget-Abadie,M.Mirza,B.Xu,D.Warde-Farley, OpenProceedings.org,2015,pp.481–492.
S. Ozair, A. C. Courville, and Y. Bengio, “Generative adversarial [40] H.N.AkouemoandR.J.Povinelli,“Dataimprovingintimeseriesusing
networks,”CoRR,vol.abs/1406.2661,2014. arx and ann models,” IEEE Transactions on Power Systems, vol. 32,
[19] Z. Cai, Z. Xiong, H. Xu, P. Wang, W. Li, and Y. Pan, no.5,pp.3352–3359,2017.
“Generativeadversarialnetworks:Asurveytowardsprivateandsecure [41] M.Defferrard,X.Bresson,andP.Vandergheynst,“Convolutionalneural
applications,” CoRR, vol. abs/2106.03785, 2021. [Online]. Available: networks on graphs with fast localized spectral filtering,” in Advances
https://arxiv.org/abs/2106.03785
|     |     |     |     |     |     |     |     | in Neural | Information |     | Processing | Systems | 29: Annual | Conference | on  |
| --- | --- | --- | --- | --- | --- | --- | --- | --------- | ----------- | --- | ---------- | ------- | ---------- | ---------- | --- |
[20] D. Li, D. Chen, J. Goh, and S. Ng, “Anomaly detection with gen- Neural Information Processing Systems 2016, December 5-10, 2016,
erative adversarial networks for multivariate time series,” CoRR, vol. Barcelona,Spain,D.D.Lee,M.Sugiyama,U.vonLuxburg,I.Guyon,
| abs/1809.04758,2018. |     |     |     |     |     |     |     | andR.Garnett,Eds.,2016,pp.3837–3845. |     |     |     |     |     |     |     |
| -------------------- | --- | --- | --- | --- | --- | --- | --- | ------------------------------------ | --- | --- | --- | --- | --- | --- | --- |

12
[42] C.J.Maddison,D.Tarlow,andT.Minka,“A*sampling,”inNeurIPS,
2014,pp.3086–3094.
[43] E. Jang, S. Gu, and B. Poole, “Categorical reparameterization with
gumbel-softmax,” in 5th International Conference on Learning Repre-
sentations. OpenReview.net,2017.
[44] C.Rosenbaum,T.Klinger,andM.Riemer,“Routingnetworks:Adaptive
selection of non-linear functions for multi-task learning,” in 6th Inter-
national Conference on Learning Representations. OpenReview.net,
2018.
[45] Y. Guo, H. Shi, A. Kumar, K. Grauman, T. Rosing, and R. S. Feris,
“Spottune: Transfer learning through adaptive fine-tuning,” in IEEE
Conference on Computer Vision and Pattern Recognition. Computer
VisionFoundation/IEEE,2019,pp.4805–4814.
[46] F.YuandV.Koltun,“Multi-scalecontextaggregationbydilatedconvo-
lutions,”in4thInternationalConferenceonLearningRepresentations,
Y.BengioandY.LeCun,Eds.,2016.
[47] C. Szegedy, W. Liu, Y. Jia, P. Sermanet, S. E. Reed, D. Anguelov,
D. Erhan, V. Vanhoucke, and A. Rabinovich, “Going deeper with
convolutions,” in IEEE Conference on Computer Vision and Pattern
Recognition. IEEEComputerSociety,2015,pp.1–9.
[48] A.RaganatoandJ.Tiedemann,“Ananalysisofencoderrepresentations
intransformer-basedmachinetranslation,”inEMNLP. Associationfor
ComputationalLinguistics,2018,pp.287–297.
[49] E. Voita, R. Sennrich, and I. Titov, “The bottom-up evolution of
representations in the transformer: A study with machine translation
and language modeling objectives,” in EMNLP-IJCNLP. Association
forComputationalLinguistics,2019,pp.4395–4405.
[50] A. Raganato, Y. Scherrer, and J. Tiedemann, “Fixed encoder self-
attentionpatternsintransformer-basedmachinetranslation,”inEMNLP,
T. Cohn, Y. He, and Y. Liu, Eds. Association for Computational
Linguistics,2020,pp.556–568.
[51] Y. Tay, D. Bahri, D. Metzler, D. Juan, Z. Zhao, and C. Zheng,
“Synthesizer: Rethinking self-attention in transformer models,” CoRR,
vol.abs/2005.00743,2020.
[52] Z. Wu, Z. Liu, J. Lin, Y. Lin, and S. Han, “Lite transformer with
long-shortrangeattention,”in8thInternationalConferenceonLearning
Representations. OpenReview.net,2020.
[53] F.Wu,A.Fan,A.Baevski,Y.N.Dauphin,andM.Auli,“Paylessatten-
tion with lightweight and dynamic convolutions,” in 7th International
ConferenceonLearningRepresentations. OpenReview.net,2019.
[54] H.Zhou,S.Zhang,J.Peng,S.Zhang,J.Li,H.Xiong,andW.Zhang,
“Informer: Beyond efficient transformer for long sequence time-series
forecasting,”CoRR,vol.abs/2012.07436,2020.
[55] A.P.MathurandN.O.Tippenhauer,“Swat:awatertreatmenttestbedfor
researchandtrainingonICSsecurity,”in2016InternationalWorkshop
onCyber-physicalSystemsforSmartWaterNetworks. IEEEComputer
Society,2016,pp.31–36.
[56] P. O’Neill, D. Entekhabi, E. G. Njoku, and K. H. Kellogg, “The
NASAsoilmoistureactivepassive(SMAP)mission:Overview,”inIEEE
InternationalGeoscience&RemoteSensingSymposium. IEEE,2010,
pp.3236–3239.
[57] Y. Mirsky, T. Doitshman, Y. Elovici, and A. Shabtai, “Kitsune: An
ensemble of autoencoders for online network intrusion detection,” in
25thAnnualNetworkandDistributedSystemSecuritySymposium. The
InternetSociety,2018.
[58] M. Fey and J. E. Lenssen, “Fast graph representation learning with
pytorchgeometric,”CoRR,vol.abs/1903.02428,2019.
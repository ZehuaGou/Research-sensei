PublishedasaconferencepaperatICLR2022
ANOMALY TRANSFORMER: TIME SERIES ANOMALY
DETECTION WITH ASSOCIATION DISCREPANCY
JiehuiXu∗,HaixuWu∗,JianminWang,MingshengLong((cid:66))
SchoolofSoftware,BNRist,TsinghuaUniversity,China
{xjh20,whx20}@mails.tsinghua.edu.cn, {jimwang,mingsheng}@tsinghua.edu.cn
Unsuperviseddetectionofanomalypointsintimeseriesisachallengingproblem,
whichrequiresthemodeltoderiveadistinguishablecriterion. Previousmethods
tackletheproblemmainlythroughlearningpointwiserepresentationorpairwise
association, however,neitherissufficienttoreasonabouttheintricatedynamics.
Recently,Transformershaveshowngreatpowerinunifiedmodelingofpointwise
representationandpairwiseassociation,andwefindthattheself-attentionweight
distributionofeachtimepointcanembodyrichassociationwiththewholeseries.
Ourkeyobservationisthatduetotherarityofanomalies,itisextremelydifficult
tobuildnontrivialassociationsfromabnormalpointstothewholeseries,thereby,
theanomalies’associationsshallmainlyconcentrateontheiradjacenttimepoints.
Thisadjacent-concentrationbiasimpliesanassociation-basedcriterioninherently
distinguishablebetweennormalandabnormalpoints,whichwehighlightthrough
theAssociationDiscrepancy. Technically,weproposetheAnomalyTransformer
withanewAnomaly-Attentionmechanismtocomputetheassociationdiscrepancy.
Aminimaxstrategyisdevisedtoamplifythenormal-abnormaldistinguishability
ofthe associationdiscrepancy. The AnomalyTransformerachieves state-of-the-
artresultsonsixunsupervisedtimeseriesanomalydetectionbenchmarksofthree
applications: servicemonitoring,space&earthexploration,andwatertreatment.
Real-worldsystemsalwaysworkinacontinuousway,whichcangenerateseveralsuccessivemea-
surementsmonitoredbymulti-sensors,suchasindustrialequipment,spaceprobe,etc. Discovering
themalfunctionsfromlarge-scalesystemmonitoringdatacanbereducedtodetectingtheabnormal
timepointsfromtimeseries,whichisquitemeaningfulforensuringsecurityandavoidingfinancial
loss.Butanomaliesareusuallyrareandhiddenbyvastnormalpoints,makingthedatalabelinghard
andexpensive. Thus,wefocusontimeseriesanomalydetectionundertheunsupervisedsetting.
Unsupervisedtimeseriesanomalydetectionisextremelychallenginginpractice. Themodelshould
learn informative representations from complex temporal dynamics through unsupervised tasks.
Still,itshouldalsoderiveadistinguishablecriterionthatcandetecttherareanomaliesfromplentyof
normaltimepoints. Variousclassicanomalydetectionmethodshaveprovidedmanyunsupervised
paradigms, such as the density-estimation methods proposed in local outlier factor (LOF, Breunig
et al. (2000)), clustering-based methods presented in one-class SVM (OC-SVM, Scho¨lkopf et al.
(2001))andSVDD(Tax&Duin,2004). Theseclassicmethodsdonotconsiderthetemporalinfor-
mation and are difficult to generalize to unseen real scenarios. Benefiting from the representation
learning capability of neural networks, recent deep models (Su et al., 2019; Shen et al., 2020; Li
etal.,2021)haveachievedsuperiorperformance. Amajorcategoryof methodsfocusonlearning
pointwiserepresentationsthroughwell-designedrecurrentnetworksandareself-supervisedbythe
reconstructionorautoregressivetask.Here,anaturalandpracticalanomalycriterionisthepointwise
reconstructionorpredictionerror.However,duetotherarityofanomalies,thepointwiserepresenta-
tionislessinformativeforcomplextemporalpatternsandcanbedominatedbynormaltimepoints,
making anomalies less distinguishable. Also, the reconstruction or prediction error is calculated
pointbypoint,whichcannotprovideacomprehensivedescriptionofthetemporalcontext.
∗EqualContribution
1
2202
nuJ
92
]GL.sc[
5v24620.0112:viXra

PublishedasaconferencepaperatICLR2022
Anothermajorcategoryofmethodsdetectanomaliesbasedonexplicitassociationmodeling. The
vectorautoregressionandstatespacemodelsfallintothiscategory. Thegraphwasalsousedtocap-
turetheassociationexplicitly,throughrepresentingtimeserieswithdifferenttimepointsasvertices
anddetectinganomaliesbyrandomwalk(Chengetal.,2008;2009). Ingeneral,itishardforthese
classicmethodstolearninformativerepresentationsandmodelfine-grainedassociations. Recently,
graphneuralnetwork(GNN)hasbeenappliedtolearnthedynamicgraphamongmultiplevariables
inmultivariatetimeseries(Zhaoetal.,2020;Deng&Hooi,2021). Whilebeingmoreexpressive,
the learned graph is still limited to a single time point, which is insufficient for complex temporal
patterns.Besides,subsequence-basedmethodsdetectanomaliesbycalculatingthesimilarityamong
subsequences(Boniol&Palpanas,2020). Whileexploringwidertemporalcontext, thesemethods
cannotcapturethefine-grainedtemporalassociationbetweeneachtimepointandthewholeseries.
Inthispaper, weadaptTransfomers(Vaswanietal.,2017)totimeseriesanomalydetectioninthe
unsupervisedregime. Transformershaveachievedgreatprogressinvariousareas,includingnatural
languageprocessing(Brownetal., 2020), machinevision(Liuetal.,2021)andtime series(Zhou
etal.,2021).Thissuccessisattributedtoitsgreatpowerinunifiedmodelingofglobalrepresentation
andlong-rangerelation. ApplyingTransformerstotimeseries,wefindthatthetemporalassociation
ofeachtimepointcanbeobtainedfromtheself-attentionmap,whichpresentsasadistributionofits
associationweightstoallthetimepointsalongthetemporaldimension.Theassociationdistribution
of each time point can provide a more informative description for the temporal context, indicat-
ing dynamic patterns, such as the period or trend of time series. We name the above association
distributionastheseries-association,whichcanbediscoveredfromtherawseriesbyTransformers
Further, weobservethatduetotherarityofanomaliesandthedominanceofnormalpatterns, itis
harderforanomaliestobuildstrongassociationswiththewholeseries. Theassociationsofanoma-
lies shall concentrate on the adjacent time points that are more likely to contain similar abnormal
patterns due to the continuity. Such an adjacent-concentration inductive bias is referred to as the
prior-association. Incontrast,thedominatingnormaltimepointscandiscoverinformativeassoci-
ationswiththewholeseries,notlimitingtotheadjacentarea. Basedonthisobservation,wetryto
utilizetheinherentnormal-abnormaldistinguishabilityoftheassociationdistribution. Thisleadsto
a new anomaly criterion for each time point, quantified by the distance between each time point’s
prior-associationanditsseries-association,namedasAssociationDiscrepancy. Asaforementioned,
becausetheassociationsofanomaliesaremorelikelytobeadjacent-concentrating,anomalieswill
presentasmallerassociationdiscrepancythannormaltimepoints.
Gobeyondpreviousmethods,weintroduceTransformerstotheunsupervisedtimeseriesanomaly
detection and propose the Anomaly Transformer for association learning. To compute the Associ-
ationDiscrepancy,werenovatetheself-attentionmechanismtotheAnomaly-Attention,whichcon-
tainsatwo-branchstructuretomodeltheprior-associationandseries-associationofeachtimepoint
respectively. The prior-association employs the learnable Gaussian kernel to present the adjacent-
concentrationinductivebiasofeachtimepoint,whiletheseries-associationcorrespondstotheself-
attentionweightslearnedfromrawseries. Besides,aminimaxstrategyisappliedbetweenthetwo
branches,whichcanamplifythenormal-abnormaldistinguishabilityoftheAssociationDiscrepancy
andfurtherderiveanewassociation-basedcriterion. AnomalyTransformerachievesstrongresults
onsixbenchmarks,coveringthreerealapplications. Thecontributionsaresummarizedasfollows:
• BasedonthekeyobservationofAssociationDiscrepancy,weproposetheAnomalyTrans-
formerwithanAnomaly-Attentionmechanism,whichcanmodeltheprior-associationand
series-associationsimultaneouslytoembodytheAssociationDiscrepancy.
• We propose a minimax strategy to amplify the normal-abnormal distinguishability of the
AssociationDiscrepancyandfurtherderiveanewassociation-baseddetectioncriterion.
• AnomalyTransformerachievesthestate-of-the-artanomalydetectionresultsonsixbench-
marksforthreerealapplications. Extensiveablationsandinsightfulcasestudiesaregiven.
2.1 UNSUPERVISEDTIMESERIESANOMALYDETECTION
As a vital real-world problem, unsupervised time series anomaly detection has been widely ex-
plored.Categorizingbyanomalydeterminationcriterion,theparadigmsroughlyincludethedensity-
estimation,clustering-based,reconstruction-basedandautoregression-basedmethods.
2

PublishedasaconferencepaperatICLR2022
Asforthedensity-estimationmethods,theclassicmethodslocaloutlierfactor(LOF,Breunigetal.
(2000))andconnectivityoutlierfactor(COF,Tangetal.(2002))calculatesthelocaldensityandlocal
connectivity for outlier determination respectively. DAGMM (Zong et al., 2018) and MPPCACD
(Yairietal.,2017)integratetheGaussianMixtureModeltoestimatethedensityofrepresentations.
Inclustering-basedmethods,theanomalyscoreisalwaysformalizedasthedistancetoclustercenter.
SVDD (Tax & Duin, 2004) and Deep SVDD (Ruff et al., 2018) gather the representations from
normaldatatoacompactcluster. THOC(Shenetal.,2020)fusesthemulti-scaletemporalfeatures
from intermediate layers by a hierarchical clustering mechanism and detects the anomalies by the
multi-layerdistances. ITAD(Shinetal.,2020)conductstheclusteringondecomposedtensors.
Thereconstruction-basedmodelsattempttodetecttheanomaliesbythereconstructionerror. Park
et al. (2018) presented the LSTM-VAE model that employed the LSTM backbone for temporal
modeling and the Variational AutoEncoder (VAE) for reconstruction. OmniAnomaly proposed by
Suetal.(2019)furtherextendstheLSTM-VAEmodelwithanormalizingflowandusestherecon-
structionprobabilitiesfordetection. InterFusionfromLietal.(2021)renovatesthebackbonetoa
hierarchicalVAEtomodeltheinter-andintra-dependencyamongmultipleseriessimultaneously.
GANs(Goodfellowetal.,2014)arealsousedforreconstruction-basedanomalydetection(Schlegl
etal.,2019;Lietal.,2019a;Zhouetal.,2019)andperformasanadversarialregularization.
Theautoregression-basedmodelsdetecttheanomaliesbythepredictionerror.VARextendsARIMA
(Anderson & Kendall, 1976) and predicts the future based on the lag-dependent covariance. The
autoregressivemodelcanalsobereplacedbyLSTMs(Hundmanetal.,2018;Tariqetal.,2019).
This paper is characterized by a new association-based criterion. Different from the random walk
andsubsequence-basedmethods(Chengetal.,2008;Boniol&Palpanas,2020),ourcriterionisem-
bodiedbyaco-designofthetemporalmodelsforlearningmoreinformativetime-pointassociations.
2.2 TRANSFORMERSFORTIMESERIESANALYSIS
Recently, Transformers(Vaswanietal.,2017)haveshowngreatpowerinsequentialdataprocess-
ing,suchasnaturallanguageprocessing(Devlinetal.,2019;Brownetal.,2020),audioprocessing
(Huangetal.,2019)andcomputervision(Dosovitskiyetal.,2021;Liuetal.,2021). Fortimeseries
analysis, benefiting from the advantage of the self-attention mechanism, Transformers are used to
discoverthereliablelong-rangetemporaldependencies(Kitaevetal.,2020;Lietal.,2019b;Zhou
etal.,2021;Wuetal.,2021). Especiallyfortimeseriesanomalydetection,GTAproposedbyChen
et al. (2021) employs the graph structure to learn the relationship among multiple IoT sensors, as
wellastheTransformerfortemporalmodelingandthereconstructioncriterionforanomalydetec-
tion. UnliketheprevioususageofTransformers,AnomalyTransformerrenovatestheself-attention
mechanismtotheAnomaly-Attentionbasedonthekeyobservationofassociationdiscrepancy.
Supposemonitoringasuccessivesystemofdmeasurementsandrecordingtheequallyspacedobser-
vationsovertime. Theobservedtimeseries isdenotedbyasetoftimepoints x ,x , ,x ,
1 2 N
wherex Rdrepresentstheobservationof X timet.Theunsupervisedtimeseries { anomaly · d · e · tectio } n
t
∈
problemistodeterminewhetherx isanomalousornotwithoutlabels.
t
Asaforementioned,wehighlightthekeytounsupervisedtimeseriesanomalydetectionaslearning
informative representations and finding distinguishable criterion. We propose the Anomaly Trans-
former todiscovermoreinformativeassociationsandtacklethisproblembylearningtheAssocia-
tionDiscrepancy,whichisinherentlynormal-abnormaldistinguishable.Technically,weproposethe
Anomaly-Attention to embody the prior-association and series-associations, along with a minimax
optimizationstrategytoobtainamoredistinguishableassociationdiscrepancy.Co-designedwiththe
architecture,wederiveanassociation-basedcriterionbasedonthelearnedassociationdiscrepancy.
3.1 ANOMALYTRANSFORMER
GiventhelimitationofTransformers(Vaswanietal.,2017)foranomalydetection,werenovatethe
vanillaarchitecturetotheAnomalyTransformer(Figure1)withanAnomaly-Attentionmechanism.
OverallArchitecture AnomalyTransformerischaracterizedbystackingtheAnomaly-Attention
blocksandfeed-forwardlayersalternately. Thisstackingstructureisconducivetolearningunderly-
ingassociationsfromdeepmulti-levelfeatures.SupposethemodelcontainsLlayerswithlength-N
3

Diagonal Local Min KL KL
Sigma
Filling Relation Distance
Stop
gradient
Q
M atM
ul
Scale SoftM
ax R
G
e
l
l
o
at
b
io
al
nMax KL Dis
K
ta
L
nce
K
Z Linear V M atM
ul
Sigma Q K
PublishedasaconferencepaperatICLR2022
Concat Linear
Anomaly Attention
Layer Norm
Reconstruction
+ Loss
Feed
Forward
Layer Norm
+
Anomaly Global-Local Attention KL Distance
Min
Sigma
Diagonalize Ad
A
ja
ss
c
o
e
c
n
i
t
a
-
t
S
i
e
o
r
n
ies KL
Dis
K
ta
L
nce
Stop
gradient
Q
M atM
ul
Scale SoftM
ax
G
A
lo
ss
b
o
a
c
l
i
-
a
S
t
e
i
r
o
i
n
es
Max Dis
K
ta
L
nce
K KL
X
Linear
V
M
atM ul
Linear
Reconstruction
Layer Norm
+
Feed
Forward
Layer Norm
+
Anomaly
L x Attention
Prior- Minimize Association Discrepancy
Stop
Q Grad
M atM
ul
Scale SoftM
ax Ass
S
o
e
c
ri
i
e
a
s
ti
-
on D
M
isc
a
r
x
e
im
pa
iz
n
e
cy
K
X
Linear
V
M
atM
ul
Linear
Reconstruction
Layer Norm
  N N N N N N N N ( ( ( ( ( ( ( ( ( N 1 2N 1 2 N 1 2, , , , , , ,    ,,           1 2   2 2  1 2 1 2 2 2 2 2 2 ) )NN 22 ) ) ) ) ) )) Fe + ed
N N Forward
Layer Norm
+
Anomaly
Attention
L x
2
22
2
… Grad Scale
Grad
Prior- Minimize Association Discrepancy
Stop
Q grad
M atM
ul
Scale SoftM
ax Ass
S
o
e
c
ri
i
e
a
s
ti
-
on D
M
isc
a
r
x
e
im
pa
iz
n
e
cy
K
X Linear V M atM ul
Linear
Reconstruction
Layer Norm
  N N N N N N N N ( ( ( ( ( ( ( ( ( N 1 2N 1 2 N 1 2, , , , , , ,    ,,           1 2   2 2  1 2 1 2 2 2 2 2 2 ) )NN 22 ) ) ) ) ) )) Fe + ed
N N Forward
Layer Norm
+
Anomaly Attention L x
2
22
2
… grad Scale
grad
Prior- Minimize Association Discrepancy
Stop
Q Grad
M atM
ul
Scale SoftM
ax Ass
S
o
e
c
ri
i
e
a
s
ti
-
on D
M
isc
a
r
x
e
im
pa
iz
n
e
cy
K
X
Linear
V
M
atM ul
Linear
Reconstruction
Layer Norm
+  
Feed
Forward
Layer Norm
+
Anomaly
Attention L x
2
…
(cid:56) 作业要求 (cid:56) 作业要求
(cid:56) 作业要求
(cid:199) 本次作业为单人作业（需独立完成）。
(cid:199) 本次作业为单人作业（需独立完成）。
(cid:199)(cid:199)本如次与作他业人为交单流人或作使业用（开需源独代立码完、成）论。文，请在报告中说明或给出引用。
(cid:199) 如与他人交流或使用开源代码、论文，请在报告中说明或给出引用。
(cid:199)如与他人交流或使用开源代码、论文，请在报告中说明或给出引用。 (cid:199) 由于作业(cid:46)(cid:46)(cid:71)较晚，本次作业《最终报告与代码》不允许迟交。
(cid:199) 由于作业(cid:46)(cid:46)(cid:71)较晚，本次作业《最终报告与代码》不允许迟交。
(cid:199)由于作业(cid:46)(cid:46)(cid:71)较晚，本次作业《最终报告与代码》不允许迟交。
(cid:199)(cid:199)在在项项目目中中遇遇到到任任何何困困难难，，如如选选题题、、数数据据集集挑挑选选或或者者技技术术方方案案设设计计，，请请及及时时和和助助教教联联系系。。
(cid:199)在项目中遇到任何困难，如选题、数据集挑选或者技术方案设计，请及时和助教联系。
G G G G G G ( ( ( ( ( ( | | | | | | j j j j j j − − − − − − 1 2 1 2 1 2 | | ; ; | | | | ; ; ; ; σ σ σ σ σ σ 1 2 1 2 1 2 ) ) ) ) ) ) Rescale Grad
G
GG( ((
| ||j
jj
− −−N
NN
| ;||
;;σ σσ
N
NN)))
参参参考考考文文文献献献
(cid:40)(cid:40)(cid:40)(cid:82)(cid:82)(cid:82)(cid:41)(cid:41)(cid:41)(cid:49)(cid:49)(cid:49)(cid:88)(cid:88)(cid:88)(cid:46)(cid:46)(cid:46)(cid:81)(cid:81)(cid:81)(cid:77)(cid:77)(cid:77)(cid:59)(cid:59)(cid:59)(cid:45)(cid:45)(cid:45)(cid:62)(cid:62)(cid:62)(cid:88)(cid:88)(cid:88)(cid:46)(cid:46)(cid:46)(cid:109)(cid:109)(cid:109)(cid:45)(cid:45)(cid:45)(cid:28)(cid:77)(cid:28)(cid:28)(cid:77)(cid:77)(cid:47)(cid:47)(cid:47)(cid:71)(cid:71)(cid:88)(cid:71)(cid:58)(cid:88)(cid:88)(cid:58)(cid:58)(cid:28)(cid:96)(cid:28)(cid:28)(cid:47)(cid:96)(cid:96)(cid:77)(cid:47)(cid:47)(cid:50)(cid:77)(cid:77)(cid:96)(cid:88)(cid:50)(cid:50)(cid:96)(cid:96)(cid:27)(cid:88)(cid:88)(cid:77)(cid:27)(cid:27)(cid:66)(cid:77)(cid:77)(cid:77)(cid:105)(cid:66)(cid:66)(cid:50)(cid:77)(cid:77)(cid:96)(cid:105)(cid:105)(cid:28)(cid:50)(cid:50)(cid:43)(cid:96)(cid:96)(cid:105)(cid:28)(cid:28)(cid:66)(cid:112)(cid:43)(cid:43)(cid:50)(cid:105)(cid:105)(cid:66)(cid:66)(cid:112)(cid:114)G(cid:112)(cid:50)(cid:50)(cid:50)r(cid:35)a(cid:114)(cid:114)(cid:64)d(cid:50)(cid:35)(cid:50)(cid:35)(cid:28)(cid:35)(cid:64)(cid:98)(cid:64)(cid:35)(cid:50)(cid:35)(cid:47)(cid:28)(cid:28)(cid:98)(cid:98)(cid:47)(cid:50)(cid:50)(cid:28)(cid:47)(cid:47)(cid:98)(cid:63)(cid:47)(cid:47)(cid:35)(cid:28)(cid:28)(cid:81)(cid:98)(cid:98)(cid:28)(cid:63)(cid:63)(cid:96)(cid:35)(cid:47)(cid:35)(cid:81)(cid:81)(cid:28)(cid:105)(cid:28)(cid:81)(cid:96)(cid:96)(cid:47)(cid:47)(cid:105)(cid:96)(cid:105)(cid:28)(cid:105)(cid:81)(cid:43)(cid:81)(cid:70)(cid:105)(cid:105)(cid:96)(cid:43)(cid:96)(cid:28)(cid:81)(cid:28)(cid:43)(cid:112)(cid:43)(cid:70)(cid:66)(cid:70)(cid:47)(cid:43)(cid:64)(cid:43)(cid:81)(cid:82)(cid:81)(cid:112)(cid:78)(cid:112)(cid:66)(cid:47)(cid:66)(cid:66)(cid:77)(cid:47)(cid:64)(cid:82)(cid:64)(cid:96)(cid:82)(cid:78)(cid:50)(cid:78)(cid:28)(cid:66)(cid:72)(cid:77)(cid:66)(cid:77)(cid:105)(cid:96)(cid:66)(cid:75)(cid:50)(cid:96)(cid:28)(cid:50)(cid:50)(cid:28)(cid:72)(cid:88)(cid:72)(cid:105)(cid:66)(cid:105)(cid:75)(cid:66)(cid:75)(cid:50)(cid:88)(cid:50)(cid:88)
(cid:71)(cid:71)(cid:71)(cid:28)(cid:28)(cid:28)(cid:77)(cid:77)(cid:77)(cid:43)(cid:43)(cid:43)(cid:50)(cid:50)(cid:50)(cid:105)(cid:105)(cid:105)(cid:65)(cid:65)(cid:65)(cid:77)(cid:77)(cid:77)(cid:55)(cid:55)(cid:50)(cid:55)(cid:50)(cid:50)(cid:43)(cid:43)(cid:43)(cid:105)(cid:88)(cid:105)(cid:105)(cid:88)(cid:88)(cid:46)(cid:46)(cid:46)(cid:66)(cid:98)(cid:66)(cid:66)(cid:88)(cid:98)(cid:98)(cid:45)(cid:88)(cid:88)(cid:45)(cid:45)(cid:107)(cid:121)(cid:107)(cid:107)(cid:107)(cid:121)(cid:121)(cid:121)(cid:107)(cid:107)(cid:88)(cid:121)(cid:121)(cid:88)(cid:88)
(cid:40)(cid:40)(cid:40)(cid:107)(cid:107)(cid:107)(cid:41)(cid:41)(cid:41)(cid:49)(cid:49)(cid:49)(cid:28)(cid:28)(cid:28)(cid:75)(cid:75)(cid:75)(cid:81)(cid:81)(cid:81)(cid:77)(cid:77)(cid:77)(cid:77)(cid:77)(cid:77)(cid:67)(cid:67)(cid:67)(cid:88)(cid:88)(cid:88)(cid:69)(cid:69)(cid:69)(cid:50)(cid:50)(cid:50)(cid:81)(cid:81)(cid:81)(cid:59)(cid:59)(cid:59)(cid:63)(cid:63)(cid:63)(cid:45)(cid:45)(cid:45)(cid:97)(cid:50)(cid:97)(cid:97)(cid:72)(cid:50)(cid:50)(cid:66)(cid:77)(cid:72)(cid:72)(cid:66)(cid:66)(cid:28)(cid:77)(cid:77)(cid:28)(cid:28)(cid:42)(cid:63)(cid:42)(cid:42)(cid:109)(cid:63)(cid:63)(cid:45)(cid:109)(cid:109)(cid:46)(cid:45)(cid:45)(cid:28)(cid:46)(cid:46)(cid:112)(cid:28)(cid:66)(cid:28)(cid:47)(cid:112)(cid:112)(cid:66)(cid:66)(cid:74)(cid:47)(cid:47)(cid:88)(cid:74)(cid:74)(cid:62)(cid:88)(cid:88)(cid:28)(cid:62)(cid:96)(cid:62)(cid:105)(cid:28)(cid:45)(cid:28)(cid:96)(cid:96)(cid:28)(cid:105)(cid:105)(cid:77)(cid:45)(cid:45)(cid:47)(cid:28)(cid:28)(cid:77)(cid:74)(cid:77)(cid:47)(cid:47)(cid:66)(cid:43)(cid:74)(cid:63)(cid:74)(cid:28)(cid:66)(cid:66)(cid:43)(cid:50)(cid:43)(cid:63)(cid:72)(cid:63)(cid:28)(cid:67)(cid:28)(cid:50)(cid:88)(cid:50)(cid:72)(cid:72)(cid:83)(cid:67)(cid:28)(cid:67)(cid:88)(cid:120)(cid:88)(cid:120)(cid:83)(cid:83)(cid:28)(cid:28)(cid:77)(cid:28)(cid:120)(cid:66)(cid:120)(cid:120)(cid:88)(cid:120)(cid:28)(cid:28)(cid:97)(cid:77)(cid:77)(cid:50)(cid:66)(cid:88)(cid:59)(cid:66)(cid:88)(cid:75)(cid:97)(cid:97)(cid:50)(cid:50)(cid:77)(cid:50)(cid:59)(cid:105)(cid:59)(cid:75)(cid:66)(cid:75)(cid:77)(cid:50)(cid:59)(cid:50)(cid:77)(cid:77)(cid:105)(cid:105)(cid:66)(cid:105)(cid:66)(cid:75)(cid:77)(cid:66)(cid:77)(cid:59)(cid:50)(cid:59)(cid:105)(cid:98)(cid:66)(cid:105)(cid:50)(cid:75)(cid:66)(cid:96)(cid:75)(cid:66)(cid:50)(cid:50)(cid:50)(cid:98)(cid:98)(cid:44)(cid:50)(cid:98)(cid:27)(cid:96)(cid:50)(cid:66)(cid:96)(cid:50)(cid:66)(cid:98)(cid:50)(cid:44)(cid:98)(cid:44)(cid:27)(cid:27)
(cid:98) (cid:98)(cid:98)(cid:109) (cid:109)(cid:109)(cid:96) (cid:96)(cid:96)(cid:112) (cid:112)(cid:112)(cid:50) (cid:50)(cid:50)(cid:118) (cid:118)(cid:118)(cid:28) (cid:28)(cid:28)(cid:77) (cid:77)(cid:77)(cid:47) (cid:47)(cid:47)(cid:77) (cid:77)(cid:77)(cid:81) (cid:81)(cid:81)(cid:112) (cid:112)(cid:112)(cid:50)(cid:72) (cid:50)(cid:50)(cid:72)(cid:72) (cid:28)(cid:84)(cid:28)(cid:28)(cid:84)(cid:84) (cid:84)(cid:96)(cid:84)(cid:84) (cid:81)(cid:96)(cid:96) (cid:28)(cid:81)(cid:81) (cid:43)(cid:28)(cid:28) (cid:63)(cid:43)(cid:43) (cid:88)(cid:63)(cid:63) (cid:107)(cid:88)(cid:88) (cid:121)(cid:107)(cid:107) (cid:121)(cid:121)(cid:121) (cid:107)(cid:121)(cid:121) (cid:88)(cid:107)(cid:107)(cid:88)(cid:88)
(cid:40)(cid:40)(cid:40) (cid:106) (cid:106)(cid:106)(cid:41) (cid:41)(cid:41)(cid:83) (cid:83)(cid:83)(cid:28) (cid:28)(cid:28)(cid:96) (cid:96)(cid:96)(cid:105) (cid:105)(cid:105)(cid:63) (cid:63)(cid:63)(cid:83) (cid:83)(cid:83)(cid:28) (cid:28)(cid:28)(cid:105) (cid:105)(cid:105)(cid:114) (cid:114)(cid:114)(cid:28) (cid:28)(cid:28)(cid:45) (cid:45)(cid:45)(cid:97) (cid:97)(cid:97)(cid:63) (cid:63)(cid:63)(cid:66)(cid:112)(cid:66)(cid:66) (cid:28)(cid:112)(cid:112) (cid:75)(cid:28)(cid:28)(cid:75)(cid:75) (cid:97)(cid:63)(cid:97)(cid:97) (cid:28)(cid:63)(cid:63) (cid:96)(cid:28)(cid:28) (cid:75)(cid:96)(cid:96)(cid:75)(cid:75) (cid:28)(cid:45)(cid:28)(cid:28) (cid:97)(cid:45)(cid:45) (cid:96)(cid:97)(cid:66) (cid:97) (cid:77)(cid:96)(cid:96) (cid:66)(cid:66)(cid:66) (cid:112)(cid:77)(cid:77) (cid:28)(cid:66)(cid:66)(cid:112)(cid:98) (cid:112)(cid:28)(cid:28) (cid:83)(cid:98)(cid:98) (cid:118)(cid:83)(cid:70) (cid:83) (cid:72)(cid:118)(cid:118) (cid:45)(cid:70)(cid:70) (cid:111)(cid:72)(cid:72)(cid:45)(cid:45) (cid:66)(cid:77)(cid:111)(cid:111) (cid:50)(cid:66)(cid:50) (cid:66)(cid:77)(cid:105) (cid:77) (cid:63)(cid:50)(cid:50)(cid:50)(cid:50) (cid:58)(cid:105)(cid:105)(cid:63)(cid:63) (cid:109)(cid:84)(cid:58)(cid:58) (cid:105)(cid:109)(cid:63) (cid:109) (cid:28)(cid:84)(cid:84) (cid:45)(cid:105)(cid:105)(cid:63)(cid:58) (cid:63)(cid:28)(cid:28) (cid:66)(cid:45)(cid:105) (cid:45) (cid:28)(cid:58)(cid:77) (cid:58)(cid:66)(cid:68)(cid:105)(cid:66) (cid:28) (cid:105)(cid:28)(cid:72) (cid:28) (cid:66)(cid:77)(cid:77) (cid:69)(cid:68)(cid:28)(cid:68)(cid:28) (cid:109)(cid:72)(cid:66)(cid:72) (cid:75) (cid:66)(cid:69)(cid:28) (cid:69) (cid:96)(cid:109)(cid:66) (cid:109)(cid:75)(cid:45) (cid:75) (cid:74)(cid:28)(cid:28)(cid:96)(cid:47) (cid:96)(cid:66)(cid:45)(cid:88) (cid:66)(cid:45)(cid:74)(cid:97) (cid:74) (cid:63)(cid:47)(cid:28) (cid:47)(cid:88)(cid:47) (cid:88)(cid:97)(cid:27) (cid:97)(cid:63)(cid:63) (cid:70)(cid:28)(cid:63) (cid:28)(cid:47)(cid:105) (cid:47) (cid:28)(cid:27)(cid:96) (cid:27) (cid:45)(cid:70)(cid:70)(cid:63)(cid:63)(cid:105)(cid:28)(cid:105)(cid:28)(cid:96)(cid:45)(cid:96)(cid:45)
(cid:27)(cid:27)(cid:98)(cid:98)(cid:66)(cid:66)(cid:55)(cid:55)(cid:49)(cid:49)(cid:70)(cid:70)(cid:35)(cid:35)(cid:28)(cid:28)(cid:72)(cid:45)(cid:72)(cid:45)(cid:27)(cid:27)(cid:75)(cid:75)(cid:66)(cid:105)(cid:66)(cid:28)(cid:105)(cid:112)(cid:28)(cid:28)(cid:112)(cid:28)(cid:46)(cid:46)(cid:28)(cid:98)(cid:28)(cid:45)(cid:98)(cid:45)(cid:28)(cid:77)(cid:28)(cid:47)(cid:77)(cid:47)(cid:104)(cid:28)(cid:104)(cid:77)(cid:28)(cid:75)(cid:77)(cid:81)(cid:75)(cid:118)(cid:81)(cid:42)(cid:118)(cid:63)(cid:42)(cid:28)(cid:70)(cid:63)(cid:96)(cid:28)(cid:28)(cid:70)(cid:35)(cid:96)(cid:81)(cid:28)(cid:96)(cid:35)(cid:105)(cid:118)(cid:81)(cid:88)(cid:96)(cid:105)(cid:118)(cid:54)(cid:88)(cid:66)(cid:59)(cid:63)(cid:54)(cid:105)(cid:66)(cid:66)(cid:59)(cid:77)(cid:63)(cid:59)(cid:105)(cid:66)(cid:28)(cid:77)(cid:77)(cid:59)(cid:66)(cid:28)(cid:77)(cid:77)(cid:55)(cid:81)(cid:47)(cid:66)(cid:77)(cid:50)(cid:55)(cid:75)(cid:81)(cid:66)(cid:47)(cid:43)(cid:50)(cid:44)(cid:75)(cid:42)(cid:66)(cid:43)(cid:81)(cid:44)(cid:112)(cid:66)(cid:47)(cid:42)(cid:64)(cid:81)(cid:82)(cid:112)(cid:78)(cid:66)(cid:47)(cid:55)(cid:28)(cid:64)(cid:82)(cid:70)(cid:78)(cid:50)(cid:77)(cid:55)(cid:28)(cid:50)(cid:70)(cid:114)(cid:50)(cid:98)(cid:77)(cid:50)(cid:114)(cid:98)
(cid:27)(cid:98)(cid:66)(cid:55)(cid:49)(cid:70)(cid:35)(cid:28)(cid:72)(cid:45) (cid:27)(cid:75)(cid:66)(cid:105)(cid:28)(cid:112)(cid:28)(cid:46)(cid:28)(cid:98)(cid:45) (cid:28)(cid:77)(cid:47)(cid:104)(cid:28)(cid:77)(cid:75)(cid:81)(cid:118)(cid:42)(cid:63)(cid:28)(cid:70)(cid:96)(cid:28)(cid:35)(cid:81)(cid:96)(cid:105)(cid:118)(cid:88) (cid:54)(cid:66)(cid:59)(cid:63)(cid:105)(cid:66)(cid:77)(cid:59)(cid:28)(cid:77)(cid:66)(cid:77)(cid:55)(cid:81)(cid:47)(cid:50)(cid:75)(cid:66)(cid:43)(cid:44) (cid:42)(cid:81)(cid:112)(cid:66)(cid:47)(cid:64)(cid:82)(cid:78)(cid:55)(cid:28)(cid:70)(cid:50)(cid:77)(cid:50)(cid:114)(cid:98)
Figure1:Anomaly(cid:47)(cid:47)(cid:28)(cid:28)T(cid:105)(cid:105)(cid:28)(cid:28)(cid:98)r(cid:98)(cid:50)(cid:50)a(cid:105)(cid:105)(cid:88)(cid:88)n(cid:65)(cid:65)(cid:77)s(cid:77)f(cid:42)(cid:42)o(cid:80)(cid:80)r(cid:76)(cid:76)m(cid:97)(cid:97)(cid:104)(cid:104)e(cid:95)(cid:95)(cid:27)r(cid:27)(cid:65)a(cid:76)(cid:65)(cid:76)(cid:104)rc(cid:104)(cid:33)h(cid:33)(cid:27)(cid:27)(cid:27)it(cid:27)(cid:27)e(cid:65)(cid:27)(cid:45)c(cid:65)(cid:107)t(cid:45)(cid:121)u(cid:107)(cid:107)(cid:121)(cid:82)r(cid:88)(cid:107)e(cid:82)(cid:88).Anomaly-Attention(left)modelstheprior-association
(cid:47)(cid:28)(cid:105)(cid:28)(cid:98)(cid:50)(cid:105)(cid:88)(cid:65)(cid:77)(cid:42)(cid:80)(cid:76)(cid:97)(cid:104)(cid:95)(cid:27)(cid:65)(cid:76)(cid:104)(cid:33)(cid:27)(cid:27)(cid:27)(cid:65)(cid:45)(cid:107)(cid:121)(cid:107)(cid:82)(cid:88)
andseries-associationsimultaneously. Inadditiontothereconstructionloss,ourmodelisalsoopti-
mizedbytheminimaxstrategywithaspecially-designedstop-gradientmechanism(grayarrows)to
constraintheprior-andseries-associationsformoredistinguishableassociationdiscrepancy.
inputtimeseries RN×d. Theoverallequationsofthel-thlayerareformalizedas:
X ∈
(cid:16) (cid:17)
l =Layer-Norm Anomaly-Attention( l−1)+ l−1
Z X X
(1)
(cid:16) (cid:17)
l =Layer-Norm Feed-Forward( l)+ l ,
X Z Z
where l RN×dmodel,l 1, ,L denotestheoutputofthel-thlayerwithd
model
channels. The
initiali X npu ∈ t 0 = Embe ∈ dd { ing · ( ·· )re } presentstheembeddedrawseries. l RN×dmodel isthel-th
X X Z ∈
layer’shiddenrepresentation. Anomaly-Attention()istocomputetheassociationdiscrepancy.
·
Anomaly-Attention Notethatthesingle-branchself-attentionmechanism(Vaswanietal.,2017)
cannotmodeltheprior-associationandseries-associationsimultaneously.WeproposetheAnomaly-
Attention with a two-branch structure (Figure 1). For the prior-association, we adopt a learnable
Gaussiankerneltocalculatethepriorwithrespecttotherelativetemporaldistance. Benefitingfrom
the unimodal property of the Gaussian kernel, this design can pay more attention to the adjacent
horizonconstitutionally. WealsousealearnablescaleparameterσfortheGaussiankernel,making
(cid:57)
theprior-associationsadapttothevarioustimeseriespatterns,suchasdifferentlengthsofanomaly
segments. The series-association branch is to l(cid:57)earn the associations from raw series, which can
find the most effective associations adaptively. N(cid:57) ote that these two forms maintain the temporal
dependenciesofeachtimepoint,whicharemoreinformativethanpoint-wiserepresentation. They
also reflect the adjacent-concentration prior and the learned real associations respectively, whose
discrepancyshallbenormal-abnormaldistinguishable. TheAnomaly-Attentioninthel-thlayeris:
Initialization: , , ,σ = l−1Wl , l−1Wl, l−1Wl, l−1Wl
Q K V X Q X K X V X σ
(cid:32)(cid:20)
1
(cid:18)
j
i2(cid:19)(cid:21) (cid:33)
Prior-Association: l =Rescale exp | − |
P √2πσ − 2σ2
i i i,j∈{1,···,N} (2)
(cid:18) T (cid:19)
Series-Association: l =Softmax QK
S √d
model
Reconstruction: (cid:98)l = l ,
Z S V
where , , RN×dmodel,σ RN×1 represent the query, key, value of self-attention and the
learned Q sc K ale V res ∈ pectively. Wl , ∈ Wl,Wl Rdmodel×dmodel,Wl Rdmodel×1 represent the parameter
Q K V ∈ σ ∈
matrices for , , ,σ in the l-th layer respectively. Prior-association l RN×N is generated
based on the Q lea K rne V d scale σ RN×1 and the i-th element σ correspo P nds ∈ to the i-th time point.
i
∈
Concretely,forthei-thtimepoint,itsassociationweighttothej-thpointiscalculatebytheGaussian
kernelG(j i;σ )= √ 1 exp( |j−i|2 )w.r.t.thedistance j i. Further,weuseRescale()to
| − | i 2πσi − 2σ i 2 | − | ·
transformtheassociationweightstodiscretedistributions lbydividingtherowsum. l RN×N
P S ∈
denotestheseries-associations. Softmax()normalizestheattentionmapalongthelastdimension.
·
4

Abnormal Time Points Normal Time Points
a. b. c. d.
Association
Discrepancy Association
Discrepancy
Max KL Max KL
Min KL Min KL
Adjacet-series Global-series Reconstruction Loss
Gaussian Family Association Space
Association Association Constrained Space
Minimize Phase Time series Maximize Phase Time series
Association
Discrepancy Global-series Global-series Constrained by
Association Association Reconstruction
Within the
Adjacet-series Gaussian Family Adjacet-series
Association Association
Adjacet-series Global-series Reconstruction Loss Optimization
Gaussian Family Association Space
Association Association Constrained Space Direction
Minimize Phase Time series Maximize Phase Time series
Association Association
Discrepancy Series- Discrepancy Series- Constrained by
Association Association Reconstruction
Within the
Prior- Prior-
Gaussian Family
Association Association
Reconstruction Loss Optimization
Prior-Association Gaussian Family Series-Association
Constrained Space Direction
Adjacet-series
Association
Global-series
PublishedasaconferencepaperatICLR2022 Association
Time series
Adjacet-series
Association
Minimize Phase Time series Maximize Phase Time series Global-series Time series
Association
Association Association
Discrepancy Series- Discrepancy Series- Constrained by
Association Association Reconstruction Adjacet-series
Association
Constrained by
P A r s i s o o r- ciation Gaussian Kernel P A r s i s o o r- ciation G As lo so b c a i l a -s ti e o r n ies C Re o c n o s n tr s a t i r n u e c d ti o b n y
Distribution Family Reconstruction Loss Optimization
Prior-Association Series-Association
From Gaussian Kernel Constrained Space Direction
Figure2:Minimaxassociationlearning. Attheminimizephase,theprior-associationminimizesthe
AssociationDiscrepancywithinthedistributionfamilyderivedbyGaussiankernel.Atthemaximize
phase,theseries-associationmaximizestheAssociationDiscrepancyunderthereconstructionloss.
Thus,eachrowof lformsadiscretedistribution. (cid:98)l RN×dmodel isthehiddenrepresentationafter
S Z ∈
theAnomaly-Attentioninthel-thlayer. WeuseAnomaly-Attention()tosummarizeEquation2.
·
Inthemulti-headversionthatweuse,thelearnedscaleisσ RN×h forhheads. , ,
m m m
RN×dm h odel denote the query, key and value of the m-th head ∈ respectively. The bloc Q k co K ncate V nate ∈ s
theoutputs {Z (cid:98) m l ∈ RN×dm h odel } 1≤m≤h frommultipleheadsandgetsthefinalresult Z (cid:98)l ∈ RN×dmodel.
AssociationDiscrepancy WeformalizetheAssociationDiscrepancyasthesymmetrizedKLdi-
vergence between prior- and series- associations, which represents the information gain between
thesetwodistributions(Neal,2007). Weaveragetheassociationdiscrepancyfrommultiplelayers
tocombinetheassociationsfrommulti-levelfeaturesintoamoreinformativemeasureas:
(cid:20) 1 (cid:88) L (cid:16) (cid:17)(cid:21)
AssDis( , ; )= KL( l l )+KL( l l ) (3)
P S X L Pi,:(cid:107)Si,: Si,:(cid:107)Pi,:
l=1 i=1,···,N
whereKL( )istheKLdivergencecomputedbetweentwodiscretedistributionscorrespondingto
everyrowo · f (cid:107)· l and l. AssDis( , ; ) RN×1 isthepoint-wiseassociationdiscrepancyof
P S P S X ∈ X
withrespecttoprior-association andseries-association frommultiplelayers. Thei-thelement
P S
ofresultscorrespondstothei-thtimepointof .Frompreviousobservation,anomalieswillpresent
X
smallerAssDis( , ; )thannormaltimepoints,whichmakesAssDisinherentlydistinguishable.
P S X
3.2 MINIMAXASSOCIATIONLEARNING
Asanunsupervisedtask,weemploythereconstructionlossforoptimizingourmodel. Therecon-
structionlosswillguidetheseries-associationtofindthemostinformativeassociations. Tofurther
amplify the difference between normal and abnormal time points, we also use an additional loss
to enlarge the association discrepancy. Due to the unimodal property of the prior-association, the
discrepancy loss will guide the series-association to pay more attention to the non-adjacent area,
which makes the reconstruction of anomalies harder and makes anomalies more identifiable. The
lossfunctionforinputseries RN×disformalizedas:
X ∈
L Total ( X (cid:98), P , S ,λ; X )= (cid:107)X −X (cid:98) (cid:107) 2 F− λ ×(cid:107) AssDis( P , S ; X ) (cid:107) 1 (4)
where (cid:98) RN×ddenotesthereconstructionof . F , k indicatetheFrobeniusandk-norm.λ
X ∈ X (cid:107)·(cid:107) (cid:107)·(cid:107)
istotradeoffthelossterms.Whenλ>0,theoptimizationistoenlargetheassociationdiscrepancy.
Aminimaxstrategyisproposedtomaketheassociationdiscrepancymoredistinguishable.
MinimaxStrategy Notethatdirectlymaximizingtheassociationdiscrepancywillextremelyre-
duce the scale parameter of the Gaussian kernel (Neal, 2007), making the prior-association mean-
ingless. Towardsabettercontrolofassociationlearning,weproposeaminimaxstrategy(Figure2).
Concretely, for the minimize phase, we drive the prior-association l to approximate the series-
association l thatislearnedfromrawseries. Thisprocesswillmake P theprior-associationadaptto
S
various temporal patterns. For the maximize phase, we optimize the series-association to enlarge
theassociationdiscrepancy. Thisprocessforcestheseries-associationtopaymoreattentiontothe
non-adjacenthorizon.Thus,integratingthereconstructionloss,thelossfunctionsoftwophasesare:
MinimizePhase:
Total
((cid:98), ,
detach
, λ; )
L X P S − X (5)
MaximizePhase:
Total
((cid:98),
detach
, ,λ; ),
L X P S X
5

PublishedasaconferencepaperatICLR2022
where λ > 0 and means to stop the gradient backpropagation of the association (Figure
detach
∗
1). As approximates in the minimize phase, the maximize phase will conduct a stronger
detach
P S
constrainttotheseries-association,forcingthetimepointstopaymoreattentiontothenon-adjacent
area. Underthereconstructionloss,thisismuchharderforanomaliestoachievethannormaltime
points,therebyamplifyingthenormal-abnormaldistinguishabilityoftheassociationdiscrepancy.
Association-based Anomaly Criterion We incorporate the normalized association discrepancy
tothereconstructioncriterion,whichwilltakethebenefitsofbothtemporalrepresentationandthe
distinguishableassociationdiscrepancy.Thefinalanomalyscoreof RN×disshownasfollows:
X ∈
(cid:16) (cid:17) (cid:104) (cid:105)
AnomalyScore( X )=Softmax − AssDis( P , S ; X ) (cid:12) (cid:107)X i,: −X (cid:98)i,: (cid:107) 2 2 i=1,···,N (6)
where is the element-wise multiplication. AnomalyScore( ) RN×1 denotes the point-wise
(cid:12) X ∈
anomaly criterion of . Towards a better reconstruction, anomalies usually decrease the associa-
X
tion discrepancy, which will still derive a higher anomaly score. Thus, this design can make the
reconstructionerrorandtheassociationdiscrepancycollaboratetoimprovedetectionperformance.
WeextensivelyevaluateAnomalyTransformeronsixbenchmarksforthreepracticalapplications.
Datasets Hereisadescriptionofthesixexperimentdatasets: (1)SMD(ServerMachineDataset,
Suetal.(2019))isa5-week-longdatasetthatiscollectedfromalargeInternetcompanywith38di-
mensions. (2)PSM(PooledServerMetrics,Abdulaaletal.(2021))iscollectedinternallyfrommul-
tipleapplicationservernodesateBaywith26dimensions. (3)BothMSL(MarsScienceLaboratory
rover)andSMAP(SoilMoistureActivePassivesatellite)arepublicdatasetsfromNASA(Hundman
etal.,2018)with55and25dimensionsrespectively,whichcontainthetelemetryanomalydatade-
rivedfromtheIncidentSurpriseAnomaly(ISA)reportsofspacecraftmonitoringsystems.(4)SWaT
(Secure Water Treatment, Mathur & Tippenhauer (2016)) is obtained from 51 sensors of the criti-
calinfrastructuresystemundercontinuousoperations. (5)NeurIPS-TS(NeurIPS2021TimeSeries
Benchmark)isadatasetproposedbyLaietal.(2021)andincludesfivetimeseriesanomalyscenar-
ios categorized by behavior-driven taxonomy as point-global, pattern-contextual, pattern-shapelet,
pattern-seasonalandpattern-trend. ThestatisticaldetailsaresummarizedinTable13ofAppendix.
Implementationdetails Followingthewell-establishedprotocolinShenetal.(2020),weadopta
non-overlappedslidingwindowtoobtainasetofsub-series. Theslidingwindowiswithafixedsize
of100foralldatasets. Welabelthetimepointsasanomaliesiftheiranomalyscores(Equation6)
arelargerthanacertainthresholdδ. Thethresholdδisdeterminedtomakerproportiondataofthe
validationdatasetlabeledasanomalies. Forthemainresults,wesetr = 0.1%forSWaT,0.5%for
SMDand1%forotherdatasets. Weadoptthewidely-usedadjustmentstrategy(Xuetal.,2018;Su
etal.,2019;Shenetal.,2020): ifatimepointinacertainsuccessiveabnormalsegmentisdetected,
allanomaliesinthisabnormalsegmentareviewedtobecorrectlydetected. Thisstrategyisjustified
from the observation that an abnormal time point will cause an alert and further make the whole
segment noticed in real-world applications. Anomaly Transformer contains 3 layers. We set the
channelnumberofhiddenstatesd as512andthenumberofheadshas8. Thehyperparameter
model
λ (Equation 4) is set as 3 for all datasets to trade-off two parts of the loss function. We use the
ADAM(Kingma&Ba,2015)optimizerwithaninitiallearningrateof10−4. Thetrainingprocess
isearlystoppedwithin10epochswiththebatchsizeof32. Alltheexperimentsareimplementedin
Pytorch(Paszkeetal.,2019)withasingleNVIDIATITANRTX24GBGPU.
Baselines We extensively compare our model with 18 baselines, including the reconstruction-
based models: InterFusion (2021), BeatGAN (2019), OmniAnomaly (2019), LSTM-VAE (2018);
the density-estimation models: DAGMM (2018), MPPCACD (2017), LOF (2000); the clustering-
basedmethods: ITAD(2020), THOC(2020), Deep-SVDD(2018); theautoregression-basedmod-
els: CL-MPPCA(2019),LSTM(2018),VAR(1976);theclassicmethods: OC-SVM(2004),Isola-
tionForest(2008).Another3baselinesfromchangepointdetectionandtimeseriessegmentationare
deferredtoAppendixI.InterFusion(2021)andTHOC(2020)arethestate-of-the-artdeepmodels.
6

PublishedasaconferencepaperatICLR2022
| 1.0 1.0 |     | 1.0 1.0 |     | 1.0 1.0 |     |     | 1.0 1.0 |     | 1.0 1.0 |     |
| ------- | --- | ------- | --- | ------- | --- | --- | ------- | --- | ------- | --- |
| 0.8 0.8 |     | 0.8 0.8 |     | 0.8 0.8 |     |     | 0.8 0.8 |     | 0.8 0.8 |     |
etaR evitisoP  eurT
| etaR evitisoP  eurT 0.6 0.6 |     | etaR evitisoP  eurT 0.6 |     | etaR evitisoP  eurT 0.6 |     |     | etaR evitisoP  eurT 0.6 0.6 |     | 0.6 0.6 |     |
| --------------------------- | --- | ----------------------- | --- | ----------------------- | --- | --- | --------------------------- | --- | ------- | --- |
|                             |     | 0.6                     |     | 0.6                     |     |     |                             |     |         |     |
| 0.4                         |     | 0.4                     |     | 0.4                     |     |     | 0.4                         |     | 0.4     |     |
0.4 Ours (AUC=0.9866) 0.4 Ours (AUC=0.9812) 0.4 Ours (AUC=0.9941) 0.4 Ours (AUC=0.9876) 0.4 Ours (AUC=0.9946)
BeatGAN (AUC=0.9727) O u r s  (A U C  =  0 .9 8 6 6 ) BeatGAN (AUC=0.9700) O u r s  (A U C  =  0 .9 8 1 2 ) BeatGAN (AUC=0.8581) O u r s  (A U C  =  0 .9 9 4 1 ) BeatGAN (AUC=0.8953) O u r s  (A U C  =  0 .9 8 7 6 ) BeatGAN (AUC=0.9691) O u r s  (A U C  =  0 .9 9 4 6 )
0.2 0.2 Deep-SVDD (AUC=0.9648) Be a t G A N  (A U C  =   0 .9 727) 0.2 0.2 Deep-SVDD (AUC=0.9756) Be a t G A N  (A U C  =   0 .9 700) 0.2 0.2 Deep-SVDD (AUC=0.9040) Be a t G A N  (A U C  =   0 .9 881) 0.2 0.2 Deep-SVDD (AUC=0.8708) Be Deep-SVDD (AUC = 0.8708) a t G A N  (A U C  =   0 .8 953) 0.2 0.2 Deep-SVDD (AUC=0.9638) Be Deep-SVDD (AUC = 0.9638) a t G A N  (A U C  =   0 .9 691)
LSTM-VAE (AUC=0.9831) Deep-SVDD (AUC = 0.9648) LSTM-VAE (AUC = 0.9831) LSTM-VAE (AUC=0.9726) Deep-SVDD (AUC = 0.9756) LSTM-VAE (AUC = 0.9726) LSTM-VAE (AUC=0.9808) Deep-SVDD (AUC = 0.9040) LSTM-VAE (AUC = 0.9808) LSTM-VAE (AUC=0.9034) LSTM-VAE (AUC = 0.9034) LSTM-VAE (AUC=0.9801) LSTM-VAE (AUC = 0.9801)
0.0 0.0 0.0 0.0 0.2 0.2 0.4 0.4 0.6 0.6 0.8 0.8 1.0 1.00.0 0.0 0.0 0.0 0.2 0.2 0.4 0.4 0.6 0.6 0.8 0.8 1.0 1.0 0.0 0.0 0.0 0.0 0.2 0.2 0.4 0.4 0.6 0.6 0.8 0.8 1.0 1.0 0.0 0.0 0.0 0.0 0.2 0.2 0.4 0.4 0.6 0.6 0.8 0.8 1.0 1.0 0.0 0.0 00..00 00..22 00..44 00..66 00..88 11..00
|     | (a) SMD False Positive Rate |     | (b) MSL False Positive Rate |     | (c) SMAP False Positive Rate |     |     | (d) SWaT False Positive Rate |     | (eFa)l seP PoSsiMtive Rate |
| --- | --------------------------- | --- | --------------------------- | --- | ---------------------------- | --- | --- | ---------------------------- | --- | -------------------------- |
Figure3: ROCcurves(horizontal-axis: false-positiverate;vertical-axis: true-positiverate)forfive
correspondingdatasets. AhigherAUCvalue(areaundertheROCcurve)indicatesabetterperfor-
mance. Thepredefinedthresholdproportionrisin 0.5%,1.0%,1.5%,2.0%,10%,20%,30% .
|     |     |     |     |     |     | {   |     |     |     | }   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Table 1: Quantitative results for Anomaly Transformer (Ours) in five real-world datasets. The P,
RandF1representtheprecision,recallandF1-score(as%)respectively. F1-scoreistheharmonic
meanofprecisionandrecall. Forthesethreemetrics,ahighervalueindicatesabetterperformance.
| Dataset |     | SMD |     | MSL |     | SMAP |      | SWaT |     | PSM    |
| ------- | --- | --- | --- | --- | --- | ---- | ---- | ---- | --- | ------ |
| Metric  |     | P R | F1  | P R | F1  | P    | R F1 | P R  | F1  | P R F1 |
OCSVM 44.34 76.72 56.19 59.78 86.87 70.82 53.85 59.07 56.34 45.39 49.22 47.23 62.75 80.89 70.67
IsolationForest 42.31 73.29 53.64 53.94 86.54 66.45 52.39 59.07 55.53 49.29 44.95 47.02 76.09 92.45 83.48
LOF 56.34 39.86 46.68 47.72 85.25 61.18 58.93 56.33 57.60 72.15 65.43 68.62 57.89 90.49 70.61
Deep-SVDD 78.54 79.67 79.10 91.92 76.63 83.58 89.93 56.02 69.04 80.42 84.45 82.39 95.41 86.49 90.73
DAGMM 67.30 49.89 57.30 89.60 63.93 74.62 86.45 56.73 68.51 89.92 57.84 70.40 93.49 70.03 80.08
MMPCACD 71.20 79.28 75.02 81.42 61.31 69.95 88.61 75.84 81.73 82.52 68.29 74.73 76.26 78.35 77.29
VAR 78.35 70.26 74.08 74.68 81.42 77.90 81.38 53.88 64.83 81.59 60.29 69.34 90.71 83.82 87.13
LSTM 78.55 85.28 81.78 85.45 82.50 83.95 89.41 78.13 83.39 86.15 83.27 84.69 76.93 89.64 82.80
CL-MPPCA 82.36 76.07 79.09 73.71 88.54 80.44 86.13 63.16 72.88 76.78 81.50 79.07 56.02 99.93 71.80
ITAD 86.22 73.71 79.48 69.44 84.09 76.07 82.42 66.89 73.85 63.13 52.08 57.08 72.80 64.02 68.13
LSTM-VAE 75.76 90.08 82.30 85.49 79.94 82.62 92.20 67.75 78.10 76.00 89.50 82.20 73.62 89.92 80.96
BeatGAN 72.90 84.09 78.10 89.75 85.42 87.53 92.38 55.85 69.61 64.01 87.46 73.92 90.30 93.84 92.04
OmniAnomaly 83.68 86.82 85.22 89.02 86.37 87.67 92.49 81.99 86.92 81.42 84.30 82.83 88.39 74.46 80.83
InterFusion 87.02 85.43 86.22 81.28 92.70 86.62 89.77 88.52 89.14 80.59 85.58 83.01 83.61 83.45 83.52
THOC 79.76 90.95 84.99 88.45 90.97 89.69 92.06 89.34 90.68 83.94 86.36 85.13 88.14 90.99 89.54
Ours 89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
4.1 MAINRESULTS
Real-worlddatasets Weextensivelyevaluateourmodelonfivereal-worlddatasetswithtencom-
petitivebaselines. AsshowninTable1,AnomalyTransformerachievestheconsistentstate-of-the-
artonallbenchmarks. Weobservethatdeepmodelsthatconsiderthetemporalinformationoutper-
formthegeneralanomalydetectionmodel, suchasDeep-SVDD(Ruffetal.,2018)andDAGMM
(Zongetal.,2018),whichverifiestheeffectivenessoftemporalmodeling. OurproposedAnomaly
Transformergoesbeyondthepoint-wiserepresentationlearnedbyRNNsandmodelsthemoreinfor-
mativeassociations.TheresultsinTable1arepersuasivefortheadvantageofassociationlearningin
timeseriesanomalydetection. Inaddition,weplottheROCcurveinFigure3foracompletecom-
parison. Anomaly Transformer has the highest AUC values on all five datasets. It means that our
modelperformswellinthefalse-positiveandtrue-positiveratesundervariouspre-selectedthresh-
olds,whichisimportantforreal-worldapplications.
7755
71.31
| NeurIPS-TS |     | benchmark | This | benchmark | is  | generated | from |     |     |     |
| ---------- | --- | --------- | ---- | --------- | --- | --------- | ---- | --- | --- | --- |
7700
well-designed rules proposed by Lai et al. (2021), which com- 67.45
)%( erocS-1F
| pletely | includes | all types | of anomalies, | covering |     | both | the point- | 6655 |     |     |
| ------- | -------- | --------- | ------------- | -------- | --- | ---- | ---------- | ---- | --- | --- |
62.52
| wiseandpattern-wiseanomalies.AsshowninFigure4,Anomaly |     |     |     |     |     |     |     |     | 60.14 |     |
| ----------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | ----- | --- |
6600
Transformer can still achieve state-of-the-art performance. This 58.39
56.51
5555
verifiestheeffectivenessofourmodelonvariousanomalies.
51.77
Ablationstudy AsshowninTable2,wefurtherinvestigatethe 5500 mor ma el yr e r an lyi - ly De Dp - DTTHHOOCC STTMM--VVAAEE DAAGGMMMM aatGtGANAN
|                             |     |     |     |                               |     |     |     | AA nn oof | fo rm m iAO n omm m ae ep-DSVe | D LS Bee  |
| --------------------------- | --- | --- | --- | ----------------------------- | --- | --- | --- | --------- | ------------------------------ | --------- |
|                             |     |     |     |                               |     |     |     | ra n      | s O n A n o D                  | S V L D B |
| effectofeachpartinourmodel. |     |     |     | Ourassociation-basedcriterion |     |     |     | T         |                                |           |
|                             |     |     |     |                               |     |     |     | Figure4:  | ResultsforNeurIPS-TS.          |           |
outperformsthewidely-usedreconstructioncriterionconsistently.
Specifically, the association-based criterion brings a remarkable 18.76% (76.20 94.96) averaged
| absoluteF1-scorepromotion. |     |     | Also,directlytakingtheassociationdiscrepancyasthecriterionstill |     |     |     |     |     |     | →   |
| -------------------------- | --- | --- | --------------------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- |
achievesagoodperformance(F1-score: 91.55%)andsurpassesthepreviousstate-of-the-artmodel
7

PublishedasaconferencepaperatICLR2022
THOC(F1-score: 88.01%calculatedfromTable1). Besides,thelearnableprior-association(corre-
spondingtoσinEquation2)andtheminimaxstrategycanfurtherimproveourmodelandget8.43%
(79.05 87.48)and7.48%(87.48 94.96)averagedabsolutepromotionsrespectively. Finally,our
→ →
proposed Anomaly Transformer surpasses the pure Transformer by 18.34% (76.62 94.96) abso-
→
lute improvement. These verify that each module of our design is effective and necessary. More
ablationsofassociationdiscrepancycanbefoundinAppendixD.
Table2: Ablationresults(F1-score)inanomalycriterion, prior-associationandoptimizationstrat-
egy. Recon,AssDisandAssocmeanthepurereconstructionperformance,pureassociationdiscrep-
ancyandourproposedassociation-basedcriterionrespectively. FixistofixLearnablescaleparam-
eterσofprior-associationas1.0. MaxandMinimaxreftothestrategiesforassociationdiscrepancy
inthemaximization(Equation4)andminimax(Equation5)wayrespectively.
Anomaly Prior- Optimization AvgF1
Architecture SMD MSL SMAP SWaT PSM
Criterion Association Strategy (as%)
Transformer Recon × × 79.72 76.64 73.74 74.56 78.43 76.62
Recon Learnable Minmax 71.35 78.61 69.12 81.53 80.40 76.20
Anomaly AssDis Learnable Minmax 87.57 90.50 90.98 93.21 95.47 91.55
Transformer Assoc Fix Max 83.95 82.17 70.65 79.46 79.04 79.05
Assoc Learnable Max 88.88 85.20 87.84 81.65 93.83 87.48
*final Assoc Learnable Minmax 92.33 93.59 96.90 94.07 97.89 94.96
4.2 MODELANALYSIS
Toexplainhowourmodelworksintuitively,weprovidethevisualizationandstatisticalresultsfor
ourthreekeydesigns: anomalycriterion,learnableprior-associationandoptimizationstrategy.
0.15 0.1 0.05 0 0 20 40 60 80 100 length eulav 0.15 0.1 0.05 0 0 20 40 60 80 100 Time ssoL laniF
10 8 6 4
2
0 0 20 40 60 80 100 length
eulav 10 8 6 4
2
0
ssoL noitcurtsnoceR 1.6 1.4 1.2 1 0.8 0.6 0.4
0.2
0 0 20 40Time60 80 100 0 20 40 length 60 80 100
eulav 1.6 1.4 1.2 1 0.8 0.6 0.4
0.2
0 0 20 40Time60 80 100
ssoL noitcurtsnoceR 0.7 0.6 0.5 0.4 0.3 0.2
0.1
0 0 20 40 60 80 100 length
eulav 0.7 0.6 0.5 0.4 0.3 0.2
0.1
0 00 2200 4400TTiimmee 6600 8800 110000
ssoL noitcurtsnoceR 2.5 2 1.5 1
0.5
00 20 40 60 80 100 length
eulav
0 20 40Time60 80 100
ssoL noitcurtsnoceR 1.5 2.5 2 1 1.5 1 0.5
0.5
0 0 0 20 40 60 80 100 length
eulav
0 20 40Time60 80 100
ssoL noitcurtsnoceR
4
3 2 1
0 -1 0 20 40 60 80 100 length 2 1.5 0.5
0
eulav
4
3 2 1
0 -1 0 20 40 60 80 100 Time
eulaV
1.5
1 0.5 0
-0.5 -1 -1.5 0 20 40 60 80 100 length
eulav
1.5
1 0.5 0
-0.5 -1 -1.5
eulaV
-0.3
-0.4 -0.5 -0.6 -0.7
-0.8 -0.9 0 20 40 60 80 100 -10 20 40 60 80 100 Time length
eulav
-0.3
-0.4 -0.5 -0.6 -0.7
-0.8 -0.9 -1 0 20 40Time60 80 100
eulaV
1.5
1 0.5 0
-0.5 -1 -1.5 0 20 40 60 80 100 length
eulav
0 20 40Time60 80 100
eulaV
1.5 1.5
1 1 0.5 0.5 0 0
-0.5 -0.5 -1 -1 -1.5 -1.5 0 20 40 60 80 100 length
eulav
0 20 40Time60 80 100
eulaV
1.5
1 0.5 0
-0.5 -1 -1.5
16 14 12 10 8 6 4 2 0 0 20 40 60 80 100 eulav 0.3 0.25 0.2 0.15 0.1 0.05 0 0 20 40 60 80 100 length ssoLe ulalanviF 0.3 0.08 0.25 0.06 0.2 0.15 0.04 0.1 0.02 0.05 0 0 0 20 40 Time 60 80 100 0 20 40 length 60 80 100 eulav 0 20 40 60 80 100 Time ssoL laniF 0.08 0.06 0.06 0.04 0.04 0.02 0.02 0 0 0 20 40 60 80 100 length eulav 0 20 40 60 80 100 Time ssoL laniF
Time Series Anomaly
Point Pattern
Global Contextual Shapelet Seasonal Trend
4 1.5 1.5 1.5 -0.3
3 -0.5 0.5 0.5 0.5 2 1 -0.7
-0.5 -0.5 -0.5 0 -1 -0.9 -1.5 -1.5 -1.5 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 Time Time Time Time Time 10 0.7 1.6 2 8 0.5 1.2 1.0 1.5 6 0.8 4 0.3 0.4 0.5 0.5
2 0.1
0 0 0 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 Time Time Time Time Time 0.3 0.08 00.0.066 0.2 0.03 0.06 0.06 (cid:19)0(cid:17)(cid:19).0(cid:23)4 0.02 (cid:19)(cid:17)(cid:19)(cid:23) 0.1 0.01 0.03 00.0.022 0.02 0 0 00 0 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 Time Time Time Time Time
tupnI
noitcurtsnoceR
desab-noitaicossA
seireS emiT
noiretirC
noiretirC
(cid:56) 作业要求 (cid:199)本次作业为单人 (cid:56) 作业 作 （需 业 独 要 立 求 完成）。 (cid:56) 作业要求 (cid:56) 作业要求
(cid:199)如与他人交流或使用开源代码、论文，请在报告中说明或给出引用。 (cid:56) 作业要求 (cid:199)由于作业(cid:46)(cid:46)(cid:71)较(cid:199)晚，本本次次作作业业为《单最人终作报业告（与需代独码立》完不成允）。许迟(cid:199)交本。次作业为单人作业（(cid:199)需本独次立作完业成为）。单人作业（需独立完成）。 (cid:199)本次作业为单人作业（需独立完成）。 (cid:199)在项目中遇到任何(cid:199)困如难与，他如人选交题流、或数使据用集开挑源选代或码者、技论术文方，案请(cid:199)设在计如报，与告请他中及人说时交明和流或助或给教使出联用引系开(cid:199)用。源如。代与码他、人论交文流，或请使在用报开告源中代说码明、或论给文出，引请用在。报告中说明或给出引用。 (cid:199) (cid:199) 如 由 与 于 他 作 人 业 交 (cid:46) 流 (cid:46)(cid:71) 或 较 使 晚 用 ， 开 本 源 次 代 作 码 业 、 《 论 最 文 终 ，De 报 请te 告 在c E 与 报t r i r o 代 o 告n r 码 中 》 说 不 明 允 或 许 给δ δ 迟 = = 出 交 0 0 引. . 0 5 。 用3。 (cid:199) (cid:199) 由 在 D 于 项 e 作 目 te 业 中 c E t 遇r (cid:46) i r o o到 (cid:46) n r (cid:71) 任 较 何 晚 困 ， 难 本 ， 次 如 作 选 业 题 《 、 最 数 终 据 报 集 (cid:199) (cid:199) 告 挑 由 在 D E 与 选 于 项r e 代 r或 t o 作 目 e 码 r者 c 业 中 t 》 技 i 遇 o (cid:46)不 术 n 到 (cid:46)允 方 (cid:71) 任 许 案 较 何 迟 设 晚 困 交 计 ， 难 (cid:199) (cid:199) 。 ， 本 ， 由 在请 次 如 于 项及 作 选 作 目时 业 题 业 中和 《 、遇助 最(cid:46) 数 D 到教 (cid:46)终 据 e (cid:71) 任联 报 t 集 e 较 何系 告 c 挑 晚 t 困。 与 i 选 o ， 难 n 代 或 本 ， 码 者 次 如 》 技 作 选 不 术 业 题 允 方 《 、 许 案 最 数 迟 设 终 据 交 计 报 集 。 ， 告 挑请 与 选及 代 或时 码 者和 》 技助 不 术教 允 方联 许 案系 迟 设。 交 计 。 ，请及时和助教联系。 (cid:199)在项目中遇到任何困难，如选题、数据集挑选或者技术方案设计，请及时和助δ教=联0系.0。3 δ=0.03 δ=0.03 Error (cid:56) 作业要求 参考文献 δ=0.5 δ=0.5 δ=0.5 δ=0.03
δ=0.5 (cid:199)
(cid:199)
本
如
次
与
作
他
业
人
为
交
单
流
人
或
作
使
业
用
(cid:40)(cid:82)(cid:41)（
开
(cid:49)
(cid:71)
需
源(cid:28)
(cid:88)
(cid:77)
(cid:46)独
代(cid:43)(cid:50)
(cid:81)立
码(cid:105)
(cid:77)(cid:59)
(cid:65)
完
、(cid:77)
(cid:45)
(cid:55)
(cid:62)成
论(cid:50)(cid:43)
(cid:88)）
文(cid:105)
(cid:46)
(cid:88)
。
，(cid:46)
(cid:109)(cid:45)
(cid:66)请(cid:98)
(cid:28)
(cid:88)参
(cid:77)
(cid:45)在
(cid:47)
(cid:107)报(cid:121)
(cid:71)
考(cid:107)
(cid:88)
告(cid:121)(cid:88)
(cid:58)
文中
(cid:28)(cid:96)
说
(cid:47)
献
(cid:77)
明
(cid:50)(cid:96)
或
(cid:88)
给
(cid:27)(cid:56)(cid:77)
出
(cid:66)(cid:77)
引
作(cid:105)(cid:50)
用
(cid:96)业(cid:28)
。
(cid:43)(cid:105)(cid:66)要(cid:112)(cid:50)求(cid:114)(cid:50)(cid:35)(cid:64)(cid:35)(cid:28)(cid:98)(cid:50)(cid:47)(cid:47)(cid:28)(cid:98)
参
(cid:63)(cid:35)(cid:81)
考
(cid:28)(cid:96)(cid:47)
文
(cid:105)(cid:81)
献
(cid:56)(cid:105)(cid:96)(cid:28)(cid:43)(cid:70)作(cid:43)(cid:81)(cid:112)业(cid:66)(cid:47)(cid:64)要(cid:82)(cid:78)求(cid:66)参(cid:77)(cid:56)(cid:96)(cid:50)考(cid:28)(cid:72)作(cid:105)文(cid:66)(cid:75)业(cid:50)献(cid:88)要求
参 (cid:40) (cid:40) (cid:40) (cid:56) (cid:82) (cid:107) (cid:106) (cid:41) (cid:41) (cid:41) (cid:199) (cid:199) (cid:199) (cid:199) 考 (cid:49) (cid:71) (cid:49) (cid:98) (cid:83) (cid:27) (cid:109) δ δ (cid:28) (cid:28) (cid:88) (cid:28) 作 (cid:98) (cid:96) 本 如 由 在 (cid:77) (cid:66) (cid:96) (cid:75) (cid:46) = = (cid:112) (cid:55) 文 (cid:105) (cid:43) (cid:50) (cid:63) 次 与 于 项 (cid:81) (cid:50) (cid:81) 业 (cid:49) (cid:118) 0 0 (cid:77) (cid:105) (cid:77) . . (cid:83) (cid:70) 作 他 作 目 (cid:77) 献 0 5 (cid:59) (cid:28) (cid:65) (cid:35) (cid:28) 要 (cid:77) 3 (cid:45) (cid:77) 业 人 业 中 (cid:28) (cid:67) (cid:105) (cid:55) (cid:47) (cid:62) (cid:114) (cid:50) (cid:72) (cid:88) (cid:45) (cid:43) 为 交 遇 求 (cid:88) (cid:28) (cid:77) (cid:69) (cid:46) (cid:105) (cid:27) (cid:45) (cid:46) (cid:81) (cid:88) 单 流 到 (cid:46) (cid:50) (cid:112) (cid:97) (cid:75) (cid:46) (cid:109) (cid:81) (cid:50) (cid:71) (cid:63) 人 或 任 (cid:59) (cid:45) (cid:72) (cid:66) (cid:66) (cid:66) (cid:98) (cid:105) (cid:63) (cid:28) (cid:112) (cid:28) 较 (cid:88) (cid:28) 作 使 何 (cid:45) (cid:77) (cid:45) (cid:28) (cid:84) (cid:112) (cid:47) (cid:75) 晚 (cid:97) (cid:107) (cid:84) (cid:28) 业 用 困 (cid:121) (cid:50) (cid:96) (cid:71) ， (cid:81) (cid:72) (cid:107) (cid:46) （ 开 难 (cid:97) (cid:66) (cid:88) (cid:28) (cid:121) (cid:77) (cid:63) (cid:28) 本 (cid:43) (cid:88) (cid:58) (cid:28) 需 源 ， (cid:28) (cid:98) (cid:63) (cid:45) (cid:96) (cid:28) 次 (cid:88) (cid:42) 独 代 如 (cid:75) (cid:96) (cid:28) (cid:107) (cid:63) (cid:47) 作 (cid:77) (cid:28) 立 码 选(cid:121) (cid:109) (cid:77) (cid:45) (cid:47) (cid:121) (cid:45) (cid:50) 业 完 、 题 (cid:97) (cid:107) (cid:96) (cid:46) (cid:104) (cid:88) (cid:88) (cid:96) 《 成 论 、 (cid:66) (cid:28) (cid:28) (cid:77) (cid:27) (cid:77) (cid:112) 最 参 (cid:40) 0 (cid:66) ） 文 数 (cid:82) (cid:77) (cid:112) (cid:75) (cid:66) . 。 (cid:47) (cid:41) 0 (cid:28) 终 0 ， 据 (cid:199) (cid:199)4 (cid:81) (cid:66) (cid:98) 考 (cid:49) (cid:71) (cid:77) (cid:74) (cid:118) 报 (cid:28) (cid:105)δ δ (cid:88)(cid:83) 请 集 (cid:50) (cid:77) 由 在 (cid:88) (cid:46) (cid:42) (cid:118) = = 文 (cid:96) 告 (cid:43) 在 挑 (cid:62) (cid:28) (cid:70) (cid:50) (cid:81) (cid:63) 于 项 (cid:105) (cid:43) (cid:77)(cid:72) 0 0 与 (cid:28) (cid:28) 报 选 (cid:45) (cid:105) 献 (cid:59) . . (cid:65) 作 目 (cid:70) (cid:96) (cid:66)0 5 (cid:77) (cid:45)(cid:111) (cid:105) (cid:112) 代 (cid:96) 告 或 3 (cid:55) (cid:45) (cid:62) (cid:50) (cid:28) 业 中 (cid:50) (cid:66)(cid:77) (cid:43)(cid:35) 码 (cid:28) (cid:88) 中 者 (cid:114) (cid:105) (cid:50) 遇 (cid:77) (cid:81) (cid:46) (cid:88) (cid:46) (cid:50) (cid:50) 》 (cid:96) (cid:47) 说 技 (cid:46) (cid:109)(cid:105) (cid:35) (cid:105) 到 (cid:46) (cid:63) (cid:118) (cid:45) (cid:64) 不 (cid:66) (cid:74) 明 术 (cid:88)(cid:98) (cid:35) (cid:71) (cid:28) 任 (cid:88) (cid:58) (cid:28) (cid:77) (cid:45) 允 (cid:66) 或 方 (cid:43) 较 (cid:98) (cid:47) (cid:54) 何 (cid:107) (cid:109) (cid:63) (cid:50) (cid:121) 许 (cid:84) (cid:66) 给 案 (cid:47) (cid:28) (cid:71) 晚 (cid:59)(cid:107) 困 (cid:40) (cid:40) (cid:105) (cid:50) (cid:107) (cid:106) (cid:88) (cid:63)(cid:121) 迟 (cid:63) (cid:47) 出 设 (cid:72) ，(cid:41) (cid:41) (cid:88) (cid:58) (cid:105) 难 (cid:28) (cid:28) (cid:66) (cid:67) 交 (cid:77) (cid:45) (cid:49) (cid:98) (cid:83) (cid:27) (cid:47) (cid:28) 引 计 (cid:98) 本 (cid:88) ，(cid:109) (cid:63) (cid:96) (cid:59) (cid:28) (cid:28) (cid:58) (cid:28) (cid:98) 。 (cid:47) (cid:96) (cid:83) (cid:35) 用 ， (cid:105) 次 (cid:66) (cid:96) (cid:75) 如 (cid:77) (cid:112) (cid:55) (cid:66) (cid:28) (cid:28) (cid:105)(cid:81) (cid:28) (cid:105)(cid:50) (cid:50) (cid:63) (cid:98) 。 请 (cid:77) (cid:81) (cid:28) (cid:28) (cid:120) 作 (cid:49) (cid:96) (cid:118)选 (cid:50) (cid:77) (cid:120) (cid:96) (cid:88)(cid:77) (cid:105) (cid:83) (cid:70) (cid:47) 及 (cid:28) (cid:66) (cid:77)业 (cid:28) (cid:68) (cid:88) (cid:27) 题 (cid:77) (cid:35) (cid:28) (cid:77) (cid:28) (cid:77) (cid:105) (cid:55) (cid:65) 时 (cid:72) (cid:28) (cid:77) (cid:67) (cid:105) (cid:66) 《 (cid:81) (cid:47) (cid:66) (cid:77) (cid:81) 、 (cid:88) (cid:114) (cid:72) (cid:88) (cid:47) (cid:45) (cid:66)(cid:69) 和 (cid:77) 最 (cid:28) (cid:77) (cid:105) (cid:42) (cid:69) (cid:50) (cid:97) 数 (cid:96) (cid:105) (cid:27) (cid:45) (cid:81) (cid:109) (cid:75) (cid:50)(cid:80) (cid:28) (cid:50) 助 (cid:50)终 (cid:112) (cid:75) 据 (cid:59) (cid:97) (cid:96) (cid:75) 0 (cid:43) (cid:81) (cid:66) (cid:50) (cid:76) (cid:28) (cid:75) (cid:70) (cid:43) (cid:63) 教 (cid:59)报 (cid:72) (cid:28)(cid:43) (cid:66) 集 (cid:44) (cid:97) (cid:66) (cid:105) (cid:63) (cid:105)(cid:96) (cid:50) (cid:112)(cid:43) (cid:28) (cid:28) (cid:66) 联 (cid:104) (cid:66) (cid:40) (cid:40) (cid:40) (cid:45) (cid:77) 告 (cid:81) (cid:112) (cid:28) (cid:84)挑 (cid:45) (cid:112) (cid:82) (cid:107) (cid:106) (cid:42) (cid:105) (cid:50) (cid:112)(cid:75) (cid:95) (cid:97) (cid:84) (cid:28) (cid:41) (cid:41) (cid:41)系 (cid:74) (cid:66) (cid:81) 与 (cid:66) 选 (cid:77) (cid:50) (cid:96) (cid:114) (cid:27) (cid:47) (cid:112) (cid:49) (cid:71) (cid:49) (cid:98) (cid:83) (cid:27) (cid:47) (cid:81) (cid:72) (cid:46) (cid:59) (cid:47) (cid:97) 。 (cid:50) (cid:64) (cid:66) (cid:109) (cid:66) 代 (cid:65) (cid:28) (cid:28)(cid:28)或 (cid:28) (cid:77)(cid:88) (cid:28) (cid:47) (cid:82) (cid:35) (cid:98) (cid:88) (cid:63) (cid:28) (cid:76) (cid:96) (cid:105) (cid:43)(cid:77) (cid:105) (cid:66) (cid:96) (cid:75) (cid:78) (cid:28) (cid:64) (cid:64) (cid:46) (cid:112) (cid:28) (cid:98) 码 (cid:55) (cid:28)(cid:97) (cid:66) (cid:63) (cid:105) (cid:35) (cid:82) 者 (cid:43) (cid:104)(cid:75) (cid:45)(cid:50) (cid:96) (cid:63) (cid:98) (cid:81) (cid:63) (cid:66) (cid:28) (cid:50)(cid:88) (cid:81) (cid:78) (cid:42) (cid:49) (cid:75) (cid:118) (cid:77) (cid:50) (cid:33) 》 (cid:98) (cid:77) (cid:105) (cid:77) 技 (cid:28) (cid:28) (cid:50) (cid:107) (cid:105) (cid:63) (cid:50) (cid:83) (cid:70) (cid:55) (cid:77) (cid:77) (cid:47) (cid:28) (cid:59) (cid:27) (cid:28) (cid:88) (cid:65) (cid:96) (cid:47) (cid:121) (cid:28) (cid:109)不 (cid:35) (cid:98) (cid:28) 术 (cid:77) (cid:45)(cid:50) (cid:45) (cid:47)(cid:77) (cid:121) (cid:50) (cid:70) (cid:27) (cid:65) (cid:45) (cid:28) (cid:67) (cid:105) (cid:27) (cid:28) (cid:47) (cid:55) (cid:47) (cid:62) (cid:77) (cid:97) (cid:107) (cid:96) (cid:50) 允 (cid:114) (cid:50) (cid:72) (cid:88) 方 (cid:72) (cid:28) (cid:46) (cid:27) (cid:104) (cid:66) (cid:45) (cid:88) (cid:70) (cid:96) (cid:43) (cid:50) (cid:88) (cid:98) (cid:28) (cid:77) (cid:42) (cid:105) (cid:69)(cid:66) (cid:77) (cid:28) (cid:63) (cid:105) 许 (cid:65) (cid:28) (cid:98) (cid:63) (cid:77) 案 (cid:27) (cid:66) (cid:45) 参 (cid:46) (cid:81) (cid:88) (cid:45)(cid:44) (cid:77) (cid:50) (cid:105) (cid:75) (cid:112) (cid:80)(cid:35) (cid:50)(cid:66) (cid:112) (cid:28) (cid:97) (cid:114) (cid:75) (cid:46) 迟 (cid:112) (cid:107) (cid:75) (cid:66)(cid:109) (cid:81) (cid:81) 设 (cid:50) (cid:76) (cid:27) (cid:47) (cid:50) (cid:96) (cid:28) (cid:199) (cid:199) (cid:199) (cid:199) (cid:63) (cid:121) (cid:28) (cid:59) (cid:45) (cid:98)考 (cid:72) (cid:66) (cid:88) (cid:45) (cid:66) (cid:81) (cid:98) 交 (cid:96) (cid:107) (cid:97) (cid:66) (cid:98) (cid:105) (cid:63) 计 (cid:28)(cid:74) (cid:112) (cid:118) δ δ (cid:28) (cid:47) (cid:88) (cid:28) (cid:82) (cid:104) (cid:45) 本 如 由 在 (cid:77) (cid:83) (cid:45) (cid:28) (cid:84) (cid:112) 。 (cid:88)= = 文 ， (cid:105) (cid:88)(cid:47) (cid:75) (cid:95) (cid:42) (cid:97) (cid:107) (cid:84) (cid:28) (cid:118) (cid:81) 次 与 于 项 (cid:62) (cid:121) (cid:50) (cid:96) (cid:70) (cid:27) (cid:63) 0 0 请 (cid:71) (cid:105) (cid:81) (cid:72) (cid:107) (cid:46) (cid:72) (cid:97) 献 . . (cid:28) (cid:28) (cid:66) (cid:96) 作 他 作 目 (cid:45) (cid:65) (cid:88) (cid:28) (cid:121) 0 5 (cid:77) (cid:28) (cid:63) 及 (cid:70) (cid:96) (cid:28) (cid:76) (cid:43) (cid:88) 3 (cid:58) (cid:111)(cid:28) (cid:43) (cid:105) (cid:28) (cid:98) (cid:96) 业 人 业 中 (cid:63) (cid:70) (cid:45) (cid:104) (cid:28) (cid:45) 时 (cid:96) (cid:66) (cid:28) (cid:88) (cid:42)(cid:77) (cid:75) (cid:35) (cid:28) (cid:33)(cid:43) 为 交 遇 (cid:96) (cid:28) (cid:46) (cid:107) (cid:50) (cid:81) 和 (cid:63) (cid:77)(cid:47) (cid:81) (cid:77) (cid:28) (cid:27) (cid:50) (cid:112) (cid:121) (cid:109) (cid:96) (cid:47)单 流 到 (cid:77) (cid:46) (cid:45) (cid:47) (cid:105) (cid:66) (cid:105)(cid:121) 助 (cid:27) (cid:45) (cid:47) (cid:50) (cid:63) (cid:118) (cid:71) (cid:97) (cid:107) (cid:74)人 或 任 (cid:96) (cid:64) (cid:88) (cid:46) (cid:27) (cid:104) (cid:88) (cid:82) 教 (cid:88) (cid:96) (cid:58)较 (cid:66) (cid:78) (cid:66) (cid:28) (cid:65) 作 使 何 (cid:28) (cid:77) (cid:43)(cid:27) (cid:54) (cid:45) (cid:109) 联 (cid:77) (cid:112) (cid:63) (cid:66) (cid:66) 晚 (cid:77) (cid:77) (cid:112) (cid:84) (cid:107) 业 用 困(cid:66) (cid:75) (cid:66) (cid:28) (cid:59) (cid:47) 系 (cid:28) (cid:121) (cid:105) (cid:50) (cid:96) (cid:63) ， (cid:81) (cid:66) (cid:63) (cid:98) （ 开 难 (cid:107)(cid:50) (cid:72)(cid:77) (cid:74) (cid:105) (cid:118) 。 (cid:28) (cid:28)(cid:82) (cid:105) (cid:66) (cid:83) (cid:67) 本 (cid:72) 需 源 ，(cid:77) (cid:45) (cid:88) (cid:50) (cid:88) (cid:40) (cid:40) (cid:40) (cid:88) (cid:42) (cid:118) (cid:96) (cid:105) (cid:59) (cid:82) (cid:107) (cid:106) (cid:58)次 (cid:62) (cid:66) (cid:28) (cid:70) 独 代 如 (cid:83) (cid:63) (cid:41) (cid:41) (cid:41) (cid:75) (cid:43) (cid:66) (cid:72) (cid:28) (cid:28) (cid:28) (cid:28) (cid:105) (cid:45) 作 (cid:105) (cid:50) (cid:49) (cid:71) (cid:49) (cid:98) (cid:83) (cid:27) (cid:47) 立 码 选(cid:77) (cid:70) (cid:96)(cid:28) (cid:120)(cid:66) (cid:88) (cid:109) (cid:111) (cid:28) (cid:28) (cid:105) (cid:112) (cid:28) (cid:88) (cid:28) (cid:120) (cid:77) (cid:96)(cid:98) 业 (cid:96) (cid:45) 完 、 题 (cid:105) (cid:77) (cid:50) (cid:28) (cid:28) (cid:66) (cid:66) (cid:96) (cid:75) (cid:68) (cid:66) (cid:46) (cid:112) (cid:55) (cid:77) (cid:28) (cid:105)(cid:77) (cid:28) (cid:35) (cid:77) (cid:43) (cid:28) 《 (cid:50) (cid:114) (cid:63) (cid:98) (cid:55) (cid:81) 成 论 、 (cid:50) (cid:81) (cid:72) (cid:50) (cid:77) (cid:66) (cid:81)(cid:49) (cid:118) (cid:81) (cid:50) (cid:66) (cid:88) (cid:77) (cid:105) (cid:50) (cid:77)(cid:50) (cid:96) (cid:47) (cid:105) (cid:47) 最 (cid:83) (cid:70) (cid:105) ） 文 数 (cid:69) (cid:35) (cid:77) (cid:105) 参 (cid:59) (cid:28) (cid:88) (cid:65) (cid:50) (cid:97) (cid:63) (cid:35)(cid:118) 。 (cid:28) (cid:64) (cid:77) (cid:45) (cid:77) (cid:74)(cid:109)终 (cid:75) (cid:65) (cid:88) (cid:35)(cid:50) (cid:28) ， 据 (cid:67) (cid:105) (cid:55) (cid:47) (cid:62) (cid:77) (cid:199) (cid:199) (cid:199) (cid:199) (cid:58) (cid:75) (cid:59) (cid:114) (cid:50) (cid:72) (cid:28) 考 (cid:88)(cid:66) (cid:66) (cid:45) 报 (cid:43) (cid:75) (cid:43) (cid:43) 请 集 (cid:98)(cid:88) (cid:54) (cid:28) (cid:77) (cid:109) (cid:42) δ δ (cid:28) (cid:69)(cid:63) (cid:105) (cid:50) (cid:44) (cid:27) 本 如 由 在 (cid:45) (cid:46) (cid:81) (cid:88) (cid:84) (cid:96) (cid:66) (cid:50) 告 (cid:47) (cid:80) (cid:28) = = 文 在 挑 (cid:59) (cid:50) (cid:66) (cid:112) (cid:77) (cid:105)(cid:97) (cid:75) (cid:46) (cid:50)(cid:45) (cid:109) (cid:42) (cid:81) (cid:63) 次 与 于 项 (cid:50) (cid:63) (cid:76) (cid:105)(cid:47) 与 (cid:72) (cid:63) (cid:59) (cid:45) 报 选 0 0 (cid:105) (cid:74) (cid:72) (cid:66) (cid:66) (cid:81) (cid:66) (cid:28) (cid:28)(cid:77) (cid:97)献 (cid:66) (cid:98) (cid:66)(cid:105) (cid:63) . . (cid:67) 作 他 作 目 (cid:28) (cid:112) (cid:112) (cid:77) (cid:28) (cid:45) 0 5 代 (cid:98) (cid:88) (cid:28) (cid:59) (cid:104) 告 或 (cid:47)(cid:88)(cid:45) (cid:77) (cid:45) (cid:66) (cid:28) (cid:63) (cid:84) (cid:59) 3 (cid:112) (cid:58) (cid:47) (cid:88) 业 人 业 中 (cid:47) (cid:75) (cid:95) (cid:83)(cid:97) (cid:35) (cid:107) (cid:84) 码 (cid:28) (cid:105) 中 者(cid:64) (cid:66) (cid:97) (cid:66) (cid:28) (cid:121) (cid:50) (cid:81) (cid:82) (cid:96) (cid:28) (cid:27) (cid:105) (cid:75) 为 交 遇 (cid:71) (cid:81) (cid:72) (cid:77) (cid:107) (cid:46) 》(cid:63) (cid:28) (cid:78) (cid:28) (cid:120) (cid:46) (cid:40) (cid:40) (cid:40)(cid:97) 说 技 (cid:66) (cid:65) (cid:82) (cid:107) (cid:106) (cid:88) 参 (cid:28) (cid:121) (cid:77)(cid:120) (cid:96) (cid:28) (cid:50) (cid:77)(cid:63) (cid:28) (cid:76) 单 流 到 (cid:46) (cid:41) (cid:41) (cid:41) (cid:47) (cid:43) 不 (cid:88) (cid:28) (cid:66) (cid:55) (cid:58) (cid:47) (cid:28) (cid:68) 明 术 (cid:28) (cid:98)(cid:77) (cid:28) (cid:63) (cid:98) (cid:28) (cid:77) (cid:104) (cid:71) (cid:199) (cid:199) (cid:199) (cid:199) (cid:45) (cid:49) (cid:71) (cid:49) (cid:98) (cid:83) (cid:27) (cid:47) (cid:96) 人 或 任 (cid:50) (cid:28) (cid:70) (cid:105) (cid:55) 考 (cid:88) (cid:72) 允 (cid:42) (cid:27)(cid:66) (cid:109) (cid:75) 或 方 (cid:81) (cid:66) (cid:33) (cid:81)(cid:96) (cid:28) (cid:28) (cid:88) (cid:96) (cid:50) (cid:28) (cid:88) (cid:28) (cid:28)(cid:98) δ δ 较 (cid:107) (cid:66) (cid:96) (cid:47) (cid:63) (cid:47) 作 使 何(cid:70) (cid:105) (cid:77) (cid:66) (cid:96)(cid:69) 本 如 由 在 (cid:75) (cid:50) (cid:77) 许 (cid:28) (cid:27) (cid:46) (cid:112) (cid:105) 给 案 (cid:55) (cid:121) (cid:28) (cid:109) (cid:50) (cid:97) = = (cid:77) (cid:105) 文 (cid:77) (cid:63) (cid:43) (cid:98) (cid:45) (cid:96) (cid:47) 晚 (cid:50)(cid:121) (cid:63) (cid:98) (cid:109) (cid:75) 业 用 困(cid:81) (cid:27) (cid:44) (cid:50) (cid:45) (cid:81) (cid:50) (cid:50) (cid:105) (cid:50)(cid:28) 次 与 于 项 (cid:49) 迟 (cid:118) (cid:50) 出 设 (cid:97) (cid:107) (cid:28) (cid:75) (cid:77) (cid:105) (cid:59) (cid:114) (cid:96)(cid:77) 0 0 (cid:43) (cid:46) (cid:27)(cid:105) (cid:66)(cid:104) ， (cid:83) (cid:70) (cid:27) (cid:88) (cid:88) 献 (cid:96) (cid:96) （ 开 难(cid:75) (cid:70) . . (cid:77) (cid:43) (cid:59) (cid:28) 作 他 作 目 (cid:88) (cid:65) 交 (cid:98) (cid:28) 0 5(cid:66) (cid:45) 引 计 (cid:35)(cid:28) (cid:65) (cid:44) (cid:28) (cid:28) (cid:77) (cid:45) (cid:77) (cid:77) (cid:27) 本 3 (cid:96) (cid:50) (cid:45)(cid:65) (cid:43) (cid:77)(cid:28) 需 源 ，(cid:112)(cid:67) (cid:105) 业 人 业 中 (cid:55) 。 (cid:47) (cid:66)(cid:66) (cid:62) (cid:77) (cid:77) 用 ， (cid:81) (cid:114) (cid:50) (cid:77) (cid:72) (cid:112) (cid:107) (cid:45) (cid:75) (cid:66) (cid:42) (cid:88) (cid:45) 次 (cid:47)(cid:105) (cid:112) (cid:43) (cid:28) 独 代 如 (cid:88) (cid:121) (cid:28) (cid:77) 为 交 遇 (cid:42) (cid:74) (cid:66)(cid:69) (cid:81) (cid:105) (cid:81) 。 请 (cid:66)(cid:66) (cid:46) (cid:98) (cid:77) (cid:107) (cid:27) (cid:45) (cid:46)(cid:77) (cid:81) (cid:47) (cid:88) (cid:112) (cid:74) 作 (cid:118) (cid:80) 立 码 选(cid:50) (cid:82) (cid:59) (cid:47) 单 流 到(cid:112) (cid:105) (cid:46) (cid:64) (cid:83) (cid:66) (cid:97) (cid:75) (cid:46) 及 (cid:109) (cid:81) (cid:88) (cid:47) (cid:82)(cid:50) (cid:50) (cid:76) (cid:88) (cid:88) 业 (cid:63) (cid:42) (cid:118) 完 、 题(cid:59) (cid:45) (cid:105) (cid:71) (cid:96)(cid:78) (cid:72) (cid:66) (cid:64) 人 或 任 (cid:66) 时 (cid:97) (cid:66)(cid:62) (cid:97) (cid:66) (cid:98) (cid:28) (cid:105)(cid:82) (cid:63) (cid:70) (cid:63) (cid:28) (cid:75) (cid:112) (cid:28) 《 (cid:88) (cid:28) (cid:63) (cid:66)(cid:43) 较 成 论 、 (cid:78) (cid:104) (cid:72) (cid:45) (cid:77) 作 使 何 (cid:45) (cid:28) (cid:28) (cid:28) (cid:77) (cid:84) (cid:45) (cid:112) 和 (cid:105) (cid:28) (cid:50) (cid:70) (cid:96) (cid:47) (cid:75) (cid:95) (cid:97) (cid:107) (cid:66) (cid:84) 最 (cid:28) 晚 (cid:55) ） 文 数 (cid:111)(cid:47) (cid:105) (cid:112) 业 用 困 (cid:96) (cid:96) (cid:121) (cid:28) (cid:50) (cid:96) (cid:98) 助 (cid:27) (cid:45) 。 (cid:50)(cid:50) (cid:28) (cid:71) (cid:81) (cid:66) (cid:50)(cid:72) (cid:107) (cid:70) 终 (cid:46) (cid:97) ， (cid:27) ， 据 (cid:28) (cid:77) (cid:66) (cid:35) （ 开 难(cid:28) (cid:65) (cid:96) (cid:88) (cid:28) (cid:121) (cid:50) (cid:77) 教 (cid:114)(cid:72) (cid:63) (cid:28) (cid:76) (cid:50) (cid:66)(cid:77) (cid:81) (cid:70) (cid:43) 报 (cid:88) (cid:58) (cid:50)(cid:28) 本 请 集 (cid:50)(cid:28) (cid:98) (cid:50)(cid:105) 需 源 ，(cid:63) (cid:96)(cid:77) (cid:47) (cid:63) (cid:104) (cid:98) 联 (cid:45) (cid:105) (cid:66)(cid:35) (cid:96) (cid:105) (cid:28) (cid:44) (cid:88) 告 (cid:50) (cid:105) (cid:75) (cid:42) (cid:63) 次 (cid:75) (cid:118) 在 挑 (cid:33) (cid:64) 独 代 如 (cid:96) (cid:28) (cid:74) (cid:114)(cid:28) 系 (cid:88) (cid:35) (cid:107) (cid:63) (cid:47) (cid:27) (cid:50) (cid:96) (cid:77) 与 (cid:28) (cid:27) (cid:58) 作 报 选 (cid:98) (cid:121) (cid:28) (cid:109) (cid:88) (cid:45) 立 码 选 (cid:77) (cid:66) (cid:45) (cid:47) 。 (cid:43) (cid:121) (cid:98) (cid:54) (cid:27) (cid:45) (cid:109) (cid:50) 代 (cid:63) (cid:50) 业 告 或 (cid:97) (cid:107) 完 、 题 (cid:96) (cid:84) (cid:66) (cid:46) (cid:27) (cid:47) (cid:28) (cid:104) (cid:88) (cid:59) (cid:88) (cid:96)(cid:105) 码 (cid:50) 《 (cid:66) 中 者 (cid:63)(cid:28) (cid:65) (cid:28) 成 论 、 (cid:63)(cid:77) (cid:47)(cid:27) (cid:72) (cid:45) (cid:77)(cid:105) (cid:112) (cid:28) 》 (cid:66) (cid:28) 最 (cid:66) 说 技(cid:67) (cid:77) (cid:112) (cid:107) (cid:75) ） 文 数 (cid:66) (cid:77) (cid:45) (cid:98) (cid:47) (cid:28) (cid:88) (cid:121) 。 (cid:63) 不 (cid:59) (cid:58) 终 (cid:81) 明 术 (cid:66) (cid:98) (cid:107) ， 据(cid:83) (cid:77)(cid:35) (cid:74) (cid:118) (cid:82) (cid:66) 允 (cid:28) (cid:105)(cid:81) (cid:83) (cid:28) 报 或 方 (cid:105) 请 集 (cid:88) (cid:50) (cid:77) (cid:88) (cid:28) (cid:28) (cid:120) (cid:42) (cid:118) (cid:96) 许 (cid:120) (cid:96) (cid:77) 告 给 案(cid:62) (cid:28) (cid:70) 在 挑 (cid:63) (cid:47) (cid:28) (cid:66) (cid:68) (cid:43) (cid:72) (cid:77)(cid:28) (cid:28) 迟 (cid:28) (cid:77) (cid:45) 与 出 设 (cid:105) 报 选 (cid:105) (cid:55)(cid:70) (cid:96) (cid:72) (cid:66) (cid:66) (cid:81) (cid:66) (cid:81) (cid:111) (cid:105) (cid:112) (cid:88) 交 (cid:96) 代 引 计 (cid:47) (cid:45) 告 或 (cid:50) (cid:28) (cid:69)(cid:66) (cid:105) (cid:50) (cid:97) (cid:77) (cid:35) (cid:28) 。 (cid:96) 码 用 ， (cid:114) (cid:109) (cid:75) 中 者(cid:50) (cid:50) (cid:28) (cid:77) (cid:81) (cid:75) (cid:59) (cid:50) (cid:50)(cid:43) (cid:96) (cid:47) (cid:66) 》 。 请 (cid:105) 说 技(cid:75) (cid:35)(cid:70) (cid:43)(cid:105) (cid:28)(cid:63) (cid:118)(cid:44) (cid:64) (cid:74) 不 (cid:96) 及(cid:50) (cid:88) (cid:35)(cid:43)明 术 (cid:66) (cid:77) (cid:58) (cid:81)(cid:28) (cid:45) (cid:42) (cid:66) 允 (cid:105)时 (cid:112) (cid:43) (cid:98) 或 方 (cid:54) (cid:109)(cid:74) (cid:66) (cid:81) (cid:63) (cid:50)(cid:66) (cid:77) (cid:47) (cid:84) (cid:66)(cid:112) 许 (cid:47) 和(cid:28) 给 案 (cid:59) (cid:59) (cid:47) (cid:64) (cid:105) (cid:66) (cid:50) (cid:63)(cid:47) (cid:82) (cid:63)(cid:88) (cid:47) 迟 助(cid:72)(cid:105) 出 设 (cid:105) (cid:78) (cid:64) (cid:28) (cid:28) (cid:97) (cid:66) (cid:66)(cid:82) (cid:67)(cid:75) (cid:77) (cid:45) 交 (cid:98) 教 (cid:63) (cid:66) (cid:78) 引 计 (cid:88) (cid:63)(cid:77) (cid:59) (cid:58)(cid:28) (cid:50)(cid:83) (cid:35) 。 联 (cid:55) 用 ， (cid:47) (cid:96) (cid:66) (cid:28)(cid:28) (cid:81) (cid:98)(cid:28) (cid:105) (cid:50) (cid:50) (cid:77)(cid:70) 系 (cid:28) (cid:28) (cid:120) (cid:27) (cid:28)。 请(cid:96) (cid:50) (cid:120) (cid:96) (cid:77) (cid:72) (cid:66) (cid:70) (cid:47) (cid:28) (cid:66) 。(cid:50) (cid:68) 及 (cid:77) (cid:105) (cid:77) (cid:63)(cid:28) (cid:77)(cid:98) (cid:66)(cid:105) (cid:55) (cid:44) (cid:72) (cid:50) (cid:105) (cid:75) (cid:66) (cid:81) 时 (cid:66) (cid:81) (cid:88) (cid:28) (cid:114)(cid:47) (cid:27) (cid:50) (cid:96)(cid:69) (cid:105) (cid:98) 和 (cid:50) (cid:97) (cid:88) (cid:45) (cid:96) (cid:109) (cid:75) (cid:50) (cid:28) 助 (cid:75) (cid:59) (cid:43) (cid:66) (cid:75) (cid:70) (cid:43) (cid:28) 教 (cid:44) (cid:96) (cid:50) (cid:43) (cid:66) (cid:77) (cid:81) 联 (cid:45) (cid:42) (cid:105) (cid:112) (cid:74) (cid:66) (cid:81) 系 (cid:66) (cid:77) (cid:47) (cid:112) (cid:59) (cid:47) (cid:64) (cid:66) 。 (cid:47) (cid:82) (cid:88) (cid:105) (cid:78) (cid:64) (cid:97) (cid:66) (cid:82) (cid:75) (cid:63) (cid:66) (cid:78) (cid:77) (cid:28) (cid:50) (cid:55) (cid:47) (cid:96) (cid:28) (cid:98) (cid:50) (cid:50) (cid:70) (cid:27) (cid:28) (cid:96) (cid:50) (cid:72) (cid:66) (cid:70) (cid:50) (cid:105) (cid:77) (cid:63) (cid:98) (cid:66) (cid:44) (cid:50) (cid:105) (cid:75) (cid:28) (cid:114) (cid:27) (cid:50) (cid:96) (cid:98) (cid:88) (cid:45) Figu参re考 (cid:47)(cid:28)(cid:105) 文 (cid:28) 5 (cid:98)(cid:50) :献 (cid:105)(cid:88)(cid:65)(cid:77) V (cid:42) i (cid:80) s (cid:76) u (cid:97)(cid:104) a (cid:95)(cid:27) li (cid:65)(cid:76) z (cid:104) a (cid:33)(cid:27) ti (cid:27) o (cid:27)(cid:65) n (cid:45)(cid:40)(cid:107)(cid:107)(cid:41)(cid:121)(cid:107) o (cid:49) (cid:98)(cid:109) (cid:82)(cid:28) (cid:96) (cid:88)(cid:75) f(cid:112)(cid:50) (cid:81) (cid:118) (cid:77) d (cid:77) (cid:28)(cid:77) (cid:67) i(cid:47) (cid:88) f(cid:77) (cid:69) f(cid:81) (cid:50) (cid:112)e (cid:81) (cid:50) (cid:59) (cid:72)r (cid:63) (cid:28) (cid:45) (cid:84)e (cid:97) (cid:84) (cid:50) (cid:96)n(cid:81) (cid:72)(cid:66) (cid:28) (cid:77) t(cid:43) (cid:28) (cid:63)(cid:88) (cid:42) a(cid:107) (cid:63) (cid:121) (cid:109) n(cid:121) (cid:45) (cid:107) (cid:46) (cid:88)o (cid:28)(cid:112) m (cid:66)(cid:47)(cid:74) a (cid:88) l (cid:62) y (cid:28)(cid:96)(cid:105)(cid:45) c (cid:28)(cid:77) a (cid:47)(cid:74) te (cid:66)(cid:43)(cid:63) g (cid:28)(cid:50) o (cid:72)(cid:67)(cid:88) r(cid:40)(cid:82)(cid:83) i(cid:41)(cid:28) e (cid:120)(cid:49) (cid:71) (cid:120) (cid:28) s(cid:88)(cid:28) (cid:77) (cid:77)(cid:46) (cid:43) (cid:66) (cid:50) (cid:81)(cid:88) ( (cid:105) (cid:77)(cid:97)(cid:59) (cid:65) L (cid:50) (cid:77) (cid:45)(cid:59) (cid:55) (cid:62) (cid:50) (cid:75) a (cid:43) (cid:88) (cid:105) (cid:50)(cid:46) (cid:88) (cid:77) i (cid:105) (cid:46) (cid:109)(cid:66)(cid:45)(cid:77) (cid:66) e (cid:98) (cid:59)(cid:28) (cid:88) (cid:77) (cid:45) (cid:105) t(cid:47) (cid:107) (cid:66)(cid:75) (cid:121) (cid:71) (cid:107) (cid:50) a(cid:88) (cid:121)(cid:88) (cid:98)(cid:58)l (cid:50)(cid:28)(cid:96) . (cid:66)(cid:96)(cid:50) ,(cid:47)(cid:98)(cid:77)(cid:44)(cid:50)2 (cid:27)(cid:96)(cid:88)0(cid:27)(cid:77)2(cid:66)(cid:77) (cid:40) 1(cid:105) (cid:82) (cid:50) (cid:41) (cid:96))(cid:28) (cid:49) (cid:71) (cid:43).(cid:28) (cid:88) (cid:105) (cid:77) (cid:66) (cid:46) (cid:112) (cid:43) (cid:50) (cid:50) (cid:81) (cid:105)W (cid:77) (cid:114) (cid:59) (cid:65) (cid:50) (cid:77) (cid:45) (cid:35) (cid:55) (cid:62) (cid:64) (cid:50)e(cid:35) (cid:43) (cid:88) (cid:28) (cid:105) (cid:46) (cid:88) (cid:98)(cid:40)(cid:50) (cid:46) (cid:109)(cid:82)p(cid:47)(cid:41)(cid:45) (cid:66)(cid:98) (cid:47) (cid:28)(cid:49) (cid:71)(cid:88)l (cid:77) (cid:28) (cid:45)(cid:28) (cid:88)o(cid:98) (cid:47) (cid:107)(cid:77) (cid:63)(cid:46) (cid:121)(cid:43) (cid:35) (cid:71) (cid:107)t (cid:50) (cid:81)(cid:81) (cid:88) (cid:121)(cid:105) (cid:77)(cid:28) (cid:88) (cid:58)(cid:59) (cid:65) (cid:96)t (cid:77) (cid:45)(cid:47) (cid:28) (cid:55) h(cid:62)(cid:96) (cid:50) (cid:105) (cid:47) (cid:43) (cid:88)(cid:81) (cid:77) (cid:105) e(cid:46) (cid:88) (cid:50) (cid:105)(cid:96) (cid:96) (cid:46) (cid:109)(cid:28) (cid:88)(cid:45) (cid:66) (cid:43)r (cid:98) (cid:27)(cid:28)(cid:70) (cid:88) (cid:77) (cid:45) (cid:77) a(cid:43)(cid:47) (cid:107) (cid:81) (cid:66) (cid:121) w (cid:77) (cid:112)(cid:71) (cid:107) (cid:105) (cid:66)(cid:88)(cid:47) (cid:121) (cid:50) (cid:88) (cid:96) (cid:64)(cid:58)(cid:82) (cid:28) (cid:78)(cid:28)(cid:43) s (cid:105)(cid:96)(cid:66) (cid:66)(cid:47)(cid:77) (cid:112) e(cid:77)(cid:50)(cid:50)(cid:96)r(cid:50) (cid:114)(cid:96)(cid:88)(cid:28) (cid:50) i(cid:72) (cid:35)(cid:27)e(cid:105) (cid:64)(cid:77)(cid:66) (cid:35) (cid:75)s (cid:28)(cid:66)(cid:50)(cid:77)(cid:98)(cid:50) (cid:88)(cid:105)(cid:47)(cid:50)(cid:96)(cid:47)(cid:28)(cid:43)(cid:28)(cid:105)(cid:98)(cid:66)(cid:63)(cid:112)(cid:35)(cid:50)(cid:81)(cid:114)(cid:28)(cid:96)(cid:50)(cid:47)(cid:35)(cid:64)(cid:105)(cid:35)(cid:81)(cid:28)(cid:98)(cid:105)(cid:50)(cid:96)(cid:47)(cid:28)(cid:43)(cid:47)(cid:70)(cid:28)(cid:43)(cid:98)(cid:81)(cid:63)(cid:112)(cid:35)(cid:66)(cid:81)(cid:47)(cid:28)(cid:64)(cid:82)(cid:96)(cid:47)(cid:78)(cid:105)(cid:66)(cid:77)(cid:81)(cid:96)(cid:105)(cid:50)(cid:96)(cid:28)(cid:28)(cid:43)(cid:72)(cid:70)(cid:105)(cid:66)(cid:43)(cid:75)(cid:81)(cid:50)(cid:112)(cid:88)(cid:66)(cid:47)(cid:64)(cid:82)(cid:78)(cid:66)(cid:77)(cid:96)(cid:50)(cid:28)(cid:72)(cid:105)(cid:66)(cid:75)(cid:50)(cid:88)
(firs(cid:40)t(cid:82)(cid:41)r(cid:49)o(cid:88)(cid:46)w(cid:81)(cid:77)(cid:59))(cid:45)(cid:62)f(cid:88)(cid:46)r(cid:109)o(cid:45)(cid:28)m(cid:77)(cid:47)(cid:71)(cid:88)N(cid:58)(cid:28)e(cid:96)(cid:47)(cid:77)u(cid:50)(cid:96)r(cid:88)(cid:27)I(cid:77)P(cid:66)(cid:77)(cid:40)S(cid:106)(cid:105)(cid:41)(cid:50)(cid:96)(cid:83)-(cid:28)(cid:43)(cid:28)T(cid:105)(cid:96)(cid:66)(cid:105)(cid:112)(cid:63)(cid:50)S(cid:83)(cid:114)(cid:28)(cid:50)(cid:105)(cid:35)d(cid:114)(cid:64)(cid:35)(cid:28)a(cid:45)(cid:28)(cid:98)(cid:97)(cid:50)t(cid:63)(cid:47)a(cid:66)(cid:112)(cid:47)(cid:28)(cid:28)s(cid:75)(cid:98)(cid:63)e(cid:35)(cid:97)(cid:81)(cid:63)t(cid:28)(cid:28),(cid:96)(cid:96)(cid:47)(cid:75)a(cid:28)(cid:105)(cid:81)(cid:45)s(cid:97)(cid:105)(cid:96)(cid:96)(cid:28)(cid:66)w(cid:77)(cid:43)(cid:70)(cid:66)(cid:112)(cid:28)(cid:43)e(cid:98)(cid:81)(cid:112)(cid:83)l(cid:66)(cid:47)(cid:118)l(cid:64)(cid:70)(cid:82)(cid:72)(cid:78)(cid:45)a(cid:111)(cid:66)(cid:77)s(cid:66)(cid:77)(cid:96)(cid:50)(cid:50)(cid:50)(cid:28)t(cid:105)(cid:72)h(cid:63)(cid:105)(cid:66)(cid:58)(cid:75)e(cid:109)(cid:50)i(cid:84)(cid:88)(cid:105)r(cid:63)(cid:28)(cid:45)c(cid:58)(cid:40)(cid:107)o(cid:66)(cid:41)(cid:105)(cid:28)(cid:49)r(cid:77)(cid:28)(cid:68)r(cid:75)(cid:28)(cid:72)e(cid:66)(cid:81)(cid:77)(cid:69)s(cid:77)(cid:109)p(cid:75)(cid:67)(cid:88)(cid:28)o(cid:69)(cid:96)(cid:66)(cid:45)(cid:50)n(cid:81)(cid:74)(cid:59)(cid:63)d(cid:47)(cid:45)(cid:88)(cid:97)i(cid:97)(cid:50)(cid:63)n(cid:72)(cid:28)(cid:66)(cid:77)(cid:47)g(cid:28)(cid:27)(cid:42)(cid:70)(cid:63)r(cid:63)(cid:109)(cid:105)e(cid:45)(cid:28)(cid:96)(cid:46)c(cid:45)(cid:28)(cid:112)o(cid:66)(cid:47)n(cid:74) (cid:40)(cid:107)s(cid:88) (cid:41) (cid:62)t(cid:49) (cid:28)r(cid:28) (cid:96) (cid:75) (cid:105)u(cid:45) (cid:81) (cid:28) (cid:77)c(cid:77) (cid:77) (cid:47)t(cid:67)i(cid:74) (cid:88)o(cid:69) (cid:66)(cid:43) (cid:50) (cid:63)(cid:40)n(cid:107)(cid:81) (cid:28)(cid:41)(cid:59) (cid:50) (cid:63) (cid:72)(cid:49)(cid:45)((cid:67)(cid:28)(cid:97) (cid:88)(cid:75)s(cid:50) (cid:83) (cid:72)(cid:81)(cid:66)e(cid:28) (cid:77)(cid:77)(cid:120) (cid:28)(cid:77)c(cid:120)(cid:28) (cid:42)(cid:67)(cid:77)o(cid:88)(cid:63) (cid:66)(cid:88)(cid:69)(cid:109)n(cid:45)(cid:50)(cid:97)(cid:81)(cid:46) (cid:50)d(cid:59)(cid:59) (cid:28)(cid:63)(cid:75) (cid:112)(cid:45)(cid:66) (cid:50) (cid:47)(cid:97)r(cid:77)(cid:50)(cid:105) (cid:74)o(cid:72)(cid:66)(cid:66)(cid:77)(cid:77)(cid:88) (cid:59)w(cid:28)(cid:62) (cid:105)(cid:42)(cid:28) (cid:66)(cid:75) (cid:96)(cid:63))(cid:105)(cid:109)(cid:50) (cid:45)(cid:45)(cid:28) (cid:98)a(cid:46)(cid:50) (cid:77) (cid:96) (cid:47)(cid:28)n(cid:66)(cid:50)(cid:112)(cid:98) (cid:74)(cid:66)(cid:44)d(cid:47)(cid:66)(cid:43) (cid:27)(cid:74)(cid:63)(cid:28)(cid:88)(cid:50)(cid:62)(cid:72)(cid:28)(cid:67)(cid:96)(cid:88)(cid:105)(cid:83)(cid:45)(cid:28)(cid:28)(cid:120)(cid:77)(cid:120)(cid:47)(cid:28)(cid:77)(cid:74)(cid:66)(cid:88)(cid:66)(cid:43)(cid:97)(cid:63)(cid:50)(cid:28)(cid:59)(cid:50)(cid:75)(cid:72)(cid:67)(cid:50)(cid:88)(cid:77)(cid:105)(cid:83)(cid:66)(cid:77)(cid:28)(cid:59)(cid:120)(cid:120)(cid:105)(cid:28)(cid:66)(cid:77)(cid:75)(cid:66)(cid:88)(cid:50)(cid:97)(cid:98)(cid:50)(cid:50)(cid:96)(cid:59)(cid:66)(cid:75)(cid:50)(cid:98)(cid:50)(cid:44)(cid:77)(cid:27)(cid:105)(cid:66)(cid:77)(cid:59)(cid:105)(cid:66)(cid:75)(cid:50)(cid:98)(cid:50)(cid:96)(cid:66)(cid:50)(cid:98)(cid:44)(cid:27)
asso (cid:40)(cid:107) c (cid:41) i(cid:71) (cid:49) a(cid:28) (cid:28) (cid:77) (cid:75) t(cid:43) (cid:81) (cid:50)i (cid:77) (cid:105)o (cid:77) (cid:65)(cid:77) (cid:67) (cid:55)n(cid:50) (cid:88) (cid:43) (cid:69) (cid:105)-(cid:88) (cid:50) b(cid:46) (cid:81)(cid:59) (cid:66)(cid:98) (cid:63) a(cid:88) (cid:45) (cid:45)s (cid:97) (cid:107)(cid:121) (cid:50) e (cid:72) (cid:107) (cid:66) (cid:121) (cid:77) d(cid:88) (cid:28)(cid:42)(cid:63) c (cid:109)(cid:45) r (cid:46) i (cid:28) t (cid:112) e (cid:66)(cid:47) r (cid:74) i (cid:88) a (cid:27) (cid:47) (cid:62) (cid:28) (cid:98) (cid:28) (cid:105) (cid:66) (cid:96) (cid:55) (cid:28)( (cid:105) (cid:98) (cid:45) (cid:49) (cid:50)t(cid:105) (cid:28) (cid:70) h(cid:88) (cid:77) (cid:35) (cid:47) (cid:65) (cid:28) (cid:77)i (cid:72)(cid:45) (cid:74) r(cid:42) (cid:27) (cid:66) (cid:80)d (cid:43) (cid:75) (cid:63) (cid:76) (cid:28) (cid:66) (cid:97) (cid:105) (cid:50) (cid:28) r (cid:72) (cid:104) (cid:112) (cid:67) (cid:95)o (cid:28) (cid:88) (cid:27) (cid:46) (cid:83) w(cid:65) (cid:28) (cid:28) (cid:76) (cid:120) (cid:98) (cid:104) (cid:45) (cid:120) ) (cid:28) (cid:33) (cid:28) (cid:77) . (cid:77) (cid:27) (cid:66)(cid:88) (cid:47) (cid:27) (cid:97) T(cid:27) (cid:104) (cid:50) (cid:28) (cid:65) (cid:59) (cid:45) (cid:77) (cid:75) h(cid:107) (cid:75) (cid:50) (cid:121) (cid:81) (cid:77) e(cid:107) (cid:118) (cid:105) (cid:82) (cid:66) (cid:88) (cid:77) (cid:42) (cid:59) p (cid:63) (cid:105) (cid:28) (cid:66) o (cid:70) (cid:75) (cid:96)(cid:28) (cid:50) i (cid:35) (cid:98) n (cid:81) (cid:50) (cid:96) (cid:96) (cid:105) (cid:66) t (cid:118) (cid:50) (cid:88) - (cid:98)(cid:44) w (cid:54) (cid:27) (cid:66)(cid:59)(cid:63) i (cid:105) s (cid:66)(cid:77) e (cid:59) (cid:40)(cid:106)(cid:41) (cid:28)(cid:77)(cid:98) (cid:83) a(cid:109) (cid:28) (cid:66)(cid:96)(cid:77) (cid:96) n(cid:112) (cid:105) (cid:55)(cid:50)(cid:81) (cid:63) (cid:118)o (cid:47) (cid:83) (cid:50)(cid:28)(cid:75) (cid:28) m(cid:77) (cid:105) (cid:47)(cid:66) (cid:114) (cid:43)(cid:44) (cid:28) (cid:77)a (cid:45) (cid:81)(cid:42)(cid:112) (cid:97) (cid:50)l (cid:81) (cid:63) (cid:72)(cid:112) i (cid:66)(cid:112) (cid:28)(cid:66)(cid:47) e (cid:28) (cid:84)(cid:64) (cid:75) (cid:84)(cid:82) s(cid:96)(cid:78)(cid:81) (cid:97) (cid:28)(cid:55) (cid:63) (cid:43)(cid:28) a (cid:28) (cid:63)(cid:70) (cid:96) (cid:88)(cid:50) (cid:75) r(cid:107)(cid:77) (cid:28) e(cid:121)(cid:50) (cid:45) (cid:121)(cid:114) (cid:97) (cid:107)(cid:98)(cid:88) (cid:96) m (cid:66)(cid:77)(cid:66)(cid:112)(cid:28) a (cid:98) (cid:40) r (cid:83) (cid:106)(cid:41) (cid:118) k (cid:70) (cid:98) (cid:83) (cid:72) (cid:109) e (cid:28) (cid:45) (cid:96) (cid:96) (cid:111) (cid:112) (cid:105) d (cid:50) (cid:63) (cid:66) (cid:118) (cid:77) (cid:83) (cid:50) (cid:28) (cid:50) (cid:28) b (cid:77) (cid:105) (cid:105) (cid:63) (cid:47) (cid:114) y (cid:28) (cid:77) (cid:58) (cid:45) (cid:81) (cid:109) (cid:112) (cid:40)(cid:97)(cid:106)(cid:84) (cid:50) (cid:63) r (cid:41)(cid:105) (cid:72) (cid:66) (cid:63) (cid:112) e (cid:28)(cid:98) (cid:83)(cid:28) (cid:28) (cid:109)(cid:84) (cid:28)(cid:45) (cid:75) (cid:96)(cid:84) d (cid:96) (cid:112) (cid:58)(cid:105) (cid:96)(cid:50) (cid:63) (cid:81) (cid:97) (cid:66) (cid:118)(cid:28) (cid:105) (cid:63)(cid:83)(cid:28) (cid:43) c(cid:28) (cid:28) (cid:63) (cid:77)(cid:28) (cid:77) (cid:96) (cid:88) (cid:68)(cid:105) i (cid:75) (cid:47) (cid:28)(cid:114) (cid:107) (cid:72) r (cid:28) (cid:66)(cid:28) (cid:77)(cid:121) (cid:45)(cid:45) c (cid:121)(cid:81) (cid:69) (cid:112) (cid:97) (cid:107) (cid:97)(cid:109) (cid:50)(cid:88) (cid:96) l (cid:63)(cid:75) (cid:72) (cid:66)(cid:77)(cid:66) e (cid:112) (cid:28) (cid:28) (cid:66)(cid:28) (cid:84) (cid:112) (cid:96) s (cid:75)(cid:28) (cid:84) (cid:66)(cid:45) (cid:98) (cid:96)(cid:81) (cid:74)(cid:97)(cid:83) a(cid:28) (cid:63)(cid:118) (cid:47) (cid:43) (cid:28) (cid:63) (cid:70) (cid:88) n (cid:96) (cid:88) (cid:72) (cid:97)(cid:75)(cid:45) (cid:107) (cid:63) d (cid:111)(cid:28) (cid:121) (cid:28)(cid:45) (cid:121) (cid:66) (cid:47) (cid:77)(cid:97) (cid:107) (cid:50) (cid:88) (cid:27)(cid:96) t (cid:50)(cid:66)(cid:77)(cid:105) h (cid:70) (cid:63)(cid:66)(cid:63)(cid:112)(cid:105) e (cid:28)(cid:58) (cid:28)(cid:98)(cid:96) (cid:109) (cid:45)(cid:83)(cid:84)(cid:105)(cid:118)(cid:63)(cid:70)(cid:28)(cid:72)(cid:45)(cid:45)(cid:111)(cid:58)(cid:66)(cid:66)(cid:77)(cid:105)(cid:28)(cid:50)(cid:50)(cid:77)(cid:105)(cid:68)(cid:63)(cid:28)(cid:72)(cid:66)(cid:58)(cid:69)(cid:109)(cid:109)(cid:84)(cid:75)(cid:105)(cid:63)(cid:28)(cid:28)(cid:96)(cid:45)(cid:66)(cid:45)(cid:58)(cid:74)(cid:66)(cid:105)(cid:28)(cid:47)(cid:77)(cid:88)(cid:68)(cid:97)(cid:28)(cid:63)(cid:72)(cid:66)(cid:28)(cid:69)(cid:47)(cid:109)(cid:27)(cid:75)(cid:70)(cid:28)(cid:63)(cid:96)(cid:105)(cid:66)(cid:28)(cid:45)(cid:96)(cid:74)(cid:45)(cid:47)(cid:88)(cid:97)(cid:63)(cid:28)(cid:47)(cid:27)(cid:70)(cid:63)(cid:105)(cid:28)(cid:96)(cid:45)
patter(cid:98)n(cid:109)(cid:96)-(cid:112)(cid:50)w(cid:118)(cid:28)(cid:77)i(cid:47)s(cid:77)e(cid:81)(cid:112)(cid:50)(cid:72)a(cid:28)(cid:84)n(cid:84)(cid:96)o(cid:81)(cid:28)(cid:43)m(cid:63)(cid:88)(cid:107)a(cid:121)(cid:121)(cid:107)l(cid:88)iesareinredsegments. Thewrong(cid:27)l(cid:98)(cid:66)y(cid:55)(cid:49)(cid:70)d(cid:35)(cid:28)(cid:72)e(cid:45)(cid:27)te(cid:75)(cid:66)c(cid:105)(cid:28)(cid:112)t(cid:28)e(cid:46)d(cid:28)(cid:98)(cid:45)c(cid:28)(cid:77)a(cid:47)(cid:104)s(cid:28)e(cid:77)(cid:75)s(cid:81)(cid:118)a(cid:42)(cid:63) (cid:27)r(cid:28) (cid:98)e(cid:70) (cid:66)(cid:55) (cid:96)(cid:28) (cid:49) (cid:35)b(cid:70) (cid:81) (cid:35) (cid:96)o(cid:105) (cid:28) (cid:118) (cid:72) (cid:88) (cid:45)u(cid:27) (cid:54)n(cid:75) (cid:66)(cid:59) (cid:66) (cid:63) (cid:105)d(cid:27)(cid:28) (cid:105)(cid:66) (cid:112) (cid:77)(cid:98)(cid:28)e(cid:66)(cid:59)(cid:55)(cid:46)d(cid:49)(cid:28) (cid:28) (cid:77)(cid:70)(cid:98)(cid:35)(cid:45) (cid:66)b(cid:28)(cid:77) (cid:28)(cid:72)(cid:55)(cid:45)(cid:77) (cid:81)y(cid:47) (cid:47)(cid:27)(cid:50)(cid:75)(cid:75) (cid:104)r(cid:66)(cid:28) (cid:66)(cid:105)(cid:43) (cid:77)(cid:28)e(cid:44) (cid:75)(cid:112)(cid:28)d(cid:81) (cid:42) (cid:118)(cid:46)(cid:81)(cid:112)(cid:28)(cid:42) (cid:66)b(cid:98)(cid:47) (cid:63)(cid:45)(cid:64) (cid:28) (cid:82)o(cid:28)(cid:70) (cid:78)(cid:77)(cid:96)(cid:47)(cid:28)x(cid:55) (cid:35) (cid:28)(cid:70)(cid:104)(cid:81)e(cid:50) (cid:96)(cid:28)(cid:105)(cid:77)(cid:118)s(cid:77)(cid:75)(cid:88) (cid:50).(cid:114)(cid:81)(cid:54)(cid:118)(cid:98) (cid:66)(cid:59)(cid:42)(cid:63)(cid:63)(cid:105)(cid:66)(cid:28)(cid:77)(cid:70)(cid:59)(cid:96)(cid:28)(cid:28)(cid:35)(cid:77)(cid:81)(cid:96)(cid:66)(cid:105)(cid:77)(cid:118)(cid:55)(cid:88)(cid:81)(cid:47)(cid:54)(cid:50)(cid:75)(cid:66)(cid:59)(cid:63)(cid:66)(cid:43)(cid:105)(cid:44)(cid:66)(cid:77)(cid:59)(cid:42)(cid:81)(cid:28)(cid:112)(cid:77)(cid:66)(cid:47)(cid:66)(cid:64)(cid:77)(cid:82)(cid:55)(cid:78)(cid:81)(cid:47)(cid:55)(cid:28)(cid:50)(cid:75)(cid:70)(cid:50)(cid:66)(cid:43)(cid:77)(cid:44)(cid:50)(cid:114)(cid:42)(cid:98)(cid:81)(cid:112)(cid:66)(cid:47)(cid:64)(cid:82)(cid:78)(cid:55)(cid:28)(cid:70)(cid:50)(cid:77)(cid:50)(cid:114)(cid:98)
(cid:40)(cid:106)(cid:41)(cid:83)(cid:28)(cid:96)(cid:105)(cid:63)(cid:83)(cid:28)(cid:105)(cid:114)(cid:28)(cid:45)(cid:97)(cid:63)(cid:66)(cid:112)(cid:28)(cid:75)(cid:97)(cid:63)(cid:28)(cid:96)(cid:75)(cid:28)(cid:45)(cid:97)(cid:96)(cid:66)(cid:77)(cid:66)(cid:112)(cid:28)(cid:98)(cid:83)(cid:118)(cid:70)(cid:72)(cid:45)(cid:111)(cid:66)(cid:77)(cid:50)(cid:50)(cid:105)(cid:63)(cid:58)(cid:109)(cid:84)(cid:105)(cid:63)(cid:28)(cid:45)(cid:58)(cid:66)(cid:105)(cid:28)(cid:77)(cid:68)(cid:28)(cid:72)(cid:66)(cid:69)(cid:109)(cid:75)(cid:28)(cid:96)(cid:66)(cid:45)(cid:74)(cid:47)(cid:88)(cid:97)(cid:63)(cid:28)(cid:47)(cid:27)(cid:70)(cid:63)(cid:105)(cid:28)(cid:96)(cid:45) (cid:47)(cid:28)(cid:105)(cid:28)(cid:98)(cid:50)(cid:105)(cid:88)(cid:65)(cid:77)(cid:42)(cid:80)(cid:76)(cid:97)(cid:104)(cid:95)(cid:27)(cid:65)(cid:76)(cid:104)(cid:33)(cid:27)(cid:27)(cid:27)(cid:65)(cid:45)(cid:107)(cid:121)(cid:107)(cid:82)(cid:88)
(cid:47)(cid:28)(cid:105)(cid:28)(cid:98)(cid:50)(cid:105)(cid:88)(cid:65)(cid:77)(cid:42)(cid:80)(cid:76)(cid:97)(cid:47)(cid:104)(cid:28)(cid:95)(cid:105)(cid:28)(cid:27)(cid:98)(cid:50)(cid:65)(cid:76)(cid:105)(cid:88)(cid:104)(cid:65)(cid:33)(cid:77)(cid:27)(cid:42)(cid:27)(cid:80)(cid:27)(cid:76)(cid:65)(cid:97)(cid:45)(cid:104)(cid:107)(cid:95)(cid:121)(cid:107)(cid:27)(cid:82)(cid:65)(cid:88)(cid:76)(cid:104)(cid:33)(cid:27)(cid:27)(cid:27)(cid:65)(cid:45)(cid:107)(cid:121)(cid:107)(cid:82)(cid:88)
(cid:27)(cid:98)(cid:66)(cid:55)(cid:49)(cid:70)(cid:35)(cid:28)(cid:72)(cid:45)(cid:27)(cid:75)(cid:66)(cid:105)(cid:28)(cid:112)(cid:28)(cid:46)(cid:28)(cid:98)(cid:45)(cid:28)(cid:77)(cid:47)(cid:104)(cid:28)(cid:77)(cid:75)(cid:81)(cid:118)(cid:42)(cid:63)(cid:28)(cid:70)(cid:96)(cid:28)(cid:35)(cid:81)(cid:96)(cid:105)(cid:118)(cid:88) (cid:54)(cid:66)(cid:59)(cid:63)(cid:105)(cid:66)(cid:77)(cid:59)(cid:28)(cid:77)(cid:66)(cid:77)(cid:55)(cid:81)(cid:47)(cid:50)(cid:75)(cid:66)(cid:43)(cid:44)(cid:42)(cid:81)(cid:112)(cid:66)(cid:47)(cid:64)(cid:82)(cid:78)(cid:55)(cid:28)(cid:70)(cid:50)(cid:77)(cid:50)(cid:114)(cid:98)
Anom(cid:47)(cid:28)a(cid:105)(cid:28)(cid:98)l(cid:50)(cid:105)y(cid:88)(cid:65)(cid:77)c(cid:42)(cid:80)r(cid:76)i(cid:97)t(cid:104)e(cid:95)(cid:27)r(cid:65)(cid:76)i(cid:104)o(cid:33)n(cid:27)(cid:27)(cid:27)v(cid:65)(cid:45)(cid:107)i(cid:121)s(cid:107)(cid:82)u(cid:88) alization Togetmoreintuitivecasesabouthowassociation-basedcrite-
rionworks,weprovidesomevisualizationinFigure5andexplorethecriterionperformanceunder
different types of anomalies, where the taxonomy is from Lai et al. (2021). We can find that our
proposedassociation-basedcriterionismoredistinguishableingeneral.Concretely,theassociation-
basedcriterioncanobtaintheconsistentsmallervaluesforthenormalpart,whichisquitecontrasting
8
(cid:57)
(cid:57) (cid:57) (cid:57)
(cid:57) (cid:57)
(cid:57) (cid:57) (cid:57)
(cid:57)

PublishedasaconferencepaperatICLR2022
inpoint-contextualandpattern-seasonalcases(Figure5). Incontrast,thejittercurvesoftherecon-
struction criterion make the detection process confused and fail in the aforementioned two cases.
This verifies that our criterion can highlight the anomalies and provide distinct values for normal
andabnormalpoints,makingthedetectionpreciseandreducingthefalse-positiverate.
-0.3 -0.3
|     | 4 4       |     | 1.5 1.5   |     | 11..55 1.5    |     | 1.5 1.5   |     | -0.3                       |     |
| --- | --------- | --- | --------- | --- | ------------- | --- | --------- | --- | -------------------------- | --- |
|     |           |     |           |     | 1             |     | 1         |     | -0.4 -0.4 -0.4             |     |
|     | 3 3       |     | 1         |     | 1             |     |           |     | -0.5 -0.5                  |     |
|     | Input     |     | 0.5 0.5   |     | 00 0.5 ..55   |     | 0.5 0.5   |     | -0.5                       |     |
|     | eulav 2 2 |     |           |     | eulav eulaV   |     | eulav     |     | eulav eulaV -0.6 -0.6 -0.6 |     |
|     | Time      |     | eulav 0   |     | 0 0           |     | 0         |     |                            |     |
|     | Series1 1 |     |           |     |               |     |           |     | -0.7 - -0.7 0 . 7          |     |
|     | 0         |     | -0.5 -0.5 |     | -0-0..55 -0.5 |     | -0.5 -0.5 |     | -0.8 - -0.8 0 . 8          |     |
|     | 0         |     | -1        |     | -1 -1         |     | -1        |     |                            |     |
|     | -1 -1     |     |           |     |               |     |           |     | -0.9 -0.9 -0.9             |     |
|     |           |     | -1.5 -1.5 |     | -1-1..55 -1.5 |     | -1.5 -1.5 |     | -1 -10                     |     |
0 0 20 20 40 40 60 60 80 80 100 100 0 0 20 20 40 40 60 60 80 80 100 100 0 0 0 20 20 20 40 40 40Time60 60 60 80 80 80 100 100 100 0 0 20 20 40 40 60 60 80 80 100 100 0 0 20 20 20 40Time60 40 40 60 60 80 80 80 100 100 100
|     |           | length Time |           | length Time |               | length Time | 2 .1    | length Time |               | length Time |
| --- | --------- | ----------- | --------- | ----------- | ------------- | ----------- | ------- | ----------- | ------------- | ----------- |
|     |           |             | 2 2.3 . 3 |             | 2 2.2 . 2     |             | 2.1     |             | 2 2.3 . 3     |             |
|     | 2 2.2 . 2 |             | 2 2.2 . 2 |             |               |             |         |             |               |             |
|     | 2 2.1 . 1 |             |           |             | 2 2.1 . 1     |             | 2 2     |             | 2 2.2 . 2     |             |
|     |           |             | 2 2.1 . 1 |             | 2 2           |             |         |             |               |             |
|     | eulav 2 2 |             |           |             |               |             | 1.9 1.9 |             | eulav 2.1 2.1 |             |
|     | !!        |             | eulav 2 2 |             | eulav 1.9 1.9 |             | eulav   |             |               |             |
|     | 1.9 1.9   |             | 1.9 1.9   |             | 1.8 1.8       |             |         |             | 2 2           |             |
1.8 1.8
|     | 1.8 1.8 |     | 1.8 1.8 |     | 1.7 1.7   |     |         |     | 1.9 1.9 |     |
| --- | ------- | --- | ------- | --- | --------- | --- | ------- | --- | ------- | --- |
|     |         |     |         |     | 1 1.6 . 6 |     | 1.7 1.7 |     |         |     |
|     | 1.7 1.7 |     | 1.7 1.7 |     | 1 . 50    |     |         |     |         |     |
0 0 20 20 40 40 60 60 80 80 100 100 0 0 20 20 40 40 60 60 80 80 100 100 1.50 20 20 40 40 60 60 80 80 100 100 0 0 20 20 40 40 60 60 80 80 100 100 1.80 1.8 0 20 20 40 40 60 60 80 80 100 100
|     |     | length Time |     | length Time |     | length Time |     | length Time |     | length Time |
| --- | --- | ----------- | --- | ----------- | --- | ----------- | --- | ----------- | --- | ----------- |
(cid:1153)a(cid:1154)Point-Global (cid:1153)b(cid:1154)Point-Contextual (cid:1153)c(cid:1154)Pattern-Shapelet (cid:1153)d(cid:1154)Pattern-Seasonal (cid:1153)e(cid:1154)Pattern-Trend
Figure6: Learnedscaleparameterσfordifferenttypesofanomalies(highlightinred).
Prior-associationvisualization Duringtheminimaxoptimization,theprior-associationislearned
to get close to the series-association. Thus, the learned σ can reflect the adjacent-concentrating
degreeoftimeseries. AsshowninFigure6,wefindthatσchangestoadapttovariousdatapatterns
oftimeseries. Especially,theprior-associationofanomaliesgenerallyhasasmallerσ thannormal
timepoints,whichmatchesouradjacent-concentrationinductivebiasofanomalies.
Optimizationstrategyanalysis Onlywiththereconstructionloss,theabnormalandnormaltime
points present similar performance in the association weights to adjacent time points, correspond-
ingtoacontrastvalueclosedto1(Table3). Maximizingtheassociationdiscrepancywillforcethe
series-associationstopaymoreattentiontothenon-adjacentarea.However,toobtainabetterrecon-
struction,theanomalieshavetomaintainmuchlargeradjacentassociationweightsthannormaltime
points,correspondingtoalargercontrastvalue.Butdirectmaximizationwillcausetheoptimization
problemofGaussiankernel,cannotstronglyamplifythedifferencebetweennormalandabnormal
timepointsasexpected(SMD:1.15 1.27).Theminimaxstrategyoptimizestheprior-associationto
→
provideastrongerconstrainttoseries-association. Thus,theminimaxstrategyobtainsmoredistin-
guishablecontrastvaluesthandirectmaximization(SMD:1.27 2.39)andtherebyperformsbetter.
→
Table3:ThestatisticalresultsofadjacentassociationweightsforAbnormalandNormaltimepoints
respectively. Recon,MaxandMinimaxrepresenttheassociationlearningprocessthatissupervised
by reconstruction loss, direct maximization and minimax strategy respectively. A higher contrast
value(Abnormal)indicatesastrongerdistinguishabilitybetweennormalandabnormaltimepoints.
Normal
|     | Dataset |     | SMD |     | MSL | SMAP |     | SWaT |     | PSM |
| --- | ------- | --- | --- | --- | --- | ---- | --- | ---- | --- | --- |
Optimization ReconMaxOursReconMaxOursReconMaxOursReconMaxOursReconMaxOurs
Abnormal(%) 1.08 0.95 0.86 1.01 0.65 0.35 1.29 1.18 0.70 1.27 0.89 0.37 1.02 0.56 0.29
Normal(%) 0.94 0.75 0.36 1.00 0.59 0.22 1.23 1.09 0.49 1.18 0.78 0.21 0.99 0.54 0.11
Contrast(Abnormal) 1.15 1.27 2.39 1.01 1.10 1.59 1.05 1.08 1.43 1.08 1.14 1.76 1.03 1.04 2.64
Normal
|     | 5 CONCLUSION |     | AND | FUTURE | WORK |     |     |     |     |     |
| --- | ------------ | --- | --- | ------ | ---- | --- | --- | --- | --- | --- |
Thispaperstudiestheunsupervisedtimeseriesanomalydetectionproblem. Unlikepreviousmeth-
ods,welearnthemoreinformativetime-pointassociationsbyTransformers. Basedonthekeyob-
servationofassociationdiscrepancy,weproposetheAnomalyTransformer,includinganAnomaly-
Attentionwiththetwo-branchstructuretoembodytheassociationdiscrepancy. Aminimaxstrategy
isadoptedtofurtheramplifythedifferencebetweennormalandabnormaltimepoints. Byintroduc-
ingtheassociationdiscrepancy,weproposetheassociation-basedcriterion,whichmakestherecon-
structionperformanceandassociationdiscrepancycollaborate. AnomalyTransformerachievesthe
state-of-the-art results on an exhaustive set of empirical studies. Future work includes theoretical
studyofAnomolyTransformerinlightofclassicanalysisforautoregressionandstatespacemodels.
9

PublishedasaconferencepaperatICLR2022
ACKNOWLEDGMENTS
ThisworkwassupportedbytheNationalMegaprojectforNewGenerationAI(2020AAA0109201),
National Natural Science Foundation of China (62022050 and 62021002), Beijing Nova Program
(Z201100006820041),andBNRistInnovationFund(BNR2021RC01002).
Ahmed Abdulaal, Zhuanghua Liu, and Tomer Lancewicki. Practical approach to asynchronous
multivariatetimeseriesanomalydetectionandlocalization. KDD,2021.
Ryan Prescott Adams and David J. C. MacKay. Bayesian online changepoint detection. arXiv
preprintarXiv:0710.3742,2007.
O.AndersonandM.Kendall. Time-series.2ndedn. J.R.Stat.Soc.(SeriesD),1976.
PaulBoniolandThemisPalpanas. Series2graph: Graph-basedsubsequenceanomalydetectionfor
timeseries. Proc.VLDBEndow.,2020.
Markus M. Breunig, Hans-Peter Kriegel, Raymond T. Ng, and Jo¨rg Sander. LOF: identifying
density-basedlocaloutliers. InSIGMOD,2000.
Tom Brown, Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared D Kaplan, Prafulla Dhariwal,
Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, Sandhini Agarwal, Ariel
Herbert-Voss,GretchenKrueger,TomHenighan,RewonChild,AdityaRamesh,DanielZiegler,
JeffreyWu,ClemensWinter,ChrisHesse,MarkChen,EricSigler,MateuszLitwin,ScottGray,
BenjaminChess,JackClark,ChristopherBerner,SamMcCandlish,AlecRadford,IlyaSutskever,
andDarioAmodei. Languagemodelsarefew-shotlearners. InNeurIPS,2020.
Zekai Chen, Dingshuo Chen, Zixuan Yuan, Xiuzhen Cheng, and Xiao Zhang. Learning graph
structures with transformer for multivariate time series anomaly detection in iot. ArXiv,
abs/2104.03466,2021.
Haibin Cheng, Pang-Ning Tan, Christopher Potter, and Steven A. Klooster. A robust graph-based
algorithmfordetectionandcharacterizationofanomaliesinnoisymultivariatetimeseries.ICDM
Workshops,2008.
HaibinCheng, Pang-NingTan, ChristopherPotter, andStevenA.Klooster. Detectionandcharac-
terizationofanomaliesinmultivariatetimeseries. InSDM,2009.
ShohrehDeldari,DanielV.Smith,HaoXue,andFloraD.Salim.Timeserieschangepointdetection
withself-supervisedcontrastivepredictivecoding. InWWW,2021.
Ailin Deng and Bryan Hooi. Graph neural network-based anomaly detection in multivariate time
series. AAAI,2021.
Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova. Bert: Pre-training of deep
bidirectionaltransformersforlanguageunderstanding. InNAACL,2019.
AlexeyDosovitskiy,LucasBeyer,AlexanderKolesnikov,DirkWeissenborn,XiaohuaZhai,Thomas
Unterthiner,MostafaDehghani,MatthiasMinderer,GeorgHeigold,SylvainGelly,JakobUszko-
reit,andNeilHoulsby. Animageisworth16x16words: Transformersforimagerecognitionat
scale. InICLR,2021.
I. Goodfellow, Jean Pouget-Abadie, Mehdi Mirza, Bing Xu, David Warde-Farley, Sherjil Ozair,
AaronC.Courville,andYoshuaBengio. Generativeadversarialnets. InNeurIPS,2014.
Cheng-Zhi Anna Huang, Ashish Vaswani, Jakob Uszkoreit, Ian Simon, Curtis Hawthorne, Noam
Shazeer, Andrew M. Dai, Matthew D. Hoffman, Monica Dinculescu, and Douglas Eck. Music
transformer. InICLR,2019.
Kyle Hundman, Valentino Constantinou, Christopher Laporte, Ian Colwell, and Tom So¨derstro¨m.
Detectingspacecraftanomaliesusinglstmsandnonparametricdynamicthresholding.KDD,2018.
10

PublishedasaconferencepaperatICLR2022
EamonnJ.Keogh,TaposhRoy,NaikU,andAgrawalA.Multi-datasettime-seriesanomalydetection
competition,CompetitionofInternationalConferenceonKnowledgeDiscovery&DataMining
2021. URLhttps://compete.hexagon-ml.com/practice/competition/39/.
DiederikP.KingmaandJimmyBa. Adam: Amethodforstochasticoptimization. InICLR,2015.
NikitaKitaev,LukaszKaiser,andAnselmLevskaya. Reformer: Theefficienttransformer. InICLR,
2020.
Kwei-HerngLai,D.Zha,JunjieXu,andYueZhao. Revisitingtimeseriesoutlierdetection: Defini-
tionsandbenchmarks. InNeurIPSDatasetandBenchmarkTrack,2021.
DanLi,DachengChen,LeiShi,BaihongJin,JonathanGoh,andSee-KiongNg. Mad-gan: Multi-
variate anomaly detection fortime series data with generative adversarial networks. In ICANN,
2019a.
Shiyang Li, Xiaoyong Jin, Yao Xuan, Xiyou Zhou, Wenhu Chen, Yu-Xiang Wang, and Xifeng
Yan. Enhancing the locality and breaking the memory bottleneck of transformer on time series
forecasting. InNeurIPS,2019b.
ZhihanLi,YoujianZhao,JiaqiHan,YaSu,RuiJiao,XidaoWen,andDanPei.Multivariatetimese-
riesanomalydetectionandinterpretationusinghierarchicalinter-metricandtemporalembedding.
KDD,2021.
F.Liu,K.Ting,andZ.Zhou. Isolationforest. ICDM,2008.
Ze Liu, Yutong Lin, Yue Cao, Han Hu, Yixuan Wei, Zheng Zhang, Stephen Ching-Feng Lin, and
BainingGuo. Swintransformer: Hierarchicalvisiontransformerusingshiftedwindows. ICCV,
2021.
AdityaP.MathurandNilsOleTippenhauer.Swat:awatertreatmenttestbedforresearchandtraining
onICSsecurity. InCySWATER,2016.
RadfordM.Neal. Patternrecognitionandmachinelearning. Technometrics,2007.
Daehyung Park, Yuuna Hoshi, and Charles C. Kemp. A multimodal anomaly detector for robot-
assistedfeedingusinganlstm-basedvariationalautoencoder. RA-L,2018.
Adam Paszke, S. Gross, Francisco Massa, A. Lerer, James Bradbury, Gregory Chanan, Trevor
Killeen,Z.Lin,N.Gimelshein,L.Antiga,AlbanDesmaison,AndreasKo¨pf,EdwardYang,Zach
DeVito, Martin Raison, Alykhan Tejani, Sasank Chilamkurthy, Benoit Steiner, Lu Fang, Junjie
Bai,andSoumithChintala.Pytorch:Animperativestyle,high-performancedeeplearninglibrary.
InNeurIPS,2019.
MathiasPerslev,MichaelJensen,SuneDarkner,PoulJørgenJennum,andChristianIgel. U-time:
Afullyconvolutionalnetworkfortimeseriessegmentationappliedtosleepstaging. InNeurIPS.
2019.
Lukas Ruff, Nico Go¨rnitz, Lucas Deecke, Shoaib Ahmed Siddiqui, Robert A. Vandermeulen,
Alexander Binder, Emmanuel Mu¨ller, and M. Kloft. Deep one-class classification. In ICML,
2018.
T.Schlegl,PhilippSeebo¨ck,S.Waldstein,G.Langs,andU.Schmidt-Erfurth. f-anogan: Fastunsu-
pervisedanomalydetectionwithgenerativeadversarialnetworks. Med.ImageAnal.,2019.
B. Scho¨lkopf, John C. Platt, J. Shawe-Taylor, Alex Smola, and R. C. Williamson. Estimating the
supportofahigh-dimensionaldistribution. NeuralComput.,2001.
Lifeng Shen, Zhuocong Li, and James T. Kwok. Timeseries anomaly detection using temporal
hierarchicalone-classnetwork. InHugoLarochelle,Marc’AurelioRanzato,RaiaHadsell,Maria-
FlorinaBalcan,andHsuan-TienLin(eds.),NeurIPS,2020.
YoujinShin,SangyupLee,ShahrozTariq,MyeongShinLee,OkchulJung,DaewonChung,andSi-
monS.Woo. Itad: Integrativetensor-basedanomalydetectionsystemforreducingfalsepositives
ofsatellitesystems. CIKM,2020.
11

PublishedasaconferencepaperatICLR2022
Ya Su, Y. Zhao, Chenhao Niu, Rong Liu, W. Sun, and Dan Pei. Robust anomaly detection for
| multivariatetimeseriesthroughstochasticrecurrentneuralnetwork. |     |     |     | KDD,2019. |
| -------------------------------------------------------------- | --- | --- | --- | --------- |
JianTang,ZhixiangChen,A.Fu,andD.Cheung. Enhancingeffectivenessofoutlierdetectionsfor
| lowdensitypatterns. | InPAKDD,2002. |     |     |     |
| ------------------- | ------------- | --- | --- | --- |
Shahroz Tariq, Sangyup Lee, Youjin Shin, Myeong Shin Lee, Okchul Jung, Daewon Chung, and
SimonS.Woo. Detectinganomaliesinspaceusingmultivariateconvolutionallstmwithmixtures
| ofprobabilisticpca. | KDD,2019.                     |     |                   |     |
| ------------------- | ----------------------------- | --- | ----------------- | --- |
| D.TaxandR.Duin.     | Supportvectordatadescription. |     | Mach.Learn.,2004. |     |
Robert Tibshirani, Guenther Walther, and Trevor Hastie. Estimating the number of clusters in a
| datasetviathegapstatistic. | J.R.Stat.Soc.(SeriesB),2001. |     |     |     |
| -------------------------- | ---------------------------- | --- | --- | --- |
Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N Gomez,
| ŁukaszKaiser,andIlliaPolosukhin. |     | Attentionisallyouneed. |     | InNeurIPS,2017. |
| -------------------------------- | --- | ---------------------- | --- | --------------- |
Haixu Wu, Jiehui Xu, Jianmin Wang, and Mingsheng Long. Autoformer: Decomposition trans-
| formerswithAuto-Correlationforlong-termseriesforecasting. |     |     |     | InNeurIPS,2021. |
| --------------------------------------------------------- | --- | --- | --- | --------------- |
Haowen Xu, Wenxiao Chen, N. Zhao, Zeyan Li, Jiahao Bu, Zhihan Li, Y. Liu, Y. Zhao, Dan Pei,
YangFeng,JianJhenChen,ZhaogangWang,andHonglinQiao.Unsupervisedanomalydetection
| viavariationalauto-encoderforseasonalkpisinwebapplications. |     |     |     | WWW,2018. |
| ----------------------------------------------------------- | --- | --- | --- | --------- |
TakehisaYairi,NaoyaTakeishi,TetsuoOda,YutaNakajima,NaokiNishimura,andNoboruTakata.
A data-driven health monitoring method for satellite housekeeping data based on probabilistic
| clusteringanddimensionalityreduction. |     | IEEETrans.Aerosp.Electron.Syst.,2017. |     |     |
| ------------------------------------- | --- | ------------------------------------- | --- | --- |
HangZhao, YujingWang, JuanyongDuan, CongruiHuang, DefuCao, YunhaiTong, BixiongXu,
JingBai,JieTong,andQiZhang. Multivariatetime-seriesanomalydetectionviagraphattention
| network. ICDM,2020. |     |     |     |     |
| ------------------- | --- | --- | --- | --- |
Bin Zhou, Shenghua Liu, Bryan Hooi, Xueqi Cheng, and Jing Ye. Beatgan: Anomalous rhythm
| detectionusingadversariallygeneratedtimeseries. |     |     | InIJCAI,2019. |     |
| ----------------------------------------------- | --- | --- | ------------- | --- |
HaoyiZhou,ShanghangZhang,JieqiPeng,ShuaiZhang,JianxinLi,HuiXiong,andWancaiZhang.
Informer:Beyondefficienttransformerforlongsequencetime-seriesforecasting. InAAAI,2021.
BoZong,QiSong,MartinRenqiangMin,WeiCheng,CristianLumezanu,Dae-kiCho,andHaifeng
Chen. Deepautoencodinggaussianmixturemodelforunsupervisedanomalydetection. InICLR,
2018.
12

PublishedasaconferencepaperatICLR2022
A PARAMETER SENSITIVITY
We set the window size as 100 throughout the main text, which considers the temporal informa-
tion,memoryandcomputationefficiency. Andwesetthelossweightλbasedontheconvergence
propertyofthetrainingcurve.
Furthermore,Figure7providesthemodelperformanceunderdifferentchoicesofthewindowsize
andthelossweight. Wepresentthatourmodelisstabletothewindowsizeoverextensivedatasets
(Figure7left). Notethatalargerwindowsizeindicatesalargermemorycostandasmallersliding
number. Especially, only considering the performance, its relationship to the window size can be
determinedbythedatapattern. Forexample,ourmodelperformsbetterwhenthewindowsizeis50
fortheSMDdataset.Besides,weadoptthelossweightλinEquation5totradeoffthereconstruction
loss and the association part. We find that λ is stable and easy to tune in the range of 2 to 4. The
aboveresultsverifythesensitivityofourmodel,whichisessentialforapplications.
100
95
90
85
80
75
70
65
1 2 3 4 5 6 7
factor
erocs-f
100
95
SMD
90 MSL
SMAP
SWaT
PSM
85
1 2 3 4 5 6
factor
erocs-f
100
95
90
85
1 2 3 4 5 6 factor
SMD
MSL
SMAP
SWaT
PSM
erocs-f
100
95
SSMMDD
90 MMSSLL
SSMMAAPP
SSWWaaTT
PPSSMM
85
erocs-F
100
98
96
94
92
90
50 100 150 200 250 300 1 2 3 4 5 6 factor Window Size
erocs-f
100
98
SSMMDD 96 MMSSLL
SSMMAAPP SSWWaaTT
94 PPSSMM
92
90
erocs-F
100 100
98
95 96
94
90 92
90
85
1 2 3 4 5 6 !
)%(
erocs-1F
)%(
erocs-1F
50 100 150 200 250 300 1 2 3 4 5 6 Window Size Loss Weight
100 100
95
85
80
90
75
70
85 65
)%(
erocs-1F
)%(
erocs-1F
95
90
SMD
SMD MSL
MSL SMAP
SMAP SWaT
SWaT PSM
PSM
50 100 150 200 250 300 0 1 2 3 4 5 6
Window Size Loss Weight
Figure7: Parametersensitivityforslidingwindowsize(left)andlossweightλ(right). Themodel
withλ=0stilladoptstheassociation-basedcriterionbutonlysupervisedbyreconstructionloss.
B IMPLEMENTATION DETAILS
Wepresentthepseudo-codeofAnomaly-AttentioninAlgorithm1.
Algorithm1Anomaly-AttentionMechanism(multi-headversion).
(cid:16) (cid:17)
Input: RN×dmodel: input; = (j i)2 RN×N: relativedistancematrix
X ∈ D − i,j∈{1,···,N} ∈
Layerparams: MLP : linearprojectorforinput;MLP : linearprojectorforoutput
input output
(cid:16) (cid:17)
1: , , ,σ =Split MLP input ( ),dim=1 (cid:46) , , RN×dmodel,σ RN×h
Q K V X Q K V ∈ ∈
2: for( m , m , m ,σ m )in( , , ,σ): (cid:46) m , m , m RN×dm h odel,σ m RN×1
Q K V Q K V Q K V ∈ ∈
3: forσ =Broadcast(σ ,dim=1) (cid:46)σ RN×N
m m m
(cid:16) (cid:17) ∈
4: for = √ 1 exp D (cid:46) RN×N
P m 2πσm − 2σ (cid:16)m 2 (cid:17) P m ∈
5: for = /Broadcast Sum( ,dim=1) (cid:46)Rescaled RN×N
m m m m
P P P P ∈
(cid:32) (cid:33)
(cid:113)
6: for =Softmax h T (cid:46) RN×N
S m dmodelQ m Km S m ∈
7: for Z (cid:98)m = S m V m(cid:16) (cid:17) (cid:46) Z (cid:98)m ∈ RN×dm h odel
8: (cid:98)=MLP output Concat([(cid:98)1 , , (cid:98)h ],dim=1) (cid:46) (cid:98) RN×dmodel
Z Z ··· Z Z ∈
9: Return (cid:98) (cid:46)Keepthe m and m ,m=1, ,h
Z P S ···
C MORE SHOWCASES
To obtain an intuitive comparison of main results (Table 1), we visualize the criterion of various
baselines.AnomalyTransformercanpresentthemostdistinguishablecriterion(Figure8).Besides,
13

PublishedasaconferencepaperatICLR2022
forthereal-worlddataset,AnomalyTransformercanalsodetecttheanomaliescorrectly. Especially
fortheSWaTdataset(Figure9(d)),ourmodelcandetecttheanomaliesintheearlystage,whichis
meaningfulforreal-worldapplications,suchastheearlywarningofmalfunctions.
Point-Global Point-Contextual Pattern-Shapelet Pattern-Seasonal Pattern-Trend
-0.3 -0.3 -0.3
| 4 4 4                   |     | 1.5 1.5 1.5    |     | 11..55 1.5    |     | 1.5 1.5 1.5    |     |                       |     |
| ----------------------- | --- | -------------- | --- | ------------- | --- | -------------- | --- | --------------------- | --- |
|                         |     | 1 1            |     | 1 1           |     | 1 1            |     | -0.4 -0.4             |     |
| seireS emiT 3 3 3       |     |                |     |               |     |                |     | -0.5 -0.5 -0.5        |     |
|                         |     | 0.5 0.5 0.5    |     | 00..55 0.5    |     | 0.5 0.5 0.5    |     |                       |     |
| tupnI eulav eulaV 2 2 2 |     | eulav eulaV    |     | eulav eulaV   |     | eulav eulaV    |     | eulav eulaV -0.6 -0.6 |     |
| 1 1 1                   |     | 0 0            |     | 0 0           |     | 0 0            |     | -0.7 -0.7             |     |
|                         |     | -0.5 -0.5 -0.5 |     | -0-0..55 -0.5 |     | -0.5 -0.5 -0.5 |     | -0.7                  |     |
| 0 0 0                   |     |                |     |               |     |                |     | -0.8 -0.8             |     |
|                         |     | -1 -1          |     | -1 -1         |     | -1 -1          |     |                       |     |
| -1 -1 -1                |     |                |     |               |     |                |     | -0.9 -0.9 -0.9        |     |
|                         |     | -1.5 -1.5 -1.5 |     | -1-1..55 -1.5 |     | -1.5 -1.5 -1.5 |     | -1 -10                |     |
0 0 0 20 20 20 40 40 40 length Time Time 60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40 length Time Time 60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40Time60 length Time 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40Time60 40 40 length Time 60 60 80 80 80 100 100 100 0 0 20 20 20 40Time60 40 40 length Time 60 60 80 80 80 100 100 100
| 6       |     |                   |     | 3.5 3.5     |     | 1.5 1.5     |     | 1.5 1.5 1.5 |     |
| ------- | --- | ----------------- | --- | ----------- | --- | ----------- | --- | ----------- | --- |
| 6 6     |     | 2.5 2.5           |     |             |     | 1.5         |     |             |     |
| 5 5     |     | 2.5               |     | 3 3 3       |     |             |     |             |     |
| NAGtaeB |     | 2 2               |     | 2.5 2.5     |     | 1 1         |     |             |     |
| 4 4 4   |     |                   |     |             |     | 1           |     | 1 1 1       |     |
| eulav   |     | eulav 1.5 1.5 1.5 |     | eulav 2 2 2 |     | eulav       |     | eulav       |     |
| 3 3     |     |                   |     | 1.5 1.5     |     |             |     |             |     |
| 2 2 2   |     | 1 1               |     |             |     | 0.5 0.5 0.5 |     | 0.5 0.5 0.5 |     |
1 1 1
| 1 1 |     | 0.5 0.5 0.5 |     | 0.5 0.5 |     |     |     |     |     |
| --- | --- | ----------- | --- | ------- | --- | --- | --- | --- | --- |
0 0 0
| 0 0 0 |     | 0 0 |     | 0 0 0 |     |     |     | 0 0 0 |     |
| ----- | --- | --- | --- | ----- | --- | --- | --- | ----- | --- |
0 0 0 20 20 20 40 40 40Time60 length 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40Time60 40 length 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40 60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40 length Time 60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40Time60 60 60 80 80 80 100 100 100
0.042 0.042 Time Time 0.04003 length Time Time Time length Time
| 0.042     |     | 0.054 |     | 0.04003               |     | 0.03596 0.03596 0.037 |     | 0.062 0.063 0.062 |     |
| --------- | --- | ----- | --- | --------------------- | --- | --------------------- | --- | ----------------- | --- |
| DDVS-peeD |     |       |     | 0.04002 0.04002 0.041 |     | 0.03594 0.03594       |     |                   |     |
0.0415 0.0415
|             |     |       |     | 0.04001 0.04001       |     | 0.03592 0.03592     |     | 0.0615 0.062 |     |
| ----------- | --- | ----- | --- | --------------------- | --- | ------------------- | --- | ------------ | --- |
| eulav 0.041 |     |       |     |                       |     | eulav               |     | 0.0615       |     |
| 0.041 0.041 |     | 0.053 |     | eulav 0.040 0.04 0.04 |     | 0.0359 0.0359 0.036 |     | eulav        |     |
0.03588 0.03588
| 0.0405 0.0405 |     |     |     | 0.03999 0.03999 |     |     |     | 0.061 0.061 0.061 |     |
| ------------- | --- | --- | --- | --------------- | --- | --- | --- | ----------------- | --- |
0.03586 0.03586
|                |     |       |     | 0.03998 0.03998 0.039 |     |                       |     |      |     |
| -------------- | --- | ----- | --- | --------------------- | --- | --------------------- | --- | ---- | --- |
| 0.04 0.04 0.04 |     | 0.052 |     | 0.03997 0.03997       |     | 0.03584 0.03584 0.035 |     | 0.06 |     |
0 0 0 20 20 20 40 40 40Time60 60 60 80 80 80 100 100 100 0 20 40 60 80 100 0 0 0 20 20 20 40 40 40Time60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40 60 60 60 80 80 80 1000.06050 100 100 0.0605 0 0 20 20 20 40 40 40Time60 60 60 80 80 80 100 100 100
|          | length Time |     | Time |     | length Time |     | length Time Time |     | length Time |
| -------- | ----------- | --- | ---- | --- | ----------- | --- | ---------------- | --- | ----------- |
| 10 10 10 |             | 1.6 |      |     |             | 2   |                  | 0.8 |             |
1.6
| EAV-MTSL 8 8 8 |     | 1.2 |     |     |     |     |     | 0.6 |     |
| -------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
1.2
6 6 6
| eulav |     | 0.8 |     | 0.8 |     | 1   |     | 0.4 |     |
| ----- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
4 4 4
|     |     | 0.4 |     | 0.4 |     |     |     | 0.2 |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
2 2 2
|     |     |     |     | 0   |     | 0   |     | 0   |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
0 0 0 0 20 40 60 80 100 0 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100
0 0 20 20 40 40Time60 length Time 60 80 80 100 100 Time Time Time Time
| 0.3 0.3                     |     | (cid:1)10-3 |     | 0.15 0.15              |     | 0.08 0.08 0.08                   |     | 0.08 0.08                        |     |
| --------------------------- | --- | ----------- | --- | ---------------------- | --- | -------------------------------- | --- | -------------------------------- | --- |
| 0.3                         |     | 0.025       |     | 0.15                   |     |                                  |     | 0.08                             |     |
| 0.25 0.25                   |     | 16          |     |                        |     |                                  |     |                                  |     |
| ylamonA remrofsnarT         |     | 14          |     |                        |     | 0.06 0.06 0.06                   |     | 0.06 0.06 0.06                   |     |
| ssoLe ulalanviF 0.2 0.2 0.2 |     | 0.015 12    |     | ssoL laniF 0.1 0.1 0.1 |     | ssoL laniF                       |     | ssoL laniF                       |     |
|                             |     | eulav 10    |     | eulav                  |     | eulav 0.04 0.04                  |     | eulav 0.04 0.04                  |     |
| 0.15 0.15                   |     | 8           |     |                        |     | (cid:19)(cid:17)(cid:19)(cid:23) |     | (cid:19)(cid:17)(cid:19)(cid:23) |     |
| 0.1 0.1 0.1                 |     | 6           |     | 0.05 0.05 0.05         |     |                                  |     |                                  |     |
|                             |     | 0.005       |     |                        |     | 0.02 0.02 0.02                   |     | 0.02 0.02 0.02                   |     |
| 0.05 0.05                   |     | 4           |     |                        |     |                                  |     |                                  |     |
|                             |     | 2           |     | 0 0                    |     | 0 0 0                            |     |                                  |     |
| 0 0 0                       |     | 0           |     | 0                      |     |                                  |     | 0 0 0                            |     |
0 0 0 20 20 20 40Time60 40 40 length Time 60 60 80 80 80 100 100 100 0 0 20 20 40 40 Time 60 60 80 80 100 100 0 0 0 20 20 20 40 40 40 length TTiimmee Time 60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40 Time Time 60 60 60 80 80 80 100 100 100 0 0 0 20 20 20 40 40 40 length Time Time 60 60 60 80 80 80 100 100 100
|     |     |     | length |     |     |     | length |     |     |
| --- | --- | --- | ------ | --- | --- | --- | ------ | --- | --- |
Figure8: VisualizationoflearnedcriterionfortheNeurIPS-TSdataset. Anomaliesarelabeledby
redcirclesandredsegments(firstrow). Thefailurecasesofthebaselinesareboundedbyredboxes.
| -0.6 |     | 1   |     | 3   |     |     |     | -0.4 |     |
| ---- | --- | --- | --- | --- | --- | --- | --- | ---- | --- |
0.5
| seireS emiT -0.7 |     |     |     | 2   |     |     |     |     |     |
| ---------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
tupnI
|      |     | 0   |     |     |     | -0.5 |     | -0.6 |     |
| ---- | --- | --- | --- | --- | --- | ---- | --- | ---- | --- |
| -0.8 |     |     |     | 1   |     |      |     |      |     |
0
| -0.9 |     | -1  |     |     |     | -1.5 |     | -0.8 |     |
| ---- | --- | --- | --- | --- | --- | ---- | --- | ---- | --- |
0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100 0 20 40 60 80 100
|                   | Time |     | Time |     | Time |      | Time        |     | Time |
| ----------------- | ---- | --- | ---- | --- | ---- | ---- | ----------- | --- | ---- |
| 10                |      |     |      |     |      |      |             | 2.5 |      |
| desab-noitaicossA |      |     |      | 0.4 |      |      |             |     |      |
| 8                 |      | 10  |      |     |      | 0.06 | Early Stage |     |      |
Detection
| noiretirC 6 |     |     |     |     |     | 0.04 |     |     |     |
| ----------- | --- | --- | --- | --- | --- | ---- | --- | --- | --- |
|             |     |     |     | 0.2 |     |      |     | 1.5 |     |
5
| 4   |     |     |     |     |     | 0.02 |     |     |     |
| --- | --- | --- | --- | --- | --- | ---- | --- | --- | --- |
| 2   |     |     |     |     |     |      |     | 0.5 |     |
0
| 0   |     | 0   |     | 0   |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
0 20 40 Time 60 80 100 0 20 40 Time 60 80 100 0 20 40 Time 60 80 100 0 20 40 Time 60 80 100 0 20 40 Time 60 80 100
|     | (a) SMD |     | (b) MSL |     | (c) SMAP |     | (d) SWaT |     | (e) PSM |
| --- | ------- | --- | ------- | --- | -------- | --- | -------- | --- | ------- |
Figure9: Visualizationofthemodellearnedcriterioninreal-worlddatasets. Weselectonedimen-
sionofthedataforvisualization. Theseshowcasesarefromthetestsetofcorrespondingdatasets.
| D ABLATION |     | OF ASSOCIATION |     | DISCREPANCY |     |     |     |     |     |
| ---------- | --- | -------------- | --- | ----------- | --- | --- | --- | --- | --- |
WepresentthepseudocodeofthecalculationinAlgorithm2.
14

PublishedasaconferencepaperatICLR2022
D.1 ABLATIONOFMULTI-LEVELQUANTIFICATION
Weaveragetheassociationdiscrepancyfrommultiplelayersforthefinalresults(Equation6). We
further investigate the model performance under the single-layer usage. As shown in Table 4, the
multiple-layerdesignachievesthebest,whichverifiestheeffectivenessofmulti-levelquantification.
Table4: Modelperformanceunderdifferenceselectionofmodellayersforassociationdiscrepancy.
| Dataset | SMD    | MSL |     | SMAP   | SWaT | PSM       |
| ------- | ------ | --- | --- | ------ | ---- | --------- |
| Metric  | P R F1 | P R | F1  | P R F1 | P R  | F1 P R F1 |
layer1 87.15 92.87 89.92 90.36 94.11 92.19 93.65 99.03 96.26 92.61 91.92 92.27 97.20 97.50 97.35
layer2 87.22 95.17 91.02 90.82 92.41 91.60 93.69 98.75 96.15 92.48 92.50 92.49 96.12 98.62 97.35
layer3 87.27 93.89 90.46 91.61 88.81 90.19 93.40 98.83 96.04 88.75 91.22 89.96 77.25 94.53 85.02
Multiple-layer 89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
D.2 ABLATIONOFSTATISTICALDISTANCE
Weselectthefollowingwidely-usedstatisticaldistancestocalculatetheassociationdiscrepancy:
• SymmetrizedKullback–LeiblerDivergence(Ours).
• Jensen–ShannonDivergence(JSD).
• WassersteinDistance(Wasserstein).
• Cross-Entropy(CE).
• L2Distance(L2).
| Table5: | Modelperformanceunderdifferentdefinitionsofassociationdiscrepancy. |     |     |        |      |           |
| ------- | ------------------------------------------------------------------ | --- | --- | ------ | ---- | --------- |
| Dataset | SMD                                                                | MSL |     | SMAP   | SWaT | PSM       |
| Metric  | P R F1                                                             | P R | F1  | P R F1 | P R  | F1 P R F1 |
L2
85.26 74.80 79.69 85.58 81.30 83.39 91.25 56.77 70.00 79.90 87.45 83.51 70.24 96.34 81.24
CE 88.23 81.85 84.92 90.07 86.44 88.22 92.37 64.08 75.67 62.78 81.50 70.93 70.71 94.68 80.96
Wasserstein 78.80 71.86 75.17 60.77 36.47 45.58 90.46 57.62 70.40 92.00 71.63 80.55 68.25 92.18 78.43
JSD 85.33 90.09 87.64 91.19 92.42 91.80 94.83 95.14 94.98 83.75 96.75 89.78 95.33 98.58 96.93
Ours 89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
AsshowninTable5,ourproposeddefinitionofassociationdiscrepancystillachievesthebestper-
formance. We find that both the CE and JSD can provide fairly good results, which are close to
ourdefinitioninprincipleandcanbeusedtorepresenttheinformationgain. TheL2distanceisnot
suitableforthediscrepancy,whichoverlooksthepropertyofdiscretedistribution. TheWasserstein
distance also fails in some datasets. The reason is that the prior-association and series-association
areexactlymatchedinthepositionindexes. Still,theWassersteindistanceisnotcalculatedpointby
pointandconsidersthedistributionoffset,whichmaybringnoisestotheoptimizationanddetection.
Algorithm2AssociationDiscrepancyAssDis( , ; )Calculation(multi-headversion).
P S X
Input: time series length N; layers number L; heads number h; prior-association
all
P ∈
| RL×h×N×N;series-association |     |     | RL×h×N×N; |     |     |     |
| --------------------------- | --- | --- | --------- | --- | --- | --- |
all
S ∈
| 1: (cid:48) =Mean( | ,dim=1)    |          |          |          |     | (cid:46) (cid:48) RL×N×N |
| ------------------ | ---------- | -------- | -------- | -------- | --- | ------------------------ |
| P                  | P          |          |          |          |     | P ∈                      |
| 2: (cid:48) =Mean( | ,dim=1)    |          |          |          |     | (cid:46) (cid:48) RL×N×N |
| S                  | (cid:16) S | (cid:17) | (cid:16) | (cid:17) |     | S ∈                      |
(cid:48) (cid:48), (cid:48)),dim=-1 (cid:48), (cid:48)),dim=-1 (cid:48) RL×N
| 3: =KL | (   | +KL | (   |     |     | (cid:46) |
| ------ | --- | --- | --- | --- | --- | -------- |
| R      | P S |     | S P |     |     | R ∈      |
RN×1
| 4: =Mean( | (cid:48),dim=0) |     |     |     |     | (cid:46) |
| --------- | --------------- | --- | --- | --- | --- | -------- |
| R         | R               |     |     |     |     | R∈       |
5: Return (cid:46)Representtheassociationdiscrepancyofeachtimepoint
R
15

PublishedasaconferencepaperatICLR2022
D.3 ABLATIONOFPRIOR-ASSOCIATION
InadditiontotheGaussiankernelwithalearnablescaleparameter,wealsotrytousethepower-law
kernel P(x;α) = x−α with a learnable power parameter α for prior-association, which is also a
unimodaldistribution. AsshowninTable6, power-lawkernelcanachieveagoodperformancein
mostofthedatasets. However,becausethescaleparameteriseasiertooptimizethantheparameter
ofpower,Gaussiankernelstillsurpassesthepower-lawkernelconsistently.
Table6: Modelperformanceunderdifferentdefinitionsofprior-association. OurAnomalyTrans-
formeradoptstheGaussiankernelastheprior. Power-lawreferstothepower-lawkernel.
| Dataset |     | SMD |     | MSL |     | SMAP |      | SWaT |      |     | PSM  |     |
| ------- | --- | --- | --- | --- | --- | ---- | ---- | ---- | ---- | --- | ---- | --- |
| Metric  |     | P R | F1  | P R | F1  | P    | R F1 | P    | R F1 | P   | R F1 |     |
Power-law
89.41 92.46 90.91 90.95 85.87 88.34 91.95 58.24 71.31 92.52 93.29 92.90 96.46 98.15 97.30
Ours
89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
| E   | ABLATION | OF  | ASSOCIATION-BASED |     |     | CRITERION |     |     |     |     |     |     |
| --- | -------- | --- | ----------------- | --- | --- | --------- | --- | --- | --- | --- | --- | --- |
E.1 CALCULATION
Wepresentthepseudo-codeofassociation-basedcriterioninAlgorithm3.
| Algorithm3Association-basedCriterionAnomalyScore( |     |     |     |     |     |     | )Calculation |     |     |     |     |     |
| ------------------------------------------------- | --- | --- | --- | --- | --- | --- | ------------ | --- | --- | --- | --- | --- |
X
Input: timeserieslengthN;inputtimeseries RN×d;reconstructiontimeseries RN×d;
(cid:98)
|     |     |     |     |     |     | X ∈ |     |     |     |     | X ∈ |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
RN×1;
| associationdiscrepancyAssDis( |           |     |         |     | , ; )      |     |     |     |     |          |        |     |
| ----------------------------- | --------- | --- | ------- | --- | ---------- | --- | --- | --- | --- | -------- | ------ | --- |
|                               |           |     |         | P   | S X        | ∈   |     |     |     |          |        |     |
| 1:                            | =Softmax( |     | AssDis( | ,   | ; ),dim=0) |     |     |     |     | (cid:46) | RN×1   |     |
| C                             | AD        |     | −       | P S | X(cid:17)  |     |     |     |     |          | C AD ∈ |     |
(cid:16)
| 2:  | =Mean |     | ( (cid:98))2,dim=1 |     |     |     |     |     |     | (cid:46) | RN×1 |     |
| --- | ----- | --- | ------------------ | --- | --- | --- | --- | --- | --- | -------- | ---- | --- |
|     | Recon |     |                    |     |     |     |     |     |     | Recon    |      |     |
| C   |       |     | X −X               |     |     |     |     |     |     | C        | ∈    |     |
RN×1
| 3:        | = AD | Recon |     |     |     |     |                                      |     |     |     | (cid:46) |     |
| --------- | ---- | ----- | --- | --- | --- | --- | ------------------------------------ | --- | --- | --- | -------- | --- |
| C         | C    | ×C    |     |     |     |     |                                      |     |     |     | C ∈      |     |
| 4: Return |      |       |     |     |     |     | (cid:46)Anomalyscoreforeachtimepoint |     |     |     |          |     |
C
E.2 ABLATIONOFCRITERIONDEFINITION
We explore the model performance under different definitions of anomaly criterion, including the
pure association discrepancy, pure reconstruction performance and different combination methods
forassociationdiscrepancyandreconstructionperformance: additionandmultiplication.
|     |     |     |     |     |     |     | (cid:16) |     |     | (cid:17) |     |     |
| --- | --- | --- | --- | --- | --- | --- | -------- | --- | --- | -------- | --- | --- |
AssociationDiscrepancy:AnomalyScore(
|     |                              |     |     |     | )=Softmax |            | AssDis(            |           | , ;   | ) , |     |     |
| --- | ---------------------------- | --- | --- | --- | --------- | ---------- | ------------------ | --------- | ----- | --- | --- | --- |
|     |                              |     |     |     | X         |            | −                  |           | P S X |     |     |     |
|     |                              |     |     |     |           | (cid:104)  |                    | (cid:105) |       |     |     |     |
|     | Reconstruction:AnomalyScore( |     |     |     | )=        |            | (cid:98)i,: 2      |           | ,     |     |     |     |
|     |                              |     |     |     | X         | (cid:107)X | i,: −X (cid:107) 2 |           |       |     |     |     |
i=1,···,N
|     |     |     |     |     |     |     | (cid:16) |     |     | (cid:17) (cid:104) |     | (cid:105) |
| --- | --- | --- | --- | --- | --- | --- | -------- | --- | --- | ------------------ | --- | --------- |
2
Addition:AnomalyScore( )=Softmax AssDis( , ; ) + i,: (cid:98)i,: ,
|     |     |     |     |     | X   |     | −        |     | P S X |                    | (cid:107)X −X | (cid:107) 2 i=1,···,N |
| --- | --- | --- | --- | --- | --- | --- | -------- | --- | ----- | ------------------ | ------------- | --------------------- |
|     |     |     |     |     |     |     | (cid:16) |     |       | (cid:17) (cid:104) |               | (cid:105)             |
Multiplication(Ours):AnomalyScore( )=Softmax AssDis( , ; ) 2 .
|     |     |     |     |     |     |     |     |     |       |                     | i,: (cid:98)i,: | 2                   |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ----- | ------------------- | --------------- | ------------------- |
|     |     |     |     |     | X   |     | −   |     | P S X | (cid:12) (cid:107)X | −X              | (cid:107) i=1,···,N |
(7)
FromTable7, wefindthat directlyusingourproposedassociationdiscrepancycanalso achievea
goodperformance,whichsurpassesthecompetitivebaselineTHOC(Shenetal.,2020)consistently.
Besides, the multiplication combination that we used in Equation 6 performs the best, which can
bringabettercollaborationtothereconstructionperformanceandassociationdiscrepancy.
16

PublishedasaconferencepaperatICLR2022
Table 7: Ablation of criterion definition. We also include the state-of-the-art deep model THOC
(Shen et al., 2020) for comparison. AssDis and Recon represent the pure association discrepancy
andthepurereconstructionperformancerespectively.Oursreferstoourproposedassociation-based
criterionwiththemultiplicationcombination.
Dataset SMD MSL SMAP SWaT PSM Avg
Metric P R F1 P R F1 P R F1 P R F1 P R F1 F1(%)
THOC 79.76 90.95 84.99 88.45 90.97 89.69 92.06 89.34 90.68 83.94 86.36 85.13 88.14 90.99 89.54 88.01
Recon 78.63 65.29 71.35 79.15 78.07 78.61 89.38 56.35 69.12 76.81 86.89 81.53 69.84 94.73 80.40 76.20
AssDis 86.74 88.42 87.57 91.20 89.81 90.50 91.56 90.41 90.98 97.27 89.48 93.21 97.80 93.25 95.47 91.55
Addition 77.16 70.58 73.73 88.08 87.37 87.72 91.28 55.97 69.39 84.34 81.98 83.14 97.60 97.61 97.61 82.32
Ours 89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89 94.96
F CONVERGENCE OF MINIMAX OPTIMIZATION
Thetotallossofourmodel(Equation4)containstwoparts: thereconstructionlossandtheassocia-
tiondiscrepancy. Towardsabettercontrolofassociationlearning,weadoptaminimaxstrategyfor
optimization(Equation5). Duringtheminimizationphase,theoptimizationtrendstominimizethe
associationdiscrepancyandthereconstructionerror. Duringthemaximizationphase,theoptimiza-
tiontrendstomaximizetheassociationdiscrepancyandminimizethereconstructionerror.
Weplotthechangecurveoftheabovetwopartsduringthetrainingprocedure. AsshowninFigures
10and11,bothpartsofthetotallosscanconvergewithinlimitediterationsonallthefivereal-world
datasets. Thisniceconvergencepropertyisessentialfortheoptimizationofourmodel.
2.5 0.6 2 3 1.2
2 1.5 2 0.8
1.5 1
1 0.4 1 0.4
0.5
0.5
0 0.2 0 0 0 0 100 200 300 400 0 200 400 600 0 200 400 600 800 0 200 400 600 0 200 400 600
iterations iterations iterations iterations iterations (a) SMD (b) MSL (c) SMAP (d) SWaT (e) PSM
16 16 16 16 16 14 14 14 14 14 12 12 12 12 12
10 10 10 10 10
8 8 8 8 8
0 100 200 300 400 0 400 800 0 400 800 0 400 800 0 400 800
iterations iterations iterations iterations iterations
(a) SMD (b) MSL (c) SMAP (d) SWaT (e) PSM
ssol
noceR
ssol siDssA
ssol
noceR
ssol siDssA
ssol
noceR
ssol siDssA
ssol
noceR
ssol siDssA
ssol
noceR
ssol siDssA
2.5 0.6 2 3 1.2
2 1.5 2 0.8
1.5 1
F 0 1 .5 igure10: Changec 0 u .4 rveofreconstructio0.5nloss (cid:107)X −X (cid:98) (cid:107) 2 F in1real-worlddatasets0.4duringtraining. 0 0.2 0 0 0 0 100 200 300 400 0 200 400 600 0 200 400 600 800 0 200 400 600 0 200 400 600 iterations iterations iterations iterations iterations
(a) SMD (b) MSL (c) SMAP (d) SWaT (e) PSM
16 16 16 16 16
14 14 14 14 14
12 12 12 12 12
10 10 10 10 10
8 8 8 8 8
0 100 200 300 400 0 400 800 0 400 800 0 400 800 0 400 800
iterations iterations iterations iterations iterations
(a) SMD (b) MSL (c) SMAP (d) SWaT (e) PSM
ssol
noceR
ssol
siDssA
ssol
noceR
ssol
siDssA
ssol
noceR
ssol
siDssA
ssol
noceR
ssol
siDssA
ssol
noceR
ssol
siDssA
Figure 11: Change curve of association discrepancy AssDis( , ; ) in real-world datasets
1
(cid:107) P S X (cid:107)
duringthetrainingprocess.
G MODEL PARAMETER SENSITIVITY
In this paper, we set the hyper-parameters L and d following the convention of Transformers
model
(Vaswanietal.,2017;Zhouetal.,2021).
Furthermore,toevaluatemodelparametersensitivity,weinvestigatetheperformanceandefficiency
underdifferentchoicesforthenumberoflayersLandhiddenchannelsd . Generally,increasing
model
themodelsizecanobtainbetterresultsbutwithlargermemoryandcomputationcosts.
17

PublishedasaconferencepaperatICLR2022
|     | Table8: | ModelperformanceunderdifferentchoicesofthenumberoflayersL. |     |     |     |      |      |      |      |      |     |
| --- | ------- | ---------------------------------------------------------- | --- | --- | --- | ---- | ---- | ---- | ---- | ---- | --- |
|     | Dataset | SMD                                                        |     | MSL |     | SMAP |      | SWaT |      | PSM  |     |
|     | Metric  | P R                                                        | F1  | P R | F1  | P R  | F1 P | R    | F1 P | R F1 |     |
L=1 89.24 93.73 91.43 91.99 97.59 94.71 93.58 99.35 96.38 91.57 95.33 93.42 96.74 98.09 97.41
L=2 89.26 94.33 91.72 91.89 94.73 93.29 93.79 98.91 96.28 92.37 94.59 93.47 97.22 98.23 97.72
L=3 89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
L=4
|     | 89.59 | 95.76 | 92.58 91.88 | 95.40 | 93.61 | 93.75 99.13 96.37 | 93.37 | 93.45 93.41 | 97.30 | 97.58 97.44 |     |
| --- | ----- | ----- | ----------- | ----- | ----- | ----------------- | ----- | ----------- | ----- | ----------- | --- |
Table9: Modelperformanceunderdifferentchoicesofthenumberofhiddenchannelsd . Mem
model
meanstheaveragedGPUmemorycost. Timeistheaveragedrunningtimeof100iterationsduring
thetrainingprocess.
|     | Dataset | SMD |      | MSL |      | SMAP   |     | SWaT | PSM | MemTime   |     |
| --- | ------- | --- | ---- | --- | ---- | ------ | --- | ---- | --- | --------- | --- |
|     | Metric  | P   | R F1 | P   | R F1 | P R F1 | P   | R F1 | P   | R F1 (GB) | (s) |
d =256 88.8391.8290.3091.9697.6094.7093.7499.4796.5293.9193.9993.9597.3898.1697.77 4.9 0.12
model
d =512 89.4095.4592.3392.0995.1593.5994.1399.4096.6991.5596.7394.0796.9198.9097.89 5.5 0.15
model
d =102489.4496.3392.7691.8094.9993.3793.5899.4796.4392.0295.0193.4995.7898.1296.94
|     | model    |     |           |     |           |     |     |     |     | 6.6 | 0.27 |
| --- | -------- | --- | --------- | --- | --------- | --- | --- | --- | --- | --- | ---- |
| H   | PROTOCOL | OF  | THRESHOLD |     | SELECTION |     |     |     |     |     |      |
Our paper focuses on unsupervised time series anomaly detection. Experimentally, each dataset
includes training, validation and testing subsets. Anomalies are only labeled in the testing subset.
Thus,weselectthehyper-parametersfollowingtheGapStatisticmethod(Tibshiranietal.,2001)
| inK-Means. |     | Hereistheselectionprocedure: |     |     |     |     |     |     |     |     |     |
| ---------- | --- | ---------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
• After the training phase, we apply the model to the validation subset (without label) and
obtaintheanomalyscores(Equation6)ofalltimepoints.
• Wecountthefrequencyoftheanomalyscoresinthevalidationsubset. Itisobservedthat
the distribution of anomaly scores is separated into two clusters. We find that the cluster
withalargeranomalyscorecontainsrtimepoints. Andforourmodel,risclosedto0.1%,
0.5%,1%forSWaT,SMDandotherdatasetsrespectively(Table10).
• Duetothesizeofthetestsubsetbeingstillinaccessibleinreal-worldapplications,wehave
to fix the threshold as a fixed value δ, which can gaurantee that the anomaly scores of r
timepointsinthevalidationsetarelargerthanδandthusdetectedasanomalies.
Table10:Statisticalresultsofanomalyscoredistributiononthevalidationset.Wecountthenumber
oftimepointswithcorrespondingvaluesinseveralintervals.
|     | (a)SMD,MSLandSWaTdatasets. |     |     |     |     |     | (b)SMAPandPSMdatasets. |     |     |     |     |
| --- | -------------------------- | --- | --- | --- | --- | --- | ---------------------- | --- | --- | --- | --- |
AnomalyScoreInterval SMD MSL SWaT AnomalyScoreInterval SMAP PSM
|     | (0,+∞]     |     | 141681 | 11664 | 99000 |     | (0,+∞]      |     |     | 27037 26497 |     |
| --- | ---------- | --- | ------ | ----- | ----- | --- | ----------- | --- | --- | ----------- | --- |
|     | [0,10−2]   |     | 140925 | 11537 | 98849 |     | [0,10−3]    |     |     | 26732 26223 |     |
|     | (10−2,0.1] |     | 2      |       | 8     | 17  | (10−3,10−2] |     |     | 0           | 5   |
|     | (0.1,+∞]   |     | 754    | 119   | 134   |     | (10−2,+∞]   |     |     | 305 269     |     |
Ratioof(0.1,+∞] 0.53% 1.02% 0.14% Ratioof(10−2,+∞] 1.12% 1.01%
Notethat, directlysettingtheδ isalsofeasible. AccordingtotheintervalsinTable10, wecanfix
the δ as 0.1 for the SMD, MSL and SWaT datasets, 0.01 for the SMAP and PSM datasets, which
yieldaquitecloseperformancetosettingr.
18

PublishedasaconferencepaperatICLR2022
Table 11: Model performance. Choose by δ means that we fix δ as 0.1 for the SMD, MSL and
Choosebyrmeansthatweselectras0.1%
SWaTdatasets,0.01fortheSMAPandPSMdatasets.
forSWaT,0.5%forSMDand1%fortheotherdatasets.
| Dataset | SMD    | MSL    | SMAP   | SWaT   | PSM    |
| ------- | ------ | ------ | ------ | ------ | ------ |
| Metric  | P R F1 | P R F1 | P R F1 | P R F1 | P R F1 |
Choosebyδ 88.65 97.17 92.71 91.86 95.15 93.47 97.69 98.24 97.96 86.02 95.01 90.29 97.69 98.24 97.96
Choosebyr 89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
In real-world applications, the number of selected anomalies is always decided up to human re-
sources. Underthisconsideration,settingthenumberofdetectedanomaliesbytheratior ismore
practicalandeasiertodecideaccordingtotheavailableresources.
| I MORE | BASELINES |     |     |     |     |
| ------ | --------- | --- | --- | --- | --- |
Inadditiontothetimeseriesanomalydetectionmethods,themethodsforchangepointdetectionand
timeseriessegmentationcanalsoperformasvaluablebaselines. Thus,wealsoincludetheBOCPD
(Adams&MacKay,2007)andTS-CP2(Deldarietal.,2021)fromchangepointdetectionandU-
Time (Perslev et al., 2019) from time series segmentation for comparison. Anomaly Transformer
stillachievesthebestperformance.
Table12:AdditionalquantitativeresultsforAnomalyTransformer(Ours)infivereal-worlddatasets.
TheP,RandF1representtheprecision,recallandF1-score(as%)respectively. F1-scoreisthehar-
monicmeanofprecisionandrecall.Forthesemetrics,ahighervalueindicatesabetterperformance.
| Dataset | SMD    | MSL    | SMAP   | SWaT   | PSM    |
| ------- | ------ | ------ | ------ | ------ | ------ |
| Metric  | P R F1 | P R F1 | P R F1 | P R F1 | P R F1 |
BOCPD
70.90 82.04 76.07 80.32 87.20 83.62 84.65 85.85 85.24 89.46 70.75 79.01 80.22 75.33 77.70
TS-CP2
87.42 66.25 75.38 86.45 68.48 76.42 87.65 83.18 85.36 81.23 74.10 77.50 82.67 78.16 80.35
U-Time
65.95 74.75 70.07 57.20 71.66 63.62 49.71 56.18 52.75 46.20 87.94 60.58 82.85 79.34 81.06
Ours
89.40 95.45 92.33 92.09 95.15 93.59 94.13 99.40 96.69 91.55 96.73 94.07 96.91 98.90 97.89
| J LIMITATIONS | AND FUTURE | WORK |     |     |     |
| ------------- | ---------- | ---- | --- | --- | --- |
Window size As shown in the Figure 7 of Appendix A, the model may fail if the window size
is too small for association learning. But the Transformers is with quadratic complexity w.r.t. the
| windowsize. | Thetrade-offisneededforreal-worldapplications. |     |     |     |     |
| ----------- | ---------------------------------------------- | --- | --- | --- | --- |
Theoreticalanalysis Asawell-establisheddeepmodel,theperformanceofTransformershasbeen
exploredinpreviousworks. Butitisstillunder-exploringforthetheoryofcomplexdeepmodels.
Inthefuture,wewillexplorethetheoremofAnomalyTransformerforbetterjustificationsinlight
ofclassicanalysisforautoregressionandstatespacemodels.
K DATASET
Hereisthestatisticaldetailsofexperimentdatasets.
Table13: Detailsofbenchmarks. ARrepresentsthetruthabnormalproportionofthewholedataset.
Benchmarks Applications Dimension Window #Training #Validation #Test(labeled) AR(Truth)
| SMD        | Server           | 38 100 | 566,724 141,681 | 708,420 | 0.042 |
| ---------- | ---------------- | ------ | --------------- | ------- | ----- |
| PSM        | Server           | 25 100 | 105,984 26,497  | 87,841  | 0.278 |
| MSL        | Space            | 55 100 | 46,653 11,664   | 73,729  | 0.105 |
| SMAP       | Space            | 25 100 | 108,146 27,037  | 427,617 | 0.128 |
| SWaT       | Water            | 51 100 | 396,000 99,000  | 449,919 | 0.121 |
| NeurIPS-TS | VariousAnomalies | 1 100  | 20,000 10,000   | 20,000  | 0.018 |
19

PublishedasaconferencepaperatICLR2022
L UCR DATASET
UCRDatasetisaverychallengingandcomprehensivedatasetprovidedbytheMulti-datasetTime
Series Anomaly Detection Competition of KDD2021 (Keogh et al., Competition of International
ConferenceonKnowledgeDiscovery&DataMining2021). Thewholedatasetcontains250sub-
datasets, covering various real-world scenarios. Each sub-dataset of UCR has only one anomaly
segmentandonlyhasonedimension. Thesesub-datasetsrangeinlengthfrom6,684to900,000and
arepre-dividedintotrainingandtestsets.
WealsoexperimentontheUCRdatasetforawideevaluation. AsshowinTable14,ourAnomaly
Transformerstillachievesthestate-of-the-artinthischallengingbenchmark.
Table14: QuantitativeresultsinUCRDataset. IF referstotheIsolationForest(2008). Oursisour
AnomalyTransformer. P,RandF1representtheprecison,recallandF1-score(%)respectively.
Metric LSTM-VAE InterFusion OmniAnomaly THOC Deep-SVDD BeatGAN LOF OC-SVM IF Ours
P 62.08 60.74 64.21 54.61 47.08 45.20 41.47 41.14 40.77 72.80
R 97.60 95.20 86.93 80.83 88.91 88.42 98.80 94.00 93.60 99.60
F1 75.89 74.16 73.86 65.19 61.56 59.82 58.42 57.23 56.80 84.12
20
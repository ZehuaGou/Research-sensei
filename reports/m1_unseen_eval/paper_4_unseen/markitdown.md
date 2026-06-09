MEMTO: Memory-guided Transformer for
Multivariate Time Series Anomaly Detection
JunhoSong1∗ KeonwooKim1,2∗ JeonglyulOh1 SungzoonCho1†
1SeoulNationalUniversity
2VRCREWInc.
{jhsong, keonwookim, jamesoh0813}@bdai.snu.ac.kr
zoon@snu.ac.kr
Detecting anomalies in real-world multivariate time series data is challenging
duetocomplextemporaldependenciesandinter-variablecorrelations. Recently,
reconstruction-based deep models have been widely used to solve the problem.
However, these methods still suffer from an over-generalization issue and fail
todeliverconsistentlyhighperformance. Toaddressthisissue,weproposethe
MEMTO,amemory-guidedTransformerusingareconstruction-basedapproach.
It is designed to incorporate a novel memory module that can learn the degree
towhicheachmemoryitemshouldbeupdatedinresponsetotheinputdata. To
stabilize the training procedure, we use a two-phase training paradigm which
involvesusingK-meansclusteringforinitializingmemoryitems. Additionally,
weintroduceabi-dimensionaldeviation-baseddetectioncriterionthatcalculates
anomalyscoresconsideringbothinputspaceandlatentspace. Weevaluateour
proposedmethodonfivereal-worlddatasetsfromdiversedomains,anditachieves
an average anomaly detection F1-score of 95.74%, significantly outperforming
thepreviousstate-of-the-artmethods. Wealsoconductextensiveexperimentsto
empiricallyvalidatetheeffectivenessofourproposedmodel’skeycomponents.
Ascyber-physicalsystemsadvance,avastamountoftimeseriesdataiscontinuouslycollectedfrom
numeroussensors. Anomaliesresultingfrommalfunctionsincriticalinfrastructures,suchaswater
treatmentfacilitiesandspaceprobes, canincurfatalpropertyloss. Thetaskofmultivariatetime
seriesanomalydetectioninvolvesidentifyingwhethereachtimestampofthemultivariatetimeseries
is normal or abnormal. Anomaly detection in real-world scenarios is challenging due to severe
dataimbalanceandtheprevalenceofunlabeledanomalies. Wehaveformulatedtheproblemasan
unsupervisedlearningtasktotacklethesechallenges. Theunderlyingassumptionofthisapproachis
thatthetrainingdatasolelyconsistsofnormalsamples[25,42].
Traditionalunsupervisedlearningmethodssuchasone-classSVM(OC-SVM)[28],supportvector
data description (SVDD) [35], isolation forest [20], and local outlier factor (LOF) [5] have been
widely used for anomaly detection tasks. Recently, density-estimation methods combined with
deeprepresentationlearning,suchasDAGMM[45]andMPPCACD[41],havealsobeenpresented.
Fortheclustering-basedmethod,DeepSVDD[25]findsthesmallesthyper-sphereenclosingmost
normalsamplesinthefeaturespacetrainedusingdeepneuralnetworks. However,theyexhibitpoor
performanceinthetimeseriesdomainduetotheirinabilitytocapturedynamicnonlineartemporal
∗indicatesequalcontributions
†indicatescorrespondingauthor
37thConferenceonNeuralInformationProcessingSystems(NeurIPS2023).
3202
ceD
5
]GL.sc[
1v03520.2132:viXra

dependenciesandcomplexinter-variablecorrelations. Deepmodelstailoredforsequentialdatahave
been introduced to solve these inherent challenges [30, 7, 29]. THOC [29] uses a differentiable
hierarchicalclusteringmechanismtocombinetemporalfeaturesofvaryingscalesfromdifferent
resolutions. Multiplehyper-spheresareusedtorepresenteachnormalpatternatvariousresolutions,
improvingtherepresentationalcapacitytocaptureintricatetemporalfeaturesoftimeseriesdata.
One of the primary types of recent deep methods is a reconstruction-based method, which uses
an encoder-decoder architecture trained by a self-supervised pretext task of reconstructing input.
Thisapproachexpectsaccuratereconstructionfornormalsamplesandhighreconstructionerrorsfor
anomalies. EarlymethodsincludeLSTM-basedencoder-decodermodel[22]andLSTM-VAE[23].
OmniAnomaly[31]andInterFusion[19]areotherstochasticrecurrentneuralnetwork-basedmodels
extendedfromLSTM-VAE.Anotherbranchofthereconstruction-basedmethodisdeepgenerative
models. MAD-GAN[17]andBeatGAN[42]aregenerativeadversarialnetwork[9]variantstailored
fortimeseriesanomalydetection. ThemostrecentlyproposedAnomalyTransformer[40]introduces
theAnomaly-Attentionmechanismtosimultaneouslymodelprior-andseries-associations. However,
to the best of our knowledge, existing reconstruction-based methods may suffer from an over-
generalizationproblem,whereabnormalinputsarereconstructedtoowell[8,24]. Thiscanoccur
if the encoder extracts unique features of an anomaly or if the decoder has excessive decoding
capabilitiesforabnormalencodingvectors.
Ourpaperpresentsanewreconstruction-basedmethod,amemory-guidedTransformer,formultivari-
atetimeseriesanomalydetection(MEMTO).OneofthekeycomponentsinMEMTOistheGated
memorymodule,whichincludesitemsrepresentingtheprototypicalfeaturesofnormalpatternsinthe
data. WeemployanincrementalapproachtotraintheindividualitemsintheGatedmemorymodule.
Itdeterminesthedegreetowhicheachexistingitemshouldbeupdatedbasedontheinputdata. This
anappropriateclusteringalgorithmdependingonthetypeofdataset.
3.4 Anomalycriterion
Weintroduceabi-dimensionaldeviation-baseddetectioncriterionthatcomprehensivelyconsiders
input and latent space. We define Latent Space Deviation (LSD) LSD(qs,m) at time point t as
t
distance between each query qs and its nearest memory item ms,pos in latent space (9). LSD of
t t
anomalieswouldbelargerthanthoseofnormaltimepointsbecauseeachmemoryitemcontainsa
prototypeofnormalpatterns. Additionally,wedefineInputSpaceDeviation(ISD)ISD(Xs ,Xˆs )
t,: t,:
attimetasdistancebetweeninputXs ∈RnandreconstructedinputXˆs ∈Rnininputspace(10).
t,: t,:
LSD(qs,m)=∥qs−ms,pos∥2
(9)
t t t 2
(cid:13) (cid:13)2
ISD(Xs ,Xˆs )=(cid:13)Xs −Xˆs (cid:13) (10)
t,: t,: (cid:13) t,: t,:(cid:13)
2
WemultiplynormalizedLSDwithISD,usingLSDasweightsforamplifyingthenormal-abnormal
gapinISD:
A(Xs)=softmax([LSD(qs,m)] )◦[ISD(Xs ,Xˆs )] , (11)
t t=1,...,L t,: t,: t=1,...,L
where ◦ is element-wise multiplication and A(Xs) ∈ RL is anomaly score at each time point.
Leveragingnormal-abnormaldistinguishingcriteriainlatentspace(i.e.,LatentSpaceDeviation)and
inputspace(i.e.,InputSpaceDeviation)leadstobetterdetectionperformance.
A.1 Hyperparametersettings
ImportanthyperparametersofMEMTOweredeterminedthroughgridsearch,whileotherswereset
tocommonlyuseddefaultvaluesbasedonempiricalobservations. Weperformedagridsearchto
determinethevaluesofeachhyperparameterwithinthefollowingrange:
• λ∈{1e+0,5e-1,1e-1,5e-2,1e-2,5e-3,1e-3}
• lr ∈{1e-4,3e-4,5e-4,1e-5,3e-5,5e-5}
• τ ∈{0.1,0.3,0.5,0.7,0.9}
• M ∈{5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100}
, where lr, τ, and M denote the learning rate, the temperature in the softmax function, and the
numberofclusters,respectively. Sincewesetthecentroidsofclustersasmemoryitems,thenumber
ofmemoryitemsandthatofclustersarethesame. Wesettheoptimalhyperparametersasfollows:
λas1e-2,lras5e-5,τ as0.1,andM as10. Allexperimentsinthispaperareconductedusingthe
samehyperparametersregardlessofthedataset.
A.2 Dataset
Table6: Detailsinfivebenchmarks. Thenumberofsamplesinthetraining,validation,andtestsets
isrepresentedinthecolumnslabeled‘Train,’ ‘Valid,’ and‘Test,’ respectively. The‘p%’column
indicatestheanomalyratiousedintheexperiment. The‘Dim’columnshowsthedimensionsizeof
thedataforeachdataset.
Train Valid Test p(%) Dim
SMD 566,724 141,681 708,420 0.5 38
MSL 46,653 11,664 73,729 1.0 55
PSM 105,984 26,497 87,841 1.0 26
SMAP 108,146 27,037 427,617 1.0 25
SWaT 396,000 99,000 449,919 0.1 53
Table6showsthestatisticaldetailsofdatasetsusedinexperiments. WeobtainedSWaTbysubmitting
arequestthroughhttps://itrust.sutd.edu.sg/itrust-labs_datasets/.
14

B AlgorithmforMEMTO
Algorithm2ProposedMethodMEMTO
| Input | Xs ∈RL×n: | inputsub-series |     |     |     |     |     |     |     |     |
| ----- | --------- | --------------- | --- | --- | --- | --- | --- | --- | --- | --- |
Trainingparams f : encoder,f : decoder,U ,W ∈RC×C: linearprojectionmatrices
|     |         | e   |                          | d   | ψ   | ψ     |     |     |     |     |
| --- | ------- | --- | ------------------------ | --- | --- | ----- | --- | --- | --- | --- |
|     | qs (Xs) |     | \\feed-forwardencoder,qs |     |     | ∈RL×C |     |     |     |     |
1: =f e
(cid:16) (cid:17)
|     | vs  | m(qs)T |     |     | \\Gatedmemoryupdatestart,m∈RM×C,vs |     |     |     |     | ∈RM×L |
| --- | --- | ------ | --- | --- | ---------------------------------- | --- | --- | --- | --- | ----- |
2: =softmax
∈RM×C
| 3:  | ψ =sigmoid(mU      |     | +(vsqs)W | )   |                        | \\ψ |     |     |     |     |
| --- | ------------------ | --- | -------- | --- | ---------------------- | --- | --- | --- | --- | --- |
|     |                    |     | ψ        | ψ   |                        |     |     |     |     |     |
| 4:  | m=(1−ψ)◦m+ψ◦(vsqs) |     |          |     | \\Gatedmemoryupdateend |     |     |     |     |     |
(cid:16) (cid:17)
| 5:  | ws =softmax                 | qs(m)T |             |     | \\Queryupdatestart,ws |     |     | ∈RL×M  |     |     |
| --- | --------------------------- | ------ | ----------- | --- | --------------------- | --- | --- | ------ | --- | --- |
| 6:  | q˜s =wsm                    |        | \\q˜s ∈RL×C |     |                       |     |     |        |     |     |
|     | qˆs =concat([qs,q˜s],dim=1) |        |             |     | \\Queryupdateend,qˆs  |     |     | ∈RL×2C |     |     |
7:
|     | Xˆs      |     | \\feed-forwarddecoder,Xˆs |     |     |       |     |     |     |     |
| --- | -------- | --- | ------------------------- | --- | --- | ----- | --- | --- | --- | --- |
| 8:  | =f (qˆs) |     |                           |     |     | ∈RL×n |     |     |     |     |
d
returnXˆs
| 9:  |     |     | \\reconstructedsub-series |     |     |     |     |     |     |     |
| --- | --- | --- | ------------------------- | --- | --- | --- | --- | --- | --- | --- |
Algorithm2providesanoverallmechanismforourmodel. Itdemonstratesthematrixoperation
versionoftheforwardprocesswhenasingleinputsub-seriesXsisfedtoMEMTO.
C Additionalexperiments
Table7: Theablationresults(F1-score)inanomalycriterionandobjectivefunction. L andL
|     |     |     |     |     |     |     |     |     |     | rec entr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | -------- |
signifyReconstructionLossandEntropyLoss,respectively.
|     | Loss | AnomalyCriterion |     |     |     |     | F1-score |      |      |      |
| --- | ---- | ---------------- | --- | --- | --- | --- | -------- | ---- | ---- | ---- |
|     |      |                  | ISD | LSD | SMD | MSL | PSM      | SMAP | SWaT | avg. |
✓
|     |     |     |     | ×   | 79.63 | 86.23 | 82.15 | 71.18 | 31.29 | 70.09 |
| --- | --- | --- | --- | --- | ----- | ----- | ----- | ----- | ----- | ----- |
✓
|     | L   |     | ×   |     | 69.73 | 72.63 | 93.07 | 67.69 | 82.50 | 77.12 |
| --- | --- | --- | --- | --- | ----- | ----- | ----- | ----- | ----- | ----- |
rec
|     |     |     | ✓   | ✓   | 93.19 | 92.66 | 98.05 | 96.48 | 93.34 | 94.74 |
| --- | --- | --- | --- | --- | ----- | ----- | ----- | ----- | ----- | ----- |
|     |     |     | ✓   | ×   | 75.71 | 88.39 | 87.47 | 69.28 | 79.28 | 80.02 |
|     | L   |     | ×   | ✓   | 12.53 | 84.34 | 76.49 | 68.17 | 83.52 | 65.01 |
entr
|     |     |     | ✓   | ✓   |       |       |       |       |       |       |
| --- | --- | --- | --- | --- | ----- | ----- | ----- | ----- | ----- | ----- |
|     |     |     |     |     | 88.43 | 93.40 | 97.97 | 96.22 | 92.77 | 93.75 |
✓
|     |          |     |     | ×   | 77.54 | 87.22 | 79.25 | 70.99 | 31.17 | 69.23 |
| --- | -------- | --- | --- | --- | ----- | ----- | ----- | ----- | ----- | ----- |
|     | L +λL    |     | ×   | ✓   | 72.78 | 80.33 | 80.15 | 67.55 | 0.00  | 60.16 |
|     | rec entr |     |     |     |       |       |       |       |       |       |
|     |          |     | ✓   | ✓   | 93.54 | 94.36 | 98.34 | 96.61 | 95.83 | 95.73 |
Table8: Wereportmeanandstandarddeviationover10runsforA.T(AnomalyTransformer)and
MEMTO,respectively. Weconductt-test(p<0.05)toindicatestatisticalsignficance.
|     |     |     |      | SMD   | MSL   | SMAP |       | SWaT  | PSM   |     |
| --- | --- | --- | ---- | ----- | ----- | ---- | ----- | ----- | ----- | --- |
|     |     |     | mean | 91.34 | 92.60 |      | 95.83 | 92.86 | 97.57 |     |
A.T
|     |     |     | std  | 0.6942 | 1.103 |     | 1.088 | 0.9455 | 0.1230 |     |
| --- | --- | --- | ---- | ------ | ----- | --- | ----- | ------ | ------ | --- |
|     |     |     | mean | 93.05  | 94.07 |     | 96.49 | 95.23  | 98.15  |     |
MEMTO
|     |     |         | std | 0.3762 | 0.5185 | 0.07987 |     | 1.016  | 0.1666 |     |
| --- | --- | ------- | --- | ------ | ------ | ------- | --- | ------ | ------ | --- |
|     |     | p-value |     | 0.0000 | 0.0301 | 0.0360  |     | 0.0002 | 0.0000 |     |
C.1 Objectivefunctionandanomalycriterion
Inthisexperiment,weinvestigatetheimpactoflossterms,specificallythereconstructionlossL
rec
andtheentropylossL ,ontheperformanceofourproposedframework,MEMTO.Weremove
entr
15

oneofthetwotermsonebyonefromtheobjectivefunctionandevaluatetheresultingperformance.
Table7demonstratesthesignificanceofincorporatingbothL andL termsintheobjective
rec entr
function. Applyingbi-dimensionaldeviation-basedcriteriontotheMEMTOvariantsthatonlyuse
L or L as the loss function shows competitive performance compared to ours in terms of
rec entr
averageF1-score. ThisdemonstratestherobustnessofMEMTOtolossterms. Additionally,both
casesshowasignificantperformancedropwhenusingonlyISDorLSDastheanomalycriterion,
emphasizingtheimportanceofcombiningISDandLSDforachievingoptimalperformance.
C.2 Statisticalsignificancetest
Wealsoperformstatisticaltestscomparingourresultstothelateststate-of-the-artmodel,Anomaly
Transformer. Weconductat-testtoproveasignificantperformancedifferencebetweenMEMTO
andAnomalyTransformer. TheresultsinTable8showap-valuelessthan0.05acrossalldatasets,
confirmingasignificantperformancedifferencebetweenthetwomodels.
C.3 Numberofdecoderlayers
Figure5: F1-scoreandnumberofparameters,accordingtothenumberofdecoderlayers. Theright
y-axisrepresentsthevaluesofthebluelinegraphinmillionunits,whilethelefty-axisrepresentsthe
valuesofthebargraph.
Figure 5 provides the performance of MEMTO under different numbers of decoder layers. As
shown in Figure 5, a decoder that is too shallow (e.g., a decoder with a single layer) performs
worse because it lacks sufficient capacity to reconstruct the input data accurately. On the other
hand, if the decoder is too large (e.g., decoder with ten layers), it can become overly expressive
andreconstructevenanomaliesregardlessoftheencodingabilityoftheencoder. Therefore,itcan
leadtoanover-generalizationproblem,whichcanultimatelydecreasetheperformanceofanomaly
detectionbyreconstructinganomaliestooaccurately. Furthermore,alargerdecoderlayerwithmore
parameters can increase computational and memory costs. We empirically find that considering
thebalancebetweenperformanceandresourcecost,adecoderwithtwolayersismostsuitablefor
anomalydetectiontaskspresentedinourpaper.
D Additionaldetailsfordiscussion
D.1 LSDvalues
Table9showsmeanLSDvaluesofnormalandabnormalsamplesacrossvariousdomainsofdatasets
whileusingdifferentmemorymodulemechanisms. Inmostdatasets,ourproposedGatedmemory
moduleconsistentlyexhibitsalowermeanLSDvaluefornormalsamplesthanforabnormalsamples.
Furthermore, the relative difference between these values is more significant than other memory
modulemechanisms. Theseresultsdemonstratetheefficacyofourmemorymodulemechanismin
capturingprototypicalfeaturesofnormalpatternsindata.
16

Table9: ThemeanLSDvaluescorrespondingtotestdata.
SMD MSL PSM SMAP SWaT
Normal Abnormal Normal Abnormal Normal Abnormal Normal Abnormal Normal Abnormal
MemAE 814.7836 842.2023 622.5195 640.4954 766.2473 782.1895 710.4929 706.3115 795.7227 770.9069
MNAD 259.3633 258.0175 791.6371 788.2654 292.3340 293.4836 301.3480 301.2153 303.1933 310.9818
Ours 297.5692 330.1162 249.8632 263.4532 340.7552 363.7520 237.0070 234.7110 450.0926 721.3093
D.2 Anomalyscore
Figure6: VisualizationofanomalyscoresforMSL,PSM,SMAP,andSWaTdatasets.
Figure6visuallyrepresentstheanomalyscoresforbenchmarkdatasetsnotdiscussedinSection4.4.
We randomly sampled data of length 150 from MSL, PSM, SMAP, and SWaT test datasets and
plottedtheanomalyscoresforeachsegment. Comparedtootherbaselines,ourproposedmethod
consistentlydetectsanomaliespreciselywithalowfalsepositiveratefromtheperspectiveofthe
pointadjustmentmethod.
17
WeintroduceMEMTO,anunsupervisedreconstruction-basedmodelformultivariatetimeseries
anomalydetection. TheGatedmemorymoduleinMEMTOadaptivelycapturesthenormalpatterns
inresponsetotheinputdata, anditcanbetrainedrobustlyusingatwo-phasetrainingparadigm.
Ourproposedanomalycriterion,whichcomprehensivelyconsidersbi-dimensionalspace,enhances
theperformanceofMEMTO.Extensiveexperimentsonreal-worldmultivariatetimeseriesbench-
marksvalidatethatourproposedmodelachievesstate-of-the-artperformancecomparedtoexisting
competitivemodels.
Limitations While our two update stages in the Gated memory module and bi-dimensional
deviation-based criterion have led to enhanced performance, a thorough theoretical proof for its
efficacyremainstobeestablished. Also,weacknowledgethelimitationofouromissionofvisually
inspectingtheprototypicalnormalpatternsstoredinmemoryitems. Inthefuture,wewillexplore
theseissuesfurtherasapartofourresearch.
Broaderimpacts MEMTOistailoredfordetectinganomaliesinmultivariatetimeseriesdataand
canbeappliedtovariouscomplexcyber-physicalsystems,suchassmartfactories,powergrids,data
centers,andvehicles. However,westronglydiscourageitsuseinactivitiesrelatedtofinancialcrimes
orotherapplicationsthatcouldhavenegativesocietalconsequences.
10

Acknowledgements
ThisworkwassupportedbytheNationalResearchFoundationofKorea(NRF)grantfundedbythe
Koreagovernment(MSIT).(No. 2021R1A2C2093785)
[1] AhmedAbdulaal,ZhuanghuaLiu,andTomerLancewicki. Practicalapproachtoasynchronous
multivariatetimeseriesanomalydetectionandlocalization. InProceedingsofthe27thACM
SIGKDDconferenceonknowledgediscovery&datamining,pages2485–2494,2021.
[2] JulienAudibert, PietroMichiardi, FrédéricGuyard, SébastienMarti, andMariaAZuluaga.
Usad: Unsupervised anomaly detection on multivariate time series. In Proceedings of the
26thACMSIGKDDInternationalConferenceonKnowledgeDiscovery&DataMining,pages
3395–3404,2020.
[3] DzmitryBahdanau,KyunghyunCho,andYoshuaBengio. Neuralmachinetranslationbyjointly
learningtoalignandtranslate. arXivpreprintarXiv:1409.0473,2014.
[4] Ane Blázquez-García, Angel Conde, Usue Mori, and Jose A Lozano. A review on out-
lier/anomaly detection in time series data. ACM Computing Surveys (CSUR), 54(3):1–33,
2021.
[5] MarkusMBreunig,Hans-PeterKriegel,RaymondTNg,andJörgSander. Lof: identifying
density-basedlocaloutliers.InProceedingsofthe2000ACMSIGMODinternationalconference
onManagementofdata,pages93–104,2000.
[6] QiCai,YingweiPan,TingYao,ChenggangYan,andTaoMei. Memorymatchingnetworksfor
one-shotimagerecognition. InProceedingsoftheIEEEconferenceoncomputervisionand
patternrecognition,pages4080–4088,2018.
[7] YongliangCheng,YanXu,HongZhong,andYiLiu. Hs-tcn: Asemi-supervisedhierarchical
stacking temporal convolutional network for anomaly detection in iot. In 2019 IEEE 38th
InternationalPerformanceComputingandCommunicationsConference(IPCCC),pages1–7.
IEEE,2019.
[8] Dong Gong, Lingqiao Liu, Vuong Le, Budhaditya Saha, Moussa Reda Mansour, Svetha
Venkatesh,andAntonvandenHengel. Memorizingnormalitytodetectanomaly: Memory-
augmented deep autoencoder for unsupervised anomaly detection. In Proceedings of the
IEEE/CVFInternationalConferenceonComputerVision,pages1705–1714,2019.
[9] Ian Goodfellow, Jean Pouget-Abadie, Mehdi Mirza, Bing Xu, David Warde-Farley, Sherjil
Ozair,AaronCourville,andYoshuaBengio. Generativeadversarialnetworks. Communications
oftheACM,63(11):139–144,2020.
[10] MononitoGoswami,CristianChallu,LaurentCallot,LenonMinorics,andAndreyKan. Unsu-
pervisedmodelselectionfortime-seriesanomalydetection. arXivpreprintarXiv:2210.01078,
2022.
[11] Alex Graves, Greg Wayne, and Ivo Danihelka. Neural turing machines. arXiv preprint
arXiv:1410.5401,2014.
[12] TengdaHan,WeidiXie,andAndrewZisserman. Memory-augmenteddensepredictivecoding
forvideorepresentationlearning. InComputerVision–ECCV2020: 16thEuropeanConference,
Glasgow,UK,August23–28,2020,Proceedings,PartIII16,pages312–329.Springer,2020.
[13] KyleHundman,ValentinoConstantinou,ChristopherLaporte,IanColwell,andTomSoderstrom.
Detecting spacecraft anomalies using lstms and nonparametric dynamic thresholding. In
Proceedingsofthe24thACMSIGKDDinternationalconferenceonknowledgediscovery&
datamining,pages387–395,2018.
[14] ŁukaszKaiser,OfirNachum,AurkoRoy,andSamyBengio. Learningtorememberrareevents.
arXivpreprintarXiv:1703.03129,2017.
11

[15] DiederikPKingmaandJimmyBa. Adam:Amethodforstochasticoptimization. arXivpreprint
arXiv:1412.6980,2014.
[16] Ankit Kumar, Ozan Irsoy, Peter Ondruska, Mohit Iyyer, James Bradbury, Ishaan Gulrajani,
Victor Zhong, Romain Paulus, and Richard Socher. Ask me anything: Dynamic memory
networksfornaturallanguageprocessing. InInternationalconferenceonmachinelearning,
pages1378–1387.PMLR,2016.
[17] DanLi,DachengChen,BaihongJin,LeiShi,JonathanGoh,andSee-KiongNg. Mad-gan:
Multivariateanomalydetectionfortimeseriesdatawithgenerativeadversarialnetworks. In
ArtificialNeuralNetworksandMachineLearning–ICANN2019: TextandTimeSeries: 28th
InternationalConferenceonArtificialNeuralNetworks,Munich,Germany,September17–19,
2019,Proceedings,PartIV,pages703–716.Springer,2019.
[18] DanLi,DachengChen,BaihongJin,LeiShi,JonathanGoh,andSee-KiongNg. Mad-gan:
Multivariateanomalydetectionfortimeseriesdatawithgenerativeadversarialnetworks. In
ArtificialNeuralNetworksandMachineLearning–ICANN2019: TextandTimeSeries: 28th
InternationalConferenceonArtificialNeuralNetworks,Munich,Germany,September17–19,
2019,Proceedings,PartIV,pages703–716.Springer,2019.
[19] ZhihanLi,YoujianZhao,JiaqiHan,YaSu,RuiJiao,XidaoWen,andDanPei. Multivariate
timeseriesanomalydetectionandinterpretationusinghierarchicalinter-metricandtemporal
embedding. InProceedingsofthe27thACMSIGKDDconferenceonknowledgediscovery&
datamining,pages3220–3230,2021.
[20] Fei Tony Liu, Kai Ming Ting, and Zhi-Hua Zhou. Isolation forest. In 2008 eighth ieee
internationalconferenceondatamining,pages413–422.IEEE,2008.
[21] Zhian Liu, Yongwei Nie, Chengjiang Long, Qing Zhang, and Guiqing Li. A hybrid video
anomaly detection framework via memory-augmented flow reconstruction and flow-guided
frame prediction. In Proceedings of the IEEE/CVF International Conference on Computer
Vision,pages13588–13597,2021.
[22] PankajMalhotra, AnushaRamakrishnan, GaurangiAnand, LovekeshVig, PuneetAgarwal,
andGautamShroff. Lstm-basedencoder-decoderformulti-sensoranomalydetection. arXiv
preprintarXiv:1607.00148,2016.
[23] DaehyungPark,YuunaHoshi,andCharlesCKemp. Amultimodalanomalydetectorforrobot-
assistedfeedingusinganlstm-basedvariationalautoencoder. IEEERoboticsandAutomation
Letters,3(3):1544–1551,2018.
[24] HyunjongPark,JongyounNoh,andBumsubHam. Learningmemory-guidednormalityfor
anomalydetection. InProceedingsoftheIEEE/CVFconferenceoncomputervisionandpattern
recognition,pages14372–14381,2020.
[25] Lukas Ruff, Robert Vandermeulen, Nico Goernitz, Lucas Deecke, Shoaib Ahmed Siddiqui,
Alexander Binder, Emmanuel Müller, and Marius Kloft. Deep one-class classification. In
Internationalconferenceonmachinelearning,pages4393–4402.PMLR,2018.
[26] Lukas Ruff, Robert Vandermeulen, Nico Goernitz, Lucas Deecke, Shoaib Ahmed Siddiqui,
Alexander Binder, Emmanuel Müller, and Marius Kloft. Deep one-class classification. In
Internationalconferenceonmachinelearning,pages4393–4402.PMLR,2018.
[27] AdamSantoro,SergeyBartunov,MatthewBotvinick,DaanWierstra,andTimothyLillicrap.
Meta-learning with memory-augmented neural networks. In International conference on
machinelearning,pages1842–1850.PMLR,2016.
[28] BernhardSchölkopf,JohnCPlatt,JohnShawe-Taylor,AlexJSmola,andRobertCWilliamson.
Estimatingthesupportofahigh-dimensionaldistribution. Neuralcomputation,13(7):1443–
1471,2001.
[29] LifengShen,ZhuocongLi,andJamesKwok. Timeseriesanomalydetectionusingtemporal
hierarchical one-class network. Advances in Neural Information Processing Systems, 33:
13016–13026,2020.
12

[30] LifengShen,ZhongzhongYu,QianliMa,andJamesTKwok. Timeseriesanomalydetection
withmultiresolutionensembledecoding. InProceedingsoftheAAAIConferenceonArtificial
Intelligence,volume35,pages9567–9575,2021.
[31] YaSu,YoujianZhao,ChenhaoNiu,RongLiu,WeiSun,andDanPei.Robustanomalydetection
formultivariatetimeseriesthroughstochasticrecurrentneuralnetwork. InProceedingsofthe
25thACMSIGKDDinternationalconferenceonknowledgediscovery&datamining,pages
2828–2837,2019.
[32] YaSu,YoujianZhao,ChenhaoNiu,RongLiu,WeiSun,andDanPei.Robustanomalydetection
formultivariatetimeseriesthroughstochasticrecurrentneuralnetwork. InProceedingsofthe
25thACMSIGKDDinternationalconferenceonknowledgediscovery&datamining,pages
2828–2837,2019.
[33] YaSu,YoujianZhao,ChenhaoNiu,RongLiu,WeiSun,andDanPei.Robustanomalydetection
formultivariatetimeseriesthroughstochasticrecurrentneuralnetwork. InProceedingsofthe
25thACMSIGKDDinternationalconferenceonknowledgediscovery&datamining,pages
2828–2837,2019.
[34] SainbayarSukhbaatar,JasonWeston,RobFergus,etal.End-to-endmemorynetworks.Advances
inneuralinformationprocessingsystems,28,2015.
[35] DavidMJTaxandRobertPWDuin. Supportvectordatadescription. Machinelearning,54:
45–66,2004.
[36] AshishVaswani,NoamShazeer,NikiParmar,JakobUszkoreit,LlionJones,AidanNGomez,
ŁukaszKaiser,andIlliaPolosukhin. Attentionisallyouneed. Advancesinneuralinformation
processingsystems,30,2017.
[37] XixuanWang,DechangPi,XiangyanZhang,HaoLiu,andChangGuo. Variationaltransformer-
based anomaly detection approach for multivariate time series. Measurement, 191:110791,
2022.
[38] Jason Weston, Sumit Chopra, and Antoine Bordes. Memory networks. arXiv preprint
arXiv:1410.3916,2014.
[39] CaimingXiong,StephenMerity,andRichardSocher.Dynamicmemorynetworksforvisualand
textualquestionanswering. InInternationalconferenceonmachinelearning,pages2397–2406.
PMLR,2016.
[40] JiehuiXu,HaixuWu,JianminWang,andMingshengLong. Anomalytransformer: Timeseries
anomalydetectionwithassociationdiscrepancy. arXivpreprintarXiv:2110.02642,2021.
[41] TakehisaYairi,NaoyaTakeishi,TetsuoOda,YutaNakajima,NaokiNishimura,andNoboru
Takata. A data-driven health monitoring method for satellite housekeeping data based on
probabilisticclusteringanddimensionalityreduction. IEEETransactionsonAerospaceand
ElectronicSystems,53(3):1384–1401,2017.
[42] BinZhou,ShenghuaLiu,BryanHooi,XueqiCheng,andJingYe. Beatgan: Anomalousrhythm
detectionusingadversariallygeneratedtimeseries. InIJCAI,volume2019,pages4433–4439,
2019.
[43] HaoyiZhou,ShanghangZhang,JieqiPeng,ShuaiZhang,JianxinLi,HuiXiong,andWancai
Zhang. Informer: Beyondefficienttransformerforlongsequencetime-seriesforecasting. In
ProceedingsoftheAAAIconferenceonartificialintelligence,volume35,pages11106–11115,
2021.
[44] MinfengZhu,PingboPan,WeiChen,andYiYang. Dm-gan: Dynamicmemorygenerative
adversarialnetworksfortext-to-imagesynthesis. InProceedingsoftheIEEE/CVFconference
oncomputervisionandpatternrecognition,pages5802–5810,2019.
[45] BoZong,QiSong,MartinRenqiangMin,WeiCheng,CristianLumezanu,DaekiCho,and
HaifengChen. Deepautoencodinggaussianmixturemodelforunsupervisedanomalydetection.
InInternationalconferenceonlearningrepresentations,2018.
13

A Trainingdetails
WeusetenmemoryitemsforourMEMTOmodel,correspondingtothenumberofclustersinour
K-meansclustering. Todetermineanomalies,wesetthethresholdasthetop-p%ofthecombined
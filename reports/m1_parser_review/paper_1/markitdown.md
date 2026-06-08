|     | Monte |     | Carlo                  | EM for | Deep | Time Series    | Anomaly      |     | Detection |     |     |     |
| --- | ----- | --- | ---------------------- | ------ | ---- | -------------- | ------------ | --- | --------- | --- | --- | --- |
|     |       |     | Franc¸ois-XavierAubet1 |        |      | DanielZu¨gner2 | JanGasthaus1 |     |           |     |     |     |
Abstract
(explicitlyorimplicitly)assumeaccesstonominaldatacan
oftenalsosuccessfullybeappliedtomixeddatabyassum-
Timeseriesdataareoftencorruptedbyoutliersor
ingitisnominal,aslongastheproportionofanomaliesis
| otherkindsofanomalies. |     |     | Identifyingtheanoma- |     |     |     |     |     |     |     |     |     |
| ---------------------- | --- | --- | -------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
1202 ceD 92  ]GL.sc[  1v63441.2112:viXra
lous points can be a goal on its own (anomaly sufficientlysmall.,theyarehoweverbiasedbytrainingon
someanomalousdata.
detection),orameanstoimprovingperformance
| ofothertimeseriestasks(e.g.forecasting). |     |     |     |     | Re- |     |     |     |     |     |     |     |
| ---------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Whilesometimeseriesanomalydetectionmodelrelyonthe
centdeep-learning-basedapproachestoanomaly oneclassclassificationparadigmwhichdoesnotsufferfrom
detectionandforecastingcommonlyassumethat thisassumption(Shenetal.,2020;Carmonaetal.,2021),
theproportionofanomaliesinthetrainingdata
thevastmajorityofthecurrenttimeseriesanomalydetec-
issmallenoughtoignore,andtreattheunlabeled tionmethodsareeitherforecastingmethods(Shipmonetal.,
| data | as coming | from | the nominal | data distribu- |     |     |     |     |     |     |     |     |
| ---- | --------- | ---- | ----------- | -------------- | --- | --- | --- | --- | --- | --- | --- | --- |
2017;Zhaoetal.,2020)orreconstructionmethods(Suetal.,
tion. Wepresentasimpleyeteffectivetechnique 2019;Xuetal.,2018;Parketal.,2018;Zhangetal.,2019).
for augmenting existing time series models so Forecastingmethodsdetectanomaliesasdeviationsofob-
thattheyexplicitlyaccountforanomaliesinthe
servationsfrompredictions,whilereconstructionmethods
training data. By augmenting the training data declare observations that deviate from the reconstruction
| with | a latent | anomaly | indicator | variable | whose |              |                                      |     |     |     |     |     |
| ---- | -------- | ------- | --------- | -------- | ----- | ------------ | ------------------------------------ | --- | --- | --- | --- | --- |
|      |          |         |           |          |       | asanomalous. | Inbothcases,aprobabilisticmodelofthe |     |     |     |     |     |
distributionisinferredwhiletrainingtheunder- observed data is assumed and its parameters are learned.
lyingmodelusingMonteCarloEM,ourmethod However,bytrainingthemodelontheobserveddatawhich
simultaneouslyinfersanomalouspointswhileim-
containsbothnormalandanomalousdatapoints,themodel
provingmodelperformanceonnominaldata. We ultimatelylearnsthewrongdatadistribution. Ehrlichetal.
demonstratetheeffectivenessoftheapproachby
|     |     |     |     |     |     | (2021) propose | an  | approach | to  | make | the model | robust to |
| --- | --- | --- | --- | --- | --- | -------------- | --- | -------- | --- | ---- | --------- | --------- |
combiningitwithasimplefeed-forwardforecast- the anomalous points, still the aim is to learn the distri-
ingmodel. Weinvestigatehowanomaliesinthe bution of both thenormal and theanomalous points. We
trainsetaffectthetrainingofforecastingmodels,
proposetoaddressthisissueusingasimpletechniquebased
whicharecommonlyusedfortimeseriesanomaly onlatentindicatorvariablesthatcanreadilybecombined
detection,andshowthatourmethodimprovesthe withexistingprobabilisticanomalydetectionapproaches.
trainingofthemodel.
Byusinglatentindicatorvariablestoexplicitlyinferwhich
observationsinthetrainingsetareanomalous,wecansub-
sequentlysuitablyaccountfortheanomalousobservations
1.Introduction
whiletrainingtheprobabilisticmodel.
Inmanytimeseriesanomalydetectionapplicationsoneonly
|     |     |     |     |     |     | Probabilistic | models | that | use | latent | (unobserved) | indica- |
| --- | --- | --- | --- | --- | --- | ------------- | ------ | ---- | --- | ------ | ------------ | ------- |
has access to unlabeled data. This data is usually mostly torvariablestoexplicitlydistinguishbetweennominaland
nominalbutmaycontainsome(unlabeled)anomalies. Ex- anomalousdatapointsarewell-establishedinthecontext
amples of this setting are e.g. the widely used anomaly of robust mixture models (e.g. Fraley & Raftery, 1998)
detectionbenchmarksSMAP,MSL(Hundmanetal.,2018), and classical time series models (e.g. Wang et al., 2018).
andSMD(Suetal.,2019).
However,thesetechniqueshavenotyetbeenutilizedinthe
contextofrecentadvancesindeepanomalydetectionand
This“true”unsupervisedsettingwithmixeddatacanbecon-
|     |     |     |     |     |     | time series | modeling, | presumably |     | due | to the | (perceived) |
| --- | --- | --- | --- | --- | --- | ----------- | --------- | ---------- | --- | --- | ------ | ----------- |
trastedwiththe“nominal-only”setting,whereoneassumes
|                             |     |     |     |                           |     | increased                 | complexity | of  | the required           |     | probabilistic | infer- |
| --------------------------- | --- | --- | --- | ------------------------- | --- | ------------------------- | ---------- | --- | ---------------------- | --- | ------------- | ------ |
| accessto“clean”nominaldata. |     |     |     | Inpractice,techniquesthat |     |                           |            |     |                        |     |               |        |
|                             |     |     |     |                           |     | enceandtrainingprocedure. |            |     | Weshowthatcombiningla- |     |               |        |
1AWSAILabs2TechnicalUniversityofMunich.Correspon-
|     |     |     |     |     |     | tent anomaly | indicators |     | with a | Monte | Carlo Expectation- |     |
| --- | --- | --- | --- | --- | --- | ------------ | ---------- | --- | ------ | ----- | ------------------ | --- |
denceto:Franc¸ois-XavierAubet<aubetf@amazon.com>. Maximization(EM)(Wei&Tanner,1990)trainingproce-
dure,resultsinasimpleyeteffectivetechniquethatcanbe
38th
| Proceedings | of the | International |     | Conference | on Machine |     |     |     |     |     |     |     |
| ----------- | ------ | ------------- | --- | ---------- | ---------- | --- | --- | --- | --- | --- | --- | --- |
combinedwith(almost)allexistingdeepanomalydetection
Learning,PMLR139,2021.Copyright2021bytheauthor(s).

MonteCarloEMforDeepTimeSeriesAnomalyDetection
y+
andtimeseriesforecastingtechniques. of p+(·) only from by inferring z ∼ pz(z ) on
|     |             |                   |     |     |              |     |        |                 |     | 1:T                             |     | 1:T | 1:T |
| --- | ----------- | ----------------- | --- | --- | ------------ | --- | ------ | --------------- | --- | ------------------------------- | --- | --- | --- |
|     |             |                   |     |     |              |     |        | thetrainingset. |     | Thiswaywecantrainthemodelonlyon |     |     |     |
| We  | demonstrate | the effectiveness |     | of  | our approach |     | with a |                 |     |                                 |     |     |     |
theobservedpointsthatarenormal,theonesthatareequal
simplemodelforanomalydetectionontheYahooanomaly
|                                                        |     |     |     |     |     |     |     | toy+ | . Dependingonthemodel,theanomalouspointscan |     |     |     |     |
| ------------------------------------------------------ | --- | --- | --- | --- | --- | --- | --- | ---- | ------------------------------------------- | --- | --- | --- | --- |
| detectiondatasetandontheelectricitydatasetforforecast- |     |     |     |     |     |     |     |      | 1:T                                         |     |     |     |     |
betreatedasmissingorthenormalpointcanbeinferred.
ingfromanoisytrainingset.
3.1.Models
2.Background
Eachofthethreelatenttimeseriesismodeledwithaprob-
Fornon-timeseriesdata,onecommonapproachofformal- aparametrizedmodelp+
|     |     |     |     |     |     |     |     | abilisticmodel: |     |     |     | ofthenominal |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --------------- | --- | --- | --- | ------------ | --- |
θ
izingthenotionofanomaliesistoassumethattheobserved datay+ ,afixedmodelp− tomodeltheanomalousdata
1:T
data is generated by a mixture model (Ruff et al., 2020): y− ,andamodelpz oftheindicatortimeseriesz .
|     |     |     |     |     |     |     |     | 1:T |     |     |     |     | 1:T |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
eachobservationxisdrawnfromthemixturedistribution
αp+(x)+(1−α)p−(x),wherep+(x)isthedis-
p(x) =
|     |     |     |     |     |     |     |     | NominalDataModel |     |     | Manyexistingdeepanomalydetec- |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | --- | ----------------------------- | --- | --- |
tributionofthenominaldataandp−(x)theanomalousdata
tionmethodsaimtomodelthenominaldata(e.g.(Shipmon
distribution. Typicallyoneassumesaflexibleparametrized et al., 2017; Zhao et al., 2020; Su et al., 2019; Xu et al.,
distributionforp+andabroad,unspecificdistributionfor
2018;Parketal.,2018;Zhangetal.,2019;Ehrlichetal.,
p−(e.g.auniformdistributionovertheextentofthedata).
2021)),andanyofthemcanbeusedtomodely+,thelatent
This mixture distribution can equivalently be written us- nominaltimeseries. Ourmethodisagnostictothetypeof
ingabinaryindicatorlatentvariableztakingvalue0with modelused,sothatitcanbecombinedwithanyprobabilis-
tictimeseriesmodel,beitadeeporshallowprobabilistic
| probability |     | p(z = 0) | = α | and value | 1 with | probability |     |     |     |     |     |     |     |
| ----------- | --- | -------- | --- | --------- | ------ | ----------- | --- | --- | --- | --- | --- | --- | --- |
p(z =1)=1−α,andspecifyingtheconditionaldistribu- forecastingmethod,areconstructionmethod,oranyother
| tion |     |         |          |     |     |     |     | typeofmodel.                                     |     | Wecallthemodelofthelatentnormaltime |     |     |     |
| ---- | --- | ------- | -------- | --- | --- | --- | --- | ------------------------------------------------ | --- | ----------------------------------- | --- | --- | --- |
|      |     |         | (cid:40) |     |     |     |     | seriesp+,whichisparametrisedbyasetofparametersθ. |     |                                     |     |     |     |
|      |     |         | p+(x)    | ifz | =0  |     |     |                                                  |     |                                     |     |     |     |
|      |     | p(x|z)= |          |     |     |     | (1) |                                                  | θ   |                                     |     |     |     |
p−(x)
ifz =1, In our experiments we demonstrate the general setup by
|                                                    |     |                                        |     |     |     |     |     | modelingp+(y    |        | + )withasimpledeepprobabilisticfore- |          |            |           |
| -------------------------------------------------- | --- | -------------------------------------- | --- | --- | --- | --- | --- | --------------- | ------ | ------------------------------------ | -------- | ---------- | --------- |
|                                                    |     | (cid:80) p(x|z)p(z)=αp+(x)+(1−α)p−(x). |     |     |     |     |     |                 |        | 1 :T                                 |          |            |           |
| sothatp(x)=                                        |     |                                        |     |     |     |     |     |                 |        |                                      | p(y+     |            |           |
|                                                    |     | z                                      |     |     |     |     |     | casting         | model. | We decompose                         |          | ) into the | telescop- |
| Inthissetup,anomalydetectioncanbeperformedbyinfer- |     |                                        |     |     |     |     |     |                 |        |                                      |          | 1:T        |           |
|                                                    |     |                                        |     |     |     |     |     | ingproductp(y+) |        | (cid:81)T                            | p(y+ |y+ |            |           |
ringtheposteriordistributionp(z|x)(andthresholdingitif )and,makinganl-th
|     |     |     |     |     |     |     |     |     |     | 0 t=0 | t+1 | t:0 |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ----- | --- | --- | --- |
orderMarkovassumption,approximateitwithanetwork
| ahardchoiceisdesired). |     |     | Yetanotherwayofrepresenting |     |     |     |     |     |        |          |     |                    |     |
| ---------------------- | --- | --- | --------------------------- | --- | --- | --- | --- | --- | ------ | -------- | --- | ------------------ | --- |
|                        |     |     |                             |     |     |     |     | p(y | + |y + | )=N(f (y | ),g | (y ))takingasinput |     |
the same model is generatively: first, draw y+ ∼ p+(·), t +1 t :t−l θ t:t−l θ t:t−l
| y−  | p−(·), |           |               |       |          |             |     | thelastltimepoints. |     |     |     |     |     |
| --- | ------ | --------- | ------------- | ----- | -------- | ----------- | --- | ------------------- | --- | --- | --- | --- | --- |
|     | ∼      | and z     | ∼ Bernoulli(1 |       | − α),    | and then    | set |                     |     |     |     |     |     |
| x = | I[z =  | 0]y+ +I[z | =             | 1]y−, | i.e. the | observation | x   |                     |     |     |     |     |     |
isequaltoy+ifitisnominal(z =1)andequaltoy−oth- AnomalousDataModel Asimplemodelcanbeusedto
|     |     |     |     |     |     |     |     | model | p−, | it does not need | to take | into account | the time |
| --- | --- | --- | --- | --- | --- | --- | --- | ----- | --- | ---------------- | ------- | ------------ | -------- |
erwise. Introducingtheadditionallatentvariablesy+and
y−isunnecessaryintheIIDsetting,butbecomesusefulin componentastherearetypicallyfewanomalouspoints. It
canbemodeledwithamixtureofGaussiandistributionsfor
thetimeseriessettingdescribednext.
example,withtheriskofover-fittingtothefewanomalies
Intimeseriessetting,wherethetheobservationsaretime
|     |     |     |     |     |     |     |     | ofthetrainset. |     | Wesimplymodelp−withauniformdistri- |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | -------------- | --- | ---------------------------------- | --- | --- | --- |
seriesx 1:T = x 1 ,...,x T thatexhibittemporaldependen- butionoverthedomainofthetrainingdata,notassuming
cies,andanomaliesaretimepointsorregionswithinthese
anyprioronthekindofanomaliesthatwemayexpect.
| time | series, | we have | one anomaly |     | indicator | variable | z   |     |     |     |     |     |     |
| ---- | ------- | ------- | ----------- | --- | --------- | -------- | --- | --- | --- | --- | --- | --- | --- |
t
| corresponding |      | to each  | time | point          | x t . Like | before,       | the |                       |     |     |                         |     |     |
| ------------- | ---- | -------- | ---- | -------------- | ---------- | ------------- | --- | --------------------- | --- | --- | ----------------------- | --- | --- |
|               |      |          |      |                |            |               |     | AnomalyIndicatorModel |     |     | Wemodelthelatentanomaly |     |     |
| nominal       | data | is drawn | from | a parametrized |            | probabilistic |     |                       |     |     |                         |     |     |
indicatorwithaHiddenMarkovModel(HMM)withtwo
|         | p+(y       | ),      |               |            |        |           |        |               |     |                                        |     |     |     |
| ------- | ---------- | ------- | ------------- | ---------- | ------ | --------- | ------ | ------------- | --- | -------------------------------------- | --- | --- | --- |
| model   |            | 1:T and | the anomalies |            | are    | generated | from   |               |     |                                        |     |     |     |
|         | θ          |         |               |            |        |           |        | states,statez |     | t = 0correspondstothepointbeingnormal  |     |     |     |
| a fixed | model      | p−(y    | ). For        | time       | series | data, the | mix-   |               |     |                                        |     |     |     |
|         |            | 1:T     |               |            |        |           |        | andstatez     |     | =1correspondstothepointbeinganomalous. |     |     |     |
| ture    | data model | then    | amounts       | to drawing |        | y+ ∼      | p+(·), |               |     | t                                      |     |     |     |
1:T
y− p−(·), pz(z AnykindoftimeseriesmodelparameterizingaBernoulli
|     | ∼         | and z  | 1:T ∼ | 1:T | ), and | setting | x t = |                                                     |     |     |     |     |     |
| --- | --------- | ------ | ----- | --- | ------ | ------- | ----- | --------------------------------------------------- | --- | --- | --- | --- | --- |
| 1:T |           |        |       |     |        |         |       | distributioncanbeusedtomodelthelatentanomalyindica- |     |     |     |     |     |
| I[z | =0]y++I[z | =1]y−. |       |     |        |         |       |                                                     |     |     |     |     |     |
| t   |           | t t    | t     |     |        |         |       | tors,wepickanHMMasitencodesbasictimedependencies    |     |     |     |     |     |
whilestayingasimplemodel.
3.Method
Ifitisavailable,priorknowledgeaboutthedatasetcanbe
Forecastingorreconstructionmodelsaredesignedtolearn usedtoinitialisethetransitionmatrix. Theexpectedlength
a model of p+(·) but are typically trained directly on the ofanomalouswindowscanbeusedtoinitialisethetransition
observedtimeseriesx . Weproposetolearnthemodel probabilityp(z = 1|z = 1). Theexpectedpercentage
|     |     |     | 1:T |     |     |     |     |     |     | t+1 | t   |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

MonteCarloEMforDeepTimeSeriesAnomalyDetection
ofanomalouspointsinthedatasetcanbeusedtoinitialise Dependingonthechoiceofmodelforp−,onecanupdateit
thetransitionprobabilityp(z =1|z =0). usingthepointsthataresampledascomingfromy− .
|     |     |     |     | t+1 | t   |     |     |     |     |     |     | 1:T |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
WecanupdatethetransitionmatrixoftheHMMwiththe
3.2.Training
|     |     |     |     |     |     |     |     | classicalM-step. |     | Theaveragenumberoftransitionsfrom |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ---------------- | --- | --------------------------------- | --- | --- | --- |
onestatetothenextinthesamplesfrompz(z
Our training procedure follows Monte Carlo EM (Wei & 1:T )become
Tanner, 1990). In the E-step we infer pz(z ). In the thenewtransitionprobabilities.
1:T
pz(z
| M-step | we  | sample from |     | ),  | using these | samples | to  |     |     |     |     |     |     |
| ------ | --- | ----------- | --- | --- | ----------- | ------- | --- | --- | --- | --- | --- | --- | --- |
1:T
| updatep+andthetransitionmatrixoftheHMM.Algorithm |     |     |     |     |     |     |     | 3.3.Inference |     |     |     |     |     |
| ------------------------------------------------ | --- | --- | --- | --- | --- | --- | --- | ------------- | --- | --- | --- | --- | --- |
θ
1sketchesthisprocedure.
Atinferencetime,weproposetousetheHMMtoperform
filteringonzandinferifincomingpointsaremorelikelyto
Algorithm1MonteCarloEMforLatentAnomalyIndicator
|        |                     |     |     |                     |     |     |     | bedrawnfromp+ |     | orp−. | Ifanincomingpointx |          |     |
| ------ | ------------------- | --- | --- | ------------------- | --- | --- | --- | ------------- | --- | ----- | ------------------ | -------- | --- |
|        |                     |     |     |                     |     |     |     |               |     |       |                    | t ismore |     |
| Input: | Observedtimeseriesx |     |     | ,modeltobetrainedp+ |     |     |     |               |     |       |                    |          |     |
1:T θ likely to be coming from p− it can be treated as missing
| fore∈{1,...,numb |     |     | epochs}do |     |     |     |     |             |      |          |         |                 |      |
| ---------------- | --- | --- | --------- | --- | --- | --- | --- | ----------- | ---- | -------- | ------- | --------------- | ---- |
| 1                |     |     |           |     |     |     |     | or replaced | with | a sample | from p+ | or by its mode. | This |
θt
|     | // E-step: |     |     |     |     |     |     |     |     |     |     |     |     |
| --- | ---------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
wayweensurethatthetrainedmodelisonlyusedonpoints
|     | →inferpz(z       |     | )          |     |     |     |     |              |     |     |     |     |     |
| --- | ---------------- | --- | ---------- | --- | --- | --- | --- | ------------ | --- | --- | --- | --- | --- |
| 2   |                  | 1:T |            |     |     |     |     | comingfromy+ |     | .   |     |     |     |
|     | // M-step:       |     |            |     |     |     |     |              |     | 1:T |     |     |     |
| 3   | fors∈{1,...,numb |     | samples}do |     |     |     |     |              |     |     |     |     |     |
4.Experiments
|     | →sampleindicatortimeseriesz |         |           |       | frompz(z |       | )   |                                                   |     |     |     |     |     |
| --- | --------------------------- | ------- | --------- | ----- | -------- | ----- | --- | ------------------------------------------------- | --- | --- | --- | --- | --- |
| 4   |                             |         |           |       | s        |       | 1:T |                                                   |     |     |     |     |     |
| 5   | →                           | perform | one epoch | of p+ | on x     | where | the |                                                   |     |     |     |     | 1   |
|     |                             |         |           |       | θ        | ¬zs   |     | Wemakeourcodeavailablewithanillustrationnotebook. |     |     |     |     |     |
pointsatsampledanomalousindicesarereplaced
6 end
7 →updatethetransitionmatrixoftheHMM Model Weevaluateourapproachwithasimpleforecast-
ingmodelonbothanomalydetectionandforecastingtasks.
8 end
Weshowtheperformanceofthemodelwhentrainedina
standardwayandwhentrainedwithourprocedure,which
3.2.1.E-STEP we call our procedure Latent Anomaly Indicator (LAI).
| Weinferpz(z |     |     |     |     |     |     |     | WeuseasimpleMulti-LayerPerceptron(MLP)modelto |     |     |     |     |     |
| ----------- | --- | --- | --- | --- | --- | --- | --- | --------------------------------------------- | --- | --- | --- | --- | --- |
1:T )byusingthestandardforward-backward
parametrisethemeanandthevarianceofapredictiveGaus-
algorithmforHMMs,usingthefollowingdistributions:
|     |     |     |             |     |     |     |     | siandistribution. |     | Ittakesasinputthelast25points. |     |     |     |
| --- | --- | --- | ----------- | --- | --- | --- | --- | ----------------- | --- | ------------------------------ | --- | --- | --- |
|     |     | p(x | |z =0)=p+(x |     | )   |     | (2) |                   |     |                                |     |     |     |
|     |     |     | t t         |     | t   |     |     |                   |     |                                |     |     |     |
θ
=1)=p−(x
p(x t |z t t ) (3) Datasets Fortheanomalydetectionevaluation,weusethe
andp(z |z )isgivenbytheHMMtransitionmatrix. Yahoodataset,publishedbyYahoolabs.2 Itconsistsof367
|     | t+1 | t   |     |     |     |     |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
realandsynthetictimeseries,dividedintofoursubsets(A1-
3.2.2.M-STEP A4)withvaryinglevelofdifficulty. Thelengthoftheseries
|     |     |     |     |     |     |     |     | varyfrom700to1700observations. |     |     |     | Labelsareavailablefor |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------------------------ | --- | --- | --- | --------------------- | --- |
Wewanttotrainp+(·)onlyfromy+
.Asmostmodelsmay alltheseries. Weusethelast50%ofthetimepointsofeach
1:T
| notallowforananalyticalupdateusingx |     |     |     |     |     | andz | ,we |                                                     |     |     |     |     |     |
| ----------------------------------- | --- | --- | --- | --- | --- | ---- | --- | --------------------------------------------------- | --- | --- | --- | --- | --- |
|                                     |     |     |     |     | 1:T |      | 1:T | ofthetimeseriesastestset,like(Renetal.,2019)did,and |     |     |     |     |     |
proposetoaMonteCarloapproximationoftheexpectation
|           |     |                               |     |     |     |     |     | splittherestin40%trainingand10%validationset.      |     |     |     |     | We  |
| --------- | --- | ----------------------------- | --- | --- | --- | --- | --- | -------------------------------------------------- | --- | --- | --- | --- | --- |
| underpz(z |     | Wedrawmultiplesamplesfrompz(z |     |     |     |     |     |                                                    |     |     |     |     |     |
|           |     | ).                            |     |     |     |     | )   |                                                    |     |     |     |     |     |
|           |     | 1:T                           |     |     |     |     | 1:T | evaluatetheperformanceofthemodelusingtheadjustedF1 |     |     |     |     |     |
givinguspossiblenormalpointsonwhichp+canbetrained.
|                                                   |     |     |     |     |     | θ   |     | scoreproposedbyXuetal.(2018)andsubsequentlyused |     |     |     |     |     |
| ------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | ----------------------------------------------- | --- | --- | --- | --- | --- |
| Eachpathsampledgivesusasetofobservedpointsthatcan |     |     |     |     |     |     |     | inotherwork.                                    |     |     |     |     |     |
beconsideredascomingfromthenormaldatadistribution
p+. Wemaximisetheprobabilityofthesepointsunderp+, In addition, we evaluate the method on forecasting tasks
θ
treatingthepointscomingfromp−pointsasmissing. using the commonly used electricity dataset (Dheeru &
|           |     |               |     |       |         |         |     | Taniskidou, | 2017),                                  | composed | of 370 | time series of | 133k |
| --------- | --- | ------------- | --- | ----- | ------- | ------- | --- | ----------- | --------------------------------------- | -------- | ------ | -------------- | ---- |
| Depending |     | on the choice | of  | model | for p+, | one may | not |             |                                         |          |        |                |      |
|           |     |               |     |       | θ       |         |     | pointseach. | Giventhelengthofthedataset,wesub-sample |          |        |                |      |
beabletosimplyignoreanomalouspointsandtheywould
|                  |     |     |                                    |     |     |     |     | it by a factor |     | 10. We select | the last | 50% of the points | of  |
| ---------------- | --- | --- | ---------------------------------- | --- | --- | --- | --- | -------------- | --- | ------------- | -------- | ----------------- | --- |
| havetobeimputed. |     |     | Fordeepforecastingorreconstruction |     |     |     |     |                |     |               |          |                   |     |
modelsforexamplethemodelhastobegivenaninputfor 1https://github.com/Francois-Aubet/gluon-
|                |     |                                   |     |     |     |     |     | ts/blob/monte           |     | carlo | em masking          | notebook/src/ |     |
| -------------- | --- | --------------------------------- | --- | --- | --- | --- | --- | ----------------------- | --- | ----- | ------------------- | ------------- | --- |
| eachtimepoint. |     | Inthesecases,weproposetoimputethe |     |     |     |     |     |                         |     |       |                     |               |     |
|                |     |                                   |     |     |     |     |     | gluonts/nursery/anomaly |     |       | detection/Monte-Car |               |     |
pointwiththeforecastorreconstructionobtainedfromp+
|     |     |     |     |     |     |     | θ   | lo-EM-for-Time-Series-Anomaly-Detection-de |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | ------------------------------------------ | --- | --- | --- | --- | --- |
weusep+
| atthelastM-step. |     | Thisway, |     |     | toinferthetime |     |     | mo-notebook.ipynb |     |     |     |     |     |
| ---------------- | --- | -------- | --- | --- | -------------- | --- | --- | ----------------- | --- | --- | --- | --- | --- |
θ
pointsofy + thatwerenotobserved. Withthismethodwe 2https://webscope.sandbox.yahoo.com/catal
1 :T
canrecoverthefully+ timeseriesandtrainp+onit. og.php?datatype=s&did=70
|     |     |     | 1:T |     |     | θ   |     |     |     |     |     |     |     |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

MonteCarloEMforDeepTimeSeriesAnomalyDetection
Table1.F1scoreonthedifferentsubsetsoftheYahoodataset.
|     |     |     |     | Model                           |     | A1    | A2    | A3 A4           |     |
| --- | --- | --- | --- | ------------------------------- | --- | ----- | ----- | --------------- | --- |
|     |     |     |     | MLP                             |     | 33.64 | 53.28 | 63.25 47.30     |     |
|     |     |     |     | MLP+LAI                         |     | 41.84 | 87.26 | 87.91 61.62     |     |
|     |     |     |     | InadditiontotheimprovedF1score, |     |       |       | wecomparethein- |     |
ferredanomalouspointsonthetrainingsetwiththeactual
(a)ThefitofasimpleMLPwithoutLAI. labeledanomalouspoints.Table2showstheF1scoreonthe
trainingsetwhenusingtheanomalyindicatorasanomaly
score. Weobservethatourmethodallowstofindaccurately
|     |     |     |     | theanomaliespresentinthetrainingset. |     |     |     | Whilethetraining |     |
| --- | --- | --- | --- | ------------------------------------ | --- | --- | --- | ---------------- | --- |
andtestsetsaredifferent,weproposethatthehigherF1on
|     |     |     |     | the train | set is | due to the | fact that | the model can | use the |
| --- | --- | --- | --- | --------- | ------ | ---------- | --------- | ------------- | ------- |
wholetrainingsettoinferifapointisanomalous,andnot
onlythepastpoints.
Table2.F1scoreonthetrainingsetthedifferentsubsetsofthe
(b)ThefitofasimpleMLPwithLAI. Yahoodatasetusingtheinferredp(z =1)asanomalyscore.
t
|     |     |     |     | Model   |     | A1    | A2    | A3 A4       |     |
| --- | --- | --- | --- | ------- | --- | ----- | ----- | ----------- | --- |
|     |     |     |     | MLP+LAI |     | 59.48 | 94.02 | 81.89 73.77 |     |
(c)Thetimeseriesoflatentanomalyindicatorp(z =1). 4.3.Forecastingusingacorruptedtrainset
t
Figure1.WefitaMLPonthissimplesynthetictimeserieswith Ourmethodcanbeusedmoregenerallytotrainaforecast-
anomalies.(a)showsthefitofthemodeltrainedinaconventional ing model on a forecasting dataset containing anomalies.
way,(b)showsthefitofthemodeltrainedasweproposeto,(c) Wetaketheelectricityforecastingdatasetandinjectpoint
showtheinferredp(z 1:T )distributionattheendofthetraining. outliersinthetrainingsetsothatabout0.4%ofthetraining
|     |     |     |     | pointhaveanaddedorsubtractedspike. |     |             |        | Table3showsthe  |         |
| --- | --- | --- | --- | ---------------------------------- | --- | ----------- | ------ | --------------- | ------- |
|     |     |     |     | mean absolute                      |     | error (MAE) | on the | test set in the | setting |
wheretheoriginaltrainsetisusedandinthesettingwhere
| eachtimeseriesfortesting. |     | Wescaleeachtimeseriesusing |     |                         |     |     |                         |     |     |
| ------------------------- | --- | -------------------------- | --- | ----------------------- | --- | --- | ----------------------- | --- | --- |
|                           |     |                            |     | thenoisytrainsetisused. |     |     | Weseethatusingourmethod |     |     |
themedianandinter-quartilerangeonthetrainset.
|     |     |     |     | allows to | reduce | significantly | the | increase in error | from |
| --- | --- | --- | --- | --------- | ------ | ------------- | --- | ----------------- | ---- |
theoutliersinthetrainingset,only0.0146increaseinthe
4.1.Visualizationonsyntheticdata
meanabsoluteerrorversus0.0542whentrainingthemodel
| Figure1visualizestheadvantageofthemethodonasimple |                  |                |            | normally. |     |     |     |     |     |
| ------------------------------------------------- | ---------------- | -------------- | ---------- | --------- | --- | --- | --- | --- | --- |
| sinusoidal                                        | time series with | the simple MLP | for p+. We |           |     |     |     |     |     |
θ
| generateasynthetictimeseriesandinjectoutliersinit. |     |     | We  |     |     |     |     |     |     |
| -------------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Table3.MAEonelectricitywithandwithoutinjectingpointout-
observethatourapproachallowstotrainthemodelp+while
|     |     |     | θ   | liersinthetrainset |     |     |     |     |     |
| --- | --- | --- | --- | ------------------ | --- | --- | --- | --- | --- |
ignoringtheoutliersinthedata,whereastheoutliersheavily
|           |                   |                 |            | Model |     | electricity | electricity+outliers |     |     |
| --------- | ----------------- | --------------- | ---------- | ----- | --- | ----------- | -------------------- | --- | --- |
| influence | the model trained | conventionally. | We observe |       |     |             |                      |     |     |
from figure 1c that the model is able to infer accurately MLP 0.1551 0.2092
whichofthetrainingpointsarelikelytobeanomalous. MLP+LAI 0.1558 0.1704
4.2.Timeseriesanomalydetection
5.Conclusion
Table1showstheF1scoreofthemodelwithandwithout
LAIonthedifferentsubsetsoftheYahoodataset. Wetrain We present LAI, a method that can be used to wrap any
one MLP on each of the time series and average the F1 probabilistictimeseriesmodeltoperformanomalydetec-
scores obtained on the different time series of the subset. tionwithoutbeingimpactedbyunlabeledanomaliesinthe
Weobservethatusingourapproachgreatlyimprovesthe training set. We present the details of the approach and
performanceofthemodel. proposepreliminaryempiricalresultsoncommonlyused

MonteCarloEMforDeepTimeSeriesAnomalyDetection
| publicbenchmarkdatasets. | Theapproachseemstogreatly |           |                |
| ------------------------ | ------------------------- | --------- | -------------- |
| help both                | for anomaly detection     | tasks and | for training a |
forecastingmodelonacontaminatedtrainingset.
Onecanextendthisworkbywrappingotherbiggermodels
suchasOmniAnomaly(Suetal.,2019)orstate-of-the-art
| forecastingmodels(Benidisetal.,2020). |     | Finally,withour |     |
| ------------------------------------- | --- | --------------- | --- |
currentmethodatinferencetime,onehastodecideateach
incomingpointifitistobereplacedornot,onecoulduse
particleswhichwouldmimictheMonteCarloapproachof
thetrainingtime.

MonteCarloEMforDeepTimeSeriesAnomalyDetection
References Su, Y., Zhao, Y., Niu, C., Liu, R., Sun, W., and Pei, D.
|             |     |              |     |               |     |             |       | Robust                                   | anomaly | detection | for | multivariate |     | time series |
| ----------- | --- | ------------ | --- | ------------- | --- | ----------- | ----- | ---------------------------------------- | ------- | --------- | --- | ------------ | --- | ----------- |
| Benidis,    | K., | Rangapuram,  | S.  | S., Flunkert, |     | V.,         | Wang, |                                          |         |           |     |              |     |             |
|             |     |              |     |               |     |             |       | throughstochasticrecurrentneuralnetwork. |         |           |     |              |     | InProceed-  |
| B., Maddix, |     | D., Turkmen, |     | C., Gasthaus, |     | J., Bohlke- |       |                                          |         |           |     |              |     |             |
ingsofthe25thACMSIGKDDInternationalConference
| Schneider, |     | M., Salinas, | D., | Stella, | L., et | al. Neural |     |     |     |     |     |     |     |     |
| ---------- | --- | ------------ | --- | ------- | ------ | ---------- | --- | --- | --- | --- | --- | --- | --- | --- |
onKnowledgeDiscovery&DataMining,pp.2828–2837,
| forecasting: |     | Introductionandliteratureoverview. |     |     |     |     | arXiv |     |     |     |     |     |     |     |
| ------------ | --- | ---------------------------------- | --- | --- | --- | --- | ----- | --- | --- | --- | --- | --- | --- | --- |
2019.
preprintarXiv:2004.10240,2020.
|          |     |               |           |     |         |           |     | Wang, H.,   | Li, H., | Fang, | J., and | Wang,      | H. Robust | Gaus-  |
| -------- | --- | ------------- | --------- | --- | ------- | --------- | --- | ----------- | ------- | ----- | ------- | ---------- | --------- | ------ |
| Carmona, | C., | Aubet, F.-X., | Flunkert, |     | V., and | Gasthaus, |     |             |         |       |         |            |           |        |
|          |     |               |           |     |         |           |     | sian Kalman | filter  | with  | outlier | detection. | IEEE      | Signal |
J. Neuralcontextualanomalydetectionfortimeseries.
ProcessingLetters,25(8):1236–1240,2018.
2021.
|                             |     |     |     |              |     |            |     | Wei, G. C. | and Tanner, | M.  | A.  | A monte | carlo | implemen- |
| --------------------------- | --- | --- | --- | ------------ | --- | ---------- | --- | ---------- | ----------- | --- | --- | ------- | ----- | --------- |
| Dheeru,D.andTaniskidou,E.K. |     |     |     | electricity: |     | hourlytime |     |            |             |     |     |         |       |           |
tationoftheemalgorithmandthepoorman’sdataaug-
seriesoftheelectricityconsumptionof370customers, mentationalgorithms. JournaloftheAmericanstatistical
2017. URLhttp://archive.ics.uci.edu/ml.
Association,85(411):699–704,1990.
| Ehrlich, | E., Callot, | L., | and Aubet, | F.-X. | Spliced | binned- |     |     |     |     |     |     |     |     |
| -------- | ----------- | --- | ---------- | ----- | ------- | ------- | --- | --- | --- | --- | --- | --- | --- | --- |
Xu,H.,Chen,W.,Zhao,N.,Li,Z.,Bu,J.,Li,Z.,Liu,Y.,
pareto distribution for robust modeling ofheavy-tailed Zhao,Y.,Pei,D.,Feng,Y.,etal. Unsupervisedanomaly
timeseries. arXivpreprintarXiv:2106.10952,2021. detectionviavariationalauto-encoderforseasonalkpis
|                          |     |     |                  |     |     |     |       | inwebapplications. |     | InProceedingsofthe2018World |     |     |     |     |
| ------------------------ | --- | --- | ---------------- | --- | --- | --- | ----- | ------------------ | --- | --------------------------- | --- | --- | --- | --- |
| Fraley,C.andRaftery,A.E. |     |     | Howmanyclusters? |     |     |     | Which |                    |     |                             |     |     |     |     |
WideWebConference,pp.187–196,2018.
| clustering | method? |     | Answers | via model-based |     |     | cluster |     |     |     |     |     |     |     |
| ---------- | ------- | --- | ------- | --------------- | --- | --- | ------- | --- | --- | --- | --- | --- | --- | --- |
analysis. TheComputerJournal,41(8):578–588,1998. Zhang, C., Song, D., Chen, Y., Feng, X., Lumezanu, C.,
|          |     |               |     |          |     |          |     | Cheng, | W., Ni, | J., Zong, | B., | Chen, | H., and | Chawla, |
| -------- | --- | ------------- | --- | -------- | --- | -------- | --- | ------ | ------- | --------- | --- | ----- | ------- | ------- |
| Hundman, | K., | Constantinou, | V., | Laporte, | C., | Colwell, | I., |        |         |           |     |       |         |         |
N.V.ADeepNeuralNetworkforUnsupervisedAnomaly
andSoderstrom,T. Detectingspacecraftanomaliesus- Detection and Diagnosis in Multivariate Time Series
| inglstmsandnonparametricdynamicthresholding. |     |     |     |     |     |     | In  |                   |     |     |          |            |     |            |
| -------------------------------------------- | --- | --- | --- | --- | --- | --- | --- | ----------------- | --- | --- | -------- | ---------- | --- | ---------- |
|                                              |     |     |     |     |     |     |     | Data. Proceedings |     | of  | the AAAI | Conference |     | on Artifi- |
Proceedingsofthe24thACMSIGKDDinternationalcon- cialIntelligence,33:1409–1416,jul2019. ISSN2374-
ferenceonknowledgediscovery&datamining,pp.387–
|     |     |     |     |     |     |     |     | 3468. | doi: 10.1609/aaai.v33i01.33011409. |     |     |     |     | URL |
| --- | --- | --- | --- | --- | --- | --- | --- | ----- | ---------------------------------- | --- | --- | --- | --- | --- |
395,2018.
www.aaai.orghttps://aaai.org/ojs/ind
ex.php/AAAI/article/view/3942.
Park,D.,Hoshi,Y.,andKemp,C.C.Amultimodalanomaly
detectorforrobot-assistedfeedingusinganlstm-based Zhao,H.,Wang,Y.,Duan,J.,Huang,C.,Cao,D.,Tong,Y.,
| variationalautoencoder. |     |     | IEEERoboticsandAutomation |     |     |     |     |                                  |     |     |     |     |                   |     |
| ----------------------- | --- | --- | ------------------------- | --- | --- | --- | --- | -------------------------------- | --- | --- | --- | --- | ----------------- | --- |
|                         |     |     |                           |     |     |     |     | Xu,B.,Bai,J.,Tong,J.,andZhang,Q. |     |     |     |     | Multivariatetime- |     |
Letters,3(3):1544–1551,2018. series anomaly detection via graph attention network.
arXivpreprintarXiv:2009.02040,2020.
| Ren, H.,                            | Xu, | B., Wang, | Y., Yi, | C., Huang, |               | C., Kou,    | X., |     |     |     |     |     |     |     |
| ----------------------------------- | --- | --------- | ------- | ---------- | ------------- | ----------- | --- | --- | --- | --- | --- | --- | --- | --- |
| Xing,T.,Yang,M.,Tong,J.,andZhang,Q. |     |           |         |            |               | Time-series |     |     |     |     |     |     |     |     |
| anomalydetectionserviceatmicrosoft. |     |           |         |            | InProceedings |             |     |     |     |     |     |     |     |     |
ofthe25thACMSIGKDDInternationalConferenceon
| KnowledgeDiscovery&DataMining, |     |     |     |     | pp.3009–3017, |     |     |     |     |     |     |     |     |     |
| ------------------------------ | --- | --- | --- | --- | ------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
2019.
Ruff,L.,Kauffmann,J.R.,Vandermeulen,R.A.,Montavon,
G.,Samek,W.,Kloft,M.,Dietterich,T.G.,andMu¨ller,
K.-R. Aunifyingreviewofdeepandshallowanomaly
| detection. | arXivpreprintarXiv:2009.11732,2020. |     |     |     |     |     |     |     |     |     |     |     |     |     |
| ---------- | ----------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
Shen,L.,Li,Z.,andKwok,J.Timeseriesanomalydetection
| usingtemporalhierarchicalone-classnetwork. |     |     |     |     |     | Advances |     |     |     |     |     |     |     |     |
| ------------------------------------------ | --- | --- | --- | --- | --- | -------- | --- | --- | --- | --- | --- | --- | --- | --- |
inNeuralInformationProcessingSystems,33,2020.
| Shipmon, | D. T., | Gurevitch,  | J. M.,  | Piselli,   | P.  | M., and   | Ed- |     |     |     |     |     |     |     |
| -------- | ------ | ----------- | ------- | ---------- | --- | --------- | --- | --- | --- | --- | --- | --- | --- | --- |
| wards,   | S. T.  | Time series | anomaly | detection; |     | detection |     |     |     |     |     |     |     |     |
ofanomalousdropswithlimitedfeaturesandsparseex-
| amples | in noisy | highly | periodic | data. | arXiv | preprint |     |     |     |     |     |     |     |     |
| ------ | -------- | ------ | -------- | ----- | ----- | -------- | --- | --- | --- | --- | --- | --- | --- | --- |
arXiv:1708.03665,2017.
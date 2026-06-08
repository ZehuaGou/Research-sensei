# Section Samples: Learning Graph Structures with Transformer for Multivariate Time Series Anomaly Detection in IoT

## Abstract sample

Many real-world IoT systems, which include a
variety of internet-connected sensory devices, produce substantial
amounts of multivariate time series data. Meanwhile, vital IoT
infrastructures like smart power grids and water distribution net-
works are frequently targeted by cyber-attacks, making anomaly
detection an important study topic. Modeling such relatedness is,
nevertheless, unavoidable for any efﬁcient and effective anomaly
detection system, given the intricate topological and nonlinear
connections that are originally unknown among sensors. Further-
more, detecting anomalies in multivariate time series is difﬁcult
due to their temporal dependency and stochasticity. This paper
presented GTA, a new framework for multivariate time series
anomaly detection that involves automatically learning a graph
structure, graph convolution, and modeling temporal dependency
using a Transformer-based architecture. The connection learning
policy, which is based on the Gumbel-softmax sampling app

## Introduction sample

Due to the fast rising number of Internet-connected sensory
devices, the Internet of Things (IoT) infrastructure has created
vast sensory data. IoT data is often characterized by its
speed in terms of geographical and temporal dependency
[1], [2], and it is frequently subjected to correspondingly
rising abnormalities and cyberattacks [3], [4]. Many critical
infrastructures constructed on top of Cyber-Physical Systems
(CPS) [5], such as smart power grids, water treatment and
distribution networks, transportation, and autonomous cars, are
especially in need of security monitoring [6], [7], [4]. As
a result, an efﬁcient and accurate anomaly detection system
has great research value because it can help with continuous
monitoring of fundamental controls or indicators and promptly
provide notiﬁcations for any probable anomalous occurrence.
Z. Chen is with the Department of Computer Science, George Washington
University, Washington, DC, 20052 USA (email: zech chan@gwu.edu)
Z. Yuan is with the

## Method sample

In most real-life scenarios of IoT, there are usually complex
topological relationships between sensors where the entire
entity can be seen as a graph structure. Each sensor is also
viewed as a speciﬁc node in the graph. Previous methods [25],

## Experiments sample

A. Datasets
We evaluate our method over a wide range of real-world
anomaly detection datasets. SWaT [55] The Secure Water
Treatment dataset is collected from a water treatment testbed
for cyber-attack investigation initially launched in May 2015.
The SWaT dataset collection process lasted for 11 days, with
the system operated 24 hours per day such that the network
trafﬁc and all the values obtained from all 51 sensors and
actuators are recorded. Due to the system working ﬂow char-
acteristics, there is a natural topological structure relationship
between all sensing nodes. After this, a total of 41 attacks
derived through an attack model considering the intent space
of a CPS were launched during the last 4 days of the 2016
SWaT data collection process. As such, the overall sequential
data is labeled according to normal and abnormal behaviors
at each timestamp. WADI [9] Water Distribution dataset is
collected from a water distribution testbed as an extension
of the SWaT testbed. It cons

## Conclusion sample

In this work, we proposed GTA, a Transformer-based frame-
work for anomaly detection that uses the introduced connec-
tion learning policy to automatically learn sensor dependen-
cies. To simulate the information ﬂow among the sensors in the
graph, we devised an unique Inﬂuence Propagation (IP) graph
convolution. The inference speed of our proposed multi-branch
attention technique is greatly improved without sacriﬁcing
model performance. Extensive experiments on four real-world
datasets demonstrated that our strategy outperformed other
state-of-the-art approaches in terms of prediction accuracy. We
also provided a case study to demonstrate how our approach
identiﬁes the anomaly by utilizing our proposed techniques.
We aim to explore more about combining this approach with
the online learning strategy to land it on the mobile IoT
scenarios for future work.
11

## References sample

[1] M. S. Mahdavinejad, M. Rezvan, M. Barekatain, P. Adibi, P. M.
Barnaghi, and A. P. Sheth, “Machine learning for internet of things
data analysis: A survey,” CoRR, vol. abs/1802.06305, 2018.
[2] Z. Cai and Z. He, “Trading private range counting over big iot data,” in
39th IEEE International Conference on Distributed Computing Systems,
ICDCS 2019, Dallas, TX, USA, July 7-10, 2019.
IEEE, 2019, pp. 144–
153. [Online]. Available: https://doi.org/10.1109/ICDCS.2019.00023
[3] M. Mohammadi, A. I. Al-Fuqaha, S. Sorour, and M. Guizani, “Deep
learning for iot big data and streaming analytics: A survey,” IEEE
Commun. Surv. Tutorials, vol. 20, no. 4, pp. 2923–2960, 2018.
[4] A. Deng and B. Hooi, “Graph neural network-based anomaly detection
in multivariate time series,” in Proceedings of the 35th AAAI Conference
on Artiﬁcial Intelligence, 2021.
[5] Z. Cai and X. Zheng, “A private and efﬁcient mechanism for
data uploading in smart cyber-physical systems,” IEEE Trans. Netw.
Sci. Eng., vol. 7, no. 

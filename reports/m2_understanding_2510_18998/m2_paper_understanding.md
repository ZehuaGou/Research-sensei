# M2 Paper Understanding

## Paper

- paper_id: 2510_18998
- title: An Encode-then-Decompose Approach to Unsupervised Time Series Anomaly Detection on Contaminated Training Data--Extended Version
- primary_parser: mineru25pro

## Research Problem

I. INTRODUCTION Time-ordered data, known as time series, from a variety of embedded sensors has become the foundation for the continuous monitoring and management of large-scale systems across a variety of domains such as healthcare  \( [70] \) , finance  \( [4] \) , logistics  \( [78] \) , manufacturing  \( [71] \) , and natural sciences  \( [33] \) . Time series anomaly detection, an important branch of time series analysis, constitutes fundamental functionality in data analytics, data management, and data mining. Time series anomaly detection is receiving increasing attention in academia and industry, with numerous applications that include system maintenance  \( [53] \) , network intrusion monitoring  \( [55] \) , and credit card fraud detection  \( [74] \) . The lack of labeled data and the diversity of anomalies combine to make the problem of identifying anomalies challenging and to limit the applicability of methods that require supervision. This has spurred research on unsupervised methods, leading to promising results. Recent neural network based methods for time series anomaly detection achieve strong performance on challenging datasets [26]. These methods are able to lea

## Method Overview

III. METHODOLOGY We first present an overview of the Encode-then-Decompose Anomaly Detection (EDAD) framework that efficiently decomposes a learned hidden time series representation into stable and auxiliary representations. Next, we present the objective function, which is based on representation closeness and mutual information. This function aims to enable robust training, to contend settings with contaminated training data. A. Framework Overview An overview of the framework is shown in Figure 2. The proposed framework consists of two stages, covering offline training and online detection. In the offline training stage, the model training is performed on time series datasets that may 3 already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. The data preprocessing component is shared by the offline training and online detection. This component adopts an established technique [25], [58] and applies the dimension independence strategy, which is the state-of-the-art method for time series [79]. This strategy assumes that the dimensions of a time series do not share information. Thus, it disregards correlations between dimensions.

## Module Structure

- section:Conclusion
- section:Experiments
- section:Introduction
- section:Method
- section:References
- section:Related Work
- section:Unknown
- group:eq_1
- group:eq_2
- group:eq_3
- group:eq_4
- group:eq_5
- group:eq_6
- group:eq_7
- group:eq_8
- group:eq_9
- group:eq_10
- group:eq_11
- group:eq_12
- group:eq_13
- group:eq_14
- group:eq_15
- group:eq_16
- group:eq_17
- group:eq_18

## Key Formulas

- formula_001: definition, section=Related Work, group=eq_1, confidence=0.78
- formula_002: definition, section=Related Work, group=eq_2, confidence=0.56
- formula_003: definition, section=Related Work, group=eq_3, confidence=0.78
- formula_004: attention computation, section=Method, group=eq_4, confidence=0.78
- formula_005: definition, section=Method, group=eq_5, confidence=0.78
- formula_006: definition, section=Method, group=eq_6, confidence=0.56
- formula_007: definition, section=Method, group=eq_6, confidence=0.56
- formula_008: definition, section=Method, group=eq_6, confidence=0.56
- formula_009: definition, section=Method, group=eq_6, confidence=0.56
- formula_010: definition, section=Method, group=eq_6, confidence=0.78
- formula_011: definition, section=Method, group=eq_7, confidence=0.78
- formula_012: attention computation, section=Method, group=eq_8, confidence=0.56
- formula_013: attention computation, section=Method, group=eq_9, confidence=0.78
- formula_014: definition, section=Method, group=eq_10, confidence=0.56
- formula_015: definition, section=Method, group=eq_10, confidence=0.56
- formula_016: reconstruction objective, section=Method, group=eq_10, confidence=0.56
- formula_017: reconstruction objective, section=Method, group=eq_11, confidence=0.78
- formula_018: loss function, section=Method, group=eq_12, confidence=0.56
- formula_019: loss function, section=Method, group=eq_12, confidence=0.56
- formula_020: reconstruction objective, section=Method, group=eq_12, confidence=0.56
- formula_021: contrastive objective, section=Method, group=eq_13, confidence=0.78
- formula_022: contrastive objective, section=Method, group=eq_14, confidence=0.56
- formula_023: contrastive objective, section=Method, group=eq_15, confidence=0.78
- formula_024: contrastive objective, section=Method, group=eq_16, confidence=0.56
- formula_025: reconstruction objective, section=Method, group=eq_17, confidence=0.56
- formula_026: definition, section=Method, group=eq_18, confidence=0.78

## Formula To Method Mapping

- formula_001 -> Related Work / definition
- formula_002 -> Related Work / definition
- formula_003 -> Related Work / definition
- formula_004 -> Method / attention computation
- formula_005 -> Method / definition
- formula_006 -> Method / definition
- formula_007 -> Method / definition
- formula_008 -> Method / definition
- formula_009 -> Method / definition
- formula_010 -> Method / definition
- formula_011 -> Method / definition
- formula_012 -> Method / attention computation
- formula_013 -> Method / attention computation
- formula_014 -> Method / definition
- formula_015 -> Method / definition
- formula_016 -> Method / reconstruction objective
- formula_017 -> Method / reconstruction objective
- formula_018 -> Method / loss function
- formula_019 -> Method / loss function
- formula_020 -> Method / reconstruction objective
- formula_021 -> Method / contrastive objective
- formula_022 -> Method / contrastive objective
- formula_023 -> Method / contrastive objective
- formula_024 -> Method / contrastive objective
- formula_025 -> Method / reconstruction objective
- formula_026 -> Method / definition

## Experiments Summary

IV. EXPERIMENTS A. Experimental Settings 1) Datasets: We conduct experiments on eight real-world datasets that span a wide range of domains, such as manufacturing, natural sciences, and healthcare: (1) Pooled Server Metrics (PSM) [2] is collected from EBAY servers and records the server monitoring metrics; (2) Soil Moisture Active Passive (SMAP) [23] is collected by NASA and presents soil samples and telemetry information from the Mars exploration project; (3) Secure Water Treatment (SWAT) [41] is collected from a water treatment process in an infrastructure for research on cyber-security; (4) Mars Science Laboratory (MSL) [31] is collected by NASA and shows the state of the sensors in the Mars exploration project; (5) NIPSTS-SWAN (SWAN) [31] is extracted from solar photospheric vector magnetograms in Spaceweather HMI Active Region Patch series; (6) KDD21 [47] is a composite dataset released for a SIGKDD 2021 competition; (7) Numenta Anomaly Benchmark (NAB) [3] comprises labeled time series data from diverse sources, encompassing AWS server metrics, online ad click rates, real-time traffic data, and Twitter mentions of major publicly traded firms; (8) Supraventricular Arrhythmia Da

## Main Uncertainties

- Rule-based M2 does not infer claims that are absent from M1 nearby_text.
- Crop/group risk flags lower confidence instead of being hidden.
- Performance gate WARNING from M1 remains a known risk, not a PASS.

## M1 Evidence And M2 Inference Boundary

M2 reads only M1 artifacts and treats page, bbox, latex, parser source, crop path, overlay path, and source identity as immutable evidence. Explanations are role guesses from final_latex plus nearby_text, not new parser output.
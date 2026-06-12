# M2 Formula Understanding

paper_id: 2510_18998

## formula_001

- equation_group_id: eq_1
- equation_number: 1
- page: 3
- section: Related Work
- role_guess: definition
- confidence: 0.78
- risk_flags: none

```latex
I (X, Y) = \sum_ {x \in X} \sum_ {y \in Y} \mathbb {P} (x, y) \log \left(\frac {\mathbb {P} (x , y)}{\mathbb {P} (x) \mathbb {P} (y)}\right) \tag {1}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: C. Mutual Information Estimation for High-Dimensional Data Mutual information (MI) measures the statistical dependency between random variables. Formally, given random variables \( X \) and \( Y \), the MI between \( X \) and \( Y \), denoted as \( I(X,Y) \), Here, \(\mathbb{P}(x,y)\) indicate the joint distribution, and \(\mathbb{P}(x)\) and \(\mathbb{P}(y)\) are the marginal distributions of \(X\) and \(Y\) obtained through a marginalization process. Not; latex: I (X, Y) = \sum_ {x \in X} \sum_ {y \in Y} \mathbb {P} (x, y) \log \left(\frac {\mathbb {P} (x , y)}{\mathbb {P} (x) \mathbb {P} (y)}\right) \tag {1}

## formula_002

- equation_group_id: eq_2
- equation_number: 2
- page: 3
- section: Related Work
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\begin{array}{l} I _ {\mathrm{UBA}} (X, Y) \triangleq \mathbb {E} _ {p (x, y)} [ \log q (x | y) ] + h (X) \\ = \mathbb {E} _ {p (x, y)} [ \log p (x) - \log Z (y) + f (x, y) ] + h (X) \\ = \mathbb {E} _ {p (x, y)} [ f (x, y) ] - \mathbb {E} _ {p (y)} [ \log Z (y) ] \tag {2} \\ \end{array}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: A time series \(\mathcal{T} = \langle \mathbf{s}_1, \mathbf{s}_2, \ldots, \mathbf{s}_N \rangle\) is a sequence of \(N\) time-ordered observations, where each observation \(\mathbf{s}_i \in \mathbb{R}^ B. Time Series Anomaly Detection C. Mutual Information Estimation for High-Dimensional Data; latex: \begin{array}{l} I _ {\mathrm{UBA}} (X, Y) \triangleq \mathbb {E} _ {p (x, y)} [ \log q (x | y) ] + h (X) \\ = \mathbb {E} _ {p (x, y)} [ \log p (x) - \log Z (y

## formula_003

- equation_group_id: eq_3
- equation_number: 3
- page: 3
- section: Related Work
- role_guess: definition
- confidence: 0.78
- risk_flags: none

```latex
q (x | y) = \frac {p (x)}{Z (y)} e ^ {f (x, y)} \tag {3}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: A time series \(\mathcal{T} = \langle \mathbf{s}_1, \mathbf{s}_2, \ldots, \mathbf{s}_N \rangle\) is a sequence of \(N\) time-ordered observations, where each observation \(\mathbf{s}_i \in \mathbb{R}^ B. Time Series Anomaly Detection C. Mutual Information Estimation for High-Dimensional Data; latex: q (x | y) = \frac {p (x)}{Z (y)} e ^ {f (x, y)} \tag {3}

## formula_004

- equation_group_id: eq_4
- equation_number: 4
- page: 4
- section: Method
- role_guess: attention computation
- confidence: 0.78
- risk_flags: none

```latex
\mathbf {H} _ {t: t + B} = \frac {\mathbf {s} _ {t : t + B} - \mathbb {E} [ \mathbf {s} _ {t : t + B} ]}{\sqrt {\operatorname{Var} [ \mathbf {s} _ {t : t + B} ] + \epsilon}} \cdot \gamma_ {1} + \beta_ {1} \tag {4}
```

Uses the formula text and nearby evidence to identify an attention computation. Evidence: er-decomposer based architecture as the backbone of the EDAD framework, as illustrated in Figure 3. The framework comprises two components—an encoder and a decomposer. The encoder encompasses an attention module. The decomposer encompasses two modules—stable feature module and auxiliary feature modu Here, the  \( \gamma_{1} \)  and  \( \beta_{1} \)  are learnable parameter vectors, and  \( E[s_{t:t+B}] \)  and  \( Var[s_{t:t+B}] \)  are the expectation and variance

## formula_005

- equation_group_id: eq_5
- equation_number: 5
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.78
- risk_flags: none

```latex
\mathbf {H} _ {\mathrm{emb}} = \mathbf {W} _ {\mathrm{emb}} \cdot \mathbf {H} \tag {5}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {H} _ {\mathrm{emb}} = \mathbf {W} _ {\mathrm{emb}} \cdot \mathbf {H} \tag {5}

## formula_006

- equation_group_id: eq_6
- equation_number: unknown
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {Q} = \mathbf {W} _ {\mathbf {Q}} \cdot \mathbf {H} _ {\text { emb }}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {Q} = \mathbf {W} _ {\mathbf {Q}} \cdot \mathbf {H} _ {\text { emb }}

## formula_007

- equation_group_id: eq_6
- equation_number: unknown
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION, CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {K} = \mathbf {W} _ {\mathbf {K}} \cdot \mathbf {H} _ {\text { emb }}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {K} = \mathbf {W} _ {\mathbf {K}} \cdot \mathbf {H} _ {\text { emb }}

## formula_008

- equation_group_id: eq_6
- equation_number: 6
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION

```latex
\mathbf {V} = \mathbf {W} _ {\mathbf {V}} \cdot \mathbf {H} _ {\text {emb}} \tag {6}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {V} = \mathbf {W} _ {\mathbf {V}} \cdot \mathbf {H} _ {\text {emb}} \tag {6}

## formula_009

- equation_group_id: eq_6
- equation_number: unknown
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION, CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {S} = \operatorname{softmax} \left(\frac {\mathbf {Q} \cdot \mathbf {K} ^ {\top}}{\sqrt {d}}\right)
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {S} = \operatorname{softmax} \left(\frac {\mathbf {Q} \cdot \mathbf {K} ^ {\top}}{\sqrt {d}}\right)

## formula_010

- equation_group_id: eq_6
- equation_number: unknown
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.78
- risk_flags: none

```latex
\mathbf {Y} _ {1} = \mathbf {S} \cdot \mathbf {V}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {Y} _ {1} = \mathbf {S} \cdot \mathbf {V}

## formula_011

- equation_group_id: eq_7
- equation_number: 7
- page: 4
- section: Method
- role_guess: definition
- confidence: 0.78
- risk_flags: none

```latex
\mathbf {Y} _ {1} = \mathbf {W} _ {\text { mult }} \cdot \left[ \mathbf {Y} _ {1} ^ {1}, \dots , \mathbf {Y} _ {1} ^ {M} \right] ^ {\top} \tag {7}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: Figure 2: Framework pipeline. The data preprocessing component is shared by the offline training and online detection stages. already include anomalies. In the online detection stage, the trained model is used for detecting anomalies. B. Network Architecture; latex: \mathbf {Y} _ {1} = \mathbf {W} _ {\text { mult }} \cdot \left[ \mathbf {Y} _ {1} ^ {1}, \dots , \mathbf {Y} _ {1} ^ {M} \right] ^ {\top} \tag {7}

## formula_012

- equation_group_id: eq_8
- equation_number: 8
- page: 4
- section: Method
- role_guess: attention computation
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {Y} _ {2} = \mathbf {Y} _ {1} + \frac {\mathbf {Y} _ {1} - \mathbb {E} [ \mathbf {Y} _ {1} ]}{\sqrt {\operatorname{Var} [ \mathbf {Y} _ {1} ] + \epsilon}} \cdot \gamma_ {2} + \beta_ {2} \tag {8}
```

Uses the formula text and nearby evidence to identify an attention computation. Evidence: The data preprocessing component is shared by the offline training and online detection. This component adopts an established technique [25], [58] and applies the dimension independence strategy, whic B. Network Architecture The framework comprises two components—an encoder and a decomposer. The encoder encompasses an attention module. The decomposer encompasses two modules—stable feature module and auxiliary feature modu

## formula_013

- equation_group_id: eq_9
- equation_number: 9
- page: 4
- section: Method
- role_guess: attention computation
- confidence: 0.78
- risk_flags: none

```latex
\mathbf {Y} _ {3} = \mathbf {W} _ {2} \cdot \operatorname{ReLU} \left(\mathbf {W} _ {1} \cdot \mathbf {Y} _ {2}\right) \tag {9}
```

Uses the formula text and nearby evidence to identify an attention computation. Evidence: er-decomposer based architecture as the backbone of the EDAD framework, as illustrated in Figure 3. The framework comprises two components—an encoder and a decomposer. The encoder encompasses an attention module. The decomposer encompasses two modules—stable feature module and auxiliary feature modu Here, the  \( \gamma_{1} \)  and  \( \beta_{1} \)  are learnable parameter vectors, and  \( E[s_{t:t+B}] \)  and  \( Var[s_{t:t+B}] \)  are the expectation and variance

## formula_014

- equation_group_id: eq_10
- equation_number: unknown
- page: 5
- section: Method
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {Y} _ {\mathrm{sta}} ^ {I} = \text { identity } (\mathbf {Y} _ {\mathrm{sta}})
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: wo parts, and each part is fed into one of the two modules—the stable feature module and the auxili More specifically, \(\mathbf{Y} = [\mathbf{Y}_{\mathrm{sta}},\mathbf{Y}_{\mathrm{aux}}]\), where \(\mathbf{Y}_{\mathrm{sta}}\in \mathbb{R}^{B\times \frac{d}{2}}\) and \(\mathbf{Y}_{\mathrm{aux}}\in \m To be able to distinguish between stable features and the auxiliary features, we first define two operations—a shuffle operation and an identity operation, which are used in both modules. The shuffle; latex: \mathbf {Y} _ {\mathrm{sta}} ^ {I} = \text { identity } (\mathbf {Y} _ {\mathrm{sta}})

## formula_015

- equation_group_id: eq_10
- equation_number: 10
- page: 5
- section: Method
- role_guess: definition
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION, CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {Y} _ {\text { aux }} ^ {S} = \text { shuffle } (\mathbf {Y} _ {\text { aux }}) \tag {10}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: wo parts, and each part is fed into one of the two modules—the stable feature module and the auxili More specifically, \(\mathbf{Y} = [\mathbf{Y}_{\mathrm{sta}},\mathbf{Y}_{\mathrm{aux}}]\), where \(\mathbf{Y}_{\mathrm{sta}}\in \mathbb{R}^{B\times \frac{d}{2}}\) and \(\mathbf{Y}_{\mathrm{aux}}\in \m To be able to distinguish between stable features and the auxiliary features, we first define two operations—a shuffle operation and an identity operation, which are used in both modules. The shuffle; latex: \mathbf {Y} _ {\text { aux }} ^ {S} = \text { shuffle } (\mathbf {Y} _ {\text { aux }}) \tag {10}

## formula_016

- equation_group_id: eq_10
- equation_number: unknown
- page: 5
- section: Method
- role_guess: reconstruction objective
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION, CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\hat {\mathbf {Y}} _ {\mathrm{aux}} = \mathrm{concat} (\mathbf {Y} _ {\mathrm{sta}} ^ {I}, \mathbf {Y} _ {\mathrm{aux}} ^ {S}) \cdot \mathbf {W} _ {p}
```

Uses the formula text and nearby evidence to identify a reconstruction objective. Evidence: wo parts, and each part is fed into one of the two modules—the stable feature module and the auxili More specifically, \(\mathbf{Y} = [\mathbf{Y}_{\mathrm{sta}},\mathbf{Y}_{\mathrm{aux}}]\), where \(\mathbf{Y}_{\mathrm{sta}}\in \mathbb{R}^{B\times \frac{d}{2}}\) and \(\mathbf{Y}_{\mathrm{aux}}\in \m To be able to distinguish between stable features and the auxiliary features, we first define two operations—a shuffle operation and an identity operation, which are used in both modules. The shuffle

## formula_017

- equation_group_id: eq_11
- equation_number: 11
- page: 5
- section: Method
- role_guess: reconstruction objective
- confidence: 0.78
- risk_flags: none

```latex
\mathcal {L} _ {\text { aux }} = \| \text { shuffle } (\mathbf {Y}) - \hat {\mathbf {Y}} _ {\text { aux }} \| _ {\mathcal {F}} ^ {2} \tag {11}
```

Uses the formula text and nearby evidence to identify a reconstruction objective. Evidence: odule: In the auxiliary module, we apply an identity operation to  \( Y_{sta} \)  and perform a shuffle operation on  \( Y_{aux} \) . Since the auxiliary features contain information relate Then, we formulate the auxiliary loss that measures the closeness between the two representations, as follows. Stable Module: By definition, stable features remain relatively stable over a long period. Therefore a random perturbation of the stable features at a particular timestamp i, denoted as  \( Y_{sta,i}^

## formula_018

- equation_group_id: eq_12
- equation_number: unknown
- page: 6
- section: Method
- role_guess: loss function
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {Y} _ {\mathrm{sta}} ^ {S} = \text { shuffle } (\mathbf {Y} _ {\mathrm{sta}})
```

Uses the formula text and nearby evidence to identify a training loss. Evidence: in long sequences. Finally, after concatenating these two types of features, we apply a projection to obtain the projected representation  \( \hat{Y}_{sta} \) . The stable feature module lacks the self-supervisory information (i.e., shuffle) compared to the auxiliary module, which considers the shuffled Y as self-supervisory information. Using a loss function

## formula_019

- equation_group_id: eq_12
- equation_number: 12
- page: 6
- section: Method
- role_guess: loss function
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION, CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathbf {Y} _ {\text { aux }} ^ {I} = \text { identity } (\mathbf {Y} _ {\text { aux }}) \tag {12}
```

Uses the formula text and nearby evidence to identify a training loss. Evidence: in long sequences. Finally, after concatenating these two types of features, we apply a projection to obtain the projected representation  \( \hat{Y}_{sta} \) . The stable feature module lacks the self-supervisory information (i.e., shuffle) compared to the auxiliary module, which considers the shuffled Y as self-supervisory information. Using a loss function

## formula_020

- equation_group_id: eq_12
- equation_number: unknown
- page: 6
- section: Method
- role_guess: reconstruction objective
- confidence: 0.56
- risk_flags: CROP_TOP_EDGE_CONTAMINATION, CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\hat {\mathbf {Y}} _ {\mathrm{sta}} = \mathrm{concat} (\mathbf {Y} _ {\mathrm{sta}} ^ {S}, \mathbf {Y} _ {\mathrm{aux}} ^ {I}) \cdot \mathbf {W} _ {p}
```

Uses the formula text and nearby evidence to identify a reconstruction objective. Evidence: in long sequences. Finally, after concatenating these two types of features, we apply a projection to obtain the projected representation  \( \hat{Y}_{sta} \) . The stable feature module lacks the self-supervisory information (i.e., shuffle) compared to the auxiliary module, which considers the shuffled Y as self-supervisory information. Using a loss function

## formula_021

- equation_group_id: eq_13
- equation_number: 13
- page: 6
- section: Method
- role_guess: contrastive objective
- confidence: 0.78
- risk_flags: none

```latex
\mathcal {L} _ {\mathrm{sta}} = \left\| \mathbf {Y} - \hat {\mathbf {Y}} _ {\mathrm{sta}} \right\| _ {\mathcal {F}} ^ {2} - I _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}) \tag {13}
```

Formula role is inferred as contrastive objective from final_latex and nearby M1 text. Evidence: es of features, we apply a projection to obtain the projected representation  \( \hat{Y}_{sta} \) . The stable feature module lacks the self-supervisory information (i.e., shuffle) compared to the auxiliary module, which considers the shuffled Y as self-supervisory information. Using a loss function Here,  \( I_{\theta}(\cdot) \)  is the mutual information estimator parameterized by  \( \theta \) . We can choose a specific estimator among many existing ones. We choose InfoNCE as defined in Equati; latex: \mathcal {L} _ {\mathrm{sta}} = \left\| \mathbf {Y} - \hat {\mathbf {Y}} _ {\mathrm{sta}} \right\| _ {\mathcal {F}} ^ {2} - I _ {\theta} (\mathbf {Y}, \mathbf {

## formula_022

- equation_group_id: eq_14
- equation_number: 14
- page: 6
- section: Method
- role_guess: contrastive objective
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
I _ {\text {InfoNCE}} = \mathbb {E} _ {\mathbb {P} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}})} \left[ f _ {\theta} \left(\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}\right) \right] - \mathbb {E} _ {\mathbb {P} \left(\mathbf {Y} _ {\mathrm{sta}}\right)} \left[ \mathbb {E} _ {\mathbb {P} (\mathbf {Y})} \left[ e ^ {f _ {\theta} \left(\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}\right)} \right] \right] \tag {14}
```

Formula role is inferred as contrastive objective from final_latex and nearby M1 text. Evidence: liary module, which considers the shuffled Y as self-supervisory information. Using a loss function Here,  \( I_{\theta}(\cdot) \)  is the mutual information estimator parameterized by  \( \theta \) . We can choose a specific estimator among many existing ones. We choose InfoNCE as defined in Equati Here,  \( f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\mathrm{sta}}) \)  is separable critic function defined as shown in Equation 15.; latex: I _ {\text {InfoNCE}} = \mathbb {E} _ {\mathbb {P} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}})} \left[ f _ {\theta} \left(\mathbf {Y}, \mathbf {Y} _ {\mathrm{st

## formula_023

- equation_group_id: eq_15
- equation_number: 15
- page: 6
- section: Method
- role_guess: contrastive objective
- confidence: 0.78
- risk_flags: none

```latex
f _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}) = \phi_ {\theta} (\mathbf {Y}) ^ {\top} \phi_ {\theta} (\mathbf {Y} _ {\mathrm{sta}}), \tag {15}
```

Formula role is inferred as contrastive objective from final_latex and nearby M1 text. Evidence: ) \)  is the mutual information estimator parameterized by  \( \theta \) . We can choose a specific estimator among many existing ones. We choose InfoNCE as defined in Equati Here,  \( f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\mathrm{sta}}) \)  is separable critic function defined as shown in Equation 15. where \(\phi_{\theta}(\cdot)\) is a non-linear transformation function such as a feed-forward neural network.; latex: f _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\mathrm{sta}}) = \phi_ {\theta} (\mathbf {Y}) ^ {\top} \phi_ {\theta} (\mathbf {Y} _ {\mathrm{sta}}), \tag {15}

## formula_024

- equation_group_id: eq_16
- equation_number: 16
- page: 6
- section: Method
- role_guess: contrastive objective
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathcal {L} _ {\text { reg }} = \| \mathbf {Y} _ {\omega} ^ {\prime} \cdot \mathbf {W} _ {p} - \mathbf {Y} _ {\psi} ^ {\prime} \cdot \mathbf {W} _ {p} \| _ {\mathcal {F}} ^ {2} \tag {16}
```

Formula role is inferred as contrastive objective from final_latex and nearby M1 text. Evidence: ) \)  is the mutual information estimator parameterized by  \( \theta \) . We can choose a specific estimator among many existing ones. We choose InfoNCE as defined in Equati Here,  \( f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\mathrm{sta}}) \)  is separable critic function defined as shown in Equation 15. where \(\phi_{\theta}(\cdot)\) is a non-linear transformation function such as a feed-forward neural network.; latex: \mathcal {L} _ {\text { reg }} = \| \mathbf {Y} _ {\omega} ^ {\prime} \cdot \mathbf {W} _ {p} - \mathbf {Y} _ {\psi} ^ {\prime} \cdot \mathbf {W} _ {p} \| _ {\m

## formula_025

- equation_group_id: eq_17
- equation_number: 17
- page: 6
- section: Method
- role_guess: reconstruction objective
- confidence: 0.56
- risk_flags: CROP_BOTTOM_EDGE_CONTAMINATION

```latex
\mathcal {L} = \lambda_ {1} \cdot \mathcal {L} _ {\mathrm{sta}} + \lambda_ {2} \cdot \mathcal {L} _ {\mathrm{aux}} + \lambda_ {3} \cdot \mathcal {L} _ {\mathrm{reg}} \tag {17}
```

Uses the formula text and nearby evidence to identify a reconstruction objective. Evidence: D. Objective Function The overall loss is the weighted sum of the auxiliary reconstruction loss (Equation 11), the stable reconstruction loss (Equation 13), and the regularization (Equation 16). Hyperparameters  \( \lambda_{1} \) ,  \( \lambda_{2} \) , and  \( \lambda_{3} \)  control the trade-off between the objective function terms. We investigate the sensitivity to  \( \lambda_{1} \) ,  \(

## formula_026

- equation_group_id: eq_18
- equation_number: 18
- page: 7
- section: Method
- role_guess: definition
- confidence: 0.78
- risk_flags: none

```latex
\mathcal {A} \mathcal {S} (\mathbf {s} _ {i}) = - I _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\text {aux}}) \tag {18}
```

Formula role is inferred as definition from final_latex and nearby M1 text. Evidence: on between its encoded representation Y and the corresponding auxiliary representation  \( Y_{aux}  Due to the choice of different mutual information estimators, the critic function  \(  f_{\theta}(\cdot)  \)  (see Equation 13) may not necessarily be proportional to  \(  \frac{\mathbb{P}(\mathbf{Y}, A high score indicates that the input Y and  \( Y_{aux} \)  share less information. Since  \( Y_{aux} \)  includes only short-term variations,  \( s_{i} \)  is more likely to be anomalous.; latex: \mathcal {A} \mathcal {S} (\mathbf {s} _ {i}) = - I _ {\theta} (\mathbf {Y}, \mathbf {Y} _ {\text {aux}}) \tag {18}

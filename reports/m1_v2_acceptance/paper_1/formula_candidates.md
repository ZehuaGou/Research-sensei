# Formula Candidates: Monte Carlo EM for Deep Time Series Anomaly Detection

| id | page | section | origin | is_latex | content |
| -- | ---: | ------- | ------ | -------- | ------- |
| fc_1 | 1 | Unknown | parser_latex | True | p(\mathbf{x}|z) = \begin{cases} p^+(\mathbf{x}) & \text{if } z = 0\\ p^-(\mathbf{x}) & \text{if } z = 1, \end{cases} |
| fc_2 | 1 | Unknown | parser_latex | True | p(\mathbf{x}_t|z_t=0) = p_{\theta}^+(\mathbf{x}_t) \tag{2} |
| fc_3 | 1 | Unknown | parser_latex | True | p(\mathbf{x}_t|z_t=1) = p^-(\mathbf{x}_t) \tag{3} |
| fc_4 | 1 | Unknown | parser_latex | True | \mathbf{x} |
| fc_5 | 1 | Unknown | parser_latex | True | p(\mathbf{x}) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x}) |
| fc_6 | 1 | Unknown | parser_latex | True | p^+(\mathbf{x}) |
| fc_7 | 1 | Unknown | parser_latex | True | p^+ |
| fc_8 | 1 | Unknown | parser_latex | True | p(z=0)=\alpha |
| fc_9 | 1 | Unknown | parser_latex | True | p(z=1)=1-\alpha |
| fc_10 | 1 | Unknown | parser_latex | True | p(\mathbf{x}) = \sum_z p(\mathbf{x}|z)p(z) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x}) |
| fc_11 | 1 | Unknown | parser_latex | True | p(z|\mathbf{x}) |
| fc_12 | 1 | Unknown | parser_latex | True | \mathbf{y}^+ \sim p^+(\cdot) |
| fc_13 | 1 | Unknown | parser_latex | True | z \sim \text{Bernoulli}(1-\alpha) |
| fc_14 | 1 | Unknown | parser_latex | True | \mathbf{x} = \mathbf{I}[z=0]\,\mathbf{y}^+ + \mathbf{I}[z=1]\,\mathbf{y}^- |
| fc_15 | 1 | Unknown | parser_latex | True | \mathbf{y}^+ |
| fc_16 | 1 | Unknown | parser_latex | True | \mathbf{x}_{1:T} = \mathbf{x}_1, \dots, \mathbf{x}_T |
| fc_17 | 1 | Unknown | parser_latex | True | z_t |
| fc_18 | 1 | Unknown | parser_latex | True | \mathbf{x}_t |
| fc_19 | 1 | Unknown | parser_latex | True | p_{\theta}^+(\mathbf{y}_{1:T}) |
| fc_20 | 1 | Unknown | parser_latex | True | p^-(\mathbf{y}_{1:T}) |
| fc_21 | 1 | Unknown | parser_latex | True | \mathbf{y}_{1:T}^+ \sim p^+(\cdot) |
| fc_22 | 1 | Unknown | parser_latex | True | z_{1:T} \sim p^z(z_{1:T}) |
| fc_23 | 1 | Unknown | parser_latex | True | \mathbf{x}_t = \mathbf{I}[z_t = 0] \mathbf{y}_t^+ + \mathbf{I}[z_t = 1] \mathbf{y}_t^- |
| fc_24 | 1 | Unknown | parser_latex | True | p^+(\cdot) |
| fc_25 | 1 | Unknown | parser_latex | True | \mathbf{x}_{1:T} |
| fc_26 | 1 | Unknown | parser_latex | True | \mathbf{y}_{1:T}^+ |
| fc_27 | 1 | Unknown | parser_latex | True | p_{\theta}^+ |
| fc_28 | 1 | Unknown | parser_latex | True | p^z |
| fc_29 | 1 | Unknown | parser_latex | True | z_{1:T} |
| fc_30 | 1 | Unknown | parser_latex | True | \theta |
| fc_31 | 1 | Unknown | parser_latex | True | p(\mathbf{y}_0^+)\prod_{t=0}^T p(\mathbf{y}_{t+1}^+|\mathbf{y}_{t:0}^+) |
| fc_32 | 1 | Unknown | parser_latex | True | p(\mathbf{y}_{t+1}^+|\mathbf{y}_{t:t-l}^+) = \mathcal{N}(f_{\theta}(\mathbf{y}_{t:t-l}), g_{\theta}(\mathbf{y}_{t:t-l})) |
| fc_33 | 1 | Unknown | parser_latex | True | z_t=0 |
| fc_34 | 1 | Unknown | parser_latex | True | z_t=1 |
| fc_35 | 1 | Unknown | parser_latex | True | p(z_{t+1}=1|z_t=1) |
| fc_36 | 1 | Unknown | parser_latex | True | p(z_{t+1} = 1 | z_t = 0) |
| fc_37 | 1 | Unknown | parser_latex | True | p^z(z_{1:T}) |
| fc_38 | 1 | Unknown | parser_latex | True | p(z_{t+1}|z_t) |
| fc_39 | 1 | Unknown | parser_latex | True | p_{\theta t}^+ |
| fc_40 | 1 | Unknown | parser_latex | True | p(z_t = 1) |
| fc_41 | 1 | Unknown | parser_latex | True | p(z_{1:T}) |
| fc_42 | 1 | Unknown | raw_formula_text | False | z)p(z)=αp+(x)+(1−α)p−(x). |     |     |     |     |     |                 |        | 1 :T |
| fc_43 | 1 | Unknown | raw_formula_text | False | sothatp(x)=                                        |     |                                        |     |     |     |     |     |                 | |
| fc_44 | 1 | Unknown | raw_formula_text | False | ifitisnominal(z =1)andequaltoy−oth- AnomalousDataModel Asimplemodelcanbeusedto |
| fc_45 | 1 | Unknown | raw_formula_text | False | Weproposetolearnthemodel probabilityp(z = 1|z = 1). Theexpectedpercentage |
| fc_46 | 1 | Unknown | raw_formula_text | False | onecanupdateit thetransitionprobabilityp(z =1|z =0). usingthepointsthataresampledascomingfromy− . |
| fc_47 | 1 | Unknown | raw_formula_text | False | datatype=s&did=70 |
| fc_48 | 1 | Unknown | raw_formula_text | False | Yahoodatasetusingtheinferredp(z =1)asanomalyscore. |
| fc_49 | 1 | Unknown | raw_formula_text | False | c)Thetimeseriesoflatentanomalyindicatorp(z =1). 4.3.Forecastingusingacorruptedtrainset |
| fc_50 | 1 | Unknown | raw_formula_text | False | tent variable z taking value 0 with probability p(z = 0) = α and value 1 with probability |
| fc_51 | 1 | Unknown | raw_formula_text | False | z)p(z) = αp+(x) + (1 −α)p−(x). |
| fc_52 | 1 | Unknown | raw_formula_text | False | T ), and setting xt = I[zt = 0] y+ |
| fc_53 | 1 | Unknown | raw_formula_text | False | z)p(z) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x})$ . In this setup, anomaly detection can be perfor |
| fc_54 | 1 | Unknown | raw_formula_text | False | span id="page-5-0"></span>References |
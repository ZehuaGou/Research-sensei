# Formula Candidates: Monte Carlo EM for Deep Time Series Anomaly Detection

| idx | source_parser | origin | is_latex | confidence | content |
| --: | ------------- | ------ | -------- | ---------: | ------- |
| 1 | marker | parser_latex | True | 0.80 | p(\mathbf{x}\|z) = \begin{cases} p^+(\mathbf{x}) & \text{if } z = 0\\ p^-(\mathbf{x}) & \text{if } z = 1, \end{cases} |
| 2 | marker | parser_latex | True | 0.80 | p(\mathbf{x}_t\|z_t=0) = p_{\theta}^+(\mathbf{x}_t) \tag{2} |
| 3 | marker | parser_latex | True | 0.80 | p(\mathbf{x}_t\|z_t=1) = p^-(\mathbf{x}_t) \tag{3} |
| 4 | marker | parser_latex | True | 0.80 | \mathbf{x} |
| 5 | marker | parser_latex | True | 0.80 | p(\mathbf{x}) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x}) |
| 6 | marker | parser_latex | True | 0.80 | p^+(\mathbf{x}) |
| 7 | marker | parser_latex | True | 0.80 | p^+ |
| 8 | marker | parser_latex | True | 0.80 | p(z=0)=\alpha |
| 9 | marker | parser_latex | True | 0.80 | p(z=1)=1-\alpha |
| 10 | marker | parser_latex | True | 0.80 | p(\mathbf{x}) = \sum_z p(\mathbf{x}\|z)p(z) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x}) |
| 11 | marker | parser_latex | True | 0.80 | p(z\|\mathbf{x}) |
| 12 | marker | parser_latex | True | 0.80 | \mathbf{y}^+ \sim p^+(\cdot) |
| 13 | marker | parser_latex | True | 0.80 | z \sim \text{Bernoulli}(1-\alpha) |
| 14 | marker | parser_latex | True | 0.80 | \mathbf{x} = \mathbf{I}[z=0]\,\mathbf{y}^+ + \mathbf{I}[z=1]\,\mathbf{y}^- |
| 15 | marker | parser_latex | True | 0.80 | \mathbf{y}^+ |
| 16 | marker | parser_latex | True | 0.80 | \mathbf{x}_{1:T} = \mathbf{x}_1, \dots, \mathbf{x}_T |
| 17 | marker | parser_latex | True | 0.80 | z_t |
| 18 | marker | parser_latex | True | 0.80 | \mathbf{x}_t |
| 19 | marker | parser_latex | True | 0.80 | p_{\theta}^+(\mathbf{y}_{1:T}) |
| 20 | marker | parser_latex | True | 0.80 | p^-(\mathbf{y}_{1:T}) |
| 21 | marker | parser_latex | True | 0.80 | \mathbf{y}_{1:T}^+ \sim p^+(\cdot) |
| 22 | marker | parser_latex | True | 0.80 | z_{1:T} \sim p^z(z_{1:T}) |
| 23 | marker | parser_latex | True | 0.80 | \mathbf{x}_t = \mathbf{I}[z_t = 0] \mathbf{y}_t^+ + \mathbf{I}[z_t = 1] \mathbf{y}_t^- |
| 24 | marker | parser_latex | True | 0.80 | p^+(\cdot) |
| 25 | marker | parser_latex | True | 0.80 | \mathbf{x}_{1:T} |
| 26 | marker | parser_latex | True | 0.80 | \mathbf{y}_{1:T}^+ |
| 27 | marker | parser_latex | True | 0.80 | p_{\theta}^+ |
| 28 | marker | parser_latex | True | 0.80 | p^z |
| 29 | marker | parser_latex | True | 0.80 | z_{1:T} |
| 30 | marker | parser_latex | True | 0.80 | \theta |
| 31 | marker | parser_latex | True | 0.80 | p(\mathbf{y}_0^+)\prod_{t=0}^T p(\mathbf{y}_{t+1}^+\|\mathbf{y}_{t:0}^+) |
| 32 | marker | parser_latex | True | 0.80 | p(\mathbf{y}_{t+1}^+\|\mathbf{y}_{t:t-l}^+) = \mathcal{N}(f_{\theta}(\mathbf{y}_{t:t-l}), g_{\theta}(\mathbf{y}_{t:t-l})) |
| 33 | marker | parser_latex | True | 0.80 | z_t=0 |
| 34 | marker | parser_latex | True | 0.80 | z_t=1 |
| 35 | marker | parser_latex | True | 0.80 | p(z_{t+1}=1\|z_t=1) |
| 36 | marker | parser_latex | True | 0.80 | p(z_{t+1} = 1 \| z_t = 0) |
| 37 | marker | parser_latex | True | 0.80 | p^z(z_{1:T}) |
| 38 | marker | parser_latex | True | 0.80 | p(z_{t+1}\|z_t) |
| 39 | marker | parser_latex | True | 0.80 | p_{\theta t}^+ |
| 40 | marker | parser_latex | True | 0.80 | p(z_t = 1) |
| 41 | marker | parser_latex | True | 0.80 | p(z_{1:T}) |
| 42 | markitdown | raw_formula_text | False | 0.30 | z)p(z)=αp+(x)+(1−α)p−(x). \|     \|     \|     \|     \|     \|                 \|        \| 1 :T |
| 43 | markitdown | raw_formula_text | False | 0.30 | sothatp(x)=                                        \|     \|                                        \|     \|     \|     \|     \|     \|                 \| |
| 44 | markitdown | raw_formula_text | False | 0.30 | ifitisnominal(z =1)andequaltoy−oth- AnomalousDataModel Asimplemodelcanbeusedto |
| 45 | markitdown | raw_formula_text | False | 0.30 | Weproposetolearnthemodel probabilityp(z = 1\|z = 1). Theexpectedpercentage |
| 46 | markitdown | raw_formula_text | False | 0.30 | onecanupdateit thetransitionprobabilityp(z =1\|z =0). usingthepointsthataresampledascomingfromy− . |
| 47 | markitdown | raw_formula_text | False | 0.30 | datatype=s&did=70 |
| 48 | markitdown | raw_formula_text | False | 0.30 | Yahoodatasetusingtheinferredp(z =1)asanomalyscore. |
| 49 | markitdown | raw_formula_text | False | 0.30 | c)Thetimeseriesoflatentanomalyindicatorp(z =1). 4.3.Forecastingusingacorruptedtrainset |
| 50 | pymupdf | raw_formula_text | False | 0.30 | tent variable z taking value 0 with probability p(z = 0) = α and value 1 with probability |
| 51 | pymupdf | raw_formula_text | False | 0.30 | z)p(z) = αp+(x) + (1 −α)p−(x). |
| 52 | pymupdf | raw_formula_text | False | 0.30 | T ), and setting xt = I[zt = 0] y+ |
| 53 | marker | raw_formula_text | False | 0.30 | z)p(z) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x})$ . In this setup, anomaly detection can be perfor |
| 54 | marker | raw_formula_text | False | 0.30 | span id="page-5-0"></span>References |
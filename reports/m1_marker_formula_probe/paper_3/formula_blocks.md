# Marker Formula Blocks: paper_3

## Block formulas: 0

## Markdown formulas: 161

### Formula 1: latex_display
```latex
I(X,Y) = \sum_{x \in X} \sum_{y \in Y} \mathbb{P}(x,y) \log \left( \frac{\mathbb{P}(x,y)}{\mathbb{P}(x)\mathbb{P}(y)} \right)
```
- position: chars 13837-13966

### Formula 2: latex_display
```latex
I_{\text{UBA}}(X,Y) \triangleq \mathbb{E}_{p(x,y)}[\log q(x|y)] + h(X)
```
- position: chars 15848-15922

### Formula 3: latex_display
```latex
= \mathbb{E}_{p(x,y)}[\log p(x) - \log Z(y) + f(x,y)] + h(X)
```
- position: chars 15924-15988

### Formula 4: latex_display
```latex
= \mathbb{E}_{p(x,y)}[f(x,y)] - \mathbb{E}_{p(y)}[\log Z(y)]
```
- position: chars 15990-16054

### Formula 5: latex_display
```latex
q(x|y) = \frac{p(x)}{Z(y)}e^{f(x,y)}
```
- position: chars 16288-16328

### Formula 6: latex_display
```latex
\mathbf{H}_{t:t+B} = \frac{\mathbf{s}_{t:t+B} - \mathbb{E}[\mathbf{s}_{t:t+B}]}{\sqrt{\text{Var}[\mathbf{s}_{t:t+B}] + \epsilon}} \cdot \gamma_1 + \beta_1
```
- position: chars 20051-20209

### Formula 7: latex_display
```latex
\mathbf{H}_{\text{emb}} = \mathbf{W}_{\text{emb}} \cdot \mathbf{H} \tag{5}
```
- position: chars 21116-21194

### Formula 8: latex_display
```latex
\mathbf{Q} = \mathbf{W}_{\mathbf{Q}} \cdot \mathbf{H}_{\text{emb}}
```
- position: chars 21342-21412

### Formula 9: latex_display
```latex
\mathbf{K} = \mathbf{W}_{\mathbf{K}} \cdot \mathbf{H}_{\text{emb}}
```
- position: chars 21414-21484

### Formula 10: latex_display
```latex
\mathbf{V} = \mathbf{W}_{\mathbf{V}} \cdot \mathbf{H}_{\text{emb}}
```
- position: chars 21486-21556

### Formula 11: latex_display
```latex
\mathbf{S} = \operatorname{softmax} \left( \frac{\mathbf{Q} \cdot \mathbf{K}^{\top}}{\sqrt{d}} \right)
```
- position: chars 21558-21664

### Formula 12: latex_display
```latex
\mathbf{Y}_{1} = \mathbf{S} \cdot \mathbf{V}
```
- position: chars 21666-21714

### Formula 13: latex_display
```latex
\mathbf{Y}_1 = \mathbf{W}_{\text{mult}} \cdot [\mathbf{Y}_1^1, \dots, \mathbf{Y}_1^M]^\top \tag{7}
```
- position: chars 22338-22440

### Formula 14: latex_display
```latex
\mathbf{Y}_{2} = \mathbf{Y}_{1} + \frac{\mathbf{Y}_{1} - \mathbb{E}[\mathbf{Y}_{1}]}{\sqrt{\operatorname{Var}[\mathbf{Y}_{1}] + \epsilon}} \cdot \gamma_{2} + \beta_{2}
```
- position: chars 22736-22907

### Formula 15: latex_display
```latex
\mathbf{Y}_3 = \mathbf{W}_2 \cdot \text{ReLU}(\mathbf{W}_1 \cdot \mathbf{Y}_2) \tag{9}
```
- position: chars 23325-23415

### Formula 16: latex_display
```latex
\begin{aligned} \mathbf{Y}_{\text{sta}}^{I} &= \text{identity}(\mathbf{Y}_{\text{sta}}) \\ \mathbf{Y}_{\text{aux}}^{S} &= \text{shuffle}(\mathbf{Y}_{\text{aux}}) \\ \mathbf{\hat{Y}}_{\text{aux}} &= \t
```
- position: chars 26797-27114

### Formula 17: latex_display
```latex
\mathcal{L}_{aux} = \|\text{shuffle}(\mathbf{Y}) - \hat{\mathbf{Y}}_{aux}\|_{\mathcal{F}}^{2}
```
- position: chars 27256-27353

### Formula 18: latex_display
```latex
\begin{aligned} \mathbf{Y}_{\text{sta}}^{S} &= \text{shuffle}(\mathbf{Y}_{\text{sta}}) \\ \mathbf{Y}_{\text{aux}}^{I} &= \text{identity}(\mathbf{Y}_{\text{aux}}) \\ \mathbf{\hat{Y}}_{\text{sta}} &= \t
```
- position: chars 28140-28457

### Formula 19: latex_display
```latex
\mathcal{L}_{\text{sta}} = \|\mathbf{Y} - \hat{\mathbf{Y}}_{\text{sta}}\|_{\mathcal{F}}^2 - I_{\theta}(\mathbf{Y}, \mathbf{Y}_{\text{sta}})
```
- position: chars 29522-29665

### Formula 20: latex_display
```latex
I_{\text{InfoNCE}} = \mathbb{E}_{\mathbb{P}(\mathbf{Y}, \mathbf{Y}_{\text{sta}})}[f_{\theta}(\mathbf{Y}, \mathbf{Y}_{\text{sta}})] - \mathbb{E}_{\mathbb{P}(\mathbf{Y}_{\text{sta}})}[\mathbb{E}_{\mathb
```
- position: chars 30075-30350
# Marker Formula Blocks: paper_2

## Block formulas: 0

## Markdown formulas: 111

### Formula 1: latex_display
```latex
z^{i,j} = \underset{c \in \{0,1\}}{\arg \max} (\log \pi_c^{i,j} + g_c^{i,j})
```
- position: chars 20655-20735

### Formula 2: latex_display
```latex
z_c^{i,j} = \frac{\exp((\log \pi_c^{i,j} + g_c^{i,j})/\tau)}{\sum_{v \in \{0,1\}} \exp((\log \pi_v^{i,j} + g_v^{i,j})/\tau)}
```
- position: chars 21128-21256

### Formula 3: latex_display
```latex
\mathbf{x}_{i}' = \sum_{j \in \mathcal{N}(i)} h_{\mathbf{\Theta}}(\mathbf{x}_{i}||\mathbf{x}_{j} - \mathbf{x}_{j}||\mathbf{x}_{j} + \mathbf{x}_{i})
```
- position: chars 23124-23275

### Formula 4: latex_display
```latex
\mathcal{L}_s = \sum_{1 \le i, j \le M, i \ne j} \log \pi_1^{i,j} \tag{4}
```
- position: chars 25078-25155

### Formula 5: latex_display
```latex
\frac{QK^T}{\sqrt{d_k}}
```
- position: chars 29389-29416

### Formula 6: latex_display
```latex
MultiHead(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = Concat(head_1, \cdots, head_h)W^O
```
- position: chars 30195-30280

### Formula 7: latex_display
```latex
head_i = Attention(\mathbf{Q}W_i^Q, \mathbf{K}W_i^K, \mathbf{V}W_i^V)
```
- position: chars 30354-30427

### Formula 8: latex_display
```latex
Attention(S, V) = Softmax(S)V
```
- position: chars 31821-31854

### Formula 9: latex_display
```latex
\mathbf{A}^{(1)}, \mathbf{A}^{(2)}
```
- position: chars 33431-33469

### Formula 10: latex_display
```latex
\mathbf{A}^{(1)} = \text{MultiHead}(\mathbf{X}^{(1)})
```
- position: chars 33475-33532

### Formula 11: latex_display
```latex
\mathbf{A}^{(2)} = \text{Global}(\mathbf{X}^{(2)})
```
- position: chars 33534-33588

### Formula 12: latex_display
```latex
\mathbf{X}^{(1)} \in \mathcal{R}^{n \times d_1}
```
- position: chars 33601-33652

### Formula 13: latex_display
```latex
\mathcal{L}_{mse} = \frac{1}{M} \sum_{t=1}^{n} ||\mathcal{Y}^{(t)} - \hat{\mathcal{Y}}^{(t)}||_{2}^{2}
```
- position: chars 36224-36330

### Formula 14: latex_display
```latex
\hat{\mathbf{y}}^{(t)} = \sum_{i=1}^{M} ||\mathcal{Y}_i^{(t)} - \hat{\mathcal{Y}}_i^{(t)}||_2^2
```
- position: chars 36506-36605

### Formula 15: latex_display
```latex
\tilde{x} = \frac{x - \min X_{train}}{\max X_{train} - \min X_{train}} \tag{12}
```
- position: chars 40773-40856

### Formula 16: latex_display
```latex
Precision = \frac{TP}{TP + FP}
```
- position: chars 41174-41208

### Formula 17: latex_display
```latex
Recall = \frac{TP}{TP + FN}
```
- position: chars 41216-41247

### Formula 18: latex_display
```latex
F1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}
```
- position: chars 41255-41351

### Formula 19: latex_inline
```latex
\mathcal{X}^{(t)} \in \mathbb{R}^M
```
- position: chars 15359-15395

### Formula 20: latex_inline
```latex
\mathcal{X}
```
- position: chars 15898-15911
# Marker Formula Blocks: paper_1

## Block formulas: 0

## Markdown formulas: 85

### Formula 1: latex_display
```latex
p(\mathbf{x}|z) = \begin{cases} p^+(\mathbf{x}) & \text{if } z = 0\\ p^-(\mathbf{x}) & \text{if } z = 1, \end{cases}
```
- position: chars 6186-6306

### Formula 2: latex_display
```latex
p(\mathbf{x}_t|z_t=0) = p_{\theta}^+(\mathbf{x}_t) \tag{2}
```
- position: chars 11990-12052

### Formula 3: latex_display
```latex
p(\mathbf{x}_t|z_t=1) = p^-(\mathbf{x}_t) \tag{3}
```
- position: chars 12054-12107

### Formula 4: latex_inline
```latex
\mathbf{x}
```
- position: chars 5516-5528

### Formula 5: latex_inline
```latex
p(\mathbf{x}) = \alpha p^+(\mathbf{x}) + (1-\alpha)p^-(\mathbf{x})
```
- position: chars 5570-5638

### Formula 6: latex_inline
```latex
p^+(\mathbf{x})
```
- position: chars 5648-5665

### Formula 7: latex_inline
```latex
p^-(\mathbf{x})
```
- position: chars 5712-5729

### Formula 8: latex_inline
```latex
p(z=0)=\alpha
```
- position: chars 6074-6089

### Formula 9: latex_inline
```latex
p(z=1)=1-\alpha
```
- position: chars 6121-6138

### Formula 10: latex_inline
```latex
p(\mathbf{x}|z) = \begin{cases} p^+(\mathbf{x}) & \text{if } z = 0\\ p^-(\mathbf{x}) & \text{if } z = 1, \end{cases}
```
- position: chars 6187-6305

### Formula 11: latex_inline
```latex
(1)

so that
```
- position: chars 6305-6323

### Formula 12: latex_inline
```latex
. In this setup, anomaly detection can be performed by inferring the posterior distribution
```
- position: chars 6418-6514

### Formula 13: latex_inline
```latex
(and thresholding it if a hard choice is desired). Yet another way of representing the same model is generatively: first, draw
```
- position: chars 6529-6661

### Formula 14: latex_inline
```latex
, and then set
```
- position: chars 6766-6785

### Formula 15: latex_inline
```latex
, i.e. the observation
```
- position: chars 6859-6886

### Formula 16: latex_inline
```latex
is equal to
```
- position: chars 6896-6913

### Formula 17: latex_inline
```latex
if it is nominal (z=1) and equal to
```
- position: chars 6925-6966

### Formula 18: latex_inline
```latex
otherwise. Introducing the additional latent variables
```
- position: chars 6978-7038

### Formula 19: latex_inline
```latex
is unnecessary in the IID setting, but becomes useful in the time series setting described next.

In time series setting, where the observations are time series
```
- position: chars 7071-7237

### Formula 20: latex_inline
```latex
that exhibit temporal dependencies, and anomalies are time points or regions within these time series, we have one anomaly indicator variable
```
- position: chars 7289-7436
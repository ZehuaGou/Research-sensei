# Formula Slots

Total: 11 slots

## Origin Summary

- parser_latex: 11

## Slots

### formula_001
- page: 3
- bbox: [207.685546875, 335.28515625, 504.66741943359375, 365.6975402832031]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `v_{i,t}^s = P(m_i \to q_t^s) = \frac{\exp(\langle m_i, q_t^s \rangle / \tau)}{\sum_{p=1}^L \exp(\lan`
- final_latex: `v_{i,t}^s = P(m_i \to q_t^s) = \frac{\exp(\langle m_i, q_t^s \rangle / \tau)}{\sum_{p=1}^L \exp(\lan`
- crop_path: `formula_001_p3.png`

### formula_002
- page: 3
- bbox: [233.68359375, 452.07421875, 504.6673889160156, 485.45556640625]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `\psi = \sigma \left( U_{\psi} m_i + W_{\psi} \sum_{t=1}^L v_{i,t}^s q_t^s \right), \tag{2}`
- final_latex: `\psi = \sigma \left( U_{\psi} m_i + W_{\psi} \sum_{t=1}^L v_{i,t}^s q_t^s \right), \tag{2}`
- crop_path: `formula_002_p3.png`

### formula_003
- page: 3
- bbox: [229.201171875, 488.0390625, 504.66741943359375, 520.5245666503906]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `m_i \leftarrow (1 - \psi) \circ m_i + \psi \circ \sum_{t=1}^L v_{i,t}^s q_t^s, \tag{3}`
- final_latex: `m_i \leftarrow (1 - \psi) \circ m_i + \psi \circ \sum_{t=1}^L v_{i,t}^s q_t^s, \tag{3}`
- crop_path: `formula_003_p3.png`

### formula_004
- page: 3
- bbox: [206.490234375, 617.58984375, 504.6673889160156, 647.8185424804688]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `w_{t,i}^{s} = P(q_{t}^{s} \to m_{i}) = \frac{\exp(\langle m_{i}, q_{t}^{s} \rangle / \tau)}{\sum_{j=`
- final_latex: `w_{t,i}^{s} = P(q_{t}^{s} \to m_{i}) = \frac{\exp(\langle m_{i}, q_{t}^{s} \rangle / \tau)}{\sum_{j=`
- crop_path: `formula_004_p3.png`

### formula_005
- page: 3
- bbox: [264.76171875, 690.29296875, 504.6673278808594, 725.5085525512695]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `\tilde{q}_{t}^{s} = \sum_{i'=1}^{M} w_{t,i'}^{s} m_{i'}. \tag{5}`
- final_latex: `\tilde{q}_{t}^{s} = \sum_{i'=1}^{M} w_{t,i'}^{s} m_{i'}. \tag{5}`
- crop_path: `formula_005_p3.png`

### formula_006
- page: 4
- bbox: [244.740234375, 209.21484375, 504.66748046875, 242.196533203125]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `L_{rec} = \frac{1}{N} \sum_{s=1}^{N} \left\| X^s - \hat{X}^s \right\|_2^2.`
- final_latex: `L_{rec} = \frac{1}{N} \sum_{s=1}^{N} \left\| X^s - \hat{X}^s \right\|_2^2.`
- crop_path: `formula_006_p4.png`

### formula_007
- page: 4
- bbox: [224.12109375, 305.5078125, 504.6673583984375, 340.23455810546875]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `L_{entr} = \frac{1}{N} \sum_{s=1}^{N} \sum_{t=1}^{L} \sum_{i=1}^{M} -w_{t,i}^{s} log(w_{t,i}^{s}).`
- final_latex: `L_{entr} = \frac{1}{N} \sum_{s=1}^{N} \sum_{t=1}^{L} \sum_{i=1}^{M} -w_{t,i}^{s} log(w_{t,i}^{s}).`
- crop_path: `formula_007_p4.png`

### formula_008
- page: 4
- bbox: [263.56640625, 373.95703125, 504.6673889160156, 386.9834899902344]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `L = L_{rec} + \lambda L_{entr}, \tag{8}`
- final_latex: `L = L_{rec} + \lambda L_{entr}, \tag{8}`
- crop_path: `formula_008_p4.png`

### formula_009
- page: 5
- bbox: [239.958984375, 211.921875, 504.6673889160156, 227.8255615234375]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `LSD(q_t^s, m) = \|q_t^s - m_t^{s, pos}\|_2^2`
- final_latex: `LSD(q_t^s, m) = \|q_t^s - m_t^{s, pos}\|_2^2`
- crop_path: `formula_009_p5.png`

### formula_010
- page: 5
- bbox: [234.28125, 238.9921875, 504.6676940917969, 265.14794921875]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `ISD(X_{t,:}^{s}, \hat{X}_{t,:}^{s}) = \left\| X_{t,:}^{s} - \hat{X}_{t,:}^{s} \right\|_{2}^{2}`
- final_latex: `ISD(X_{t,:}^{s}, \hat{X}_{t,:}^{s}) = \left\| X_{t,:}^{s} - \hat{X}_{t,:}^{s} \right\|_{2}^{2}`
- crop_path: `formula_010_p5.png`

### formula_011
- page: 5
- bbox: [158.080078125, 303.57421875, 504.667724609375, 318.82958984375]
- block_type: Equation
- detection_source: marker_document
- detection_confidence: 0.8
- final_origin: parser_latex
- marker_latex: `A(X^{s}) = softmax([LSD(q_{t}^{s}, m)]_{t=1,\dots,L}) \circ [ISD(X_{t,:}^{s}, \hat{X}_{t,:}^{s})]_{t`
- final_latex: `A(X^{s}) = softmax([LSD(q_{t}^{s}, m)]_{t=1,\dots,L}) \circ [ISD(X_{t,:}^{s}, \hat{X}_{t,:}^{s})]_{t`
- crop_path: `formula_011_p5.png`

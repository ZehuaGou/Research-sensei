import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import FormulaCard from '../cards/FormulaCard.vue'

function mountCard(card: any) {
  return mount(FormulaCard, {
    props: { card },
    global: {
      plugins: [createPinia()],
    },
  })
}

describe('FormulaCard', () => {
  it('renders formula card without exposing internal metadata', () => {
    const wrapper = mountCard({
      formula_latex: 'E = mc^2',
      formula_ref: 'eq:1',
      problem: 'Einstein energy equivalence',
      evidence_status: 'SUPPORTED_BY_TEXT',
      terms: [],
    })
    expect(wrapper.text()).toContain('Einstein energy equivalence')
    expect(wrapper.text()).toContain('证据已绑定')
    expect(wrapper.text()).not.toContain('eq:1')
    expect(wrapper.text()).not.toContain('SUPPORTED_BY_TEXT')
  })

  it('hides formula_origin and formula_ocr_status badges from the reader view', () => {
    const wrapper = mountCard({
      formula_latex: 'x + y',
      formula_origin: 'source_latex',
      formula_ocr_status: 'not_required',
      terms: [],
    })
    expect(wrapper.text()).not.toContain('source_latex')
    expect(wrapper.text()).not.toContain('not_required')
  })

  it('renders terms with encourages, penalizes, and removal effects', () => {
    const terms = [
      {
        term: '\\|x - y\\|^2',
        meaning: 'Squared distance between x and y',
        encourages: 'Similar representations',
        penalizes: 'Dissimilar representations',
        if_removed: 'Model loses contrastive signal',
      },
      {
        term: '\\log p(x)',
        meaning: 'Log likelihood',
        encourages: 'High probability data',
        penalizes: 'Unlikely data',
        if_removed: 'Model becomes unnormalized',
      },
    ]
    const wrapper = mountCard({
      formula_latex: 'L = ||x - y||^2 + log p(x)',
      terms,
    })

    expect(wrapper.html()).toContain('katex')
    expect(wrapper.text()).not.toContain('\\|x - y\\|^2')
    expect(wrapper.text()).toContain('Squared distance between x and y')
    expect(wrapper.text()).toContain('鼓励：Similar representations')
    expect(wrapper.text()).toContain('惩罚：Dissimilar representations')
    expect(wrapper.text()).toContain('去掉：Model loses contrastive signal')
    expect(wrapper.text()).not.toContain('\\log p(x)')
    expect(wrapper.text()).toContain('Log likelihood')
    expect(wrapper.text()).toContain('High probability data')
    expect(wrapper.text()).toContain('Unlikely data')
    expect(wrapper.text()).toContain('Model becomes unnormalized')
  })

  it('renders LaTeX symbols as readable inline math instead of raw source text', () => {
    const wrapper = mountCard({
      formula_latex: '\\mathbf{V}',
      symbols: [{ symbol: '\\mathbf{V}', meaning: '值矩阵' }],
      terms: [],
    })

    expect(wrapper.html()).toContain('katex')
    expect(wrapper.text()).toContain('值矩阵')
    expect(wrapper.text()).not.toContain('\\mathbf{V}')
  })

  it('shows term meaning even when optional FormulaTerm fields are empty', () => {
    const wrapper = mountCard({
      formula_latex: 'f(x)',
      terms: [{ term: 'x', meaning: 'Input variable', encourages: '', penalizes: '', if_removed: '' }],
    })
    expect(wrapper.text()).toContain('Input variable')
    expect(wrapper.text()).toContain('x')
    expect(wrapper.text()).not.toContain('鼓励：')
  })

  it('does not render term items when terms are empty', () => {
    const wrapper = mountCard({
      formula_latex: 'x + y',
      terms: [],
    })
    expect(wrapper.text()).not.toContain('Input variable')
    expect(wrapper.text()).toContain('直觉')
  })

  it('handles card without terms field gracefully', () => {
    const wrapper = mountCard({
      formula_latex: 'x = y',
    })
    expect(wrapper.text()).toContain('直觉')
    expect(wrapper.text()).toContain('小例子')
    expect(wrapper.text()).toContain('拿掉会怎样')
  })

  it('does not throw for invalid LaTeX', async () => {
    const wrapper = mountCard({
      formula_latex: '$$invalid',
      terms: [],
    })
    await new Promise(resolve => setTimeout(resolve, 100))
    expect(wrapper.exists()).toBe(true)
  })

  it('renders remove_effect, weight_change_effect, and plain summary', () => {
    const wrapper = mountCard({
      formula_latex: 'L = L_task + lambda * L_reg',
      remove_effect: 'Without regularization, model overfits',
      weight_change_effect: 'Higher lambda means stronger regularization',
      plain_summary: 'This is a regularized loss function',
      terms: [],
    })
    expect(wrapper.text()).toContain('This is a regularized loss function')
    expect(wrapper.text()).toContain('Without regularization')
    expect(wrapper.text()).toContain('Higher lambda')
  })

  it('presents insufficient formula evidence as a readable degraded state', () => {
    const wrapper = mountCard({
      display_title: '公式 1 来源不足，暂不推导',
      formula_raw: 'Precision = TP / (TP + FP) where TP represents true positives',
      formula_origin: 'raw_formula_text',
      purpose: 'INSUFFICIENT_EVIDENCE: literature discovery did not provide reliable LaTeX.',
      intuition: 'INSUFFICIENT_EVIDENCE',
      numeric_example: 'INSUFFICIENT_EVIDENCE',
      terms: [],
    })

    expect(wrapper.text()).toContain('公式 1 来源不足，暂不推导')
    expect(wrapper.text()).toContain('来源不足')
    expect(wrapper.text()).toContain('证据不足，暂不推导。')
    expect(wrapper.text()).not.toContain('INSUFFICIENT_EVIDENCE')
  })
})

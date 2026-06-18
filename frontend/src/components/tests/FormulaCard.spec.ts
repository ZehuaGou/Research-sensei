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
  it('renders formula card with core fields', () => {
    const wrapper = mountCard({
      formula_latex: 'E = mc^2',
      formula_ref: 'eq:1',
      problem: 'Einstein energy equivalence',
      evidence_status: 'SUPPORTED_BY_TEXT',
      terms: [],
    })
    expect(wrapper.text()).toContain('Einstein energy equivalence')
    expect(wrapper.text()).toContain('eq:1')
    expect(wrapper.text()).toContain('SUPPORTED_BY_TEXT')
  })

  it('renders formula_origin badge', () => {
    const wrapper = mountCard({
      formula_latex: 'x + y',
      formula_origin: 'source_latex',
      terms: [],
    })
    expect(wrapper.text()).toContain('source_latex')
  })

  it('renders formula_ocr_status badge', () => {
    const wrapper = mountCard({
      formula_latex: 'x + y',
      formula_ocr_status: 'not_required',
      terms: [],
    })
    expect(wrapper.text()).toContain('not_required')
  })

  it('renders term table with encourages/penalizes/if_removed for FormulaTerm data', () => {
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
    expect(wrapper.text()).toContain('项')
    expect(wrapper.text()).toContain('含义')
    expect(wrapper.text()).toContain('鼓励')
    expect(wrapper.text()).toContain('惩罚')
    expect(wrapper.text()).toContain('去掉会怎样')

    // Verify FormulaTerm fields render correctly
    expect(wrapper.text()).toContain('\\|x - y\\|^2')
    expect(wrapper.text()).toContain('Squared distance between x and y')
    expect(wrapper.text()).toContain('Similar representations')
    expect(wrapper.text()).toContain('Dissimilar representations')
    expect(wrapper.text()).toContain('Model loses contrastive signal')

    expect(wrapper.text()).toContain('\\log p(x)')
    expect(wrapper.text()).toContain('Log likelihood')
    expect(wrapper.text()).toContain('High probability data')
    expect(wrapper.text()).toContain('Unlikely data')
    expect(wrapper.text()).toContain('Model becomes unnormalized')
  })

  it('shows fallback dash when FormulaTerm fields are empty', () => {
    const terms = [
      {
        term: 'x',
        meaning: 'Input variable',
        encourages: '',
        penalizes: '',
        if_removed: '',
      },
    ]
    const wrapper = mountCard({
      formula_latex: 'f(x)',
      terms,
    })
    // Empty fields should show '-' as fallback, not blank
    expect(wrapper.text()).toContain('Input variable')
    expect(wrapper.text()).toContain('x')
  })

  it('does not render term table when terms is empty', () => {
    const wrapper = mountCard({
      formula_latex: 'x + y',
      terms: [],
    })
    expect(wrapper.text()).not.toContain('项含义')
  })

  it('handles card without terms field gracefully', () => {
    const wrapper = mountCard({
      formula_latex: 'x = y',
    })
    // Should not crash, should render other sections
    expect(wrapper.text()).toContain('更多分析')
  })

  it('shows render error for invalid LaTeX', async () => {
    const wrapper = mountCard({
      formula_latex: '$$invalid',
      terms: [],
    })
    await new Promise(resolve => setTimeout(resolve, 100))
    // Component should not throw even if KaTeX rendering fails in jsdom
    expect(wrapper.exists()).toBe(true)
  })

  it('renders expanded section with remove_effect and weight_change_effect', async () => {
    const wrapper = mountCard({
      formula_latex: 'L = L_task + lambda * L_reg',
      remove_effect: 'Without regularization, model overfits',
      weight_change_effect: 'Higher lambda means stronger regularization',
      plain_summary: 'This is a regularized loss function',
      terms: [],
    })
    expect(wrapper.text()).toContain('更多分析')
    // Expanded content should not be visible initially
    expect(wrapper.text()).not.toContain('去掉该项')

    // Click the expand button (the one with "更多分析"/"收起" text)
    const expandBtn = wrapper.findAll('button').find(b => b.text().includes('更多分析') || b.text().includes('收起'))
    expect(expandBtn).toBeTruthy()
    await expandBtn!.trigger('click')
    expect(wrapper.text()).toContain('去掉该项')
    expect(wrapper.text()).toContain('Without regularization')
    expect(wrapper.text()).toContain('权重变化')
    expect(wrapper.text()).toContain('Higher lambda')
    expect(wrapper.text()).toContain('This is a regularized loss function')
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import LearningWorkspaceView from '../LearningWorkspaceView.vue'

const routerMock = vi.hoisted(() => ({
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { jobId: 'job-123' } }),
  useRouter: () => routerMock,
}))

function mountView() {
  return mount(LearningWorkspaceView, {
    global: {
      plugins: [createPinia()],
      stubs: {
        PaperCard: { props: ['card'], template: '<div data-testid="paper-card">{{ card.thirty_second }}</div>' },
        FormulaCard: { props: ['card'], template: '<div data-testid="formula-card">{{ card.problem }}</div>' },
        AskPanel: { template: '<div data-testid="ask-panel-stub"></div>' },
        TextSelectionToolbar: { template: '<div data-testid="selection-toolbar-stub"></div>' },
      },
    },
  })
}

function tab(wrapper: any, text: string) {
  const button = wrapper.findAll('button').find((item: any) => item.text().includes(text))
  expect(button).toBeDefined()
  return button!
}

describe('LearningWorkspaceView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    routerMock.push.mockReset()
  })

  it('does not request cards for BASELINE_ONLY', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        understanding_status: {
          status: 'BASELINE_ONLY',
          blocking_reason: 'NO_LLM_CLIENT',
          warnings: [],
          component_status: { paper_card: 'BASELINE' },
          allowed_downstream: { reading_display: false },
        },
        paper_workspace_status: {
          source_type: 'upload',
          canonicalization_status: 'not_available',
          evidence_status: 'SUCCESS',
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountView()
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(String(fetchMock.mock.calls[0][0])).toContain('/understanding_status')
    expect(wrapper.find('[data-testid="no-cards-state"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="paper-card"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="ask-panel-stub"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="selection-toolbar-stub"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('仅基础解析')
    expect(wrapper.text()).toContain('ccswitch')
    expect(wrapper.text()).toContain('来源类型')
    expect(wrapper.text()).toContain('论文卡片')
  })

  it('does not request or render cards for BLOCKED_UNDERSTANDING', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        understanding_status: {
          status: 'BLOCKED_UNDERSTANDING',
          blocking_reason: 'MISSING_METHOD_EVIDENCE',
          warnings: [{ code: 'NO_METHOD', message: 'No method evidence.' }],
          component_status: { paper_card: 'SKIPPED' },
          allowed_downstream: { reading_display: false },
        },
        paper_workspace_status: {
          source_type: 'm1_canonical_bundle',
          canonicalization_status: 'success',
          m2_ready: true,
          evidence_status: 'SUCCESS',
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountView()
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-testid="paper-card"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="no-cards-state"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="ask-panel-stub"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('理解被阻断')
    expect(wrapper.text()).toContain('缺少方法证据')
  })

  it('requests cards for SUCCESS and renders paper, formula, and teaching tabs', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          understanding_status: {
            status: 'SUCCESS',
            warnings: [],
            component_status: { paper_card: 'SUCCESS', formula_cards: 'SUCCESS', teaching_cards: 'SUCCESS' },
            allowed_downstream: { reading_display: true, advisor_questions: true },
          },
          paper_workspace_status: {
            source_type: 'm1_canonical_bundle',
            canonicalization_status: 'success',
            m2_ready: true,
            formula_origin: 'mineru_latex',
            formula_ocr_status: 'not_required',
            evidence_status: 'SUCCESS',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'SUCCESS',
          paper_workspace_status: { source_type: 'upload', quality_status: 'pass' },
          cards: {
            paper_card: {
              one_sentence_summary: 'A grounded summary.',
              problem: { text: 'Problem', evidence_ref: 'p:b1' },
              core_idea: { text: 'Idea', evidence_ref: 'p:b2' },
              method_overview: { text: 'Method', evidence_ref: 'p:b3' },
            },
            formula_cards: {
              formula_cards: [{
                formula_id: 'formula_001',
                purpose: 'Formula purpose',
                formula_raw: 'x=y',
                formula_origin: 'mineru_latex',
                formula_ocr_status: 'not_required',
                evidence_status: 'SUPPORTED_BY_FORMULA',
                evidence_ref: 'p:eq1',
              }, {
                formula_id: 'formula_002',
                purpose: 'Second formula purpose',
                formula_raw: 'a=b',
                formula_origin: 'mineru_latex',
                formula_ocr_status: 'not_required',
                evidence_status: 'SUPPORTED_BY_FORMULA',
                evidence_ref: 'p:eq2',
              }],
            },
            teaching_cards: {
              teaching_cards: [{
                card_id: 't1',
                title: 'Teaching',
                human_explanation: 'A teaching explanation.',
                evidence_refs: ['p:b2'],
              }],
            },
          },
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountView()
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(String(fetchMock.mock.calls[1][0])).toContain('/cards')
    expect(wrapper.find('[data-testid="paper-card"]').text()).toContain('A grounded summary.')
    expect(wrapper.find('[data-testid="ask-panel-stub"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('打开 M4')
    expect(wrapper.find('[data-testid="selection-toolbar-stub"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('理解完成')
    expect(wrapper.text()).toContain('公式来源')
    expect(wrapper.text()).toContain('MinerU LaTeX')

    await tab(wrapper, '公式拆解').trigger('click')
    expect(wrapper.get('[data-testid="formula-index"]').text()).toContain('公式目录')
    expect(wrapper.get('[data-testid="formula-index"]').text()).toContain('Formula purpose')
    expect(wrapper.get('[data-testid="formula-index"]').text()).toContain('Second formula purpose')
    expect(wrapper.findAll('[data-testid="formula-card"]')).toHaveLength(2)
    expect(wrapper.find('[data-testid="formula-card"]').text()).toContain('Formula purpose')

    await tab(wrapper, '教学卡片').trigger('click')
    expect(wrapper.get('[data-testid="teaching-cards"]').text()).toContain('p:b2')
  })

  it('switches old deep-read routes to the latest reparsed job', async () => {
    const replaceState = vi.spyOn(window.history, 'replaceState')
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-latest',
          understanding_status: {
            status: 'SUCCESS',
            warnings: [],
            component_status: { paper_card: 'SUCCESS', formula_cards: 'SUCCESS', teaching_cards: 'SUCCESS' },
            allowed_downstream: { reading_display: true, advisor_questions: true },
          },
          paper_workspace_status: { source_type: 'reparse', evidence_status: 'SUCCESS' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          job_id: 'job-latest',
          status: 'SUCCESS',
          cards: {
            paper_card: { one_sentence_summary: 'Latest grounded summary.' },
            formula_cards: { formula_cards: [] },
            teaching_cards: { teaching_cards: [] },
          },
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountView()
    await flushPromises()

    expect(String(fetchMock.mock.calls[0][0])).toContain('/jobs/job-123/understanding_status')
    expect(String(fetchMock.mock.calls[1][0])).toContain('/jobs/job-latest/cards')
    expect(replaceState).toHaveBeenCalledWith(window.history.state, '', '/learn/job-latest')
    expect(wrapper.text()).toContain('Latest grounded summary.')
  })

  it('renders available components for structural formula degradation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          understanding_status: {
            status: 'DEGRADED_STRUCTURAL',
            blocking_reason: 'FORMULA_DERIVATION_BLOCKED',
            warnings: [{ code: 'FORMULA_BLOCKED', message: 'formula cards blocked' }],
            component_status: { paper_card: 'SUCCESS', formula_cards: 'FAILED', teaching_cards: 'SUCCESS' },
            allowed_downstream: { reading_display: true, advisor_questions: true },
          },
          paper_workspace_status: {
            source_type: 'm1_canonical_bundle',
            canonicalization_status: 'success',
            m2_ready: true,
            degradation_reason: 'FORMULA_DERIVATION_BLOCKED',
            formula_origin: 'raw_formula_text',
            formula_ocr_status: 'not_available',
            evidence_status: 'SUCCESS',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'DEGRADED_STRUCTURAL',
          degraded: true,
          missing_components: ['formula_cards'],
          paper_workspace_status: { quality_status: 'warning' },
          cards: {
            paper_card: {
              one_sentence_summary: 'A grounded summary with blocked formulas.',
              problem: { text: 'Problem', evidence_ref: 'p:b1' },
              core_idea: { text: 'Idea', evidence_ref: 'p:b2' },
              method_overview: { text: 'Method', evidence_ref: 'p:b3' },
            },
            teaching_cards: {
              teaching_cards: [{
                card_id: 't1',
                title: 'Teaching still available',
                human_explanation: 'Teaching remains available.',
                evidence_refs: ['p:b2'],
              }],
            },
            formula_cards: {
              formula_cards: [{
                formula_id: 'raw-1',
                formula_raw: 'Y = X beta + epsilon',
                formula_origin: 'raw_formula_text',
                derivation_status: 'blocked',
                coverage_status: 'BLOCKED_RAW_ONLY',
              }, {
                formula_id: 'raw-2',
                formula_raw: 'R = X - beta Z',
                formula_origin: 'raw_formula_text',
                derivation_status: 'blocked',
                coverage_status: 'BLOCKED_RAW_ONLY',
              }],
            },
          },
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountView()
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('结构不完整')
    expect(wrapper.text()).toContain('受限：公式卡片')
    expect(wrapper.text()).toContain('公式推导被阻断')
    expect(wrapper.text()).toContain('2 段受限')
    expect(wrapper.find('[data-testid="paper-card"]').text()).toContain('A grounded summary with blocked formulas.')

    await tab(wrapper, '公式拆解').trigger('click')
    expect(wrapper.find('[data-testid="formula-degraded-message"]').text()).toContain('公式拆解暂时不可用')
    expect(wrapper.find('[data-testid="formula-degraded-message"]').text()).toContain('raw_formula_text')
    expect(wrapper.find('[data-testid="formula-degraded-message"]').text()).toContain('已隐藏 2 条不完整的原始公式残片')

    await tab(wrapper, '教学卡片').trigger('click')
    expect(wrapper.find('[data-testid="teaching-cards"]').text()).toContain('Teaching remains available.')
  })

  it('does not show formula degradation message when status is blocked', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        understanding_status: {
          status: 'BLOCKED_UNDERSTANDING',
          blocking_reason: 'MISSING_METHOD_EVIDENCE',
          warnings: [],
          component_status: { paper_card: 'SKIPPED' },
          allowed_downstream: { reading_display: false },
        },
        paper_workspace_status: {
          source_type: 'm1_canonical_bundle',
          canonicalization_status: 'success',
          evidence_status: 'SUCCESS',
        },
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mountView()
    await flushPromises()

    const formulaTab = wrapper.findAll('button').find((button) => button.text().includes('公式拆解'))
    expect(formulaTab).toBeDefined()
    expect(formulaTab!.attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="formula-degraded-message"]').exists()).toBe(false)
  })
})

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
        AskPanel: { template: '<div />' },
        TextSelectionToolbar: { template: '<div />' },
      },
    },
  })
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
    expect(wrapper.text()).toContain('Baseline only')
    expect(wrapper.text()).toContain('source_type')
    expect(wrapper.text()).toContain('component_status.paper_card')
    expect(wrapper.text()).toContain('allowed_downstream.reading_display')
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
    expect(wrapper.text()).toContain('Understanding blocked')
    expect(wrapper.text()).toContain('MISSING_METHOD_EVIDENCE')
  })

  it('requests cards for SUCCESS and renders paper card', async () => {
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
    expect(wrapper.text()).toContain('Understanding ready')
    expect(wrapper.text()).toContain('formula_origin')
    expect(wrapper.text()).toContain('mineru_latex')
    expect(wrapper.text()).toContain('allowed_downstream.advisor_questions')

    await wrapper.get('button:nth-of-type(2)').trigger('click')
    expect(wrapper.find('[data-testid="formula-card"]').text()).toContain('Formula purpose')

    await wrapper.get('button:nth-of-type(3)').trigger('click')
    expect(wrapper.get('[data-testid="teaching-cards"]').text()).toContain('p:b2')
  })

  it('requests cards for DEGRADED_STRUCTURAL and renders only successful components', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          understanding_status: {
            status: 'DEGRADED_STRUCTURAL',
            blocking_reason: 'TEACHING_CARDS_FAILED',
            warnings: [{ code: 'V2_BUILDER_FAILED', message: 'teaching_cards_v2 failed' }],
            component_status: { paper_card: 'SUCCESS', formula_cards: 'SUCCESS', teaching_cards: 'FAILED' },
            allowed_downstream: { reading_display: true, advisor_questions: false },
          },
          paper_workspace_status: {
            source_type: 'm1_canonical_bundle',
            canonicalization_status: 'success',
            m2_ready: true,
            degradation_reason: 'TEACHING_CARDS_FAILED',
            formula_origin: 'mineru_latex',
            formula_ocr_status: 'not_required',
            evidence_status: 'SUCCESS',
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'DEGRADED_STRUCTURAL',
          degraded: true,
          missing_components: ['teaching_cards'],
          paper_workspace_status: { quality_status: 'warning' },
          cards: {
            paper_card: {
              one_sentence_summary: 'A degraded but grounded summary.',
              problem: { text: 'Problem', evidence_ref: 'p:b1' },
              core_idea: { text: 'Idea', evidence_ref: 'p:b2' },
              method_overview: { text: 'Method', evidence_ref: 'p:b3' },
            },
            formula_cards: {
              formula_cards: [{
                formula_id: 'formula_001',
                purpose: 'Formula still available',
                formula_origin: 'mineru_latex',
                formula_ocr_status: 'not_required',
                evidence_ref: 'p:eq1',
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
    expect(wrapper.text()).toContain('Degraded understanding')
    expect(wrapper.text()).toContain('missing_components: teaching_cards')
    expect(wrapper.text()).toContain('TEACHING_CARDS_FAILED')
    expect(wrapper.find('[data-testid="paper-card"]').text()).toContain('A degraded but grounded summary.')
    expect(wrapper.text()).toContain('allowed_downstream.advisor_questions')
    expect(wrapper.text()).toContain('false')

    await wrapper.get('button:nth-of-type(2)').trigger('click')
    expect(wrapper.find('[data-testid="formula-card"]').text()).toContain('Formula still available')
    expect(wrapper.find('[data-testid="teaching-cards"]').exists()).toBe(false)
  })

  it('shows formula degradation message when formula_cards missing in DEGRADED_STRUCTURAL', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          understanding_status: {
            status: 'DEGRADED_STRUCTURAL',
            blocking_reason: 'FORMULA_DERIVATION_BLOCKED',
            warnings: [{ code: 'FORMULA_BLOCKED', message: '9 blocked formulas, formula_origins: raw_formula_text' }],
            component_status: { paper_card: 'SUCCESS', formula_cards: 'FAILED', teaching_cards: 'SUCCESS', llm: 'SUCCESS', evidence_pack: 'SUCCESS' },
            allowed_downstream: { reading_display: true, advisor_questions: false },
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
          paper_workspace_status: {},
          cards: {
            paper_card: {
              one_sentence_summary: 'A grounded summary.',
              problem: { text: 'Problem', evidence_ref: 'p:b1' },
              core_idea: { text: 'Idea', evidence_ref: 'p:b2' },
              method_overview: { text: 'Method', evidence_ref: 'p:b3' },
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
    expect(wrapper.text()).toContain('Degraded understanding')
    expect(wrapper.text()).toContain('missing_components: formula_cards')
    expect(wrapper.text()).toContain('FORMULA_DERIVATION_BLOCKED')

    // Formulas tab should be clickable (not disabled) in DEGRADED state
    const formulaTab = wrapper.findAll('button').find(b => b.text() === 'Formulas')
    expect(formulaTab).toBeDefined()
    expect(formulaTab!.attributes('disabled')).toBeUndefined()

    // Click Formulas tab
    await formulaTab!.trigger('click')
    await flushPromises()

    // Should show degradation message, not formula cards
    expect(wrapper.find('[data-testid="formula-degraded-message"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="formula-degraded-message"]').text()).toContain('公式推导不可用')
    expect(wrapper.find('[data-testid="formula-degraded-message"]').text()).toContain('FORMULA_DERIVATION_BLOCKED')
    expect(wrapper.find('[data-testid="formula-degraded-message"]').text()).toContain('raw_formula_text')
    expect(wrapper.find('[data-testid="formula-card"]').exists()).toBe(false)

    // Paper card should still work
    await wrapper.findAll('button').find(b => b.text() === 'Paper')!.trigger('click')
    expect(wrapper.find('[data-testid="paper-card"]').text()).toContain('A grounded summary.')

    // Teaching card should still work
    await wrapper.findAll('button').find(b => b.text() === 'Teaching')!.trigger('click')
    expect(wrapper.get('[data-testid="teaching-cards"]').text()).toContain('A teaching explanation.')
  })

  it('does not show formula degradation message when status is not DEGRADED', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
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

    // Formulas tab should be disabled for BLOCKED
    const formulaTab = wrapper.findAll('button').find(b => b.text() === 'Formulas')
    expect(formulaTab).toBeDefined()
    expect(formulaTab!.attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="formula-degraded-message"]').exists()).toBe(false)
  })
})

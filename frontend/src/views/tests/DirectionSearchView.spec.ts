import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DirectionSearchView from '../DirectionSearchView.vue'

function directionResponse(overrides: Record<string, any> = {}) {
  return {
    status: 'SUCCESS',
    direction_workspace_status: 'SUCCESS',
    message: 'Direction exploration returned a structured bundle from real paper sources.',
    overview: 'time series anomaly detection is organized as a conservative reading landscape.',
    seed_expansion_status: 'NOT_IMPLEMENTED',
    warnings: [],
    key_sub_directions: [
      { name: 'reconstruction-based detection', description: 'Track reconstruction papers.' },
    ],
    method_families: [
      { name: 'Transformer/attention methods', role: 'TRANSFORMER_METHOD', paper_count: 1 },
    ],
    papers: [
      {
        paper_id: 'p1',
        title: 'Time Series Anomaly Detection with Transformers',
        authors: ['A. Researcher'],
        year: 2024,
        venue: 'NeurIPS',
        source: 'arxiv',
        url: 'https://arxiv.org/abs/2401.00001',
        doi: '',
        arxiv_id: '2401.00001',
        relevance_score: 0.82,
        verification_status: 'verified',
        source_confidence: 'high',
        pdf_available: true,
        canonicalization_status: 'not_attempted',
        m2_ready: false,
        can_enter_m2: false,
        priority: 'B_SKIM',
        risk_note: 'Not cleared for M2 deep-card generation until full text is downloaded and validated.',
      },
    ],
    recommended_reading_order: [
      {
        rank: 1,
        title: 'Time Series Anomaly Detection with Transformers',
        role: 'TRANSFORMER_METHOD',
        priority: 'B_SKIM',
      },
    ],
    ...overrides,
  }
}

function mockFetch(data: Record<string, any>, ok = true) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    json: async () => data,
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('DirectionSearchView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('submits a query and renders the direction bundle', async () => {
    const fetchMock = mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('SUCCESS')
    expect(wrapper.get('[data-testid="direction-overview"]').text()).toContain('conservative reading landscape')
    expect(wrapper.get('[data-testid="sub-directions"]').text()).toContain('reconstruction-based detection')
    expect(wrapper.get('[data-testid="method-families"]').text()).toContain('Transformer/attention methods')
    expect(wrapper.get('[data-testid="reading-order"]').text()).toContain('B_SKIM')
    expect(wrapper.get('[data-testid="seed-expansion-panel"]').text()).toContain('NOT_IMPLEMENTED')
  })

  it('shows DEGRADED warnings from source failures', async () => {
    mockFetch(directionResponse({
      status: 'DEGRADED',
      direction_workspace_status: 'DEGRADED',
      warnings: ['ACQUISITION_FAILED:openalex: RuntimeError: source unavailable'],
    }))

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('DEGRADED')
    expect(wrapper.get('[data-testid="direction-warning"]').text()).toContain('ACQUISITION_FAILED')
  })

  it('shows an explicit empty-result state', async () => {
    mockFetch(directionResponse({
      status: 'EMPTY_RESULT',
      direction_workspace_status: 'EMPTY_RESULT',
      papers: [],
      candidate_cards: [],
      recommended_reading_order: [],
      message: 'Sources responded, but no candidate passed the relevance/readability filters.',
    }))

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('very narrow topic')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('EMPTY_RESULT')
    expect(wrapper.get('[data-testid="empty-result"]').text()).toContain('没有可展示的候选论文')
  })

  it('renders complete candidate paper fields', async () => {
    mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const card = wrapper.get('[data-testid="candidate-card"]')
    expect(card.text()).toContain('Time Series Anomaly Detection with Transformers')
    expect(card.text()).toContain('source: arxiv')
    expect(card.text()).toContain('relevance: 82%')
    expect(card.text()).toContain('verified: verified')
    expect(card.text()).toContain('pdf: available')
    expect(card.text()).toContain('canonical: not_attempted')
    expect(card.text()).toContain('m2_ready: false')
  })

  it('keeps deep-read disabled when backend has no PaperWorkspace job', async () => {
    mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const button = wrapper.get('[data-testid="deep-read-button"]')
    expect(button.text()).toContain('待接入')
    expect((button.element as HTMLButtonElement).disabled).toBe(true)
  })
})

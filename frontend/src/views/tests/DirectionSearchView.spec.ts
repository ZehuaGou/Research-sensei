import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DirectionSearchView from '../DirectionSearchView.vue'

const routerPush = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

function directionResponse(overrides: Record<string, any> = {}) {
  return {
    status: 'SUCCESS',
    direction_workspace_status: 'SUCCESS',
    message: 'Direction exploration returned a structured bundle from real paper sources.',
    overview: 'time series anomaly detection is organized as a conservative reading landscape.',
    seed_expansion_status: 'READY',
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
        sources: ['arxiv', 'openalex'],
        discovery_sources: ['arxiv', 'openalex'],
        url: 'https://arxiv.org/abs/2401.00001',
        doi: '',
        arxiv_id: '2401.00001',
        arxiv_url: 'https://arxiv.org/abs/2401.00001',
        candidate_pdf_urls: ['https://arxiv.org/pdf/2401.00001.pdf'],
        candidate_source_urls: ['https://arxiv.org/e-print/2401.00001'],
        selected_fulltext_source: 'arxiv_source',
        selected_fulltext_url: 'https://arxiv.org/e-print/2401.00001',
        fulltext_status: 'source_ready',
        fulltext_failure_reason: '',
        can_deep_read: true,
        needs_user_upload: false,
        relevance_score: 0.82,
        verification_status: 'verified',
        source_confidence: 'high',
        pdf_available: true,
        canonicalization_status: 'not_attempted',
        m2_ready: false,
        can_enter_m2: false,
        can_prepare_deep_read: true,
        priority: 'B_SKIM',
        risk_note: 'Not cleared for M2 deep-card generation until full text is downloaded and validated.',
        m2_unavailable_reason: 'Not cleared for M2 deep-card generation until full text is downloaded and validated.',
        deep_read_unavailable_reason: '',
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
    routerPush.mockReset()
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
    expect(wrapper.get('[data-testid="seed-expansion-panel"]').text()).toContain('READY')
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
    expect(card.text()).toContain('相关度 82%')
    expect(card.text()).toContain('验证 verified')
    expect(card.text()).toContain('全文 可用')
    expect(card.text()).toContain('发现来源 arxiv, openalex')
    expect(card.text()).toContain('M2 待验证')
  })

  it('shows prepare deep-read when candidate has a supported source', async () => {
    mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const button = wrapper.get('[data-testid="deep-read-button"]')
    expect(button.text()).toContain('深读这篇')
    expect((button.element as HTMLButtonElement).disabled).toBe(false)
  })

  it('calls handoff API and redirects to PaperWorkspace on success', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => directionResponse(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'JOB_CREATED',
          handoff_status: 'JOB_CREATED',
          job_id: 'job-123',
          final_status: 'DEGRADED_STRUCTURAL',
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('[data-testid="deep-read-button"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/directions/deep_read')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).candidate.arxiv_id).toBe('2401.00001')
    expect(routerPush).toHaveBeenCalledWith('/learn/job-123')
  })

  it('can hand off a DOI-only candidate without sending a non-arXiv landing URL as arxiv_url', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => directionResponse({
          papers: [{
            ...directionResponse().papers[0],
            paper_id: 'doi-1',
            source: 'crossref',
            url: 'https://doi.org/10.1145/example',
            doi: '10.1145/example',
            arxiv_id: '',
            arxiv_url: '',
            pdf_url: '',
            candidate_pdf_urls: [],
            selected_fulltext_url: '',
            fulltext_status: 'metadata_only',
            can_deep_read: false,
            can_prepare_deep_read: true,
            deep_read_unavailable_reason: '',
          }],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'JOB_CREATED',
          handoff_status: 'JOB_CREATED',
          job_id: 'job-doi',
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('doi only paper')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('[data-testid="deep-read-button"]').trigger('click')
    await flushPromises()

    const candidate = JSON.parse(fetchMock.mock.calls[1][1].body).candidate
    expect(candidate.doi).toBe('10.1145/example')
    expect(candidate.arxiv_url).toBe('')
    expect(routerPush).toHaveBeenCalledWith('/learn/job-doi')
  })

  it('shows handoff failure reason on the candidate card', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => directionResponse(),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: {
            status: 'PDF_DOWNLOAD_FAILED',
            message: 'PDF download failed for the direction candidate.',
          },
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('[data-testid="deep-read-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="handoff-error"]').text()).toContain('PDF_DOWNLOAD_FAILED')
    expect(routerPush).not.toHaveBeenCalled()
  })

  it('shows why a candidate is not currently cleared for M2', async () => {
    mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-testid="m2-readiness-note"]').text()).toContain('Not cleared for M2')
  })

  it('passes a selected candidate into SeedExpansionPanel', async () => {
    mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('[data-testid="seed-select-button"]').trigger('click')
    await flushPromises()

    expect((wrapper.get('[data-testid="seed-title-input"]').element as HTMLInputElement).value)
      .toBe('Time Series Anomaly Detection with Transformers')
    expect((wrapper.get('[data-testid="seed-arxiv-input"]').element as HTMLInputElement).value)
      .toBe('2401.00001')
  })

  it('disables handoff when candidate has no supported source', async () => {
    mockFetch(directionResponse({
      papers: [
        {
          paper_id: 'p2',
          title: 'Metadata Only Paper',
          authors: ['A. Researcher'],
          year: 2022,
          source: 'crossref',
          doi: '',
          arxiv_id: '',
          arxiv_url: '',
          pdf_url: '',
          selected_fulltext_source: '',
          selected_fulltext_url: '',
          fulltext_status: 'metadata_only',
          fulltext_failure_reason: 'NO_LEGAL_OA_FULLTEXT_FOUND',
          can_deep_read: false,
          needs_user_upload: true,
          relevance_score: 0.51,
          verification_status: 'unverified',
          source_confidence: 'low',
          pdf_available: false,
          canonicalization_status: 'not_attempted',
          m2_ready: false,
          can_enter_m2: false,
          can_prepare_deep_read: false,
          priority: 'C_REFERENCE',
          deep_read_unavailable_reason: 'No arXiv ID, arXiv URL, or PDF URL is available for this candidate.',
        },
      ],
    }))

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('metadata only')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const button = wrapper.get('[data-testid="deep-read-button"]')
    expect(button.text()).toContain('来源不可用')
    expect((button.element as HTMLButtonElement).disabled).toBe(true)
    expect(wrapper.get('[data-testid="source-unavailable-note"]').text()).toContain('No arXiv ID')
  })
})

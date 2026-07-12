import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SeedExpansionPanel from '../SeedExpansionPanel.vue'

const routerPush = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

function seedResponse(overrides: Record<string, any> = {}) {
  return {
    status: 'SUCCESS',
    seed_expansion_status: 'SUCCESS',
    message: 'Seed expansion returned a source-backed weak-relation reading network.',
    warnings: [],
    upstream_papers: [paper({ paper_id: 'up-1', title: 'Foundations of Time Series Anomaly Detection', relation_type: 'upstream' })],
    downstream_papers: [paper({ paper_id: 'down-1', title: 'Improving Transformer Anomaly Detection', relation_type: 'downstream' })],
    same_route_papers: [paper({ paper_id: 'same-1', title: 'Transformer Routes for Time Series Anomaly Detection', relation_type: 'same_route' })],
    related_surveys: [paper({ paper_id: 'survey-1', title: 'A Survey of Time Series Anomaly Detection', relation_type: 'survey' })],
    follow_up_improvements: [
      { name: 'Upgrade weak relations with citation data', reason: 'Relations remain query-similarity based.' },
    ],
    recommended_expansion_order: [
      { rank: 1, title: 'A Survey of Time Series Anomaly Detection', relation_type: 'survey', can_enter_m2: true },
    ],
    papers: [],
    ...overrides,
  }
}

function paper(overrides: Record<string, any> = {}) {
  return {
    paper_id: 'p1',
    source: 'arxiv',
    title: 'A Seed Expansion Paper',
    authors: ['A. Researcher'],
    year: 2024,
    venue: 'arXiv',
    url: 'https://arxiv.org/abs/2401.00001',
    arxiv_id: '2401.00001',
    arxiv_url: 'https://arxiv.org/abs/2401.00001',
    pdf_url: 'https://arxiv.org/pdf/2401.00001.pdf',
    relation_type: 'upstream',
    relation_reason: 'weak_relation: query similarity, not a verified citation graph.',
    relation_basis: 'query_similarity',
    citation_graph_verified: false,
    confidence: 0.61,
    verification_status: 'verified',
    source_confidence: 'high',
    can_enter_m2: true,
    can_prepare_deep_read: true,
    deep_read_unavailable_reason: '',
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

describe('SeedExpansionPanel', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    routerPush.mockReset()
  })

  it('expands a seed and renders relation groups', async () => {
    mockFetch(seedResponse())

    const wrapper = mount(SeedExpansionPanel)
    await wrapper.get('[data-testid="seed-title-input"]').setValue('Time Series Anomaly Detection')
    await wrapper.get('[data-testid="seed-expand-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="seed-status"]').text()).toContain('SUCCESS')
    expect(wrapper.get('[data-testid="seed-group-upstream_papers"]').text()).toContain('Foundations')
    expect(wrapper.get('[data-testid="seed-group-downstream_papers"]').text()).toContain('Improving')
    expect(wrapper.get('[data-testid="seed-group-same_route_papers"]').text()).toContain('Transformer Routes')
    expect(wrapper.get('[data-testid="seed-group-related_surveys"]').text()).toContain('Survey')
    expect(wrapper.get('[data-testid="seed-relation-reason"]').text()).toContain('weak_relation')
    expect(wrapper.get('[data-testid="seed-confidence"]').text()).toContain('置信度：61%')
    expect(wrapper.get('[data-testid="seed-source"]').text()).toContain('来源：arxiv')
    expect(wrapper.get('[data-testid="seed-verification"]').text()).toContain('verified')
    expect(wrapper.get('[data-testid="seed-can-enter-m2"]').text()).toContain('M2：可进入')
  })

  it('shows DEGRADED warnings from partial source failures', async () => {
    mockFetch(seedResponse({
      status: 'DEGRADED',
      seed_expansion_status: 'DEGRADED',
      warnings: ['SEED_SOURCE_FAILED:downstream:openalex: RuntimeError: source unavailable'],
    }))

    const wrapper = mount(SeedExpansionPanel)
    await wrapper.get('[data-testid="seed-title-input"]').setValue('Time Series Anomaly Detection')
    await wrapper.get('[data-testid="seed-expand-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="seed-status"]').text()).toContain('DEGRADED')
    expect(wrapper.get('[data-testid="seed-warning"]').text()).toContain('SEED_SOURCE_FAILED')
  })

  it('shows EMPTY_RESULT without synthetic papers', async () => {
    mockFetch(seedResponse({
      status: 'EMPTY_RESULT',
      seed_expansion_status: 'EMPTY_RESULT',
      message: 'Sources responded, but no expansion candidates were found.',
      upstream_papers: [],
      downstream_papers: [],
      same_route_papers: [],
      related_surveys: [],
      follow_up_improvements: [],
      recommended_expansion_order: [],
    }))

    const wrapper = mount(SeedExpansionPanel)
    await wrapper.get('[data-testid="seed-title-input"]').setValue('No Result Seed')
    await wrapper.get('[data-testid="seed-expand-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="seed-status"]').text()).toContain('EMPTY_RESULT')
    expect(wrapper.get('[data-testid="seed-empty"]').text()).toContain('no expansion candidates')
    expect(wrapper.find('[data-testid="seed-paper-card"]').exists()).toBe(false)
  })

  it('uses selected candidate props as the seed input', async () => {
    const wrapper = mount(SeedExpansionPanel, {
      props: {
        seed: {
          title: 'Candidate Seed',
          arxiv_id: '2401.00001',
          url: 'https://arxiv.org/abs/2401.00001',
        },
      },
    })

    expect((wrapper.get('[data-testid="seed-title-input"]').element as HTMLInputElement).value).toBe('Candidate Seed')
    expect((wrapper.get('[data-testid="seed-arxiv-input"]').element as HTMLInputElement).value).toBe('2401.00001')
  })

  it('calls handoff API and redirects on prepare deep read success', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => seedResponse(),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'job-456', handoff_status: 'JOB_CREATED' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SeedExpansionPanel)
    await wrapper.get('[data-testid="seed-title-input"]').setValue('Time Series Anomaly Detection')
    await wrapper.get('[data-testid="seed-expand-button"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="seed-deep-read-button"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/directions/jobs/deep_read')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).candidate.arxiv_id).toBe('2401.00001')
    expect(routerPush).toHaveBeenCalledWith('/learn/job-456')
  })

  it('can hand off a DOI-only expansion paper without sending a non-ArXiv URL as arxiv_url', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => seedResponse({
          upstream_papers: [paper({
            paper_id: 'doi-up',
            source: 'crossref',
            title: 'DOI Only Expansion Paper',
            url: 'https://doi.org/10.1145/example',
            doi: '10.1145/example',
            arxiv_id: '',
            arxiv_url: '',
            pdf_url: '',
            can_enter_m2: false,
            can_prepare_deep_read: true,
          })],
          downstream_papers: [],
          same_route_papers: [],
          related_surveys: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'job-doi-seed', handoff_status: 'JOB_CREATED' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SeedExpansionPanel)
    await wrapper.get('[data-testid="seed-title-input"]').setValue('Time Series Anomaly Detection')
    await wrapper.get('[data-testid="seed-expand-button"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="seed-deep-read-button"]').trigger('click')
    await flushPromises()

    const candidate = JSON.parse(fetchMock.mock.calls[1][1].body).candidate
    expect(candidate.doi).toBe('10.1145/example')
    expect(candidate.arxiv_url).toBe('')
    expect(routerPush).toHaveBeenCalledWith('/learn/job-doi-seed')
  })

  it('shows handoff failure reason', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => seedResponse(),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({
          detail: { status: 'PDF_DOWNLOAD_FAILED', message: 'PDF download failed.' },
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(SeedExpansionPanel)
    await wrapper.get('[data-testid="seed-title-input"]').setValue('Time Series Anomaly Detection')
    await wrapper.get('[data-testid="seed-expand-button"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="seed-deep-read-button"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="seed-handoff-error"]').text()).toContain('PDF_DOWNLOAD_FAILED')
    expect(routerPush).not.toHaveBeenCalled()
  })
})

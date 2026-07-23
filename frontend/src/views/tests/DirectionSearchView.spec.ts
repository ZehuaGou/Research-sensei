import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DirectionSearchView from '../DirectionSearchView.vue'
import { researchApi } from '../../api/client'

const routerPush = vi.hoisted(() => vi.fn())
const routeState = vi.hoisted(() => ({ query: {} as Record<string, any> }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
  useRoute: () => routeState,
}))

function directionResponse(overrides: Record<string, any> = {}) {
  return {
    status: 'SUCCESS',
    direction_workspace_status: 'SUCCESS',
    message: 'Direction exploration returned a structured bundle from real paper sources.',
    overview: 'time series anomaly detection is organized as a conservative reading landscape.',
    seed_expansion_status: 'READY',
    warnings: [],
    query_plan: {
      user_query: '时间序列异常检测',
      direction_en: 'time series anomaly detection',
      english_query: 'time series anomaly detection',
      core_terms: ['time series', 'anomaly detection'],
      query_variants: ['time series anomaly detection', 'multivariate time series anomaly detection'],
    },
    key_sub_directions: [
      { name: 'reconstruction-based detection', description: 'Track reconstruction papers.' },
    ],
    method_families: [
      { name: 'Transformer/attention methods', role: 'TRANSFORMER_METHOD', paper_count: 1 },
    ],
    source_resolution: {
      query: 'time series anomaly detection',
      items: [
        {
          paper_id: 'p1',
          download_status: 'downloaded',
          has_valid_deep_reading_source: true,
        },
      ],
    },
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
    window.localStorage.clear()
    routeState.query = {}
    routerPush.mockReset()
  })

  it('opens a historical direction run without re-running direction search', async () => {
    routeState.query = { run_id: 'run-1' }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        search_runs: [
          {
            run_id: 'run-1',
            query: 'time series anomaly detection',
            candidate_count: 2,
            downloaded_count: 1,
            reused_count: 0,
            created_at: '2026-07-04T00:00:00Z',
            papers: [
              {
                paper_id: 'p1',
                title: 'Reusable Historical Paper',
                search_rank: 1,
                action: 'downloaded',
                venue: 'ICML',
                venue_rank: 'A*',
                local_path: 'D:\\workspace\\paper.pdf',
              },
            ],
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(DirectionSearchView)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/library/search_runs?limit=200')
    expect(wrapper.get('[data-testid="direction-history"]').text()).toContain('Reusable Historical Paper')
    expect(wrapper.get('[data-testid="history-deep-read"]').text()).toContain('深读')
  })

  it('opens a downloaded historical paper through a recoverable document task', async () => {
    routeState.query = { run_id: 'run-history-parse' }
    const fetchMock = mockFetch({
      search_runs: [{
        run_id: 'run-history-parse',
        query: 'root system analysis',
        candidate_count: 1,
        downloaded_count: 1,
        reused_count: 0,
        created_at: '2026-07-21T00:00:00Z',
        papers: [{
          paper_id: 'root-toolbox',
          title: 'A Novel Image-Analysis Toolbox',
          search_rank: 1,
          action: 'downloaded',
          local_path: 'D:\\workspace\\root-toolbox.pdf',
        }],
      }],
    })
    let finishParse!: (value: { job_id: string }) => void
    const parseResult = new Promise<{ job_id: string }>((resolve) => {
      finishParse = resolve
    })
    const parseSpy = vi.spyOn(researchApi, 'parseDocumentAsync').mockImplementation(async (form, onProgress) => {
      expect(form.get('local_path')).toBe('D:\\workspace\\root-toolbox.pdf')
      onProgress?.({
        job_id: 'task-history-parse',
        task_id: 'task-history-parse',
        kind: 'document_parse',
        status: 'RUNNING',
        stage: 'parsing_document',
        progress: 20,
        result: { job_id: '' },
        error_type: '',
        error: '',
        cancel_requested: false,
        created_at: '',
        updated_at: '',
      })
      return parseResult as any
    })

    const wrapper = mount(DirectionSearchView)
    await flushPromises()
    await wrapper.get('[data-testid="history-deep-read"]').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(parseSpy).toHaveBeenCalledTimes(1)
    expect(window.localStorage.getItem('researchsensei.historyParse.activeTaskId')).toBe('task-history-parse')
    expect(wrapper.get('[data-testid="direction-task-progress"]').text()).toContain('20%')

    finishParse({ job_id: 'root-toolbox-job' })
    await flushPromises()
    expect(routerPush).toHaveBeenCalledWith('/learn/root-toolbox-job')
    expect(window.localStorage.getItem('researchsensei.historyParse.activeTaskId')).toBeNull()
  })

  it('resumes a persisted historical document task after reload', async () => {
    window.localStorage.setItem('researchsensei.historyParse.activeTaskId', 'task-history-recover')
    const resumeSpy = vi.spyOn(researchApi, 'resumeDocumentParseTask').mockResolvedValue({
      job_id: 'root-toolbox-recovered',
    } as any)

    mount(DirectionSearchView)
    await flushPromises()

    expect(resumeSpy).toHaveBeenCalledWith('task-history-recover', expect.any(Function))
    expect(routerPush).toHaveBeenCalledWith('/learn/root-toolbox-recovered')
    expect(window.localStorage.getItem('researchsensei.historyParse.activeTaskId')).toBeNull()
  })

  it('submits a query and renders the direction bundle', async () => {
    const fetchMock = mockFetch(directionResponse())

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('检索完成')
    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('尝试全文 1 篇 · 成功 1 篇')
    expect(wrapper.get('[data-testid="query-plan"]').text()).toContain('time series anomaly detection')
    expect(wrapper.get('[data-testid="direction-overview"]').text()).toContain('保守的阅读地图')
    expect(wrapper.get('[data-testid="sub-directions"]').text()).toContain('reconstruction-based detection')
    expect(wrapper.get('[data-testid="method-families"]').text()).toContain('Transformer/attention methods')
    expect(wrapper.get('[data-testid="reading-order"]').text()).toContain('快速浏览')
    expect(wrapper.get('[data-testid="seed-expansion-panel"]').text()).toContain('READY')
  })

  it('resumes a persisted direction task after the page reloads', async () => {
    window.localStorage.setItem('researchsensei.directionSearch.activeTaskId', 'task-recover')
    window.localStorage.setItem('researchsensei.directionSearch.activeQuery', '时间序列根因分析')
    const fetchMock = mockFetch({
      job_id: 'task-recover',
      task_id: 'task-recover',
      kind: 'direction_search',
      status: 'SUCCEEDED',
      stage: 'completed',
      progress: 100,
      result: directionResponse(),
      error_type: '',
      error: '',
      cancel_requested: false,
      created_at: '',
      updated_at: '',
    })

    const wrapper = mount(DirectionSearchView)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/directions/jobs/task-recover')
    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('检索完成')
    expect((wrapper.get('[data-testid="direction-query"]').element as HTMLTextAreaElement).value)
      .toBe('时间序列根因分析')
    expect(window.localStorage.getItem('researchsensei.directionSearch.activeTaskId')).toBeNull()
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

    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('部分来源降级')
    expect(wrapper.get('[data-testid="direction-warning"]').text()).toContain('openalex 暂时不可用')
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

    expect(wrapper.get('[data-testid="direction-status"]').text()).toContain('没有可展示候选')
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
    expect(card.text()).toContain('验证 已验证')
    expect(card.text()).toContain('全文 可用')
    expect(card.text()).toContain('发现来源 arxiv, openalex')
    expect(card.text()).toContain('论文代理 待验证')
  })

  it('hides rejected candidates by default and keeps fulltext probes collapsed', async () => {
    const accepted = directionResponse().papers[0]
    mockFetch(directionResponse({
      warnings: ['NO_A_READ_WITH_DOWNLOADABLE_FULL_TEXT'],
      source_metrics: [
        { source: 'paper_search_mcp', success: true, count: 30 },
        { source: 'openalex', success: true, count: 50, trigger: 'low_coverage_oa_supplement' },
        { source: 'unpaywall', success: false, count: 0 },
        { source: 'landing_extractor:repository', success: true, count: 1 },
      ],
      papers: [
        accepted,
        {
          ...accepted,
          paper_id: 'p-filtered',
          title: 'Unrelated Candidate',
          priority: 'D_IGNORE',
          relevance_gate_passed: false,
          download_selected: false,
        },
      ],
    }))

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="candidate-card"]')).toHaveLength(1)
    expect(wrapper.get('[data-testid="toggle-filtered-candidates"]').text()).toContain('查看 1 篇已过滤结果')
    expect(wrapper.get('[data-testid="direction-warning"]').text()).toContain('论文代理建立深读会话')
    expect(wrapper.get('[data-testid="source-ledger"]').text()).not.toContain('unpaywall')
    expect(wrapper.get('.source-probe-details').attributes('open')).toBeUndefined()

    await wrapper.get('[data-testid="toggle-filtered-candidates"]').trigger('click')
    expect(wrapper.findAll('[data-testid="candidate-card"]')).toHaveLength(2)
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
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/directions/jobs/deep_read')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body).candidate.arxiv_id).toBe('2401.00001')
    expect(routerPush).toHaveBeenCalledWith('/learn/job-123')
  })

  it('shows formula batch progress while deep read is running', async () => {
    mockFetch(directionResponse())
    let finishDeepRead!: (value: { job_id: string }) => void
    const deepReadResult = new Promise<{ job_id: string }>((resolve) => {
      finishDeepRead = resolve
    })
    vi.spyOn(researchApi, 'deepReadAsync').mockImplementation(async (_candidate, onProgress) => {
      onProgress?.({
        job_id: 'task-deep',
        task_id: 'task-deep',
        kind: 'direction_deep_read',
        status: 'RUNNING',
        stage: 'building_formula_cards:3/11',
        progress: 61,
        result: { job_id: '' },
        error_type: '',
        error: '',
        cancel_requested: false,
        created_at: '',
        updated_at: '',
      })
      return deepReadResult as any
    })

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.get('[data-testid="deep-read-button"]').trigger('click')
    await flushPromises()

    const progress = wrapper.get('[data-testid="deep-read-progress"]')
    expect(progress.text()).toContain('正在生成公式卡片（3/11 批）')
    expect(progress.text()).toContain('61%')
    expect(window.localStorage.getItem('researchsensei.directionDeepRead.activeTaskId')).toBe('task-deep')

    finishDeepRead({ job_id: 'job-progress' })
    await flushPromises()
    expect(routerPush).toHaveBeenCalledWith('/learn/job-progress')
    expect(window.localStorage.getItem('researchsensei.directionDeepRead.activeTaskId')).toBeNull()
  })

  it('resumes a persisted deep-read task after reload', async () => {
    window.localStorage.setItem('researchsensei.directionDeepRead.activeTaskId', 'task-deep-recover')
    const fetchMock = mockFetch({
      job_id: 'task-deep-recover',
      task_id: 'task-deep-recover',
      kind: 'direction_deep_read',
      status: 'SUCCEEDED',
      stage: 'completed',
      progress: 100,
      result: { job_id: 'paper-recovered' },
      error_type: '',
      error: '',
      cancel_requested: false,
      created_at: '',
      updated_at: '',
    })

    mount(DirectionSearchView)
    await flushPromises()

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/directions/jobs/task-deep-recover')
    expect(routerPush).toHaveBeenCalledWith('/learn/paper-recovered')
    expect(window.localStorage.getItem('researchsensei.directionDeepRead.activeTaskId')).toBeNull()
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

    expect(wrapper.get('[data-testid="m2-readiness-note"]').text()).toContain('尚未准备好深读')
  })

  it('explains publisher browser barriers on the candidate card', async () => {
    const base = directionResponse()
    mockFetch(directionResponse({
      papers: [{
        ...base.papers[0],
        download_error_code: 'BROWSER_ACCESS_REQUIRED',
        browser_diagnostics: { page_barrier: 'subscription_or_login' },
      }],
    }))

    const wrapper = mount(DirectionSearchView)
    await wrapper.get('[data-testid="direction-query"]').setValue('time series anomaly detection')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.get('[data-testid="browser-download-note"]').text()).toContain('机构订阅或购买')
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

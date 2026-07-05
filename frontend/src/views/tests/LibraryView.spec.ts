import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import LibraryView from '../LibraryView.vue'

const routerPush = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

function okJson(data: Record<string, any>) {
  return {
    ok: true,
    json: async () => data,
  }
}

describe('LibraryView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    routerPush.mockReset()
  })

  it('loads papers and search runs', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(okJson({
        papers: [
          {
            paper_id: 'p1',
            title: 'Graph Neural Network-based Anomaly Detection in Multivariate Time Series',
            authors: ['A. Researcher'],
            year: 2024,
            venue: 'AAAI',
            venue_rank: 'A*',
            local_path: 'D:\\workspace\\m1_searches\\topic\\paper.pdf',
            file_size: 1024,
          },
        ],
      }))
      .mockResolvedValueOnce(okJson({
        search_runs: [
          {
            run_id: 'r1',
            query: 'time series anomaly detection',
            candidate_count: 4,
            downloaded_count: 0,
            reused_count: 4,
            created_at: '2026-07-04T00:00:00Z',
          },
        ],
      }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(LibraryView)
    await flushPromises()

    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/library/papers?')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/library/search_runs?limit=20')
    expect(wrapper.get('[data-testid="library-papers"]').text()).toContain('Graph Neural Network-based Anomaly Detection')
    expect(wrapper.get('[data-testid="library-runs"]').text()).toContain('4 reused')
  })

  it('searches and deletes a paper', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(okJson({
        papers: [
          {
            paper_id: 'p1',
            title: 'Reusable Paper',
            venue: 'ICML',
            venue_rank: 'A*',
            local_path: 'paper.pdf',
          },
        ],
      }))
      .mockResolvedValueOnce(okJson({ search_runs: [] }))
      .mockResolvedValueOnce(okJson({
        papers: [
          {
            paper_id: 'p1',
            title: 'Reusable Paper',
            venue: 'ICML',
            venue_rank: 'A*',
            local_path: 'paper.pdf',
          },
        ],
      }))
      .mockResolvedValueOnce(okJson({ status: 'DELETED', paper_id: 'p1' }))
      .mockResolvedValueOnce(okJson({ search_runs: [] }))
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mount(LibraryView)
    await flushPromises()

    await wrapper.get('[data-testid="library-query"]').setValue('graph')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(fetchMock.mock.calls[2][0]).toContain('query=graph')

    await wrapper.get('[data-testid="delete-library-paper"]').trigger('click')
    await flushPromises()

    expect(fetchMock.mock.calls[3][0]).toBe('/api/v1/library/papers/p1')
    expect(fetchMock.mock.calls[3][1]).toEqual({ method: 'DELETE' })
    expect(wrapper.text()).toContain('Paper removed')
  })

  it('opens a downloaded paper in PaperWorkspace', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(okJson({
        papers: [
          {
            paper_id: 'p1',
            title: 'Reusable Paper',
            venue: 'ICML',
            venue_rank: 'A*',
            doi: '10.1000/reusable',
            local_path: 'D:\\workspace\\m1_searches\\topic\\paper.pdf',
          },
        ],
      }))
      .mockResolvedValueOnce(okJson({ search_runs: [] }))
      .mockResolvedValueOnce(okJson({ job_id: 'job-library', status: 'SUCCEEDED' }))
    vi.stubGlobal('fetch', fetchMock)

    const wrapper = mount(LibraryView)
    await flushPromises()

    await wrapper.get('[data-testid="open-library-paper"]').trigger('click')
    await flushPromises()

    expect(fetchMock.mock.calls[2][0]).toBe('/api/v1/documents/parse')
    const parseInit = fetchMock.mock.calls[2][1] as RequestInit
    expect(parseInit.method).toBe('POST')
    const body = parseInit.body as FormData
    expect(body.get('local_path')).toBe('D:\\workspace\\m1_searches\\topic\\paper.pdf')
    expect(body.get('title')).toBe('Reusable Paper')
    expect(body.get('doi')).toBeNull()
    expect(routerPush).toHaveBeenCalledWith('/learn/job-library')
  })
})

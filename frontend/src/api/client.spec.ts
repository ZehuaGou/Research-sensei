import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiClientError, apiRequest, researchApi } from './client'

function response(status: number, payload: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(payload),
  } as Response
}

describe('api client error contract', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('classifies 422 validation issues with machine-readable details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(422, {
      detail: [{ loc: ['body', 'limit'], msg: 'Input should be less than or equal to 200', type: 'less_than_equal' }],
    })))

    const error = await apiRequest('/api/example').catch(value => value)

    expect(error).toBeInstanceOf(ApiClientError)
    expect(error).toMatchObject({ code: 'VALIDATION_ERROR', status: 422 })
    expect((error as ApiClientError).validationIssues[0]?.loc).toEqual(['body', 'limit'])
  })

  it.each([
    [403, 'FORBIDDEN'],
    [409, 'STATE_CONFLICT'],
  ] as const)('classifies HTTP %s as %s', async (status, code) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(status, {
      detail: { code, message: 'controlled failure' },
    })))

    await expect(apiRequest('/api/example')).rejects.toMatchObject({ code, status, message: 'controlled failure' })
  })

  it('distinguishes timeout from caller cancellation', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn((_path: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
    })))

    const timedOut = apiRequest('/api/slow', { timeoutMs: 25 })
    const timeoutAssertion = expect(timedOut).rejects.toMatchObject({ code: 'TIMEOUT' })
    await vi.advanceTimersByTimeAsync(30)
    await timeoutAssertion

    const controller = new AbortController()
    const cancelled = apiRequest('/api/cancel', { signal: controller.signal, timeoutMs: 1_000 })
    const cancelAssertion = expect(cancelled).rejects.toMatchObject({ code: 'CANCELLED' })
    controller.abort()
    await cancelAssertion
  })

  it('uses the persistent direction job API and returns its terminal result', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(202, {
        job_id: 'task-1', task_id: 'task-1', kind: 'direction_search', status: 'PENDING',
        stage: 'queued', progress: 0, result: {}, error_type: '', error: '',
        cancel_requested: false, created_at: '', updated_at: '',
      }))
      .mockResolvedValueOnce(response(200, {
        job_id: 'task-1', task_id: 'task-1', kind: 'direction_search', status: 'SUCCEEDED',
        stage: 'completed', progress: 100, result: { status: 'SUCCESS', papers: [] },
        error_type: '', error: '', cancel_requested: false, created_at: '', updated_at: '',
      }))
    vi.stubGlobal('fetch', fetchMock)
    const progress: string[] = []

    const pending = researchApi.searchDirectionsAsync('graph anomaly detection', task => progress.push(task.status))
    await vi.advanceTimersByTimeAsync(1_100)

    await expect(pending).resolves.toMatchObject({ status: 'SUCCESS' })
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/v1/directions/jobs/search',
      '/api/v1/directions/jobs/task-1',
    ])
    expect(progress).toEqual(['PENDING', 'SUCCEEDED'])
  })

  it('resumes an existing persistent direction task without submitting a duplicate', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(200, {
      job_id: 'task-existing', task_id: 'task-existing', kind: 'direction_search', status: 'SUCCEEDED',
      stage: 'completed', progress: 100, result: { status: 'SUCCESS', papers: [{ title: 'Recovered' }] },
      error_type: '', error: '', cancel_requested: false, created_at: '', updated_at: '',
    })))

    await expect(researchApi.resumeDirectionSearchTask('task-existing')).resolves.toMatchObject({
      status: 'SUCCESS',
      papers: [{ title: 'Recovered' }],
    })
    expect(fetch).toHaveBeenCalledOnce()
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/v1/directions/jobs/task-existing')
  })

  it('keeps machine-readable background task failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(202, {
      job_id: 'task-2', task_id: 'task-2', kind: 'direction_deep_read', status: 'FAILED',
      stage: 'failed', progress: 100, result: {}, error_type: 'RELEVANCE_GATE_FAILED',
      error: 'Candidate is not relevant enough.', cancel_requested: false, created_at: '', updated_at: '',
    })))

    await expect(researchApi.deepReadAsync({ title: 'wrong paper' })).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
      status: 409,
      detail: { code: 'RELEVANCE_GATE_FAILED', status: 'FAILED' },
    })
  })

  it('polls the persistent document task until parsing succeeds', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(202, {
        job_id: 'doc-task', task_id: 'doc-task', kind: 'document_parse', status: 'PENDING',
        stage: 'queued', progress: 0, result: {}, error_type: '', error: '',
        cancel_requested: false, created_at: '', updated_at: '',
      }))
      .mockResolvedValueOnce(response(200, {
        job_id: 'doc-task', task_id: 'doc-task', kind: 'document_parse', status: 'SUCCEEDED',
        stage: 'completed', progress: 100, result: { job_id: 'paper-job' },
        error_type: '', error: '', cancel_requested: false, created_at: '', updated_at: '',
      }))
    vi.stubGlobal('fetch', fetchMock)
    const progress: number[] = []

    const pending = researchApi.parseDocumentAsync(new FormData(), task => progress.push(task.progress))
    await vi.advanceTimersByTimeAsync(800)

    await expect(pending).resolves.toEqual({ job_id: 'paper-job' })
    expect(fetchMock.mock.calls.map(call => call[0])).toEqual([
      '/api/v1/documents/jobs/parse',
      '/api/v1/documents/jobs/doc-task',
    ])
    expect(progress).toEqual([0, 100])
  })
})

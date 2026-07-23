import type {
  AdvisorEvaluateResponse,
  AdvisorQuestionResponse,
  ApiErrorCode,
  ApiErrorDetail,
  ApiErrorPayload,
  AskResponse,
  FormulaExplainResponse,
  DirectionCandidate,
  DirectionResponse,
  DirectionTask,
  DocumentParseResponse,
  JobsResponse,
  LibraryPapersResponse,
  SearchRunsResponse,
  SettingsPayload,
  SettingsValidationResponse,
  MemoryResponse,
  ValidationIssue,
  WorkspaceApi,
} from '../types/api'
import type {
  CardsResponse,
  FormulaCard,
  ReparseResponse,
  UnderstandingStatusResponse,
} from '../types/workspace'
import type {
  LearningAnswerResult,
  LearningOverview,
  LearningSession,
} from '../types/learning'

const DEFAULT_TIMEOUT_MS = 20_000
const TUTOR_REQUEST_TIMEOUT_MS = 120_000
const DIRECTION_TASK_POLL_MS = 1_000
const DIRECTION_TASK_TIMEOUT_MS = 30 * 60_000
const DOCUMENT_TASK_POLL_MS = 750
const DOCUMENT_TASK_TIMEOUT_MS = 15 * 60_000

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: BodyInit | object
  timeoutMs?: number
}

export class ApiClientError extends Error {
  readonly code: ApiErrorCode
  readonly status: number | null
  readonly detail: ApiErrorDetail | null
  readonly validationIssues: ValidationIssue[]

  constructor(options: {
    code: ApiErrorCode
    message: string
    status?: number | null
    detail?: ApiErrorDetail | null
    validationIssues?: ValidationIssue[]
    cause?: unknown
  }) {
    super(options.message, { cause: options.cause })
    this.name = 'ApiClientError'
    this.code = options.code
    this.status = options.status ?? null
    this.detail = options.detail ?? null
    this.validationIssues = options.validationIssues ?? []
  }
}

function codeForStatus(status: number): ApiErrorCode {
  if (status === 422) return 'VALIDATION_ERROR'
  if (status === 403) return 'FORBIDDEN'
  if (status === 409) return 'STATE_CONFLICT'
  if (status === 404) return 'NOT_FOUND'
  return 'HTTP_ERROR'
}

function normalizeErrorPayload(payload: unknown) {
  const body = payload && typeof payload === 'object' ? payload as ApiErrorPayload : {}
  const detail = body.detail
  if (Array.isArray(detail)) {
    return {
      message: detail.map(issue => issue.msg).filter(Boolean).join('；') || '请求参数不符合接口约束。',
      detail: null,
      validationIssues: detail,
    }
  }
  if (typeof detail === 'string') {
    return { message: detail, detail: null, validationIssues: [] }
  }
  if (detail && typeof detail === 'object') {
    return {
      message: typeof detail.message === 'string' && detail.message.trim() ? detail.message : '请求失败。',
      detail,
      validationIssues: [],
    }
  }
  return { message: '请求失败。', detail: null, validationIssues: [] }
}

async function readPayload(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const responseWithText = response as Response & { text?: () => Promise<string> }
  if (typeof responseWithText.text === 'function') {
    const text = await responseWithText.text()
    if (!text) return undefined
    try {
      return JSON.parse(text) as unknown
    } catch {
      return text
    }
  }
  const responseWithJson = response as Response & { json?: () => Promise<unknown> }
  return typeof responseWithJson.json === 'function' ? responseWithJson.json() : undefined
}

function requestBody(body: ApiRequestOptions['body']) {
  if (!body || typeof body !== 'object' || body instanceof Blob || body instanceof FormData || body instanceof URLSearchParams) {
    return body as BodyInit | undefined
  }
  return JSON.stringify(body)
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  let timedOut = false
  const timeout = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const onExternalAbort = () => controller.abort()
  const { timeoutMs: _timeoutMs, signal: externalSignal, body: rawBody, ...requestInit } = options
  externalSignal?.addEventListener('abort', onExternalAbort, { once: true })
  const body = requestBody(rawBody)
  const headers = new Headers(requestInit.headers)
  if (typeof body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const fetchInit: RequestInit = { ...requestInit, signal: controller.signal }
  if ([...headers.keys()].length) fetchInit.headers = Object.fromEntries(headers.entries())
  if (body !== undefined) fetchInit.body = body

  try {
    const response = await fetch(path, fetchInit)
    const payload = await readPayload(response)
    if (!response.ok) {
      const normalized = normalizeErrorPayload(payload)
      throw new ApiClientError({
        code: codeForStatus(response.status),
        status: response.status,
        message: normalized.message,
        detail: normalized.detail,
        validationIssues: normalized.validationIssues,
      })
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiClientError) throw error
    if (controller.signal.aborted) {
      throw new ApiClientError({
        code: timedOut ? 'TIMEOUT' : 'CANCELLED',
        message: timedOut ? '请求超时，请稍后重试。' : '请求已取消。',
        cause: error,
      })
    }
    throw new ApiClientError({
      code: 'NETWORK_ERROR',
      message: '网络请求失败，请确认后端服务正在运行。',
      cause: error,
    })
  } finally {
    window.clearTimeout(timeout)
    externalSignal?.removeEventListener('abort', onExternalAbort)
  }
}

function jobPath(jobId: string, suffix: string) {
  return `/api/v1/jobs/${encodeURIComponent(jobId)}/${suffix}`
}

export const workspaceApi: WorkspaceApi = {
  getUnderstandingStatus(jobId, signal) {
    return apiRequest<UnderstandingStatusResponse>(jobPath(jobId, 'understanding_status'), { signal })
  },
  getCards(jobId, signal) {
    return apiRequest<CardsResponse>(jobPath(jobId, 'cards'), { signal })
  },
  reparse(jobId, signal, onProgress) {
    return waitForSubmittedTask<ReparseResponse>(
      apiRequest<DirectionTask<ReparseResponse>>(`/api/v1/documents/jobs/${encodeURIComponent(jobId)}/reparse`, {
        method: 'POST',
        signal,
      }),
      taskId => researchApi.getDocumentJob<ReparseResponse>(taskId, signal),
      onProgress,
      signal,
      DOCUMENT_TASK_POLL_MS,
      DOCUMENT_TASK_TIMEOUT_MS,
    )
  },
  getMemory(jobId, signal) {
    return apiRequest<MemoryResponse>(jobPath(jobId, 'memory'), { signal })
  },
  async clearMemory(jobId, signal) {
    await apiRequest<void>(jobPath(jobId, 'memory'), { method: 'DELETE', signal })
  },
  ask(jobId, request, signal) {
    return apiRequest<AskResponse>(jobPath(jobId, 'ask'), {
      method: 'POST',
      body: request,
      signal,
      timeoutMs: TUTOR_REQUEST_TIMEOUT_MS,
    })
  },
  advisorQuestion(jobId, request, signal) {
    return apiRequest<AdvisorQuestionResponse>(jobPath(jobId, 'advisor/question'), {
      method: 'POST',
      body: request,
      signal,
      timeoutMs: TUTOR_REQUEST_TIMEOUT_MS,
    })
  },
  advisorEvaluate(jobId, request, signal) {
    return apiRequest<AdvisorEvaluateResponse>(jobPath(jobId, 'advisor/evaluate'), {
      method: 'POST',
      body: request,
      signal,
      timeoutMs: TUTOR_REQUEST_TIMEOUT_MS,
    })
  },
  explainFormula(jobId, card: FormulaCard, signal) {
    return apiRequest<FormulaExplainResponse>(jobPath(jobId, 'formula/explain'), {
      method: 'POST',
      body: { formula_id: card.formula_id || card.formula_ref || '' },
      signal,
      timeoutMs: TUTOR_REQUEST_TIMEOUT_MS,
    })
  },
}

export const learningApi = {
  getOverview(jobId?: string, signal?: AbortSignal) {
    const path = jobId ? jobPath(jobId, 'learning') : '/api/v1/learning'
    return apiRequest<LearningOverview>(path, { signal })
  },
  importPaper(jobId: string, signal?: AbortSignal) {
    return apiRequest<{ job_id: string; imported_count: number; overview: LearningOverview }>(
      jobPath(jobId, 'learning/import'),
      { method: 'POST', signal },
    )
  },
  startSession(
    jobId: string,
    options: { count?: number; include_not_due?: boolean } = {},
    signal?: AbortSignal,
  ) {
    return apiRequest<LearningSession>(jobPath(jobId, 'learning/sessions'), {
      method: 'POST',
      body: {
        count: options.count ?? 5,
        include_not_due: options.include_not_due ?? false,
      },
      signal,
      timeoutMs: TUTOR_REQUEST_TIMEOUT_MS,
    })
  },
  getActiveSession(jobId: string, signal?: AbortSignal) {
    return apiRequest<{ job_id: string; session: LearningSession | null }>(
      jobPath(jobId, 'learning/active-session'),
      { signal, timeoutMs: TUTOR_REQUEST_TIMEOUT_MS },
    )
  },
  getSession(jobId: string, sessionId: string, signal?: AbortSignal) {
    return apiRequest<LearningSession>(
      jobPath(jobId, `learning/sessions/${encodeURIComponent(sessionId)}`),
      { signal, timeoutMs: TUTOR_REQUEST_TIMEOUT_MS },
    )
  },
  answer(jobId: string, sessionId: string, userAnswer: string, signal?: AbortSignal) {
    return apiRequest<LearningAnswerResult>(
      jobPath(jobId, `learning/sessions/${encodeURIComponent(sessionId)}/answer`),
      {
        method: 'POST',
        body: { user_answer: userAnswer },
        signal,
        timeoutMs: TUTOR_REQUEST_TIMEOUT_MS,
      },
    )
  },
}

export const researchApi = {
  listJobs(signal?: AbortSignal) {
    return apiRequest<JobsResponse>('/api/v1/jobs', { signal })
  },
  async deleteJob(jobId: string, signal?: AbortSignal) {
    await apiRequest<void>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE', signal })
  },
  listLibraryPapers(query: string, limit: number, signal?: AbortSignal, offset = 0) {
    const params = new URLSearchParams({ query, limit: String(limit), offset: String(offset) })
    return apiRequest<LibraryPapersResponse>(`/api/v1/library/papers?${params.toString()}`, { signal })
  },
  listSearchRuns(limit: number, signal?: AbortSignal) {
    return apiRequest<SearchRunsResponse>(`/api/v1/library/search_runs?limit=${limit}`, { signal })
  },
  async deleteLibraryPaper(paperId: string, signal?: AbortSignal) {
    await apiRequest<void>(`/api/v1/library/papers/${encodeURIComponent(paperId)}`, { method: 'DELETE', signal })
  },
  parseDocument(form: FormData, signal?: AbortSignal) {
    return apiRequest<DocumentParseResponse>('/api/v1/documents/parse', {
      method: 'POST',
      body: form,
      signal,
      timeoutMs: 120_000,
    })
  },
  createDocumentParseJob(form: FormData, signal?: AbortSignal) {
    return apiRequest<DirectionTask<DocumentParseResponse>>('/api/v1/documents/jobs/parse', {
      method: 'POST',
      body: form,
      signal,
      timeoutMs: 60_000,
    })
  },
  getDocumentJob<T = Record<string, unknown>>(taskId: string, signal?: AbortSignal) {
    return apiRequest<DirectionTask<T>>(`/api/v1/documents/jobs/${encodeURIComponent(taskId)}`, { signal })
  },
  cancelDocumentJob(taskId: string, signal?: AbortSignal) {
    return apiRequest<DirectionTask>(`/api/v1/documents/jobs/${encodeURIComponent(taskId)}`, {
      method: 'DELETE',
      signal,
    })
  },
  async parseDocumentAsync(
    form: FormData,
    onProgress?: (task: DirectionTask<DocumentParseResponse>) => void,
    signal?: AbortSignal,
  ) {
    return waitForSubmittedTask(
      this.createDocumentParseJob(form, signal),
      taskId => this.getDocumentJob<DocumentParseResponse>(taskId, signal),
      onProgress,
      signal,
      DOCUMENT_TASK_POLL_MS,
      DOCUMENT_TASK_TIMEOUT_MS,
    )
  },
  async resumeDocumentParseTask(
    taskId: string,
    onProgress?: (task: DirectionTask<DocumentParseResponse>) => void,
    signal?: AbortSignal,
  ) {
    const task = await this.getDocumentJob<DocumentParseResponse>(taskId, signal)
    return waitForTask(
      task,
      id => this.getDocumentJob<DocumentParseResponse>(id, signal),
      onProgress,
      signal,
      DOCUMENT_TASK_POLL_MS,
      DOCUMENT_TASK_TIMEOUT_MS,
    )
  },
  async resumeDocumentTask<T>(
    taskId: string,
    onProgress?: (task: DirectionTask<T>) => void,
    signal?: AbortSignal,
  ) {
    const task = await this.getDocumentJob<T>(taskId, signal)
    return waitForTask(
      task,
      id => this.getDocumentJob<T>(id, signal),
      onProgress,
      signal,
      DOCUMENT_TASK_POLL_MS,
      DOCUMENT_TASK_TIMEOUT_MS,
    )
  },
  searchDirections(query: string, signal?: AbortSignal) {
    return apiRequest<DirectionResponse>('/api/v1/directions/search', {
      method: 'POST',
      body: { query },
      signal,
      timeoutMs: 120_000,
    })
  },
  createDirectionSearchJob(query: string, signal?: AbortSignal) {
    return apiRequest<DirectionTask<DirectionResponse>>('/api/v1/directions/jobs/search', {
      method: 'POST',
      body: { query },
      signal,
    })
  },
  createDirectionDeepReadJob(candidate: DirectionCandidate, signal?: AbortSignal) {
    return apiRequest<DirectionTask<DocumentParseResponse>>('/api/v1/directions/jobs/deep_read', {
      method: 'POST',
      body: { candidate },
      signal,
    })
  },
  getDirectionJob<T = Record<string, unknown>>(taskId: string, signal?: AbortSignal) {
    return apiRequest<DirectionTask<T>>(`/api/v1/directions/jobs/${encodeURIComponent(taskId)}`, { signal })
  },
  cancelDirectionJob(taskId: string, signal?: AbortSignal) {
    return apiRequest<DirectionTask>(`/api/v1/directions/jobs/${encodeURIComponent(taskId)}`, {
      method: 'DELETE',
      signal,
    })
  },
  async searchDirectionsAsync(
    query: string,
    onProgress?: (task: DirectionTask<DirectionResponse>) => void,
    signal?: AbortSignal,
  ) {
    const task = await this.createDirectionSearchJob(query, signal)
    if (!isDirectionTask(task)) return task as unknown as DirectionResponse
    return waitForTask(task, id => this.getDirectionJob<DirectionResponse>(id, signal), onProgress, signal)
  },
  async resumeDirectionSearchTask(
    taskId: string,
    onProgress?: (task: DirectionTask<DirectionResponse>) => void,
    signal?: AbortSignal,
  ) {
    const task = await this.getDirectionJob<DirectionResponse>(taskId, signal)
    return waitForTask(
      task,
      id => this.getDirectionJob<DirectionResponse>(id, signal),
      onProgress,
      signal,
      DIRECTION_TASK_POLL_MS,
      DIRECTION_TASK_TIMEOUT_MS,
    )
  },
  expandSeed(seed: DirectionCandidate, signal?: AbortSignal) {
    return apiRequest<DirectionResponse>('/api/v1/directions/seed_expansion', {
      method: 'POST',
      body: { seed },
      signal,
      timeoutMs: 120_000,
    })
  },
  deepRead(candidate: DirectionCandidate, signal?: AbortSignal) {
    return apiRequest<DocumentParseResponse>('/api/v1/directions/deep_read', {
      method: 'POST',
      body: { candidate },
      signal,
      timeoutMs: 120_000,
    })
  },
  async deepReadAsync(
    candidate: DirectionCandidate,
    onProgress?: (task: DirectionTask<DocumentParseResponse>) => void,
    signal?: AbortSignal,
  ) {
    const task = await this.createDirectionDeepReadJob(candidate, signal)
    if (!isDirectionTask(task)) return task as unknown as DocumentParseResponse
    return waitForTask(task, id => this.getDirectionJob<DocumentParseResponse>(id, signal), onProgress, signal)
  },
  async resumeDirectionDeepReadTask(
    taskId: string,
    onProgress?: (task: DirectionTask<DocumentParseResponse>) => void,
    signal?: AbortSignal,
  ) {
    const task = await this.getDirectionJob<DocumentParseResponse>(taskId, signal)
    return waitForTask(
      task,
      id => this.getDirectionJob<DocumentParseResponse>(id, signal),
      onProgress,
      signal,
    )
  },
  getSettings(signal?: AbortSignal) {
    return apiRequest<SettingsPayload>('/api/v1/settings', { signal })
  },
  updateSettings(update: { model?: string; paper_model?: string; tutor_model?: string }, signal?: AbortSignal) {
    return apiRequest<SettingsPayload>('/api/v1/settings', { method: 'PATCH', body: update, signal })
  },
  validateSettings(signal?: AbortSignal) {
    return apiRequest<SettingsValidationResponse>('/api/v1/settings/test', { method: 'POST', signal, timeoutMs: 15_000 })
  },
}

function isDirectionTask(value: unknown): value is DirectionTask<never> {
  if (!value || typeof value !== 'object') return false
  const task = value as Partial<DirectionTask>
  return typeof task.task_id === 'string'
    && task.task_id.length > 0
    && typeof task.status === 'string'
}

async function waitForSubmittedTask<T>(
  submission: Promise<DirectionTask<T>>,
  getTask: (taskId: string) => Promise<DirectionTask<T>>,
  onProgress?: (task: DirectionTask<T>) => void,
  signal?: AbortSignal,
  pollMs = DIRECTION_TASK_POLL_MS,
  timeoutMs = DIRECTION_TASK_TIMEOUT_MS,
): Promise<T> {
  const task = await submission
  if (!isDirectionTask(task)) return task as unknown as T
  return waitForTask(task, getTask, onProgress, signal, pollMs, timeoutMs)
}

async function waitForTask<T>(
  initialTask: DirectionTask<T>,
  getTask: (taskId: string) => Promise<DirectionTask<T>>,
  onProgress?: (task: DirectionTask<T>) => void,
  signal?: AbortSignal,
  pollMs = DIRECTION_TASK_POLL_MS,
  timeoutMs = DIRECTION_TASK_TIMEOUT_MS,
): Promise<T> {
  const startedAt = Date.now()
  let task = initialTask
  while (true) {
    onProgress?.(task)
    if (task.status === 'SUCCEEDED') return task.result
    if (['FAILED', 'CANCELLED', 'INTERRUPTED'].includes(task.status)) {
      throw new ApiClientError({
        code: 'STATE_CONFLICT',
        status: 409,
        message: task.error || `后台任务以 ${task.status} 结束。`,
        detail: {
          code: task.error_type || `TASK_${task.status}`,
          status: task.status,
          message: task.error || `后台任务以 ${task.status} 结束。`,
          stage: task.stage,
        },
      })
    }
    if (signal?.aborted) {
      throw new ApiClientError({ code: 'CANCELLED', message: '请求已取消。' })
    }
    if (Date.now() - startedAt >= timeoutMs) {
      throw new ApiClientError({ code: 'TIMEOUT', message: '后台任务超时，请稍后重试。' })
    }
    await pollDelay(pollMs, signal)
    task = await getTask(task.task_id)
  }
}

function pollDelay(milliseconds: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const finish = () => {
      signal?.removeEventListener('abort', cancel)
      resolve()
    }
    const cancel = () => {
      window.clearTimeout(timeout)
      reject(new ApiClientError({ code: 'CANCELLED', message: '请求已取消。' }))
    }
    const timeout = window.setTimeout(finish, milliseconds)
    signal?.addEventListener('abort', cancel, { once: true })
  })
}

export function apiErrorMessage(error: unknown, fallback: string) {
  if (!(error instanceof ApiClientError)) return fallback
  if (error.code === 'VALIDATION_ERROR') return error.message || '请求参数不符合接口约束。'
  if (error.code === 'FORBIDDEN') return error.detail?.message as string || '当前状态不允许执行此操作。'
  if (error.code === 'STATE_CONFLICT') return error.detail?.message as string || '任务状态已变化，请刷新后重试。'
  if (error.code === 'TIMEOUT') return '请求超时，请稍后重试。'
  if (error.code === 'CANCELLED') return '请求已取消。'
  if (error.code === 'NETWORK_ERROR') return '网络请求失败，请确认后端服务正在运行。'
  return error.message || fallback
}

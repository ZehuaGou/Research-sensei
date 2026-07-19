import type {
  CardsResponse,
  FormulaCard,
  ReparseResponse,
  UnderstandingStatusResponse,
} from './workspace'

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'FORBIDDEN'
  | 'STATE_CONFLICT'
  | 'NOT_FOUND'
  | 'TIMEOUT'
  | 'CANCELLED'
  | 'NETWORK_ERROR'
  | 'HTTP_ERROR'

export interface ApiErrorDetail {
  code?: string
  message?: string
  status?: string
  blocking_reason?: string
  warnings?: Array<{ code: string; message: string }>
  [key: string]: unknown
}

export interface ValidationIssue {
  loc?: Array<string | number>
  msg?: string
  type?: string
}

export interface ApiErrorPayload {
  detail?: string | ApiErrorDetail | ValidationIssue[]
}

export interface ConversationMessageRequest {
  role: 'user' | 'assistant'
  content: string
}

export interface AskRequest {
  question: string
  selected_text?: string
  context_scope: 'selection' | 'paper'
  conversation_history?: ConversationMessageRequest[]
}

export interface M4ContextTrace {
  scope: 'selection' | 'paper'
  continued_from_history: boolean
  focus_question: string
  evidence_count: number
  selected_text_used: boolean
}

export interface AskResponse {
  answer: string
  status?: string
  evidence_refs?: string[]
  uncertainty?: string
  follow_up_suggestions?: string[]
  context_trace?: M4ContextTrace
  [key: string]: unknown
}

export interface MemoryResponse {
  records: unknown[]
  warning?: string
  schema_version?: number
}

export interface AdvisorQuestionRequest {
  advisor_mode: 'group_meeting'
  user_question?: string
  selected_text?: string
}

export interface AdvisorQuestionResponse {
  question: string
  user_question?: string
  expected_answer_points?: string[]
  answer_format?: string[]
  evidence_refs?: string[]
}

export interface AdvisorEvaluateRequest {
  question: string
  user_question: string
  user_answer: string
  expected_answer_points: string[]
  evidence_refs: string[]
}

export interface AdvisorEvaluateResponse {
  feedback?: string
  score?: number
  missing_points?: string[]
  covered_points?: string[]
  next_question?: string
}

export interface FormulaExplainResponse {
  meaning?: string
  intuition?: string
  numeric_example?: string
  role_in_method?: string
  evidence_refs?: string[]
  status?: string
}

export interface JobSummary {
  job_id: string
  status?: string
  source_path?: string
  title?: string
  created_at?: string
  [key: string]: unknown
}

export interface JobsResponse {
  jobs: JobSummary[]
}

export interface LibraryPaper {
  paper_id: string
  title: string
  authors?: string[]
  year?: number | null
  venue?: string
  venue_canonical_name?: string
  venue_rank?: string
  doi?: string
  arxiv_id?: string
  local_path?: string
  file_size?: number
  downloaded_at?: string
  [key: string]: unknown
}

export interface SearchRunPaper {
  paper_id?: string
  title: string
  search_rank?: number
  action?: string
  reason?: string
  download_selected?: boolean
  venue?: string
  venue_rank?: string
  local_path?: string
  [key: string]: unknown
}

export interface SearchRun {
  run_id: string
  query: string
  created_at: string
  candidate_count: number
  downloaded_count: number
  reused_count: number
  papers?: SearchRunPaper[]
  [key: string]: unknown
}

export interface LibraryPapersResponse {
  papers: LibraryPaper[]
  total: number
  limit: number
  offset: number
}

export interface SearchRunsResponse {
  search_runs: SearchRun[]
}

export interface DocumentParseResponse {
  job_id: string
  [key: string]: unknown
}

export interface DirectionCandidate {
  title?: string
  doi?: string
  arxiv_id?: string
  arxiv_url?: string
  pdf_url?: string
  [key: string]: unknown
}

export interface DirectionResponse {
  status?: string
  direction_workspace_status?: string
  warnings?: Array<string | { code: string; message: string }>
  papers?: DirectionCandidate[]
  candidate_cards?: DirectionCandidate[]
  query_plan?: Record<string, unknown>
  [key: string]: unknown
}

export type DirectionTaskStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'CANCEL_REQUESTED'
  | 'CANCELLED'
  | 'INTERRUPTED'

export interface DirectionTask<T = Record<string, unknown>> {
  job_id: string
  task_id: string
  kind: 'direction_search' | 'direction_deep_read' | string
  status: DirectionTaskStatus
  stage: string
  progress: number
  result: T
  error_type: string
  error: string
  cancel_requested: boolean
  created_at: string
  updated_at: string
}

export interface SettingsPayload {
  active_provider: string
  provider_display_name?: string
  provider_key?: string
  provider_kind?: string
  base_url: string
  request_endpoint?: string
  api_key_env: string
  auth_header?: string
  model: string
  model_options?: Array<{ id: string; label?: string; source?: string }>
  model_env?: string
  route_note?: string
  enable_env?: string
  llm_enabled?: boolean
  api_key_configured?: boolean
  provider_known?: boolean
}

export interface SettingsValidationResponse {
  ok: boolean
  message?: string
  error_type?: string
}

export interface WorkspaceApi {
  getUnderstandingStatus(jobId: string, signal?: AbortSignal): Promise<UnderstandingStatusResponse>
  getCards(jobId: string, signal?: AbortSignal): Promise<CardsResponse>
  reparse(
    jobId: string,
    signal?: AbortSignal,
    onProgress?: (task: DirectionTask<ReparseResponse>) => void,
  ): Promise<ReparseResponse>
  getMemory(jobId: string, signal?: AbortSignal): Promise<MemoryResponse>
  clearMemory(jobId: string, signal?: AbortSignal): Promise<void>
  ask(jobId: string, request: AskRequest, signal?: AbortSignal): Promise<AskResponse>
  advisorQuestion(jobId: string, request: AdvisorQuestionRequest, signal?: AbortSignal): Promise<AdvisorQuestionResponse>
  advisorEvaluate(jobId: string, request: AdvisorEvaluateRequest, signal?: AbortSignal): Promise<AdvisorEvaluateResponse>
  explainFormula(jobId: string, card: FormulaCard, signal?: AbortSignal): Promise<FormulaExplainResponse>
}

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SeedExpansionPanel from '../components/SeedExpansionPanel.vue'
import { ApiClientError, apiErrorMessage, researchApi } from '../api/client'
import type { SearchRun, SearchRunPaper } from '../types/api'
import { formatTaskStage } from '../utils/taskStage'

const ACTIVE_DIRECTION_TASK_KEY = 'researchsensei.directionSearch.activeTaskId'
const ACTIVE_DIRECTION_QUERY_KEY = 'researchsensei.directionSearch.activeQuery'
const ACTIVE_DEEP_READ_TASK_KEY = 'researchsensei.directionDeepRead.activeTaskId'
const ACTIVE_HISTORY_PARSE_TASK_KEY = 'researchsensei.historyParse.activeTaskId'

const router = useRouter()
const route = useRoute()
const query = ref('')
const isLoading = ref(false)
const taskId = ref('')
const taskStage = ref('')
const taskProgress = ref(0)
const isHistoryLoading = ref(false)
const error = ref('')
const historyError = ref('')
const result = ref<Record<string, any> | null>(null)
const historyRun = ref<SearchRun | null>(null)
const openingHistoryKey = ref('')
interface HandoffState {
  loading?: boolean
  error?: string
  stage?: string
  progress?: number
  taskId?: string
}

const handoffStates = ref<Record<string, HandoffState>>({})
const selectedSeed = ref<Record<string, any> | null>(null)
const showFilteredCandidates = ref(false)

const status = computed(() => result.value?.direction_workspace_status || result.value?.status || '')
const warnings = computed(() => normalizeWarnings(result.value?.warnings || []))
const allPapers = computed<Array<Record<string, any>>>(() => result.value?.papers || result.value?.candidate_cards || [])
const relevantPapers = computed(() => allPapers.value.filter((paper) => (
  paper.relevance_gate_passed === true || paper.download_selected === true || paper.priority !== 'D_IGNORE'
)))
const papers = computed(() => showFilteredCandidates.value ? allPapers.value : relevantPapers.value)
const filteredCandidateCount = computed(() => Math.max(allPapers.value.length - relevantPapers.value.length, 0))
const hasEmptyResult = computed(() => ['EMPTY_RESULT', 'BLOCKED'].includes(String(status.value)))
const queryPlan = computed(() => result.value?.query_plan || null)
const historyPapers = computed(() => historyRun.value?.papers || [])
const historyReadyPapers = computed(() => historyPapers.value.filter((paper) => Boolean(paper.local_path)))
const currentDirectionLabel = computed(() => historyRun.value?.query || result.value?.query_plan?.english_query || query.value.trim() || '新的研究方向')
const activeCandidateCount = computed(() => historyRun.value ? (historyRun.value.candidate_count || historyPapers.value.length) : papers.value.length)
const activeReadyCount = computed(() => {
  if (historyRun.value) return historyReadyPapers.value.length
  return papers.value.filter((paper: Record<string, any>) => hasDeepReadSource(paper)).length
})
const currentNextStep = computed(() => {
  if (isLoading.value) return '正在检索'
  if (isHistoryLoading.value) return '正在加载历史'
  if (historyRun.value) return historyReadyPapers.value.length ? '选择论文深读' : '需要重新检索'
  if (result.value && papers.value.length) return '筛选候选论文'
  if (result.value && hasEmptyResult.value) return '换一个更具体方向'
  return '输入方向'
})
const taskStageLabel = computed(() => {
  return formatTaskStage(taskStage.value)
})
const panelNote = computed(() => {
  if (historyRun.value) return '历史方向只读取已有论文。只有点击“重新检索”或底部发送，才会重新搜索和下载。'
  if (result.value) return '候选论文会按相关性与全文可用性展示；已验证 PDF 可直接交给论文代理深读。'
  return '输入方向后会检索真实论文来源；点击左侧历史方向时不会自动重新下载。'
})
const queryPlanMode = computed(() => {
  if (!queryPlan.value) return ''
  if (warnings.value.some((warning) => warning.code === 'HEURISTIC_QUERY_PLAN_NO_LLM')) return '本地规划'
  if (warnings.value.some((warning) => warning.code === 'LLM_QUERY_PLAN_FAILED')) return 'LLM 降级'
  return 'LLM 规划'
})
const queryVariants = computed(() => toTextList(queryPlan.value?.query_variants).slice(0, 6))
const queryCoreTerms = computed(() => toTextList(queryPlan.value?.core_terms).slice(0, 8))
const sourceMetrics = computed<Array<Record<string, any>>>(() => (
  Array.isArray(result.value?.source_metrics) ? result.value.source_metrics : []
))
const acquisitionSourceMetrics = computed(() => sourceMetrics.value.filter((metric) => (
  !String(metric.source || '').startsWith('landing_extractor:') && metric.source !== 'unpaywall'
)))
const fulltextProbeMetrics = computed(() => sourceMetrics.value.filter((metric) => (
  String(metric.source || '').startsWith('landing_extractor:') || metric.source === 'unpaywall'
)))
const successfulFulltextProbes = computed(() => fulltextProbeMetrics.value.filter((metric) => metric.success).length)
const sourceResolutionItems = computed<Array<Record<string, any>>>(() => (
  Array.isArray(result.value?.source_resolution?.items) ? result.value.source_resolution.items : []
))
const downloadAttemptCount = computed(() => sourceResolutionItems.value.length)
const downloadedPaperCount = computed(() => sourceResolutionItems.value.filter((item) => (
  item.download_status === 'downloaded' && item.has_valid_deep_reading_source === true
)).length)

onMounted(() => {
  const savedHistoryParseTaskId = window.localStorage.getItem(ACTIVE_HISTORY_PARSE_TASK_KEY)
  if (savedHistoryParseTaskId) {
    void resumeActiveHistoryParseTask(savedHistoryParseTaskId)
    return
  }
  const savedDeepReadTaskId = window.localStorage.getItem(ACTIVE_DEEP_READ_TASK_KEY)
  if (savedDeepReadTaskId) {
    void resumeActiveDeepReadTask(savedDeepReadTaskId)
    return
  }
  const savedTaskId = window.localStorage.getItem(ACTIVE_DIRECTION_TASK_KEY)
  const openingHistory = Boolean(route.query.run_id || route.query.history_q)
  if (savedTaskId && !openingHistory) {
    void resumeActiveDirectionTask(savedTaskId)
    return
  }
  syncQueryFromRoute()
})

async function resumeActiveDeepReadTask(savedTaskId: string) {
  isLoading.value = true
  error.value = ''
  taskId.value = savedTaskId
  taskStage.value = 'starting'
  try {
    const data = await researchApi.resumeDirectionDeepReadTask(savedTaskId, task => {
      taskId.value = task.task_id
      taskStage.value = task.stage
      taskProgress.value = task.progress
    })
    clearActiveDeepReadTask()
    await router.push(`/learn/${data.job_id}`)
  } catch (resumeError) {
    if (isRecoverableDirectionTaskError(resumeError)) {
      error.value = '论文深读仍在后台继续，连接恢复后会继续读取进度。'
    } else {
      clearActiveDeepReadTask()
      error.value = apiErrorMessage(resumeError, '之前的论文深读任务无法恢复，请重新提交。')
    }
  } finally {
    isLoading.value = false
    taskStage.value = ''
  }
}

function clearActiveDeepReadTask() {
  taskId.value = ''
  taskStage.value = ''
  taskProgress.value = 0
  window.localStorage.removeItem(ACTIVE_DEEP_READ_TASK_KEY)
}

function updateHistoryParseTask(task: { task_id: string; stage: string; progress: number }) {
  taskId.value = task.task_id
  taskStage.value = task.stage
  taskProgress.value = task.progress
  window.localStorage.setItem(ACTIVE_HISTORY_PARSE_TASK_KEY, task.task_id)
}

function clearActiveHistoryParseTask() {
  taskId.value = ''
  taskStage.value = ''
  taskProgress.value = 0
  window.localStorage.removeItem(ACTIVE_HISTORY_PARSE_TASK_KEY)
}

async function resumeActiveHistoryParseTask(savedTaskId: string) {
  isLoading.value = true
  error.value = ''
  historyError.value = ''
  taskId.value = savedTaskId
  taskStage.value = 'starting'
  try {
    const data = await researchApi.resumeDocumentParseTask(savedTaskId, updateHistoryParseTask)
    clearActiveHistoryParseTask()
    await router.push(`/learn/${data.job_id}`)
  } catch (resumeError) {
    if (isRecoverableDirectionTaskError(resumeError)) {
      historyError.value = '论文仍在后台解析；连接恢复或刷新页面后会继续读取进度。'
    } else {
      clearActiveHistoryParseTask()
      historyError.value = apiErrorMessage(resumeError, '之前的历史论文解析任务无法恢复，请重新提交。')
    }
  } finally {
    isLoading.value = false
  }
}

watch(() => [route.query.q, route.query.run_id, route.query.history_q], () => {
  syncQueryFromRoute()
})

function syncQueryFromRoute() {
  const runId = String(route.query.run_id || '').trim()
  const historyQuery = String(route.query.history_q || '').trim()
  if (runId || historyQuery) {
    void loadHistoryRun({ runId, query: historyQuery })
    return
  }
  const routedQuery = String(route.query.q || '').trim()
  if (!routedQuery || routedQuery === query.value.trim()) return
  query.value = routedQuery
  void search()
}

async function search() {
  if (!query.value.trim() || isLoading.value) return
  isLoading.value = true
  error.value = ''
  historyError.value = ''
  result.value = null
  historyRun.value = null
  handoffStates.value = {}
  selectedSeed.value = null
  taskStage.value = 'queued'
  taskProgress.value = 0
  const submittedQuery = query.value.trim()
  try {
    const data = await researchApi.searchDirectionsAsync(submittedQuery, task => updateDirectionTask(task, submittedQuery))
    clearActiveDirectionTask()
    result.value = data
  } catch (searchError) {
    if (isRecoverableDirectionTaskError(searchError)) {
      error.value = '后台检索仍在继续，页面刷新后会自动恢复这个任务。'
    } else {
      clearActiveDirectionTask()
      error.value = apiErrorMessage(searchError, '方向检索失败。')
    }
  } finally {
    isLoading.value = false
    taskStage.value = ''
  }
}

function updateDirectionTask(task: { task_id: string; stage: string; progress: number }, submittedQuery = query.value.trim()) {
  taskId.value = task.task_id
  taskStage.value = task.stage
  taskProgress.value = task.progress
  window.localStorage.setItem(ACTIVE_DIRECTION_TASK_KEY, task.task_id)
  window.localStorage.setItem(ACTIVE_DIRECTION_QUERY_KEY, submittedQuery)
}

function clearActiveDirectionTask() {
  taskId.value = ''
  taskStage.value = ''
  taskProgress.value = 0
  window.localStorage.removeItem(ACTIVE_DIRECTION_TASK_KEY)
  window.localStorage.removeItem(ACTIVE_DIRECTION_QUERY_KEY)
}

function isRecoverableDirectionTaskError(value: unknown) {
  return Boolean(
    taskId.value
    && value instanceof ApiClientError
    && ['TIMEOUT', 'NETWORK_ERROR', 'CANCELLED'].includes(value.code),
  )
}

async function resumeActiveDirectionTask(savedTaskId: string) {
  if (isLoading.value) return
  const savedQuery = window.localStorage.getItem(ACTIVE_DIRECTION_QUERY_KEY) || ''
  if (savedQuery) query.value = savedQuery
  isLoading.value = true
  error.value = ''
  historyError.value = ''
  result.value = null
  historyRun.value = null
  taskId.value = savedTaskId
  taskStage.value = 'starting'
  try {
    const data = await researchApi.resumeDirectionSearchTask(savedTaskId, task => updateDirectionTask(task, savedQuery))
    clearActiveDirectionTask()
    result.value = data
  } catch (resumeError) {
    if (isRecoverableDirectionTaskError(resumeError)) {
      error.value = '后台检索仍在继续，连接恢复后会继续读取结果。'
    } else {
      clearActiveDirectionTask()
      error.value = apiErrorMessage(resumeError, '之前的方向检索任务无法恢复，请重新提交。')
    }
  } finally {
    isLoading.value = false
    taskStage.value = ''
  }
}

async function loadHistoryRun({ runId, query: historyQuery }: { runId?: string; query?: string }) {
  if (isHistoryLoading.value) return
  isHistoryLoading.value = true
  error.value = ''
  historyError.value = ''
  result.value = null
  historyRun.value = null
  handoffStates.value = {}
  selectedSeed.value = null
  try {
    const data = await researchApi.listSearchRuns(200)
    const runs = data.search_runs
    const target = runId
      ? runs.find((run) => run.run_id === runId)
      : runs.find((run) => normalizeDirection(run.query) === normalizeDirection(historyQuery || ''))
    if (!target) {
      historyError.value = '没有找到这个方向的历史论文列表。可以重新检索，或先在论文库里查看已有论文。'
      query.value = historyQuery || ''
      return
    }
    historyRun.value = target
    query.value = target.query
  } catch (historyLoadError) {
    historyError.value = apiErrorMessage(historyLoadError, '历史论文列表加载失败，请确认后端服务正在运行。')
  } finally {
    isHistoryLoading.value = false
  }
}

function normalizeWarnings(raw: any[]): Array<{ code: string; message: string }> {
  if (!Array.isArray(raw)) return []
  return raw.map((warning, index) => {
    if (typeof warning === 'string') {
      const [code, ...rest] = warning.split(':')
      return {
        code: code || `WARNING_${index + 1}`,
        message: rest.join(':').trim() || warning,
      }
    }
    return {
      code: warning?.code || `WARNING_${index + 1}`,
      message: warning?.message || warning?.detail || String(warning || ''),
    }
  })
}

function toTextList(raw: unknown): string[] {
  return Array.isArray(raw)
    ? raw.map((item) => String(item || '').trim()).filter(Boolean)
    : []
}

function normalizeDirection(value: string) {
  return value.toLowerCase().replace(/[\s\-_:;,.，。；：]+/g, ' ').trim()
}

function warningText(warning: { code: string; message: string }) {
  const code = warning.code || ''
  const message = warning.message || ''
  if (code === 'HEURISTIC_QUERY_PLAN_NO_LLM') return '当前使用本地查询规划，未调用 LLM 规划。'
  if (code === 'ACQUISITION_FAILED') {
    const source = (message.split(/\s+/).find(Boolean) || '某个外部来源').replace(/:+$/, '')
    return `${source} 暂时不可用，已用其它来源降级继续。`
  }
  if (code === 'PARTIAL_SOURCE_RESOLUTION') return '部分候选论文还没有解析出合法全文来源。'
  if (code === 'NO_A_READ_WITH_DOWNLOADABLE_FULL_TEXT') return 'M1 已完成全文下载；验证通过的 PDF 可交给论文代理建立深读会话。'
  if (code === 'UNVERIFIED_CANDIDATES') return `${message || '部分'} 个候选仍需进一步验证。`
  if (code === 'FILTERED_D_IGNORE') return `${message || '部分'} 个低相关候选已标记为暂不推荐。`
  if (code === 'NO_RATED_WITH_DOWNLOADABLE_FULL_TEXT') return '没有候选同时满足评分和可下载全文门槛。'
  if (code === 'DOWNLOAD_ATTEMPT_SUMMARY') return `全文下载尝试：${message || '待确认'}`
  if (code === 'LLM_QUERY_PLAN_FAILED') return `LLM 查询规划失败，已降级到本地规划：${message}`
  return message ? `${code}：${message}` : code
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    SUCCESS: '检索完成',
    DEGRADED: '部分来源降级',
    EMPTY_RESULT: '没有可展示候选',
    BLOCKED: '检索被阻断',
    FAILED: '检索失败',
  }
  return labels[value] || value || '已返回结果'
}

function directionMessage(value: unknown) {
  const text = String(value || '')
  if (text.includes('returned real candidates')) return '已返回真实候选论文，但部分外部来源或全文门槛发生降级。'
  if (text.includes('structured bundle')) return '已从真实论文来源生成结构化方向包。'
  if (text.includes('used the reranked download queue')) {
    const match = text.match(/downloaded\s+(\d+)\/(\d+)\s+attempted papers/i)
    return match
      ? `已完成候选重排，并下载 ${match[1]}/${match[2]} 篇尝试论文。`
      : '已完成候选重排，并尝试下载可深读全文。'
  }
  if (text.includes('No external paper source')) return '外部论文来源没有返回可用结果。'
  if (text.includes('no candidate passed')) return '外部来源有响应，但没有候选通过相关性或可读性筛选。'
  return text
}

function overviewText(value: unknown) {
  const text = String(value || '')
  const match = text.match(/^(.+?) is organized as a conservative reading landscape with (\d+) candidate papers/i)
  if (match) {
    return `${match[1]} 已整理为保守的阅读地图，共 ${match[2]} 篇候选论文；通过全文验证的论文可交给 OpenCode 论文代理深读。`
  }
  const shortMatch = text.match(/^(.+?) is organized as a conservative reading landscape/i)
  if (shortMatch) {
    return `${shortMatch[1]} 已整理为保守的阅读地图；通过全文验证的论文可交给 OpenCode 论文代理深读。`
  }
  return text
}

function percent(value: unknown) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 'n/a'
  return `${Math.round(num * 100)}%`
}

function confidenceLabel(value: unknown) {
  const labels: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低',
  }
  return labels[String(value || '').toLowerCase()] || String(value || 'n/a')
}

function verificationLabel(value: unknown) {
  const labels: Record<string, string> = {
    verified: '已验证',
    verify_pending: '待验证',
    unverified: '未验证',
    failed: '失败',
  }
  return labels[String(value || '').toLowerCase()] || String(value || '未知')
}

function fulltextSourceLabel(value: unknown) {
  const labels: Record<string, string> = {
    metadata_only: '仅元数据',
    publisher_oa_pdf: '出版方开放 PDF',
    arxiv_pdf: 'arXiv PDF',
    arxiv_source: 'arXiv 源码',
    doi: 'DOI',
  }
  return labels[String(value || '')] || String(value || '待确认')
}

function discoverySourceLabel(value: unknown) {
  const labels: Record<string, string> = {
    paper_search: '聚合搜索',
    arxiv_fallback: 'arXiv',
    openalex_fallback: 'OpenAlex',
    semantic_scholar_fallback: 'Semantic Scholar',
  }
  return labels[String(value || '')] || String(value || '未知来源')
}

function m2ReadinessNote(paper: Record<string, any>) {
  const reason = String(paper.m2_unavailable_reason || paper.risk_note || '')
  if (!reason) return '需要先下载并验证合法 PDF，之后由论文代理建立会话。'
  if (reason.includes('Not cleared for M2')) return '尚未准备好深读：需要先下载并验证合法 PDF。'
  if (reason.includes('Metadata/source confidence is low')) return '来源或元数据置信度偏低，进入深读前需要人工确认。'
  return reason
}

function downloadDiagnosticNote(paper: Record<string, any>) {
  const code = String(paper.download_error_code || '')
  const diagnostics = paper.browser_diagnostics && typeof paper.browser_diagnostics === 'object'
    ? paper.browser_diagnostics
    : {}
  if (code === 'BROWSER_USER_VERIFICATION_REQUIRED') return '出版社要求在专用 Chrome 中完成人机验证，本次没有自动绕过。'
  if (code === 'BROWSER_ACCESS_REQUIRED') return '出版社要求登录、机构订阅或购买，Cookie 并不是剩余阻塞原因。'
  if (code === 'BROWSER_COOKIE_CONSENT_BLOCKED') return 'Cookie/隐私弹窗未能安全关闭，已保存失败页面诊断截图。'
  if (diagnostics.cookie_consent_action === 'rejected_optional') return '已关闭 Cookie 弹窗，并拒绝可选 Cookie。'
  if (diagnostics.cookie_consent_action === 'accepted_required') return '页面只提供接受 Cookie 的继续入口，已完成该操作。'
  if (diagnostics.cookie_consent_action === 'dismissed') return '已关闭 Cookie/隐私提示后继续下载。'
  return ''
}

function readingOrderText(item: Record<string, any>) {
  const priorityLabels: Record<string, string> = {
    A_READ: '优先深读',
    A_READ_FOR_M2: '优先进入 M2',
    B_SKIM: '快速浏览',
    C_REFERENCE: '留作参考',
    D_IGNORE: '忽略',
  }
  const roleLabels: Record<string, string> = {
    TRANSFORMER_METHOD: 'Transformer 方法',
    GRAPH_METHOD: '图方法',
    RECONSTRUCTION_METHOD: '重构方法',
    PREDICTION_METHOD: '预测方法',
    BENCHMARK: '基准/数据集',
    SURVEY: '综述',
    METHOD: '方法论文',
  }
  return `${item.title} · ${priorityLabels[item.priority] || item.priority} · ${roleLabels[item.role] || item.role}`
}

function authorsText(authors: unknown) {
  return Array.isArray(authors) && authors.length ? authors.join(', ') : '作者未知'
}

function deepReadJobId(paper: Record<string, any>) {
  return paper.paper_workspace_job_id || paper.job_id || ''
}

function candidateKey(paper: Record<string, any>) {
  return paper.paper_id || paper.arxiv_id || paper.pdf_url || paper.title || 'candidate'
}

function handoffState(paper: Record<string, any>) {
  return handoffStates.value[candidateKey(paper)] || {}
}

function setHandoffState(paper: Record<string, any>, state: HandoffState) {
  handoffStates.value = {
    ...handoffStates.value,
    [candidateKey(paper)]: state,
  }
}

function discoverySourcesText(paper: Record<string, any>) {
  const sources = paper.discovery_sources || paper.sources
  if (Array.isArray(sources) && sources.length) return sources.join(', ')
  return paper.source || '未知来源'
}

function fulltextPdfUrl(paper: Record<string, any>) {
  if (paper.pdf_url) return paper.pdf_url
  if (paper.fulltext_status === 'pdf_ready' && paper.selected_fulltext_url) return paper.selected_fulltext_url
  return ''
}

function arxivHandoffUrl(paper: Record<string, any>) {
  const value = paper.arxiv_url || ''
  return typeof value === 'string' && value.includes('arxiv.org/') ? value : ''
}

function hasDeepReadSource(paper: Record<string, any>) {
  return Boolean(
    paper.can_deep_read ||
    paper.arxiv_id ||
    arxivHandoffUrl(paper) ||
    fulltextPdfUrl(paper) ||
    paper.doi
  )
}

function deepReadLabel(paper: Record<string, any>) {
  if (deepReadJobId(paper)) return '进入深读'
  if (!hasDeepReadSource(paper)) return '来源不可用'
  const state = handoffState(paper)
  return state.loading ? `正在准备 ${state.progress || 0}%` : '深读这篇'
}

function deepReadDisabled(paper: Record<string, any>) {
  return Boolean(handoffState(paper).loading || (!deepReadJobId(paper) && !hasDeepReadSource(paper)))
}

function selectSeed(paper: Record<string, any>) {
  selectedSeed.value = paper
}

function historyPaperKey(paper: SearchRunPaper) {
  return paper.paper_id || paper.local_path || paper.title
}

function historyActionLabel(action: unknown) {
  const labels: Record<string, string> = {
    downloaded: '已下载',
    reused: '已复用',
    failed: '下载失败',
    skipped: '已跳过',
    not_attempted: '未下载',
    not_available: '无全文',
  }
  return labels[String(action || '')] || String(action || '未知')
}

function historyActionTone(action: unknown) {
  const value = String(action || '')
  if (value === 'downloaded' || value === 'reused') return 'ready'
  if (value === 'failed') return 'failed'
  return 'muted'
}

function venueRankLabel(value: unknown) {
  const text = String(value || '').trim()
  if (!text || text === 'unranked') return '未定级'
  return text
}

function historyReasonText(paper: SearchRunPaper) {
  const action = String(paper.action || '')
  const reason = String(paper.reason || '')
  const rank = reason.match(/reranked order #(\d+)/i)?.[1]
  const suffix = rank ? ` · 重排 #${rank}` : ''
  if (action === 'reused') return `本地已有全文，已复用${suffix}`
  if (action === 'downloaded') return `已下载全文${suffix}`
  if (action === 'not_available') return `未找到可下载全文${suffix}`
  if (action === 'failed') {
    if (/403 Forbidden/i.test(reason)) return '全文下载被站点拒绝（403）'
    if (/404 Not Found/i.test(reason)) return '全文链接已失效（404）'
    return '全文下载失败'
  }
  if (reason.includes('Selected for download')) return `进入下载队列${suffix}`
  return reason.replace(/\s+/g, ' ').trim()
}

function historyMetaText(paper: SearchRunPaper) {
  return [
    paper.venue || '来源未知',
    venueRankLabel(paper.venue_rank),
    historyReasonText(paper),
  ].filter(Boolean).join(' · ')
}

async function openHistoryPaper(paper: SearchRunPaper) {
  const key = historyPaperKey(paper)
  if (!paper.local_path || openingHistoryKey.value) return
  openingHistoryKey.value = key
  isLoading.value = true
  historyError.value = ''
  taskStage.value = 'queued'
  taskProgress.value = 0
  try {
    const form = new FormData()
    form.append('local_path', paper.local_path)
    form.append('title', paper.title || '')
    const data = await researchApi.parseDocumentAsync(form, updateHistoryParseTask)
    clearActiveHistoryParseTask()
    await router.push(`/learn/${data.job_id}`)
  } catch (openError) {
    if (isRecoverableDirectionTaskError(openError)) {
      historyError.value = '论文仍在后台解析；连接恢复或刷新页面后会继续读取进度。'
    } else {
      clearActiveHistoryParseTask()
      historyError.value = apiErrorMessage(openError, '网络请求失败，暂时不能打开这篇历史论文。')
    }
  } finally {
    openingHistoryKey.value = ''
    isLoading.value = false
  }
}

async function openDeepRead(paper: Record<string, any>) {
  const jobId = deepReadJobId(paper)
  if (jobId) {
    await router.push(`/learn/${jobId}`)
    return
  }
  if (!hasDeepReadSource(paper)) {
    setHandoffState(paper, {
      error: paper.deep_read_unavailable_reason || '没有可用的 arXiv、DOI 或 PDF 来源。',
    })
    return
  }

  setHandoffState(paper, { loading: true, error: '' })
  try {
    const data = await researchApi.deepReadAsync({
      title: String(paper.title || ''),
      doi: String(paper.doi || ''),
      arxiv_id: String(paper.arxiv_id || ''),
      arxiv_url: arxivHandoffUrl(paper),
      pdf_url: fulltextPdfUrl(paper),
      relevance_gate_evaluated: paper.relevance_gate_evaluated,
      relevance_gate_passed: paper.relevance_gate_passed,
      deep_read_relevance_passed: paper.deep_read_relevance_passed,
      rule_relevance_score: paper.rule_relevance_score,
      relevance_reason: paper.relevance_reason,
    }, task => {
      window.localStorage.setItem(ACTIVE_DEEP_READ_TASK_KEY, task.task_id)
      taskId.value = task.task_id
      taskStage.value = task.stage
      taskProgress.value = task.progress
      setHandoffState(paper, {
        loading: true,
        error: '',
        stage: task.stage,
        progress: task.progress,
        taskId: task.task_id,
      })
    })
    clearActiveDeepReadTask()
    await router.push(`/learn/${data.job_id}`)
  } catch (handoffError) {
    const code = handoffError instanceof ApiClientError
      ? String(handoffError.detail?.status || handoffError.detail?.handoff_status || handoffError.code)
      : 'HANDOFF_FAILED'
    setHandoffState(paper, { error: `${code}：${apiErrorMessage(handoffError, '候选论文移交深读失败。')}` })
  } finally {
    const state = handoffState(paper)
    if (state.loading) {
      setHandoffState(paper, { ...state, loading: false })
    }
  }
}
</script>

<template>
  <main class="direction-page">
    <div class="direction-canvas">
      <section class="direction-thread" aria-label="方向工作流">
        <div class="direction-thread-content" data-testid="direction-scroll-region">
        <article class="codex-message user-message">
          <div class="message-icon">R</div>
          <div class="message-body">
            <p class="message-kicker">Research Sensei</p>
            <h1>{{ currentDirectionLabel }}</h1>
            <ul>
              <li>先展示这个方向已经记录的论文，不会在点击历史方向时自动重新检索或下载。</li>
              <li>需要新增论文时，用底部输入框主动发起检索，再把可用全文移交到深读工作区。</li>
              <li>候选列表只保留来源、全文、M2 门槛这些能支撑下一步阅读的证据。</li>
            </ul>
          </div>
        </article>

        <div v-if="error" class="error-box">
          {{ error }}
        </div>

        <article v-if="isHistoryLoading" class="codex-card loading-card">
          正在加载这个方向已有的论文列表...
        </article>

        <article v-if="isLoading" class="codex-card loading-card" role="status" data-testid="direction-task-progress">
          <span>后台任务：{{ taskStageLabel }} · {{ taskProgress }}%</span>
          <progress :value="taskProgress" max="100" />
        </article>

        <div v-if="historyError" class="error-box">
          {{ historyError }}
        </div>

        <section v-if="historyRun" class="codex-card history-panel" data-testid="direction-history">
          <header class="card-head">
            <div>
              <span>已记录论文</span>
              <h2>{{ historyRun.query }}</h2>
              <p>
                {{ historyRun.candidate_count || historyPapers.length }} 篇候选 ·
                {{ historyRun.downloaded_count || 0 }} 已下载 ·
                {{ historyRun.reused_count || 0 }} 已复用
              </p>
            </div>
            <button type="button" class="secondary-btn" :disabled="isLoading" @click="search">
              重新检索
            </button>
          </header>

          <div v-if="historyPapers.length" class="history-list">
            <article
              v-for="paper in historyPapers"
              :key="historyPaperKey(paper)"
              class="history-row"
              data-testid="history-paper"
            >
              <div class="history-main">
                <div class="history-title-line">
                  <span class="rank">{{ paper.search_rank || '-' }}</span>
                  <h3>{{ paper.title }}</h3>
                </div>
                <p>{{ historyMetaText(paper) }}</p>
              </div>
              <div class="history-actions">
                <span class="history-pill" :class="historyActionTone(paper.action)">
                  {{ historyActionLabel(paper.action) }}
                </span>
                <button
                  type="button"
                  class="primary-btn"
                  :disabled="!paper.local_path || openingHistoryKey === historyPaperKey(paper)"
                  data-testid="history-deep-read"
                  @click="openHistoryPaper(paper)"
                >
                  {{ openingHistoryKey === historyPaperKey(paper) ? '打开中...' : paper.local_path ? '深读' : '无全文' }}
                </button>
              </div>
            </article>
          </div>
          <p v-else class="history-empty">这个方向有历史记录，但没有保存论文条目。</p>
          <p v-if="historyRun && historyReadyPapers.length === 0" class="history-note">
            这个方向还没有可直接深读的本地全文。只有点击“重新检索”才会重新搜索和尝试下载。
          </p>
        </section>

        <section v-if="result" class="codex-card status-card" data-testid="direction-status">
          <div class="status-line">
            <strong>{{ statusLabel(status) }}</strong>
            <span>
              {{ relevantPapers.length }} 篇严格相关 ·
              尝试全文 {{ downloadAttemptCount }} 篇 ·
              成功 {{ downloadedPaperCount }} 篇 ·
              {{ allPapers.length }} 篇去重候选
            </span>
          </div>
          <p v-if="result.message">{{ directionMessage(result.message) }}</p>
          <div v-if="warnings.length" class="warning-list">
            <span v-for="warning in warnings" :key="warning.code" data-testid="direction-warning">
              {{ warningText(warning) }}
            </span>
          </div>
          <div v-if="acquisitionSourceMetrics.length" class="source-ledger" data-testid="source-ledger">
            <span
              v-for="metric in acquisitionSourceMetrics"
              :key="`${metric.source}-${metric.trigger || 'primary'}`"
              :class="{ failed: !metric.success, supplement: metric.trigger === 'low_coverage_oa_supplement' }"
            >
              {{ discoverySourceLabel(metric.source) }} · {{ metric.success ? `${metric.count || 0} 篇` : '不可用' }}
              <small v-if="metric.trigger === 'low_coverage_oa_supplement'">开放来源补搜</small>
            </span>
          </div>
          <details v-if="fulltextProbeMetrics.length" class="source-probe-details">
            <summary>
              全文来源解析 {{ fulltextProbeMetrics.length }} 次 · {{ successfulFulltextProbes }} 次发现可用候选
            </summary>
            <div class="source-ledger source-ledger-probes">
              <span
                v-for="(metric, index) in fulltextProbeMetrics"
                :key="`${metric.source}-${metric.trigger || 'probe'}-${index}`"
                :class="{ failed: !metric.success }"
              >
                {{ discoverySourceLabel(metric.source) }} · {{ metric.success ? `${metric.count || 0} 篇` : '未发现' }}
              </span>
            </div>
          </details>
        </section>

        <section v-if="queryPlan" class="codex-card query-plan" data-testid="query-plan">
          <header class="card-head compact">
            <div>
              <span>{{ queryPlanMode }}</span>
              <h2>{{ queryPlan.english_query || queryPlan.direction_en || queryPlan.user_query }}</h2>
            </div>
          </header>
          <div class="query-plan-body">
            <div>
              <small>核心词</small>
              <p>{{ queryCoreTerms.length ? queryCoreTerms.join(' / ') : '待确认' }}</p>
            </div>
            <div>
              <small>检索变体</small>
              <p>{{ queryVariants.length ? queryVariants.join(' / ') : '待确认' }}</p>
            </div>
          </div>
        </section>

        <section v-if="result?.overview" class="thread-section" data-testid="direction-overview">
          <h2>方向概览</h2>
          <p>{{ overviewText(result.overview) }}</p>
        </section>

        <section v-if="result?.key_sub_directions?.length" class="thread-section" data-testid="sub-directions">
          <h2>关键子方向</h2>
          <div class="mini-grid">
            <article v-for="item in result.key_sub_directions" :key="item.name" class="mini-card">
              <strong>{{ item.name }}</strong>
              <span>{{ item.description }}</span>
            </article>
          </div>
        </section>

        <section v-if="result?.method_families?.length" class="thread-section" data-testid="method-families">
          <h2>方法家族</h2>
          <div class="mini-grid three">
            <article v-for="family in result.method_families" :key="family.role || family.name" class="mini-card">
              <strong>{{ family.name }}</strong>
              <span>{{ family.paper_count || 0 }} 篇论文</span>
            </article>
          </div>
        </section>

        <section v-if="papers.length" class="thread-section">
          <div class="section-heading-row">
            <h2>候选论文</h2>
            <button
              v-if="filteredCandidateCount"
              type="button"
              class="secondary-btn"
              data-testid="toggle-filtered-candidates"
              @click="showFilteredCandidates = !showFilteredCandidates"
            >
              {{ showFilteredCandidates ? '隐藏低相关结果' : `查看 ${filteredCandidateCount} 篇已过滤结果` }}
            </button>
          </div>
          <div class="candidate-list">
            <article
              v-for="paper in papers"
              :key="paper.paper_id || paper.title"
              class="candidate-card"
              data-testid="candidate-card"
            >
              <div class="candidate-main">
                <div class="candidate-title">
                  <h3>{{ paper.title }}</h3>
                  <p>
                    {{ authorsText(paper.authors) }} · {{ paper.year || '年份未知' }} · {{ paper.venue || paper.source || '来源未知' }}
                  </p>
                </div>
                <div class="candidate-actions">
                  <button
                    type="button"
                    class="primary-btn"
                    :disabled="deepReadDisabled(paper)"
                    data-testid="deep-read-button"
                    @click="openDeepRead(paper)"
                  >
                    {{ deepReadLabel(paper) }}
                  </button>
                  <button
                    type="button"
                    class="secondary-btn"
                    data-testid="seed-select-button"
                    @click="selectSeed(paper)"
                  >
                    扩展相关论文
                  </button>
                </div>
              </div>

              <div class="meta-grid">
                <span>相关度 {{ percent(paper.relevance_score) }}</span>
                <span>可信度 {{ confidenceLabel(paper.source_confidence) }}</span>
                <span>验证 {{ verificationLabel(paper.verification_status) }}</span>
                <span>全文 {{ paper.pdf_available || paper.selected_fulltext_url ? '可用' : '待确认' }}</span>
                <span>发现来源 {{ discoverySourcesText(paper) }}</span>
                <span>论文代理 {{ paper.paper_agent_ready || paper.m2_ready || paper.can_enter_m2 ? '可接收' : '待验证' }}</span>
              </div>

              <p v-if="paper.selected_fulltext_source || paper.fulltext_failure_reason" class="note" data-testid="fulltext-note">
                全文来源：{{ fulltextSourceLabel(paper.selected_fulltext_source || 'metadata_only') }}
                {{ paper.fulltext_failure_reason ? ` · ${paper.fulltext_failure_reason}` : '' }}
              </p>
              <p v-if="downloadDiagnosticNote(paper)" class="note" data-testid="browser-download-note">
                {{ downloadDiagnosticNote(paper) }}
              </p>
              <p v-if="!paper.paper_agent_ready && !paper.can_enter_m2" class="note" data-testid="m2-readiness-note">
                深读准备：{{ m2ReadinessNote(paper) }}
              </p>
              <p v-if="!hasDeepReadSource(paper)" class="note warning" data-testid="source-unavailable-note">
                {{ paper.deep_read_unavailable_reason || '没有可支持的全文来源。' }}
              </p>
              <p v-if="handoffState(paper).error" class="note danger" data-testid="handoff-error">
                {{ handoffState(paper).error }}
              </p>
              <div
                v-if="handoffState(paper).loading"
                class="handoff-progress"
                role="status"
                data-testid="deep-read-progress"
              >
                <div>
                  <span>{{ formatTaskStage(handoffState(paper).stage || '') }}</span>
                  <strong>{{ handoffState(paper).progress || 0 }}%</strong>
                </div>
                <progress :value="handoffState(paper).progress || 0" max="100" />
              </div>
            </article>
          </div>
        </section>

        <section v-if="result?.recommended_reading_order?.length" class="thread-section" data-testid="reading-order">
          <h2>建议阅读顺序</h2>
          <ol class="reading-order">
            <li v-for="item in result.recommended_reading_order" :key="`${item.rank}-${item.title}`">
              <span>{{ item.rank }}</span>
              <p>{{ readingOrderText(item) }}</p>
            </li>
          </ol>
        </section>

        <section v-if="result && hasEmptyResult" class="codex-card empty-result" data-testid="empty-result">
          没有可展示的候选论文。可以换一个更具体的方向，或稍后重试外部来源。
        </section>

        <section v-if="result || selectedSeed" class="expansion-wrap">
          <SeedExpansionPanel
            :status="result?.seed_expansion_status || 'READY'"
            :warnings="warnings"
            :seed="selectedSeed"
          />
        </section>
        </div>

        <form class="codex-composer" @submit.prevent="search">
          <textarea
            v-model="query"
            data-testid="direction-query"
            rows="2"
            placeholder="输入一个研究方向，例如 time-series anomaly detection"
          />
          <footer>
            <span class="composer-hint">{{ historyRun ? '发送后会重新检索这个方向' : '发送后开始检索论文' }}</span>
            <button type="submit" class="send-button" :disabled="isLoading || !query.trim()" aria-label="检索方向">
              {{ isLoading ? '...' : '↑' }}
            </button>
          </footer>
        </form>
      </section>

      <aside class="research-panel" aria-label="当前方向状态">
        <header>
          <span>当前方向</span>
          <strong>{{ currentDirectionLabel }}</strong>
        </header>
        <dl>
          <div>
            <dt>候选</dt>
            <dd>{{ activeCandidateCount }} 篇</dd>
          </div>
          <div>
            <dt>可深读</dt>
            <dd>{{ activeReadyCount }} 篇</dd>
          </div>
          <div>
            <dt>告警</dt>
            <dd>{{ warnings.length }} 条</dd>
          </div>
          <div>
            <dt>下一步</dt>
            <dd>{{ currentNextStep }}</dd>
          </div>
        </dl>
        <div class="panel-actions">
          <button type="button" @click="router.push('/papers/library')">打开论文库</button>
          <button type="button" @click="router.push('/settings')">检查模型设置</button>
        </div>
        <p>{{ panelNote }}</p>
      </aside>
    </div>
  </main>
</template>

<style scoped src="./DirectionSearchView.css"></style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import SeedExpansionPanel from '../components/SeedExpansionPanel.vue'

const router = useRouter()
const query = ref('')
const isLoading = ref(false)
const error = ref('')
const result = ref<Record<string, any> | null>(null)
const handoffStates = ref<Record<string, { loading?: boolean; error?: string }>>({})
const selectedSeed = ref<Record<string, any> | null>(null)

const status = computed(() => result.value?.direction_workspace_status || result.value?.status || '')
const warnings = computed(() => normalizeWarnings(result.value?.warnings || []))
const papers = computed(() => result.value?.papers || result.value?.candidate_cards || [])
const hasEmptyResult = computed(() => ['EMPTY_RESULT', 'BLOCKED'].includes(String(status.value)))
const queryPlan = computed(() => result.value?.query_plan || null)
const queryPlanMode = computed(() => {
  if (!queryPlan.value) return ''
  if (warnings.value.some((warning) => warning.code === 'HEURISTIC_QUERY_PLAN_NO_LLM')) return '本地规划'
  if (warnings.value.some((warning) => warning.code === 'LLM_QUERY_PLAN_FAILED')) return 'LLM 降级'
  return 'LLM 规划'
})
const queryVariants = computed(() => toTextList(queryPlan.value?.query_variants).slice(0, 6))
const queryCoreTerms = computed(() => toTextList(queryPlan.value?.core_terms).slice(0, 8))

async function search() {
  if (!query.value.trim() || isLoading.value) return
  isLoading.value = true
  error.value = ''
  result.value = null
  handoffStates.value = {}
  selectedSeed.value = null
  try {
    const res = await fetch('/api/v1/directions/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.value.trim() }),
    })
    const data = await res.json().catch(() => ({}))
    result.value = data
    if (!res.ok) {
      error.value = data.detail?.message || '方向检索失败。'
    }
  } catch {
    error.value = '网络请求失败，请确认后端服务正在运行。'
  } finally {
    isLoading.value = false
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

function warningText(warning: { code: string; message: string }) {
  const code = warning.code || ''
  const message = warning.message || ''
  if (code === 'HEURISTIC_QUERY_PLAN_NO_LLM') return '当前使用本地查询规划，未调用 LLM 规划。'
  if (code === 'ACQUISITION_FAILED') {
    const source = (message.split(/\s+/).find(Boolean) || '某个外部来源').replace(/:+$/, '')
    return `${source} 暂时不可用，已用其它来源降级继续。`
  }
  if (code === 'PARTIAL_SOURCE_RESOLUTION') return '部分候选论文还没有解析出合法全文来源。'
  if (code === 'NO_A_READ_WITH_DOWNLOADABLE_FULL_TEXT') return '当前没有候选同时满足深读全文下载与质量门槛。'
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
    return `${match[1]} 已整理为保守的阅读地图，共 ${match[2]} 篇候选论文；只有通过验证全文和规范化门槛的论文才会进入 PaperWorkspace 深读。`
  }
  const shortMatch = text.match(/^(.+?) is organized as a conservative reading landscape/i)
  if (shortMatch) {
    return `${shortMatch[1]} 已整理为保守的阅读地图；只有通过验证全文和规范化门槛的论文才会进入 PaperWorkspace 深读。`
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

function m2ReadinessNote(paper: Record<string, any>) {
  const reason = String(paper.m2_unavailable_reason || paper.risk_note || '')
  if (!reason) return '需要完成来源下载和规范化校验。'
  if (reason.includes('Not cleared for M2')) return '尚未通过 M2 深读门槛：需要先下载并验证合法全文。'
  if (reason.includes('Metadata/source confidence is low')) return '来源或元数据置信度偏低，进入深读前需要人工确认。'
  return reason
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

function setHandoffState(paper: Record<string, any>, state: { loading?: boolean; error?: string }) {
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
  return handoffState(paper).loading ? '正在准备...' : '深读这篇'
}

function deepReadDisabled(paper: Record<string, any>) {
  return Boolean(handoffState(paper).loading || (!deepReadJobId(paper) && !hasDeepReadSource(paper)))
}

function selectSeed(paper: Record<string, any>) {
  selectedSeed.value = paper
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
    const res = await fetch('/api/v1/directions/deep_read', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate: {
          title: paper.title || '',
          doi: paper.doi || '',
          arxiv_id: paper.arxiv_id || '',
          arxiv_url: arxivHandoffUrl(paper),
          pdf_url: fulltextPdfUrl(paper),
        },
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || !data.job_id) {
      const detail = data.detail || data
      setHandoffState(paper, {
        error: `${detail.status || detail.handoff_status || 'HANDOFF_FAILED'}：${detail.message || '候选论文移交深读失败。'}`,
      })
      return
    }
    await router.push(`/learn/${data.job_id}`)
  } catch {
    setHandoffState(paper, { error: '网络请求失败，暂时不能创建深读任务。' })
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
    <section class="search-head">
      <p>方向工作台</p>
      <h1>先找方向，再挑论文深读</h1>
      <form class="search-box" @submit.prevent="search">
        <input
          v-model="query"
          data-testid="direction-query"
          placeholder="例如：time-series anomaly detection"
        />
        <button type="submit" class="primary-btn" :disabled="isLoading || !query.trim()">
          {{ isLoading ? '检索中...' : '检索方向' }}
        </button>
      </form>
    </section>

    <div v-if="error" class="error-box">
      {{ error }}
    </div>

    <section v-if="result" class="status-card surface" data-testid="direction-status">
      <div>
        <strong>{{ statusLabel(status) }}</strong>
        <span>{{ papers.length }} 篇候选论文</span>
      </div>
      <p v-if="result.message">{{ directionMessage(result.message) }}</p>
      <div v-if="warnings.length" class="warning-list">
        <span v-for="warning in warnings" :key="warning.code" data-testid="direction-warning">
          {{ warningText(warning) }}
        </span>
      </div>
    </section>

    <section v-if="queryPlan" class="query-plan surface" data-testid="query-plan">
      <div class="query-plan-head">
        <span>{{ queryPlanMode }}</span>
        <strong>{{ queryPlan.english_query || queryPlan.direction_en || queryPlan.user_query }}</strong>
      </div>
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

    <section v-if="result?.overview" class="overview" data-testid="direction-overview">
      <h2>方向概览</h2>
      <p>{{ overviewText(result.overview) }}</p>
    </section>

    <section v-if="result?.key_sub_directions?.length" class="section-block" data-testid="sub-directions">
      <h2>关键子方向</h2>
      <div class="mini-grid">
        <article v-for="item in result.key_sub_directions" :key="item.name" class="surface mini-card">
          <strong>{{ item.name }}</strong>
          <span>{{ item.description }}</span>
        </article>
      </div>
    </section>

    <section v-if="result?.method_families?.length" class="section-block" data-testid="method-families">
      <h2>方法家族</h2>
      <div class="mini-grid three">
        <article v-for="family in result.method_families" :key="family.role || family.name" class="surface mini-card">
          <strong>{{ family.name }}</strong>
          <span>{{ family.paper_count || 0 }} 篇论文</span>
        </article>
      </div>
    </section>

    <section v-if="papers.length" class="section-block">
      <h2>候选论文</h2>
      <div class="candidate-list">
        <article
          v-for="paper in papers"
          :key="paper.paper_id || paper.title"
          class="candidate-card surface"
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
            <span>M2 {{ paper.m2_ready || paper.can_enter_m2 ? '可进入' : '待验证' }}</span>
          </div>

          <p v-if="paper.selected_fulltext_source || paper.fulltext_failure_reason" class="note" data-testid="fulltext-note">
            全文来源：{{ fulltextSourceLabel(paper.selected_fulltext_source || 'metadata_only') }}
            {{ paper.fulltext_failure_reason ? ` · ${paper.fulltext_failure_reason}` : '' }}
          </p>
          <p v-if="!paper.can_enter_m2" class="note" data-testid="m2-readiness-note">
            M2 闸门：{{ m2ReadinessNote(paper) }}
          </p>
          <p v-if="!hasDeepReadSource(paper)" class="note warning" data-testid="source-unavailable-note">
            {{ paper.deep_read_unavailable_reason || '没有可支持的全文来源。' }}
          </p>
          <p v-if="handoffState(paper).error" class="note danger" data-testid="handoff-error">
            {{ handoffState(paper).error }}
          </p>
        </article>
      </div>
    </section>

    <section v-if="result?.recommended_reading_order?.length" class="section-block" data-testid="reading-order">
      <h2>建议阅读顺序</h2>
      <ol class="reading-order">
        <li v-for="item in result.recommended_reading_order" :key="`${item.rank}-${item.title}`">
          <span>{{ item.rank }}</span>
          <p>{{ readingOrderText(item) }}</p>
        </li>
      </ol>
    </section>

    <section v-if="result && hasEmptyResult" class="empty-result surface" data-testid="empty-result">
      没有可展示的候选论文。可以换一个更具体的方向，或稍后重试外部来源。
    </section>

    <SeedExpansionPanel
      :status="result?.seed_expansion_status || 'READY'"
      :warnings="warnings"
      :seed="selectedSeed"
    />
  </main>
</template>

<style scoped>
.direction-page {
  width: min(1120px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 28px 0 64px;
}

.search-head {
  margin-bottom: 16px;
}

.search-head > p {
  color: var(--accent);
  font-size: 13px;
  font-weight: 800;
}

.search-head h1 {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 28px;
  font-weight: 900;
}

.search-box {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  margin-top: 20px;
}

.search-box input {
  width: 100%;
  outline: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 16px;
}

.error-box,
.empty-result {
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 15px;
  line-height: 1.7;
}

.error-box {
  margin-bottom: 16px;
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
}

.status-card {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
  padding: 14px;
}

.status-card div:first-child {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.status-card strong {
  color: var(--text-primary);
  font-size: 16px;
}

.status-card span,
.status-card p,
.warning-list span {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.warning-list {
  display: grid;
  gap: 4px;
}

.query-plan {
  display: grid;
  gap: 12px;
  margin-bottom: 24px;
  padding: 14px;
}

.query-plan-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.query-plan-head span {
  border-radius: 999px;
  padding: 3px 9px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.query-plan-head strong {
  min-width: 0;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.query-plan-body {
  display: grid;
  grid-template-columns: minmax(180px, 0.35fr) minmax(0, 1fr);
  gap: 10px;
}

.query-plan-body div {
  border-radius: 8px;
  padding: 9px 10px;
  background: var(--bg-secondary);
}

.query-plan-body small {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.query-plan-body p {
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.overview,
.section-block {
  margin-bottom: 28px;
}

.overview h2,
.section-block h2 {
  margin-bottom: 12px;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 900;
}

.overview p {
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.9;
}

.mini-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.mini-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.mini-card {
  padding: 15px;
}

.mini-card strong,
.mini-card span {
  display: block;
}

.mini-card strong {
  color: var(--text-primary);
  font-size: 15px;
}

.mini-card span {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.candidate-list {
  display: grid;
  gap: 14px;
}

.candidate-card {
  padding: 18px;
}

.candidate-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
}

.candidate-title h3 {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
  line-height: 1.45;
}

.candidate-title p {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.6;
}

.candidate-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 16px;
}

.meta-grid span {
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
}

.note {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
}

.note.warning {
  color: #b45309;
}

.note.danger {
  color: #dc2626;
}

.reading-order {
  display: grid;
  gap: 10px;
}

.reading-order li {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  color: var(--text-secondary);
}

.reading-order span {
  display: flex;
  height: 30px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 900;
}

.reading-order p {
  padding-top: 4px;
  font-size: 15px;
  line-height: 1.7;
}

@media (max-width: 820px) {
  .search-box,
  .candidate-main {
    grid-template-columns: 1fr;
  }

  .candidate-actions {
    flex-wrap: wrap;
  }

  .mini-grid,
  .mini-grid.three,
  .query-plan-body,
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>

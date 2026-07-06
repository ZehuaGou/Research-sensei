<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  status?: string
  warnings?: Array<{ code: string; message: string }> | string[]
  seed?: Record<string, any> | null
}>()

const router = useRouter()
const seedTitle = ref('')
const seedArxivId = ref('')
const seedDoi = ref('')
const seedPaperUrl = ref('')
const seedPdfUrl = ref('')
const isLoading = ref(false)
const error = ref('')
const result = ref<Record<string, any> | null>(null)
const handoffStates = ref<Record<string, { loading?: boolean; error?: string }>>({})

watch(
  () => props.seed,
  (seed) => {
    if (!seed) return
    seedTitle.value = seed.title || ''
    seedArxivId.value = seed.arxiv_id || ''
    seedDoi.value = seed.doi || ''
    seedPaperUrl.value = seed.paper_url || seed.arxiv_url || seed.url || seed.landing_url || ''
    seedPdfUrl.value = seed.pdf_url || ''
    result.value = null
    error.value = ''
    handoffStates.value = {}
  },
  { immediate: true },
)

const effectiveStatus = computed(() => result.value?.seed_expansion_status || result.value?.status || props.status || 'READY')
const warnings = computed(() => normalizeWarnings([...(props.warnings || []), ...(result.value?.warnings || [])]))
const groups = computed(() => [
  { key: 'upstream_papers', label: '上游基础论文' },
  { key: 'downstream_papers', label: '下游应用论文' },
  { key: 'same_route_papers', label: '同路线论文' },
  { key: 'related_surveys', label: '相关综述' },
])
const hasAnyPaper = computed(() => groups.value.some((group) => groupItems(group.key).length > 0))
const canSubmit = computed(() => Boolean(seedTitle.value.trim() || seedArxivId.value.trim() || seedDoi.value.trim() || seedPaperUrl.value.trim() || seedPdfUrl.value.trim()))

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

function groupItems(key: string) {
  const items = result.value?.[key]
  return Array.isArray(items) ? items : []
}

function percent(value: unknown) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 'n/a'
  return `${Math.round(num * 100)}%`
}

function authorsText(authors: unknown) {
  return Array.isArray(authors) && authors.length ? authors.join(', ') : '作者未知'
}

function paperKey(paper: Record<string, any>) {
  return paper.paper_id || paper.arxiv_id || paper.pdf_url || paper.title || 'seed-paper'
}

function handoffState(paper: Record<string, any>) {
  return handoffStates.value[paperKey(paper)] || {}
}

function setHandoffState(paper: Record<string, any>, state: { loading?: boolean; error?: string }) {
  handoffStates.value = {
    ...handoffStates.value,
    [paperKey(paper)]: state,
  }
}

function hasDeepReadSource(paper: Record<string, any>) {
  return Boolean(paper.arxiv_id || arxivHandoffUrl(paper) || paper.pdf_url || paper.doi)
}

function arxivHandoffUrl(paper: Record<string, any>) {
  const value = paper.arxiv_url || paper.paper_url || paper.url || paper.landing_url || ''
  return typeof value === 'string' && value.includes('arxiv.org/') ? value : ''
}

function deepReadDisabled(paper: Record<string, any>) {
  return Boolean(handoffState(paper).loading || !hasDeepReadSource(paper))
}

function deepReadLabel(paper: Record<string, any>) {
  if (!hasDeepReadSource(paper)) return '来源不可用'
  return handoffState(paper).loading ? '正在准备...' : '深读这篇'
}

async function expandSeed() {
  if (!canSubmit.value || isLoading.value) return
  isLoading.value = true
  error.value = ''
  result.value = null
  handoffStates.value = {}
  try {
    const res = await fetch('/api/v1/directions/seed_expansion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        seed: {
          title: seedTitle.value.trim(),
          arxiv_id: seedArxivId.value.trim(),
          doi: seedDoi.value.trim(),
          paper_url: seedPaperUrl.value.trim(),
          pdf_url: seedPdfUrl.value.trim(),
        },
      }),
    })
    const data = await res.json().catch(() => ({}))
    result.value = data
    if (!res.ok) {
      error.value = data.detail?.message || data.message || '相关论文扩展失败。'
    }
  } catch {
    error.value = '网络请求失败，请确认后端服务正在运行。'
  } finally {
    isLoading.value = false
  }
}

async function prepareDeepRead(paper: Record<string, any>) {
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
          pdf_url: paper.pdf_url || '',
        },
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || !data.job_id) {
      const detail = data.detail || data
      setHandoffState(paper, {
        error: `${detail.status || detail.handoff_status || 'HANDOFF_FAILED'}：${detail.message || '扩展论文移交深读失败。'}`,
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
  <section class="seed-panel surface" data-testid="seed-expansion-panel">
    <header class="seed-head">
      <div>
        <h2>从一篇论文扩展阅读网络</h2>
        <span data-testid="seed-status">{{ effectiveStatus }}</span>
      </div>
      <button
        type="button"
        class="primary-btn"
        :disabled="isLoading || !canSubmit"
        data-testid="seed-expand-button"
        @click="expandSeed"
      >
        {{ isLoading ? '正在扩展...' : '扩展相关论文' }}
      </button>
    </header>

    <div class="seed-form">
      <input v-model="seedTitle" placeholder="种子论文标题" data-testid="seed-title-input" />
      <input v-model="seedArxivId" placeholder="arXiv ID" data-testid="seed-arxiv-input" />
      <input v-model="seedDoi" placeholder="DOI" data-testid="seed-doi-input" />
      <input v-model="seedPaperUrl" placeholder="论文链接" data-testid="seed-url-input" />
    </div>

    <div v-if="warnings.length" class="warning-list">
      <span v-for="warning in warnings" :key="`${warning.code}-${warning.message}`" data-testid="seed-warning">
        {{ warningText(warning) }}
      </span>
    </div>

    <div v-if="error" class="error-text" data-testid="seed-error">
      {{ error }}
    </div>

    <div v-if="result && !hasAnyPaper" class="seed-empty" data-testid="seed-empty">
      {{ result.message || '没有返回可扩展的论文。' }}
    </div>

    <div v-if="result && hasAnyPaper" class="seed-results">
      <section v-for="group in groups" :key="group.key" :data-testid="`seed-group-${group.key}`">
        <h3>{{ group.label }}</h3>
        <div v-if="groupItems(group.key).length" class="seed-paper-list">
          <article
            v-for="paper in groupItems(group.key)"
            :key="paper.paper_id || paper.title"
            class="seed-paper"
            data-testid="seed-paper-card"
          >
            <div class="paper-top">
              <div>
                <h4>{{ paper.title }}</h4>
                <p>{{ authorsText(paper.authors) }} · {{ paper.year || '年份未知' }} · {{ paper.venue || paper.source || '来源未知' }}</p>
              </div>
              <button
                type="button"
                class="secondary-btn"
                :disabled="deepReadDisabled(paper)"
                data-testid="seed-deep-read-button"
                @click="prepareDeepRead(paper)"
              >
                {{ deepReadLabel(paper) }}
              </button>
            </div>

            <div class="paper-meta">
              <span data-testid="seed-source">来源：{{ paper.source || '未知' }}</span>
              <span>关系：{{ paper.relation_type || '未知' }}</span>
              <span data-testid="seed-confidence">置信度：{{ percent(paper.confidence) }}</span>
              <span data-testid="seed-verification">验证：{{ paper.verification_status || '未知' }}</span>
              <span data-testid="seed-can-enter-m2">M2：{{ paper.can_enter_m2 ? '可进入' : '待验证' }}</span>
              <span>图谱：{{ paper.citation_graph_verified ? '已验证' : '未验证' }}</span>
            </div>

            <p class="paper-reason" data-testid="seed-relation-reason">{{ paper.relation_reason }}</p>
            <p v-if="!paper.can_enter_m2" class="paper-note">
              {{ paper.deep_read_unavailable_reason || '还没有可解析来源。' }}
            </p>
            <p v-if="handoffState(paper).error" class="paper-note danger" data-testid="seed-handoff-error">
              {{ handoffState(paper).error }}
            </p>
          </article>
        </div>
        <p v-else class="group-empty">这一组暂时没有论文。</p>
      </section>

      <section v-if="result.follow_up_improvements?.length" data-testid="seed-improvements">
        <h3>后续改进方向</h3>
        <ul>
          <li v-for="item in result.follow_up_improvements" :key="item.name">
            {{ item.name }}：{{ item.reason }}
          </li>
        </ul>
      </section>

      <section v-if="result.recommended_expansion_order?.length" data-testid="seed-reading-order">
        <h3>推荐扩展顺序</h3>
        <ol>
          <li v-for="item in result.recommended_expansion_order" :key="`${item.rank}-${item.title}`">
            {{ item.rank }}. {{ item.title }} · {{ item.relation_type }} · M2 {{ item.can_enter_m2 ? '可进入' : '待验证' }}
          </li>
        </ol>
      </section>
    </div>
  </section>
</template>

<style scoped>
.seed-panel {
  display: grid;
  gap: 16px;
  padding: 16px;
}

.seed-head,
.paper-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.seed-head h2 {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 720;
}

.seed-head span {
  display: inline-flex;
  margin-top: 6px;
  color: var(--warning);
  font-size: 13px;
  font-weight: 650;
}

.seed-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.seed-form input {
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 11px 12px;
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-size: 14px;
}

.warning-list {
  display: grid;
  gap: 4px;
}

.warning-list span,
.error-text,
.seed-empty,
.group-empty {
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.7;
}

.error-text,
.paper-note.danger {
  color: var(--danger);
}

.seed-empty {
  border-radius: 8px;
  padding: 12px 14px;
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
}

.seed-results {
  display: grid;
  gap: 20px;
}

.seed-results h3 {
  margin-bottom: 10px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
}

.seed-paper-list {
  display: grid;
  gap: 10px;
}

.seed-paper {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 14px;
  background: var(--bg-secondary);
}

.paper-top h4 {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
  line-height: 1.5;
}

.paper-top p,
.paper-reason,
.paper-note,
.seed-results li {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.paper-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.paper-meta span {
  border-radius: 8px;
  padding: 7px 9px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 13px;
}

.paper-reason {
  margin-top: 10px;
}

.paper-note {
  margin-top: 8px;
  color: var(--warning);
}

.seed-results ul,
.seed-results ol {
  display: grid;
  gap: 6px;
}

@media (max-width: 760px) {
  .seed-head,
  .paper-top {
    flex-direction: column;
  }

  .seed-form,
  .paper-meta {
    grid-template-columns: 1fr;
  }
}
</style>

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
  { key: 'upstream_papers', label: 'Upstream papers' },
  { key: 'downstream_papers', label: 'Downstream papers' },
  { key: 'same_route_papers', label: 'Same-route papers' },
  { key: 'related_surveys', label: 'Related surveys' },
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
  return Array.isArray(authors) && authors.length ? authors.join(', ') : 'Unknown authors'
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
  return Boolean(paper.arxiv_id || paper.arxiv_url || paper.pdf_url)
}

function deepReadDisabled(paper: Record<string, any>) {
  return Boolean(handoffState(paper).loading || !hasDeepReadSource(paper))
}

function deepReadLabel(paper: Record<string, any>) {
  if (!hasDeepReadSource(paper)) return 'Source unavailable'
  return handoffState(paper).loading ? 'Preparing...' : 'Prepare deep read'
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
      error.value = data.detail?.message || data.message || 'Seed expansion request failed.'
    }
  } catch {
    error.value = 'Network error while expanding seed paper.'
  } finally {
    isLoading.value = false
  }
}

async function prepareDeepRead(paper: Record<string, any>) {
  if (!hasDeepReadSource(paper)) {
    setHandoffState(paper, {
      error: paper.deep_read_unavailable_reason || 'No arXiv ID, arXiv URL, or PDF URL is available.',
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
          arxiv_url: paper.arxiv_url || paper.paper_url || paper.url || paper.landing_url || '',
          pdf_url: paper.pdf_url || '',
        },
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok || !data.job_id) {
      const detail = data.detail || data
      setHandoffState(paper, {
        error: `${detail.status || detail.handoff_status || 'HANDOFF_FAILED'}: ${detail.message || 'Seed expansion handoff failed.'}`,
      })
      return
    }
    await router.push(`/learn/${data.job_id}`)
  } catch {
    setHandoffState(paper, { error: 'Network error while preparing PaperWorkspace job.' })
  } finally {
    const state = handoffState(paper)
    if (state.loading) {
      setHandoffState(paper, { ...state, loading: false })
    }
  }
}
</script>

<template>
  <section
    class="rounded-lg p-4"
    style="background: var(--bg-card); border: 1px solid var(--border);"
    data-testid="seed-expansion-panel"
  >
    <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
      <div>
        <div class="text-sm font-semibold mb-1" style="color: var(--text-primary);">SeedExpansionPanel</div>
        <div class="text-xs font-medium" style="color: #f59e0b;" data-testid="seed-status">
          {{ effectiveStatus }}
        </div>
      </div>
      <button
        type="button"
        class="px-3 py-2 rounded-md text-xs font-semibold text-white disabled:opacity-50"
        style="background: var(--accent);"
        :disabled="isLoading || !canSubmit"
        data-testid="seed-expand-button"
        @click="expandSeed"
      >
        {{ isLoading ? 'Expanding...' : 'Expand seed' }}
      </button>
    </div>

    <div class="grid gap-2 mt-4 md:grid-cols-2">
      <input
        v-model="seedTitle"
        class="px-3 py-2 rounded-md text-xs outline-none"
        style="background: var(--bg); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="Seed title"
        data-testid="seed-title-input"
      />
      <input
        v-model="seedArxivId"
        class="px-3 py-2 rounded-md text-xs outline-none"
        style="background: var(--bg); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="arXiv ID"
        data-testid="seed-arxiv-input"
      />
      <input
        v-model="seedDoi"
        class="px-3 py-2 rounded-md text-xs outline-none"
        style="background: var(--bg); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="DOI"
        data-testid="seed-doi-input"
      />
      <input
        v-model="seedPaperUrl"
        class="px-3 py-2 rounded-md text-xs outline-none"
        style="background: var(--bg); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="paper URL"
        data-testid="seed-url-input"
      />
    </div>

    <div v-if="warnings.length" class="mt-3 space-y-1">
      <div v-for="warning in warnings" :key="`${warning.code}-${warning.message}`" class="text-xs" style="color: var(--text-muted);" data-testid="seed-warning">
        {{ warning.code }}: {{ warning.message }}
      </div>
    </div>

    <div v-if="error" class="mt-3 text-xs" style="color: #ef4444;" data-testid="seed-error">
      {{ error }}
    </div>

    <div
      v-if="result && !hasAnyPaper"
      class="mt-4 rounded-md p-3 text-xs"
      style="background: rgba(245,158,11,0.08); color: #f59e0b; border: 1px solid rgba(245,158,11,0.22);"
      data-testid="seed-empty"
    >
      {{ result.message || 'EMPTY_RESULT: no expansion papers were returned.' }}
    </div>

    <div v-if="result && hasAnyPaper" class="mt-5 space-y-5">
      <section
        v-for="group in groups"
        :key="group.key"
        :data-testid="`seed-group-${group.key}`"
      >
        <h3 class="text-xs font-semibold mb-2" style="color: var(--text-primary);">{{ group.label }}</h3>
        <div v-if="groupItems(group.key).length" class="space-y-2">
          <article
            v-for="paper in groupItems(group.key)"
            :key="paper.paper_id || paper.title"
            class="rounded-md p-3"
            style="background: var(--bg); border: 1px solid var(--border);"
            data-testid="seed-paper-card"
          >
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <div class="text-sm font-semibold leading-5" style="color: var(--text-primary);">{{ paper.title }}</div>
                <div class="text-xs mt-1" style="color: var(--text-secondary);">
                  {{ authorsText(paper.authors) }} | {{ paper.year || 'n.d.' }} | {{ paper.venue || paper.source || 'unknown source' }}
                </div>
              </div>
              <button
                type="button"
                class="px-3 py-2 rounded-md text-xs font-semibold text-white disabled:opacity-50"
                style="background: var(--accent);"
                :disabled="deepReadDisabled(paper)"
                data-testid="seed-deep-read-button"
                @click="prepareDeepRead(paper)"
              >
                {{ deepReadLabel(paper) }}
              </button>
            </div>

            <div class="grid gap-2 mt-3 md:grid-cols-4">
              <div class="text-xs" style="color: var(--text-secondary);" data-testid="seed-source">source: {{ paper.source || 'unknown' }}</div>
              <div class="text-xs" style="color: var(--text-secondary);">relation: {{ paper.relation_type }}</div>
              <div class="text-xs" style="color: var(--text-secondary);" data-testid="seed-confidence">confidence: {{ percent(paper.confidence) }}</div>
              <div class="text-xs" style="color: var(--text-secondary);" data-testid="seed-verification">verified: {{ paper.verification_status }}</div>
              <div class="text-xs" style="color: var(--text-secondary);" data-testid="seed-can-enter-m2">can_enter_m2: {{ paper.can_enter_m2 ? 'true' : 'false' }}</div>
              <div class="text-xs" style="color: var(--text-secondary);">basis: {{ paper.relation_basis }}</div>
              <div class="text-xs" style="color: var(--text-secondary);">citation_graph: {{ paper.citation_graph_verified ? 'verified' : 'not_verified' }}</div>
              <div class="text-xs" style="color: var(--text-secondary);">confidence_source: {{ paper.source_confidence }}</div>
            </div>

            <p class="text-xs mt-3" style="color: var(--text-muted);" data-testid="seed-relation-reason">
              {{ paper.relation_reason }}
            </p>
            <p v-if="!paper.can_enter_m2" class="text-xs mt-2" style="color: #f59e0b;">
              {{ paper.deep_read_unavailable_reason || 'No parseable source is available yet.' }}
            </p>
            <p v-if="handoffState(paper).error" class="text-xs mt-2" style="color: #ef4444;" data-testid="seed-handoff-error">
              {{ handoffState(paper).error }}
            </p>
          </article>
        </div>
        <div v-else class="text-xs" style="color: var(--text-muted);">No papers in this group.</div>
      </section>

      <section v-if="result.follow_up_improvements?.length" data-testid="seed-improvements">
        <h3 class="text-xs font-semibold mb-2" style="color: var(--text-primary);">Follow-up improvements</h3>
        <ul class="space-y-1">
          <li v-for="item in result.follow_up_improvements" :key="item.name" class="text-xs" style="color: var(--text-secondary);">
            {{ item.name }}: {{ item.reason }}
          </li>
        </ul>
      </section>

      <section v-if="result.recommended_expansion_order?.length" data-testid="seed-reading-order">
        <h3 class="text-xs font-semibold mb-2" style="color: var(--text-primary);">Recommended expansion order</h3>
        <ol class="space-y-1">
          <li v-for="item in result.recommended_expansion_order" :key="`${item.rank}-${item.title}`" class="text-xs" style="color: var(--text-secondary);">
            {{ item.rank }}. {{ item.title }} | {{ item.relation_type }} | can_enter_m2: {{ item.can_enter_m2 ? 'true' : 'false' }}
          </li>
        </ol>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import SeedExpansionPanel from '../components/SeedExpansionPanel.vue'

const query = ref('')
const isLoading = ref(false)
const error = ref('')
const result = ref<Record<string, any> | null>(null)

const status = computed(() => result.value?.direction_workspace_status || result.value?.status || '')
const warnings = computed(() => normalizeWarnings(result.value?.warnings || []))
const papers = computed(() => result.value?.papers || result.value?.candidate_cards || [])
const hasEmptyResult = computed(() => ['EMPTY_RESULT', 'BLOCKED'].includes(String(status.value)))

async function search() {
  if (!query.value.trim() || isLoading.value) return
  isLoading.value = true
  error.value = ''
  result.value = null
  try {
    const res = await fetch('/api/v1/directions/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.value.trim() }),
    })
    const data = await res.json().catch(() => ({}))
    result.value = data
    if (!res.ok) {
      error.value = data.detail?.message || 'DirectionWorkspace request failed.'
    }
  } catch {
    error.value = 'Network error while loading DirectionWorkspace.'
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

function percent(value: unknown) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 'n/a'
  return `${Math.round(num * 100)}%`
}

function authorsText(authors: unknown) {
  return Array.isArray(authors) && authors.length ? authors.join(', ') : 'Unknown authors'
}

function deepReadJobId(paper: Record<string, any>) {
  return paper.paper_workspace_job_id || paper.job_id || ''
}

function deepReadLabel(paper: Record<string, any>) {
  return deepReadJobId(paper) ? '进入精读' : '待接入'
}

function openDeepRead(paper: Record<string, any>) {
  const jobId = deepReadJobId(paper)
  if (jobId) {
    window.location.assign(`/learn/${jobId}`)
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-6 py-10">
    <header class="mb-8">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">DirectionWorkspace</h1>
      <p class="text-sm" style="color: var(--text-secondary);">输入研究方向，生成可审计的 M1 方向探索结果。</p>
    </header>

    <form class="flex gap-2 mb-6" @submit.prevent="search">
      <input
        v-model="query"
        data-testid="direction-query"
        class="flex-1 px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="time-series anomaly detection"
      />
      <button
        type="submit"
        class="px-4 py-2 rounded-md text-sm font-semibold text-white disabled:opacity-40"
        style="background: var(--accent);"
        :disabled="isLoading || !query.trim()"
      >
        {{ isLoading ? '检索中' : '探索方向' }}
      </button>
    </form>

    <section
      v-if="result"
      class="rounded-lg p-4 mb-5"
      style="background: var(--bg-card); border: 1px solid var(--border);"
      data-testid="direction-status"
    >
      <div class="flex flex-wrap items-center gap-3 mb-2">
        <div class="text-sm font-semibold" style="color: var(--text-primary);">
          {{ status }}
        </div>
        <div class="text-xs" style="color: var(--text-secondary);">{{ papers.length }} candidates</div>
      </div>
      <div class="text-xs mb-3" style="color: var(--text-secondary);">{{ result.message }}</div>
      <div v-if="warnings.length" class="space-y-1">
        <div v-for="warning in warnings" :key="warning.code" class="text-xs" style="color: var(--text-muted);" data-testid="direction-warning">
          {{ warning.code }}: {{ warning.message }}
        </div>
      </div>
    </section>

    <div v-if="error" class="mb-5 px-4 py-3 rounded-md text-sm" style="background: rgba(239,68,68,0.08); color: #ef4444;">
      {{ error }}
    </div>

    <section v-if="result?.overview" class="mb-6" data-testid="direction-overview">
      <h2 class="text-sm font-semibold mb-2" style="color: var(--text-primary);">方向概览</h2>
      <p class="text-sm leading-6" style="color: var(--text-secondary);">{{ result.overview }}</p>
    </section>

    <section v-if="result?.key_sub_directions?.length" class="mb-6" data-testid="sub-directions">
      <h2 class="text-sm font-semibold mb-3" style="color: var(--text-primary);">关键子方向</h2>
      <div class="grid gap-2 md:grid-cols-2">
        <div
          v-for="item in result.key_sub_directions"
          :key="item.name"
          class="rounded-md px-3 py-2"
          style="background: var(--bg-card); border: 1px solid var(--border);"
        >
          <div class="text-sm font-medium" style="color: var(--text-primary);">{{ item.name }}</div>
          <div class="text-xs mt-1" style="color: var(--text-muted);">{{ item.description }}</div>
        </div>
      </div>
    </section>

    <section v-if="result?.method_families?.length" class="mb-6" data-testid="method-families">
      <h2 class="text-sm font-semibold mb-3" style="color: var(--text-primary);">方法家族</h2>
      <div class="grid gap-2 md:grid-cols-3">
        <div
          v-for="family in result.method_families"
          :key="family.role || family.name"
          class="rounded-md px-3 py-2"
          style="background: var(--bg-card); border: 1px solid var(--border);"
        >
          <div class="text-sm font-medium" style="color: var(--text-primary);">{{ family.name }}</div>
          <div class="text-xs mt-1" style="color: var(--text-muted);">{{ family.paper_count }} papers</div>
        </div>
      </div>
    </section>

    <section v-if="papers.length" class="mb-6">
      <h2 class="text-sm font-semibold mb-3" style="color: var(--text-primary);">代表论文候选</h2>
      <div class="space-y-3">
        <article
          v-for="paper in papers"
          :key="paper.paper_id || paper.title"
          class="rounded-md p-4"
          style="background: var(--bg-card); border: 1px solid var(--border);"
          data-testid="candidate-card"
        >
          <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 class="text-sm font-semibold leading-5" style="color: var(--text-primary);">{{ paper.title }}</h3>
              <p class="text-xs mt-1" style="color: var(--text-secondary);">
                {{ authorsText(paper.authors) }} · {{ paper.year || 'n.d.' }} · {{ paper.venue || paper.source || 'unknown source' }}
              </p>
            </div>
            <button
              type="button"
              class="px-3 py-2 rounded-md text-xs font-semibold disabled:opacity-50"
              style="background: var(--accent); color: white;"
              :disabled="!deepReadJobId(paper)"
              data-testid="deep-read-button"
              @click="openDeepRead(paper)"
            >
              {{ deepReadLabel(paper) }}
            </button>
          </div>

          <div class="grid gap-2 mt-4 md:grid-cols-4">
            <div class="text-xs" style="color: var(--text-secondary);">source: {{ paper.source || 'unknown' }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">relevance: {{ percent(paper.relevance_score) }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">verified: {{ paper.verification_status }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">confidence: {{ paper.source_confidence }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">pdf: {{ paper.pdf_available ? 'available' : 'unavailable' }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">canonical: {{ paper.canonicalization_status }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">m2_ready: {{ paper.m2_ready ? 'true' : 'false' }}</div>
            <div class="text-xs" style="color: var(--text-secondary);">priority: {{ paper.priority }}</div>
          </div>
          <p v-if="paper.risk_note" class="text-xs mt-3" style="color: var(--text-muted);">{{ paper.risk_note }}</p>
        </article>
      </div>
    </section>

    <section v-if="result?.recommended_reading_order?.length" class="mb-6" data-testid="reading-order">
      <h2 class="text-sm font-semibold mb-3" style="color: var(--text-primary);">推荐阅读顺序</h2>
      <ol class="space-y-2">
        <li
          v-for="item in result.recommended_reading_order"
          :key="`${item.rank}-${item.title}`"
          class="text-sm"
          style="color: var(--text-secondary);"
        >
          {{ item.rank }}. {{ item.title }} · {{ item.priority }} · {{ item.role }}
        </li>
      </ol>
    </section>

    <section
      v-if="result && hasEmptyResult"
      class="mb-6 rounded-md p-4 text-sm"
      style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary);"
      data-testid="empty-result"
    >
      没有可展示的候选论文。请换一个更具体的方向或稍后重试外部源。
    </section>

    <SeedExpansionPanel
      :status="result?.seed_expansion_status || 'NOT_IMPLEMENTED'"
      :warnings="warnings"
    />
  </div>
</template>

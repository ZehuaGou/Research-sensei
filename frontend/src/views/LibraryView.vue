<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ApiClientError, apiErrorMessage, researchApi } from '../api/client'
import type { LibraryPaper, SearchRun } from '../types/api'

const query = ref('')
const papers = ref<LibraryPaper[]>([])
const searchRuns = ref<SearchRun[]>([])
const loading = ref(false)
const deletingId = ref('')
const openingId = ref('')
const error = ref('')
const message = ref('')
const router = useRouter()

const totalSizeMb = computed(() => {
  const total = papers.value.reduce((sum, paper) => sum + Number(paper.file_size || 0), 0)
  return (total / 1024 / 1024).toFixed(1)
})

onMounted(() => {
  void refresh()
})

async function refresh() {
  await Promise.all([loadPapers(), loadSearchRuns()])
}

async function loadPapers() {
  loading.value = true
  error.value = ''
  try {
    const data = await researchApi.listLibraryPapers(query.value.trim(), 200)
    papers.value = Array.isArray(data.papers) ? data.papers : []
  } catch (loadError) {
    error.value = apiErrorMessage(loadError, 'Failed to reach the backend paper library API.')
  } finally {
    loading.value = false
  }
}

async function loadSearchRuns() {
  try {
    const data = await researchApi.listSearchRuns(20)
    searchRuns.value = data.search_runs
  } catch {
    searchRuns.value = []
  }
}

async function removePaper(paper: LibraryPaper) {
  if (!paper.paper_id || deletingId.value) return
  if (typeof window !== 'undefined' && !window.confirm(`Delete local PDF and library record for "${paper.title}"?`)) {
    return
  }
  deletingId.value = paper.paper_id
  message.value = ''
  error.value = ''
  try {
    await researchApi.deleteLibraryPaper(paper.paper_id)
    papers.value = papers.value.filter(item => item.paper_id !== paper.paper_id)
    message.value = 'Paper removed from the local library.'
    await loadSearchRuns()
  } catch (deleteError) {
    error.value = apiErrorMessage(deleteError, 'Delete request failed.')
  } finally {
    deletingId.value = ''
  }
}

async function openPaperWorkspace(paper: LibraryPaper) {
  if (!paper.paper_id || !paper.local_path || openingId.value) return
  openingId.value = paper.paper_id
  message.value = ''
  error.value = ''
  try {
    const form = new FormData()
    form.append('local_path', paper.local_path)
    form.append('title', paper.title || '')
    const data = await researchApi.parseDocument(form)
    await router.push(`/learn/${data.job_id}`)
  } catch (openError) {
    error.value = parseOpenError(openError)
  } finally {
    openingId.value = ''
  }
}

function parseOpenError(error: unknown) {
  if (error instanceof ApiClientError && error.detail) {
    const sourceStatus = error.detail.source_status
    if (sourceStatus && typeof sourceStatus === 'object') {
      const warnings = (sourceStatus as { warnings?: unknown }).warnings
      if (Array.isArray(warnings)) return warnings.join(', ')
    }
    if (error.detail.message) return error.detail.message
    if (error.detail.status) return error.detail.status
  }
  return 'Failed to prepare PaperWorkspace for this local paper.'
}

function venueText(paper: LibraryPaper) {
  return paper.venue_canonical_name || paper.venue || 'Unknown venue'
}

function authorsText(paper: LibraryPaper) {
  return Array.isArray(paper.authors) && paper.authors.length ? paper.authors.join(', ') : 'Unknown authors'
}

function compactPath(path: string | undefined) {
  if (!path) return 'No local path'
  const normalized = path.replace(/\\/g, '/')
  const parts = normalized.split('/')
  return parts.length > 4 ? `.../${parts.slice(-4).join('/')}` : path
}

function formatDate(value: string | undefined) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
</script>

<template>
  <main class="library-page">
    <section class="library-head">
      <div>
        <p class="eyebrow">M1 Paper Library</p>
        <h1>本地论文库</h1>
        <p class="intro">
          M1 已下载和复用的论文集中放在这里，可以直接进入 PaperWorkspace 解析。
        </p>
      </div>
      <div class="stats surface">
        <span>{{ papers.length }}</span>
        <small>papers</small>
        <span>{{ totalSizeMb }} MB</span>
        <small>local files</small>
      </div>
    </section>

    <form class="toolbar surface" @submit.prevent="loadPapers">
      <input
        v-model="query"
        data-testid="library-query"
        placeholder="Search title or venue"
      />
      <button type="submit" class="primary-btn" :disabled="loading">
        {{ loading ? 'Loading...' : 'Search' }}
      </button>
      <button type="button" class="secondary-btn" :disabled="loading" @click="refresh">
        Refresh
      </button>
    </form>

    <p v-if="message" class="notice">{{ message }}</p>
    <p v-if="error" class="error-box">{{ error }}</p>

    <section class="paper-list" data-testid="library-papers">
      <article v-for="paper in papers" :key="paper.paper_id" class="paper-row surface">
        <div class="paper-main">
          <div class="paper-title-line">
            <h2>{{ paper.title }}</h2>
            <span class="rank-pill">{{ paper.venue_rank || 'unranked' }}</span>
          </div>
          <p>{{ authorsText(paper) }}</p>
          <div class="meta-line">
            <span>{{ venueText(paper) }}</span>
            <span v-if="paper.year">{{ paper.year }}</span>
            <span v-if="paper.doi">DOI {{ paper.doi }}</span>
            <span v-if="paper.arxiv_id">arXiv {{ paper.arxiv_id }}</span>
          </div>
          <code :title="paper.local_path">{{ compactPath(paper.local_path) }}</code>
          <small v-if="paper.downloaded_at">Downloaded {{ formatDate(paper.downloaded_at) }}</small>
        </div>
        <div class="paper-actions">
          <button
            type="button"
            class="primary-btn"
            data-testid="open-library-paper"
            :disabled="!paper.local_path || openingId === paper.paper_id"
            @click="openPaperWorkspace(paper)"
          >
            {{ openingId === paper.paper_id ? 'Opening...' : 'Analyze' }}
          </button>
          <button
            type="button"
            class="ghost-btn danger"
            data-testid="delete-library-paper"
            :disabled="deletingId === paper.paper_id || openingId === paper.paper_id"
            @click="removePaper(paper)"
          >
            {{ deletingId === paper.paper_id ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </article>
      <div v-if="!loading && papers.length === 0" class="empty surface" data-testid="library-empty">
        No downloaded papers are in the local library yet.
      </div>
    </section>

    <section class="runs surface" data-testid="library-runs">
      <header>
        <h2>Recent M1 search runs</h2>
      </header>
      <div v-if="searchRuns.length" class="run-list">
        <div v-for="run in searchRuns" :key="run.run_id" class="run-row">
          <strong>{{ run.query }}</strong>
          <span>{{ run.candidate_count }} candidates</span>
          <span>{{ run.downloaded_count }} downloaded</span>
          <span>{{ run.reused_count }} reused</span>
          <small>{{ formatDate(run.created_at) }}</small>
        </div>
      </div>
      <p v-else>No M1 search runs have been recorded yet.</p>
    </section>
  </main>
</template>

<style scoped>
.library-page {
  width: min(1040px, calc(100vw - 36px));
  margin: 0 auto;
  padding: 34px 0 60px;
}

.library-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 20px;
  align-items: end;
  margin-bottom: 20px;
}

.eyebrow {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0;
}

h1 {
  margin: 4px 0 8px;
  color: var(--text-primary);
  font-size: 30px;
  font-weight: 720;
  line-height: 1.18;
}

.intro {
  max-width: 760px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 14px;
  padding: 12px;
}

.stats span {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 720;
}

.stats small {
  color: var(--text-muted);
  font-size: 13px;
}

.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
  padding: 10px;
}

.toolbar input {
  min-width: 0;
  flex: 1;
  min-height: 42px;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0 12px;
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.notice,
.error-box {
  margin: 0 0 14px;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}

.notice {
  background: rgba(5, 150, 105, 0.1);
  color: var(--success);
}

.error-box {
  border: 1px solid rgba(220, 38, 38, 0.18);
  background: rgba(220, 38, 38, 0.1);
  color: var(--danger);
}

.paper-list {
  display: grid;
  gap: 8px;
}

.paper-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: start;
  padding: 14px 16px;
}

.paper-title-line {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.paper-row h2 {
  min-width: 0;
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
  line-height: 1.35;
}

.rank-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--accent-light);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}

.paper-main p {
  margin: 6px 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 13px;
}

.meta-line span {
  border-radius: 999px;
  background: var(--bg-secondary);
  padding: 2px 8px;
}

code {
  display: block;
  overflow-wrap: anywhere;
  color: var(--text-secondary);
  font-size: 12px;
}

.paper-main small {
  display: block;
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.paper-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
  align-items: center;
}

.danger {
  color: var(--danger);
}

.empty {
  padding: 22px;
  color: var(--text-secondary);
  text-align: center;
}

.runs {
  margin-top: 20px;
  padding: 14px;
}

.runs h2 {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
}

.run-list {
  display: grid;
  gap: 8px;
}

.run-row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) repeat(3, auto) minmax(160px, auto);
  gap: 10px;
  align-items: center;
  border-top: 1px solid var(--border-subtle);
  padding-top: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.run-row strong {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.run-row small {
  color: var(--text-muted);
}

@media (max-width: 760px) {
  .library-head,
  .paper-row,
  .run-row {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .paper-actions {
    justify-content: flex-start;
  }

  .toolbar input {
    flex-basis: 100%;
  }
}
</style>

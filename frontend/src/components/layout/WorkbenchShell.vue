<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '../../stores/theme'

type SearchRun = {
  run_id: string
  query: string
  created_at: string
  candidate_count: number
  downloaded_count: number
  reused_count: number
  papers?: Array<Record<string, any>>
}

type CommandItem = {
  id: string
  section: string
  title: string
  meta: string
  kind: 'page' | 'run' | 'pinned'
  to?: string
  run?: SearchRun
  query?: string
}

const router = useRouter()
const route = useRoute()
const theme = useThemeStore()

const collapsed = ref(loadBoolean('researchsensei.sidebarCollapsed') || isNarrowViewport())
const commandQuery = ref('')
const showCommandPalette = ref(false)
const paletteInput = ref<HTMLInputElement | null>(null)
const searchRuns = ref<SearchRun[]>([])
const pinnedDirections = ref<string[]>(loadPinnedDirections())

const routeTitle = computed(() => {
  const labels: Record<string, string> = {
    directions: '方向工作台',
    'paper-library': '论文库',
    learn: '深读工作区',
    upload: '新建深读',
    settings: '模型设置',
  }
  return labels[String(route.name || '')] || 'Research Sensei'
})

const groupedDirections = computed(() => {
  const seen = new Set<string>()
  const result: SearchRun[] = []
  for (const run of searchRuns.value) {
    const key = normalizeDirection(run.query)
    if (!key || seen.has(key)) continue
    seen.add(key)
    result.push(run)
  }
  return result
})

const filteredDirections = computed(() => groupedDirections.value)
const filteredPinned = computed(() => pinnedDirections.value)

const workspaceLinks = computed(() => [
  { label: '方向检索', short: 'D', to: '/directions/new', active: route.name === 'directions' },
  { label: '本地论文库', short: 'L', to: '/papers/library', active: route.name === 'paper-library' },
  { label: '新建深读', short: 'R', to: '/papers/upload', active: route.name === 'upload' },
  { label: '模型设置', short: 'S', to: '/settings', active: route.name === 'settings' },
])

const commandItems = computed<CommandItem[]>(() => {
  const needle = commandQuery.value.trim().toLowerCase()
  const pages: CommandItem[] = workspaceLinks.value.map((item) => ({
    id: `page:${item.to}`,
    section: '页面',
    title: item.label,
    meta: item.to,
    kind: 'page',
    to: item.to,
  }))
  const pinned: CommandItem[] = pinnedDirections.value.map((query) => ({
    id: `pinned:${normalizeDirection(query)}`,
    section: '置顶方向',
    title: query,
    meta: '打开已有论文列表',
    kind: 'pinned',
    query,
  }))
  const runs: CommandItem[] = groupedDirections.value.map((run) => ({
    id: `run:${run.run_id}`,
    section: '最近方向',
    title: run.query,
    meta: formatCount(run),
    kind: 'run',
    run,
  }))
  const all = [...pages, ...pinned, ...runs]
  if (!needle) return all.slice(0, 18)
  return all
    .filter((item) => `${item.section} ${item.title} ${item.meta}`.toLowerCase().includes(needle))
    .slice(0, 18)
})

onMounted(() => {
  if (isNarrowViewport()) collapsed.value = true
  window.addEventListener('resize', handleViewportResize)
  void loadSearchRuns()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleViewportResize)
})

watch(collapsed, (value) => {
  if (isNarrowViewport()) return
  localStorage.setItem('researchsensei.sidebarCollapsed', value ? '1' : '0')
})

watch(pinnedDirections, (value) => {
  localStorage.setItem('researchsensei.pinnedDirections', JSON.stringify(value))
}, { deep: true })

watch(() => route.fullPath, () => {
  if (route.name === 'directions' || route.name === 'paper-library') {
    void loadSearchRuns()
  }
})

async function loadSearchRuns() {
  try {
    const res = await fetch('/api/v1/library/search_runs?limit=60')
    const data = await res.json().catch(() => ({}))
    searchRuns.value = res.ok && Array.isArray(data.search_runs) ? data.search_runs : []
  } catch {
    searchRuns.value = []
  }
}

function normalizeDirection(query: string) {
  return query.toLowerCase().replace(/[\s\-_:;,.，。；：]+/g, ' ').trim()
}

function openDirectionRun(run: SearchRun) {
  void router.push({ path: '/directions/new', query: { run_id: run.run_id } })
}

function openPinnedDirection(query: string) {
  void router.push({ path: '/directions/new', query: { history_q: query } })
}

function newDirection() {
  void router.push('/directions/new')
}

function openCommandPalette() {
  commandQuery.value = ''
  showCommandPalette.value = true
  void nextTick(() => paletteInput.value?.focus())
}

function closeCommandPalette() {
  showCommandPalette.value = false
}

function runCommand(item: CommandItem) {
  if (item.kind === 'page' && item.to) {
    void router.push(item.to)
  } else if (item.kind === 'run' && item.run) {
    openDirectionRun(item.run)
  } else if (item.kind === 'pinned' && item.query) {
    openPinnedDirection(item.query)
  }
  closeCommandPalette()
}

function runFirstCommand() {
  const first = commandItems.value[0]
  if (first) runCommand(first)
}

function togglePinned(query: string) {
  const trimmed = query.trim()
  if (!trimmed) return
  const index = pinnedDirections.value.findIndex((item) => normalizeDirection(item) === normalizeDirection(trimmed))
  if (index >= 0) {
    pinnedDirections.value = pinnedDirections.value.filter((_, itemIndex) => itemIndex !== index)
  } else {
    pinnedDirections.value = [trimmed, ...pinnedDirections.value].slice(0, 12)
  }
}

function isPinned(query: string) {
  const key = normalizeDirection(query)
  return pinnedDirections.value.some((item) => normalizeDirection(item) === key)
}

function loadBoolean(key: string) {
  if (typeof localStorage === 'undefined') return false
  return localStorage.getItem(key) === '1'
}

function isNarrowViewport() {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(max-width: 900px)').matches
}

function handleViewportResize() {
  if (isNarrowViewport()) collapsed.value = true
}

function loadPinnedDirections() {
  if (typeof localStorage === 'undefined') return []
  try {
    const raw = JSON.parse(localStorage.getItem('researchsensei.pinnedDirections') || '[]')
    return Array.isArray(raw) ? raw.map((item) => String(item || '').trim()).filter(Boolean) : []
  } catch {
    return []
  }
}

function formatCount(run: SearchRun) {
  return `${run.candidate_count || 0} 论文`
}
</script>

<template>
  <div class="codex-shell" :class="{ collapsed }">
    <aside class="workbench-sidebar">
      <header class="sidebar-brand">
        <router-link to="/directions/new" class="brand-mark" aria-label="Research Sensei">
          R
        </router-link>
        <div class="brand-text">
          <strong>Research-sensei</strong>
          <span>main</span>
        </div>
      </header>

      <nav class="utility-nav" aria-label="快捷操作">
        <button type="button" aria-label="新对话" @click="newDirection">
          <span class="nav-symbol">□</span>
          <span>新对话</span>
        </button>
        <button type="button" aria-label="搜索工作区" data-testid="sidebar-search" @click="openCommandPalette">
          <span class="nav-symbol">⌕</span>
          <span>搜索</span>
        </button>
      </nav>

      <nav class="workspace-nav" aria-label="工作区">
        <router-link
          v-for="item in workspaceLinks"
          :key="item.to"
          :to="item.to"
          :class="{ active: item.active }"
        >
          <b>{{ item.short }}</b>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-history">
        <section v-if="filteredPinned.length" class="sidebar-section">
          <h2>置顶</h2>
          <div v-for="query in filteredPinned" :key="query" class="pinned-row">
            <button type="button" class="direction-item pinned" @click="openPinnedDirection(query)">
              <span>{{ query }}</span>
              <small>方向</small>
            </button>
            <button
              type="button"
              class="unpin-item"
              aria-label="取消置顶"
              title="取消置顶"
              @click.stop="togglePinned(query)"
            >
              ×
            </button>
          </div>
        </section>

        <section class="sidebar-section directions-tree">
          <h2>最近方向</h2>
          <div v-for="run in filteredDirections" :key="run.run_id" class="direction-row">
            <button type="button" class="direction-item" @click="openDirectionRun(run)">
              <span>{{ run.query }}</span>
              <small>{{ formatCount(run) }}</small>
            </button>
            <button
              type="button"
              class="pin-item"
              :class="{ active: isPinned(run.query) }"
              :aria-label="isPinned(run.query) ? '取消置顶' : '置顶方向'"
              :title="isPinned(run.query) ? '取消置顶' : '置顶方向'"
              @click.stop="togglePinned(run.query)"
            >
              {{ isPinned(run.query) ? '★' : '☆' }}
            </button>
          </div>
          <p v-if="!filteredDirections.length">暂无记录的方向。</p>
        </section>
      </div>

    </aside>

    <section class="workbench-frame">
      <header class="workbench-topbar">
        <div class="topbar-left">
          <button type="button" class="topbar-btn icon-only" aria-label="返回" @click="router.back()">‹</button>
          <button
            type="button"
            class="topbar-btn icon-only"
            :aria-label="collapsed ? '展开边栏' : '收起边栏'"
            @click="collapsed = !collapsed"
          >
            {{ collapsed ? '☰' : '☷' }}
          </button>
          <strong>{{ routeTitle }}</strong>
          <span class="branch-pill">main</span>
        </div>
        <div id="workbench-topbar-center" class="topbar-center" />
        <div class="topbar-right">
          <button type="button" class="topbar-btn open-location" @click="router.push('/papers/library')">论文库</button>
          <button type="button" class="topbar-btn icon-only" aria-label="切换主题" @click="theme.toggle()">
            {{ theme.isDark ? '☀' : '◐' }}
          </button>
        </div>
      </header>

      <main class="workbench-content">
        <slot />
      </main>
    </section>

    <Teleport to="body">
      <div
        v-if="showCommandPalette"
        class="command-backdrop"
        role="presentation"
        @click.self="closeCommandPalette"
      >
        <section class="command-palette" role="dialog" aria-modal="true" aria-label="搜索工作区" @keydown.esc="closeCommandPalette">
          <header>
            <span>⌕</span>
            <input
              class="command-input"
              data-testid="command-input"
              aria-label="搜索页面和方向"
              ref="paletteInput"
              v-model="commandQuery"
              placeholder="搜索页面、置顶方向或最近方向"
              @keydown.enter.prevent="runFirstCommand"
            />
          </header>
          <div v-if="commandItems.length" class="command-list">
            <button
              v-for="item in commandItems"
              :key="item.id"
              type="button"
              @click="runCommand(item)"
            >
              <span>{{ item.section }}</span>
              <strong>{{ item.title }}</strong>
              <small>{{ item.meta }}</small>
            </button>
          </div>
          <p v-else>没有匹配结果。</p>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.codex-shell {
  display: grid;
  grid-template-columns: 292px minmax(0, 1fr);
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.codex-shell.collapsed {
  grid-template-columns: 64px minmax(0, 1fr);
}

.workbench-sidebar {
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 10px;
  min-width: 0;
  border-right: 1px solid var(--sidebar-border);
  padding: 12px 10px 10px;
  background: var(--bg-sidebar);
  color: var(--sidebar-text);
  overflow: hidden;
}

.sidebar-brand {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 38px;
  padding: 2px 2px 12px;
}

.brand-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--sidebar-text);
  font-weight: 680;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border: 1px solid var(--sidebar-border);
  background: var(--bg-card);
  font-size: 13px;
  text-decoration: none;
}

.brand-text {
  min-width: 0;
}

.brand-text strong,
.brand-text span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-text strong {
  color: var(--sidebar-text);
  font-size: 14px;
  font-weight: 620;
}

.brand-text span {
  color: var(--sidebar-muted);
  font-size: 12px;
}

.utility-nav,
.workspace-nav,
.sidebar-section {
  display: grid;
  gap: 2px;
}

.utility-nav button,
.workspace-nav a,
.direction-item {
  display: grid;
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--sidebar-text);
  text-decoration: none;
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease;
}

.utility-nav button,
.workspace-nav a {
  grid-template-columns: 26px minmax(0, 1fr);
  min-height: 36px;
  gap: 6px;
  padding: 6px 8px;
  font-size: 14px;
  font-weight: 520;
  justify-items: start;
  text-align: left;
}

.nav-symbol,
.workspace-nav a b {
  display: flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  color: var(--sidebar-muted);
  font-size: 14px;
  font-weight: 560;
}

.workspace-nav a b {
  border-radius: 6px;
  font-size: 11px;
  font-weight: 680;
}

.utility-nav button:hover,
.workspace-nav a:hover,
.workspace-nav a.active,
.direction-item:hover {
  background: var(--sidebar-hover);
}

.workspace-nav a.active,
.direction-item.pinned {
  background: var(--sidebar-surface);
}

.sidebar-history {
  display: grid;
  min-height: 0;
  align-content: start;
  gap: 18px;
  overflow-y: auto;
  padding: 14px 2px 18px 0;
}

.directions-tree {
  overflow: visible;
}

.sidebar-section h2 {
  margin: 2px 8px 5px;
  color: var(--sidebar-muted);
  font-size: 13px;
  font-weight: 650;
}

.direction-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px;
  gap: 3px;
  align-items: center;
  border-radius: 8px;
}

.direction-row:hover {
  background: var(--sidebar-hover);
}

.pinned-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 26px;
  align-items: center;
  border-radius: 8px;
}

.pinned-row:hover {
  background: var(--sidebar-hover);
}

.pinned-row .direction-item {
  min-width: 0;
}

.direction-item {
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 8px;
  padding: 7px 8px;
  text-align: left;
}

.direction-row .direction-item {
  min-width: 0;
}

.pin-item,
.unpin-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  min-width: 22px;
  height: 22px;
  border-radius: 6px;
  margin: 0;
  padding: 0;
  background: transparent;
  color: var(--sidebar-muted);
  font-size: 12px;
  font-weight: 560;
}

.pin-item:hover,
.pin-item.active,
.unpin-item:hover {
  background: var(--sidebar-surface);
  color: var(--sidebar-text);
}

.unpin-item {
  margin-right: 4px;
  font-size: 16px;
}

.direction-item span {
  min-width: 0;
  overflow: hidden;
  color: var(--sidebar-text);
  font-size: 14px;
  font-weight: 560;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.direction-item small {
  color: var(--sidebar-muted);
  font-size: 13px;
}

.sidebar-section p {
  margin: 6px 8px;
  color: var(--sidebar-muted);
  font-size: 13px;
  line-height: 1.5;
}

.workbench-frame {
  display: grid;
  min-width: 0;
  grid-template-rows: 49px minmax(0, 1fr);
}

.workbench-topbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  min-width: 0;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 18px;
  background: var(--bg-card);
}

.topbar-left,
.topbar-right {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.topbar-center {
  display: flex;
  min-width: 0;
  justify-content: center;
}

.topbar-left strong {
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topbar-btn {
  display: inline-flex;
  min-height: 30px;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 0 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 560;
}

.topbar-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.topbar-btn.icon-only {
  width: 30px;
  padding: 0;
}

.open-location {
  border-color: var(--border-subtle);
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
}

.branch-pill {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  padding: 0 8px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 560;
}

.workbench-content {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background: var(--bg-primary);
}

.command-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: start center;
  padding-top: min(16vh, 128px);
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(5px);
}

.command-palette {
  width: min(680px, calc(100vw - 28px));
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  background: var(--bg-card);
  box-shadow: 0 24px 80px rgba(18, 18, 16, 0.18);
}

.command-palette header {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
  padding: 12px 14px;
}

.command-palette header span {
  color: var(--text-muted);
  font-size: 18px;
}

.command-palette input {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  font-size: 17px;
  outline: none;
}

.command-palette input:focus {
  box-shadow: none;
}

.command-list {
  display: grid;
  max-height: min(62vh, 560px);
  overflow-y: auto;
  padding: 8px;
}

.command-list button {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border-radius: 9px;
  padding: 10px 11px;
  background: transparent;
  text-align: left;
}

.command-list button:hover {
  background: var(--bg-hover);
}

.command-list span,
.command-list small,
.command-palette p {
  color: var(--text-muted);
  font-size: 12px;
}

.command-list strong {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 620;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-list small {
  overflow: hidden;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.command-palette p {
  margin: 0;
  padding: 18px;
  line-height: 1.6;
}

.codex-shell.collapsed .workbench-sidebar {
  padding-inline: 8px;
}

.codex-shell.collapsed .brand-text,
.codex-shell.collapsed .utility-nav button span:last-child,
.codex-shell.collapsed .workspace-nav a span,
.codex-shell.collapsed .sidebar-history {
  display: none;
}

.codex-shell.collapsed .sidebar-brand,
.codex-shell.collapsed .utility-nav button,
.codex-shell.collapsed .workspace-nav a {
  grid-template-columns: 1fr;
  justify-items: center;
  padding-inline: 0;
}

@media (max-width: 900px) {
  .codex-shell,
  .codex-shell.collapsed {
    grid-template-columns: 1fr;
  }

  .workbench-sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 110;
    width: min(292px, calc(100vw - 52px));
    box-shadow: var(--shadow-lg);
    transform: translateX(0);
  }

  .codex-shell.collapsed .workbench-sidebar {
    transform: translateX(-100%);
  }

  .codex-shell.collapsed .brand-text,
  .codex-shell.collapsed .utility-nav button span:last-child,
  .codex-shell.collapsed .workspace-nav a span,
  .codex-shell.collapsed .sidebar-history {
    display: block;
  }

  .codex-shell.collapsed .sidebar-brand,
  .codex-shell.collapsed .utility-nav button,
  .codex-shell.collapsed .workspace-nav a {
    grid-template-columns: 34px minmax(0, 1fr);
    justify-items: stretch;
    padding-inline: 8px;
  }
}
</style>

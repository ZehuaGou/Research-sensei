<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '../../stores/theme'

type SearchRun = {
  run_id: string
  query: string
  created_at: string
  candidate_count: number
  downloaded_count: number
  reused_count: number
}

const router = useRouter()
const route = useRoute()
const theme = useThemeStore()

const collapsed = ref(loadBoolean('researchsensei.sidebarCollapsed'))
const sidebarSearch = ref('')
const searchRuns = ref<SearchRun[]>([])
const pinnedDirections = ref<string[]>(loadPinnedDirections())

const routeTitle = computed(() => {
  const labels: Record<string, string> = {
    directions: '找方向',
    'paper-library': '论文库',
    learn: '论文深读',
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

const filteredDirections = computed(() => {
  const needle = sidebarSearch.value.trim().toLowerCase()
  const items = groupedDirections.value
  if (!needle) return items
  return items.filter(run => run.query.toLowerCase().includes(needle))
})

const filteredPinned = computed(() => {
  const needle = sidebarSearch.value.trim().toLowerCase()
  if (!needle) return pinnedDirections.value
  return pinnedDirections.value.filter(query => query.toLowerCase().includes(needle))
})

const workspaceLinks = computed(() => [
  { label: '新方向', short: '新', to: '/directions/new', active: route.name === 'directions' },
  { label: '论文库', short: '库', to: '/papers/library', active: route.name === 'paper-library' },
  { label: '读论文', short: '读', to: '/papers/upload', active: route.name === 'upload' },
  { label: '插件设置', short: '设', to: '/settings', active: route.name === 'settings' },
])

onMounted(() => {
  void loadSearchRuns()
})

watch(collapsed, value => {
  localStorage.setItem('researchsensei.sidebarCollapsed', value ? '1' : '0')
})

watch(pinnedDirections, value => {
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

function openDirection(query: string) {
  void router.push({ path: '/directions/new', query: { q: query } })
}

function newDirection() {
  void router.push('/directions/new')
}

function togglePinned(query: string) {
  const trimmed = query.trim()
  if (!trimmed) return
  const index = pinnedDirections.value.findIndex(item => normalizeDirection(item) === normalizeDirection(trimmed))
  if (index >= 0) {
    pinnedDirections.value = pinnedDirections.value.filter((_, itemIndex) => itemIndex !== index)
  } else {
    pinnedDirections.value = [trimmed, ...pinnedDirections.value].slice(0, 12)
  }
}

function isPinned(query: string) {
  const key = normalizeDirection(query)
  return pinnedDirections.value.some(item => normalizeDirection(item) === key)
}

function loadBoolean(key: string) {
  if (typeof localStorage === 'undefined') return false
  return localStorage.getItem(key) === '1'
}

function loadPinnedDirections() {
  if (typeof localStorage === 'undefined') return []
  try {
    const raw = JSON.parse(localStorage.getItem('researchsensei.pinnedDirections') || '[]')
    return Array.isArray(raw) ? raw.map(item => String(item || '').trim()).filter(Boolean) : []
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
          研
        </router-link>
        <div class="brand-text">
          <strong>Research Sensei</strong>
          <span>research workspace</span>
        </div>
      </header>

      <div class="sidebar-actions">
        <button type="button" class="new-btn" @click="newDirection">
          <span>+</span>
          <strong>新方向</strong>
        </button>
        <button
          type="button"
          class="icon-btn"
          :aria-label="collapsed ? '展开边栏' : '收起边栏'"
          @click="collapsed = !collapsed"
        >
          {{ collapsed ? '>' : '<' }}
        </button>
      </div>

      <label class="sidebar-search">
        <span>搜索</span>
        <input v-model="sidebarSearch" placeholder="方向、论文、工具" />
      </label>

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

      <section v-if="filteredPinned.length" class="sidebar-section">
        <h2>置顶</h2>
        <button
          v-for="query in filteredPinned"
          :key="query"
          type="button"
          class="direction-item pinned"
          @click="openDirection(query)"
        >
          <span>{{ query }}</span>
          <small>方向</small>
        </button>
      </section>

      <section class="sidebar-section directions-tree">
        <h2>项目</h2>
        <template v-for="run in filteredDirections" :key="run.run_id">
          <button
            type="button"
            class="direction-item"
            @click="openDirection(run.query)"
          >
            <span>{{ run.query }}</span>
            <small>{{ formatCount(run) }}</small>
          </button>
          <button
            type="button"
            class="pin-item"
            :aria-label="isPinned(run.query) ? '取消置顶' : '置顶方向'"
            @click="togglePinned(run.query)"
          >
            {{ isPinned(run.query) ? '已置顶' : '置顶' }}
          </button>
        </template>
        <p v-if="!filteredDirections.length">还没有记录的方向。</p>
      </section>
    </aside>

    <section class="workbench-frame">
      <header class="workbench-topbar">
        <div class="topbar-left">
          <button type="button" class="topbar-btn" aria-label="返回" @click="router.back()">返回</button>
          <button
            type="button"
            class="topbar-btn"
            :aria-label="collapsed ? '展开边栏' : '收起边栏'"
            @click="collapsed = !collapsed"
          >
            边栏
          </button>
          <strong>{{ routeTitle }}</strong>
        </div>
        <div class="topbar-right">
          <button type="button" class="topbar-btn" @click="theme.toggle()">
            {{ theme.isDark ? '日间' : '夜间' }}
          </button>
        </div>
      </header>

      <main class="workbench-content">
        <slot />
      </main>
    </section>
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
  grid-template-columns: 74px minmax(0, 1fr);
}

.workbench-sidebar {
  display: grid;
  grid-template-rows: auto auto auto auto auto minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
  border-right: 1px solid var(--border-subtle);
  padding: 12px;
  background: var(--bg-sidebar);
  overflow: hidden;
}

.sidebar-brand {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 42px;
}

.brand-mark {
  display: flex;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-weight: 900;
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
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 820;
}

.brand-text span {
  color: var(--text-muted);
  font-size: 12px;
}

.sidebar-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  gap: 8px;
}

.new-btn,
.icon-btn,
.topbar-btn,
.workspace-nav a,
.direction-item {
  border: 1px solid transparent;
  border-radius: 8px;
  text-decoration: none;
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease;
}

.new-btn {
  display: flex;
  min-width: 0;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

.new-btn span {
  font-size: 19px;
  line-height: 1;
}

.new-btn strong {
  overflow: hidden;
  font-size: 14px;
  font-weight: 780;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-btn {
  min-height: 38px;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.sidebar-search {
  display: grid;
  gap: 6px;
}

.sidebar-search span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 760;
}

.sidebar-search input {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 0 10px;
  background: var(--bg-card);
  color: var(--text-primary);
  outline: none;
}

.workspace-nav {
  display: grid;
  gap: 4px;
}

.workspace-nav a {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 760;
}

.workspace-nav a b {
  display: flex;
  width: 24px;
  height: 24px;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: var(--bg-secondary);
  color: inherit;
  font-size: 12px;
  font-weight: 900;
}

.workspace-nav a:hover,
.workspace-nav a.active,
.direction-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.workspace-nav a.active {
  border-color: var(--border-subtle);
  background: var(--bg-card);
}

.sidebar-section {
  display: grid;
  min-height: 0;
  gap: 5px;
}

.directions-tree {
  overflow-y: auto;
  padding-right: 2px;
}

.sidebar-section h2 {
  margin: 6px 0 2px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 820;
}

.direction-item,
.pin-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 8px;
  align-items: center;
  padding: 8px 9px;
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
}

.pin-item {
  display: block;
  width: fit-content;
  margin: -4px 0 4px 8px;
  padding: 0;
  background: transparent;
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
}

.direction-item span {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 720;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.direction-item small {
  color: var(--text-muted);
  font-size: 11px;
}

.direction-item.pinned {
  border-color: var(--border-subtle);
  background: var(--bg-card);
}

.sidebar-section p {
  margin: 6px 4px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.workbench-frame {
  display: grid;
  min-width: 0;
  grid-template-rows: 50px minmax(0, 1fr);
}

.workbench-topbar {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 14px;
  background: color-mix(in srgb, var(--bg-card) 88%, transparent);
  backdrop-filter: blur(16px);
}

.topbar-left,
.topbar-right {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.topbar-left strong {
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 820;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topbar-btn {
  min-height: 32px;
  padding: 0 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 720;
}

.topbar-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.workbench-content {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background: var(--bg-primary);
}

.codex-shell.collapsed .workbench-sidebar {
  padding-inline: 10px;
}

.codex-shell.collapsed .brand-text,
.codex-shell.collapsed .new-btn strong,
.codex-shell.collapsed .sidebar-search,
.codex-shell.collapsed .workspace-nav a span,
.codex-shell.collapsed .sidebar-section {
  display: none;
}

.codex-shell.collapsed .workspace-nav a {
  grid-template-columns: 1fr;
  justify-items: center;
  padding-inline: 0;
}

.codex-shell.collapsed .sidebar-actions {
  grid-template-columns: 1fr;
}

.codex-shell.collapsed .new-btn,
.codex-shell.collapsed .icon-btn {
  justify-content: center;
  padding: 0;
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
  .codex-shell.collapsed .new-btn strong,
  .codex-shell.collapsed .sidebar-search,
  .codex-shell.collapsed .workspace-nav a span,
  .codex-shell.collapsed .sidebar-section {
    display: initial;
  }
}
</style>

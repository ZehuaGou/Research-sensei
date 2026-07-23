<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '../../stores/theme'
import { researchApi } from '../../api/client'
import type { SearchRun } from '../../types/api'

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
    const data = await researchApi.listSearchRuns(60)
    searchRuns.value = data.search_runs
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

<style scoped src="./WorkbenchShell.css"></style>

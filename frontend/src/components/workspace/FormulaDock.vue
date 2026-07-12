<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { FormulaEntry } from '../../types/workspace'

const props = defineProps<{
  entries: FormulaEntry[]
  activeId: string
  collapsed: boolean
  dragging: boolean
  style: Record<string, string>
}>()

const emit = defineEmits<{
  register: [element: HTMLElement | null]
  dragStart: [event: PointerEvent]
  keyMove: [event: KeyboardEvent]
  toggle: []
  resetPosition: []
  focus: [entry: FormulaEntry]
  scroll: [id: string]
  collapseAll: [collapsed: boolean]
}>()

const root = ref<HTMLElement | null>(null)
const activeEntry = computed(() => props.entries.find(entry => entry.id === props.activeId) || props.entries[0] || null)

onMounted(() => emit('register', root.value))
onBeforeUnmount(() => emit('register', null))
</script>

<template>
  <aside
    ref="root"
    class="formula-dock surface"
    :class="{ collapsed, dragging }"
    :style="style"
    aria-label="当前公式与目录"
    data-testid="formula-dock"
    @pointerdown="emit('dragStart', $event)"
  >
    <div
      class="formula-dock-handle"
      data-testid="formula-dock-handle"
      role="toolbar"
      aria-label="移动公式停靠栏"
      tabindex="0"
      @keydown="emit('keyMove', $event)"
    >
      <button type="button" class="rail-toggle" :aria-expanded="!collapsed" @click="emit('toggle')">
        {{ collapsed ? `公式 ${activeEntry?.index || '...'}` : '收起' }}
      </button>
      <span v-if="!collapsed">拖动或用方向键移动</span>
      <button v-if="!collapsed" type="button" class="dock-reset" @click="emit('resetPosition')">复位</button>
    </div>

    <template v-if="!collapsed">
      <section v-if="activeEntry" class="active-formula-card">
        <span>当前公式</span>
        <strong>{{ activeEntry.title }}</strong>
        <small>公式 {{ activeEntry.index }}</small>
        <div class="active-formula-actions">
          <button type="button" @click="emit('focus', activeEntry)">点开看</button>
          <button type="button" @click="emit('scroll', activeEntry.id)">回到正文</button>
        </div>
      </section>

      <nav class="formula-index" data-testid="formula-index" aria-label="公式目录">
        <header>
          <div>
            <strong>公式目录</strong>
            <small>{{ entries.length }} 张卡片</small>
          </div>
          <div class="formula-index-actions">
            <button type="button" @click="emit('collapseAll', true)">折叠</button>
            <button type="button" @click="emit('collapseAll', false)">展开</button>
          </div>
        </header>
        <div class="formula-index-list">
          <button
            v-for="entry in entries"
            :key="entry.id"
            type="button"
            :class="{ active: activeId === entry.id }"
            :title="entry.title"
            @click="emit('scroll', entry.id)"
          >
            <b>{{ entry.index }}</b>
            <span>{{ entry.title }}</span>
          </button>
        </div>
      </nav>
    </template>
  </aside>
</template>

<style scoped>
.formula-dock {
  position: fixed;
  z-index: 60;
  display: grid;
  width: 300px;
  max-height: min(72vh, calc(100dvh - 82px));
  align-content: start;
  min-width: 0;
  overflow-y: auto;
  padding: 0;
  background: var(--bg-card);
  box-shadow: var(--shadow-lg);
  overscroll-behavior: contain;
  touch-action: none;
  user-select: none;
}

.formula-dock.collapsed {
  width: 96px;
  height: 44px;
  align-content: stretch;
  overflow: hidden;
  border-radius: 999px;
}

.formula-dock.dragging {
  cursor: grabbing;
}

.formula-dock-handle {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 7px;
  background: color-mix(in srgb, var(--bg-card) 92%, transparent);
  backdrop-filter: blur(12px);
  cursor: grab;
}

.formula-dock-handle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.formula-dock.collapsed .formula-dock-handle {
  min-height: 44px;
  border-bottom: 0;
  padding: 0;
}

.formula-dock-handle span {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 650;
}

.rail-toggle,
.dock-reset,
.formula-index-actions button,
.active-formula-actions button {
  min-height: 28px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 3px 8px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 650;
}

.formula-dock.collapsed .rail-toggle {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 999px;
  color: var(--text-primary);
}

.active-formula-card {
  display: grid;
  gap: 5px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 13px;
}

.active-formula-card > span,
.active-formula-card > small {
  color: var(--text-muted);
  font-size: 11px;
}

.active-formula-card strong {
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.4;
}

.active-formula-actions,
.formula-index-actions {
  display: flex;
  gap: 6px;
}

.formula-index {
  display: grid;
  gap: 10px;
  padding: 12px;
}

.formula-index header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.formula-index header strong,
.formula-index header small {
  display: block;
}

.formula-index header strong {
  color: var(--text-primary);
  font-size: 14px;
}

.formula-index header small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
}

.formula-index-list {
  display: grid;
  gap: 5px;
}

.formula-index-list > button {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 38px;
  border-radius: 8px;
  padding: 5px 7px;
  color: var(--text-secondary);
  text-align: left;
}

.formula-index-list > button.active {
  background: var(--accent-light);
  color: var(--accent);
}

.formula-index-list b {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  border-radius: 7px;
  background: var(--bg-secondary);
  font-size: 11px;
}

.formula-index-list span {
  overflow: hidden;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

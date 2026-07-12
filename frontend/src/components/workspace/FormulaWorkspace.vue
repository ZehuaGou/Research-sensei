<script setup lang="ts">
import FormulaCardComponent from '../cards/FormulaCard.vue'
import type { FormulaEntry } from '../../types/workspace'

defineProps<{
  entries: FormulaEntry[]
  collapsed: Record<string, boolean>
  activeId: string
}>()

const emit = defineEmits<{
  reset: []
  focus: [entry: FormulaEntry]
  toggle: [id: string]
}>()
</script>

<template>
  <div class="formula-workspace">
    <section class="formula-reader">
      <section class="formula-board-toolbar surface" aria-label="公式阅读器">
        <div>
          <strong>公式阅读器</strong>
          <span>按正文顺序阅读；当前公式会在停靠栏中同步高亮。</span>
        </div>
        <button type="button" class="secondary-btn" @click="emit('reset')">重置卡片布局</button>
      </section>

      <div class="formula-list" data-testid="formula-board">
        <article
          v-for="entry in entries"
          :id="entry.id"
          :key="entry.id"
          class="formula-board-card"
          :class="{ collapsed: collapsed[entry.id], active: activeId === entry.id }"
          data-testid="formula-board-card"
        >
          <header class="formula-card-bar">
            <div class="formula-card-number">{{ entry.index }}</div>
            <div>
              <span>公式 {{ entry.index }}</span>
              <strong>{{ entry.title }}</strong>
            </div>
            <div class="formula-card-actions">
              <button type="button" @click="emit('focus', entry)">单独查看</button>
              <button type="button" :aria-expanded="!collapsed[entry.id]" @click="emit('toggle', entry.id)">
                {{ collapsed[entry.id] ? '展开' : '折叠' }}
              </button>
            </div>
          </header>
          <FormulaCardComponent v-if="!collapsed[entry.id]" :card="entry.card" />
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.formula-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1040px);
  align-items: start;
  justify-content: center;
}

.formula-reader,
.formula-list {
  display: grid;
  min-width: 0;
  gap: 14px;
}

.formula-list {
  gap: 18px;
}

.formula-board-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
}

.formula-board-toolbar strong,
.formula-board-toolbar span {
  display: block;
}

.formula-board-toolbar strong {
  color: var(--text-primary);
  font-size: 15px;
}

.formula-board-toolbar span {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

.formula-board-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-card);
  scroll-margin-top: 16px;
}

.formula-board-card.active {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--border-subtle));
}

.formula-card-bar {
  position: sticky;
  top: -34px;
  z-index: 4;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 62px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 10px 14px;
  background: color-mix(in srgb, var(--bg-card) 94%, transparent);
  backdrop-filter: blur(12px);
}

.formula-board-card.collapsed .formula-card-bar {
  border-bottom: 0;
}

.formula-card-number {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 9px;
  background: var(--bg-secondary);
  color: var(--accent);
  font-size: 13px;
  font-weight: 750;
}

.formula-card-bar span,
.formula-card-bar strong {
  display: block;
}

.formula-card-bar span {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 650;
}

.formula-card-bar strong {
  margin-top: 2px;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.formula-card-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.formula-card-actions button {
  min-height: 30px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 4px 9px;
  color: var(--text-secondary);
  font-size: 12px;
}

@media (max-width: 720px) {
  .formula-board-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .formula-card-bar {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .formula-card-actions {
    grid-column: 1 / -1;
  }
}
</style>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useSelectionStore } from '../../stores/selection'
import { useLearningStore } from '../../stores/learning'

const selectionStore = useSelectionStore()
const learningStore = useLearningStore()

function handleMouseUp(e: MouseEvent) {
  const target = e.target instanceof HTMLElement ? e.target : null
  if (target?.closest('input, textarea, button')) return
  const selection = window.getSelection()
  const text = selection?.toString().trim()
  if (text && text.length > 2) {
    const range = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null
    const rect = range?.getBoundingClientRect()
    const position = positionToolbar(rect, e.clientX, e.clientY)
    selectionStore.showSelection(text, position.x, position.y)
  } else {
    selectionStore.hide()
  }
}

function handleMouseDown(e: MouseEvent) {
  const target = e.target instanceof HTMLElement ? e.target : null
  if (target?.closest('[data-testid="selection-toolbar"]')) return
  selectionStore.hide()
}

function positionToolbar(rect: DOMRect | undefined, fallbackX: number, fallbackY: number) {
  const toolbarWidth = 292
  const toolbarHeight = 52
  const margin = 14
  const width = window.innerWidth
  const height = window.innerHeight

  if (width < 720) {
    return {
      x: Math.max(margin, Math.round((width - toolbarWidth) / 2)),
      y: Math.max(margin, height - toolbarHeight - 28),
    }
  }

  const baseLeft = rect && rect.width > 0 ? rect.right + 16 : fallbackX + 16
  const baseTop = rect && rect.height > 0 ? rect.bottom + 14 : fallbackY + 14
  const left = baseLeft + toolbarWidth > width - margin
    ? Math.max(margin, (rect?.left || fallbackX) - toolbarWidth - 12)
    : baseLeft
  const top = baseTop + toolbarHeight > height - margin
    ? Math.max(margin, (rect?.top || fallbackY) - toolbarHeight - 12)
    : baseTop

  return {
    x: Math.round(Math.min(Math.max(left, margin), width - toolbarWidth - margin)),
    y: Math.round(Math.min(Math.max(top, margin), height - toolbarHeight - margin)),
  }
}

function askAbout(intent: 'explain' | 'simplify' | 'example') {
  learningStore.setSelectedText(selectionStore.selectedText, intent)
  learningStore.isAskPanelOpen = true
  selectionStore.hide()
}

onMounted(() => {
  document.addEventListener('mouseup', handleMouseUp)
  document.addEventListener('mousedown', handleMouseDown)
})

onUnmounted(() => {
  document.removeEventListener('mouseup', handleMouseUp)
  document.removeEventListener('mousedown', handleMouseDown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="selectionStore.isVisible && selectionStore.selectionPosition"
        class="selection-toolbar"
        data-testid="selection-toolbar"
        :style="{
          left: selectionStore.selectionPosition.x + 'px',
          top: selectionStore.selectionPosition.y + 'px',
        }"
        @mousedown.stop
      >
        <button class="toolbar-btn primary" @click="askAbout('explain')">追问</button>
        <button class="toolbar-btn" @click="askAbout('simplify')">讲简单点</button>
        <button class="toolbar-btn" @click="askAbout('example')">举例</button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.selection-toolbar {
  position: fixed;
  z-index: 100;
  display: flex;
  gap: 6px;
  max-width: calc(100vw - 28px);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 6px;
  background: var(--bg-elevated);
  box-shadow: var(--shadow-lg);
}

.toolbar-btn {
  min-height: 36px;
  border-radius: 10px;
  padding: 7px 12px;
  font-size: 13px;
  font-weight: 700;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  white-space: nowrap;
}

.toolbar-btn.primary {
  background: var(--accent);
  color: white;
}

@media (max-width: 719px) {
  .selection-toolbar {
    left: 14px !important;
    right: 14px;
    justify-content: center;
  }
}
</style>

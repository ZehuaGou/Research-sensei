<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useSelectionStore } from '../../stores/selection'
import { useLearningStore } from '../../stores/learning'

const selectionStore = useSelectionStore()
const learningStore = useLearningStore()

function handleMouseUp(e: MouseEvent) {
  const selection = window.getSelection()
  const text = selection?.toString().trim()
  if (text && text.length > 2) {
    selectionStore.showSelection(text, e.clientX, e.clientY)
  } else {
    selectionStore.hide()
  }
}

function handleMouseDown() {
  selectionStore.hide()
}

function askAbout() {
  learningStore.setSelectedText(selectionStore.selectedText)
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
      <div v-if="selectionStore.isVisible && selectionStore.selectionPosition"
        class="fixed z-[100] flex gap-1 p-1.5 rounded-xl"
        :style="{
          left: selectionStore.selectionPosition.x + 'px',
          top: (selectionStore.selectionPosition.y - 48) + 'px',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-lg)',
        }"
        @mousedown.stop
      >
        <button @click="askAbout"
          class="px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all hover:scale-105"
          style="background: var(--accent); color: white;">
          追问
        </button>
        <button @click="learningStore.setSelectedText('请用更简单的方式解释：' + selectionStore.selectedText); selectionStore.hide()"
          class="px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all hover:scale-105"
          style="background: rgba(16,185,129,0.1); color: #10b981;">
          简单解释
        </button>
        <button @click="learningStore.setSelectedText('举个数字例子：' + selectionStore.selectedText); selectionStore.hide()"
          class="px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all hover:scale-105"
          style="background: rgba(245,158,11,0.1); color: #f59e0b;">
          举例子
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

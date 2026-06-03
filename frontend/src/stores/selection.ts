import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSelectionStore = defineStore('selection', () => {
  const selectedText = ref('')
  const selectionPosition = ref<{ x: number; y: number } | null>(null)
  const isVisible = ref(false)

  function showSelection(text: string, x: number, y: number) {
    selectedText.value = text
    selectionPosition.value = { x, y }
    isVisible.value = true
  }

  function hide() {
    isVisible.value = false
    selectedText.value = ''
    selectionPosition.value = null
  }

  return { selectedText, selectionPosition, isVisible, showSelection, hide }
})

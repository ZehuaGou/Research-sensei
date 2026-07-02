import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

function normalizeSelectedText(text: string) {
  return text
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:，。；：、）\]\}])/g, '$1')
    .replace(/([（\[\{])\s+/g, '$1')
    .trim()
}

export const useLearningStore = defineStore('learning', () => {
  const currentJobId = ref('')
  const chatHistory = ref<ChatMessage[]>([])
  const selectedText = ref('')
  const selectedIntent = ref<'explain' | 'simplify' | 'example'>('explain')
  const isAskPanelOpen = ref(false)

  function addMessage(msg: ChatMessage) {
    chatHistory.value.push(msg)
  }

  function clearChat() {
    chatHistory.value = []
  }

  function setSelectedText(text: string, intent: 'explain' | 'simplify' | 'example' = 'explain') {
    selectedText.value = normalizeSelectedText(text)
    selectedIntent.value = intent
  }

  return {
    currentJobId,
    chatHistory,
    selectedText,
    selectedIntent,
    isAskPanelOpen,
    addMessage,
    clearChat,
    setSelectedText,
  }
})

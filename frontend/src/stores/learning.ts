import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export const useLearningStore = defineStore('learning', () => {
  const currentJobId = ref('')
  const chatHistory = ref<ChatMessage[]>([])
  const selectedText = ref('')
  const isAskPanelOpen = ref(true)

  function addMessage(msg: ChatMessage) {
    chatHistory.value.push(msg)
  }

  function clearChat() {
    chatHistory.value = []
  }

  function setSelectedText(text: string) {
    selectedText.value = text
  }

  return { currentJobId, chatHistory, selectedText, isAskPanelOpen, addMessage, clearChat, setSelectedText }
})

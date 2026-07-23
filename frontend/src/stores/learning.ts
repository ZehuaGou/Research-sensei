import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { TutorContextTrace } from '../types/api'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  evidenceRefs?: string[]
  uncertainty?: string
  followUpSuggestions?: string[]
  contextTrace?: TutorContextTrace
  status?: string
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
  const chatByJob = ref<Record<string, ChatMessage[]>>({})
  const selectedText = ref('')
  const selectedIntent = ref<'explain' | 'simplify' | 'example'>('explain')
  const isPaperTutorPanelOpen = ref(false)

  function addMessage(msg: ChatMessage) {
    chatHistory.value.push(msg)
    if (currentJobId.value) chatByJob.value[currentJobId.value] = [...chatHistory.value]
  }

  function clearChat() {
    chatHistory.value = []
    if (currentJobId.value) chatByJob.value[currentJobId.value] = []
  }

  function replaceChat(messages: ChatMessage[]) {
    chatHistory.value = [...messages]
    if (currentJobId.value) chatByJob.value[currentJobId.value] = [...messages]
  }

  function replaceMessage(index: number, msg: ChatMessage) {
    if (index < 0 || index >= chatHistory.value.length) return
    chatHistory.value.splice(index, 1, msg)
    if (currentJobId.value) chatByJob.value[currentJobId.value] = [...chatHistory.value]
  }

  function setCurrentJob(jobId: string) {
    const nextJobId = jobId.trim()
    if (nextJobId === currentJobId.value) return
    if (currentJobId.value) chatByJob.value[currentJobId.value] = [...chatHistory.value]
    currentJobId.value = nextJobId
    chatHistory.value = [...(chatByJob.value[nextJobId] || [])]
    selectedText.value = ''
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
    isPaperTutorPanelOpen,
    addMessage,
    clearChat,
    replaceChat,
    replaceMessage,
    setCurrentJob,
    setSelectedText,
  }
})

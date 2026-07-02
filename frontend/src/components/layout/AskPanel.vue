<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useLearningStore } from '../../stores/learning'

const store = useLearningStore()
const input = ref('')
const chatContainer = ref<HTMLElement>()
const isLoading = ref(false)
const memoryCount = ref(0)

function compactInlineText(value: string) {
  return value
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:，。；：、）\]\}])/g, '$1')
    .replace(/([（\[\{])\s+/g, '$1')
    .trim()
}

function clipText(value: string, maxLength: number) {
  const compact = compactInlineText(value)
  return compact.length > maxLength ? `${compact.slice(0, maxLength)}...` : compact
}

function selectedPreviewText() {
  return clipText(store.selectedText, 220)
}

function selectedPayloadText() {
  return clipText(store.selectedText, 900)
}

function normalizeMessageText(value: string) {
  return value
    .replace(/\n{3,}/g, '\n\n')
    .replace(/([A-Za-z])\n(?=[A-Za-z])/g, '$1 ')
    .trim()
}

function extractApiError(data: unknown) {
  if (!data || typeof data !== 'object') return 'M4 请求失败，请稍后再试。'
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string' && message.trim()) return message
  }
  return 'M4 请求失败，请稍后再试。'
}

async function loadMemory() {
  if (!store.currentJobId) return
  try {
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/memory`)
    const data = await res.json()
    memoryCount.value = Array.isArray(data.records) ? data.records.length : 0
  } catch {
    memoryCount.value = 0
  }
}

async function send() {
  const question = compactInlineText(input.value)
  if (!question || isLoading.value || !store.currentJobId) return
  const selectedText = selectedPayloadText()
  store.addMessage({ role: 'user', content: question, timestamp: Date.now() })
  input.value = ''
  isLoading.value = true
  await scrollToBottom()

  try {
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        selected_text: selectedText,
        context_scope: selectedText ? 'selection' : 'paper',
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(extractApiError(data))
    }
    store.addMessage({
      role: 'assistant',
      content: normalizeMessageText(data.answer || 'M4 暂时无法回答这个问题。'),
      timestamp: Date.now(),
    })
    await loadMemory()
  } catch (error) {
    const message = error instanceof Error ? error.message : 'M4 请求失败，请稍后再试。'
    store.addMessage({ role: 'assistant', content: message, timestamp: Date.now() })
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

async function requestAdvisorQuestion() {
  if (!store.currentJobId || isLoading.value) return
  isLoading.value = true
  try {
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/advisor/question`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ advisor_mode: 'group_meeting' }),
    })
    const data = await res.json()
    const points = Array.isArray(data.expected_answer_points) && data.expected_answer_points.length
      ? `\n\n参考回答要点：${data.expected_answer_points.join('；')}`
      : ''
    store.addMessage({
      role: 'assistant',
      content: normalizeMessageText(`组会追问：${data.question || '暂时没有生成问题。'}${points}`),
      timestamp: Date.now(),
    })
    await loadMemory()
  } catch {
    store.addMessage({ role: 'assistant', content: '组会追问生成失败。', timestamp: Date.now() })
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

async function clearMemory() {
  if (!store.currentJobId) return
  await fetch(`/api/v1/jobs/${store.currentJobId}/memory`, { method: 'DELETE' }).catch(() => null)
  store.clearChat()
  memoryCount.value = 0
}

function quick(text: string) {
  input.value = text
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void send()
  }
}

async function scrollToBottom() {
  await nextTick()
  chatContainer.value?.scrollTo?.({ top: chatContainer.value.scrollHeight, behavior: 'smooth' })
}

watch(() => store.selectedText, (text) => {
  if (text) {
    const promptMap = {
      explain: '请解释这段话',
      simplify: '请用更简单的中文讲这段话',
      example: '请给这段话配一个具体例子',
    }
    input.value = `${promptMap[store.selectedIntent]}：${clipText(text, 260)}`
    store.isAskPanelOpen = true
  }
})

watch(() => store.currentJobId, () => {
  void loadMemory()
}, { immediate: true })
</script>

<template>
  <section class="ask-panel" data-testid="ask-panel">
    <header>
      <div>
        <h2>M4 论文助教</h2>
        <p>论文问题基于当前证据回答</p>
      </div>
      <button type="button" class="ghost-btn !min-h-9 !px-3" data-testid="ask-panel-toggle" @click="store.isAskPanelOpen = false">收起</button>
    </header>

    <div v-if="store.selectedText" class="selected" data-testid="selected-context">
      <span>已选中文本</span>
      <p>{{ selectedPreviewText() }}</p>
    </div>

    <div ref="chatContainer" class="messages">
      <div v-if="!store.chatHistory.length && !isLoading" class="empty">
        <h3>从一个问题开始</h3>
        <p>可以选中论文中的一句话，也可以直接问“这篇论文的核心贡献是什么？”</p>
      </div>

      <article
        v-for="(msg, index) in store.chatHistory"
        :key="index"
        class="message"
        :class="msg.role"
        data-testid="chat-message"
      >
        <div class="avatar">{{ msg.role === 'user' ? '你' : 'M4' }}</div>
        <div class="bubble" :class="{ compact: msg.role === 'user' }">{{ msg.content }}</div>
      </article>

      <div v-if="isLoading" class="message assistant">
        <div class="avatar">M4</div>
        <div class="bubble loading">正在读证据并组织回答...</div>
      </div>
    </div>

    <div class="quick-row">
      <button type="button" @click="quick('请用中文按“问题-核心机制-为什么有效-对应证据”讲清楚这篇论文的核心方法，结合正文细节，不要只给一句话。')">讲方法</button>
      <button type="button" @click="quick('这条结论对应哪条证据？')">找证据</button>
      <button type="button" data-testid="advisor-button" @click="requestAdvisorQuestion">组会追问</button>
      <button type="button" @click="clearMemory">清空</button>
    </div>

    <form class="composer" @submit.prevent="send">
      <textarea
        v-model="input"
        data-testid="ask-input"
        rows="2"
        placeholder="问 M4，例如：这篇论文到底解决了什么问题？"
        @keydown="handleKeydown"
      />
      <button type="submit" data-testid="ask-submit" class="primary-btn" :disabled="!input.trim() || isLoading">发送</button>
    </form>
  </section>
</template>

<style scoped>
.ask-panel {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  background: var(--bg-card);
}

header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 18px;
}

h2 {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 800;
}

header p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.selected {
  margin: 14px 18px 0;
  border-radius: 12px;
  padding: 12px;
  background: var(--accent-light);
}

.selected span {
  color: var(--accent);
  font-size: 13px;
  font-weight: 800;
}

.selected p {
  margin-top: 4px;
  max-height: 118px;
  overflow-y: auto;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: break-word;
  white-space: normal;
  word-break: normal;
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px 18px;
}

.empty {
  margin: 70px auto 0;
  max-width: 320px;
  text-align: center;
}

.empty h3 {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 800;
}

.empty p {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 15px;
}

.message {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.message.user {
  grid-template-columns: minmax(0, 1fr) 34px;
}

.message.user .avatar {
  grid-column: 2;
  grid-row: 1;
}

.message.user .bubble {
  grid-column: 1;
  grid-row: 1;
  justify-self: end;
  background: var(--accent);
  color: #fff;
}

.avatar {
  display: flex;
  height: 34px;
  width: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 800;
}

.bubble {
  max-width: 100%;
  min-width: 0;
  border-radius: 14px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.75;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  word-break: normal;
}

.message.user .bubble.compact {
  max-width: min(100%, 320px);
  white-space: normal;
}

.loading {
  color: var(--text-muted);
}

.quick-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--border-subtle);
  padding: 12px 18px;
}

.quick-row button {
  border-radius: 999px;
  padding: 6px 11px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  padding: 0 18px 18px;
}

textarea {
  width: 100%;
  resize: none;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.6;
}
</style>

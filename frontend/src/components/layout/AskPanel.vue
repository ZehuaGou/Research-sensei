<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useLearningStore } from '../../stores/learning'

const store = useLearningStore()
const input = ref('')
const chatContainer = ref<HTMLElement>()
const isLoading = ref(false)
const isAdvisorEvaluating = ref(false)
const memoryCount = ref(0)
const advisorAnswer = ref('')
const advisorSession = ref<AdvisorSession | null>(null)

type AdvisorSession = {
  question: string
  userQuestion: string
  expectedAnswerPoints: string[]
  answerFormat: string[]
  evidenceRefs: string[]
  feedback: string
  score: number | null
  missingPoints: string[]
  coveredPoints: string[]
  nextQuestion: string
}

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

function stringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
}

function advisorPromptText(session: AdvisorSession) {
  const focus = session.userQuestion ? `围绕你的问题：${session.userQuestion}\n\n` : ''
  const points = session.expectedAnswerPoints.length
    ? `\n\n参考回答要点：${session.expectedAnswerPoints.join('；')}`
    : ''
  return normalizeMessageText(`${focus}组会追问：${session.question || '暂时没有生成问题。'}${points}`)
}

function advisorEvaluationText(session: AdvisorSession) {
  const score = session.score === null ? '' : `评分：${Math.round(session.score * 100)}%。\n`
  const missing = session.missingPoints.length ? `\n\n还要补：${session.missingPoints.join('；')}` : ''
  const next = session.nextQuestion ? `\n\n下一问：${session.nextQuestion}` : ''
  return normalizeMessageText(`${score}${session.feedback || 'M4 已完成评价。'}${missing}${next}`)
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
  const focusQuestion = compactInlineText(input.value)
  const selectedText = selectedPayloadText()
  if (focusQuestion) {
    store.addMessage({ role: 'user', content: focusQuestion, timestamp: Date.now() })
    input.value = ''
    await scrollToBottom()
  }
  isLoading.value = true
  try {
    if (focusQuestion) {
      const answerRes = await fetch(`/api/v1/jobs/${store.currentJobId}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: focusQuestion,
          selected_text: selectedText,
          context_scope: selectedText ? 'selection' : 'paper',
        }),
      })
      const answerData = await answerRes.json().catch(() => ({}))
      if (!answerRes.ok) {
        throw new Error(extractApiError(answerData))
      }
      const answerEvidenceRefs = stringList(answerData.evidence_refs)
      store.addMessage({
        role: 'assistant',
        content: normalizeMessageText(answerData.answer || 'M4 暂时无法回答这个问题。'),
        timestamp: Date.now(),
      })
      if (answerData.status === 'DEGRADED' && answerEvidenceRefs.length === 0) {
        await loadMemory()
        return
      }
    }
    const advisorPayload: Record<string, string> = { advisor_mode: 'group_meeting' }
    if (focusQuestion) advisorPayload.user_question = focusQuestion
    if (selectedText) advisorPayload.selected_text = selectedText
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/advisor/question`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(advisorPayload),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(extractApiError(data))
    }
    advisorSession.value = {
      question: typeof data.question === 'string' ? data.question : '',
      userQuestion: typeof data.user_question === 'string' && data.user_question ? data.user_question : focusQuestion,
      expectedAnswerPoints: stringList(data.expected_answer_points),
      answerFormat: stringList(data.answer_format),
      evidenceRefs: stringList(data.evidence_refs),
      feedback: '',
      score: null,
      missingPoints: [],
      coveredPoints: [],
      nextQuestion: '',
    }
    advisorAnswer.value = ''
    store.addMessage({
      role: 'assistant',
      content: advisorPromptText(advisorSession.value),
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

async function submitAdvisorAnswer() {
  const session = advisorSession.value
  const userAnswer = compactInlineText(advisorAnswer.value)
  if (!store.currentJobId || !session || !userAnswer || isAdvisorEvaluating.value) return
  isAdvisorEvaluating.value = true
  store.addMessage({ role: 'user', content: userAnswer, timestamp: Date.now() })
  try {
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/advisor/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: session.question,
        user_question: session.userQuestion,
        user_answer: userAnswer,
        expected_answer_points: session.expectedAnswerPoints,
        evidence_refs: session.evidenceRefs,
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(extractApiError(data))
    }
    advisorSession.value = {
      ...session,
      feedback: typeof data.feedback === 'string' ? data.feedback : '',
      score: typeof data.score === 'number' ? data.score : null,
      missingPoints: stringList(data.missing_points),
      coveredPoints: stringList(data.covered_points),
      nextQuestion: typeof data.next_question === 'string' ? data.next_question : '',
    }
    advisorAnswer.value = ''
    store.addMessage({
      role: 'assistant',
      content: advisorEvaluationText(advisorSession.value),
      timestamp: Date.now(),
    })
    await loadMemory()
  } catch (error) {
    const message = error instanceof Error ? error.message : '组会反馈生成失败。'
    store.addMessage({ role: 'assistant', content: message, timestamp: Date.now() })
  } finally {
    isAdvisorEvaluating.value = false
    await scrollToBottom()
  }
}

async function clearMemory() {
  if (!store.currentJobId) return
  await fetch(`/api/v1/jobs/${store.currentJobId}/memory`, { method: 'DELETE' }).catch(() => null)
  store.clearChat()
  memoryCount.value = 0
  advisorSession.value = null
  advisorAnswer.value = ''
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

    <section v-if="advisorSession" class="advisor-card" data-testid="advisor-card">
      <div class="advisor-head">
        <span>组会追问</span>
        <strong v-if="advisorSession.score !== null">{{ Math.round(advisorSession.score * 100) }}%</strong>
      </div>
      <p class="advisor-question">{{ advisorSession.question }}</p>
      <ul v-if="advisorSession.answerFormat.length || advisorSession.expectedAnswerPoints.length" class="advisor-points">
        <li v-for="point in advisorSession.answerFormat.length ? advisorSession.answerFormat : advisorSession.expectedAnswerPoints" :key="point">{{ point }}</li>
      </ul>
      <form class="advisor-composer" @submit.prevent="submitAdvisorAnswer">
        <textarea
          v-model="advisorAnswer"
          data-testid="advisor-answer"
          rows="2"
          placeholder="写下你的 20-30 秒回答，M4 会按问题、机制、证据给反馈"
          :disabled="isAdvisorEvaluating"
        />
        <button
          type="submit"
          data-testid="advisor-submit"
          class="primary-btn"
          :disabled="!advisorAnswer.trim() || isAdvisorEvaluating"
        >
          {{ isAdvisorEvaluating ? '评价中' : '提交' }}
        </button>
      </form>
      <div v-if="advisorSession.feedback" class="advisor-feedback" data-testid="advisor-feedback">
        <p>{{ advisorSession.feedback }}</p>
        <p v-if="advisorSession.missingPoints.length">还要补：{{ advisorSession.missingPoints.join('；') }}</p>
        <p v-if="advisorSession.nextQuestion">下一问：{{ advisorSession.nextQuestion }}</p>
      </div>
    </section>

    <div class="quick-row">
      <button type="button" @click="quick('请用中文按“问题-核心机制-为什么有效-对应证据”讲清楚这篇论文的核心方法，结合正文细节，不要只给一句话。')">讲方法</button>
      <button type="button" @click="quick('这条结论对应哪条证据？')">找证据</button>
      <button type="button" data-testid="advisor-button" @click="requestAdvisorQuestion">按问题追问</button>
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

.advisor-card {
  margin: 0 18px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px;
  background: var(--bg-secondary);
}

.advisor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 800;
}

.advisor-head strong {
  color: var(--text-primary);
  font-size: 13px;
}

.advisor-question {
  margin-top: 8px;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.65;
}

.advisor-points {
  display: grid;
  gap: 4px;
  margin-top: 8px;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.55;
}

.advisor-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  margin-top: 10px;
  padding: 0;
}

.advisor-composer textarea {
  min-height: 54px;
  border-radius: 8px;
  background: var(--bg-card);
  font-size: 14px;
}

.advisor-feedback {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  border-left: 3px solid var(--accent);
  padding-left: 10px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.55;
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

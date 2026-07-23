<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useLearningStore, type ChatMessage } from '../../stores/learning'
import { apiErrorMessage, workspaceApi } from '../../api/client'
import type { AdvisorEvaluateRequest, AdvisorQuestionRequest, AskRequest, AskResponse } from '../../types/api'
import {
  answerBlocks,
  clipText,
  compactInlineText,
  contextSizeLabel,
  highlightSegments,
  normalizeMessageText,
} from '../../utils/m4AnswerFormatting'

const store = useLearningStore()
const props = defineProps<{ paperTitle?: string }>()
const input = ref('')
const chatContainer = ref<HTMLElement>()
const isLoading = ref(false)
const isAdvisorEvaluating = ref(false)
const memoryCount = ref(0)
const advisorAnswer = ref('')
const advisorSession = ref<AdvisorSession | null>(null)
const mode = ref<AskMode>('paper')
const fontStorageKey = 'researchsensei.m4.fontSize'
const fontSize = ref(initialM4FontSize())

type AskMode = 'paper' | 'evidence' | 'advisor'

const modeOptions: Array<{ key: AskMode; label: string; hint: string }> = [
  { key: 'paper', label: '论文问答', hint: '结合全文，自然讲解' },
  { key: 'evidence', label: '原文证据', hint: '只定位出处，不调用模型' },
  { key: 'advisor', label: '组会演练', hint: '追问、作答、反馈' },
]

const modePrompts: Record<AskMode, string> = {
  paper: '请像一位耐心的论文助教一样，结合整篇论文自然地讲清楚核心方法。根据内容决定详略，不要只给一句概括。',
  evidence: '这条结论对应哪条证据？',
  advisor: '',
}

const inputPlaceholder = computed(() => {
  if (mode.value === 'evidence') return '问证据，例如：这个结论靠哪类实验或正文段落支撑？'
  if (mode.value === 'advisor') return '写下你想被追问的点；留空则按整篇论文生成组会问题'
  return '问 M4，例如：这篇论文到底解决了什么问题？'
})

const submitLabel = computed(() => {
  if (mode.value === 'evidence') return '找证据'
  if (mode.value === 'advisor') return '生成追问'
  return '发送'
})

const askPanelStyle = computed<Record<string, string>>(() => ({
  '--m4-font-size': `${fontSize.value}px`,
}))

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

function initialM4FontSize() {
  if (typeof localStorage === 'undefined') return 14
  const saved = Number(localStorage.getItem(fontStorageKey))
  return Number.isFinite(saved) ? Math.min(Math.max(saved, 13), 18) : 14
}

function setFontSize(nextSize: number) {
  fontSize.value = Math.min(Math.max(nextSize, 13), 18)
}

function selectedPreviewText() {
  return clipText(store.selectedText, 220)
}

function selectedPayloadText() {
  return clipText(store.selectedText, 900)
}

function stringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
}

function conversationHistoryPayload(limit = 10) {
  return store.chatHistory
    .slice(-limit)
    .map(message => ({
      role: message.role,
      content: clipText(message.content, 1200),
    }))
    .filter(message => message.content.length > 0)
}

function assistantMessage(data: AskResponse) {
  return {
    role: 'assistant' as const,
    content: normalizeMessageText(data.answer || 'M4 暂时无法回答这个问题。'),
    timestamp: Date.now(),
    evidenceRefs: stringList(data.evidence_refs),
    uncertainty: typeof data.uncertainty === 'string' ? data.uncertainty : '',
    followUpSuggestions: stringList(data.follow_up_suggestions),
    contextTrace: data.context_trace,
    status: typeof data.status === 'string' ? data.status : '',
  }
}

async function askPaper(request: AskRequest, answerMode: 'full_paper' | 'evidence_only' = 'full_paper') {
  const response = await workspaceApi.ask(store.currentJobId, {
    ...request,
    answer_mode: answerMode,
  })
  store.addMessage(assistantMessage(response))
  await scrollToBottom()
  return response
}

function useSuggestion(suggestion: string) {
  input.value = suggestion
}

function clearSelectedContext() {
  store.setSelectedText('')
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
    const data = await workspaceApi.getMemory(store.currentJobId)
    memoryCount.value = Array.isArray(data.records) ? data.records.length : 0
    if (!store.chatHistory.length && Array.isArray(data.records)) {
      const records = data.records
        .filter((record): record is Record<string, unknown> => (
          Boolean(record)
          && typeof record === 'object'
          && (record as Record<string, unknown>).memory_type === 'interactive_answer'
        ))
      const restored = records.slice(-5).flatMap<ChatMessage>((record, index) => {
        const question = typeof record.question === 'string' ? normalizeMessageText(record.question) : ''
        const answer = typeof record.answer === 'string' ? normalizeMessageText(record.answer) : ''
        if (!question || !answer) return []
        const evidenceRefs = stringList(record.evidence_refs)
        const metadata = record.metadata && typeof record.metadata === 'object'
          ? record.metadata as Record<string, unknown>
          : {}
        const parsedTimestamp = typeof record.created_at === 'string' ? Date.parse(record.created_at) : Number.NaN
        const timestamp = Number.isFinite(parsedTimestamp) ? parsedTimestamp : Date.now() + index * 2
        return [
          { role: 'user' as const, content: question, timestamp },
          {
            role: 'assistant' as const,
            content: answer,
            timestamp: timestamp + 1,
            evidenceRefs,
            status: typeof metadata.status === 'string' ? metadata.status : 'SUCCESS',
            contextTrace: {
              scope: metadata.selected_text ? 'selection' : 'paper',
              context_mode: metadata.context_mode === 'full_paper' ? 'full_paper' : 'evidence',
              continued_from_history: index > 0,
              focus_question: question,
              evidence_count: evidenceRefs.length,
              selected_text_used: Boolean(metadata.selected_text),
              full_text_chars: typeof metadata.full_text_chars === 'number' ? metadata.full_text_chars : 0,
              full_text_complete: metadata.full_text_complete !== false,
              model: typeof metadata.model === 'string' ? metadata.model : '',
            },
          },
        ]
      })
      if (restored.length) {
        store.replaceChat(restored)
      }
    }
  } catch {
    memoryCount.value = 0
  }
}

async function send() {
  const question = compactInlineText(input.value)
  if (!question || isLoading.value || !store.currentJobId) return
  const selectedText = selectedPayloadText()
  const conversationHistory = conversationHistoryPayload()
  store.addMessage({ role: 'user', content: question, timestamp: Date.now() })
  input.value = ''
  isLoading.value = true
  await scrollToBottom()

  try {
    const request: AskRequest = {
      question,
      selected_text: selectedText,
      context_scope: selectedText ? 'selection' : 'paper',
      conversation_history: conversationHistory,
    }
    await askPaper(request, mode.value === 'evidence' ? 'evidence_only' : 'full_paper')
    await loadMemory()
  } catch (error) {
    const message = apiErrorMessage(error, 'M4 请求失败，请稍后再试。')
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
  const conversationHistory = conversationHistoryPayload()
  if (focusQuestion) {
    store.addMessage({ role: 'user', content: focusQuestion, timestamp: Date.now() })
    input.value = ''
    await scrollToBottom()
  }
  isLoading.value = true
  try {
    if (focusQuestion) {
      const answerData = await askPaper({
        question: focusQuestion,
        selected_text: selectedText,
        context_scope: selectedText ? 'selection' : 'paper',
        conversation_history: conversationHistory,
      }, 'full_paper')
      const answerEvidenceRefs = stringList(answerData.evidence_refs)
      if (answerData.status === 'DEGRADED' && answerEvidenceRefs.length === 0) {
        await loadMemory()
        return
      }
    }
    const advisorPayload: AdvisorQuestionRequest = { advisor_mode: 'group_meeting' }
    if (focusQuestion) advisorPayload.user_question = focusQuestion
    if (selectedText) advisorPayload.selected_text = selectedText
    const data = await workspaceApi.advisorQuestion(store.currentJobId, advisorPayload)
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
  } catch (error) {
    store.addMessage({ role: 'assistant', content: apiErrorMessage(error, '组会追问生成失败。'), timestamp: Date.now() })
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
    const request: AdvisorEvaluateRequest = {
      question: session.question,
      user_question: session.userQuestion,
      user_answer: userAnswer,
      expected_answer_points: session.expectedAnswerPoints,
      evidence_refs: session.evidenceRefs,
    }
    const data = await workspaceApi.advisorEvaluate(store.currentJobId, request)
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
    const message = apiErrorMessage(error, '组会反馈生成失败。')
    store.addMessage({ role: 'assistant', content: message, timestamp: Date.now() })
  } finally {
    isAdvisorEvaluating.value = false
    await scrollToBottom()
  }
}

async function clearMemory() {
  if (!store.currentJobId) return
  await workspaceApi.clearMemory(store.currentJobId).catch(() => undefined)
  store.clearChat()
  memoryCount.value = 0
  advisorSession.value = null
  advisorAnswer.value = ''
}

function chooseMode(nextMode: AskMode) {
  mode.value = nextMode
  const prompt = modePrompts[nextMode]
  if (prompt && !input.value.trim()) {
    input.value = prompt
  }
}

async function handleModeKeydown(event: KeyboardEvent, currentIndex: number) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  const nextIndex = event.key === 'Home'
    ? 0
    : event.key === 'End'
      ? modeOptions.length - 1
      : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + modeOptions.length) % modeOptions.length
  const nextMode = modeOptions[nextIndex].key
  event.preventDefault()
  chooseMode(nextMode)
  await nextTick()
  document.getElementById(`m4-mode-${nextMode}`)?.focus()
}

async function submitActiveMode() {
  if (mode.value === 'advisor') {
    await requestAdvisorQuestion()
    return
  }
  await send()
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void submitActiveMode()
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
    mode.value = 'paper'
    input.value = `${promptMap[store.selectedIntent]}：${clipText(text, 260)}`
    store.isAskPanelOpen = true
  }
})

watch(() => store.currentJobId, () => {
  void loadMemory()
}, { immediate: true })

watch(fontSize, (value) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(fontStorageKey, String(value))
})
</script>

<template>
  <section class="ask-panel" data-testid="ask-panel" :style="askPanelStyle">
    <header>
      <div>
        <h2>M4 论文助教</h2>
        <strong v-if="props.paperTitle" class="paper-focus" :title="props.paperTitle">{{ props.paperTitle }}</strong>
        <p>{{ store.selectedText ? '整篇论文 + 选中文本 · 支持连续追问' : '整篇论文已加入上下文 · 支持连续追问' }}</p>
      </div>
      <div class="header-actions">
        <div class="font-controls" aria-label="M4 字体大小">
          <button type="button" aria-label="减小 M4 字体" @click="setFontSize(fontSize - 1)">A-</button>
          <span>{{ fontSize }}</span>
          <button type="button" aria-label="增大 M4 字体" @click="setFontSize(fontSize + 1)">A+</button>
        </div>
        <button type="button" class="ghost-btn !min-h-9 !px-3" data-testid="ask-panel-toggle" @click="store.isAskPanelOpen = false">收起</button>
      </div>
    </header>

    <div class="mode-tabs" role="tablist" aria-label="M4 提问模式">
      <button
        v-for="(option, optionIndex) in modeOptions"
        :id="`m4-mode-${option.key}`"
        :key="option.key"
        type="button"
        role="tab"
        :class="{ active: mode === option.key }"
        :aria-selected="mode === option.key"
        aria-controls="m4-mode-panel"
        :tabindex="mode === option.key ? 0 : -1"
        @click="chooseMode(option.key)"
        @keydown="handleModeKeydown($event, optionIndex)"
      >
        <span>{{ option.label }}</span>
        <small>{{ option.hint }}</small>
      </button>
    </div>

    <div v-if="store.selectedText" class="selected" data-testid="selected-context">
      <div class="selected-head">
        <span>本轮附加上下文</span>
        <button type="button" aria-label="移除选中文本" @click="clearSelectedContext">移除</button>
      </div>
      <p>{{ selectedPreviewText() }}</p>
    </div>

    <div
      id="m4-mode-panel"
      ref="chatContainer"
      class="messages"
      role="tabpanel"
      :aria-labelledby="`m4-mode-${mode}`"
      aria-live="polite"
    >
      <div v-if="!store.chatHistory.length && !isLoading" class="empty">
        <span class="scope-badge">整篇论文对话</span>
        <h3>从理解论文开始</h3>
        <p>先问一个具体问题，之后可以直接用“它”“为什么”“展开讲”连续追问。</p>
        <div class="starter-prompts">
          <button type="button" @click="useSuggestion('这篇论文真正解决了什么问题？')">真正解决了什么问题？</button>
          <button type="button" @click="useSuggestion('核心方法为什么有效？')">核心方法为什么有效？</button>
          <button type="button" @click="useSuggestion('实验结果足以支持作者的结论吗？')">实验是否支撑结论？</button>
        </div>
      </div>

      <article
        v-for="(msg, index) in store.chatHistory"
        :key="index"
        class="message"
        :class="msg.role"
        data-testid="chat-message"
      >
        <div class="avatar">{{ msg.role === 'user' ? '你' : 'M4' }}</div>
        <div v-if="msg.role === 'assistant'" class="message-body">
          <div class="context-trace" v-if="msg.contextTrace" data-testid="context-trace">
            <span>{{ msg.contextTrace.continued_from_history ? '承接上一问' : msg.contextTrace.scope === 'selection' ? '选中文本' : '当前论文' }}</span>
            <span v-if="msg.contextTrace.context_mode === 'full_paper'">
              {{ contextSizeLabel(msg.contextTrace.full_text_chars) }}{{ msg.contextTrace.full_text_complete === false ? ' · 已压缩' : '' }}
            </span>
            <span v-else>{{ msg.contextTrace.evidence_count }} 条出处</span>
            <span v-if="msg.contextTrace.model">{{ msg.contextTrace.model }}</span>
          </div>
          <div class="bubble answer-bubble">
            <p
              v-for="(block, blockIndex) in answerBlocks(msg.content)"
              :key="`${index}-${blockIndex}-${block.text.slice(0, 18)}`"
              class="answer-block"
              :class="`tone-${block.tone}`"
            >
              <span v-if="block.label" class="answer-label">{{ block.label }}</span>
              <span class="answer-text">
                <template
                  v-for="(segment, segmentIndex) in highlightSegments(block.text)"
                  :key="`${segmentIndex}-${segment.text}`"
                >
                  <mark v-if="segment.highlighted" class="answer-keyword">{{ segment.text }}</mark>
                  <span v-else>{{ segment.text }}</span>
                </template>
              </span>
            </p>
          </div>
          <p v-if="msg.status === 'DEGRADED' && msg.uncertainty" class="answer-uncertainty">{{ msg.uncertainty }}</p>
          <div v-if="msg.followUpSuggestions?.length" class="follow-up-row" aria-label="建议追问">
            <button
              v-for="suggestion in msg.followUpSuggestions"
              :key="suggestion"
              type="button"
              @click="useSuggestion(suggestion)"
            >
              {{ suggestion }}
            </button>
          </div>
        </div>
        <div v-else class="bubble compact">{{ msg.content }}</div>
      </article>

      <div v-if="isLoading" class="message assistant">
        <div class="avatar">M4</div>
        <div class="bubble loading">正在阅读整篇论文并组织回答...</div>
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
      <button type="button" data-testid="advisor-button" @click="requestAdvisorQuestion">直接组会追问</button>
      <button type="button" @click="clearMemory">清空对话</button>
    </div>

    <form class="composer" @submit.prevent="submitActiveMode">
      <div class="composer-box">
        <textarea
          v-model="input"
          data-testid="ask-input"
          rows="2"
          :placeholder="inputPlaceholder"
          @keydown="handleKeydown"
        />
        <div class="composer-meta">
          <span>回答范围：当前论文{{ store.selectedText ? ' + 选中文本' : '' }}</span>
          <span>Enter 发送 · Shift+Enter 换行</span>
        </div>
      </div>
      <button type="submit" data-testid="ask-submit" class="primary-btn" :disabled="isLoading || (mode !== 'advisor' && !input.trim())">{{ submitLabel }}</button>
    </form>
  </section>
</template>

<style scoped src="./AskPanel.css"></style>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useLearningStore, type ChatMessage } from '../../stores/learning'
import { apiErrorMessage, workspaceApi } from '../../api/client'
import type { AdvisorEvaluateRequest, AdvisorQuestionRequest, AskRequest, AskResponse } from '../../types/api'
import MarkdownAnswer from './MarkdownAnswer.vue'
import QuestionNavigator from './QuestionNavigator.vue'
import {
  clipText,
  compactInlineText,
  contextSizeLabel,
  normalizeMessageText,
} from '../../utils/tutorAnswerFormatting'

const store = useLearningStore()
const props = withDefaults(defineProps<{ paperTitle?: string; side?: 'left' | 'right' }>(), {
  side: 'right',
})
const emit = defineEmits<{ toggleSide: [] }>()
const input = ref('')
const chatContainer = ref<HTMLElement>()
const isLoading = ref(false)
const isAdvisorEvaluating = ref(false)
const memoryCount = ref(0)
const advisorAnswer = ref('')
const advisorSession = ref<AdvisorSession | null>(null)
const mode = ref<TutorMode>('paper')
const activeQuestionMessageIndex = ref(-1)
const fontStorageKey = 'researchsensei.tutor.fontSize.v2'
const fontSize = ref(initialTutorFontSize())

type TutorMode = 'paper' | 'evidence' | 'advisor'

const modeOptions: Array<{ key: TutorMode; label: string; hint: string }> = [
  { key: 'paper', label: '论文问答', hint: '结合全文，自然讲解' },
  { key: 'evidence', label: '原文证据', hint: '只定位出处，不调用模型' },
  { key: 'advisor', label: '组会演练', hint: '追问、作答、反馈' },
]

const questionNodes = computed(() => {
  let sequence = 0
  return store.chatHistory.flatMap((message, messageIndex) => {
    if (message.role !== 'user') return []
    sequence += 1
    return [{
      messageIndex,
      sequence,
      label: clipText(message.content, 48),
      title: message.content,
    }]
  })
})

const modePrompts: Record<TutorMode, string> = {
  paper: '请像一位耐心的论文助教一样，结合整篇论文自然地讲清楚核心方法。根据内容决定详略，不要只给一句概括。',
  evidence: '这条结论对应哪条证据？',
  advisor: '',
}

const starterPrompts = computed(() => {
  if (mode.value === 'evidence') {
    return [
      { label: '核心方法对应哪些原文？', prompt: '这篇论文的核心方法对应哪些原文段落或页码？' },
      { label: '哪些实验支撑主要结论？', prompt: '作者用哪些实验或正文证据支撑主要结论？' },
      { label: '局限写在什么位置？', prompt: '论文在哪些原文段落说明了方法局限？' },
    ]
  }
  if (mode.value === 'advisor') {
    return [
      { label: '围绕核心方法追问', prompt: '请围绕这篇论文的核心方法进行组会追问。' },
      { label: '围绕实验设计追问', prompt: '请围绕这篇论文的实验设计进行组会追问。' },
      { label: '围绕局限性追问', prompt: '请围绕这篇论文的局限性进行组会追问。' },
    ]
  }
  return [
    { label: '真正解决了什么问题？', prompt: '这篇论文真正解决了什么问题？' },
    { label: '核心方法为什么有效？', prompt: '核心方法为什么有效？' },
    { label: '实验是否支撑结论？', prompt: '实验结果足以支持作者的结论吗？' },
  ]
})

const inputPlaceholder = computed(() => {
  if (mode.value === 'evidence') return '问证据，例如：这个结论靠哪类实验或正文段落支撑？'
  if (mode.value === 'advisor') return '写下你想被追问的点；留空则按整篇论文生成组会问题'
  return '问论文助教，例如：这篇论文到底解决了什么问题？'
})

const submitLabel = computed(() => {
  if (mode.value === 'evidence') return '找证据'
  if (mode.value === 'advisor') return '生成追问'
  return '发送'
})

const tutorPanelStyle = computed<Record<string, string>>(() => ({
  '--tutor-font-size': `${fontSize.value}px`,
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

function initialTutorFontSize() {
  if (typeof localStorage === 'undefined') return 15
  const raw = localStorage.getItem(fontStorageKey)
  if (raw === null || !raw.trim()) return 15
  const saved = Number(raw)
  return Number.isFinite(saved) ? Math.min(Math.max(saved, 14), 20) : 15
}

function setFontSize(nextSize: number) {
  fontSize.value = Math.min(Math.max(nextSize, 14), 20)
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
    content: normalizeMessageText(data.answer || '论文助教暂时无法回答这个问题。'),
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

function useSuggestion(suggestion: string, nextMode: TutorMode = 'paper') {
  mode.value = nextMode
  input.value = suggestion
}

function isEvidenceLookupQuestion(question: string) {
  const normalized = question.toLowerCase().replace(/\s+/g, '')
  return [
    /原文/,
    /出处/,
    /页码|第几页|哪(?:一)?页/,
    /哪(?:一)?段|哪(?:一)?句/,
    /引用/,
    /证据/,
    /依据/,
    /支撑|支持/,
    /文中哪里|论文哪里|在哪里(?:提到|说明|写)/,
    /\b(?:quote|citation|evidence|page|paragraph|source)\b/,
  ].some(pattern => pattern.test(normalized))
}

function answerModeForQuestion(question: string): 'full_paper' | 'evidence_only' {
  if (mode.value === 'evidence' && isEvidenceLookupQuestion(question)) return 'evidence_only'
  if (mode.value === 'evidence') mode.value = 'paper'
  return 'full_paper'
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
  return normalizeMessageText(`${score}${session.feedback || '论文助教已完成评价。'}${missing}${next}`)
}

async function loadMemory({ revealLatest = false }: { revealLatest?: boolean } = {}) {
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
  } finally {
    if (revealLatest) await scrollToBottom('auto')
  }
}

async function send() {
  const question = compactInlineText(input.value)
  if (!question || isLoading.value || !store.currentJobId) return
  const answerMode = answerModeForQuestion(question)
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
    await askPaper(request, answerMode)
    await loadMemory()
  } catch (error) {
    const message = apiErrorMessage(error, '论文助教请求失败，请稍后再试。')
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

function chooseMode(nextMode: TutorMode) {
  const currentInput = input.value.trim()
  const generatedPrompts = Object.values(modePrompts).filter(Boolean)
  const shouldReplacePrompt = !currentInput || generatedPrompts.includes(currentInput)
  mode.value = nextMode
  const prompt = modePrompts[nextMode]
  if (shouldReplacePrompt) input.value = prompt
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
  document.getElementById(`tutor-mode-${nextMode}`)?.focus()
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

function updateActiveQuestion() {
  const container = chatContainer.value
  if (!container || !questionNodes.value.length) {
    activeQuestionMessageIndex.value = -1
    return
  }
  const markerY = container.getBoundingClientRect().top + Math.min(110, container.clientHeight * 0.25)
  const questionElements = Array.from(
    container.querySelectorAll<HTMLElement>('[data-question-message-index]'),
  )
  let activeIndex = questionNodes.value[0].messageIndex
  for (const element of questionElements) {
    if (element.getBoundingClientRect().top > markerY) break
    const messageIndex = Number(element.dataset.questionMessageIndex)
    if (Number.isFinite(messageIndex)) activeIndex = messageIndex
  }
  activeQuestionMessageIndex.value = activeIndex
}

function scrollToQuestion(messageIndex: number) {
  const container = chatContainer.value
  const target = container?.querySelector<HTMLElement>(
    `[data-question-message-index="${messageIndex}"]`,
  )
  if (!container || !target) return
  const top = container.scrollTop
    + target.getBoundingClientRect().top
    - container.getBoundingClientRect().top
    - 12
  activeQuestionMessageIndex.value = messageIndex
  container.scrollTo?.({ top: Math.max(0, top), behavior: 'auto' })
}

async function scrollToBottom(behavior: ScrollBehavior = 'smooth') {
  await nextTick()
  const container = chatContainer.value
  container?.scrollTo?.({ top: container.scrollHeight, behavior })
  activeQuestionMessageIndex.value = questionNodes.value.at(-1)?.messageIndex ?? -1
}

onMounted(() => {
  void scrollToBottom('auto')
})

watch(() => store.selectedText, (text) => {
  if (text) {
    const promptMap = {
      explain: '请解释这段话',
      simplify: '请用更简单的中文讲这段话',
      example: '请给这段话配一个具体例子',
    }
    mode.value = 'paper'
    input.value = `${promptMap[store.selectedIntent]}：${clipText(text, 260)}`
    store.isPaperTutorPanelOpen = true
  }
})

watch(() => store.currentJobId, () => {
  void loadMemory({ revealLatest: true })
}, { immediate: true })

watch(fontSize, (value) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(fontStorageKey, String(value))
})
</script>

<template>
  <section class="paper-tutor-panel" data-testid="paper-tutor-panel" :style="tutorPanelStyle">
    <header>
      <div>
        <h2>论文助教</h2>
        <strong v-if="props.paperTitle" class="paper-focus" :title="props.paperTitle">{{ props.paperTitle }}</strong>
        <p>{{ store.selectedText ? '整篇论文 + 选中文本 · 支持连续追问' : '整篇论文已加入上下文 · 支持连续追问' }}</p>
      </div>
      <div class="header-actions">
        <button
          type="button"
          class="pane-side-toggle"
          data-testid="tutor-side-toggle"
          :aria-label="props.side === 'right' ? '把论文助教移到论文左侧' : '把论文助教移到论文右侧'"
          :title="props.side === 'right' ? '把论文助教移到论文左侧' : '把论文助教移到论文右侧'"
          @click="emit('toggleSide')"
        >
          {{ props.side === 'right' ? '左置' : '右置' }}
        </button>
        <div class="font-controls" aria-label="论文助教字体大小">
          <button type="button" aria-label="减小论文助教字体" @click="setFontSize(fontSize - 1)">A-</button>
          <span>{{ fontSize }}</span>
          <button type="button" aria-label="增大论文助教字体" @click="setFontSize(fontSize + 1)">A+</button>
        </div>
        <button type="button" class="ghost-btn !min-h-9 !px-3" data-testid="paper-tutor-panel-toggle" @click="store.isPaperTutorPanelOpen = false">收起</button>
      </div>
    </header>

    <div class="mode-tabs" role="tablist" aria-label="论文助教提问模式">
      <button
        v-for="(option, optionIndex) in modeOptions"
        :id="`tutor-mode-${option.key}`"
        :key="option.key"
        type="button"
        role="tab"
        :class="{ active: mode === option.key }"
        :aria-selected="mode === option.key"
        aria-controls="tutor-mode-panel"
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
      id="tutor-mode-panel"
      ref="chatContainer"
      class="messages"
      role="tabpanel"
      :aria-labelledby="`tutor-mode-${mode}`"
      aria-live="polite"
      @scroll.passive="updateActiveQuestion"
    >
      <div v-if="!store.chatHistory.length && !isLoading" class="empty">
        <span class="scope-badge">整篇论文对话</span>
        <h3>从理解论文开始</h3>
        <p>先问一个具体问题，之后可以直接用“它”“为什么”“展开讲”连续追问。</p>
        <div class="starter-prompts">
          <button
            v-for="starter in starterPrompts"
            :key="starter.prompt"
            type="button"
            @click="useSuggestion(starter.prompt, mode)"
          >
            {{ starter.label }}
          </button>
        </div>
      </div>

      <article
        v-for="(msg, index) in store.chatHistory"
        :key="index"
        class="message"
        :class="msg.role"
        :data-question-message-index="msg.role === 'user' ? index : undefined"
        data-testid="chat-message"
      >
        <div class="avatar">{{ msg.role === 'user' ? '你' : '助教' }}</div>
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
            <MarkdownAnswer :content="msg.content" />
          </div>
          <p v-if="msg.status === 'DEGRADED' && msg.uncertainty" class="answer-uncertainty">{{ msg.uncertainty }}</p>
          <div v-if="msg.followUpSuggestions?.length" class="follow-up-row" aria-label="建议追问">
            <button
              v-for="suggestion in msg.followUpSuggestions"
              :key="suggestion"
              type="button"
              @click="useSuggestion(suggestion, 'paper')"
            >
              {{ suggestion }}
            </button>
          </div>
        </div>
        <div v-else class="bubble compact">{{ msg.content }}</div>
      </article>

      <div v-if="isLoading" class="message assistant">
        <div class="avatar">助教</div>
        <div class="bubble loading">正在阅读整篇论文并组织回答...</div>
      </div>
    </div>

    <QuestionNavigator
      v-if="questionNodes.length > 1"
      :nodes="questionNodes"
      :active-message-index="activeQuestionMessageIndex"
      @select="scrollToQuestion"
    />

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
          placeholder="写下你的 20-30 秒回答，论文助教会按问题、机制、证据给反馈"
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

<style scoped src="./PaperTutorPanel.css"></style>

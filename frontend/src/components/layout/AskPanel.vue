<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useLearningStore } from '../../stores/learning'
import { apiErrorMessage, workspaceApi } from '../../api/client'
import type { AdvisorEvaluateRequest, AdvisorQuestionRequest, AskRequest, AskResponse } from '../../types/api'

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
  { key: 'paper', label: '讲论文', hint: '概念、方法、贡献' },
  { key: 'evidence', label: '找证据', hint: '结论、依据、限制' },
  { key: 'advisor', label: '组会', hint: '追问、反馈、补强' },
]

const modePrompts: Record<AskMode, string> = {
  paper: '请像助教一样自然地讲清楚这篇论文的核心方法：先讲它想解决什么困惑，再讲方法怎么起作用，最后补一句主要证据。',
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

type AnswerTone = 'lead' | 'concept' | 'evidence' | 'caution' | 'followup' | 'plain'
type AnswerBlock = {
  text: string
  tone: AnswerTone
  label: string
}
type AnswerSegment = {
  text: string
  highlighted: boolean
}

const answerToneLabels: Record<AnswerTone, string> = {
  lead: '重点',
  concept: '解释',
  evidence: '证据',
  caution: '提醒',
  followup: '追问',
  plain: '说明',
}

const answerHighlightTerms = [
  '核心问题',
  '核心方法',
  '关键机制',
  '关键',
  '直觉',
  '机制',
  '证据',
  '依据',
  '结论',
  '限制',
  '公式',
  '变量',
  '实验',
  '消融',
  '结果',
  '注意力',
  'attention',
  'embedding',
  'loss',
  'reward',
]

function compactInlineText(value: string) {
  return value
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;:，。；：、）\]\}])/g, '$1')
    .replace(/([（\[\{])\s+/g, '$1')
    .trim()
}

function initialM4FontSize() {
  if (typeof localStorage === 'undefined') return 14
  const saved = Number(localStorage.getItem(fontStorageKey))
  return Number.isFinite(saved) ? Math.min(Math.max(saved, 13), 18) : 14
}

function setFontSize(nextSize: number) {
  fontSize.value = Math.min(Math.max(nextSize, 13), 18)
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

function splitAnswerText(content: string) {
  return content
    .replace(/\r\n/g, '\n')
    .split(/\n\s*\n|\n(?=\s*(?:\d+[.、]|[-*]\s|[（(]?\d+[）)]))/)
    .map(part => part.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)
}

function answerTone(text: string, index: number): AnswerTone {
  const compact = text.replace(/\s+/g, '')
  if (/证据不足|没有足够|没有给出|无法|不能硬编|不确定|暂时|缺少|不足以|失败/.test(compact)) return 'caution'
  if (/组会追问|下一问|追问|你可以|继续问|可以继续|直接问|直接回我|试着回答|补一句/.test(compact)) return 'followup'
  if (index === 0) return 'lead'
  if (/能追到|证据是|依据是|正文|实验|结果|消融|评估|对比|支撑|显示|表明|观察到/.test(compact)) return 'evidence'
  if (/直觉|可以理解为|换句话说|意思是|机制|方法|公式|变量|模型|训练|推理|注意力|attention|embedding|向量|loss|reward|算法|理论|定理|证明/.test(compact)) {
    return 'concept'
  }
  if (/证据|依据/.test(compact)) return 'evidence'
  return 'plain'
}

function answerBlocks(content: string): AnswerBlock[] {
  return splitAnswerText(content).map((text, index) => {
    const tone = answerTone(text, index)
    return {
      text,
      tone,
      label: answerToneLabels[tone],
    }
  })
}

function highlightSegments(text: string): AnswerSegment[] {
  const segments: AnswerSegment[] = []
  let cursor = 0
  const lowerText = text.toLowerCase()
  const terms = [...answerHighlightTerms].sort((a, b) => b.length - a.length)

  while (cursor < text.length) {
    let bestIndex = -1
    let bestTerm = ''
    for (const term of terms) {
      const index = lowerText.indexOf(term.toLowerCase(), cursor)
      if (index === -1) continue
      if (bestIndex === -1 || index < bestIndex || (index === bestIndex && term.length > bestTerm.length)) {
        bestIndex = index
        bestTerm = term
      }
    }
    if (bestIndex === -1) {
      segments.push({ text: text.slice(cursor), highlighted: false })
      break
    }
    if (bestIndex > cursor) {
      segments.push({ text: text.slice(cursor, bestIndex), highlighted: false })
    }
    segments.push({ text: text.slice(bestIndex, bestIndex + bestTerm.length), highlighted: true })
    cursor = bestIndex + bestTerm.length
  }

  return segments.length ? segments : [{ text, highlighted: false }]
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

function markEnhancementUnavailable(messageIndex: number) {
  const current = store.chatHistory[messageIndex]
  if (!current || current.role !== 'assistant') return
  store.replaceMessage(messageIndex, {
    ...current,
    status: 'DEGRADED',
    uncertainty: '模型增强暂时没有完成；上方答案仍来自当前论文的已验证证据。',
  })
}

async function askEvidenceFirst(request: AskRequest) {
  const preview = await workspaceApi.ask(store.currentJobId, {
    ...request,
    answer_mode: 'evidence_only',
  })
  const previewRefs = stringList(preview.evidence_refs)
  const previewIsGrounded = preview.status !== 'DEGRADED' || previewRefs.length > 0
  let messageIndex = -1
  if (previewIsGrounded) {
    messageIndex = store.chatHistory.length
    store.addMessage(assistantMessage(preview))
    await scrollToBottom()
  }

  try {
    const enhanced = await workspaceApi.ask(store.currentJobId, {
      ...request,
      answer_mode: 'enhanced',
    })
    if (
      enhanced.status === 'DEGRADED'
      && stringList(enhanced.evidence_refs).length === 0
      && previewRefs.length > 0
      && messageIndex >= 0
    ) {
      markEnhancementUnavailable(messageIndex)
      return preview
    }
    if (messageIndex >= 0) {
      store.replaceMessage(messageIndex, assistantMessage(enhanced))
    } else {
      store.addMessage(assistantMessage(enhanced))
      await scrollToBottom()
    }
    return enhanced
  } catch {
    if (messageIndex >= 0) {
      markEnhancementUnavailable(messageIndex)
    } else {
      store.addMessage(assistantMessage(preview))
      await scrollToBottom()
    }
    return preview
  }
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
      const latest = records.at(-1)
      const question = typeof latest?.question === 'string' ? normalizeMessageText(latest.question) : ''
      if (latest && question) {
        const evidenceRefs = stringList(latest.evidence_refs)
        const timestamp = typeof latest.created_at === 'string' ? Date.parse(latest.created_at) : Date.now()
        store.replaceChat([
          { role: 'user', content: question, timestamp },
          {
            role: 'assistant',
            content: '已恢复这篇论文的上一轮问题。你可以直接继续追问；M4 会重新检索并验证当前证据，不回放旧版本答案。',
            timestamp: timestamp + 1,
            evidenceRefs,
            contextTrace: {
              scope: 'paper',
              continued_from_history: true,
              focus_question: question,
              evidence_count: evidenceRefs.length,
              selected_text_used: false,
            },
          },
        ])
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
    await askEvidenceFirst(request)
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
      const answerData = await askEvidenceFirst({
        question: focusQuestion,
        selected_text: selectedText,
        context_scope: selectedText ? 'selection' : 'paper',
        conversation_history: conversationHistory,
      })
      const answerEvidenceRefs = stringList(answerData.evidence_refs)
      store.addMessage(assistantMessage(answerData))
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
        <p>{{ store.selectedText ? '当前论文 · 选中文本已加入上下文' : '当前论文证据已锁定 · 支持连续追问' }}</p>
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
        <span class="scope-badge">仅当前论文</span>
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
            <span>{{ msg.contextTrace.evidence_count }} 条已验证证据</span>
          </div>
          <div class="bubble answer-bubble">
            <p
              v-for="(block, blockIndex) in answerBlocks(msg.content)"
              :key="`${index}-${blockIndex}-${block.text.slice(0, 18)}`"
              class="answer-block"
              :class="`tone-${block.tone}`"
            >
              <span class="answer-label">{{ block.label }}</span>
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
  padding: 14px 16px;
}

h2 {
  color: var(--text-primary);
  font-size: calc(var(--m4-font-size, 14px) + 2px);
  font-weight: 720;
}

.paper-focus {
  display: block;
  max-width: 280px;
  overflow: hidden;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: calc(var(--m4-font-size, 14px) - 1px);
  font-weight: 620;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

header p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: calc(var(--m4-font-size, 14px) - 1px);
}

.header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
}

.font-controls {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 2px;
  background: var(--bg-secondary);
}

.font-controls button {
  min-height: 28px;
  min-width: 30px;
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.font-controls button:hover {
  background: var(--bg-card);
  color: var(--text-primary);
}

.font-controls span {
  min-width: 18px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 8px 12px;
  background: color-mix(in srgb, var(--bg-card) 94%, var(--bg-secondary));
}

.mode-tabs button {
  display: grid;
  min-height: 42px;
  align-content: center;
  gap: 1px;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 6px 8px;
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
}

.mode-tabs button.active {
  border-color: var(--border-subtle);
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.mode-tabs span {
  font-size: 13px;
  font-weight: 650;
  line-height: 1.2;
}

.mode-tabs small {
  overflow: hidden;
  color: inherit;
  font-size: 11px;
  line-height: 1.35;
  opacity: 0.74;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected {
  margin: 14px 18px 0;
  border-radius: 8px;
  padding: 12px;
  background: var(--accent-light);
}

.selected span {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.selected-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.selected-head button {
  border-radius: 6px;
  padding: 3px 7px;
  color: var(--text-muted);
  font-size: 11px;
}

.selected-head button:hover {
  background: color-mix(in srgb, var(--accent) 10%, transparent);
  color: var(--text-primary);
}

.selected p {
  margin-top: 4px;
  max-height: 118px;
  overflow-y: auto;
  color: var(--text-secondary);
  font-size: var(--m4-font-size, 14px);
  line-height: 1.7;
  overflow-wrap: break-word;
  white-space: normal;
  word-break: normal;
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 16px;
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
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 650;
}

.advisor-head strong {
  color: var(--text-primary);
  font-size: 13px;
}

.advisor-question {
  margin-top: 8px;
  color: var(--text-primary);
  font-size: var(--m4-font-size, 14px);
  line-height: 1.65;
}

.advisor-points {
  display: grid;
  gap: 4px;
  margin-top: 8px;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: calc(var(--m4-font-size, 14px) - 1px);
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
  font-size: var(--m4-font-size, 14px);
}

.advisor-feedback {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  border-left: 3px solid var(--accent);
  padding-left: 10px;
  color: var(--text-secondary);
  font-size: calc(var(--m4-font-size, 14px) - 1px);
  line-height: 1.55;
}

.empty {
  margin: 46px auto 0;
  max-width: 320px;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
  padding: 18px;
  background: color-mix(in srgb, var(--bg-secondary) 54%, transparent);
  text-align: left;
}

.scope-badge {
  display: inline-flex;
  border: 1px solid color-mix(in srgb, var(--success) 28%, var(--border-subtle));
  border-radius: 999px;
  padding: 3px 8px;
  background: color-mix(in srgb, var(--success) 9%, transparent);
  color: var(--success);
  font-size: 11px;
  font-weight: 700;
}

.empty h3 {
  margin-top: 12px;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 720;
}

.starter-prompts {
  display: grid;
  gap: 6px;
  margin-top: 14px;
}

.starter-prompts button {
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  text-align: left;
}

.starter-prompts button:hover {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--border-subtle));
  color: var(--text-primary);
}

.empty p {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: calc(var(--m4-font-size, 14px) + 1px);
}

.message {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 9px;
  margin-bottom: 16px;
}

.message.user {
  grid-template-columns: minmax(0, 1fr) 30px;
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
  height: 30px;
  width: 30px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.bubble {
  max-width: 100%;
  min-width: 0;
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: var(--m4-font-size, 14px);
  line-height: 1.75;
  letter-spacing: 0;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  word-break: normal;
}

.message-body {
  display: grid;
  min-width: 0;
  gap: 7px;
}

.context-trace {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.context-trace span {
  border-radius: 999px;
  padding: 3px 7px;
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 650;
}

.context-trace span:first-child {
  background: color-mix(in srgb, var(--accent) 9%, var(--bg-secondary));
  color: color-mix(in srgb, var(--accent) 78%, var(--text-primary));
}

.answer-bubble {
  display: grid;
  gap: 8px;
  padding: 9px;
  background: color-mix(in srgb, var(--bg-secondary) 92%, var(--bg-card));
  white-space: normal;
}

.answer-block {
  --answer-accent: var(--accent);
  --answer-bg: rgba(var(--accent-rgb), 0.08);
  margin: 0;
  border-left: 3px solid var(--answer-accent);
  border-radius: 8px;
  padding: 8px 10px 8px 11px;
  background: var(--answer-bg);
  color: var(--text-primary);
  font-size: var(--m4-font-size, 14px);
  line-height: 1.78;
}

.answer-block.tone-lead {
  --answer-accent: var(--text-primary);
  --answer-bg: var(--bg-card);
  font-weight: 650;
}

.answer-block.tone-concept {
  --answer-accent: #0f766e;
  --answer-bg: rgba(15, 118, 110, 0.08);
}

.answer-block.tone-evidence {
  --answer-accent: var(--warning);
  --answer-bg: rgba(180, 83, 9, 0.1);
}

.answer-block.tone-caution {
  --answer-accent: #be123c;
  --answer-bg: rgba(190, 18, 60, 0.08);
}

.answer-block.tone-followup {
  --answer-accent: var(--text-muted);
  --answer-bg: color-mix(in srgb, var(--bg-card) 62%, transparent);
}

.answer-block.tone-plain {
  --answer-accent: var(--text-muted);
  --answer-bg: color-mix(in srgb, var(--bg-card) 54%, transparent);
}

.answer-label {
  display: inline-flex;
  margin-right: 8px;
  color: var(--answer-accent);
  font-size: calc(var(--m4-font-size, 14px) - 2px);
  font-weight: 650;
  line-height: inherit;
}

.answer-text {
  font-weight: 450;
}

.answer-keyword {
  border-radius: 5px;
  padding: 0 0.18em;
  background: color-mix(in srgb, var(--answer-accent) 16%, transparent);
  color: color-mix(in srgb, var(--answer-accent) 88%, var(--text-primary));
  font-weight: 720;
}

:global(.dark) .answer-block.tone-lead {
  --answer-accent: #93c5fd;
  --answer-bg: rgba(147, 197, 253, 0.11);
}

:global(.dark) .answer-block.tone-concept {
  --answer-accent: #5eead4;
  --answer-bg: rgba(94, 234, 212, 0.1);
}

:global(.dark) .answer-block.tone-evidence {
  --answer-accent: #fbbf24;
  --answer-bg: rgba(251, 191, 36, 0.11);
}

:global(.dark) .answer-block.tone-caution {
  --answer-accent: #fb7185;
  --answer-bg: rgba(251, 113, 133, 0.1);
}

:global(.dark) .answer-block.tone-followup {
  --answer-accent: var(--text-muted);
  --answer-bg: rgba(255, 255, 255, 0.06);
}

.message.user .bubble.compact {
  max-width: min(100%, 320px);
  white-space: normal;
}

.loading {
  color: var(--text-muted);
}

.answer-uncertainty {
  border-left: 2px solid var(--warning);
  padding-left: 9px;
  color: var(--text-muted);
  font-size: calc(var(--m4-font-size, 14px) - 2px);
  line-height: 1.55;
}

.follow-up-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.follow-up-row button {
  max-width: 100%;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  padding: 5px 9px;
  color: var(--text-secondary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.follow-up-row button:hover {
  border-color: color-mix(in srgb, var(--accent) 42%, var(--border-subtle));
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.quick-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--border-subtle);
  padding: 10px 16px;
}

.quick-row button {
  border-radius: 8px;
  padding: 7px 11px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.quick-row button:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 8px;
  padding: 0 16px 16px;
}

.composer-box {
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-elevated);
}

.composer-box textarea {
  min-height: 64px;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.composer-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 0 12px 8px;
  color: var(--text-muted);
  font-size: 10px;
}

.composer-meta span:last-child {
  white-space: nowrap;
}

textarea {
  width: 100%;
  resize: none;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-size: var(--m4-font-size, 14px);
  line-height: 1.6;
}
</style>

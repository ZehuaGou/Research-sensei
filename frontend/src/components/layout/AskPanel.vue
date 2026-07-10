<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useLearningStore } from '../../stores/learning'

const store = useLearningStore()
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

function conversationHistoryPayload(limit = 10) {
  return store.chatHistory
    .slice(-limit)
    .map(message => ({
      role: message.role,
      content: clipText(message.content, 1200),
    }))
    .filter(message => message.content.length > 0)
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
  const conversationHistory = conversationHistoryPayload()
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
        conversation_history: conversationHistory,
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
  const conversationHistory = conversationHistoryPayload()
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
          conversation_history: conversationHistory,
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

function chooseMode(nextMode: AskMode) {
  mode.value = nextMode
  const prompt = modePrompts[nextMode]
  if (prompt && !input.value.trim()) {
    input.value = prompt
  }
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
        <p>{{ store.selectedText ? '正在基于选中文本回答' : '正在基于当前论文回答' }}</p>
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
        v-for="option in modeOptions"
        :key="option.key"
        type="button"
        :class="{ active: mode === option.key }"
        :aria-pressed="mode === option.key"
        @click="chooseMode(option.key)"
      >
        <span>{{ option.label }}</span>
        <small>{{ option.hint }}</small>
      </button>
    </div>

    <div v-if="store.selectedText" class="selected" data-testid="selected-context">
      <span>已选中文本</span>
      <p>{{ selectedPreviewText() }}</p>
    </div>

    <div ref="chatContainer" class="messages">
      <div v-if="!store.chatHistory.length && !isLoading" class="empty">
        <h3>还没有对话</h3>
        <p>问题越具体，回答越容易贴住论文证据。</p>
      </div>

      <article
        v-for="(msg, index) in store.chatHistory"
        :key="index"
        class="message"
        :class="msg.role"
        data-testid="chat-message"
      >
        <div class="avatar">{{ msg.role === 'user' ? '你' : 'M4' }}</div>
        <div v-if="msg.role === 'assistant'" class="bubble answer-bubble">
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
      <textarea
        v-model="input"
        data-testid="ask-input"
        rows="2"
        :placeholder="inputPlaceholder"
        @keydown="handleKeydown"
      />
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
  margin: 70px auto 0;
  max-width: 320px;
  border: 1px dashed var(--border-subtle);
  border-radius: 8px;
  padding: 18px;
  background: color-mix(in srgb, var(--bg-secondary) 54%, transparent);
  text-align: left;
}

.empty h3 {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 720;
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
  gap: 10px;
  padding: 0 16px 16px;
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

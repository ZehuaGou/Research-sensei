<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLearningStore } from '../stores/learning'
import AskPanel from '../components/layout/AskPanel.vue'
import TextSelectionToolbar from '../components/interactive/TextSelectionToolbar.vue'
import StatusBanner from '../components/StatusBanner.vue'
import PaperCard from '../components/cards/PaperCard.vue'
import FormulaCard from '../components/cards/FormulaCard.vue'

const route = useRoute()
const router = useRouter()
const store = useLearningStore()
const jobId = route.params.jobId as string

type FormulaEntry = {
  id: string
  index: number
  card: any
  title: string
}

const understandingStatus = ref<any>(null)
const paperWorkspaceStatus = ref<Record<string, any>>({})
const cards = ref<Record<string, any> | null>(null)
const degraded = ref(false)
const missingComponents = ref<string[]>([])
const isLoading = ref(true)
const error = ref('')
const activeTab = ref<'paper' | 'formulas' | 'teaching'>('paper')
const activeFormulaAnchor = ref('')
const formulaOrder = ref<string[]>([])
const collapsedFormulas = ref<Record<string, boolean>>({})
const focusedFormula = ref<{ card: any; index: number } | null>(null)
const formulaRailCollapsed = ref(false)
let formulaObserver: IntersectionObserver | null = null

const status = computed(() => understandingStatus.value?.status || '')
const canShowCards = computed(() => ['SUCCESS', 'DEGRADED_STRUCTURAL'].includes(status.value))
const paperCard = computed(() => cards.value?.paper_card || null)
const teachingCards = computed(() => cards.value?.teaching_cards?.teaching_cards || [])
const allFormulaCards = computed(() => {
  const bundle = cards.value?.formula_cards
  if (!bundle) return []
  if (Array.isArray(bundle)) return bundle
  if (Array.isArray(bundle.formula_cards)) return bundle.formula_cards
  return []
})
const formulaCardsList = computed(() => allFormulaCards.value.filter(isUsableFormulaCard))
const hiddenRawFormulaCount = computed(() => allFormulaCards.value.length - formulaCardsList.value.length)

const noCardsMessage = computed(() => {
  if (status.value === 'BASELINE_ONLY' && understandingStatus.value?.blocking_reason === 'NO_LLM_CLIENT') {
    return '这次运行没有接入实时大模型，所以只保留基础诊断，不展示用户可读卡片。请确认 ccswitch 正在运行、环境变量已启用，然后重新深读。'
  }
  if (status.value === 'BLOCKED_UNDERSTANDING') {
    return '理解阶段被阻断。系统没有展示半成品卡片，请查看上方状态原因后重新运行。'
  }
  return '当前状态没有可展示的用户卡片。'
})

const formulaTabDisabled = computed(() => {
  if (formulaCardsList.value.length > 0) return false
  return status.value !== 'DEGRADED_STRUCTURAL'
})

const tabs = computed(() => [
  { key: 'paper' as const, label: '论文概览', count: paperCard.value ? 1 : 0, disabled: !paperCard.value },
  { key: 'formulas' as const, label: '公式拆解', count: formulaCardsList.value.length, disabled: formulaTabDisabled.value },
  { key: 'teaching' as const, label: '教学卡片', count: teachingCards.value.length, disabled: teachingCards.value.length === 0 },
])

const formulaNavItems = computed(() => formulaCardsList.value.map((formula: any, index: number) => {
  const card = normalizeFormulaCard(formula, index)
  const id = formulaAnchor(formula, index)
  return {
    id,
    index: index + 1,
    title: clipLabel(card.display_title || card.purpose || card.problem || `公式 ${index + 1}`, 46),
    formula_latex: card.formula_latex || card.formula_raw || '',
  }
}))

const formulaEntries = computed<FormulaEntry[]>(() => formulaCardsList.value.map((formula: any, index: number) => {
  const card = normalizeFormulaCard(formula, index)
  return {
    id: formulaAnchor(formula, index),
    index: index + 1,
    card,
    title: clipLabel(card.display_title || card.purpose || card.problem || `公式 ${index + 1}`, 72),
  }
}))

const orderedFormulaEntries = computed<FormulaEntry[]>(() => {
  const byId = new Map(formulaEntries.value.map(entry => [entry.id, entry]))
  const ordered = formulaOrder.value
    .map(id => byId.get(id))
    .filter((entry): entry is FormulaEntry => Boolean(entry))
  const orderedIds = new Set(ordered.map(entry => entry.id))
  return [
    ...ordered,
    ...formulaEntries.value.filter(entry => !orderedIds.has(entry.id)),
  ]
})

const activeFormulaEntry = computed(() => {
  return orderedFormulaEntries.value.find(entry => entry.id === activeFormulaAnchor.value)
    || orderedFormulaEntries.value[0]
    || null
})

const workspaceTitle = computed(() => {
  const title = paperCard.value?.title || paperCard.value?.paper_title
  return title || '论文深读'
})

const workspaceSubtitle = computed(() => {
  if (paperCard.value?.one_sentence_summary) return paperCard.value.one_sentence_summary
  if (paperCard.value?.thirty_second) return paperCard.value.thirty_second
  if (status.value === 'BASELINE_ONLY') return '当前只有基础解析产物。'
  if (status.value === 'BLOCKED_UNDERSTANDING') return '理解阶段被阻断，未展示半成品卡片。'
  return jobId
})

const readerMetrics = computed(() => [
  { label: '论文卡片', value: paperCard.value ? '已生成' : '缺失', tone: paperCard.value ? 'ready' : 'muted' },
  { label: '公式', value: `${formulaCardsList.value.length}`, tone: formulaCardsList.value.length ? 'ready' : 'muted' },
  { label: '教学卡片', value: `${teachingCards.value.length}`, tone: teachingCards.value.length ? 'ready' : 'muted' },
])

const statusRows = computed(() => {
  const details = paperWorkspaceStatus.value || {}
  const labels: Record<string, string> = {
    blocking_reason: '阻断原因',
    source_type: '来源类型',
    verification_status: '来源验证',
    pdf_metadata_check: 'PDF 元数据',
    pdf_title_match: '标题匹配',
    can_enter_m2: '可进入 M2',
    source_confidence: '来源置信度',
    canonicalization_status: '规范化',
    m2_ready: 'M2 准备',
    degradation_reason: '结构原因',
    formula_origin: '公式来源',
    formula_ocr_status: '公式 OCR',
    evidence_status: '证据包',
    quality_status: '质量审计',
  }
  const rows: Array<[string, any]> = [
    ['blocking_reason', understandingStatus.value?.blocking_reason],
    ['source_type', details.source_type],
    ['verification_status', details.verification_status],
    ['pdf_metadata_check', details.pdf_metadata_check],
    ['pdf_title_match', details.pdf_title_match],
    ['can_enter_m2', details.can_enter_m2],
    ['source_confidence', details.source_confidence],
    ['canonicalization_status', details.canonicalization_status],
    ['m2_ready', details.m2_ready],
    ['degradation_reason', details.degradation_reason],
    ['formula_origin', details.formula_origin],
    ['formula_ocr_status', details.formula_ocr_status],
    ['evidence_status', details.evidence_status],
    ['quality_status', details.quality_status],
  ]
  Object.entries(understandingStatus.value?.component_status || {}).forEach(([key, value]) => {
    rows.push([componentLabel(key), value])
  })
  return rows
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([label, value]) => [labels[label] || label, formatStatusValue(value)] as [string, any])
})

function componentLabel(key: string) {
  const labels: Record<string, string> = {
    paper_card: '论文卡片',
    formula_cards: '公式卡片',
    teaching_cards: '教学卡片',
    llm: '大模型',
    evidence_pack: '证据包',
  }
  return labels[key] || key
}

function formatStatusValue(value: any) {
  if (value === true) return '是'
  if (value === false) return '否'
  const text = String(value)
  const labels: Record<string, string> = {
    NO_LLM_CLIENT: '未连接大模型',
    PAPER_CARD_FAILED: '论文卡片失败',
    FORMULA_CARDS_FAILED: '公式卡片失败',
    TEACHING_CARDS_FAILED: '教学卡片失败',
    MISSING_METHOD_EVIDENCE: '缺少方法证据',
    EMPTY_EVIDENCE_PACK: '证据为空',
    FORMULA_DERIVATION_BLOCKED: '公式推导被阻断',
    local_path: '本地文件',
    upload: '上传文件',
    arxiv_source: 'arXiv 来源',
    m1_canonical_bundle: '规范化论文包',
    verified: '已验证',
    success: '成功',
    SUCCESS: '成功',
    pass: '通过',
    blocked: '已阻断',
    failed: '失败',
    FAILED: '失败',
    skipped: '已跳过',
    SKIPPED: '已跳过',
    warning: '需注意',
    BASELINE: '基础解析',
    not_available: '未提供',
    not_required: '无需 OCR',
    source_latex: '论文 LaTeX',
    mineru_latex: 'MinerU LaTeX',
    raw_formula_text: '原始公式文本',
  }
  return labels[text] || text
}

function normalizePaperCard(card: any): any {
  if (!card) return null
  return {
    ...card,
    thirty_second: card.one_sentence_summary || card.thirty_second || '',
    five_minute: [
      card.problem?.text,
      card.core_idea?.text,
      card.method_overview?.text,
    ].filter(Boolean).join(' '),
    deep_dive: card.experiment_summary?.text || '',
    evidence_status: card.evidence_status || paperWorkspaceStatus.value.evidence_status || 'UNKNOWN',
  }
}

function normalizeSkeleton(card: any): any {
  if (!card) return {}
  return {
    problem: { plain: card.problem?.text || '' },
    mechanism: { plain: card.method_overview?.text || '' },
  }
}

function isUsableFormulaCard(card: any) {
  const origin = String(card?.formula_origin || '').trim()
  const derivation = String(card?.derivation_status || '').trim()
  const coverage = String(card?.coverage_status || '').trim()
  if (origin === 'raw_formula_text' && (derivation === 'blocked' || coverage === 'BLOCKED_RAW_ONLY')) return false
  if (isNoisyFormulaText(card?.purpose) && isNoisyFormulaText(card?.plain_summary) && origin !== 'source_latex') return false
  return true
}

function normalizeFormulaCard(card: any, index = 0): any {
  if (!card) return card
  const displayTitle = formulaDisplayTitle(card, index)
  const noisyPurpose = isNoisyFormulaText(card.purpose)
  return {
    ...card,
    display_title: displayTitle,
    formula_latex: card.formula_latex || card.formula_raw || '',
    purpose: noisyPurpose ? displayTitle : (card.purpose || displayTitle),
    problem: card.problem || displayTitle,
    formula_ref: card.formula_ref || card.location || card.formula_id || '',
    remove_effect: card.remove_effect || card.what_if_removed || '',
    weight_change_effect: card.weight_change_effect || card.weight_sensitivity || '',
    plain_summary: card.plain_summary || card.intuition || '',
  }
}

function formulaDisplayTitle(card: any, index: number) {
  const candidates = [
    card.purpose,
    card.problem,
    card.plain_summary,
    card.formula_ref,
  ].map((value: unknown) => String(value || '').replace(/\s+/g, ' ').trim())
  const readable = candidates.find(value => value && !isNoisyFormulaText(value))
  if (readable) return readable
  const raw = String(card.formula_latex || card.formula_raw || '').replace(/\s+/g, ' ').trim()
  const hint = raw ? `：${clipLabel(raw, 28)}` : ''
  return `公式 ${index + 1} 来源不足，暂不推导${hint}`
}

function isNoisyFormulaText(value: unknown) {
  const text = String(value || '').trim()
  return !text
    || /^INSUFFICIENT_EVIDENCE\b/i.test(text)
    || /^UNKNOWN$/i.test(text)
    || /M2 preserved this formula slot/i.test(text)
    || /blocked detailed derivation/i.test(text)
    || /raw\/unknown formula text/i.test(text)
}

function clipLabel(value: unknown, maxLength: number) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text.length > maxLength ? `${text.slice(0, maxLength).trim()}...` : text
}

function formulaAnchor(formula: any, index: number) {
  const raw = String(formula?.formula_id || formula?.formula_ref || formula?.evidence_ref || index + 1)
  const safe = raw.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '')
  return `formula-${index + 1}-${safe || 'item'}`
}

function syncFormulaOrder() {
  const ids = formulaEntries.value.map(entry => entry.id)
  const known = new Set(ids)
  const kept = formulaOrder.value.filter(id => known.has(id))
  const missing = ids.filter(id => !kept.includes(id))
  formulaOrder.value = [...kept, ...missing]
}

function toggleFormulaCollapsed(id: string) {
  collapsedFormulas.value = {
    ...collapsedFormulas.value,
    [id]: !collapsedFormulas.value[id],
  }
}

function setAllFormulaCollapsed(collapsed: boolean) {
  collapsedFormulas.value = Object.fromEntries(
    formulaEntries.value.map(entry => [entry.id, collapsed]),
  )
}

function resetFormulaLayout() {
  formulaOrder.value = formulaEntries.value.map(entry => entry.id)
  collapsedFormulas.value = {}
}

function openFormulaFocus(card: any, index: number) {
  focusedFormula.value = { card, index }
}

function scrollToFormula(id: string) {
  activeFormulaAnchor.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function setupFormulaObserver() {
  formulaObserver?.disconnect()
  formulaObserver = null
  if (activeTab.value !== 'formulas' || !formulaCardsList.value.length || typeof IntersectionObserver === 'undefined') {
    return
  }
  void nextTick(() => {
    const nodes = formulaNavItems.value
      .map((item: { id: string }) => document.getElementById(item.id))
      .filter((node: HTMLElement | null): node is HTMLElement => Boolean(node))
    if (!nodes.length) return
    if (!activeFormulaAnchor.value) activeFormulaAnchor.value = nodes[0].id
    formulaObserver = new IntersectionObserver((entries) => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
      if (visible?.target.id) {
        activeFormulaAnchor.value = visible.target.id
      }
    }, { rootMargin: '-45% 0px -45% 0px', threshold: 0.01 })
    nodes.forEach((node: HTMLElement) => formulaObserver?.observe(node))
  })
}

function activateFirstAvailableTab() {
  if (paperCard.value) {
    activeTab.value = 'paper'
  } else if (formulaCardsList.value.length) {
    activeTab.value = 'formulas'
  } else if (teachingCards.value.length) {
    activeTab.value = 'teaching'
  }
}

async function loadWorkspace() {
  isLoading.value = true
  error.value = ''
  try {
    const statusRes = await fetch(`/api/v1/jobs/${jobId}/understanding_status`)
    if (!statusRes.ok) {
      error.value = statusRes.status === 404 ? '没有找到这个深读任务。' : '理解状态加载失败。'
      return
    }

    const statusData = await statusRes.json()
    understandingStatus.value = statusData.understanding_status
    paperWorkspaceStatus.value = statusData.paper_workspace_status || {}

    if (!canShowCards.value) return

    const cardsRes = await fetch(`/api/v1/jobs/${jobId}/cards`)
    if (cardsRes.ok) {
      const cardsData = await cardsRes.json()
      cards.value = cardsData.cards
      paperWorkspaceStatus.value = {
        ...paperWorkspaceStatus.value,
        ...(cardsData.paper_workspace_status || {}),
      }
      degraded.value = Boolean(cardsData.degraded)
      missingComponents.value = cardsData.missing_components || []
      activateFirstAvailableTab()
      return
    }

    if (cardsRes.status === 409) {
      const detail = await cardsRes.json().catch(() => ({}))
      error.value = detail.detail?.message || '卡片产物和理解状态不一致。'
      return
    }

    if (cardsRes.status === 403) {
      const detail = await cardsRes.json().catch(() => ({}))
      understandingStatus.value = {
        ...understandingStatus.value,
        status: detail.detail?.status || status.value,
        blocking_reason: detail.detail?.blocking_reason || understandingStatus.value?.blocking_reason || '',
        warnings: detail.detail?.warnings || understandingStatus.value?.warnings || [],
      }
    }
  } catch {
    error.value = '网络请求失败，请确认后端服务正在运行。'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  store.currentJobId = jobId
  void loadWorkspace()
})

watch([activeTab, formulaCardsList], () => setupFormulaObserver(), { flush: 'post' })
watch(formulaEntries, () => syncFormulaOrder(), { immediate: true })

onBeforeUnmount(() => {
  formulaObserver?.disconnect()
})
</script>

<template>
  <div
    class="workspace-shell"
    :class="{
      'with-chat': store.isAskPanelOpen && canShowCards,
      'formula-mode': activeTab === 'formulas',
    }"
  >
    <aside class="workspace-nav">
      <div class="nav-title">
        <strong>深读工作台</strong>
        <span>{{ jobId }}</span>
      </div>
      <nav>
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :disabled="tab.disabled"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span>{{ tab.label }}</span>
          <small>{{ tab.count }}</small>
        </button>
      </nav>
      <button
        v-if="canShowCards && !store.isAskPanelOpen"
        type="button"
        class="secondary-btn chat-open"
        @click="store.isAskPanelOpen = true"
      >
        打开 M4
      </button>
    </aside>

    <main class="reader-pane">
      <div v-if="isLoading" class="loading-state">
        正在加载论文工作台...
      </div>

      <div v-else-if="error" class="error-state">
        <strong>{{ error }}</strong>
        <button class="secondary-btn" @click="router.push('/')">回到首页</button>
      </div>

      <template v-else>
        <section class="reader-header">
          <div class="reader-title">
            <span>ResearchSensei</span>
            <h1>{{ workspaceTitle }}</h1>
            <p>{{ workspaceSubtitle }}</p>
          </div>
          <div v-if="canShowCards && !store.isAskPanelOpen" class="reader-actions">
            <button type="button" class="primary-btn" @click="store.isAskPanelOpen = true">
              打开 M4
            </button>
          </div>
        </section>

        <div v-if="canShowCards" class="reader-metrics" data-testid="reader-metrics">
          <div v-for="metric in readerMetrics" :key="metric.label" :class="metric.tone">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
        </div>

        <StatusBanner
          :status="status"
          :blockingReason="understandingStatus?.blocking_reason"
          :warnings="understandingStatus?.warnings"
          :missingComponents="missingComponents"
          :paperWorkspaceStatus="paperWorkspaceStatus"
          :componentStatus="understandingStatus?.component_status"
          :allowedDownstream="understandingStatus?.allowed_downstream"
        />

        <details class="status-details">
          <summary>查看技术状态</summary>
          <dl>
            <div v-for="[label, value] in statusRows" :key="String(label)">
              <dt>{{ label }}</dt>
              <dd>{{ String(value) }}</dd>
            </div>
          </dl>
        </details>

        <section v-if="canShowCards" class="card-stack" :class="{ 'formula-stack': activeTab === 'formulas' }">
          <PaperCard
            v-if="activeTab === 'paper' && paperCard"
            :card="normalizePaperCard(paperCard)"
            :skeleton="normalizeSkeleton(paperCard)"
          />

          <template v-else-if="activeTab === 'formulas'">
            <template v-if="formulaCardsList.length > 0">
              <div class="formula-workspace">
                <section class="formula-reader">
                  <section class="formula-board-toolbar surface" aria-label="公式阅读器">
                    <div>
                      <strong>公式阅读器</strong>
                      <span>按正文顺序阅读；当前公式会在右侧停靠，滚动时公式标题会留在顶部。</span>
                    </div>
                    <button type="button" class="secondary-btn" @click="resetFormulaLayout">重置</button>
                  </section>

                  <div class="formula-list" data-testid="formula-board">
                    <article
                      v-for="entry in orderedFormulaEntries"
                      :id="entry.id"
                      :key="entry.id"
                      class="formula-board-card"
                      :class="{
                        collapsed: collapsedFormulas[entry.id],
                        active: activeFormulaAnchor === entry.id,
                      }"
                      data-testid="formula-board-card"
                    >
                      <header class="formula-card-bar">
                        <div class="formula-card-number">{{ entry.index }}</div>
                        <div>
                          <span>公式 {{ entry.index }}</span>
                          <strong>{{ entry.title }}</strong>
                        </div>
                        <div class="formula-card-actions">
                          <button type="button" @click="openFormulaFocus(entry.card, entry.index)">单独查看</button>
                          <button type="button" @click="toggleFormulaCollapsed(entry.id)">
                            {{ collapsedFormulas[entry.id] ? '展开' : '折叠' }}
                          </button>
                        </div>
                      </header>
                      <FormulaCard v-if="!collapsedFormulas[entry.id]" :card="entry.card" />
                    </article>
                  </div>
                </section>

                <aside class="formula-rail surface" :class="{ collapsed: formulaRailCollapsed }" aria-label="当前公式与目录">
                  <button type="button" class="rail-toggle" @click="formulaRailCollapsed = !formulaRailCollapsed">
                    {{ formulaRailCollapsed ? `公式 ${activeFormulaEntry?.index || '…'}` : '收起' }}
                  </button>
                  <template v-if="!formulaRailCollapsed">
                  <section v-if="activeFormulaEntry" class="active-formula-card">
                    <span>当前公式</span>
                    <strong>{{ activeFormulaEntry.title }}</strong>
                    <small>公式 {{ activeFormulaEntry.index }}</small>
                    <div class="active-formula-actions">
                      <button type="button" @click="openFormulaFocus(activeFormulaEntry.card, activeFormulaEntry.index)">点开看</button>
                      <button type="button" @click="scrollToFormula(activeFormulaEntry.id)">回到正文</button>
                    </div>
                  </section>

                  <nav class="formula-index" data-testid="formula-index" aria-label="公式目录">
                    <header>
                      <div>
                        <strong>公式目录</strong>
                        <small>{{ formulaCardsList.length }} 张卡片</small>
                      </div>
                      <div class="formula-index-actions">
                        <button type="button" @click="setAllFormulaCollapsed(true)">折叠</button>
                        <button type="button" @click="setAllFormulaCollapsed(false)">展开</button>
                      </div>
                    </header>
                    <div class="formula-index-list">
                      <button
                        v-for="item in formulaNavItems"
                        :key="item.id"
                        type="button"
                        :class="{ active: activeFormulaAnchor === item.id }"
                        :title="item.title"
                        @click="scrollToFormula(item.id)"
                      >
                        <b>{{ item.index }}</b>
                        <span>{{ item.title }}</span>
                      </button>
                    </div>
                  </nav>
                  </template>
                </aside>
              </div>
            </template>
            <div v-else class="empty-card" data-testid="formula-degraded-message">
              <h2>公式拆解暂时不可用</h2>
              <p>
                当前公式来源不足以生成可信推导。系统没有把它伪装成完整解释；
                原因是 {{ paperWorkspaceStatus.degradation_reason || 'FORMULA_DERIVATION_BLOCKED' }}。
              </p>
              <p v-if="hiddenRawFormulaCount > 0">
                已隐藏 {{ hiddenRawFormulaCount }} 条不完整的原始公式残片。
              </p>
              <span v-if="paperWorkspaceStatus.formula_origin">公式来源：{{ paperWorkspaceStatus.formula_origin }}</span>
            </div>
          </template>

          <div v-else-if="activeTab === 'teaching'" class="teaching-list" data-testid="teaching-cards">
            <article v-for="card in teachingCards" :key="card.card_id || card.title" class="surface teaching-card">
              <div>
                <strong>{{ card.title || card.target_type || '教学卡片' }}</strong>
                <span>{{ card.card_type || card.target_type || 'concept' }}</span>
              </div>
              <p>{{ card.human_explanation }}</p>
              <small>证据：{{ card.evidence_refs?.join('，') || card.evidence_ref || '未标注' }}</small>
            </article>
          </div>
        </section>

        <section v-else class="no-cards surface" data-testid="no-cards-state">
          <h2>没有展示用户卡片</h2>
          <p>{{ noCardsMessage }}</p>
        </section>
      </template>
    </main>

    <Transition name="slide-right">
      <aside v-if="store.isAskPanelOpen && canShowCards" class="chat-pane">
        <AskPanel />
      </aside>
    </Transition>

    <button
      v-if="canShowCards && !store.isAskPanelOpen"
      type="button"
      class="chat-fab"
      @click="store.isAskPanelOpen = true"
    >
      M4
    </button>

    <TextSelectionToolbar v-if="canShowCards" />

    <Teleport to="body">
      <div
        v-if="focusedFormula"
        class="formula-focus-backdrop"
        role="presentation"
        @click.self="focusedFormula = null"
      >
        <section class="formula-focus-dialog" role="dialog" aria-modal="true" aria-label="单独查看公式">
          <header>
            <div>
              <span>公式 {{ focusedFormula.index }}</span>
              <strong>{{ focusedFormula.card.display_title || focusedFormula.card.purpose || '公式卡片' }}</strong>
            </div>
            <button type="button" aria-label="关闭" @click="focusedFormula = null">×</button>
          </header>
          <FormulaCard :card="focusedFormula.card" />
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.workspace-shell {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  min-height: 100%;
  height: 100%;
  background: var(--bg-primary);
}

.workspace-shell.with-chat {
  grid-template-columns: 210px minmax(0, 1fr);
}

.workspace-shell.formula-mode {
  grid-template-columns: 166px minmax(0, 1fr);
}

.workspace-shell.formula-mode.with-chat {
  grid-template-columns: 166px minmax(0, 1fr);
}

.workspace-nav {
  position: sticky;
  top: 0;
  height: 100%;
  border-right: 1px solid var(--border-subtle);
  padding: 12px 10px;
  background: var(--bg-secondary);
}

.nav-title {
  display: grid;
  gap: 4px;
  margin-bottom: 18px;
  padding: 0 6px;
}

.nav-title strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
}

.nav-title span {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-nav nav {
  display: grid;
  gap: 3px;
}

.workspace-nav nav button {
  display: flex;
  min-height: 38px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-radius: 8px;
  padding: 8px 10px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.workspace-nav nav button.active,
.workspace-nav nav button:hover:not(:disabled) {
  background: var(--bg-card);
  color: var(--text-primary);
}

.workspace-nav nav button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.workspace-nav nav small {
  color: inherit;
  font-size: 12px;
}

.chat-open {
  width: 100%;
  margin-top: 18px;
}

.reader-pane {
  height: 100%;
  min-width: 0;
  padding: 34px clamp(18px, 4vw, 44px) 56px;
  overflow-y: auto;
}

.workspace-shell.formula-mode .reader-pane {
  padding-inline: clamp(16px, 2.2vw, 28px);
}

.reader-header {
  display: grid;
  max-width: 860px;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 18px;
  margin: 0 auto 14px;
}

.reader-title {
  min-width: 0;
}

.reader-title > span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0;
}

.reader-title h1 {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 26px;
  font-weight: 720;
  line-height: 1.28;
  overflow-wrap: anywhere;
}

.reader-title p {
  margin-top: 8px;
  max-width: 780px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.72;
}

.reader-actions {
  display: flex;
  justify-content: flex-end;
}

.reader-metrics {
  display: grid;
  max-width: 860px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0 auto 16px;
}

.reader-metrics > div {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 9px 11px;
  background: var(--bg-card);
}

.reader-metrics span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.reader-metrics strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
}

.reader-metrics .ready strong {
  color: var(--success);
}

.reader-metrics .muted {
  opacity: 0.68;
}

.loading-state,
.error-state,
.no-cards,
.empty-card {
  max-width: 780px;
  margin: 70px auto 0;
  border-radius: 8px;
  padding: 28px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.8;
}

.error-state {
  display: grid;
  gap: 16px;
  border: 1px solid rgba(220, 38, 38, 0.18);
  background: rgba(220, 38, 38, 0.07);
  color: var(--danger);
}

.status-details {
  max-width: 860px;
  margin: 16px auto 24px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.status-details summary {
  cursor: pointer;
  padding: 13px 16px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.status-details dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  border-top: 1px solid var(--border-subtle);
  padding: 14px 16px 16px;
}

.status-details div {
  min-width: 0;
  border-radius: 8px;
  padding: 9px 10px;
  background: var(--bg-secondary);
}

.status-details dt {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.status-details dd {
  overflow-wrap: anywhere;
  margin-top: 3px;
  color: var(--text-primary);
  font-size: 13px;
}

.card-stack {
  display: grid;
  max-width: 860px;
  margin: 0 auto;
  gap: 18px;
}

.card-stack.formula-stack {
  max-width: min(1180px, 100%);
}

.formula-workspace {
  display: grid;
  grid-template-columns: minmax(0, 790px) minmax(240px, 300px);
  align-items: start;
  justify-content: center;
  gap: 18px;
}

.formula-reader {
  display: grid;
  min-width: 0;
  gap: 14px;
}

.formula-rail {
  position: sticky;
  top: 16px;
  display: grid;
  max-height: calc(100vh - 32px);
  min-width: 0;
  gap: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0;
}

.formula-rail.collapsed {
  width: 72px;
  min-width: 72px;
  height: 48px;
  min-height: 48px;
  overflow: hidden;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.formula-rail.collapsed .rail-toggle {
  position: static;
  width: 100%;
  height: 100%;
  border: 0;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 13px;
  font-weight: 720;
  border-radius: 12px;
  cursor: pointer;
}

.rail-toggle {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 3px 10px;
  background: var(--bg-card);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
}

.rail-toggle:hover {
  color: var(--text-primary);
  border-color: var(--text-muted);
}

.formula-list {
  display: grid;
  min-width: 0;
  gap: 18px;
}

.formula-index {
  z-index: 1;
  display: grid;
  gap: 10px;
  padding: 12px;
  background: transparent;
  overscroll-behavior: contain;
}

.formula-index header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 2px 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.formula-index header strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
}

.formula-index header small,
.formula-board-toolbar span {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.formula-index-actions,
.formula-card-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.formula-index-actions button,
.formula-card-actions button {
  min-height: 28px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  padding: 0 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.formula-index-actions button:hover,
.formula-card-actions button:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.formula-index-list {
  display: grid;
  gap: 3px;
  max-height: none;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 0 2px 4px 0;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
}

.formula-index-list::-webkit-scrollbar {
  width: 5px;
}

.formula-index-list::-webkit-scrollbar-track {
  background: transparent;
}

.formula-index-list::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: 4px;
}

.formula-index-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.formula-index button {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  width: 100%;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  border-radius: 8px;
  padding: 7px 8px;
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
}

.formula-index button:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.formula-index button.active {
  background: var(--accent-light);
  color: var(--text-primary);
}

.formula-index button.active b {
  background: var(--accent);
  color: var(--accent-contrast);
}

.formula-index b {
  display: flex;
  width: 24px;
  height: 24px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--bg-secondary);
  color: inherit;
  font-size: 12px;
}

.formula-index button span {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.formula-anchor {
  scroll-margin-top: 18px;
}

.formula-board-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}

.formula-board-toolbar strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
}

.active-formula-card {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-bottom: 1px solid var(--border-subtle);
  background: color-mix(in srgb, var(--bg-card) 96%, var(--bg-secondary));
}

@media (min-width: 1121px) {
  .formula-rail {
    position: fixed;
    top: 88px;
    right: 28px;
    z-index: 70;
    width: 300px;
    max-height: calc(100vh - 112px);
    overflow-y: auto;
    box-shadow: var(--shadow-md);
  }
}

.workspace-shell.with-chat .formula-rail {
  position: fixed;
  top: 88px;
  right: 396px;
  width: 280px;
  max-height: calc(100vh - 112px);
  overflow-y: auto;
  z-index: 70;
}

.workspace-shell.with-chat .formula-workspace {
  grid-template-columns: minmax(0, 1fr);
}

.active-formula-card > span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.active-formula-card strong {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 720;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.active-formula-card small {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.active-formula-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
  margin-top: 4px;
}

.active-formula-actions button {
  min-height: 32px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.active-formula-actions button:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.formula-board-card {
  position: relative;
  display: block;
  min-width: 0;
  overflow: visible;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
  scroll-margin-top: 18px;
  transition: border-color 0.14s ease, box-shadow 0.14s ease;
}

.formula-board-card.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 12%, transparent);
}

.formula-board-card :deep(.formula-card) {
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.formula-card-bar {
  position: sticky;
  top: 0;
  z-index: 12;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--border-subtle);
  border-radius: 10px 10px 0 0;
  padding: 11px 12px;
  background: color-mix(in srgb, var(--bg-card) 92%, transparent);
  backdrop-filter: blur(12px);
}

.formula-card-number {
  display: flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--accent);
  color: var(--accent-contrast);
  font-size: 12px;
  font-weight: 720;
}

.formula-card-bar > div {
  min-width: 0;
}

.formula-card-bar span {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.formula-card-bar strong {
  display: block;
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.formula-board-card.collapsed .formula-card-bar {
  border-bottom: 0;
}

.formula-focus-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(20, 20, 18, 0.34);
  backdrop-filter: blur(8px);
}

.formula-focus-dialog {
  width: min(920px, calc(100vw - 32px));
  max-height: min(86vh, 900px);
  overflow: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--bg-card);
  box-shadow: 0 28px 90px rgba(18, 18, 16, 0.26);
}

.formula-focus-dialog > header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 12px 14px;
  background: var(--bg-card);
}

.formula-focus-dialog header div {
  min-width: 0;
}

.formula-focus-dialog header span {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.formula-focus-dialog header strong {
  display: block;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 720;
  overflow-wrap: anywhere;
}

.formula-focus-dialog header button {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 18px;
}

.empty-card h2,
.no-cards h2 {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 720;
}

.empty-card p,
.no-cards p {
  margin-top: 8px;
}

.empty-card span {
  display: block;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 14px;
}

.teaching-list {
  display: grid;
  gap: 14px;
}

.teaching-card {
  padding: 18px;
}

.teaching-card div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.teaching-card strong {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
}

.teaching-card span {
  border-radius: 999px;
  padding: 4px 8px;
  background: var(--accent-light);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 650;
}

.teaching-card p {
  margin-top: 10px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.8;
}

.teaching-card small {
  display: block;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.chat-pane {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  z-index: 100;
  height: 100dvh;
  border-left: 1px solid var(--border-subtle);
  background: var(--bg-card);
}

.chat-fab {
  position: fixed;
  right: 20px;
  bottom: 22px;
  z-index: 80;
  display: flex;
  width: 54px;
  height: 54px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--accent);
  color: var(--accent-contrast);
  box-shadow: var(--shadow-lg);
  font-weight: 720;
}

@media (max-width: 1120px) {
  .workspace-shell,
  .workspace-shell.with-chat,
  .workspace-shell.formula-mode,
  .workspace-shell.formula-mode.with-chat {
    grid-template-columns: 1fr;
  }

  .workspace-nav {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--border-subtle);
  }

  .reader-pane {
    height: auto;
    min-height: 100%;
    overflow-y: visible;
  }

  .reader-header {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .reader-actions {
    justify-content: flex-start;
  }

  .workspace-nav nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .chat-pane {
    position: fixed;
    inset: 62px 14px 14px;
    z-index: 90;
    height: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
  }

  .formula-workspace {
    grid-template-columns: 1fr;
  }

  .formula-rail {
    position: static;
    order: -1;
    max-height: none;
    overflow: visible;
  }

  .formula-index-list {
    display: flex;
    max-height: none;
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 6px;
  }

  .formula-index button {
    width: min(72vw, 220px);
    flex: 0 0 auto;
    min-height: 34px;
  }

  .formula-index b {
    width: 20px;
    height: 20px;
    font-size: 11px;
  }
}

@media (max-width: 720px) {
  .workspace-nav nav {
    grid-template-columns: 1fr;
  }

  .reader-pane {
    padding-inline: 14px;
  }

  .reader-title h1 {
    font-size: 23px;
  }

  .reader-metrics {
    grid-template-columns: 1fr;
  }

  .chat-fab {
    display: none;
  }

  .status-details dl {
    grid-template-columns: 1fr;
  }
}
</style>

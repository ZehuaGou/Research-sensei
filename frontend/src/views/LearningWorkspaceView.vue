<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { useLearningStore } from '../stores/learning'
import { useWorkspaceData } from '../composables/useWorkspaceData'
import { useWorkspaceTabs } from '../composables/useWorkspaceTabs'
import { useFormulaDock } from '../composables/useFormulaDock'
import { useChatPaneResize } from '../composables/useChatPaneResize'
import AskPanel from '../components/layout/AskPanel.vue'
import TextSelectionToolbar from '../components/interactive/TextSelectionToolbar.vue'
import PaperCardComponent from '../components/cards/PaperCard.vue'
import FormulaCardComponent from '../components/cards/FormulaCard.vue'
import FormulaWorkspace from '../components/workspace/FormulaWorkspace.vue'
import FormulaDock from '../components/workspace/FormulaDock.vue'
import WorkspaceStatusPanel from '../components/workspace/WorkspaceStatusPanel.vue'
import type { FormulaEntry, WorkspaceTab, WorkspaceTabItem } from '../types/workspace'
import {
  formulaEntries as createFormulaEntries,
  normalizePaperCard,
  normalizePaperSkeleton,
} from '../utils/workspaceCards'

const route = useRoute()
const router = useRouter()
const store = useLearningStore()
const { isAskPanelOpen } = storeToRefs(store)
const jobId = String(route.params.jobId || '')
const readerPaneRef = ref<HTMLElement | null>(null)
const chatPaneRef = ref<HTMLElement | null>(null)
const formulaDialogRef = ref<HTMLElement | null>(null)
const topbarTargetReady = ref(false)
const activeFormulaAnchor = ref('')
const formulaOrder = ref<string[]>([])
const collapsedFormulas = ref<Record<string, boolean>>({})
const focusedFormula = ref<FormulaEntry | null>(null)
let formulaObserver: IntersectionObserver | null = null
let formulaRestoreFocusElement: HTMLElement | null = null
let m4RestoreFocusElement: HTMLElement | null = null

const workspace = useWorkspaceData(jobId)
const tabsState = useWorkspaceTabs(jobId, readerPaneRef)
const chatResize = useChatPaneResize()
const formulaDock = useFormulaDock({
  activeTab: tabsState.activeTab,
  isAskPanelOpen,
  canShowCards: workspace.canShowCards,
  chatPaneWidth: chatResize.width,
})

const formulaEntries = computed(() => createFormulaEntries(workspace.formulaCards.value))
const orderedFormulaEntries = computed<FormulaEntry[]>(() => {
  const byId = new Map(formulaEntries.value.map(entry => [entry.id, entry]))
  const ordered = formulaOrder.value.map(id => byId.get(id)).filter((entry): entry is FormulaEntry => Boolean(entry))
  const orderedIds = new Set(ordered.map(entry => entry.id))
  return [...ordered, ...formulaEntries.value.filter(entry => !orderedIds.has(entry.id))]
})
const formulaTabDisabled = computed(() => !workspace.formulaCards.value.length && workspace.status.value !== 'DEGRADED_STRUCTURAL')
const tabs = computed<WorkspaceTabItem[]>(() => [
  { key: 'paper', label: '论文概览', count: workspace.paperCard.value ? 1 : 0, disabled: !workspace.paperCard.value },
  { key: 'formulas', label: '公式拆解', count: workspace.formulaCards.value.length, disabled: formulaTabDisabled.value },
  { key: 'teaching', label: '教学卡片', count: workspace.teachingCards.value.length, disabled: !workspace.teachingCards.value.length },
])
const workspaceTitle = computed(() => workspace.paperCard.value?.title || workspace.paperCard.value?.paper_title || '论文深读')
const workspaceSubtitle = computed(() => {
  if (workspace.paperCard.value?.one_sentence_summary) return workspace.paperCard.value.one_sentence_summary
  if (workspace.paperCard.value?.thirty_second) return workspace.paperCard.value.thirty_second
  if (workspace.status.value === 'BASELINE_ONLY') return '当前只有基础解析产物。'
  if (workspace.status.value === 'BLOCKED_UNDERSTANDING') return '理解阶段被阻断，未展示半成品卡片。'
  return jobId
})
const noCardsMessage = computed(() => {
  if (workspace.status.value === 'BASELINE_ONLY' && workspace.understandingStatus.value?.blocking_reason === 'NO_LLM_CLIENT') {
    return '这次运行没有接入实时大模型，所以只保留基础诊断，不展示用户可读卡片。请确认 ccswitch 正在运行、环境变量已启用，然后重新深读。'
  }
  if (workspace.status.value === 'BLOCKED_UNDERSTANDING') {
    return '理解阶段被阻断。系统没有展示半成品卡片，请查看上方状态原因后重新运行。'
  }
  return '当前状态没有可展示的用户卡片。'
})

function activateFirstAvailableTab() {
  if (workspace.paperCard.value) tabsState.activate('paper')
  else if (workspace.formulaCards.value.length) tabsState.activate('formulas')
  else if (workspace.teachingCards.value.length) tabsState.activate('teaching')
}

async function switchTab(tab: WorkspaceTab) {
  await tabsState.switchTab(tab)
}

async function handleWorkspaceTabKeydown(event: KeyboardEvent, currentTab: WorkspaceTab) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  const enabledTabs = tabs.value.filter(tab => !tab.disabled)
  if (!enabledTabs.length) return
  const currentIndex = Math.max(0, enabledTabs.findIndex(tab => tab.key === currentTab))
  const nextIndex = event.key === 'Home'
    ? 0
    : event.key === 'End'
      ? enabledTabs.length - 1
      : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + enabledTabs.length) % enabledTabs.length
  const nextTab = enabledTabs[nextIndex]
  event.preventDefault()
  await switchTab(nextTab.key)
  document.getElementById(`workspace-tab-${nextTab.key}`)?.focus()
}

function syncFormulaOrder() {
  const ids = formulaEntries.value.map(entry => entry.id)
  const known = new Set(ids)
  const kept = formulaOrder.value.filter(id => known.has(id))
  formulaOrder.value = [...kept, ...ids.filter(id => !kept.includes(id))]
}

function toggleFormulaCollapsed(id: string) {
  collapsedFormulas.value = { ...collapsedFormulas.value, [id]: !collapsedFormulas.value[id] }
}

function setAllFormulaCollapsed(collapsed: boolean) {
  collapsedFormulas.value = Object.fromEntries(formulaEntries.value.map(entry => [entry.id, collapsed]))
}

function resetFormulaLayout() {
  formulaOrder.value = formulaEntries.value.map(entry => entry.id)
  collapsedFormulas.value = {}
}

function openFormulaFocus(entry: FormulaEntry) {
  focusedFormula.value = entry
}

function closeFormulaFocus() {
  focusedFormula.value = null
}

function scrollToFormula(id: string) {
  activeFormulaAnchor.value = id
  const pane = readerPaneRef.value
  const target = document.getElementById(id)
  if (!pane || !target) return
  const paneRect = pane.getBoundingClientRect()
  const targetRect = target.getBoundingClientRect()
  pane.scrollTo({ top: pane.scrollTop + targetRect.top - paneRect.top - 16, behavior: 'smooth' })
}

function setupFormulaObserver() {
  formulaObserver?.disconnect()
  formulaObserver = null
  if (tabsState.activeTab.value !== 'formulas' || !workspace.formulaCards.value.length || typeof IntersectionObserver === 'undefined') return
  void nextTick(() => {
    const root = readerPaneRef.value
    if (!root) return
    const nodes = orderedFormulaEntries.value
      .map(entry => document.getElementById(entry.id))
      .filter((node): node is HTMLElement => Boolean(node))
    if (!nodes.length) return
    if (!activeFormulaAnchor.value) activeFormulaAnchor.value = nodes[0].id
    formulaObserver = new IntersectionObserver(entries => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top)[0]
      if (visible?.target.id) activeFormulaAnchor.value = visible.target.id
    }, { root, rootMargin: '-35% 0px -55% 0px', threshold: 0.01 })
    nodes.forEach(node => formulaObserver?.observe(node))
  })
}

async function reparseCurrentPaper() {
  const nextJobId = await workspace.reparseCurrentPaper()
  if (nextJobId) window.location.assign(`/learn/${encodeURIComponent(nextJobId)}`)
}

function closeM4() {
  isAskPanelOpen.value = false
}

function handleDialogKeys(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    if (focusedFormula.value) {
      event.preventDefault()
      closeFormulaFocus()
    } else if (chatResize.compactViewport.value && isAskPanelOpen.value) {
      event.preventDefault()
      closeM4()
    }
    return
  }
  if (event.key !== 'Tab') return
  const activeDialog = focusedFormula.value ? formulaDialogRef.value : (
    chatResize.compactViewport.value && isAskPanelOpen.value ? chatPaneRef.value : null
  )
  if (activeDialog) trapFocus(event, activeDialog)
}

function trapFocus(event: KeyboardEvent, container: HTMLElement) {
  const focusable = Array.from(container.querySelectorAll<HTMLElement>(
    'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )).filter(element => !element.hasAttribute('hidden'))
  if (!focusable.length) {
    event.preventDefault()
    container.focus()
    return
  }
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(formulaEntries, syncFormulaOrder, { immediate: true })
watch([tabsState.activeTab, workspace.formulaCards], setupFormulaObserver, { flush: 'post' })
watch(focusedFormula, async value => {
  if (value) {
    formulaRestoreFocusElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
    await nextTick()
    formulaDialogRef.value?.querySelector<HTMLElement>('[data-dialog-close]')?.focus()
  } else {
    formulaRestoreFocusElement?.focus()
    formulaRestoreFocusElement = null
  }
})
watch([isAskPanelOpen, chatResize.compactViewport], async ([open, compact]) => {
  if (open && compact && !focusedFormula.value) {
    m4RestoreFocusElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
    await nextTick()
    chatPaneRef.value?.focus()
  } else if (!open) {
    const target = m4RestoreFocusElement
    m4RestoreFocusElement = null
    await nextTick()
    if (target?.isConnected) target.focus()
    else document.querySelector<HTMLElement>('[data-testid="m4-open"]')?.focus()
  }
})

onMounted(async () => {
  store.currentJobId = jobId
  topbarTargetReady.value = Boolean(document.getElementById('workbench-topbar-center'))
  document.addEventListener('keydown', handleDialogKeys)
  await workspace.loadWorkspace()
  activateFirstAvailableTab()
  await tabsState.restoreCurrentScroll()
})

onBeforeUnmount(() => {
  tabsState.saveCurrentScroll()
  formulaObserver?.disconnect()
  document.removeEventListener('keydown', handleDialogKeys)
})
</script>

<template>
  <Teleport to="#workbench-topbar-center" :disabled="!topbarTargetReady">
    <nav class="learning-topbar-tabs" role="tablist" aria-label="深读页面切换" data-testid="learning-topbar-tabs">
      <button
        v-for="tab in tabs"
        :id="`workspace-tab-${tab.key}`"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="tabsState.activeTab.value === tab.key"
        :aria-controls="`workspace-panel-${tab.key}`"
        :tabindex="tabsState.activeTab.value === tab.key ? 0 : -1"
        :disabled="tab.disabled"
        :class="{ active: tabsState.activeTab.value === tab.key }"
        @click="switchTab(tab.key)"
        @keydown="handleWorkspaceTabKeydown($event, tab.key)"
      >
        <span>{{ tab.label }}</span>
        <small>{{ tab.count }}</small>
      </button>
    </nav>
  </Teleport>

  <div
    class="workspace-shell"
    data-testid="learning-workspace"
    :class="{
      'with-chat': isAskPanelOpen && workspace.canShowCards.value && !chatResize.compactViewport.value,
      'formula-mode': tabsState.activeTab.value === 'formulas' && workspace.formulaCards.value.length > 0,
    }"
    :style="chatResize.shellStyle.value"
  >
    <main ref="readerPaneRef" class="reader-pane" data-testid="reader-pane">
      <div v-if="workspace.isLoading.value" class="loading-state">正在加载论文工作台...</div>

      <div v-else-if="workspace.error.value" class="error-state" role="alert">
        <strong>{{ workspace.error.value }}</strong>
        <button class="secondary-btn" @click="router.push('/')">回到首页</button>
      </div>

      <template v-else>
        <section class="reader-header">
          <div class="reader-title">
            <span>ResearchSensei</span>
            <h1>{{ workspaceTitle }}</h1>
            <p>{{ workspaceSubtitle }}</p>
          </div>
          <div v-if="workspace.canShowCards.value" class="reader-actions">
            <button type="button" class="secondary-btn" :disabled="workspace.isReparsing.value" @click="reparseCurrentPaper">
              {{ workspace.isReparsing.value ? '重新解析中' : '重新解析' }}
            </button>
            <button
              v-if="!isAskPanelOpen"
              type="button"
              class="primary-btn"
              data-testid="m4-open"
              aria-controls="m4-chat-pane"
              :aria-expanded="isAskPanelOpen"
              @click="isAskPanelOpen = true"
            >
              打开 M4
            </button>
          </div>
        </section>

        <WorkspaceStatusPanel
          :understanding-status="workspace.understandingStatus.value"
          :paper-workspace-status="workspace.paperWorkspaceStatus.value"
          :missing-components="workspace.missingComponents.value"
          :paper-card-count="workspace.paperCard.value ? 1 : 0"
          :formula-count="workspace.formulaCards.value.length"
          :teaching-count="workspace.teachingCards.value.length"
        />

        <section v-if="workspace.canShowCards.value" class="card-stack" :class="{ 'formula-stack': tabsState.activeTab.value === 'formulas' }">
          <div
            v-show="tabsState.activeTab.value === 'paper'"
            id="workspace-panel-paper"
            role="tabpanel"
            aria-labelledby="workspace-tab-paper"
            tabindex="0"
          >
            <PaperCardComponent
              v-if="workspace.paperCard.value"
              :card="normalizePaperCard(workspace.paperCard.value, workspace.paperWorkspaceStatus.value)"
              :skeleton="normalizePaperSkeleton(workspace.paperCard.value)"
            />
          </div>

          <div
            v-show="tabsState.activeTab.value === 'formulas'"
            id="workspace-panel-formulas"
            role="tabpanel"
            aria-labelledby="workspace-tab-formulas"
            tabindex="0"
          >
            <FormulaWorkspace
              v-if="workspace.formulaCards.value.length"
              :entries="orderedFormulaEntries"
              :collapsed="collapsedFormulas"
              :active-id="activeFormulaAnchor"
              @reset="resetFormulaLayout"
              @focus="openFormulaFocus"
              @toggle="toggleFormulaCollapsed"
            />
            <div v-else class="empty-card" data-testid="formula-degraded-message">
              <h2>公式拆解暂时不可用</h2>
              <p>
                当前公式来源不足以生成可信推导。系统没有把它伪装成完整解释，
                原因是 {{ workspace.paperWorkspaceStatus.value.degradation_reason || 'FORMULA_DERIVATION_BLOCKED' }}。
              </p>
              <p v-if="workspace.hiddenRawFormulaCount.value">已隐藏 {{ workspace.hiddenRawFormulaCount.value }} 条不完整的原始公式残片。</p>
              <span v-if="workspace.paperWorkspaceStatus.value.formula_origin">公式来源：{{ workspace.paperWorkspaceStatus.value.formula_origin }}</span>
            </div>
          </div>

          <div
            v-show="tabsState.activeTab.value === 'teaching'"
            id="workspace-panel-teaching"
            role="tabpanel"
            aria-labelledby="workspace-tab-teaching"
            tabindex="0"
            class="teaching-list"
            data-testid="teaching-cards"
          >
            <article v-for="card in workspace.teachingCards.value" :key="card.card_id || card.title" class="surface teaching-card">
              <div>
                <strong>{{ card.title || card.target_type || '教学卡片' }}</strong>
                <span>{{ card.card_type || card.target_type || 'concept' }}</span>
              </div>
              <p>{{ card.human_explanation }}</p>
              <small>证据：{{ card.evidence_refs?.join('、') || card.evidence_ref || '未标注' }}</small>
            </article>
          </div>
        </section>

        <section v-else class="no-cards surface" data-testid="no-cards-state">
          <h2>没有展示用户卡片</h2>
          <p>{{ noCardsMessage }}</p>
        </section>
      </template>
    </main>

    <FormulaDock
      v-if="tabsState.activeTab.value === 'formulas' && workspace.formulaCards.value.length && !formulaDock.hiddenForCompactChat.value"
      :entries="orderedFormulaEntries"
      :active-id="activeFormulaAnchor"
      :collapsed="formulaDock.collapsed.value"
      :dragging="formulaDock.dragging.value"
      :style="formulaDock.style.value"
      @register="formulaDock.registerDock"
      @drag-start="formulaDock.startDrag"
      @key-move="formulaDock.handleKeyboardMove"
      @toggle="formulaDock.toggleCollapsed"
      @reset-position="formulaDock.resetPosition"
      @focus="openFormulaFocus"
      @scroll="scrollToFormula"
      @collapse-all="setAllFormulaCollapsed"
    />

    <aside
      v-if="isAskPanelOpen && workspace.canShowCards.value && !chatResize.compactViewport.value"
      id="m4-chat-pane"
      ref="chatPaneRef"
      class="chat-pane"
      data-testid="m4-chat-pane"
      aria-label="M4 论文助教"
    >
      <div
        class="chat-resize-handle"
        data-testid="m4-resize-handle"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整 M4 宽度"
        aria-valuemin="320"
        aria-valuemax="540"
        :aria-valuenow="Math.round(chatResize.width.value)"
        tabindex="0"
        @pointerdown="chatResize.startResize"
        @keydown="chatResize.handleSeparatorKeydown"
      />
      <AskPanel />
    </aside>

    <div
      v-if="isAskPanelOpen && workspace.canShowCards.value && chatResize.compactViewport.value"
      class="chat-overlay"
      role="presentation"
      @click.self="closeM4"
    >
      <aside
        id="m4-chat-pane"
        ref="chatPaneRef"
        class="chat-pane compact"
        data-testid="m4-chat-pane"
        role="dialog"
        aria-modal="true"
        aria-label="M4 论文助教"
        tabindex="-1"
      >
        <AskPanel />
      </aside>
    </div>

    <button
      v-if="workspace.canShowCards.value && !isAskPanelOpen"
      type="button"
      class="chat-fab"
      data-testid="m4-open"
      aria-controls="m4-chat-pane"
      :aria-expanded="isAskPanelOpen"
      @click="isAskPanelOpen = true"
    >
      M4
    </button>

    <TextSelectionToolbar v-if="workspace.canShowCards.value" />

    <Teleport to="body">
      <div v-if="focusedFormula" class="formula-focus-backdrop" role="presentation" @click.self="closeFormulaFocus">
        <section
          ref="formulaDialogRef"
          class="formula-focus-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="focused-formula-title"
          tabindex="-1"
        >
          <header>
            <div>
              <span>公式 {{ focusedFormula.index }}</span>
              <strong id="focused-formula-title">{{ focusedFormula.title }}</strong>
            </div>
            <button type="button" aria-label="关闭" data-dialog-close @click="closeFormulaFocus">×</button>
          </header>
          <FormulaCardComponent :card="focusedFormula.card" />
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.learning-topbar-tabs {
  display: flex;
  max-width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: center;
  gap: 4px;
  overflow-x: auto;
  padding: 3px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg-secondary);
}

.learning-topbar-tabs button {
  display: inline-flex;
  min-height: 30px;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  border-radius: 8px;
  padding: 0 10px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.learning-topbar-tabs button.active,
.learning-topbar-tabs button:hover:not(:disabled) {
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

.learning-topbar-tabs button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.workspace-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  grid-template-areas: "reader";
  height: calc(100dvh - 49px);
  max-height: calc(100dvh - 49px);
  min-height: 0;
  overflow: hidden;
  background: var(--bg-primary);
}

.reader-pane,
.chat-pane {
  min-height: 0;
}

.reader-pane {
  grid-area: reader;
  height: 100%;
  min-width: 0;
  padding: 34px clamp(18px, 4vw, 44px) 56px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.workspace-shell.formula-mode .reader-pane {
  padding-inline: clamp(16px, 2.2vw, 28px);
}

@media (min-width: 1121px) {
  .workspace-shell.with-chat {
    grid-template-columns: minmax(0, 1fr) var(--chat-pane-width, 380px);
    grid-template-areas: "reader chat";
  }
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
}

.reader-title h1 {
  overflow-wrap: anywhere;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 26px;
  font-weight: 720;
  line-height: 1.28;
}

.reader-title p {
  max-width: 780px;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.72;
}

.reader-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
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

.card-stack {
  display: grid;
  max-width: min(980px, 100%);
  margin: 0 auto;
  gap: 18px;
}

.card-stack.formula-stack {
  max-width: min(1120px, 100%);
}

.teaching-list {
  display: grid;
  gap: 12px;
}

.teaching-card {
  padding: 18px;
}

.teaching-card > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.teaching-card p {
  margin-top: 12px;
  color: var(--text-secondary);
  line-height: 1.72;
}

.teaching-card small {
  display: block;
  margin-top: 10px;
  color: var(--text-muted);
}

.chat-pane {
  position: relative;
  grid-area: chat;
  height: 100%;
  min-width: 0;
  border-left: 1px solid var(--border-subtle);
  background: var(--bg-card);
  box-shadow: -14px 0 34px rgba(15, 23, 42, 0.06);
}

.chat-resize-handle {
  position: absolute;
  z-index: 5;
  top: 0;
  bottom: 0;
  left: -5px;
  width: 10px;
  cursor: col-resize;
}

.chat-resize-handle::after {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 4px;
  width: 2px;
  background: transparent;
  content: '';
}

.chat-resize-handle:hover::after,
.chat-resize-handle:focus-visible::after {
  background: var(--accent);
}

.chat-overlay {
  position: fixed;
  z-index: 80;
  inset: 49px 0 0;
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.38);
}

.chat-pane.compact {
  width: min(440px, 100%);
  max-width: 100%;
  border-left: 1px solid var(--border-subtle);
  outline: none;
}

.chat-fab {
  position: fixed;
  z-index: 45;
  right: 18px;
  bottom: 18px;
  width: 48px;
  height: 48px;
  border-radius: 999px;
  background: var(--text-primary);
  color: var(--bg-card);
  box-shadow: var(--shadow-lg);
  font-size: 13px;
  font-weight: 750;
}

.formula-focus-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.56);
}

.formula-focus-dialog {
  width: min(920px, 100%);
  max-height: min(88dvh, 920px);
  overflow-y: auto;
  border-radius: 12px;
  background: var(--bg-card);
  box-shadow: var(--shadow-lg);
  outline: none;
}

.formula-focus-dialog > header {
  position: sticky;
  z-index: 5;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 14px 18px;
  background: var(--bg-card);
}

.formula-focus-dialog > header span,
.formula-focus-dialog > header strong {
  display: block;
}

.formula-focus-dialog > header span {
  color: var(--text-muted);
  font-size: 11px;
}

.formula-focus-dialog > header strong {
  margin-top: 3px;
  color: var(--text-primary);
}

.formula-focus-dialog > header button {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  font-size: 22px;
}

@media (max-width: 720px) {
  .reader-pane {
    padding: 22px 14px 44px;
  }

  .reader-header {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .reader-actions {
    justify-content: flex-start;
  }

  .chat-pane.compact {
    width: 100vw;
  }

  .formula-focus-backdrop {
    padding: 10px;
  }
}
</style>

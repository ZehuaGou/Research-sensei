<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import katex from 'katex'
import { useLearningStore } from '../../stores/learning'

const props = defineProps<{ card: any }>()
const store = useLearningStore()
const formulaEl = ref<HTMLElement>()
const floatFormulaEl = ref<HTMLElement>()
const floatEl = ref<HTMLElement>()
const renderError = ref(false)
const formulaExplainLoading = ref(false)
const isFloated = ref(false)
const renderedHtml = ref('')

// Drag state
let dragOffsetX = 0
let dragOffsetY = 0
const floatX = ref(20)
const floatY = ref(20)

let observer: IntersectionObserver | null = null

onMounted(async () => {
  await nextTick()
  await renderFormula()
  setupFloat()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.removeEventListener('touchmove', onDragMove)
  document.removeEventListener('touchend', onDragEnd)
})

function setupFloat() {
  observer?.disconnect()
  if (!formulaEl.value?.parentElement) return
  const sentinel = formulaEl.value.closest('.formula-wrap') || formulaEl.value.parentElement
  if (!sentinel) return
  observer = new IntersectionObserver(
    ([entry]) => {
      isFloated.value = !entry.isIntersecting
      if (isFloated.value) injectFormulaHtml()
    },
    { threshold: 0.1 },
  )
  observer.observe(sentinel)
}

function injectFormulaHtml() {
  nextTick(() => {
    if (!floatFormulaEl.value || !formulaEl.value) return
    floatFormulaEl.value.innerHTML = formulaEl.value.innerHTML
  })
}

// ---------- Drag ----------
function onDragStart(e: MouseEvent | TouchEvent) {
  e.preventDefault()
  const rect = floatEl.value?.getBoundingClientRect()
  if (!rect) return
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  dragOffsetX = clientX - rect.left
  dragOffsetY = clientY - rect.top
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
  document.addEventListener('touchmove', onDragMove, { passive: false })
  document.addEventListener('touchend', onDragEnd)
}

function onDragMove(e: MouseEvent | TouchEvent) {
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  floatX.value = Math.max(0, Math.min(window.innerWidth - 320, clientX - dragOffsetX))
  floatY.value = Math.max(0, Math.min(window.innerHeight - 80, clientY - dragOffsetY))
}

function onDragEnd() {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
  document.removeEventListener('touchmove', onDragMove)
  document.removeEventListener('touchend', onDragEnd)
}

function dismissFloat() {
  isFloated.value = false
  observer?.disconnect()
}

// ---------- KaTeX ----------
function cleanKatexIncompatible(latex: string): string {
  return latex
    .replace(/\\label\{[^}]*\}/g, '')
    .replace(/\\ref\{[^}]*\}/g, '')
    .replace(/\\eqref\{[^}]*\}/g, '')
    .replace(/\\tag\{([^}]*)\}\s*$/g, '')
    .replace(/\\cite\{[^}]*\}/g, '')
    .replace(/\\(?:begin|end)\{document\}/g, '')
}

function tryKatex(el: HTMLElement, latex: string): boolean {
  try {
    el.innerHTML = ''
    katex.render(latex, el, { displayMode: true, throwOnError: false })
    return !el.querySelector('.katex-error')
  } catch { el.innerHTML = ''; return false }
}

async function renderFormula() {
  const raw = props.card.formula_latex || props.card.formula_raw || ''
  if (!formulaEl.value || !raw) return
  formulaEl.value.className = ''
  renderError.value = false
  const cleaned = cleanKatexIncompatible(raw)
  if (tryKatex(formulaEl.value, cleaned)) return
  if (/[&\\]/.test(cleaned) && !/\\begin\{(aligned|gather|matrix|cases|bmatrix|pmatrix|vmatrix)\b/.test(cleaned)) {
    if (tryKatex(formulaEl.value, `\\begin{aligned}${cleaned}\\end{aligned}`)) return
  }
  formulaEl.value.textContent = raw
  formulaEl.value.classList.add('plain-formula')
}

// Keep float card in sync with main card
watch(isFloated, (v) => { if (v) injectFormulaHtml() })

// ---------- M4 ----------
async function explainFormula() {
  store.isAskPanelOpen = true
  if (!store.currentJobId || formulaExplainLoading.value) return
  formulaExplainLoading.value = true
  store.addMessage({
    role: 'user', timestamp: Date.now(),
    content: `解释公式：${props.card.formula_id || props.card.evidence_ref || props.card.formula_ref || ''}`,
  })
  try {
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/formula/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ formula_id: props.card.formula_id || props.card.formula_ref || '' }),
    })
    const data = await res.json()
    store.addMessage({
      role: 'assistant', timestamp: Date.now(),
      content: [
        data.meaning, data.intuition ? `直觉：${data.intuition}` : '',
        data.numeric_example ? `例子：${data.numeric_example}` : '',
        data.role_in_method ? `在方法里的作用：${data.role_in_method}` : '',
      ].filter(Boolean).join('\n\n') || '这条公式还没有可展示的解释。',
    })
  } catch {
    store.addMessage({ role: 'assistant', content: '公式解释请求失败，请稍后再试。', timestamp: Date.now() })
  } finally { formulaExplainLoading.value = false }
}

function askFormula() {
  store.setSelectedText(`解释这个公式：${props.card.purpose || props.card.plain_summary || props.card.formula_id || ''}`)
  store.isAskPanelOpen = true
}

function termDetail(term: any) {
  return [term.encourages ? `鼓励：${term.encourages}` : '', term.penalizes ? `惩罚：${term.penalizes}` : '', term.if_removed ? `去掉：${term.if_removed}` : ''].filter(Boolean)
}

function isInsufficientText(v: unknown) {
  const t = String(v || '').trim()
  return /^INSUFFICIENT_EVIDENCE\b/i.test(t) || /^UNKNOWN$/i.test(t) || /M2 preserved/i.test(t) || /blocked detailed/i.test(t) || /raw\/unknown/i.test(t)
}

function readableText(v: unknown, fb: string) {
  const t = String(v || '').trim()
  if (!t) return fb
  return isInsufficientText(t) ? '证据不足，暂不推导。' : t
}

function hasInsufficientSource() {
  return isInsufficientText(props.card.purpose) || isInsufficientText(props.card.plain_summary) || isInsufficientText(props.card.intuition)
}

function isMathLikeLabel(v: unknown) { return /\\|[_^{}]|(\w+\([^)]*[·,][^)]*\))/.test(String(v || '').trim()) }

function mathLabelHtml(v: unknown) {
  const t = String(v || '').trim()
  if (!t || !isMathLikeLabel(t)) return ''
  try { return katex.renderToString(t, { displayMode: false, throwOnError: false, strict: false, output: 'html' }) } catch { return '' }
}
</script>

<template>
  <!-- ========== Main card (always rendered) ========== -->
  <article class="formula-card surface" data-testid="formula-card">
    <header>
      <div class="badge-row">
        <span class="status-pill" style="background: var(--accent-light); color: var(--accent);">公式</span>
        <span v-if="hasInsufficientSource()" class="status-pill warning">来源不足</span>
        <span v-else-if="card.evidence_status || card.evidence_ref" class="status-pill success">证据已绑定</span>
      </div>
      <h2>{{ card.display_title || card.purpose || card.problem || '公式解释' }}</h2>
    </header>

    <div class="formula-box">
      <div ref="formulaEl"></div>
      <code v-if="renderError" class="block whitespace-pre-wrap text-sm">{{ card.formula_latex || card.formula_raw }}</code>
    </div>

    <section v-if="card.symbols?.length || card.terms?.length" class="term-grid">
      <div v-if="card.symbols?.length" class="term-section-title">符号</div>
      <div v-for="symbol in card.symbols || []" :key="symbol.symbol" class="term-item">
        <strong class="term-label">
          <span v-if="mathLabelHtml(symbol.symbol)" v-html="mathLabelHtml(symbol.symbol)"></span>
          <span v-else>{{ symbol.symbol }}</span>
        </strong>
        <span class="term-copy">{{ symbol.meaning }}</span>
      </div>
      <div v-if="card.terms?.length" class="term-section-title">关键项</div>
      <div v-for="term in card.terms || []" :key="term.term" class="term-item rich">
        <strong class="term-label">
          <span v-if="mathLabelHtml(term.term)" v-html="mathLabelHtml(term.term)"></span>
          <span v-else>{{ term.term }}</span>
        </strong>
        <div class="term-copy">
          <span>{{ term.meaning }}</span>
          <small v-for="detail in termDetail(term)" :key="detail">{{ detail }}</small>
        </div>
      </div>
    </section>

    <section class="formula-explain">
      <div><h3>直觉</h3><p>{{ readableText(card.intuition || card.plain_summary, '暂无直觉解释。') }}</p></div>
      <div><h3>小例子</h3><p>{{ readableText(card.numeric_example, '暂无小例子。') }}</p></div>
      <div><h3>拿掉会怎样</h3><p>{{ readableText(card.what_if_removed || card.remove_effect, '暂无说明。') }}</p></div>
      <div><h3>权重变化</h3><p>{{ readableText(card.weight_change_effect || card.weight_sensitivity, '暂无说明。') }}</p></div>
    </section>

    <footer>
      <button type="button" class="secondary-btn" @click="explainFormula">{{ formulaExplainLoading ? '解释中...' : '让 M4 解释' }}</button>
      <button type="button" class="ghost-btn" @click="askFormula">继续追问</button>
    </footer>
  </article>

  <!-- ========== Floating mini card (shown when scrolled away) ========== -->
  <Teleport to="body">
    <Transition name="float">
      <div
        v-if="isFloated"
        ref="floatEl"
        class="formula-float"
        :style="{ left: floatX + 'px', top: floatY + 'px' }"
        data-testid="formula-float"
      >
        <div class="float-drag" @mousedown="onDragStart" @touchstart="onDragStart">
          <span class="float-title">{{ card.display_title || card.purpose || '公式' }}</span>
          <button type="button" class="float-close" @click.stop="dismissFloat" title="关闭">✕</button>
        </div>
        <div ref="floatFormulaEl" class="float-formula"></div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.formula-card { overflow: hidden; min-width: 0; }
header { padding: 20px 20px 0; }
.badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
.status-pill.neutral { background: var(--bg-secondary); color: var(--text-secondary); }
.status-pill.success { background: rgba(5,150,105,0.1); color: var(--success); }
.status-pill.warning { background: rgba(245,158,11,0.12); color: #b45309; }
h2 { margin: 14px 0 0; color: var(--text-primary); font-size: 20px; line-height: 1.6; overflow-wrap: anywhere; }

.formula-box { margin: 18px 20px; overflow-x: auto; max-width: calc(100% - 40px); border-radius: 10px; padding: 15px; background: var(--bg-secondary); color: var(--text-primary); }
.formula-box :deep(.plain-formula) { white-space: pre-wrap; color: var(--text-secondary); font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }

.term-grid { display: grid; grid-template-columns: minmax(0,1fr); gap: 1px; margin: 0 20px 18px; overflow: hidden; border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--border-subtle); }
.term-section-title { padding: 7px 12px; background: var(--bg-secondary); color: var(--text-muted); font-size: 12px; font-weight: 650; }
.term-item { display: grid; grid-template-columns: minmax(92px,0.32fr) minmax(0,1fr); min-width: 0; align-items: start; gap: 10px; padding: 9px 12px; background: var(--bg-card); color: var(--text-secondary); }
.term-item strong { display: block; max-width: 100%; overflow-x: auto; border-radius: 6px; padding: 3px 5px; background: var(--bg-secondary); color: var(--text-primary); font-size: 13px; line-height: 1.5; white-space: nowrap; }
.term-label :deep(.katex) { font-size: 1.05em; }
.term-copy, .term-copy span, .term-copy small { min-width: 0; overflow-wrap: break-word; word-break: normal; }
.term-copy { display: grid; gap: 3px; color: var(--text-secondary); font-size: 14px; line-height: 1.55; }
.term-copy small { color: var(--text-muted); font-size: 12px; line-height: 1.45; }

.formula-explain { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; padding: 0 20px 20px; }
.formula-explain > div { border-radius: 8px; padding: 11px 12px; background: var(--bg-secondary); }
.formula-explain h3 { margin-bottom: 6px; color: var(--text-muted); font-size: 13px; font-weight: 650; }
.formula-explain p { color: var(--text-secondary); font-size: 14px; line-height: 1.75; }

footer { display: flex; gap: 10px; padding: 16px 20px; border-top: 1px solid var(--border-subtle); background: var(--bg-secondary); }

@media (max-width: 900px) {
  .term-grid, .formula-explain { grid-template-columns: 1fr; }
  .term-item { grid-template-columns: minmax(78px,0.35fr) minmax(0,1fr); }
}
</style>

<style>
/* ---------- Floating mini card (teleported to body, unscoped) ---------- */
.formula-float {
  position: fixed;
  z-index: 9999;
  width: min(360px, 45vw);
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.08);
  user-select: none;
  overflow: hidden;
  font-family: system-ui, -apple-system, sans-serif;
}

.float-drag {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, var(--accent-light, rgba(99,102,241,0.08)), var(--bg-card, #fff));
  cursor: grab;
}
.float-drag:active { cursor: grabbing; }

.float-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary, #111);
  font-size: 13px;
  font-weight: 600;
}

.float-close {
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--text-muted, #9ca3af);
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 2px;
}
.float-close:hover { color: var(--text-primary, #111); }

.float-formula {
  padding: 12px 14px 14px;
  overflow-x: auto;
  color: var(--text-primary, #111);
}

/* Transition */
.float-enter-active { transition: opacity 0.15s, transform 0.15s; }
.float-leave-active { transition: opacity 0.1s, transform 0.1s; }
.float-enter-from { opacity: 0; transform: translateY(8px) scale(0.95); }
.float-leave-to { opacity: 0; transform: scale(0.95); }
</style>

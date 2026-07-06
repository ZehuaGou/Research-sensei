<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import katex from 'katex'
import { useLearningStore } from '../../stores/learning'

const props = defineProps<{ card: any }>()
const store = useLearningStore()
const formulaEl = ref<HTMLElement>()
const formulaWrap = ref<HTMLElement>()
const renderError = ref(false)
const formulaExplainLoading = ref(false)
const isPinned = ref(false)

let observer: IntersectionObserver | null = null

onMounted(async () => {
  await nextTick()
  await renderFormula()
  setupPin()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})

function setupPin() {
  observer?.disconnect()
  if (!formulaWrap.value) return
  // root=null means viewport; threshold=0 triggers as soon as element leaves
  observer = new IntersectionObserver(
    ([entry]) => {
      // When the sentinel (placed right below the formula box) exits viewport
      // from the top, pin the formula; when it re-enters, unpin.
      isPinned.value = !entry.isIntersecting
    },
    { rootMargin: '-1px 0px 0px 0px', threshold: 0 },
  )
  observer.observe(formulaWrap.value)
}

/** Clean LaTeX that KaTeX doesn't support but has no visual effect. */
function cleanKatexIncompatible(latex: string): string {
  return latex
    .replace(/\\label\{[^}]*\}/g, '')
    .replace(/\\ref\{[^}]*\}/g, '')
    .replace(/\\eqref\{[^}]*\}/g, '')
    .replace(/\\tag\{([^}]*)\}\s*$/g, '')
    .replace(/\\cite\{[^}]*\}/g, '')
    .replace(/\\(?:begin|end)\{document\}/g, '')
}

/** Try KaTeX render; returns true on success. */
function tryKatex(el: HTMLElement, latex: string): boolean {
  try {
    el.innerHTML = ''
    katex.render(latex, el, { displayMode: true, throwOnError: false })
    return !el.querySelector('.katex-error')
  } catch {
    el.innerHTML = ''
    return false
  }
}

async function renderFormula() {
  const raw = props.card.formula_latex || props.card.formula_raw || ''
  if (!formulaEl.value || !raw) return
  formulaEl.value.className = ''
  renderError.value = false

  const cleaned = cleanKatexIncompatible(raw)

  // 1. Try as-is
  if (tryKatex(formulaEl.value, cleaned)) return

  // 2. Wrap alignment markers in \begin{aligned}
  if (/[&\\]/.test(cleaned)
    && !/\\begin\{(aligned|gather|matrix|cases|bmatrix|pmatrix|vmatrix)\b/.test(cleaned)) {
    if (tryKatex(formulaEl.value, `\\begin{aligned}${cleaned}\\end{aligned}`)) return
  }

  // 3. Fallback: plain text
  formulaEl.value.textContent = raw
  formulaEl.value.classList.add('plain-formula')
}

async function explainFormula() {
  store.isAskPanelOpen = true
  if (!store.currentJobId || formulaExplainLoading.value) return
  formulaExplainLoading.value = true
  store.addMessage({
    role: 'user',
    content: `解释公式：${props.card.formula_id || props.card.evidence_ref || props.card.formula_ref || ''}`,
    timestamp: Date.now(),
  })
  try {
    const res = await fetch(`/api/v1/jobs/${store.currentJobId}/formula/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ formula_id: props.card.formula_id || props.card.formula_ref || '' }),
    })
    const data = await res.json()
    store.addMessage({
      role: 'assistant',
      content: formatFormulaExplanation(data),
      timestamp: Date.now(),
    })
  } catch {
    store.addMessage({ role: 'assistant', content: '公式解释请求失败，请稍后再试。', timestamp: Date.now() })
  } finally {
    formulaExplainLoading.value = false
  }
}

function askFormula() {
  const formulaLabel = props.card.purpose || props.card.plain_summary || props.card.formula_id || props.card.evidence_ref || '当前公式'
  store.setSelectedText(`解释这个公式：${formulaLabel}`)
  store.isAskPanelOpen = true
}

function termDetail(term: any) {
  return [
    term.encourages ? `鼓励：${term.encourages}` : '',
    term.penalizes ? `惩罚：${term.penalizes}` : '',
    term.if_removed ? `去掉：${term.if_removed}` : '',
  ].filter(Boolean)
}

function formatFormulaExplanation(data: any) {
  const parts = [
    readableText(data.meaning, ''),
    data.intuition ? `直觉：${readableText(data.intuition, '')}` : '',
    data.numeric_example ? `例子：${readableText(data.numeric_example, '')}` : '',
    data.role_in_method ? `在方法里的作用：${readableText(data.role_in_method, '')}` : '',
  ].filter(Boolean)
  return parts.join('\n\n') || '这条公式还没有可展示的解释。'
}

function isInsufficientText(value: unknown) {
  const text = String(value || '').trim()
  return /^INSUFFICIENT_EVIDENCE\b/i.test(text)
    || /^UNKNOWN$/i.test(text)
    || /M2 preserved this formula slot/i.test(text)
    || /blocked detailed derivation/i.test(text)
    || /raw\/unknown formula text/i.test(text)
}

function readableText(value: unknown, fallback: string) {
  const text = String(value || '').trim()
  if (!text) return fallback
  if (isInsufficientText(text)) return '证据不足，暂不推导。'
  return text
}

function hasInsufficientSource() {
  return isInsufficientText(props.card.purpose)
    || isInsufficientText(props.card.plain_summary)
    || isInsufficientText(props.card.intuition)
}

function isMathLikeLabel(value: unknown) {
  const text = String(value || '').trim()
  return /\\|[_^{}]|(\w+\([^)]*[·,][^)]*\))/.test(text)
}

function mathLabelHtml(value: unknown) {
  const text = String(value || '').trim()
  if (!text || !isMathLikeLabel(text)) return ''
  try {
    return katex.renderToString(text, {
      displayMode: false,
      throwOnError: false,
      strict: false,
      output: 'html',
    })
  } catch {
    return ''
  }
}
</script>

<template>
  <article class="formula-card surface" data-testid="formula-card">
    <header>
      <div class="badge-row">
        <span class="status-pill" style="background: var(--accent-light); color: var(--accent);">公式</span>
        <span v-if="hasInsufficientSource()" class="status-pill warning">来源不足</span>
        <span v-else-if="card.evidence_status || card.evidence_ref" class="status-pill success">证据已绑定</span>
      </div>
      <h2>{{ card.display_title || card.purpose || card.problem || '公式解释' }}</h2>
    </header>

    <div ref="formulaWrap" class="formula-wrap" :class="{ pinned: isPinned }">
      <div class="formula-box">
        <div ref="formulaEl"></div>
        <code v-if="renderError" class="block whitespace-pre-wrap text-sm">{{ card.formula_latex || card.formula_raw }}</code>
      </div>
      <!-- sentinel: when this leaves viewport, formula pins -->
      <div class="pin-sentinel"></div>
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
      <div>
        <h3>直觉</h3>
        <p>{{ readableText(card.intuition || card.plain_summary, '暂无直觉解释。') }}</p>
      </div>
      <div>
        <h3>小例子</h3>
        <p>{{ readableText(card.numeric_example, '暂无小例子。') }}</p>
      </div>
      <div>
        <h3>拿掉会怎样</h3>
        <p>{{ readableText(card.what_if_removed || card.remove_effect, '暂无说明。') }}</p>
      </div>
      <div>
        <h3>权重变化</h3>
        <p>{{ readableText(card.weight_change_effect || card.weight_sensitivity, '暂无说明。') }}</p>
      </div>
    </section>

    <footer>
      <button type="button" class="secondary-btn" @click="explainFormula">{{ formulaExplainLoading ? '解释中...' : '让 M4 解释' }}</button>
      <button type="button" class="ghost-btn" @click="askFormula">继续追问</button>
    </footer>
  </article>
</template>

<style scoped>
.formula-card {
  min-width: 0;
}

header {
  padding: 20px 20px 0;
}

.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-pill.neutral {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.status-pill.success {
  background: rgba(5, 150, 105, 0.1);
  color: var(--success);
}

.status-pill.warning {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

h2 {
  margin: 14px 0 0;
  color: var(--text-primary);
  font-size: 20px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.formula-wrap {
  position: relative;
}

.pin-sentinel {
  height: 0;
}

.formula-box {
  margin: 0;
  padding: 15px 20px;
  overflow-x: auto;
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-radius: 10px;
}

.formula-wrap.pinned .formula-box {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  width: min(860px, 100% - 40px);
  margin: 0 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  border-radius: 0 0 10px 10px;
}

.formula-box :deep(.plain-formula) {
  white-space: pre-wrap;
  color: var(--text-secondary);
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  font-size: 13px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.term-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1px;
  margin: 16px 20px 18px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--border-subtle);
}

.term-section-title {
  padding: 7px 12px;
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 850;
}

.term-item {
  display: grid;
  grid-template-columns: minmax(92px, 0.32fr) minmax(0, 1fr);
  min-width: 0;
  align-items: start;
  gap: 10px;
  padding: 9px 12px;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.term-item strong {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-radius: 6px;
  padding: 3px 5px;
  background: var(--bg-secondary);
  color: var(--accent);
  font-size: 13px;
  line-height: 1.5;
  white-space: nowrap;
}

.term-label :deep(.katex) {
  font-size: 1.05em;
}

.term-copy,
.term-copy span,
.term-copy small {
  min-width: 0;
  overflow-wrap: break-word;
  word-break: normal;
}

.term-copy {
  display: grid;
  gap: 3px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.55;
}

.term-copy small {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.45;
}

.formula-explain {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 16px 20px 20px;
}

.formula-explain > div {
  border-radius: 8px;
  padding: 11px 12px;
  background: var(--bg-secondary);
}

.formula-explain h3 {
  margin-bottom: 6px;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 750;
}

.formula-explain p {
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.75;
}

footer {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}

@media (max-width: 900px) {
  .term-grid,
  .formula-explain {
    grid-template-columns: 1fr;
  }

  .term-item {
    grid-template-columns: minmax(78px, 0.35fr) minmax(0, 1fr);
  }
}
</style>

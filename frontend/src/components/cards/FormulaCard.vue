<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import katex from 'katex'
import { useLearningStore } from '../../stores/learning'

const props = defineProps<{ card: any }>()
const store = useLearningStore()
const formulaEl = ref<HTMLElement>()
const renderError = ref(false)
const formulaExplainLoading = ref(false)

onMounted(async () => {
  await nextTick()
  await renderFormula()
})

/** Clean LaTeX that KaTeX doesn't support but has no visual effect. */
function cleanKatexIncompatible(latex: string): string {
  let s = latex
  // Strip outer display-math delimiters: $$...$$, \[...\]
  s = s.replace(/^\s*\$\$\s*([\s\S]*?)\s*\$\$\s*$/g, '$1')
  s = s.replace(/^\s*\\\[\s*([\s\S]*?)\s*\\\]\s*$/g, '$1')
  // Strip \begin{equation}...\end{equation} etc, keep inner content
  s = s.replace(/\\begin\{(equation|align|gather|split|multline|eqnarray)\*?\}[\s\S]*?\\end\{(equation|align|gather|split|multline|eqnarray)\*?\}/g, (m) => {
    return m.replace(/\\begin\{[^}]*\}\s*/g, '').replace(/\s*\\end\{[^}]*\}/g, '')
  })
  // Remove \label, \ref, \eqref, \cite, \tag, \nonumber
  s = s.replace(/\\label\{[^}]*\}/g, '')
  s = s.replace(/\\ref\{[^}]*\}/g, '')
  s = s.replace(/\\eqref\{[^}]*\}/g, '')
  s = s.replace(/\\cite\{[^}]*\}/g, '')
  s = s.replace(/\\tag\{[^}]*\}/g, '')
  s = s.replace(/\\nonumber\s*/g, '')
  return s
}

/** Try KaTeX render; returns true on success. */
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
  formulaEl.value.textContent = '公式暂时无法渲染。'
  formulaEl.value.classList.add('plain-formula')
  renderError.value = true
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
      content: (([data.meaning, data.intuition ? `直觉：${data.intuition}` : '', data.numeric_example ? `例子：${data.numeric_example}` : '', data.role_in_method ? `在方法里的作用：${data.role_in_method}` : ''].filter(Boolean).join('\n\n')) || '这条公式还没有可展示的解释。'),
      timestamp: Date.now(),
    })
  } catch {
    store.addMessage({ role: 'assistant', content: '公式解释请求失败，请稍后再试。', timestamp: Date.now() })
  } finally {
    formulaExplainLoading.value = false
  }
}

function askFormula() {
  const formulaLabel = displayTitle() || props.card.formula_id || props.card.evidence_ref || '当前公式'
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

function isInsufficientText(value: unknown) {
  const text = String(value || '').trim()
  return /^INSUFFICIENT_EVIDENCE\b/i.test(text)
    || /^UNKNOWN$/i.test(text)
    || /M2 preserved this formula slot/i.test(text)
    || /blocked detailed derivation/i.test(text)
    || /raw\/unknown formula text/i.test(text)
}

function isRawFormulaText(value: unknown) {
  const text = String(value || '').trim()
  return /Formula evidence preserved from M1 context/i.test(text)
    || /\\begin\{(?:cases|aligned|matrix|bmatrix|pmatrix|equation|align)/.test(text)
    || /\\(?:frac|overline|underline|label|text|tau|sum|prod|int)\b/.test(text)
}

function displayTitle() {
  const candidates = [
    props.card.display_title,
    props.card.purpose,
    props.card.problem,
  ].map((value: unknown) => String(value || '').replace(/\s+/g, ' ').trim())
  return candidates.find(text => text && !isInsufficientText(text) && !isRawFormulaText(text))
    || '公式解释'
}

function readableText(value: unknown, fallback: string) {
  const text = String(value || '').trim()
  if (!text) return fallback
  if (isInsufficientText(text)) return '证据不足，暂不推导。'
  if (isRawFormulaText(text)) return fallback
  return text
}

function hasInsufficientSource() {
  return isInsufficientText(props.card.purpose)
    || isInsufficientText(props.card.plain_summary)
    || isInsufficientText(props.card.intuition)
    || isRawFormulaText(props.card.purpose)
    || isRawFormulaText(props.card.plain_summary)
    || isRawFormulaText(props.card.intuition)
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

function detailItemCount() {
  return (props.card.symbols?.length || 0) + (props.card.terms?.length || 0)
}

function shouldOpenTermDetails() {
  return detailItemCount() <= 6
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
      <h2>{{ displayTitle() }}</h2>
    </header>

    <div class="formula-box">
      <div ref="formulaEl"></div>
      <details v-if="renderError" class="raw-formula-fallback">
        <summary>查看原始 LaTeX</summary>
        <code>{{ card.formula_latex || card.formula_raw }}</code>
      </details>
    </div>

    <details
      v-if="card.symbols?.length || card.terms?.length"
      class="term-details"
      :open="shouldOpenTermDetails()"
    >
      <summary>
        <strong>符号与关键项</strong>
        <span>{{ detailItemCount() }}</span>
      </summary>
      <section class="term-grid">
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
    </details>

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
  overflow: hidden;
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
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.formula-box {
  margin: 18px 20px;
  overflow-x: auto;
  max-width: calc(100% - 40px);
  border-radius: 10px;
  padding: 16px;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.formula-box :deep(.plain-formula) {
  white-space: pre-wrap;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.raw-formula-fallback {
  margin-top: 12px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 10px;
  color: var(--text-muted);
  font-size: 12px;
}

.raw-formula-fallback summary {
  cursor: pointer;
  font-weight: 650;
}

.raw-formula-fallback code {
  display: block;
  margin-top: 8px;
  overflow-x: auto;
  border-radius: 8px;
  padding: 10px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.term-details {
  margin: 0 20px 18px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--bg-card);
}

.term-details summary {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 13px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  user-select: none;
}

.term-details summary span {
  color: var(--text-muted);
  font-size: 12px;
}

.term-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1px;
  margin: 0;
  overflow: hidden;
  border-top: 1px solid var(--border-subtle);
  background: var(--border-subtle);
}

.term-section-title {
  padding: 8px 12px;
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.term-item {
  display: grid;
  grid-template-columns: minmax(96px, 0.32fr) minmax(0, 1fr);
  min-width: 0;
  align-items: start;
  gap: 10px;
  padding: 10px 12px;
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
  color: var(--text-primary);
  font-size: 14px;
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
  line-height: 1.58;
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
  padding: 0 20px 20px;
}

.formula-explain > div {
  border-radius: 8px;
  padding: 12px;
  background: var(--bg-secondary);
}

.formula-explain h3 {
  margin-bottom: 6px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 650;
}

.formula-explain p {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.72;
}

footer {
  display: flex;
  flex-wrap: wrap;
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

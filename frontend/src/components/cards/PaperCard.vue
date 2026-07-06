<script setup lang="ts">
import { useLearningStore } from '../../stores/learning'

const props = defineProps<{ card: any; skeleton: any }>()
const store = useLearningStore()

function textOf(value: any) {
  return typeof value === 'string' ? value : value?.text || ''
}

function isInsufficientText(value: any) {
  const text = textOf(value).trim()
  return !text || /^INSUFFICIENT_EVIDENCE$/i.test(text) || /^UNKNOWN$/i.test(text) || text === '证据不足，暂不展开。'
}

function displayText(value: any, fallback = '暂无') {
  const text = textOf(value).trim()
  if (!text && fallback !== '暂无') return fallback
  return isInsufficientText(value) ? '证据不足，暂不展开。' : text || fallback
}

function canAsk(value: any) {
  return Boolean(textOf(value)) && !isInsufficientText(value)
}

function refOf(value: any) {
  return value?.evidence_ref || ''
}

function evidenceLabel(value: any) {
  return refOf(value) ? '证据已定位' : ''
}

function ask(label: string, text: string) {
  store.setSelectedText(`${label}：${text}`)
  store.isAskPanelOpen = true
}

function copySummary() {
  const text = [
    props.card.title,
    props.card.thirty_second,
    textOf(props.card.problem),
    textOf(props.card.core_idea),
    textOf(props.card.method_overview),
  ].filter(Boolean).join('\n\n')
  void navigator.clipboard?.writeText(text)
}
</script>

<template>
  <article class="paper-card surface" data-testid="paper-card">
    <header class="paper-head">
      <div class="min-w-0">
        <div class="mb-3 flex flex-wrap gap-2">
          <span class="status-pill" style="background: var(--accent-light); color: var(--accent);">论文核心</span>
          <span v-if="card.evidence_status" class="status-pill" style="background: rgba(5,150,105,0.1); color: var(--success);">证据已绑定</span>
        </div>
        <h1>{{ card.title || '论文卡片' }}</h1>
        <p class="summary">{{ card.thirty_second || card.one_sentence_summary }}</p>
      </div>
      <button type="button" class="secondary-btn" @click="copySummary">复制摘要</button>
    </header>

    <section class="claim-grid">
      <div class="claim-block">
        <div class="claim-title">
          <span>01</span>
          <div class="claim-label">研究问题</div>
        </div>
        <p>{{ displayText(card.problem, skeleton?.problem?.plain || '暂无') }}</p>
        <button v-if="canAsk(card.problem)" type="button" @click="ask('解释研究问题', textOf(card.problem))">追问</button>
        <span v-if="evidenceLabel(card.problem)" class="ref-chip" :title="refOf(card.problem)">{{ evidenceLabel(card.problem) }}</span>
      </div>

      <div class="claim-block">
        <div class="claim-title">
          <span>02</span>
          <div class="claim-label">核心想法</div>
        </div>
        <p>{{ displayText(card.core_idea) }}</p>
        <button v-if="canAsk(card.core_idea)" type="button" @click="ask('解释核心想法', textOf(card.core_idea))">追问</button>
        <span v-if="evidenceLabel(card.core_idea)" class="ref-chip" :title="refOf(card.core_idea)">{{ evidenceLabel(card.core_idea) }}</span>
      </div>

      <div class="claim-block">
        <div class="claim-title">
          <span>03</span>
          <div class="claim-label">方法机制</div>
        </div>
        <p>{{ displayText(card.method_overview, skeleton?.mechanism?.plain || '暂无') }}</p>
        <button v-if="canAsk(card.method_overview)" type="button" @click="ask('解释方法机制', textOf(card.method_overview))">追问</button>
        <span v-if="evidenceLabel(card.method_overview)" class="ref-chip" :title="refOf(card.method_overview)">{{ evidenceLabel(card.method_overview) }}</span>
      </div>

      <div class="claim-block">
        <div class="claim-title">
          <span>04</span>
          <div class="claim-label">实验结论</div>
        </div>
        <p>{{ displayText(card.experiment_summary, card.deep_dive || '暂无') }}</p>
        <button v-if="canAsk(card.experiment_summary)" type="button" @click="ask('解释实验结论', textOf(card.experiment_summary))">追问</button>
        <span v-if="evidenceLabel(card.experiment_summary)" class="ref-chip" :title="refOf(card.experiment_summary)">{{ evidenceLabel(card.experiment_summary) }}</span>
      </div>
    </section>

    <footer class="paper-actions">
      <button type="button" class="primary-btn" @click="ask('用中文讲透这篇论文', card.thirty_second || card.one_sentence_summary || '')">让 M4 讲透</button>
      <button type="button" class="ghost-btn" @click="ask('像组会一样追问这篇论文', card.title || '')">组会追问</button>
    </footer>
  </article>
</template>

<style scoped>
.paper-card {
  overflow: hidden;
}

.paper-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 20px;
  padding: 22px;
  border-bottom: 1px solid var(--border-subtle);
}

.paper-head > button {
  justify-self: end;
  align-self: start;
  white-space: nowrap;
}

.paper-head h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: clamp(22px, 3vw, 30px);
  line-height: 1.25;
  letter-spacing: 0;
  font-weight: 720;
}

.summary {
  max-width: 900px;
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.72;
}

.claim-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: var(--border-subtle);
}

.claim-block {
  min-height: 190px;
  padding: 20px;
  background: var(--bg-card);
}

.claim-title {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 12px;
}

.claim-title span {
  display: inline-flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 720;
}

.claim-label {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
}

.claim-block p {
  min-height: 82px;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.78;
}

.claim-block button {
  margin-top: 16px;
  color: var(--text-primary);
  background: transparent;
  font-weight: 650;
}

.ref-chip {
  display: inline-flex;
  margin-top: 10px;
  border-radius: 999px;
  padding: 4px 8px;
  background: rgba(5, 150, 105, 0.1);
  color: var(--success);
  font-weight: 750;
  font-size: 12px;
}

.paper-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px 22px;
  background: var(--bg-secondary);
}

@media (max-width: 900px) {
  .paper-head {
    grid-template-columns: 1fr;
  }

  .claim-grid {
    grid-template-columns: 1fr;
  }
}
</style>

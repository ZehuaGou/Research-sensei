<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  blockingReason?: string
  warnings?: Array<{ code: string; message: string }>
  missingComponents?: string[]
  paperWorkspaceStatus?: Record<string, any>
  componentStatus?: Record<string, string>
  allowedDownstream?: Record<string, boolean>
}>()

const statusText: Record<string, string> = {
  SUCCESS: '理解完成',
  BASELINE_ONLY: '仅基础解析',
  BLOCKED_UNDERSTANDING: '理解被阻断',
  DEGRADED_STRUCTURAL: '结构不完整',
  FAILED: '流水线失败',
}

const reasonText: Record<string, string> = {
  NO_LLM_CLIENT: '后端没有启用实时大模型，请开启 RESEARCHSENSEI_ENABLE_API_LLM=1 并重新跑论文。',
  PAPER_CARD_FAILED: '论文核心卡片没有生成成功。',
  FORMULA_CARDS_FAILED: '公式卡片没有生成成功。',
  TEACHING_CARDS_FAILED: '教学卡片没有生成成功。',
  MISSING_METHOD_EVIDENCE: '证据包里缺少方法部分证据。',
  EMPTY_EVIDENCE_PACK: '没有可用于生成卡片的证据。',
  FORMULA_DERIVATION_BLOCKED: '公式来源不够可靠，不能生成可信推导。',
}

const title = computed(() => statusText[props.status] || '')
const tone = computed(() => {
  if (props.status === 'SUCCESS') return 'success'
  if (props.status === 'BLOCKED_UNDERSTANDING' || props.status === 'FAILED') return 'danger'
  if (props.status === 'DEGRADED_STRUCTURAL') return 'warning'
  return 'neutral'
})
const message = computed(() => {
  if (props.status === 'SUCCESS') return '可以阅读论文卡片、解释公式，并继续向 M4 追问。'
  if (props.status === 'BASELINE_ONLY') return reasonText.NO_LLM_CLIENT
  if (props.status === 'BLOCKED_UNDERSTANDING') return reasonText[props.blockingReason || ''] || props.blockingReason || '当前结果不能展示给用户。'
  if (props.status === 'DEGRADED_STRUCTURAL') return reasonText[props.blockingReason || ''] || '部分组件缺失。'
  if (props.status === 'FAILED') return '解析或理解流水线执行失败，请查看后端日志。'
  return ''
})

const compactRows = computed(() => {
  const details = props.paperWorkspaceStatus || {}
  const rows = [
    ['来源', details.source_type],
    ['验证', details.verification_status],
    ['证据', details.evidence_status],
    ['质量', details.quality_status],
    ['公式来源', details.formula_origin],
    ['公式 OCR', details.formula_ocr_status],
    ['阻断原因', props.blockingReason || details.degradation_reason],
  ]
  return rows.filter(([, value]) => value !== undefined && value !== null && value !== '')
})

function readableKey(value: unknown) {
  const text = String(value || '')
  const labels: Record<string, string> = {
    NO_LLM_CLIENT: '未连接大模型',
    PAPER_CARD_FAILED: '论文卡片失败',
    FORMULA_CARDS_FAILED: '公式卡片失败',
    TEACHING_CARDS_FAILED: '教学卡片失败',
    MISSING_METHOD_EVIDENCE: '缺少方法证据',
    EMPTY_EVIDENCE_PACK: '证据为空',
    FORMULA_DERIVATION_BLOCKED: '公式推导被阻断',
    paper_card: '论文卡片',
    formula_cards: '公式卡片',
    teaching_cards: '教学卡片',
    llm: '大模型',
    evidence_pack: '证据包',
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
    BASELINE: '基础解析',
    not_available: '未提供',
    not_required: '无需 OCR',
    source_latex: '论文 LaTeX',
    mineru_latex: 'MinerU LaTeX',
    raw_formula_text: '原始公式文本',
  }
  return labels[text] || text
}

function valueText(value: any) {
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (Array.isArray(value)) return value.map(readableKey).join('、')
  return readableKey(value)
}
</script>

<template>
  <section v-if="title" class="status-banner surface" :class="tone" data-testid="status-banner">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="min-w-0">
        <div class="mb-2 flex flex-wrap items-center gap-2">
          <span class="status-pill" :class="tone">{{ title }}</span>
          <span v-if="blockingReason" class="text-sm font-medium" style="color: var(--text-muted);">{{ readableKey(blockingReason) }}</span>
        </div>
        <p class="max-w-3xl text-[15px] leading-7" style="color: var(--text-secondary);">{{ message }}</p>
      </div>

      <div v-if="missingComponents?.length" class="rounded-[10px] px-3 py-2 text-sm" style="background: var(--bg-secondary); color: var(--text-secondary);">
        缺少：{{ missingComponents.map(readableKey).join('、') }}
      </div>
    </div>

    <div v-if="compactRows.length" class="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      <div v-for="[label, value] in compactRows" :key="String(label)" class="rounded-[10px] px-3 py-2" style="background: var(--bg-secondary);">
        <div class="text-xs font-semibold" style="color: var(--text-muted);">{{ label }}</div>
        <div class="truncate text-sm font-medium" style="color: var(--text-primary);">{{ valueText(value) }}</div>
      </div>
    </div>

    <div v-if="warnings?.length" class="mt-3 space-y-1 text-sm" style="color: var(--text-muted);">
      <div v-for="warning in warnings" :key="warning.code">
        {{ warning.code }}：{{ warning.message }}
      </div>
    </div>
  </section>
</template>

<style scoped>
.status-banner {
  padding: 16px;
  margin-bottom: 18px;
}

.status-banner.success,
.status-pill.success {
  background: rgba(21, 128, 61, 0.1);
  color: var(--success);
}

.status-banner.warning,
.status-pill.warning {
  background: rgba(196, 122, 6, 0.1);
  color: var(--warning);
}

.status-banner.danger,
.status-pill.danger {
  background: rgba(220, 38, 38, 0.1);
  color: var(--danger);
}

.status-pill.neutral {
  background: var(--accent-light);
  color: var(--text-primary);
}
</style>

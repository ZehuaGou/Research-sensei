<script setup lang="ts">
import { computed } from 'vue'
import StatusBanner from '../StatusBanner.vue'
import type { PaperWorkspaceStatus, UnderstandingStatus } from '../../types/workspace'

const props = defineProps<{
  understandingStatus: UnderstandingStatus | null
  paperWorkspaceStatus: PaperWorkspaceStatus
  missingComponents: string[]
  paperCardCount: number
  formulaCount: number
  detectedFormulaCount: number
  teachingCount: number
}>()

const status = computed(() => props.understandingStatus?.status || '')
const metrics = computed(() => [
  { label: '论文卡片', value: props.paperCardCount ? '已生成' : '缺失', tone: props.paperCardCount ? 'ready' : 'muted' },
  {
    label: '公式',
    value: props.formulaCount
      ? props.detectedFormulaCount > props.formulaCount
        ? `${props.formulaCount} 可用 · ${props.detectedFormulaCount - props.formulaCount} 待重试`
        : `${props.formulaCount} 可推导`
      : props.detectedFormulaCount
        ? `${props.detectedFormulaCount} 段受限`
        : '0',
    tone: props.formulaCount ? 'ready' : 'muted',
  },
  { label: '教学卡片', value: String(props.teachingCount), tone: props.teachingCount ? 'ready' : 'muted' },
])

const statusRows = computed(() => {
  const details = props.paperWorkspaceStatus
  const labels: Record<string, string> = {
    blocking_reason: '阻断原因',
    source_type: '来源类型',
    verification_status: '来源验证',
    pdf_metadata_check: 'PDF 元数据',
    pdf_title_match: '标题匹配',
    can_enter_analysis: '可进入论文解析',
    source_confidence: '来源置信度',
    paper_agent_status: '论文代理',
    paper_agent_model: '页面识读模型',
    paper_tutor_model: '讲解模型',
    analysis_ready: '论文解析会话',
    degradation_reason: '结构原因',
    formula_origin: '公式来源',
    formula_ocr_status: '公式 OCR',
    evidence_status: '证据包',
    quality_status: '质量审计',
  }
  const rows: Array<[string, unknown]> = [
    ['blocking_reason', props.understandingStatus?.blocking_reason],
    ['source_type', details.source_type],
    ['verification_status', details.verification_status],
    ['pdf_metadata_check', details.pdf_metadata_check],
    ['pdf_title_match', details.pdf_title_match],
    ['can_enter_analysis', details.can_enter_analysis],
    ['source_confidence', details.source_confidence],
    ['paper_agent_status', details.paper_agent_status],
    ['paper_agent_model', details.paper_agent_model],
    ['paper_tutor_model', details.paper_tutor_model],
    ['analysis_ready', details.analysis_ready],
    ['degradation_reason', details.degradation_reason],
    ['formula_origin', details.formula_origin],
    ['formula_ocr_status', details.formula_ocr_status],
    ['evidence_status', details.evidence_status],
    ['quality_status', details.quality_status],
  ]
  Object.entries(props.understandingStatus?.component_status || {}).forEach(([key, value]) => rows.push([componentLabel(key), value]))
  return rows
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([label, value]) => [labels[label] || label, formatStatusValue(value)] as const)
})

function componentLabel(key: string) {
  return ({
    paper_card: '论文卡片',
    formula_cards: '公式卡片',
    teaching_cards: '教学卡片',
    llm: '大模型',
    evidence_pack: '证据包',
  } as Record<string, string>)[key] || key
}

function formatStatusValue(value: unknown) {
  if (value === true) return '是'
  if (value === false) return '否'
  const text = String(value)
  return ({
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
    canonical_paper_bundle: '规范化论文包',
    verified: '已验证',
    success: '成功',
    SUCCESS: '成功',
    PARTIAL: '部分可用',
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
  } as Record<string, string>)[text] || text
}
</script>

<template>
  <div v-if="paperCardCount || formulaCount || teachingCount" class="reader-metrics" data-testid="reader-metrics">
    <div v-for="metric in metrics" :key="metric.label" :class="metric.tone">
      <span>{{ metric.label }}</span>
      <strong>{{ metric.value }}</strong>
    </div>
  </div>

  <StatusBanner
    :status="status"
    :blocking-reason="understandingStatus?.blocking_reason"
    :warnings="understandingStatus?.warnings"
    :missing-components="missingComponents"
    :paper-workspace-status="paperWorkspaceStatus"
    :component-status="understandingStatus?.component_status"
    :allowed-downstream="understandingStatus?.allowed_downstream"
  />

  <details class="status-details">
    <summary>查看技术状态</summary>
    <dl>
      <div v-for="[label, value] in statusRows" :key="label">
        <dt>{{ label }}</dt>
        <dd>{{ value }}</dd>
      </div>
    </dl>
  </details>
</template>

<style scoped>
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

@media (max-width: 640px) {
  .reader-metrics,
  .status-details dl {
    grid-template-columns: 1fr;
  }
}
</style>

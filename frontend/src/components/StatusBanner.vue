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

const title = computed(() => {
  switch (props.status) {
    case 'SUCCESS':
      return 'Understanding ready'
    case 'BASELINE_ONLY':
      return 'Baseline only'
    case 'BLOCKED_UNDERSTANDING':
      return 'Understanding blocked'
    case 'DEGRADED_STRUCTURAL':
      return 'Degraded understanding'
    case 'FAILED':
      return 'Pipeline failed'
    default:
      return ''
  }
})

const message = computed(() => {
  switch (props.status) {
    case 'SUCCESS':
      return 'Evidence-bound paper, formula, and teaching cards are available for this run.'
    case 'BASELINE_ONLY':
      return 'No real LLM understanding is available for this run. Diagnostic cards are hidden from the workspace.'
    case 'BLOCKED_UNDERSTANDING':
      return props.blockingReason || 'The paper could not enter user-facing understanding.'
    case 'DEGRADED_STRUCTURAL':
      return 'Some M2 components are unavailable. Only successful components can be shown.'
    case 'FAILED':
      return 'The analysis run failed before a usable understanding status was produced.'
    default:
      return ''
  }
})

const toneStyle = computed(() => {
  if (props.status === 'SUCCESS') {
    return 'background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.2); color: #10b981;'
  }
  if (props.status === 'BLOCKED_UNDERSTANDING' || props.status === 'FAILED') {
    return 'background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); color: #ef4444;'
  }
  if (props.status === 'DEGRADED_STRUCTURAL') {
    return 'background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2); color: #6366f1;'
  }
  return 'background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2); color: #f59e0b;'
})

const detailRows = computed(() => {
  const details = props.paperWorkspaceStatus || {}
  const rows: Array<[string, any]> = [
    ['blocking_reason', props.blockingReason],
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
  Object.entries(props.componentStatus || {}).forEach(([key, value]) => {
    rows.push([`component_status.${key}`, value])
  })
  Object.entries(props.allowedDownstream || {}).forEach(([key, value]) => {
    rows.push([`allowed_downstream.${key}`, value])
  })
  return rows
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([label, value]) => ({ label: String(label), value: formatValue(value) }))
})

function formatValue(value: any): string {
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}
</script>

<template>
  <div
    v-if="title"
    class="rounded-lg p-4 mb-6"
    :style="toneStyle"
    data-testid="status-banner"
  >
    <div class="text-sm font-semibold mb-1">{{ title }}</div>
    <p class="text-xs leading-relaxed mb-3" style="color: var(--text-secondary);">
      {{ message }}
    </p>

    <div v-if="missingComponents?.length" class="text-xs mb-3" style="color: var(--text-secondary);">
      missing_components: {{ missingComponents.join(', ') }}
    </div>

    <dl v-if="detailRows.length" class="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-3">
      <div
        v-for="row in detailRows"
        :key="row.label"
        class="rounded-md px-3 py-2"
        style="background: rgba(255,255,255,0.55);"
      >
        <dt class="text-[11px] font-semibold" style="color: var(--text-muted);">{{ row.label }}</dt>
        <dd class="text-xs break-words" style="color: var(--text-primary);">{{ row.value }}</dd>
      </div>
    </dl>

    <div v-if="warnings?.length" class="space-y-1">
      <div v-for="w in warnings" :key="w.code" class="text-xs" style="color: var(--text-muted);">
        {{ w.code }}: {{ w.message }}
      </div>
    </div>
  </div>
</template>

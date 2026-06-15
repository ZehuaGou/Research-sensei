<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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

const understandingStatus = ref<any>(null)
const paperWorkspaceStatus = ref<Record<string, any>>({})
const cards = ref<Record<string, any> | null>(null)
const degraded = ref(false)
const missingComponents = ref<string[]>([])
const isLoading = ref(true)
const error = ref('')
const activeTab = ref<'paper' | 'formulas' | 'teaching'>('paper')

const status = computed(() => understandingStatus.value?.status || '')
const canShowCards = computed(() => ['SUCCESS', 'DEGRADED_STRUCTURAL'].includes(status.value))
const paperCard = computed(() => cards.value?.paper_card || null)
const teachingCards = computed(() => cards.value?.teaching_cards?.teaching_cards || [])
const formulaCardsList = computed(() => {
  const bundle = cards.value?.formula_cards
  if (!bundle) return []
  if (Array.isArray(bundle)) return bundle
  if (Array.isArray(bundle.formula_cards)) return bundle.formula_cards
  return []
})

const statusRows = computed(() => {
  const details = paperWorkspaceStatus.value || {}
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
    rows.push([`component_status.${key}`, value])
  })
  Object.entries(understandingStatus.value?.allowed_downstream || {}).forEach(([key, value]) => {
    rows.push([`allowed_downstream.${key}`, value])
  })
  return rows.filter(([, value]) => value !== undefined && value !== null && value !== '')
})

const formulaTabDisabled = computed(() => {
  if (formulaCardsList.value.length > 0) return false
  // In DEGRADED state, keep tab clickable so user can see degradation message
  if (status.value === 'DEGRADED_STRUCTURAL') return false
  return true
})

const tabs = computed(() => [
  { key: 'paper' as const, label: 'Paper', disabled: !paperCard.value },
  { key: 'formulas' as const, label: 'Formulas', disabled: formulaTabDisabled.value },
  { key: 'teaching' as const, label: 'Teaching', disabled: teachingCards.value.length === 0 },
])

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

function normalizeFormulaCard(card: any): any {
  if (!card) return card
  return {
    ...card,
    formula_latex: card.formula_latex || card.formula_raw || '',
    problem: card.problem || card.purpose || card.intuition || 'Formula explanation',
    formula_ref: card.formula_ref || card.location || card.formula_id || '',
    remove_effect: card.remove_effect || card.what_if_removed || '',
    weight_change_effect: card.weight_change_effect || card.weight_sensitivity || '',
    plain_summary: card.plain_summary || card.intuition || '',
  }
}

async function loadWorkspace() {
  isLoading.value = true
  error.value = ''
  try {
    const statusRes = await fetch(`/api/v1/jobs/${jobId}/understanding_status`)
    if (!statusRes.ok) {
      error.value = statusRes.status === 404 ? 'Analysis result not found.' : 'Failed to load understanding status.'
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
      return
    }

    if (cardsRes.status === 409) {
      const detail = await cardsRes.json().catch(() => ({}))
      error.value = detail.detail?.message || 'Card artifacts do not match understanding status.'
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
    error.value = 'Network error while loading the workspace.'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  store.currentJobId = jobId
  void loadWorkspace()
})
</script>

<template>
  <div class="flex min-h-[calc(100vh-56px)]">
    <aside class="w-64 flex-shrink-0 border-r p-4" style="border-color: var(--border-subtle); background: var(--bg-secondary);">
      <div class="text-[11px] font-semibold uppercase mb-3" style="color: var(--text-muted);">PaperWorkspace</div>
      <nav class="space-y-1">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :disabled="tab.disabled"
          class="w-full text-left px-3 py-2 rounded-md text-[13px] font-medium disabled:opacity-40"
          :style="activeTab === tab.key ? 'background: var(--accent-light); color: var(--accent);' : 'color: var(--text-secondary);'"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>
      <div v-if="understandingStatus" class="mt-6 text-xs space-y-1" style="color: var(--text-secondary);">
        <div>Status: {{ status }}</div>
        <div v-if="degraded">Degraded: true</div>
      </div>
    </aside>

    <main class="flex-1 overflow-y-auto">
      <div class="max-w-3xl mx-auto px-8 py-10">
        <div v-if="isLoading" class="py-24 text-sm" style="color: var(--text-muted);">Loading workspace...</div>

        <div v-else-if="error" class="py-24">
          <div class="text-sm font-medium mb-4" style="color: #ef4444;">{{ error }}</div>
          <button
            class="px-4 py-2 rounded-md text-[13px] font-medium"
            style="background: var(--accent-light); color: var(--accent);"
            @click="router.push('/')"
          >
            Back
          </button>
        </div>

        <div v-else>
          <StatusBanner
            :status="status"
            :blockingReason="understandingStatus?.blocking_reason"
            :warnings="understandingStatus?.warnings"
            :missingComponents="missingComponents"
            :paperWorkspaceStatus="paperWorkspaceStatus"
            :componentStatus="understandingStatus?.component_status"
            :allowedDownstream="understandingStatus?.allowed_downstream"
          />

          <section class="mb-6">
            <div class="text-xs font-semibold uppercase mb-2" style="color: var(--text-muted);">Status Details</div>
            <dl class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div
                v-for="[label, value] in statusRows"
                :key="String(label)"
                class="rounded-md px-3 py-2"
                style="background: var(--bg-card); border: 1px solid var(--border-subtle);"
              >
                <dt class="text-[11px] font-semibold" style="color: var(--text-muted);">{{ label }}</dt>
                <dd class="text-xs break-words" style="color: var(--text-primary);">{{ String(value) }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="canShowCards" class="space-y-6">
            <PaperCard
              v-if="activeTab === 'paper' && paperCard"
              :card="normalizePaperCard(paperCard)"
              :skeleton="normalizeSkeleton(paperCard)"
            />

            <template v-else-if="activeTab === 'formulas'">
              <template v-if="formulaCardsList.length > 0">
                <FormulaCard
                  v-for="formula in formulaCardsList"
                  :key="formula.formula_id || formula.evidence_ref"
                  :card="normalizeFormulaCard(formula)"
                />
              </template>
              <div
                v-else-if="status === 'DEGRADED_STRUCTURAL'"
                class="rounded-lg p-6 text-center"
                style="background: rgba(99,102,241,0.06); border: 1px solid rgba(99,102,241,0.15);"
                data-testid="formula-degraded-message"
              >
                <div class="text-sm font-semibold mb-2" style="color: #6366f1;">公式推导不可用</div>
                <p class="text-xs leading-relaxed" style="color: var(--text-secondary);">
                  公式推导因来源不可靠被阻断（{{ paperWorkspaceStatus.degradation_reason || 'FORMULA_DERIVATION_BLOCKED' }}）。
                  公式来源为 raw_formula_text，无法生成可信的详细公式讲解。
                </p>
                <div v-if="paperWorkspaceStatus.formula_origin" class="text-[11px] mt-3" style="color: var(--text-muted);">
                  formula_origin: {{ paperWorkspaceStatus.formula_origin }}
                </div>
                <div v-if="paperWorkspaceStatus.formula_ocr_status" class="text-[11px]" style="color: var(--text-muted);">
                  formula_ocr_status: {{ paperWorkspaceStatus.formula_ocr_status }}
                </div>
              </div>
            </template>

            <div
              v-else-if="activeTab === 'teaching'"
              class="space-y-3"
              data-testid="teaching-cards"
            >
              <article
                v-for="card in teachingCards"
                :key="card.card_id || card.title"
                class="rounded-lg p-4"
                style="background: var(--bg-card); border: 1px solid var(--border);"
              >
                <div class="text-sm font-semibold mb-2" style="color: var(--text-primary);">{{ card.title || card.target_type }}</div>
                <p class="text-sm leading-relaxed" style="color: var(--text-secondary);">{{ card.human_explanation }}</p>
                <div class="text-[11px] mt-3" style="color: var(--text-muted);">
                  evidence_ref: {{ card.evidence_refs?.join(', ') || card.evidence_ref || 'none' }}
                </div>
              </article>
            </div>
          </section>

          <section v-else class="py-12 text-sm" style="color: var(--text-secondary);" data-testid="no-cards-state">
            No user-facing cards are available for this status.
          </section>
        </div>
      </div>
    </main>

    <Transition name="slide-right">
      <aside
        v-if="store.isAskPanelOpen"
        class="w-80 flex-shrink-0 border-l hidden lg:flex flex-col"
        style="border-color: var(--border-subtle);"
      >
        <AskPanel />
      </aside>
    </Transition>

    <TextSelectionToolbar />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
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
const cards = ref<any>(null)
const degraded = ref(false)
const missingComponents = ref<string[]>([])
const isLoading = ref(true)
const error = ref('')
const activeTab = ref<'cards' | 'formulas' | 'patterns' | 'drill'>('cards')

const tabs = [
  { key: 'cards' as const, label: '论文卡片', icon: '📖' },
  { key: 'formulas' as const, label: '公式卡片', icon: '🔢' },
  { key: 'patterns' as const, label: '科研模式', icon: '🧩', disabled: true },
  { key: 'drill' as const, label: '训练题', icon: '🎯', disabled: true },
]

const status = computed(() => understandingStatus.value?.status || '')
const canShowCards = computed(() => ['SUCCESS', 'DEGRADED_STRUCTURAL'].includes(status.value))
const paperCard = computed(() => cards.value?.paper_card || null)
const formulaCardsList = computed(() => {
  const fc = cards.value?.formula_cards
  if (!fc) return []
  if (Array.isArray(fc)) return fc
  if (fc.formula_cards && Array.isArray(fc.formula_cards)) return fc.formula_cards
  return []
})

function normalizeFormulaCard(card: any): any {
  if (!card) return card
  return {
    ...card,
    formula_latex: card.formula_latex || card.formula_raw || '',
    problem: card.problem || card.purpose || card.intuition || '公式说明',
    formula_ref: card.formula_ref || card.location || card.formula_id || '',
    remove_effect: card.remove_effect || card.what_if_removed || '',
    weight_change_effect: card.weight_change_effect || card.weight_sensitivity || '',
    plain_summary: card.plain_summary || card.intuition || '',
  }
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
    ].filter(Boolean).join('。') + '。',
    deep_dive: card.experiment_summary?.text || '',
    evidence_status: card.evidence_status || 'UNKNOWN',
  }
}

function normalizeSkeleton(card: any): any {
  if (!card) return {}
  return {
    problem: { plain: card.problem?.text || '' },
    mechanism: { plain: card.method_overview?.text || '' },
  }
}

onMounted(async () => {
  store.currentJobId = jobId
  try {
    // Step 1: Get understanding status
    const statusRes = await fetch(`/api/v1/jobs/${jobId}/understanding_status`)
    if (!statusRes.ok) {
      if (statusRes.status === 404) {
        error.value = '分析结果不存在，该论文可能尚未完成分析'
      } else {
        error.value = '状态加载失败'
      }
      return
    }
    understandingStatus.value = (await statusRes.json()).understanding_status

    // Step 2: Get cards if status allows
    if (canShowCards.value) {
      const cardsRes = await fetch(`/api/v1/jobs/${jobId}/cards`)
      if (cardsRes.ok) {
        const cardsData = await cardsRes.json()
        cards.value = cardsData.cards
        degraded.value = cardsData.degraded || false
        missingComponents.value = cardsData.missing_components || []
      } else if (cardsRes.status === 409) {
        error.value = '卡片状态不一致，请重新分析'
      } else if (cardsRes.status === 403) {
        const detail = await cardsRes.json().catch(() => ({}))
        understandingStatus.value = {
          ...understandingStatus.value,
          status: detail.detail?.status || status.value,
          blocking_reason: detail.detail?.blocking_reason || '',
        }
      }
    }
  } catch {
    error.value = '网络错误，请稍后重试'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="flex h-[calc(100vh-56px)]">
    <!-- Sidebar -->
    <aside class="w-56 flex-shrink-0 border-r flex flex-col" style="border-color: var(--border-subtle); background: var(--bg-secondary);">
      <div class="p-4">
        <div class="text-[11px] font-semibold uppercase tracking-wider mb-3" style="color: var(--text-muted);">学习模块</div>
        <nav class="space-y-0.5">
          <button v-for="tab in tabs" :key="tab.key"
            @click="!tab.disabled && (activeTab = tab.key)"
            class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all"
            :class="tab.disabled ? 'opacity-40 cursor-not-allowed' : ''"
            :style="activeTab === tab.key && !tab.disabled
              ? 'background: var(--accent-light); color: var(--accent);'
              : 'color: var(--text-secondary);'"
          >
            <span class="text-base">{{ tab.icon }}</span>
            {{ tab.label }}
            <span v-if="tab.disabled" class="ml-auto text-[10px]" style="color: var(--text-muted);">未开放</span>
          </button>
        </nav>
      </div>

      <div v-if="understandingStatus" class="mt-auto p-4 border-t" style="border-color: var(--border-subtle);">
        <div class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--text-muted);">分析状态</div>
        <div class="text-xs" style="color: var(--text-secondary);">
          {{ status }}
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-2xl mx-auto px-8 py-10">
        <div v-if="isLoading" class="flex items-center justify-center py-32">
          <div class="text-sm" style="color: var(--text-muted);">加载中...</div>
        </div>

        <div v-else-if="error" class="flex flex-col items-center justify-center py-32">
          <div class="text-4xl mb-4">😔</div>
          <div class="text-sm font-medium mb-2" style="color: var(--text-primary);">{{ error }}</div>
          <button @click="router.push('/')"
            class="mt-4 px-4 py-2 rounded-xl text-[13px] font-medium transition-all hover:scale-105"
            style="background: var(--accent-light); color: var(--accent);">
            返回首页
          </button>
        </div>

        <div v-else>
          <!-- Status Banner -->
          <StatusBanner
            :status="status"
            :blockingReason="understandingStatus?.blocking_reason"
            :warnings="understandingStatus?.warnings"
            :missingComponents="missingComponents"
          />

          <!-- Cards Content -->
          <div v-if="canShowCards" class="space-y-6">
            <template v-if="activeTab === 'cards'">
              <PaperCard v-if="paperCard" :card="normalizePaperCard(paperCard)" :skeleton="normalizeSkeleton(paperCard)" />
              <div v-else class="text-center py-20">
                <div class="text-3xl mb-3">📖</div>
                <div class="text-sm" style="color: var(--text-muted);">暂无论文卡片</div>
              </div>
            </template>
            <template v-else-if="activeTab === 'formulas'">
              <FormulaCard v-for="(fc, i) in formulaCardsList" :key="i" :card="normalizeFormulaCard(fc)" />
              <div v-if="!formulaCardsList.length" class="text-center py-20">
                <div class="text-3xl mb-3">🔢</div>
                <div class="text-sm" style="color: var(--text-muted);">暂无公式卡片</div>
              </div>
            </template>
            <template v-else-if="activeTab === 'patterns'">
              <div class="text-center py-20">
                <div class="text-3xl mb-3">🧩</div>
                <div class="text-sm" style="color: var(--text-muted);">Phase 12 尚未开放</div>
              </div>
            </template>
            <template v-else-if="activeTab === 'drill'">
              <div class="text-center py-20">
                <div class="text-3xl mb-3">🎯</div>
                <div class="text-sm" style="color: var(--text-muted);">Phase 12 尚未开放</div>
              </div>
            </template>
          </div>

          <!-- Non-card status: show nothing more, banner already shown -->
          <div v-else class="text-center py-20">
            <button @click="router.push('/')"
              class="mt-4 px-4 py-2 rounded-xl text-[13px] font-medium transition-all hover:scale-105"
              style="background: var(--accent-light); color: var(--accent);">
              返回首页
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Ask Panel -->
    <Transition name="slide-right">
      <aside v-if="store.isAskPanelOpen"
        class="w-80 flex-shrink-0 border-l hidden lg:flex flex-col"
        style="border-color: var(--border-subtle);">
        <AskPanel />
      </aside>
    </Transition>

    <!-- Text Selection Toolbar -->
    <TextSelectionToolbar />
  </div>
</template>

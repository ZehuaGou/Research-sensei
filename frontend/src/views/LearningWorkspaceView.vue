<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLearningStore } from '../stores/learning'
import AskPanel from '../components/layout/AskPanel.vue'
import TextSelectionToolbar from '../components/interactive/TextSelectionToolbar.vue'
import PaperCard from '../components/cards/PaperCard.vue'
import FormulaCard from '../components/cards/FormulaCard.vue'
import PatternCard from '../components/cards/PatternCard.vue'
import DrillCard from '../components/cards/DrillCard.vue'

const route = useRoute()
const router = useRouter()
const store = useLearningStore()
const jobId = route.params.jobId as string
const bundle = ref<any>(null)
const isLoading = ref(true)
const error = ref('')
const activeTab = ref<'cards' | 'formulas' | 'patterns' | 'drill'>('cards')

const tabs = [
  { key: 'cards' as const, label: '教学卡片', icon: '📖' },
  { key: 'formulas' as const, label: '公式卡片', icon: '🔢' },
  { key: 'patterns' as const, label: '科研模式', icon: '🧩' },
  { key: 'drill' as const, label: '训练题', icon: '🎯' },
]

onMounted(async () => {
  store.currentJobId = jobId
  try {
    const res = await fetch(`/api/learn/${jobId}/bundle`)
    if (res.ok) {
      bundle.value = await res.json()
    } else {
      error.value = '学习数据加载失败，该论文可能尚未完成分析'
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
            @click="activeTab = tab.key"
            class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all"
            :style="activeTab === tab.key
              ? 'background: var(--accent-light); color: var(--accent);'
              : 'color: var(--text-secondary);'"
          >
            <span class="text-base">{{ tab.icon }}</span>
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <div v-if="bundle" class="mt-auto p-4 border-t" style="border-color: var(--border-subtle);">
        <div class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--text-muted);">论文概要</div>
        <div class="text-xs leading-relaxed line-clamp-3" style="color: var(--text-secondary);">
          {{ bundle.skeleton?.problem?.plain || '加载中...' }}
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

        <div v-else-if="bundle" class="space-y-6">
          <template v-if="activeTab === 'cards'">
            <PaperCard v-if="bundle.paper_card" :card="bundle.paper_card" :skeleton="bundle.skeleton" />
            <div v-else class="text-center py-20">
              <div class="text-3xl mb-3">📖</div>
              <div class="text-sm" style="color: var(--text-muted);">暂无教学卡片</div>
            </div>
          </template>
          <template v-else-if="activeTab === 'formulas'">
            <FormulaCard v-for="(fc, i) in bundle.formula_cards" :key="i" :card="fc" />
            <div v-if="!bundle.formula_cards?.length" class="text-center py-20">
              <div class="text-3xl mb-3">🔢</div>
              <div class="text-sm" style="color: var(--text-muted);">暂无公式卡片</div>
            </div>
          </template>
          <template v-else-if="activeTab === 'patterns'">
            <PatternCard v-if="bundle.pattern_card" :card="bundle.pattern_card" />
            <div v-else class="text-center py-20">
              <div class="text-3xl mb-3">🧩</div>
              <div class="text-sm" style="color: var(--text-muted);">暂无科研模式卡片</div>
            </div>
          </template>
          <template v-else-if="activeTab === 'drill'">
            <DrillCard v-if="bundle.drill_card" :card="bundle.drill_card" />
            <div v-else class="text-center py-20">
              <div class="text-3xl mb-3">🎯</div>
              <div class="text-sm" style="color: var(--text-muted);">暂无训练题</div>
            </div>
          </template>
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

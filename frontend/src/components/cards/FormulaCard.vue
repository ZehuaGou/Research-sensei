<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useLearningStore } from '../../stores/learning'

const props = defineProps<{ card: any }>()
const store = useLearningStore()
const expanded = ref(false)
const formulaEl = ref<HTMLElement>()
const renderError = ref(false)

onMounted(async () => {
  await nextTick()
  renderFormula()
})

async function renderFormula() {
  if (!formulaEl.value || !props.card.formula_latex) return
  try {
    const katex = await import('katex')
    katex.default.render(props.card.formula_latex, formulaEl.value, { displayMode: true, throwOnError: true })
  } catch {
    renderError.value = true
  }
}
</script>

<template>
  <div class="rounded-2xl overflow-hidden" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);">
    <div class="px-6 pt-6 pb-4">
      <div class="flex items-center gap-2 mb-3">
        <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold" style="background: var(--accent-light); color: var(--accent);">公式核心</span>
        <span v-if="card.evidence_status" class="px-2.5 py-1 rounded-full text-[11px] font-medium" style="background: rgba(16,185,129,0.08); color: #10b981;">
          {{ card.evidence_status }}
        </span>
      </div>
      <div class="text-sm font-medium" style="color: var(--text-primary);">{{ card.problem }}</div>
      <div class="text-[11px] mt-1" style="color: var(--text-muted);">§ {{ card.formula_ref }}</div>
    </div>

    <!-- Formula -->
    <div class="mx-6 p-5 rounded-xl text-center" style="background: var(--bg-secondary);">
      <div ref="formulaEl" style="color: var(--text-primary);"></div>
      <div v-if="renderError" class="text-[12px] py-2" style="color: var(--text-muted);">
        公式渲染失败: <code class="font-mono text-[11px]">{{ card.formula_latex }}</code>
      </div>
    </div>

    <!-- Symbol Table -->
    <div v-if="card.symbols?.length" class="px-6 py-4">
      <div class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--text-muted);">符号含义</div>
      <div class="rounded-xl overflow-hidden" style="border: 1px solid var(--border-subtle);">
        <table class="w-full text-[12px]">
          <thead>
            <tr style="background: var(--bg-secondary);">
              <th class="px-3 py-2 text-left font-semibold" style="color: var(--text-muted);">符号</th>
              <th class="px-3 py-2 text-left font-semibold" style="color: var(--text-muted);">含义</th>
              <th class="px-3 py-2 text-left font-semibold" style="color: var(--text-muted);">鼓励</th>
              <th class="px-3 py-2 text-left font-semibold" style="color: var(--text-muted);">惩罚</th>
              <th class="px-3 py-2 text-left font-semibold" style="color: var(--text-muted);">去掉会怎样</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in card.symbols" :key="s.symbol" class="border-t" style="border-color: var(--border-subtle);">
              <td class="px-3 py-2 font-mono font-medium" style="color: var(--accent);">{{ s.symbol }}</td>
              <td class="px-3 py-2" style="color: var(--text-secondary);">{{ s.meaning }}</td>
              <td class="px-3 py-2" style="color: var(--text-secondary);">{{ s.encourages || '-' }}</td>
              <td class="px-3 py-2" style="color: var(--text-secondary);">{{ s.penalizes || '-' }}</td>
              <td class="px-3 py-2" style="color: var(--text-secondary);">{{ s.if_removed || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="mx-6 border-t" style="border-color: var(--border-subtle);"></div>

    <!-- Numeric Example -->
    <div v-if="card.numeric_example" class="px-6 py-4">
      <div class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--text-muted);">小数字例子</div>
      <div class="text-[13px] rounded-xl p-3 font-mono whitespace-pre-wrap" style="background: var(--bg-secondary); color: var(--text-secondary);">
        {{ card.numeric_example }}
      </div>
    </div>

    <!-- Expand -->
    <div class="px-6 pb-4">
      <button @click="expanded = !expanded" class="text-[13px] font-medium" style="color: var(--accent);">
        {{ expanded ? '收起' : '更多分析' }}
      </button>
    </div>

    <Transition name="slide-up">
      <div v-if="expanded" class="px-6 pb-5 space-y-3 text-[13px]" style="color: var(--text-secondary);">
        <div v-if="card.remove_effect">
          <span class="font-semibold" style="color: var(--text-primary);">去掉该项：</span>{{ card.remove_effect }}
        </div>
        <div v-if="card.weight_change_effect">
          <span class="font-semibold" style="color: var(--text-primary);">权重变化：</span>{{ card.weight_change_effect }}
        </div>
        <div v-if="card.plain_summary" class="font-medium pt-1" style="color: var(--text-primary);">
          {{ card.plain_summary }}
        </div>
      </div>
    </Transition>

    <!-- Footer Actions -->
    <div class="px-6 py-4 border-t flex gap-2 flex-wrap" style="border-color: var(--border-subtle); background: var(--bg-secondary);">
      <button @click="store.setSelectedText(card.plain_summary || card.problem)"
        class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
        style="background: var(--accent-light); color: var(--accent);">
        💬 追问
      </button>
      <button @click="store.setSelectedText('请用更简单的方式解释这个公式：' + card.formula_latex)"
        class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
        style="background: rgba(16,185,129,0.08); color: #10b981;">
        📐 再推一步
      </button>
    </div>
  </div>
</template>

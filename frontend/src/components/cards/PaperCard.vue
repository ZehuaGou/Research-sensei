<script setup lang="ts">
import { ref } from 'vue'
import { useLearningStore } from '../../stores/learning'

const props = defineProps<{ card: any; skeleton: any }>()
const store = useLearningStore()
const expanded = ref(false)

function copyText() {
  const text = props.card.thirty_second + '\n\n' + props.card.five_minute
  navigator.clipboard.writeText(text)
}
</script>

<template>
  <div class="rounded-2xl overflow-hidden" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);">
    <!-- Header -->
    <div class="px-6 pt-6 pb-4">
      <div class="flex items-center gap-2 mb-3">
        <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold" style="background: var(--accent-light); color: var(--accent);">论文核心</span>
        <span class="px-2.5 py-1 rounded-full text-[11px] font-medium" style="background: rgba(16,185,129,0.08); color: #10b981;">
          证据: {{ card.evidence_status }}
        </span>
      </div>
      <!-- Difficulty tags -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-medium" style="background: rgba(239,68,68,0.08); color: #ef4444;">必须掌握</span>
      </div>
    </div>

    <!-- 30-Second Summary -->
    <div class="px-6 pb-5">
      <div class="flex items-center gap-2 mb-2.5">
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: var(--accent-light); color: var(--accent);">1</div>
        <h2 class="text-[13px] font-semibold" style="color: var(--text-primary);">30 秒看懂</h2>
      </div>
      <p class="text-[13px] leading-relaxed pl-8" style="color: var(--text-secondary);">{{ card.thirty_second }}</p>
    </div>

    <div class="mx-6 border-t" style="border-color: var(--border-subtle);"></div>

    <!-- 5-Minute Summary -->
    <div class="px-6 py-5">
      <div class="flex items-center gap-2 mb-2.5">
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: rgba(16,185,129,0.08); color: #10b981;">2</div>
        <h3 class="text-[13px] font-semibold" style="color: var(--text-primary);">5 分钟理解</h3>
      </div>
      <p class="text-[13px] leading-relaxed pl-8" style="color: var(--text-secondary);">{{ card.five_minute }}</p>
    </div>

    <div class="mx-6 border-t" style="border-color: var(--border-subtle);"></div>

    <!-- Key Takeaways -->
    <div class="px-6 py-5">
      <div class="flex items-center gap-2 mb-2.5">
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: rgba(245,158,11,0.08); color: #f59e0b;">3</div>
        <h3 class="text-[13px] font-semibold" style="color: var(--text-primary);">记住这几点</h3>
      </div>
      <ul class="pl-8 space-y-1.5 text-[13px]" style="color: var(--text-secondary);">
        <li v-if="skeleton?.problem?.plain" class="flex items-start gap-2">
          <span class="mt-1 w-1.5 h-1.5 rounded-full shrink-0" style="background: var(--accent);"></span>
          <span>{{ skeleton.problem.plain }}</span>
        </li>
        <li v-if="skeleton?.mechanism?.plain" class="flex items-start gap-2">
          <span class="mt-1 w-1.5 h-1.5 rounded-full shrink-0" style="background: #10b981;"></span>
          <span>{{ skeleton.mechanism.plain }}</span>
        </li>
      </ul>
    </div>

    <!-- Expand Button -->
    <div class="px-6 pb-4">
      <button @click="expanded = !expanded"
        class="text-[13px] font-medium transition-colors pl-8"
        style="color: var(--accent);">
        {{ expanded ? '收起' : '展开深入分析' }}
      </button>
    </div>

    <!-- Deep Dive -->
    <Transition name="slide-up">
      <div v-if="expanded" class="px-6 pb-5">
        <div class="mx-0 mb-5 border-t" style="border-color: var(--border-subtle);"></div>
        <div class="flex items-center gap-2 mb-2.5">
          <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: rgba(251,191,36,0.1); color: #f59e0b;">4</div>
          <h3 class="text-[13px] font-semibold" style="color: var(--text-primary);">深入分析</h3>
        </div>
        <p class="text-[13px] leading-relaxed pl-8" style="color: var(--text-secondary);">{{ card.deep_dive }}</p>
      </div>
    </Transition>

    <!-- Skeleton Info -->
    <div v-if="skeleton?.problem || skeleton?.mechanism?.plain"
      class="mx-6 mb-5 p-4 rounded-xl text-[13px] space-y-2"
      style="background: var(--bg-secondary);">
      <div v-if="skeleton?.problem">
        <span class="font-semibold" style="color: var(--text-primary);">问题：</span>
        <span style="color: var(--text-secondary);">{{ skeleton.problem.plain }}</span>
      </div>
      <div v-if="skeleton?.mechanism?.plain">
        <span class="font-semibold" style="color: var(--text-primary);">机制：</span>
        <span style="color: var(--text-secondary);">{{ skeleton.mechanism.plain }}</span>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="px-6 py-4 border-t flex gap-2 flex-wrap" style="border-color: var(--border-subtle); background: var(--bg-secondary);">
      <button @click="store.setSelectedText(card.thirty_second)"
        class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
        style="background: var(--accent-light); color: var(--accent);">
        💬 追问
      </button>
      <button @click="store.setSelectedText('请用更简单的方式解释：' + card.thirty_second)"
        class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
        style="background: rgba(16,185,129,0.08); color: #10b981;">
        📝 复述
      </button>
      <button @click="copyText"
        class="px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all hover:scale-105"
        style="background: rgba(245,158,11,0.08); color: #f59e0b;">
        📋 复制
      </button>
    </div>
  </div>
</template>

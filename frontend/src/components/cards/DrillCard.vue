<script setup lang="ts">
const props = defineProps<{ card: any }>()
</script>

<template>
  <div class="rounded-2xl overflow-hidden" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);">
    <div class="px-6 pt-6 pb-4">
      <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold" style="background: rgba(239,68,68,0.08); color: #ef4444;">训练题</span>
    </div>

    <!-- Recall -->
    <div v-if="card.recall_questions?.length" class="px-6 pb-5">
      <div class="flex items-center gap-2 mb-2.5">
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: rgba(239,68,68,0.08); color: #ef4444;">1</div>
        <h4 class="text-[13px] font-semibold" style="color: var(--text-primary);">立即复述</h4>
      </div>
      <ol class="list-decimal list-inside space-y-1.5 text-[13px] pl-8" style="color: var(--text-secondary);">
        <li v-for="(q, i) in card.recall_questions" :key="i">{{ q }}</li>
      </ol>
    </div>

    <div v-if="card.recall_questions?.length && card.advisor_questions?.length"
      class="mx-6 border-t" style="border-color: var(--border-subtle);"></div>

    <!-- Advisor -->
    <div v-if="card.advisor_questions?.length" class="px-6 py-5">
      <div class="flex items-center gap-2 mb-2.5">
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: rgba(245,158,11,0.08); color: #f59e0b;">2</div>
        <h4 class="text-[13px] font-semibold" style="color: var(--text-primary);">导师追问</h4>
      </div>
      <ol class="list-decimal list-inside space-y-1.5 text-[13px] pl-8" style="color: var(--text-secondary);">
        <li v-for="(q, i) in card.advisor_questions" :key="i">{{ q }}</li>
      </ol>
    </div>

    <div v-if="card.advisor_questions?.length && card.error_attribution_prompts?.length"
      class="mx-6 border-t" style="border-color: var(--border-subtle);"></div>

    <!-- Weakness Check -->
    <div v-if="card.error_attribution_prompts?.length" class="px-6 py-5">
      <div class="flex items-center gap-2 mb-2.5">
        <div class="w-6 h-6 rounded-md flex items-center justify-center text-xs" style="background: rgba(16,185,129,0.08); color: #10b981;">3</div>
        <h4 class="text-[13px] font-semibold" style="color: var(--text-primary);">薄弱点检查</h4>
      </div>
      <ol class="list-decimal list-inside space-y-1.5 text-[13px] pl-8" style="color: var(--text-secondary);">
        <li v-for="(q, i) in card.error_attribution_prompts" :key="i">{{ q }}</li>
      </ol>
    </div>
  </div>
</template>

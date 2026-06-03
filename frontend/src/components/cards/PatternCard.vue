<script setup lang="ts">
const props = defineProps<{ card: any }>()
</script>

<template>
  <div class="rounded-2xl overflow-hidden" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);">
    <div class="px-6 pt-6 pb-4">
      <span class="px-2.5 py-1 rounded-full text-[11px] font-semibold" style="background: rgba(251,191,36,0.08); color: #f59e0b;">科研模式</span>
      <h3 class="text-[15px] font-semibold mt-3" style="color: var(--text-primary);">{{ card.pattern_id }}</h3>
      <p class="text-[13px] mt-1.5 leading-relaxed" style="color: var(--text-secondary);">{{ card.definition }}</p>
    </div>

    <div v-if="card.signals?.length" class="px-6 pb-4">
      <div class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--text-muted);">信号</div>
      <div class="flex flex-wrap gap-1.5">
        <span v-for="s in card.signals" :key="s"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium"
          style="background: var(--bg-secondary); color: var(--text-secondary);">
          {{ s }}
        </span>
      </div>
    </div>

    <div v-if="card.transfer_template" class="px-6 py-4 border-t" style="border-color: var(--border-subtle);">
      <div class="text-[11px] font-semibold uppercase tracking-wider mb-1.5" style="color: var(--text-muted);">迁移指导</div>
      <p class="text-[13px] leading-relaxed" style="color: var(--text-secondary);">{{ card.transfer_template }}</p>
    </div>
  </div>
</template>

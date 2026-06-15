<script setup lang="ts">
defineProps<{
  status?: string
  warnings?: Array<{ code: string; message: string }>
}>()
</script>

<template>
  <section
    class="rounded-lg p-4"
    style="background: var(--bg-card); border: 1px solid var(--border);"
    data-testid="seed-expansion-panel"
  >
    <div class="text-sm font-semibold mb-1" style="color: var(--text-primary);">SeedExpansionPanel</div>
    <div class="text-xs font-medium mb-3" style="color: #f59e0b;">
      {{ status || 'NOT_IMPLEMENTED' }}
    </div>
    <div class="text-xs leading-relaxed" style="color: var(--text-secondary);">
      Seed expansion is not implemented yet. No seed papers are synthesized or faked.
    </div>
    <div v-if="warnings?.length" class="mt-3 space-y-1">
      <div v-for="warning in warnings" :key="warning.code" class="text-xs" style="color: var(--text-muted);">
        {{ warning.code }}: {{ warning.message }}
      </div>
    </div>
  </section>
</template>

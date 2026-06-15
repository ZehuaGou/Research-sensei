<script setup lang="ts">
import { ref } from 'vue'
import SeedExpansionPanel from '../components/SeedExpansionPanel.vue'

const query = ref('')
const isLoading = ref(false)
const error = ref('')
const result = ref<Record<string, any> | null>(null)

async function search() {
  if (!query.value.trim() || isLoading.value) return
  isLoading.value = true
  error.value = ''
  result.value = null
  try {
    const res = await fetch('/api/v1/directions/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.value.trim() }),
    })
    const data = await res.json().catch(() => ({}))
    result.value = data
    if (!res.ok) {
      error.value = data.detail?.message || 'DirectionWorkspace request failed.'
    }
  } catch {
    error.value = 'Network error while loading DirectionWorkspace.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto px-6 py-12">
    <header class="mb-8">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">DirectionWorkspace</h1>
      <p class="text-sm" style="color: var(--text-secondary);">Direction discovery is explicit about unimplemented backend paths.</p>
    </header>

    <form class="flex gap-2 mb-6" @submit.prevent="search">
      <input
        v-model="query"
        data-testid="direction-query"
        class="flex-1 px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="time-series anomaly detection"
      />
      <button
        type="submit"
        class="px-4 py-2 rounded-md text-sm font-semibold text-white disabled:opacity-40"
        style="background: var(--accent);"
        :disabled="isLoading || !query.trim()"
      >
        {{ isLoading ? 'Checking...' : 'Check' }}
      </button>
    </form>

    <section
      v-if="result"
      class="rounded-lg p-4 mb-5"
      style="background: var(--bg-card); border: 1px solid var(--border);"
      data-testid="direction-status"
    >
      <div class="text-sm font-semibold mb-1" style="color: var(--text-primary);">
        {{ result.direction_workspace_status || result.status }}
      </div>
      <div class="text-xs mb-3" style="color: var(--text-secondary);">{{ result.message }}</div>
      <div v-if="result.warnings?.length" class="space-y-1">
        <div v-for="warning in result.warnings" :key="warning.code" class="text-xs" style="color: var(--text-muted);">
          {{ warning.code }}: {{ warning.message }}
        </div>
      </div>
    </section>

    <div v-if="error" class="mb-5 px-4 py-3 rounded-md text-sm" style="background: rgba(239,68,68,0.08); color: #ef4444;">
      {{ error }}
    </div>

    <SeedExpansionPanel
      :status="result?.seed_expansion_status || 'NOT_IMPLEMENTED'"
      :warnings="result?.warnings"
    />
  </div>
</template>

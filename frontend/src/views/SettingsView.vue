<script setup lang="ts">
import { ref, onMounted } from 'vue'

const settings = ref({ base_url: '', api_key_env: '', model: '', active_provider: '' })
const testResult = ref('')
const isTesting = ref(false)

onMounted(async () => {
  try {
    const res = await fetch('/api/settings')
    if (res.ok) settings.value = await res.json()
  } catch {}
})

async function testConnection() {
  isTesting.value = true
  testResult.value = ''
  try {
    const res = await fetch('/api/settings/test', { method: 'POST' })
    const data = await res.json()
    testResult.value = data.message || (data.ok ? '连接成功' : '连接失败')
  } catch { testResult.value = '请求失败' }
  finally { isTesting.value = false }
}
</script>

<template>
  <div class="max-w-lg mx-auto px-6 py-20">
    <div class="text-center mb-10">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">模型设置</h1>
      <p class="text-sm" style="color: var(--text-secondary);">当前使用 {{ settings.active_provider }} 提供商</p>
    </div>

    <div class="rounded-2xl p-6 space-y-5" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);">
      <div>
        <label class="block text-[12px] font-semibold uppercase tracking-wider mb-1.5" style="color: var(--text-muted);">API Base URL</label>
        <input v-model="settings.base_url" readonly
          class="w-full px-3.5 py-2.5 rounded-xl text-[13px]"
          style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); color: var(--text-primary);" />
      </div>
      <div>
        <label class="block text-[12px] font-semibold uppercase tracking-wider mb-1.5" style="color: var(--text-muted);">API Key 环境变量</label>
        <input v-model="settings.api_key_env" readonly
          class="w-full px-3.5 py-2.5 rounded-xl text-[13px]"
          style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); color: var(--text-primary);" />
      </div>
      <div>
        <label class="block text-[12px] font-semibold uppercase tracking-wider mb-1.5" style="color: var(--text-muted);">模型</label>
        <input v-model="settings.model" readonly
          class="w-full px-3.5 py-2.5 rounded-xl text-[13px]"
          style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); color: var(--text-primary);" />
      </div>

      <button @click="testConnection" :disabled="isTesting"
        class="w-full py-2.5 rounded-xl text-[13px] font-medium text-white transition-all disabled:opacity-40 hover:scale-[1.01]"
        style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
        {{ isTesting ? '测试中...' : '测试连接' }}
      </button>

      <div v-if="testResult" class="px-4 py-3 rounded-xl text-[13px]"
        style="background: var(--bg-secondary); color: var(--text-secondary);">
        {{ testResult }}
      </div>
    </div>
  </div>
</template>

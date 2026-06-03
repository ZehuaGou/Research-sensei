<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')
const isLoading = ref(false)
const error = ref('')
const searchComplete = ref(false)

const suggestions = ['时间序列异常检测', 'RAG 可信性', '大模型推理优化', '图神经网络']

async function search() {
  if (!query.value.trim()) return
  isLoading.value = true
  error.value = ''
  searchComplete.value = false
  try {
    const res = await fetch('/api/directions/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.value }),
    })
    if (!res.ok) throw new Error('搜索失败')
    await res.json()
    // Jobs are generated in background, redirect to home to see results
    searchComplete.value = true
    setTimeout(() => router.push('/'), 1500)
  } catch (e: any) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto px-6 py-20">
    <div class="text-center mb-10">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">搜索研究方向</h1>
      <p class="text-sm" style="color: var(--text-secondary);">输入关键词，系统会检索相关论文并生成精读计划</p>
    </div>

    <form @submit.prevent="search" class="relative">
      <input
        v-model="query"
        placeholder="输入研究方向，如：时间序列异常检测"
        class="w-full px-5 py-4 rounded-2xl text-sm outline-none transition-all"
        style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary); box-shadow: var(--shadow-md);"
      />
      <button
        type="submit"
        :disabled="isLoading || !query.trim()"
        class="absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 rounded-xl text-sm font-medium text-white transition-all disabled:opacity-40 hover:scale-105"
        style="background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 2px 8px rgba(99,102,241,0.3);"
      >
        {{ isLoading ? '搜索中...' : '搜索' }}
      </button>
    </form>

    <div v-if="error" class="mt-4 px-4 py-3 rounded-xl text-sm" style="background: rgba(239,68,68,0.08); color: #ef4444;">
      {{ error }}
    </div>

    <div v-if="searchComplete" class="mt-4 px-4 py-3 rounded-xl text-sm" style="background: rgba(16,185,129,0.08); color: #10b981;">
      ✅ 搜索完成！正在后台生成学习卡片，即将跳转到首页...
    </div>

    <!-- Suggestions -->
    <div class="mt-8 flex flex-wrap gap-2 justify-center">
      <button v-for="s in suggestions" :key="s"
        @click="query = s"
        class="px-4 py-2 rounded-full text-xs font-medium transition-all hover:scale-105"
        style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary);">
        {{ s }}
      </button>
    </div>
  </div>
</template>

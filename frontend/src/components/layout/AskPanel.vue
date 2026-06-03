<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useLearningStore } from '../../stores/learning'

const store = useLearningStore()
const input = ref('')
const chatContainer = ref<HTMLElement>()
const isLoading = ref(false)

async function send() {
  const question = input.value.trim()
  if (!question || isLoading.value) return

  store.addMessage({ role: 'user', content: question, timestamp: Date.now() })
  input.value = ''
  isLoading.value = true

  await nextTick()
  chatContainer.value?.scrollTo({ top: chatContainer.value.scrollHeight, behavior: 'smooth' })

  try {
    const res = await fetch('/api/interactive/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: store.currentJobId,
        question,
        selected_text: store.selectedText,
      }),
    })
    const data = await res.json()
    store.addMessage({ role: 'assistant', content: data.answer_zh || data.answer || '暂时无法回答', timestamp: Date.now() })
  } catch {
    store.addMessage({ role: 'assistant', content: '请求失败，请稍后重试', timestamp: Date.now() })
  } finally {
    isLoading.value = false
    await nextTick()
    chatContainer.value?.scrollTo({ top: chatContainer.value.scrollHeight, behavior: 'smooth' })
  }
}

watch(() => store.selectedText, (text) => {
  if (text) input.value = `请解释：${text}`
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="px-5 py-4 border-b flex items-center justify-between" style="border-color: var(--border-subtle);">
      <div>
        <div class="text-[13px] font-semibold" style="color: var(--text-primary);">追问导师</div>
        <div class="text-[11px] mt-0.5" style="color: var(--text-muted);">选中文字或直接提问</div>
      </div>
      <button @click="store.isAskPanelOpen = !store.isAskPanelOpen"
        class="w-7 h-7 rounded-lg flex items-center justify-center text-[11px] transition-all hover:scale-110"
        style="background: var(--bg-secondary); color: var(--text-muted);">
        {{ store.isAskPanelOpen ? '›' : '‹' }}
      </button>
    </div>

    <!-- Selected Text Context -->
    <div v-if="store.selectedText" class="px-4 py-2 border-b text-[11px]" style="border-color: var(--border-subtle); background: var(--bg-secondary); color: var(--text-muted);">
      📌 选中: <span class="font-medium" style="color: var(--text-secondary);">{{ store.selectedText.slice(0, 50) }}{{ store.selectedText.length > 50 ? '...' : '' }}</span>
    </div>

    <!-- Messages -->
    <div ref="chatContainer" class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
      <div v-for="(msg, i) in store.chatHistory" :key="i"
        class="max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed"
        :class="msg.role === 'user' ? 'ml-auto rounded-br-md' : 'rounded-bl-md'"
        :style="msg.role === 'user'
          ? 'background: var(--accent); color: white;'
          : 'background: var(--bg-secondary); color: var(--text-secondary);'"
      >
        {{ msg.content }}
      </div>

      <div v-if="isLoading" class="flex items-center gap-1.5 px-1">
        <div class="w-1.5 h-1.5 rounded-full animate-pulse" style="background: var(--text-muted);"></div>
        <div class="w-1.5 h-1.5 rounded-full animate-pulse" style="background: var(--text-muted); animation-delay: 0.2s;"></div>
        <div class="w-1.5 h-1.5 rounded-full animate-pulse" style="background: var(--text-muted); animation-delay: 0.4s;"></div>
      </div>

      <div v-if="!store.chatHistory.length && !isLoading" class="flex flex-col items-center justify-center h-full py-12">
        <div class="text-3xl mb-3">💬</div>
        <div class="text-[13px]" style="color: var(--text-muted);">选中文字或直接提问</div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="px-4 pb-2">
      <div class="flex gap-1.5 flex-wrap">
        <button @click="input = '没看懂，请用更简单的方式解释'"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
          style="background: var(--bg-secondary); color: var(--text-muted);">
          没看懂
        </button>
        <button @click="input = '再讲简单点，用生活中的例子类比'"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
          style="background: var(--bg-secondary); color: var(--text-muted);">
          简单类比
        </button>
        <button @click="input = '举个数字例子'"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
          style="background: var(--bg-secondary); color: var(--text-muted);">
          举例子
        </button>
        <button @click="input = '请一步步推导'"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
          style="background: var(--bg-secondary); color: var(--text-muted);">
          推导
        </button>
        <button @click="input = '导师会怎么追问这个点？'"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
          style="background: var(--bg-secondary); color: var(--text-muted);">
          导师追问
        </button>
        <button @click="input = '出题考考我'"
          class="px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors"
          style="background: var(--bg-secondary); color: var(--text-muted);">
          出题考我
        </button>
      </div>
    </div>

    <!-- Input -->
    <div class="px-4 pb-4">
      <form @submit.prevent="send" class="flex gap-2">
        <input v-model="input" placeholder="输入问题..."
          class="flex-1 px-3.5 py-2.5 rounded-xl text-[13px] outline-none transition-all"
          style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); color: var(--text-primary);" />
        <button type="submit" :disabled="!input.trim() || isLoading"
          class="px-3.5 py-2.5 rounded-xl text-[13px] font-medium text-white disabled:opacity-30 transition-all hover:scale-105"
          style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
          发送
        </button>
      </form>
    </div>
  </div>
</template>

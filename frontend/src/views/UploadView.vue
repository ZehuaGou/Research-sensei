<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const file = ref<File | null>(null)
const isDragging = ref(false)
const isUploading = ref(false)

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] || null
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const f = e.dataTransfer?.files[0]
  if (f && f.type === 'application/pdf') file.value = f
}

async function upload() {
  if (!file.value) return
  isUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    const res = await fetch('/api/v1/documents/parse', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json()
    if (res.ok && data.job_id) {
      router.push(`/learn/${data.job_id}`)
    } else {
      alert(data.detail || data.error || '上传失败')
    }
  } catch {
    alert('网络错误，请稍后重试')
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="max-w-xl mx-auto px-6 py-20">
    <div class="text-center mb-10">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">上传论文</h1>
      <p class="text-sm" style="color: var(--text-secondary);">上传 PDF，自动生成结构化精读卡片</p>
    </div>

    <div
      class="relative rounded-2xl p-10 text-center transition-all cursor-pointer"
      :class="isDragging ? 'scale-[1.02]' : ''"
      style="background: var(--bg-card); border: 2px dashed var(--border);"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input type="file" accept=".pdf" @change="onFileChange" class="hidden" id="file-input" />
      <label for="file-input" class="cursor-pointer block">
        <div v-if="!file">
          <div class="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style="background: var(--accent-light);">
            📄
          </div>
          <div class="font-medium text-sm mb-1" style="color: var(--text-primary);">
            拖拽 PDF 到此处，或点击选择
          </div>
          <div class="text-xs" style="color: var(--text-muted);">支持 .pdf 格式，最大 80MB</div>
        </div>
        <div v-else class="flex items-center justify-center gap-3">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center text-lg" style="background: rgba(16,185,129,0.1);">
            ✓
          </div>
          <div class="text-left">
            <div class="font-medium text-sm" style="color: var(--text-primary);">{{ file.name }}</div>
            <div class="text-xs" style="color: var(--text-muted);">{{ (file.size / 1024 / 1024).toFixed(1) }} MB</div>
          </div>
        </div>
      </label>
    </div>

    <button
      v-if="file"
      @click="upload"
      :disabled="isUploading"
      class="mt-6 w-full py-3.5 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-40 hover:scale-[1.01]"
      style="background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 4px 14px rgba(99,102,241,0.3);"
    >
      {{ isUploading ? '分析中...' : '开始分析' }}
    </button>
  </div>
</template>

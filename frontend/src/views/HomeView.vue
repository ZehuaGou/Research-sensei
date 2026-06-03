<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const recentJobs = ref<any[]>([])

onMounted(async () => {
  try {
    const res = await fetch('/api/jobs')
    if (res.ok) recentJobs.value = await res.json()
  } catch {}
})
</script>

<template>
  <div class="min-h-[calc(100vh-56px)] flex flex-col">
    <!-- Hero -->
    <div class="px-6 pt-20 pb-16 text-center">
      <h1 class="text-[42px] font-bold tracking-tight leading-tight mb-4">
        <span class="gradient-text">AI 科研导师</span>
      </h1>
      <p class="text-lg max-w-xl mx-auto" style="color: var(--text-secondary);">
        上传论文或搜索方向，获得结构化精读卡片、公式拆解、和交互式问答
      </p>
    </div>

    <!-- Action Cards -->
    <div class="max-w-3xl mx-auto px-6 pb-16 w-full">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <button
          @click="router.push('/directions/new')"
          class="card-hover group p-7 rounded-2xl text-left"
          style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);"
        >
          <div class="w-11 h-11 rounded-xl flex items-center justify-center text-xl mb-4 transition-transform group-hover:scale-110" style="background: var(--accent-light);">
            🔍
          </div>
          <div class="font-semibold text-[15px] mb-1.5" style="color: var(--text-primary);">搜索研究方向</div>
          <div class="text-[13px] leading-relaxed" style="color: var(--text-secondary);">
            输入方向关键词，自动检索论文并生成学习计划
          </div>
        </button>

        <button
          @click="router.push('/papers/upload')"
          class="card-hover group p-7 rounded-2xl text-left"
          style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);"
        >
          <div class="w-11 h-11 rounded-xl flex items-center justify-center text-xl mb-4 transition-transform group-hover:scale-110" style="background: rgba(16,185,129,0.1);">
            📄
          </div>
          <div class="font-semibold text-[15px] mb-1.5" style="color: var(--text-primary);">上传论文</div>
          <div class="text-[13px] leading-relaxed" style="color: var(--text-secondary);">
            上传 PDF，自动生成五层教学卡片
          </div>
        </button>
      </div>
    </div>

    <!-- Recent Jobs -->
    <div v-if="recentJobs.length" class="max-w-3xl mx-auto px-6 pb-20 w-full">
      <div class="rounded-2xl overflow-hidden" style="background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-sm);">
        <div class="px-6 py-4 border-b" style="border-color: var(--border-subtle);">
          <h2 class="text-[13px] font-semibold uppercase tracking-wider" style="color: var(--text-muted);">最近学习</h2>
        </div>
        <div class="divide-y" style="border-color: var(--border-subtle);">
          <div v-for="job in recentJobs" :key="job.job_id"
            class="px-6 py-4 flex items-center justify-between transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.02]">
            <div class="min-w-0">
              <div class="font-medium text-sm truncate" style="color: var(--text-primary);">{{ job.filename }}</div>
              <div class="text-xs mt-0.5" style="color: var(--text-muted);">{{ job.status }}</div>
            </div>
            <router-link :to="`/learn/${job.job_id}`"
              class="ml-4 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all hover:scale-105 shrink-0"
              style="background: var(--accent-light); color: var(--accent);">
              继续学习
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

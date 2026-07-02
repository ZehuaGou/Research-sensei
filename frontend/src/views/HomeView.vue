<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const recentJobs = ref<any[]>([])
const deletingJobId = ref('')
const deleteMessage = ref('')
const deletedJobIds = ref<Set<string>>(new Set())

onMounted(() => {
  deletedJobIds.value = loadDeletedJobIds()
  void loadRecentJobs()
})

async function loadRecentJobs() {
  try {
    const res = await fetch('/api/v1/jobs')
    if (res.ok) {
      const data = await res.json()
      const jobs = Array.isArray(data.jobs) ? data.jobs : []
      recentJobs.value = jobs
        .filter((job: any) => !deletedJobIds.value.has(String(job.job_id || '')))
        .slice(0, 8)
    }
  } catch {}
}

async function deleteJob(jobId: string) {
  if (!jobId || deletingJobId.value) return
  deletingJobId.value = jobId
  deleteMessage.value = ''
  try {
    const res = await fetch(`/api/v1/jobs/${jobId}`, { method: 'DELETE' })
    if (res.ok || res.status === 404) {
      rememberDeletedJobId(jobId)
      recentJobs.value = recentJobs.value.filter(job => job.job_id !== jobId)
      deleteMessage.value = '已从最近任务移除。'
    } else {
      deleteMessage.value = '删除失败，请确认后端服务已更新并正在运行。'
    }
  } catch {
    deleteMessage.value = '删除请求失败，请确认后端服务正在运行。'
  } finally {
    deletingJobId.value = ''
  }
}

function loadDeletedJobIds() {
  if (typeof window === 'undefined') return new Set<string>()
  try {
    const raw = window.localStorage.getItem('researchsensei.deletedJobIds') || '[]'
    const values = JSON.parse(raw)
    return new Set(Array.isArray(values) ? values.map(String) : [])
  } catch {
    return new Set<string>()
  }
}

function rememberDeletedJobId(jobId: string) {
  deletedJobIds.value = new Set([...deletedJobIds.value, jobId])
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(
      'researchsensei.deletedJobIds',
      JSON.stringify([...deletedJobIds.value].slice(-200)),
    )
  }
}

function jobTitle(job: any) {
  return job.source_path?.split(/[\\/]/).pop() || job.title || job.job_id || '未命名论文'
}

function statusText(status: string) {
  const map: Record<string, string> = {
    succeeded: '已完成',
    running: '处理中',
    queued: '排队中',
    failed: '失败',
  }
  return map[String(status).toLowerCase()] || status || '未知'
}
</script>

<template>
  <main class="home-shell">
    <section class="home-intro">
      <p class="eyebrow">Research Sensei</p>
      <h1>把论文变成可以追问、可以复习的中文阅读工作台</h1>
      <p class="intro-copy">
        默认通过 ccswitch 调用你当前选中的模型。系统会先生成有证据引用的论文卡片、公式卡片和教学卡片，然后进入 M4 助教对话。
      </p>
    </section>

    <section class="action-grid" aria-label="主要入口">
      <button type="button" class="entry-card" @click="router.push('/directions/new')">
        <span class="entry-icon">研</span>
        <span>
          <strong>找研究方向</strong>
          <small>输入一个方向，生成候选论文、阅读顺序和可深读入口。</small>
        </span>
      </button>

      <button type="button" class="entry-card" @click="router.push('/papers/upload')">
        <span class="entry-icon green">读</span>
        <span>
          <strong>深读一篇论文</strong>
          <small>上传 PDF、粘贴 arXiv/DOI/PDF 链接，进入 M2+M4 工作流。</small>
        </span>
      </button>
    </section>

    <section class="recent surface" v-if="recentJobs.length">
      <header>
        <h2>最近任务</h2>
        <button type="button" class="secondary-btn" @click="router.push('/papers/upload')">新建深读</button>
      </header>
      <p v-if="deleteMessage" class="delete-message">{{ deleteMessage }}</p>
      <div class="job-list">
        <article v-for="job in recentJobs" :key="job.job_id" class="job-row">
          <div class="job-main">
            <h3>{{ jobTitle(job) }}</h3>
            <p>{{ statusText(job.status) }} · {{ job.current_step || '等待状态更新' }}</p>
          </div>
          <div class="job-actions">
            <button
              type="button"
              class="ghost-btn danger"
              data-testid="delete-job"
              :disabled="deletingJobId === job.job_id"
              @click="deleteJob(job.job_id)"
            >
              {{ deletingJobId === job.job_id ? '删除中' : '删除' }}
            </button>
            <router-link class="ghost-btn" :to="`/learn/${job.job_id}`">继续</router-link>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<style scoped>
.home-shell {
  width: min(1100px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 56px 0 72px;
}

.home-intro {
  max-width: 780px;
  margin-bottom: 28px;
}

.eyebrow {
  color: var(--accent);
  font-size: 14px;
  font-weight: 800;
}

h1 {
  margin-top: 10px;
  color: var(--text-primary);
  font-size: clamp(32px, 5vw, 56px);
  font-weight: 900;
  line-height: 1.1;
}

.intro-copy {
  margin-top: 18px;
  color: var(--text-secondary);
  font-size: 18px;
  line-height: 1.8;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}

.entry-card {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 22px;
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
  text-align: left;
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.entry-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--accent) 36%, var(--border));
  box-shadow: var(--shadow-md);
}

.entry-icon {
  display: flex;
  width: 48px;
  height: 48px;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: var(--accent-light);
  color: var(--accent);
  font-size: 22px;
  font-weight: 900;
}

.entry-icon.green {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.entry-card strong {
  display: block;
  color: var(--text-primary);
  font-size: 19px;
}

.entry-card small {
  display: block;
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.7;
}

.recent {
  padding: 8px;
}

.recent header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
}

.recent h2 {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 800;
}

.delete-message {
  margin: 0 16px 10px;
  border-radius: 8px;
  padding: 8px 10px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.job-list {
  display: grid;
  gap: 2px;
}

.job-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-radius: 12px;
  padding: 14px 16px;
}

.job-row:hover {
  background: var(--bg-secondary);
}

.job-main {
  min-width: 0;
}

.job-main h3 {
  overflow: hidden;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-main p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.job-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
}

.danger {
  color: #dc2626;
}

.danger:hover:not(:disabled) {
  background: rgba(220, 38, 38, 0.08);
}

@media (max-width: 760px) {
  .home-shell {
    padding-top: 32px;
  }

  .action-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 34px;
  }

  .job-row {
    align-items: flex-start;
  }

  .job-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiClientError, learningApi } from '../api/client'
import type {
  LearningAttempt,
  LearningOverview,
  LearningPaperSummary,
  LearningSession,
} from '../types/learning'

const route = useRoute()
const router = useRouter()
const overview = ref<LearningOverview>(emptyOverview())
const session = ref<LearningSession | null>(null)
const latestAttempt = ref<LearningAttempt | null>(null)
const answer = ref('')
const activeJobId = ref('')
const loading = ref(true)
const starting = ref(false)
const submitting = ref(false)
const error = ref('')
const message = ref('')

const routeJobId = computed(() => String(route.params.jobId || '').trim())
const activePaper = computed(() =>
  overview.value.papers.find(paper => paper.job_id === activeJobId.value)
  || overview.value.papers.find(paper => paper.job_id === routeJobId.value)
  || null,
)
const progress = computed(() => {
  if (!session.value?.total) return 0
  return Math.round((session.value.completed / session.value.total) * 100)
})
const sessionComplete = computed(() => session.value?.status === 'COMPLETED')

onMounted(load)
watch(routeJobId, load)

async function load() {
  loading.value = true
  error.value = ''
  session.value = null
  latestAttempt.value = null
  answer.value = ''
  try {
    if (routeJobId.value) {
      const imported = await learningApi.importPaper(routeJobId.value)
      overview.value = imported.overview
      activeJobId.value = routeJobId.value
      const active = await learningApi.getActiveSession(routeJobId.value)
      session.value = active.session
      message.value = active.session
        ? `已恢复上次未完成的练习，第 ${active.session.completed + 1} / ${active.session.total} 题。`
        : imported.imported_count
          ? `已准备 ${imported.imported_count} 个学习节点。`
          : '这篇论文暂时没有可用于练习的可靠学习节点。'
    } else {
      overview.value = await learningApi.getOverview()
      activeJobId.value = ''
      message.value = ''
    }
  } catch (loadError) {
    error.value = errorMessage(loadError, '学习数据加载失败。')
  } finally {
    loading.value = false
  }
}

async function openPaper(paper: LearningPaperSummary) {
  await router.push(`/study/${encodeURIComponent(paper.job_id)}`)
}

async function start(paper: LearningPaperSummary | null, includeNotDue = false) {
  const jobId = paper?.job_id || activeJobId.value
  if (!jobId || starting.value) return
  starting.value = true
  error.value = ''
  message.value = ''
  latestAttempt.value = null
  answer.value = ''
  try {
    activeJobId.value = jobId
    session.value = await learningApi.startSession(jobId, {
      count: 5,
      include_not_due: includeNotDue,
    })
    if (!session.value.current) {
      message.value = includeNotDue
        ? '这篇论文还没有可练习的节点。'
        : '今天已经没有到期内容，可以选择自由练习。'
    }
  } catch (startError) {
    error.value = errorMessage(startError, '无法开始本次复习。')
  } finally {
    starting.value = false
  }
}

async function submitAnswer() {
  const currentSession = session.value
  const text = answer.value.trim()
  if (!currentSession?.current || !text || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const result = await learningApi.answer(
      currentSession.job_id,
      currentSession.session_id,
      text,
    )
    latestAttempt.value = result.attempt
    session.value = result.session
    answer.value = ''
    overview.value = await learningApi.getOverview(currentSession.job_id)
  } catch (submitError) {
    error.value = errorMessage(submitError, '回答提交失败，请保留当前内容后重试。')
  } finally {
    submitting.value = false
  }
}

function onAnswerKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void submitAnswer()
}

function scoreLabel(score: number) {
  if (score >= 0.9) return '掌握很好'
  if (score >= 0.65) return '基本掌握'
  if (score >= 0.4) return '还需巩固'
  return '建议重学'
}

function typeLabel(type: string) {
  return {
    paper: '研究问题',
    concept: '核心概念',
    method: '方法机制',
    formula: '公式',
    experiment: '实验',
    limitation: '局限',
  }[type] || '论文内容'
}

function formatDate(value: string) {
  if (!value) return '尚未复习'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function emptyOverview(): LearningOverview {
  return {
    total_items: 0,
    due_count: 0,
    mastered_count: 0,
    reviewed_today: 0,
    papers: [],
    due_items: [],
    recent_attempts: [],
  }
}

function errorMessage(value: unknown, fallback: string) {
  if (value instanceof ApiClientError) return value.message || fallback
  return fallback
}
</script>

<template>
  <main class="learning-studio">
    <header class="studio-header">
      <div>
        <p>Learning Studio</p>
        <h1>{{ activePaper ? activePaper.paper_title : '学习与复习' }}</h1>
        <span>
          {{ activePaper
            ? '通过自然语言回答、反馈和间隔复习，把读过的论文真正变成自己的知识。'
            : '查看今天到期的内容，继续上次的薄弱点，或选择一篇论文开始练习。' }}
        </span>
      </div>
      <button
        v-if="activePaper"
        type="button"
        class="ghost-btn"
        @click="router.push(`/learn/${encodeURIComponent(activePaper.job_id)}`)"
      >
        返回论文
      </button>
    </header>

    <div v-if="loading" class="studio-state">正在准备学习记录…</div>
    <div v-else-if="error" class="studio-error" role="alert">{{ error }}</div>

    <template v-else>
      <section class="summary-strip" aria-label="学习概况">
        <article>
          <span>今日待复习</span>
          <strong>{{ overview.due_count }}</strong>
        </article>
        <article>
          <span>今日已完成</span>
          <strong>{{ overview.reviewed_today }}</strong>
        </article>
        <article>
          <span>已掌握节点</span>
          <strong>{{ overview.mastered_count }}</strong>
        </article>
        <article>
          <span>全部节点</span>
          <strong>{{ overview.total_items }}</strong>
        </article>
      </section>

      <p v-if="message" class="studio-message">{{ message }}</p>

      <section v-if="session?.current" class="practice-layout">
        <article class="practice-main surface">
          <header class="question-meta">
            <div>
              <span>{{ typeLabel(session.current.item_type) }}</span>
              <strong>{{ session.current.target_concept }}</strong>
            </div>
            <small>{{ session.current.position }} / {{ session.current.total }}</small>
          </header>
          <div class="progress-track" aria-label="本轮进度">
            <span :style="{ width: `${progress}%` }" />
          </div>
          <h2>{{ session.current.question }}</h2>
          <p v-if="session.current.why_it_matters" class="why">
            {{ session.current.why_it_matters }}
          </p>
          <textarea
            v-model="answer"
            rows="9"
            placeholder="用自己的话回答即可。系统评价的是关键理解，不要求背固定句子。"
            :disabled="submitting"
            @keydown="onAnswerKeydown"
          />
          <footer class="answer-actions">
            <small>Enter 提交 · Shift+Enter 换行</small>
            <button
              type="button"
              class="primary-btn"
              :disabled="!answer.trim() || submitting"
              @click="submitAnswer"
            >
              {{ submitting ? '正在结合论文评价…' : '提交回答' }}
            </button>
          </footer>
        </article>

        <aside class="practice-context">
          <section v-if="latestAttempt" class="feedback-panel surface">
            <header>
              <span>刚刚的反馈</span>
              <strong>{{ Math.round(latestAttempt.score * 100) }} · {{ scoreLabel(latestAttempt.score) }}</strong>
            </header>
            <p>{{ latestAttempt.feedback }}</p>
            <div v-if="latestAttempt.covered_points.length">
              <h3>已经讲清楚</h3>
              <ul>
                <li v-for="point in latestAttempt.covered_points" :key="point">{{ point }}</li>
              </ul>
            </div>
            <div v-if="latestAttempt.missing_points.length">
              <h3>可以补充</h3>
              <ul>
                <li v-for="point in latestAttempt.missing_points" :key="point">{{ point }}</li>
              </ul>
            </div>
            <small>下次复习：{{ formatDate(latestAttempt.next_due_at) }}</small>
          </section>
          <section class="source-panel surface">
            <h3>本题依据</h3>
            <p>问题来自当前论文的可靠学习节点，评价允许不同表达方式。</p>
            <ul v-if="session.current.evidence_refs.length">
              <li v-for="refId in session.current.evidence_refs" :key="refId">{{ refId }}</li>
            </ul>
          </section>
        </aside>
      </section>

      <section v-else-if="sessionComplete" class="session-finished surface">
        <span>本轮完成</span>
        <h2>这组内容已经复习完了</h2>
        <p>系统已根据每次回答更新下次复习时间。薄弱内容会更早再次出现。</p>
        <div>
          <button type="button" class="primary-btn" @click="start(activePaper, true)">再练一组</button>
          <button type="button" class="ghost-btn" @click="session = null">查看学习记录</button>
        </div>
      </section>

      <template v-else>
        <section v-if="activePaper" class="paper-focus surface">
          <div>
            <span>当前论文</span>
            <h2>{{ activePaper.paper_title }}</h2>
            <p>
              {{ activePaper.due_count }} 个到期 ·
              {{ activePaper.mastered_count }} / {{ activePaper.item_count }} 个节点已掌握
            </p>
          </div>
          <div>
            <button
              type="button"
              class="primary-btn"
              :disabled="starting || !activePaper.item_count"
              @click="start(activePaper)"
            >
              {{ starting ? '正在生成第一题…' : '开始今日复习' }}
            </button>
            <button
              type="button"
              class="ghost-btn"
              :disabled="starting || !activePaper.item_count"
              @click="start(activePaper, true)"
            >
              自由练习
            </button>
          </div>
        </section>

        <section class="studio-grid">
          <div class="paper-list">
            <header>
              <h2>论文学习列表</h2>
              <small>{{ overview.papers.length }} 篇</small>
            </header>
            <p v-if="!overview.papers.length" class="empty-copy">
              还没有学习记录。打开一篇已经完成解析的论文，点击“加入学习”即可开始。
            </p>
            <button
              v-for="paper in overview.papers"
              :key="paper.job_id"
              type="button"
              class="paper-row"
              :class="{ active: paper.job_id === activePaper?.job_id }"
              @click="openPaper(paper)"
            >
              <span>
                <strong>{{ paper.paper_title }}</strong>
                <small>{{ paper.due_count }} 个到期 · {{ paper.reviewed_count }} 个已练习</small>
              </span>
              <b>{{ paper.mastered_count }}/{{ paper.item_count }}</b>
            </button>
          </div>

          <aside class="recent-list">
            <header><h2>最近练习</h2></header>
            <p v-if="!overview.recent_attempts.length" class="empty-copy">完成第一题后，这里会保留练习轨迹。</p>
            <article v-for="attempt in overview.recent_attempts" :key="attempt.attempt_id">
              <div>
                <strong>{{ attempt.target_concept }}</strong>
                <small>{{ formatDate(attempt.reviewed_at) }}</small>
              </div>
              <b>{{ Math.round(attempt.score * 100) }}</b>
              <p>{{ attempt.feedback }}</p>
            </article>
          </aside>
        </section>
      </template>
    </template>
  </main>
</template>

<style scoped src="./LearningStudioView.css"></style>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

type SourceMode = 'file' | 'pdf_url' | 'arxiv_id' | 'arxiv_url' | 'doi' | 'm2_artifact_dir'

const router = useRouter()
const mode = ref<SourceMode>('file')
const file = ref<File | null>(null)
const title = ref('')
const doi = ref('')
const pdfUrl = ref('')
const arxivId = ref('')
const arxivUrl = ref('')
const m2ArtifactDir = ref('')
const isDragging = ref(false)
const isUploading = ref(false)
const error = ref('')
const sourceStatus = ref<Record<string, any> | null>(null)

const sourceOptions: Array<{ key: SourceMode; label: string; hint: string }> = [
  { key: 'file', label: '本地文件', hint: 'PDF / LaTeX / 文本' },
  { key: 'arxiv_id', label: 'arXiv ID', hint: '例如 2310.08800v2' },
  { key: 'arxiv_url', label: 'arXiv 链接', hint: 'abs 或 pdf 链接' },
  { key: 'pdf_url', label: 'PDF 链接', hint: '开放 PDF URL' },
  { key: 'doi', label: 'DOI', hint: '自动查开放全文' },
  { key: 'm2_artifact_dir', label: 'M2 目录', hint: '调试/复现入口' },
]

const activeOption = computed(() => sourceOptions.find((item) => item.key === mode.value) || sourceOptions[0])

const canSubmit = computed(() => {
  if (mode.value === 'file') return Boolean(file.value)
  if (mode.value === 'pdf_url') return Boolean(pdfUrl.value.trim())
  if (mode.value === 'arxiv_id') return Boolean(arxivId.value.trim())
  if (mode.value === 'arxiv_url') return Boolean(arxivUrl.value.trim())
  if (mode.value === 'm2_artifact_dir') return Boolean(m2ArtifactDir.value.trim())
  return Boolean(doi.value.trim())
})

function validFile(candidate: File) {
  return /\.(pdf|tex|txt|md)$/i.test(candidate.name)
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = input.files?.[0] || null
  if (selected && !validFile(selected)) {
    error.value = '请上传 PDF、LaTeX、TXT 或 Markdown 文件。'
    file.value = null
    return
  }
  file.value = selected
  error.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const dropped = e.dataTransfer?.files[0]
  if (!dropped) return
  if (validFile(dropped)) {
    file.value = dropped
    mode.value = 'file'
    error.value = ''
  } else {
    error.value = '请上传 PDF、LaTeX、TXT 或 Markdown 文件。'
  }
}

function appendFields(formData: FormData) {
  if (title.value.trim()) formData.append('title', title.value.trim())
  if (mode.value === 'file' && file.value) formData.append('file', file.value)
  if (mode.value === 'pdf_url') formData.append('pdf_url', pdfUrl.value.trim())
  if (mode.value === 'arxiv_id') formData.append('arxiv_id', arxivId.value.trim())
  if (mode.value === 'arxiv_url') formData.append('arxiv_url', arxivUrl.value.trim())
  if (mode.value === 'm2_artifact_dir') formData.append('local_path', m2ArtifactDir.value.trim())
  if (mode.value === 'doi') formData.append('doi', doi.value.trim())
}

async function upload() {
  if (!canSubmit.value || isUploading.value) return
  isUploading.value = true
  error.value = ''
  sourceStatus.value = null
  try {
    const formData = new FormData()
    appendFields(formData)
    const res = await fetch('/api/v1/documents/parse', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json().catch(() => ({}))
    if (res.ok && data.job_id) {
      await router.push(`/learn/${data.job_id}`)
      return
    }
    sourceStatus.value = data.detail?.source_status || null
    error.value = sourceStatus.value?.warnings?.join('，') || data.detail?.message || data.error || '深读任务创建失败。'
  } catch {
    error.value = '网络请求失败，请确认后端服务正在运行。'
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <main class="upload-page">
    <header class="page-heading">
      <p>论文工作台</p>
      <h1>新建论文深读</h1>
      <span>建议优先使用 arXiv 源码或 LaTeX 文件，公式和证据定位会更稳。</span>
    </header>

    <section class="upload-layout">
      <aside class="source-list surface" aria-label="来源类型">
        <button
          v-for="item in sourceOptions"
          :key="item.key"
          type="button"
          :class="{ active: mode === item.key }"
          @click="mode = item.key"
        >
          <strong>{{ item.label }}</strong>
          <small>{{ item.hint }}</small>
        </button>
      </aside>

      <section class="source-panel surface">
        <div class="field">
          <label>论文标题（可选）</label>
          <input
            v-model="title"
            data-testid="title-input"
            placeholder="例如：Attention Is All You Need"
          />
        </div>

        <div class="mode-title">
          <h2>{{ activeOption.label }}</h2>
          <p>{{ activeOption.hint }}</p>
        </div>

        <section
          v-if="mode === 'file'"
          class="drop-zone"
          :class="{ dragging: isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="onDrop"
        >
          <input id="file-input" data-testid="file-input" type="file" accept=".pdf,.tex,.txt,.md" class="hidden" @change="onFileChange" />
          <label for="file-input">
            <strong>{{ file ? file.name : '选择文件或拖到这里' }}</strong>
            <span>{{ file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : '支持 PDF、LaTeX、TXT、Markdown' }}</span>
          </label>
        </section>

        <div v-else class="field">
          <label>{{ activeOption.label }}</label>
          <input
            v-if="mode === 'pdf_url'"
            v-model="pdfUrl"
            data-testid="pdf-url-input"
            placeholder="https://example.org/paper.pdf"
          />
          <input
            v-else-if="mode === 'arxiv_id'"
            v-model="arxivId"
            data-testid="arxiv-id-input"
            placeholder="2310.08800v2"
          />
          <input
            v-else-if="mode === 'arxiv_url'"
            v-model="arxivUrl"
            data-testid="arxiv-url-input"
            placeholder="https://arxiv.org/abs/2310.08800"
          />
          <input
            v-else-if="mode === 'm2_artifact_dir'"
            v-model="m2ArtifactDir"
            data-testid="m2-artifact-dir-input"
            placeholder="D:\\Code\\Python\\Research-sensei\\workspace\\runs\\..."
          />
          <input
            v-else
            v-model="doi"
            data-testid="doi-input"
            placeholder="10.1145/example"
          />
        </div>

        <button
          class="primary-btn submit"
          :disabled="!canSubmit || isUploading"
          data-testid="submit-upload"
          @click="upload"
        >
          {{ isUploading ? '正在创建深读任务...' : '开始深读' }}
        </button>

        <section v-if="sourceStatus" class="source-status" data-testid="source-status">
          <strong>来源解析：{{ sourceStatus.status }}</strong>
          <span>来源类型：{{ sourceStatus.source_type || '未知' }}</span>
          <span v-if="sourceStatus.warnings?.length">提示：{{ sourceStatus.warnings.join('，') }}</span>
        </section>

        <div v-if="error" class="error-box">
          {{ error }}
        </div>
      </section>
    </section>
  </main>
</template>

<style scoped>
.upload-page {
  width: min(1060px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 42px 0 72px;
}

.page-heading {
  margin-bottom: 22px;
}

.page-heading p {
  color: var(--accent);
  font-size: 14px;
  font-weight: 800;
}

.page-heading h1 {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 34px;
  font-weight: 900;
}

.page-heading span {
  display: block;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 16px;
}

.upload-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
}

.source-list {
  display: grid;
  align-self: start;
  gap: 6px;
  padding: 8px;
}

.source-list button {
  border-radius: 12px;
  padding: 13px 14px;
  text-align: left;
}

.source-list button.active,
.source-list button:hover {
  background: var(--accent-light);
}

.source-list strong,
.source-list small {
  display: block;
}

.source-list strong {
  color: var(--text-primary);
  font-size: 15px;
}

.source-list small {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}

.source-panel {
  display: grid;
  gap: 18px;
  padding: 24px;
}

.field {
  display: grid;
  gap: 8px;
}

.field label {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 800;
}

.field input {
  width: 100%;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 13px 14px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 15px;
}

.mode-title h2 {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 900;
}

.mode-title p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 14px;
}

.drop-zone {
  border: 2px dashed var(--border);
  border-radius: 16px;
  padding: 42px 24px;
  background: var(--bg-secondary);
  text-align: center;
  transition: transform 0.16s ease, border-color 0.16s ease;
}

.drop-zone.dragging {
  transform: scale(1.01);
  border-color: var(--accent);
}

.drop-zone label {
  cursor: pointer;
}

.drop-zone strong,
.drop-zone span {
  display: block;
}

.drop-zone strong {
  color: var(--text-primary);
  font-size: 18px;
}

.drop-zone span {
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 14px;
}

.submit {
  width: 100%;
}

.source-status,
.error-box {
  display: grid;
  gap: 6px;
  border-radius: 12px;
  padding: 13px 14px;
  font-size: 14px;
  line-height: 1.7;
}

.source-status {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.source-status strong {
  color: var(--text-primary);
}

.error-box {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
}

@media (max-width: 820px) {
  .upload-layout {
    grid-template-columns: 1fr;
  }

  .source-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

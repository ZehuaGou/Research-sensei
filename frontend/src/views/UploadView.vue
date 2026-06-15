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

const canSubmit = computed(() => {
  if (mode.value === 'file') return Boolean(file.value)
  if (mode.value === 'pdf_url') return Boolean(pdfUrl.value.trim())
  if (mode.value === 'arxiv_id') return Boolean(arxivId.value.trim())
  if (mode.value === 'arxiv_url') return Boolean(arxivUrl.value.trim())
  if (mode.value === 'm2_artifact_dir') return Boolean(m2ArtifactDir.value.trim())
  return Boolean(doi.value.trim())
})

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  file.value = input.files?.[0] || null
  error.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  const dropped = e.dataTransfer?.files[0]
  if (!dropped) return
  if (dropped.type === 'application/pdf' || dropped.name.toLowerCase().endsWith('.pdf')) {
    file.value = dropped
    mode.value = 'file'
    error.value = ''
  } else {
    error.value = 'Only PDF files are accepted in file mode.'
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
    error.value = sourceStatus.value?.warnings?.join(', ') || data.detail?.message || data.error || 'Upload failed.'
  } catch {
    error.value = 'Network error while uploading.'
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto px-6 py-12">
    <header class="mb-8">
      <h1 class="text-2xl font-bold mb-2" style="color: var(--text-primary);">Upload Paper</h1>
      <p class="text-sm" style="color: var(--text-secondary);">Choose a source for the PaperWorkspace pipeline.</p>
    </header>

    <div class="mb-5">
      <label class="block text-xs font-semibold mb-2" style="color: var(--text-muted);">Title</label>
      <input
        v-model="title"
        data-testid="title-input"
        class="w-full px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="Optional title"
      />
    </div>

    <div class="flex flex-wrap gap-2 mb-5" role="tablist" aria-label="Source type">
      <button
        v-for="item in ['file', 'pdf_url', 'arxiv_id', 'arxiv_url', 'doi', 'm2_artifact_dir']"
        :key="item"
        type="button"
        class="px-3 py-2 rounded-md text-xs font-semibold"
        :style="mode === item ? 'background: var(--accent-light); color: var(--accent);' : 'background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border);'"
        @click="mode = item as SourceMode"
      >
        {{ item }}
      </button>
    </div>

    <section
      v-if="mode === 'file'"
      class="rounded-lg p-8 text-center"
      :class="isDragging ? 'scale-[1.01]' : ''"
      style="background: var(--bg-card); border: 2px dashed var(--border);"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input id="file-input" data-testid="file-input" type="file" accept=".pdf" class="hidden" @change="onFileChange" />
      <label for="file-input" class="cursor-pointer block">
        <div class="font-medium text-sm mb-1" style="color: var(--text-primary);">
          {{ file ? file.name : 'Select a PDF file' }}
        </div>
        <div class="text-xs" style="color: var(--text-muted);">
          {{ file ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : 'Max 80 MB' }}
        </div>
      </label>
    </section>

    <section v-else class="rounded-lg p-5" style="background: var(--bg-card); border: 1px solid var(--border);">
      <label class="block text-xs font-semibold mb-2" style="color: var(--text-muted);">{{ mode }}</label>
      <input
        v-if="mode === 'pdf_url'"
        v-model="pdfUrl"
        data-testid="pdf-url-input"
        class="w-full px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="https://example.org/paper.pdf"
      />
      <input
        v-else-if="mode === 'arxiv_id'"
        v-model="arxivId"
        data-testid="arxiv-id-input"
        class="w-full px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="2310.08800v2"
      />
      <input
        v-else-if="mode === 'arxiv_url'"
        v-model="arxivUrl"
        data-testid="arxiv-url-input"
        class="w-full px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="https://arxiv.org/abs/2310.08800"
      />
      <input
        v-else-if="mode === 'm2_artifact_dir'"
        v-model="m2ArtifactDir"
        data-testid="m2-artifact-dir-input"
        class="w-full px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="D:\\Code\\Python\\Research-sensei\\reports\\m2_live_acceptance_work\\positive_2310_08800v2"
      />
      <input
        v-else
        v-model="doi"
        data-testid="doi-input"
        class="w-full px-3 py-2 rounded-md text-sm outline-none"
        style="background: var(--bg-secondary); border: 1px solid var(--border); color: var(--text-primary);"
        placeholder="10.1145/example"
      />
    </section>

    <button
      class="mt-5 w-full py-3 rounded-md text-sm font-semibold text-white disabled:opacity-40"
      style="background: var(--accent);"
      :disabled="!canSubmit || isUploading"
      data-testid="submit-upload"
      @click="upload"
    >
      {{ isUploading ? 'Parsing...' : 'Start Parse' }}
    </button>

    <section
      v-if="sourceStatus"
      class="mt-5 rounded-lg p-4 text-xs"
      style="background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary);"
      data-testid="source-status"
    >
      <div class="font-semibold mb-2" style="color: var(--text-primary);">source_resolution: {{ sourceStatus.status }}</div>
      <div>source_type: {{ sourceStatus.source_type }}</div>
      <div v-if="sourceStatus.warnings?.length">warnings: {{ sourceStatus.warnings.join(', ') }}</div>
    </section>

    <div v-if="error" class="mt-4 px-4 py-3 rounded-md text-sm" style="background: rgba(239,68,68,0.08); color: #ef4444;">
      {{ error }}
    </div>
  </div>
</template>

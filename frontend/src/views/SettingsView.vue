<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiErrorMessage, researchApi } from '../api/client'
import type { SettingsPayload } from '../types/api'

const settings = ref<SettingsPayload>({
  active_provider: '',
  base_url: '',
  api_key_env: '',
  model: '',
  enable_env: 'RESEARCHSENSEI_ENABLE_API_LLM',
  llm_enabled: false,
  api_key_configured: false,
  provider_known: false,
})
const testResult = ref('')
const saveResult = ref('')
const isTesting = ref(false)
const isSaving = ref(false)
const modelDraft = ref('')
const paperModelDraft = ref('')
const tutorModelDraft = ref('')

const providerLabel = computed(() => {
  if (settings.value.provider_display_name) return settings.value.provider_display_name
  if (['cc_switch', 'ccswitch'].includes(settings.value.active_provider)) return 'ccswitch'
  return settings.value.active_provider || '未配置'
})

const modelOptions = computed(() => {
  const options = settings.value.model_options || []
  if (options.length) return options
  return settings.value.model ? [{ id: settings.value.model, label: settings.value.model, source: '当前配置' }] : []
})

const modelDirty = computed(() => modelDraft.value.trim() !== settings.value.model)
const paperModelDirty = computed(() => (
  paperModelDraft.value.trim() !== (settings.value.paper_agent_model || '')
))
const paperModelOptions = computed(() => settings.value.paper_agent_model_options || [])
const tutorModelDirty = computed(() => (
  tutorModelDraft.value.trim() !== (settings.value.paper_tutor_model || '')
))
const tutorModelOptions = computed(() => settings.value.paper_tutor_model_options || [])

const requestModeLabel = computed(() => (
  settings.value.provider_kind === 'anthropic_compatible'
    ? 'Claude / Anthropic messages'
    : 'OpenAI chat completions'
))

const isOpenCodeGo = computed(() => settings.value.active_provider === 'opencode_go')

const settingsTitle = computed(() => (
  isOpenCodeGo.value ? 'OpenCode Go 模型接入' : `${providerLabel.value} 模型接入`
))

const settingsDescription = computed(() => (
  isOpenCodeGo.value
    ? 'Research Sensei 直连 OpenCode Go。通用模型、PDF 识读模型和论文讲解模型分开选择，保存后无需重启项目。'
    : '这里保存的是随请求发送的 model 字段；实际请求通道由当前提供方配置决定。'
))

const modelHelp = computed(() => (
  isOpenCodeGo.value
    ? '优先显示 OpenCode Go 接口实时返回的模型；接口暂时不可用时使用内置候选列表。'
    : '优先显示当前配置和提供方接口中识别到的模型。'
))

onMounted(async () => {
  try {
    settings.value = await researchApi.getSettings()
    modelDraft.value = settings.value.model
    paperModelDraft.value = settings.value.paper_agent_model || ''
    tutorModelDraft.value = settings.value.paper_tutor_model || ''
  } catch {}
})

async function saveModel() {
  const model = modelDraft.value.trim()
  if (!model || isSaving.value) return
  isSaving.value = true
  saveResult.value = ''
  try {
    const data = await researchApi.updateSettings({ model })
    settings.value = data
    modelDraft.value = data.model || model
    saveResult.value = `模型已保存。后续请求会把这个 model 字段发送给 ${providerLabel.value}。`
  } catch (saveError) {
    saveResult.value = apiErrorMessage(saveError, '保存请求失败，请确认后端服务正在运行。')
  } finally {
    isSaving.value = false
  }
}

async function savePaperModel() {
  const paperModel = paperModelDraft.value.trim()
  if (!paperModel || isSaving.value) return
  isSaving.value = true
  saveResult.value = ''
  try {
    const data = await researchApi.updateSettings({
      paper_model: paperModel,
    })
    settings.value = data
    paperModelDraft.value = data.paper_agent_model || paperModel
    saveResult.value = 'PDF 视觉解析模型已保存，后续重新解析论文时生效。'
  } catch (saveError) {
    saveResult.value = apiErrorMessage(saveError, '保存 PDF 视觉解析模型失败。')
  } finally {
    isSaving.value = false
  }
}

async function saveTutorModel() {
  const tutorModel = tutorModelDraft.value.trim()
  if (!tutorModel || isSaving.value) return
  isSaving.value = true
  saveResult.value = ''
  try {
    const data = await researchApi.updateSettings({
      tutor_model: tutorModel,
    })
    settings.value = data
    tutorModelDraft.value = data.paper_tutor_model || tutorModel
    saveResult.value = '论文讲解模型已保存，后续论文助教对话立即使用。'
  } catch (saveError) {
    saveResult.value = apiErrorMessage(saveError, '保存论文讲解模型失败。')
  } finally {
    isSaving.value = false
  }
}

async function testConnection() {
  isTesting.value = true
  testResult.value = ''
  try {
    const data = await researchApi.validateSettings()
    testResult.value = data.ok
      ? `连接可用。Research Sensei 会通过 ${requestModeLabel.value} 通道发送请求。`
      : (data.message || '连接未就绪，请检查当前模型服务是否运行，以及环境变量是否启用。')
  } catch (testError) {
    testResult.value = apiErrorMessage(testError, '设置请求失败，请确认后端服务正在运行。')
  } finally {
    isTesting.value = false
  }
}
</script>

<template>
  <main class="settings-page">
    <section class="settings-head">
      <p>模型设置</p>
      <h1>{{ settingsTitle }}</h1>
      <span>{{ settingsDescription }}</span>
    </section>

    <section class="settings-grid">
      <div class="surface settings-panel">
        <div class="setting-row">
          <label>当前提供方</label>
          <input :value="providerLabel" readonly />
        </div>
        <div class="setting-row">
          <label>API Base URL</label>
          <input v-model="settings.base_url" readonly />
        </div>
        <div class="route-note">
          <strong>{{ requestModeLabel }}</strong>
          <span>{{ settings.request_endpoint || settings.base_url }}</span>
          <p>{{ settings.route_note || '请求通道来自当前提供方配置。' }}</p>
        </div>
        <div class="setting-row">
          <label>API Key 环境变量</label>
          <input v-model="settings.api_key_env" readonly />
        </div>
        <div class="setting-row">
          <label>模型名</label>
          <div class="model-editor">
            <select v-model="modelDraft" data-testid="model-select" :disabled="!modelOptions.length">
              <option v-for="option in modelOptions" :key="option.id" :value="option.id">
                {{ option.label || option.id }}{{ option.source ? ` · ${option.source}` : '' }}
              </option>
            </select>
            <button data-testid="save-model" class="secondary-btn" :disabled="!modelDraft.trim() || !modelDirty || isSaving" @click="saveModel">
              {{ isSaving ? '保存中...' : '保存' }}
            </button>
          </div>
          <small>{{ modelHelp }}保存后写入 {{ settings.model_env || 'RESEARCHSENSEI_LLM_MODEL' }}，并立即生效。</small>
          <small v-if="saveResult" class="save-result">{{ saveResult }}</small>
        </div>

        <div v-if="settings.paper_agent_enabled" class="setting-row paper-agent-row">
          <label>PDF 视觉解析模型</label>
          <div class="model-editor">
            <select
              v-model="paperModelDraft"
              data-testid="paper-model-select"
              :disabled="!paperModelOptions.length"
            >
              <option v-for="option in paperModelOptions" :key="option.id" :value="option.id">
                {{ option.label || option.id }}{{ option.source ? ` · ${option.source}` : '' }}
              </option>
            </select>
            <button
              data-testid="save-paper-model"
              class="secondary-btn"
              :disabled="!paperModelDraft.trim() || !paperModelDirty || isSaving"
              @click="savePaperModel"
            >
              {{ isSaving ? '保存中...' : '保存' }}
            </button>
          </div>
          <small>
            论文解析会把 PDF 按页渲染后交给这个支持图像附件的 OpenCode 模型，识别章节、公式和图表；
            论文讲解模型在下一项单独选择。
          </small>
          <small>{{ settings.paper_agent_base_url }}</small>
        </div>

        <div v-if="settings.paper_agent_enabled" class="setting-row paper-agent-row">
          <label>论文讲解模型</label>
          <div class="model-editor">
            <select
              v-model="tutorModelDraft"
              data-testid="tutor-model-select"
              :disabled="!tutorModelOptions.length"
            >
              <option v-for="option in tutorModelOptions" :key="option.id" :value="option.id">
                {{ option.label || option.id }}{{ option.source ? ` · ${option.source}` : '' }}
              </option>
            </select>
            <button
              data-testid="save-tutor-model"
              class="secondary-btn"
              :disabled="!tutorModelDraft.trim() || !tutorModelDirty || isSaving"
              @click="saveTutorModel"
            >
              {{ isSaving ? '保存中…' : '保存' }}
            </button>
          </div>
          <small>
            论文助教会在同一个论文会话中使用该模型继续讲解。视觉解析与讲解分开选择：
            Qwen 负责公式和页面，MiMo 可以专注长上下文问答。
          </small>
        </div>

        <button
          data-testid="test-connection"
          class="primary-btn test-button"
          @click="testConnection"
          :disabled="isTesting"
        >
          {{ isTesting ? '正在检测...' : '检测连接' }}
        </button>

        <div v-if="testResult" class="test-result">
          {{ testResult }}
        </div>
      </div>

      <aside class="surface status-panel">
        <h2>运行状态</h2>
        <div class="status-item">
          <span>实时 LLM</span>
          <strong :class="{ ok: settings.llm_enabled }">{{ settings.llm_enabled ? '已启用' : '未启用' }}</strong>
          <small>{{ settings.enable_env }}=1</small>
        </div>
        <div class="status-item">
          <span>密钥</span>
          <strong :class="{ ok: settings.api_key_configured, bad: !settings.api_key_configured }">
            {{ settings.api_key_configured ? '已配置' : '缺失' }}
          </strong>
          <small>{{ settings.api_key_env || '未指定' }}</small>
        </div>
        <div class="status-item">
          <span>提供方配置</span>
          <strong :class="{ ok: settings.provider_known, bad: !settings.provider_known }">
            {{ settings.provider_known ? '已识别' : '未识别' }}
          </strong>
          <small>{{ providerLabel }} · {{ settings.provider_key || settings.active_provider }}</small>
        </div>
        <p v-if="!settings.llm_enabled" class="notice">
          未启用实时 LLM 时，系统只会生成基础解析，不会生成用户可读的解析卡片和助教回答。
        </p>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.settings-page {
  width: 100%;
  max-width: 1040px;
  margin: 0 auto;
  padding: 34px 24px 60px;
  box-sizing: border-box;
  overflow-x: clip;
}

.settings-head {
  margin-bottom: 22px;
}

.settings-head p {
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 650;
}

.settings-head h1 {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 30px;
  font-weight: 720;
  line-height: 1.18;
}

.settings-head span {
  display: block;
  max-width: 760px;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.72;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 12px;
}

.settings-grid > * {
  min-width: 0;
}

.settings-panel,
.status-panel {
  padding: 16px;
}

.setting-row {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.setting-row label {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.setting-row input {
  width: 100%;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-size: 15px;
}

.setting-row select {
  width: 100%;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-size: 15px;
}

.model-editor {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.model-editor button {
  min-width: 92px;
}

.setting-row small {
  color: var(--text-muted);
  font-size: 13px;
}

.route-note {
  display: grid;
  gap: 5px;
  margin: -2px 0 18px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 11px 12px;
  background: var(--bg-secondary);
}

.route-note strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 720;
}

.route-note span,
.route-note p {
  min-width: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.save-result {
  color: var(--text-primary) !important;
  font-weight: 690;
}

.test-button {
  width: 100%;
}

.test-result {
  margin-top: 14px;
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.status-panel h2 {
  margin-bottom: 16px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
}

.status-item {
  display: grid;
  gap: 4px;
  border-top: 1px solid var(--border-subtle);
  padding: 14px 0;
}

.status-item span,
.status-item small {
  color: var(--text-muted);
  font-size: 13px;
}

.status-item strong {
  color: #d97706;
  font-size: 16px;
}

.status-item strong.ok {
  color: var(--success);
}

.status-item strong.bad {
  color: var(--danger);
}

.notice {
  border-radius: 8px;
  padding: 12px 14px;
  background: rgba(245, 158, 11, 0.1);
  color: #92400e;
  font-size: 14px;
  line-height: 1.7;
}

@media (max-width: 1200px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .status-panel {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .status-panel h2,
  .status-panel .notice {
    grid-column: 1 / -1;
  }
}

@media (max-width: 720px) {
  .model-editor {
    grid-template-columns: 1fr;
  }

  .status-panel {
    grid-template-columns: 1fr;
  }
}
</style>

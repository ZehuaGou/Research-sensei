<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

interface SettingsPayload {
  active_provider: string
  provider_display_name?: string
  provider_key?: string
  provider_kind?: string
  base_url: string
  request_endpoint?: string
  api_key_env: string
  auth_header?: string
  model: string
  model_options?: Array<{ id: string; label?: string; source?: string }>
  model_env?: string
  route_note?: string
  enable_env?: string
  llm_enabled?: boolean
  api_key_configured?: boolean
  provider_known?: boolean
}

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

const requestModeLabel = computed(() => (
  settings.value.provider_kind === 'anthropic_compatible'
    ? 'Claude / Anthropic messages'
    : 'OpenAI chat completions'
))

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/settings')
    if (res.ok) {
      settings.value = await res.json()
      modelDraft.value = settings.value.model
    }
  } catch {}
})

async function saveModel() {
  const model = modelDraft.value.trim()
  if (!model || isSaving.value) return
  isSaving.value = true
  saveResult.value = ''
  try {
    const res = await fetch('/api/v1/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    })
    const data = await res.json()
    if (!res.ok) {
      saveResult.value = data.detail || '模型名保存失败。'
      return
    }
    settings.value = data
    modelDraft.value = data.model || model
    saveResult.value = `模型已保存。后续请求会把这个 model 字段发送给 ${providerLabel.value}。`
  } catch {
    saveResult.value = '保存请求失败，请确认后端服务正在运行。'
  } finally {
    isSaving.value = false
  }
}

async function testConnection() {
  isTesting.value = true
  testResult.value = ''
  try {
    const res = await fetch('/api/v1/settings/test', { method: 'POST' })
    const data = await res.json()
    testResult.value = data.ok
      ? `连接可用。Research Sensei 会通过 ${requestModeLabel.value} 通道发送请求。`
      : (data.message || '连接未就绪，请检查 ccswitch 是否运行，以及环境变量是否启用。')
  } catch {
    testResult.value = '设置请求失败，请确认后端服务正在运行。'
  } finally {
    isTesting.value = false
  }
}
</script>

<template>
  <main class="settings-page">
    <section class="settings-head">
      <p>模型设置</p>
      <h1>ccswitch 模型接入</h1>
      <span>Research Sensei 连接本地 ccswitch 代理。这里保存的是随请求发送的 model 字段；实际使用哪条上游 API，由 ccswitch 当前 Claude provider 配置决定。</span>
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
          <small>优先显示当前配置和 ccswitch 当前 provider 中识别到的模型；保存后写入 {{ settings.model_env || 'RESEARCHSENSEI_LLM_MODEL' }}。</small>
          <small v-if="saveResult" class="save-result">{{ saveResult }}</small>
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
          未启用实时 LLM 时，系统只会生成基础解析，不会进入用户可读的 M2/M4 卡片。
        </p>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.settings-page {
  width: min(980px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 42px 0 72px;
}

.settings-head {
  margin-bottom: 22px;
}

.settings-head p {
  color: var(--accent);
  font-size: 14px;
  font-weight: 800;
}

.settings-head h1 {
  margin-top: 6px;
  color: var(--text-primary);
  font-size: 34px;
  font-weight: 900;
}

.settings-head span {
  display: block;
  max-width: 760px;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.8;
}

.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 18px;
}

.settings-panel,
.status-panel {
  padding: 22px;
}

.setting-row {
  display: grid;
  gap: 8px;
  margin-bottom: 18px;
}

.setting-row label {
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 800;
}

.setting-row input {
  width: 100%;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 15px;
}

.setting-row select {
  width: 100%;
  outline: none;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 12px 14px;
  background: var(--bg-secondary);
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
  border-radius: 10px;
  padding: 11px 12px;
  background: var(--bg-secondary);
}

.route-note strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 850;
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
  color: var(--accent) !important;
  font-weight: 800;
}

.test-button {
  width: 100%;
}

.test-result {
  margin-top: 14px;
  border-radius: 12px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}

.status-panel h2 {
  margin-bottom: 16px;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 900;
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
  font-size: 18px;
}

.status-item strong.ok {
  color: #059669;
}

.status-item strong.bad {
  color: #dc2626;
}

.notice {
  border-radius: 12px;
  padding: 12px 14px;
  background: rgba(245, 158, 11, 0.1);
  color: #92400e;
  font-size: 14px;
  line-height: 1.7;
}

@media (max-width: 820px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .model-editor {
    grid-template-columns: 1fr;
  }
}
</style>

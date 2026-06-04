<script setup lang="ts">
defineProps<{
  status: string
  blockingReason?: string
  warnings?: Array<{ code: string; message: string }>
  missingComponents?: string[]
}>()
</script>

<template>
  <div v-if="status === 'BASELINE_ONLY'"
    class="rounded-xl p-4 mb-6"
    style="background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2);">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-base">⚙️</span>
      <span class="text-sm font-semibold" style="color: #f59e0b;">基线模式</span>
    </div>
    <p class="text-xs leading-relaxed" style="color: var(--text-secondary);">
      当前为基线解析结果，不是最终导师级理解。等待 LLM 配置后可生成完整导师级解释。
    </p>
  </div>

  <div v-else-if="status === 'BLOCKED_UNDERSTANDING'"
    class="rounded-xl p-4 mb-6"
    style="background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-base">🚫</span>
      <span class="text-sm font-semibold" style="color: #ef4444;">理解被阻断</span>
    </div>
    <p class="text-xs leading-relaxed mb-2" style="color: var(--text-secondary);">
      {{ blockingReason || '论文理解过程被阻断，无法生成导师级解释。' }}
    </p>
    <div v-if="warnings?.length" class="mt-2 space-y-1">
      <div v-for="w in warnings" :key="w.code" class="text-xs" style="color: var(--text-muted);">
        · {{ w.message }}
      </div>
    </div>
  </div>

  <div v-else-if="status === 'DEGRADED_STRUCTURAL'"
    class="rounded-xl p-4 mb-6"
    style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2);">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-base">⚠️</span>
      <span class="text-sm font-semibold" style="color: #6366f1;">部分讲解不可用</span>
    </div>
    <p class="text-xs leading-relaxed" style="color: var(--text-secondary);">
      论文理解成功，但部分讲解组件暂不可用。
      <span v-if="missingComponents?.length">
        缺失：{{ missingComponents.join('、') }}
      </span>
    </p>
  </div>

  <div v-else-if="status === 'FAILED'"
    class="rounded-xl p-4 mb-6"
    style="background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-base">❌</span>
      <span class="text-sm font-semibold" style="color: #ef4444;">系统错误</span>
    </div>
    <p class="text-xs leading-relaxed" style="color: var(--text-secondary);">
      分析过程遇到系统错误，请重新上传或稍后重试。
    </p>
  </div>
</template>

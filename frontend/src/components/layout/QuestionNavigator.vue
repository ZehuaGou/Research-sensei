<script setup lang="ts">
import { computed, ref } from 'vue'

export interface QuestionNode {
  messageIndex: number
  sequence: number
  label: string
  title: string
}

const props = defineProps<{
  nodes: QuestionNode[]
  activeMessageIndex: number
}>()

const emit = defineEmits<{
  select: [messageIndex: number]
}>()

const isOpen = ref(false)

const activeSequence = computed(() => {
  const active = props.nodes.find(node => node.messageIndex === props.activeMessageIndex)
  return active?.sequence || props.nodes.at(-1)?.sequence || 0
})

function selectNode(messageIndex: number) {
  emit('select', messageIndex)
  isOpen.value = false
}
</script>

<template>
  <nav class="question-navigator" aria-label="提问节点导航" data-testid="question-navigator">
    <div v-if="isOpen" class="question-node-popover">
      <div class="question-node-head">
        <div>
          <strong>提问节点</strong>
          <span>点击返回对应问答</span>
        </div>
        <button type="button" aria-label="关闭提问节点" @click="isOpen = false">×</button>
      </div>
      <ol class="question-node-list">
        <li v-for="node in nodes" :key="node.messageIndex">
          <button
            type="button"
            class="question-node"
            :class="{ active: node.messageIndex === activeMessageIndex }"
            :aria-current="node.messageIndex === activeMessageIndex ? 'step' : undefined"
            :title="node.title"
            @click="selectNode(node.messageIndex)"
          >
            <span class="question-node-index">{{ String(node.sequence).padStart(2, '0') }}</span>
            <span class="question-node-label">{{ node.label }}</span>
          </button>
        </li>
      </ol>
    </div>
    <button
      type="button"
      class="question-navigator-toggle"
      data-testid="question-navigator-toggle"
      :aria-expanded="isOpen"
      aria-label="打开提问节点导航"
      @click="isOpen = !isOpen"
    >
      <span>问</span>
      <strong>{{ activeSequence }}/{{ nodes.length }}</strong>
    </button>
  </nav>
</template>

<style scoped>
.question-navigator {
  position: absolute;
  z-index: 8;
  right: 16px;
  bottom: 144px;
  left: 16px;
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  pointer-events: none;
}

.question-navigator-toggle {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 7px;
  border: 1px solid color-mix(in srgb, var(--text-primary) 18%, var(--border-subtle));
  border-radius: 999px;
  padding: 5px 11px 5px 6px;
  background: color-mix(in srgb, var(--bg-elevated) 94%, transparent);
  box-shadow: 0 8px 24px color-mix(in srgb, #000 12%, transparent);
  color: var(--text-secondary);
  pointer-events: auto;
  backdrop-filter: blur(12px);
}

.question-navigator-toggle:hover,
.question-navigator-toggle[aria-expanded='true'] {
  border-color: color-mix(in srgb, var(--accent) 42%, var(--border-subtle));
  color: var(--text-primary);
}

.question-navigator-toggle > span {
  display: inline-flex;
  height: 26px;
  width: 26px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  font-weight: 750;
}

.question-navigator-toggle strong {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}

.question-node-popover {
  width: min(320px, 100%);
  overflow: hidden;
  margin-bottom: 8px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: color-mix(in srgb, var(--bg-elevated) 97%, transparent);
  box-shadow: 0 16px 46px color-mix(in srgb, #000 18%, transparent);
  pointer-events: auto;
  backdrop-filter: blur(16px);
}

.question-node-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--border-subtle);
  padding: 11px 12px 9px;
}

.question-node-head > div {
  display: grid;
  gap: 1px;
}

.question-node-head strong {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 720;
}

.question-node-head span {
  color: var(--text-muted);
  font-size: 10px;
}

.question-node-head button {
  display: inline-flex;
  height: 26px;
  width: 26px;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1;
}

.question-node-head button:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.question-node-list {
  display: grid;
  max-height: min(380px, 48vh);
  overflow-y: auto;
  gap: 2px;
  margin: 0;
  padding: 6px;
  list-style: none;
}

.question-node {
  display: grid;
  width: 100%;
  grid-template-columns: 30px minmax(0, 1fr);
  align-items: center;
  gap: 7px;
  border-radius: 8px;
  padding: 7px 8px 7px 5px;
  color: var(--text-secondary);
  text-align: left;
}

.question-node:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.question-node.active {
  background: color-mix(in srgb, var(--accent) 10%, var(--bg-secondary));
  color: var(--text-primary);
}

.question-node-index {
  display: inline-flex;
  height: 26px;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  background: var(--bg-secondary);
  color: var(--text-muted);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  font-weight: 750;
}

.question-node.active .question-node-index {
  background: var(--accent);
  color: #fff;
}

.question-node-label {
  overflow: hidden;
  font-size: calc(var(--m4-font-size, 15px) - 2px);
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

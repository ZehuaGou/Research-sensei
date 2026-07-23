<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import katex from 'katex'

const props = defineProps<{ content: string }>()

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: false,
})

const defaultFence = markdown.renderer.rules.fence
markdown.renderer.rules.fence = (tokens, index, options, env, renderer) => {
  const token = tokens[index]
  const language = token.info.trim().toLowerCase()
  if (['latex', 'tex', 'math', 'katex'].includes(language)) {
    return `<div class="markdown-math" role="math">${katex.renderToString(token.content.trim(), {
      displayMode: true,
      throwOnError: false,
      strict: 'warn',
      trust: false,
      output: 'htmlAndMathml',
    })}</div>`
  }
  return defaultFence
    ? defaultFence(tokens, index, options, env, renderer)
    : renderer.renderToken(tokens, index, options)
}

const defaultLinkOpen = markdown.renderer.rules.link_open
markdown.renderer.rules.link_open = (tokens, index, options, env, renderer) => {
  tokens[index].attrSet('target', '_blank')
  tokens[index].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen
    ? defaultLinkOpen(tokens, index, options, env, renderer)
    : renderer.renderToken(tokens, index, options)
}

function normalizedMarkdown(value: string) {
  return value
    .replace(/^\s*```(?:markdown|md)\s*\n([\s\S]*?)\n```\s*$/i, '$1')
    .replace(/\r\n/g, '\n')
    .trim()
}

const rendered = computed(() => markdown.render(normalizedMarkdown(props.content)))
</script>

<template>
  <!-- Raw model HTML is disabled in markdown-it; v-html only receives escaped/generated markup. -->
  <div class="markdown-answer" v-html="rendered" />
</template>

<style scoped>
.markdown-answer {
  min-width: 0;
  color: var(--text-primary);
  font-size: var(--m4-font-size, 14px);
  line-height: 1.82;
  overflow-wrap: anywhere;
}

.markdown-answer :deep(h1),
.markdown-answer :deep(h2),
.markdown-answer :deep(h3),
.markdown-answer :deep(h4) {
  margin: 20px 0 8px;
  color: var(--text-primary);
  font-weight: 720;
  line-height: 1.42;
}

.markdown-answer :deep(h1:first-child),
.markdown-answer :deep(h2:first-child),
.markdown-answer :deep(h3:first-child),
.markdown-answer :deep(h4:first-child) {
  margin-top: 0;
}

.markdown-answer :deep(h1) {
  font-size: calc(var(--m4-font-size, 14px) + 4px);
}

.markdown-answer :deep(h2) {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 7px;
  font-size: calc(var(--m4-font-size, 14px) + 3px);
}

.markdown-answer :deep(h3) {
  font-size: calc(var(--m4-font-size, 14px) + 2px);
}

.markdown-answer :deep(h4) {
  font-size: calc(var(--m4-font-size, 14px) + 1px);
}

.markdown-answer :deep(p) {
  margin: 0 0 12px;
}

.markdown-answer :deep(ul),
.markdown-answer :deep(ol) {
  display: grid;
  gap: 7px;
  margin: 0 0 14px;
  padding-left: 22px;
}

.markdown-answer :deep(li) {
  padding-left: 2px;
}

.markdown-answer :deep(li > p) {
  margin: 0;
}

.markdown-answer :deep(blockquote) {
  margin: 14px 0;
  border-left: 3px solid var(--accent);
  padding: 8px 0 8px 13px;
  color: var(--text-secondary);
}

.markdown-answer :deep(blockquote p:last-child) {
  margin-bottom: 0;
}

.markdown-answer :deep(strong) {
  font-weight: 720;
}

.markdown-answer :deep(a) {
  color: var(--accent);
  text-decoration: underline;
  text-decoration-color: color-mix(in srgb, var(--accent) 45%, transparent);
  text-underline-offset: 3px;
}

.markdown-answer :deep(code) {
  border: 1px solid var(--border-subtle);
  border-radius: 5px;
  padding: 1px 5px;
  background: var(--bg-secondary);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 0.9em;
}

.markdown-answer :deep(pre) {
  margin: 14px 0;
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 12px;
  background: var(--bg-secondary);
}

.markdown-answer :deep(pre code) {
  border: 0;
  padding: 0;
  background: transparent;
}

.markdown-answer :deep(table) {
  width: 100%;
  margin: 14px 0 18px;
  border-collapse: collapse;
  font-size: calc(var(--m4-font-size, 14px) - 1px);
  line-height: 1.55;
}

.markdown-answer :deep(th),
.markdown-answer :deep(td) {
  border-bottom: 1px solid var(--border-subtle);
  padding: 8px 9px;
  text-align: left;
  vertical-align: top;
}

.markdown-answer :deep(th) {
  background: var(--bg-secondary);
  font-weight: 680;
}

.markdown-answer :deep(.markdown-math) {
  margin: 14px 0;
  overflow-x: auto;
  padding: 10px 2px;
  text-align: center;
}

.markdown-answer :deep(hr) {
  margin: 20px 0;
  border: 0;
  border-top: 1px solid var(--border-subtle);
}
</style>

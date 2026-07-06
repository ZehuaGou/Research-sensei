<script setup lang="ts">
defineProps<{ card: any }>()
</script>

<template>
  <article class="drill-card surface">
    <header>
      <span>训练题</span>
      <h3>{{ card.title || '复习练习' }}</h3>
    </header>

    <section v-if="card.recall_questions?.length">
      <h4>立即复述</h4>
      <ol>
        <li v-for="(q, i) in card.recall_questions" :key="i">{{ q }}</li>
      </ol>
    </section>

    <section v-if="card.advisor_questions?.length">
      <h4>导师追问</h4>
      <ol>
        <li v-for="(q, i) in card.advisor_questions" :key="i">{{ q }}</li>
      </ol>
    </section>

    <section v-if="card.error_attribution_prompts?.length">
      <h4>薄弱点检查</h4>
      <ol>
        <li v-for="(q, i) in card.error_attribution_prompts" :key="i">{{ q }}</li>
      </ol>
    </section>
  </article>
</template>

<style scoped>
.drill-card {
  display: grid;
  gap: 16px;
  padding: 18px;
}

header span {
  display: inline-flex;
  border-radius: 999px;
  padding: 4px 9px;
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
  font-size: 12px;
  font-weight: 650;
}

header h3 {
  margin-top: 10px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
}

section {
  border-top: 1px solid var(--border-subtle);
  padding-top: 14px;
}

h4 {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 720;
}

ol {
  display: grid;
  gap: 6px;
  margin-top: 8px;
  padding-left: 22px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}
</style>

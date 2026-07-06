<script setup lang="ts">
defineProps<{ card: any }>()
</script>

<template>
  <article class="pattern-card surface">
    <header>
      <span>科研模式</span>
      <h3>{{ card.pattern_id || card.title }}</h3>
      <p>{{ card.definition }}</p>
    </header>

    <section v-if="card.signals?.length">
      <h4>识别信号</h4>
      <div class="chips">
        <span v-for="signal in card.signals" :key="signal">{{ signal }}</span>
      </div>
    </section>

    <section v-if="card.transfer_template">
      <h4>迁移指导</h4>
      <p>{{ card.transfer_template }}</p>
    </section>
  </article>
</template>

<style scoped>
.pattern-card {
  display: grid;
  gap: 16px;
  padding: 18px;
}

header > span {
  display: inline-flex;
  border-radius: 999px;
  padding: 4px 9px;
  background: rgba(245, 158, 11, 0.12);
  color: var(--warning);
  font-size: 12px;
  font-weight: 650;
}

h3 {
  margin-top: 10px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 720;
}

p {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
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

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.chips span {
  border-radius: 999px;
  padding: 5px 9px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
}
</style>

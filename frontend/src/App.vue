<script setup lang="ts">
import { RouterView } from 'vue-router'
import TopBar from './components/layout/TopBar.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col" style="background: var(--bg-primary); color: var(--text-primary);">
    <TopBar />
    <main class="flex-1">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import TopBar from './components/layout/TopBar.vue'
</script>

<template>
  <div class="app-shell">
    <TopBar />
    <RouterView />
  </div>
</template>

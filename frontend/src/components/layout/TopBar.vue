<script setup lang="ts">
import { useThemeStore } from '../../stores/theme'

const theme = useThemeStore()
</script>

<template>
  <header class="glass sticky top-0 z-50 border-b" style="border-color: var(--border-subtle);">
    <div class="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
      <div class="flex items-center gap-8">
        <router-link to="/" class="flex items-center gap-2.5 text-[15px] font-semibold tracking-tight" style="color: var(--text-primary);">
          <div class="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold" style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">S</div>
          ResearchSensei
        </router-link>
        <nav class="flex items-center gap-1 text-[13px] font-medium" style="color: var(--text-secondary);">
          <router-link to="/directions/new"
            class="px-3 py-1.5 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/5">
            方向搜索
          </router-link>
          <router-link to="/papers/upload"
            class="px-3 py-1.5 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/5">
            上传论文
          </router-link>
          <router-link to="/settings"
            class="px-3 py-1.5 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/5">
            设置
          </router-link>
        </nav>
      </div>
      <button
        @click="theme.toggle()"
        class="w-8 h-8 rounded-full flex items-center justify-center transition-all text-sm hover:scale-110"
        style="background: var(--accent-light); color: var(--accent);"
      >
        {{ theme.isDark ? '☀' : '☾' }}
      </button>
    </div>
  </header>
</template>

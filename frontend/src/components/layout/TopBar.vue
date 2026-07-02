<script setup lang="ts">
import { useThemeStore } from '../../stores/theme'

const theme = useThemeStore()
</script>

<template>
  <header class="sticky top-0 z-40 border-b backdrop-blur-xl" style="border-color: var(--border-subtle); background: color-mix(in srgb, var(--bg-card) 88%, transparent);">
    <div class="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 lg:px-8">
      <div class="flex min-w-0 items-center gap-8">
        <router-link to="/" class="flex items-center gap-3 font-semibold" style="color: var(--text-primary);">
          <span class="flex h-9 w-9 items-center justify-center rounded-[10px] text-base font-black text-white" style="background: var(--accent);">研</span>
          <span class="text-lg tracking-normal">Research Sensei</span>
        </router-link>

        <nav class="hidden items-center gap-1 text-[15px] font-medium md:flex" style="color: var(--text-secondary);">
          <router-link class="rounded-[10px] px-3 py-2 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]" to="/directions/new">找方向</router-link>
          <router-link class="rounded-[10px] px-3 py-2 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]" to="/papers/upload">读论文</router-link>
          <router-link class="rounded-[10px] px-3 py-2 hover:bg-black/[0.04] dark:hover:bg-white/[0.06]" to="/settings">模型设置</router-link>
        </nav>
      </div>

      <button
        type="button"
        class="secondary-btn !h-10 !min-h-10 !px-3"
        :aria-label="theme.isDark ? '切换到浅色' : '切换到深色'"
        @click="theme.toggle()"
      >
        {{ theme.isDark ? '日间' : '夜间' }}
      </button>
    </div>
  </header>
</template>

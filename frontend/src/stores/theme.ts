import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(localStorage.getItem('theme') === 'dark')

  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  }

  watch(isDark, (v) => {
    document.documentElement.classList.toggle('dark', v)
  }, { immediate: true })

  return { isDark, toggle }
})

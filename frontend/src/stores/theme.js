import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // State
  const theme = ref(localStorage.getItem('theme') || 'light')

  // Actions
  function setTheme(newTheme) {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)
    applyTheme(newTheme)
  }

  function toggleTheme() {
    const newTheme = theme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
  }

  function applyTheme(currentTheme) {
    const html = document.documentElement
    if (currentTheme === 'dark') {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  // Initialize theme on load
  applyTheme(theme.value)

  return {
    theme,
    setTheme,
    toggleTheme
  }
})

<template>
  <div class="theme-switcher">
    <div class="theme-dropdown" ref="dropdownRef">
      <button 
        class="theme-toggle-btn"
        @click="toggleDropdown"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-palette" viewBox="0 0 16 16">
          <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
          <path d="M8 4a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 0 1h-.5V5a.5.5 0 0 1-.5-.5h-.5A.5.5 0 0 1 0 4zm0 1a1 1 0 0 1 1 1h.5a1 1 0 0 0 1 1v.5a1 1 0 0 1-1 1h-.5V6a1 1 0 0 0-1-1h-.5A1 1 0 0 1 0 5zm1 2a1 1 0 0 1 1 1h.5a1 1 0 0 0 1 1v.5a1 1 0 0 1-1 1h-.5V8a1 1 0 0 0-1-1h-.5A1 1 0 0 1 0 7zm1 2a1 1 0 0 1 1 1h.5a1 1 0 0 0 1 1v.5a1 1 0 0 1-1 1h-.5V10a1 1 0 0 0-1-1h-.5A1 1 0 0 1 0 9zm1 2a1 1 0 0 1 1 1h.5a1 1 0 0 0 1 1v.5a1 1 0 0 1-1 1h-.5V12a1 1 0 0 0-1-1h-.5A1 1 0 0 1 0 11z"/>
        </svg>
        <span class="theme-name">{{ currentTheme.displayName }}</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" fill="currentColor" class="bi bi-chevron-down" viewBox="0 0 16 16">
          <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708-.708L8.707 1.293a.5.5 0 0 1-.708 0L2 6.293a.5.5 0 0 1 0-.708l5.646 5.647a.5.5 0 0 1 .708.708L7.293 8.707a.5.5 0 0 1 0-.708L1.646 4.646z"/>
        </svg>
      </button>
      
      <div class="theme-dropdown-menu" :class="{ show: isDropdownOpen }">
        <div class="theme-grid">
          <div 
            v-for="theme in availableThemes" 
            :key="theme.name"
            class="theme-option"
            :class="{ active: currentTheme.name === theme.name }"
            @click="selectTheme(theme)"
          >
            <div class="theme-preview" :style="{ background: theme.gradient }"></div>
            <span class="theme-label">{{ theme.displayName }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { themes, getTheme, type Theme } from '@/config/themes'

const currentThemeName = ref(localStorage.getItem('theme') || 'default')
const isDropdownOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const currentTheme = computed(() => getTheme(currentThemeName.value))

const availableThemes = computed(() => Object.values(themes) as Theme[])

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value
}

const selectTheme = (theme: any) => {
  currentThemeName.value = theme.name
  localStorage.setItem('theme', theme.name)
  document.documentElement.setAttribute('data-theme', theme.name)
  isDropdownOpen.value = false
}

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.documentElement.setAttribute('data-theme', currentThemeName.value)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.theme-switcher {
  position: relative;
}

.theme-dropdown {
  position: relative;
}

.theme-toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--primary, #667eea);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.theme-toggle-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.theme-toggle-btn svg {
  flex-shrink: 0;
}

.theme-name {
  font-size: 12px;
  font-weight: 500;
}

.theme-dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  background: var(--surface, #ffffff);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  padding: 12px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.2s ease;
  z-index: 1000;
}

.theme-dropdown-menu.show {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.theme-option:hover {
  background: var(--background, #f7fafc);
  transform: scale(1.02);
}

.theme-option.active {
  border-color: var(--primary, #667eea);
  background: rgba(102, 126, 234, 0.1);
}

.theme-preview {
  width: 100%;
  height: 32px;
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.theme-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text, #2d3748);
}
</style>

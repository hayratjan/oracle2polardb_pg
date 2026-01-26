<template>
  <div class="theme-switcher">
    <div class="theme-dropdown" ref="dropdownRef">
      <button 
        class="theme-toggle-btn"
        @click="toggleDropdown"
      >
        <i class="bi bi-palette"></i>
        <span class="theme-name">{{ currentTheme.displayName }}</span>
        <i class="bi bi-chevron-down"></i>
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
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  box-shadow: 0 2px 8px var(--shadow-light);
  transition: all 0.3s ease;
}

.theme-toggle-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--shadow);
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
  background: var(--surface);
  border-radius: 12px;
  box-shadow: 0 4px 16px var(--shadow);
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
  background: var(--background);
  transform: scale(1.02);
}

.theme-option.active {
  border-color: var(--primary);
  background: var(--table-row-hover);
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

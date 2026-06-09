<template>
  <div class="theme-switcher" :class="variant">
    <div class="theme-dropdown" ref="dropdownRef">
      <button
        class="theme-toggle-btn"
        :class="{ 'header-style': variant === 'header' }"
        @click="toggleDropdown"
        aria-label="切换主题"
      >
        <i class="bi bi-palette"></i>
        <span class="theme-name d-none d-md-inline">{{ currentTheme.displayName }}</span>
        <i class="bi bi-chevron-down chevron-icon"></i>
      </button>

      <div class="theme-dropdown-menu" :class="{ show: isDropdownOpen }">
        <div class="theme-menu-title">选择主题</div>
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

withDefaults(defineProps<{
  variant?: 'default' | 'header'
}>(), {
  variant: 'default',
})

const currentThemeName = ref(localStorage.getItem('theme') || 'default')
const isDropdownOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

const currentTheme = computed(() => getTheme(currentThemeName.value))
const availableThemes = computed(() => Object.values(themes) as Theme[])

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value
}

const selectTheme = (theme: Theme) => {
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
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.theme-toggle-btn.header-style {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 6px 10px;
}

.theme-toggle-btn.header-style:hover {
  background: var(--table-row-hover);
  color: var(--text);
  border-color: var(--border);
  transform: none;
}

.theme-toggle-btn:not(.header-style):hover {
  opacity: 0.9;
}

.chevron-icon {
  font-size: 10px;
}

.theme-dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 220px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--shadow);
  padding: 12px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-6px);
  transition: all 0.2s ease;
  z-index: 1050;
}

.theme-dropdown-menu.show {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.theme-menu-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding: 0 4px;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
  border: 2px solid transparent;
}

.theme-option:hover {
  background: var(--table-row-hover);
}

.theme-option.active {
  border-color: var(--primary);
  background: var(--sidebar-active-bg, var(--table-row-hover));
}

.theme-preview {
  width: 100%;
  height: 28px;
  border-radius: 6px;
}

.theme-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
}
</style>

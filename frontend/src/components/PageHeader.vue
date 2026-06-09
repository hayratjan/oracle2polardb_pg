<template>
  <div class="page-header">
    <div class="page-header-main">
      <div class="page-header-icon" v-if="icon">
        <i :class="['bi', icon]"></i>
      </div>
      <div class="page-header-text">
        <h1 class="page-title">{{ title }}</h1>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
  icon?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}

.page-header-main {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.page-header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--primary);
  color: white;
  font-size: 20px;
  flex-shrink: 0;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
  line-height: 1.3;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 4px 0 0;
  line-height: 1.5;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

@media (max-width: 575.98px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .page-title {
    font-size: 18px;
  }

  .page-header-icon {
    width: 38px;
    height: 38px;
    font-size: 17px;
  }

  .page-header-actions {
    width: 100%;
  }

  .page-header-actions :deep(.btn) {
    flex: 1;
    justify-content: center;
  }
}
</style>

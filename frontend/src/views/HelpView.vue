<template>
  <div class="help-view">
    <PageHeader
      title="帮助文档"
      subtitle="快速上手、子文档索引与运维提示"
      icon="bi-question-circle"
    />

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
      <p class="mt-3 text-muted small">加载帮助内容…</p>
    </div>

    <div v-else-if="error" class="alert alert-warning">{{ error }}</div>

    <template v-else>
      <div class="alert alert-info d-flex align-items-start mb-4" role="alert">
        <i class="bi bi-info-circle me-2 mt-1"></i>
        <div>
          <strong>{{ helpTitle }}</strong>
          <span v-if="helpVersion" class="badge bg-primary ms-2">{{ helpVersion }}</span>
          <p class="mb-0 mt-1 small">详细 Markdown 文档见项目根目录 <code>README.md</code> 与 <code>docs/</code> 目录。</p>
        </div>
      </div>

      <div v-for="section in sections" :key="section.title" class="card mb-3">
        <div class="card-header">
          <h5 class="mb-0"><i class="bi bi-journal-text me-1"></i>{{ section.title }}</h5>
        </div>
        <ul class="list-group list-group-flush">
          <li
            v-for="(item, idx) in section.items"
            :key="idx"
            class="list-group-item d-flex justify-content-between align-items-center"
          >
            <span>
              <i :class="[item.hint ? 'bi bi-exclamation-triangle text-warning' : 'bi bi-file-text text-muted', 'me-2']"></i>
              {{ item.label }}
            </span>
            <code v-if="item.path" class="small text-muted">{{ item.path }}</code>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { helpApi } from '@/api'
import PageHeader from '@/components/PageHeader.vue'

interface HelpItem {
  label: string
  path?: string
  anchor?: string
  hint?: boolean
}

interface HelpSection {
  title: string
  items: HelpItem[]
}

const loading = ref(true)
const error = ref('')
const helpTitle = ref('Oracle → PolarDB 迁移平台帮助')
const helpVersion = ref('')
const sections = ref<HelpSection[]>([])

onMounted(async () => {
  try {
    const res = await helpApi.getHelp()
    const data = res.data
    helpTitle.value = data.title || helpTitle.value
    helpVersion.value = data.version || ''
    sections.value = data.sections || []
  } catch (e) {
    console.error(e)
    error.value = '加载帮助文档失败，请稍后重试'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.help-view {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

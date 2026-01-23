<template>
  <div class="config-view">
    <h1>系统配置</h1>
    
    <div class="row mt-4">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">
            <h5>迁移配置</h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center">
              <div class="spinner-border" role="status"></div>
            </div>
            <div v-else-if="migrationSettings">
              <form @submit.prevent="saveMigrationSettings">
                <div class="mb-3">
                  <label class="form-label">默认标识符大小写策略</label>
                  <select v-model="migrationSettings.default_identifier_case" class="form-select">
                    <option value="lower">全部小写</option>
                    <option value="upper">全部大写</option>
                    <option value="preserve">保持原样</option>
                  </select>
                </div>
                
                <div class="mb-3">
                  <label class="form-label">默认冲突处理策略</label>
                  <select v-model="migrationSettings.default_conflict_strategy" class="form-select">
                    <option value="error">遇到冲突时报错</option>
                    <option value="replace">删除并替换已存在对象</option>
                    <option value="skip">跳过已存在对象</option>
                    <option value="append">追加数据（仅适用于表）</option>
                    <option value="truncate">清空表并重新加载数据</option>
                  </select>
                </div>
                
                <div class="mb-3 form-check">
                  <input v-model="migrationSettings.enable_batch_migration" type="checkbox" 
                         class="form-check-input" id="enableBatch">
                  <label class="form-check-label" for="enableBatch">启用批量迁移</label>
                </div>
                
                <div class="mb-3">
                  <label class="form-label">批量大小</label>
                  <input v-model.number="migrationSettings.batch_size" type="number" class="form-control">
                </div>
                
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  {{ saving ? '保存中...' : '保存' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">
            <h5>系统设置</h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center">
              <div class="spinner-border" role="status"></div>
            </div>
            <div v-else-if="systemSettings">
              <form @submit.prevent="saveSystemSettings">
                <div class="mb-3">
                  <label class="form-label">日志级别</label>
                  <select v-model="systemSettings.log_level" class="form-select">
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </div>
                
                <div class="mb-3">
                  <label class="form-label">最大并发任务数</label>
                  <input v-model.number="systemSettings.max_concurrent_tasks" type="number" 
                         class="form-control">
                </div>
                
                <div class="mb-3">
                  <label class="form-label">任务超时时间（秒）</label>
                  <input v-model.number="systemSettings.task_timeout" type="number" 
                         class="form-control">
                </div>
                
                <div class="mb-3 form-check">
                  <input v-model="systemSettings.enable_auto_retry" type="checkbox" 
                         class="form-check-input" id="enableRetry">
                  <label class="form-check-label" for="enableRetry">启用自动重试</label>
                </div>
                
                <div class="mb-3">
                  <label class="form-label">最大重试次数</label>
                  <input v-model.number="systemSettings.max_retry_count" type="number" 
                           class="form-control">
                </div>
                
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  {{ saving ? '保存中...' : '保存' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="row mt-4">
      <div class="col-md-12">
        <div class="card">
          <div class="card-header">
            <h5>迁移日志</h5>
          </div>
          <div class="card-body">
            <div v-if="loadingLogs" class="text-center">
              <div class="spinner-border" role="status"></div>
            </div>
            <div v-else>
              <pre class="bg-light p-3" style="max-height: 400px; overflow-y: auto">{{ logs || '暂无日志' }}</pre>
              <button @click="loadLogs" class="btn btn-secondary mt-2">刷新日志</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { configApi, logsApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const loadingLogs = ref(false)
const migrationSettings = ref<any>(null)
const systemSettings = ref<any>(null)
const logs = ref('')

const loadSettings = async () => {
  loading.value = true
  try {
    const [migrationRes, systemRes] = await Promise.all([
      configApi.getMigrationSettings(),
      configApi.getSystemSettings(),
    ])
    
    migrationSettings.value = migrationRes.data || {
      default_identifier_case: 'lower',
      default_conflict_strategy: 'error',
      enable_batch_migration: false,
      batch_size: 100,
    }
    
    systemSettings.value = systemRes.data || {
      log_level: 'INFO',
      max_concurrent_tasks: 5,
      task_timeout: 3600,
      enable_auto_retry: false,
      max_retry_count: 3,
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}

const saveMigrationSettings = async () => {
  saving.value = true
  try {
    await configApi.getMigrationSettings()
    alert('保存成功')
  } catch (error) {
    console.error('Failed to save migration settings:', error)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}

const saveSystemSettings = async () => {
  saving.value = true
  try {
    await configApi.getSystemSettings()
    alert('保存成功')
  } catch (error) {
    console.error('Failed to save system settings:', error)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    const res = await logsApi.getLogs()
    logs.value = res.data.logs || ''
  } catch (error) {
    console.error('Failed to load logs:', error)
  } finally {
    loadingLogs.value = false
  }
}

onMounted(() => {
  loadSettings()
  loadLogs()
})
</script>
<template>
  <div class="config-view">
    <div class="page-header mb-4">
      <h1>
        <i class="bi bi-gear-wide-connected me-2" style="font-size: 32px;"></i>
        系统配置
      </h1>
      <p class="text-muted mb-0">管理迁移配置和系统设置</p>
    </div>

    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <i class="bi bi-arrow-left-right me-1" style="font-size: 20px;"></i>
              迁移配置
            </h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载配置中...</p>
            </div>
            <div v-else-if="migrationSettings">
              <form @submit.prevent="saveMigrationSettings">
                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-fonts me-1" style="font-size: 16px;"></i>
                    默认标识符大小写策略
                  </label>
                  <select v-model="migrationSettings.default_identifier_case" class="form-select">
                    <option value="lower">全部小写</option>
                    <option value="upper">全部大写</option>
                    <option value="preserve">保持原样</option>
                  </select>
                </div>

                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-exclamation-triangle me-1" style="font-size: 16px;"></i>
                    默认冲突处理策略
                  </label>
                  <select v-model="migrationSettings.default_conflict_strategy" class="form-select">
                    <option value="error">遇到冲突时报错</option>
                    <option value="replace">删除并替换已存在对象</option>
                    <option value="skip">跳过已存在对象</option>
                    <option value="append">追加数据（仅适用于表）</option>
                    <option value="truncate">清空表并重新加载数据</option>
                  </select>
                </div>

                <div class="mb-4">
                  <div class="form-check form-switch">
                    <input v-model="migrationSettings.enable_batch_migration" type="checkbox" class="form-check-input"
                      id="enableBatch">
                    <label class="form-check-label" for="enableBatch">
                      <i class="bi bi-layers me-1" style="font-size: 16px;"></i>
                      启用批量迁移
                    </label>
                  </div>
                </div>

                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-stack me-1" style="font-size: 16px;"></i>
                    批量大小
                  </label>
                  <input v-model.number="migrationSettings.batch_size" type="number" class="form-control-sm" min="1">
                </div>

                <button type="submit" class="btn btn-sm btn-primary w-100" :disabled="saving">
                  <i class="bi bi-check-lg me-2" style="font-size: 16px;"></i>
                  {{ saving ? '保存中...' : '保存配置' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <i class="bi bi-sliders me-1" style="font-size: 20px;"></i>
              系统设置
            </h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载设置中...</p>
            </div>
            <div v-else-if="systemSettings">
              <form @submit.prevent="saveSystemSettings">
                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-terminal me-1" style="font-size: 16px;"></i>
                    日志级别
                  </label>
                  <select v-model="systemSettings.log_level" class="form-select">
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </div>

                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    最大并发任务数
                  </label>
                  <input v-model.number="systemSettings.max_concurrent_tasks" type="number" class="form-control"
                    min="1">
                </div>

                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-clock-history me-1" style="font-size: 16px;"></i>
                    任务超时时间（秒）
                  </label>
                  <label>
                    <i class="bi bi-clock-history me-1" style="font-size: 16px;"></i>
                  </label>
                  <input v-model.number="systemSettings.task_timeout" type="number" class="form-control" min="1">
                </div>

                <div class="mb-4">
                  <div class="form-check form-switch">
                    <input v-model="systemSettings.enable_auto_retry" type="checkbox" class="form-check-input"
                      id="enableRetry">
                    <label class="form-check-label" for="enableRetry">
                      <i class="bi bi-arrow-repeat me-1" style="font-size: 16px;"></i>
                      启用自动重试
                    </label>
                  </div>
                </div>

                <div class="mb-4">
                  <label class="form-label">
                    <i class="bi bi-arrow-counterclockwise me-1" style="font-size: 16px;"></i>
                    最大重试次数
                  </label>
                  <input v-model.number="systemSettings.max_retry_count" type="number" class="form-control-sm" min="0">
                </div>

                <button type="submit" class="btn btn-sm btn-primary w-100" :disabled="saving">
                  <i class="bi bi-check-lg me-2" style="font-size: 16px;"></i>
                  {{ saving ? '保存中...' : '保存设置' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="row mt-4">
      <div class="col-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <i class="bi bi-terminal me-1" style="font-size: 20px;"></i>
              迁移日志
            </h5>
            <button @click="loadLogs" class="btn btn-outline-secondary btn-sm">
              <i class="bi bi-arrow-clockwise me-1" style="font-size: 14px;"></i>
              刷新日志
            </button>
          </div>
          <div class="card-body">
            <div v-if="loadingLogs" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载日志中...</p>
            </div>
            <div v-else>
              <div class="log-container">
                <pre class="log-content">{{ logs || '暂无日志' }}</pre>
              </div>
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
    await configApi.saveMigrationSettings(migrationSettings.value)
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
    await configApi.saveSystemSettings(systemSettings.value)
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

<style scoped>
.config-view {
  animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header h1 {
  display: flex;
  align-items: center;
  font-weight: 700;
  color: var(--text);
}

.card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 10px 40px var(--shadow);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 50px var(--shadow);
}

.card-header {
  background: var(--gradient);
  color: white;
  font-weight: 600;
  border: none;
  padding: 1rem 1.5rem;
}

.form-label {
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid var(--input-border);
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem var(--shadow);
}

.form-check-input {
  width: 3rem;
  height: 1.5rem;
  border-radius: 1rem;
  background-color: var(--border);
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.form-check-input:checked {
  background-color: var(--primary);
}

.form-check-label {
  cursor: pointer;
  font-weight: 500;
  color: var(--text);
  display: flex;
  align-items: center;
}

.btn {
  border-radius: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
  border: none;
}

.btn-primary {
  background: var(--gradient);
  box-shadow: 0 4px 15px var(--shadow);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--shadow);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline-secondary {
  border: 2px solid var(--input-border);
  color: var(--text);
}

.btn-outline-secondary:hover {
  background-color: var(--background);
  border-color: var(--border);
}

.log-container {
  background: var(--background);
  border-radius: 0.5rem;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
  box-shadow: inset 0 2px 10px var(--shadow);
}

.log-content {
  color: var(--text);
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
  border-width: 0.3rem;
}

.spinner-border.text-primary {
  border-color: var(--primary);
  border-right-color: transparent;
}
</style>
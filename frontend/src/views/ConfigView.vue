<template>
  <div class="config-view">
    <PageHeader
      title="系统配置"
      subtitle="管理迁移配置和系统设置"
      icon="bi-gear-wide-connected"
    />

    <!-- 全局加载错误提示 -->
    <div v-if="loadError" class="alert alert-warning d-flex align-items-center justify-content-between mb-4" role="alert">
      <span><i class="bi bi-exclamation-triangle me-2"></i>{{ loadError }}</span>
      <button type="button" class="btn btn-sm btn-outline-warning" @click="loadSettings">重试</button>
    </div>

    <!-- Celery 未配置提示 -->
    <div v-if="celeryStatus && !celeryStatus.broker_configured" class="alert alert-warning d-flex align-items-start mb-4" role="alert">
      <i class="bi bi-exclamation-triangle me-2 mt-1"></i>
      <div>
        <strong>定时增量未就绪</strong>
        <p class="mb-0 small">{{ celeryStatus.message }}</p>
        <p class="mb-0 small mt-1">请配置 <code>CELERY_BROKER_URL</code> 并启动 Worker + Beat（<code>./start_dev.sh --celery --beat</code>）。</p>
      </div>
    </div>

    <div class="row g-4">
      <!-- 迁移配置 -->
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <i class="bi bi-arrow-left-right me-1"></i>
              迁移配置
            </h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
              <p class="mt-3 text-muted small">加载配置中...</p>
            </div>
            <form v-else-if="migrationSettings" @submit.prevent="saveMigrationSettings">
              <div class="mb-3">
                <label class="form-label">默认标识符大小写策略</label>
                <select v-model="migrationSettings.default_identifier_case" class="form-select form-select-sm">
                  <option value="lower">全部小写</option>
                  <option value="upper">全部大写</option>
                  <option value="preserve">保持原样</option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label">默认冲突处理策略</label>
                <select v-model="migrationSettings.default_conflict_strategy" class="form-select form-select-sm">
                  <option value="error">遇到冲突时报错</option>
                  <option value="replace">删除并替换已存在对象</option>
                  <option value="skip">跳过已存在对象</option>
                  <option value="append">追加数据（仅适用于表）</option>
                  <option value="truncate">清空表并重新加载数据</option>
                </select>
              </div>

              <div class="mb-3">
                <div class="form-check form-switch">
                  <input
                    v-model="migrationSettings.enable_batch_migration"
                    type="checkbox"
                    class="form-check-input"
                    id="enableBatch"
                  />
                  <label class="form-check-label" for="enableBatch">启用批量迁移</label>
                </div>
              </div>

              <div class="mb-4">
                <label class="form-label">每批拉取行数（batch_size）</label>
                <input
                  v-model.number="migrationSettings.batch_size"
                  type="number"
                  class="form-control form-control-sm"
                  min="100"
                  max="50000"
                />
              </div>

              <div class="mb-3">
                <label class="form-label">每 N 批提交一次</label>
                <input v-model.number="migrationSettings.commit_every_batches" type="number" min="1" max="20" class="form-control form-control-sm" />
              </div>

              <div class="mb-3">
                <label class="form-label">多表并行线程数</label>
                <input v-model.number="migrationSettings.parallel_table_workers" type="number" min="1" max="64" class="form-control form-control-sm" />
              </div>

              <div class="mb-3">
                <div class="form-check form-switch">
                  <input v-model="migrationSettings.enable_fk_replay" type="checkbox" class="form-check-input" id="enableFkReplay" />
                  <label class="form-check-label" for="enableFkReplay">整库/全 Schema 完成后回放外键</label>
                </div>
              </div>

              <button type="submit" class="btn btn-sm btn-primary w-100" :disabled="saving">
                <i class="bi bi-check-lg me-1"></i>
                {{ saving ? '保存中...' : '保存配置' }}
              </button>
            </form>
          </div>
        </div>
      </div>

      <!-- 系统设置 -->
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <i class="bi bi-sliders me-1"></i>
              系统设置
            </h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
              <p class="mt-3 text-muted small">加载设置中...</p>
            </div>
            <form v-else-if="systemSettings" @submit.prevent="saveSystemSettings">
              <div class="mb-3">
                <label class="form-label">日志级别</label>
                <select v-model="systemSettings.log_level" class="form-select form-select-sm">
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label">最大并发任务数</label>
                <input
                  v-model.number="systemSettings.max_concurrent_tasks"
                  type="number"
                  class="form-control form-control-sm"
                  min="1"
                />
              </div>

              <div class="mb-3">
                <label class="form-label">任务超时时间（秒）</label>
                <input
                  v-model.number="systemSettings.task_timeout"
                  type="number"
                  class="form-control form-control-sm"
                  min="1"
                />
              </div>

              <div class="mb-3">
                <div class="form-check form-switch">
                  <input
                    v-model="systemSettings.enable_auto_retry"
                    type="checkbox"
                    class="form-check-input"
                    id="enableRetry"
                  />
                  <label class="form-check-label" for="enableRetry">启用自动重试</label>
                </div>
              </div>

              <div class="mb-4">
                <label class="form-label">最大重试次数</label>
                <input
                  v-model.number="systemSettings.max_retry_count"
                  type="number"
                  class="form-control form-control-sm"
                  min="0"
                />
              </div>

              <button type="submit" class="btn btn-sm btn-primary w-100" :disabled="saving">
                <i class="bi bi-check-lg me-1"></i>
                {{ saving ? '保存中...' : '保存设置' }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- 迁移日志 -->
    <div class="row mt-4">
      <div class="col-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <i class="bi bi-terminal me-1"></i>
              迁移日志
            </h5>
            <button type="button" class="btn btn-outline-secondary btn-sm" :disabled="loadingLogs" @click="loadLogs">
              <i class="bi bi-arrow-clockwise me-1" :class="{ spin: loadingLogs }"></i>
              刷新日志
            </button>
          </div>
          <div class="card-body">
            <div v-if="loadingLogs" class="text-center py-4">
              <div class="spinner-border text-primary spinner-border-sm" role="status"></div>
              <p class="mt-2 text-muted small">加载日志中...</p>
            </div>
            <div v-else-if="logsError" class="text-center py-4 text-muted">
              <i class="bi bi-exclamation-circle me-1"></i>{{ logsError }}
              <button type="button" class="btn btn-sm btn-link" @click="loadLogs">重试</button>
            </div>
            <div v-else class="log-container">
              <pre class="log-content">{{ logs || '暂无日志' }}</pre>
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
import PageHeader from '@/components/PageHeader.vue'

/** 迁移配置默认值 */
const DEFAULT_MIGRATION_SETTINGS = {
  default_identifier_case: 'lower',
  default_conflict_strategy: 'error',
  enable_batch_migration: true,
  batch_size: 5000,
  commit_every_batches: 2,
  progress_save_rows: 10000,
  parallel_table_workers: 16,
  copy_row_threshold: 100000,
  enable_fk_replay: true,
}

/** 系统设置默认值 */
const DEFAULT_SYSTEM_SETTINGS = {
  log_level: 'INFO',
  max_concurrent_tasks: 5,
  task_timeout: 3600,
  enable_auto_retry: false,
  max_retry_count: 3,
}

const loading = ref(false)
const saving = ref(false)
const loadingLogs = ref(false)
const loadError = ref('')
const logsError = ref('')
const migrationSettings = ref<typeof DEFAULT_MIGRATION_SETTINGS | null>(null)
const systemSettings = ref<typeof DEFAULT_SYSTEM_SETTINGS | null>(null)
const logs = ref('')
const celeryStatus = ref<{ broker_configured?: boolean; message?: string } | null>(null)

/** 从 API 响应中解析配置对象（兼容嵌套与扁平两种结构） */
function parseSettings<T extends Record<string, unknown>>(
  raw: unknown,
  nestedKey: string,
  defaults: T,
): T {
  if (!raw || typeof raw !== 'object') return { ...defaults }
  const data = raw as Record<string, unknown>
  const nested = data[nestedKey]
  if (nested && typeof nested === 'object') {
    return { ...defaults, ...(nested as Partial<T>) }
  }
  return { ...defaults, ...(data as Partial<T>) }
}

/** 将日志 API 响应格式化为可读文本 */
function formatLogsResponse(raw: unknown): string {
  if (!raw) return ''
  if (typeof raw === 'string') return raw
  if (Array.isArray(raw)) {
    return raw
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object') {
          const row = item as Record<string, unknown>
          const head = `[${row.created_at ?? '-'}] ${row.name ?? '任务'} (${row.status ?? '-'})`
          const body = typeof row.log === 'string' ? row.log : typeof row.message === 'string' ? row.message : ''
          return body ? `${head}\n${body}` : head
        }
        return String(item)
      })
      .join('\n\n---\n\n')
  }
  return String(raw)
}

const loadSettings = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [migrationRes, systemRes, celeryRes] = await Promise.all([
      configApi.getMigrationSettings(),
      configApi.getSystemSettings(),
      configApi.getCeleryStatus().catch(() => ({ data: null })),
    ])

    migrationSettings.value = parseSettings(
      migrationRes.data,
      'migration_settings',
      DEFAULT_MIGRATION_SETTINGS,
    )
    systemSettings.value = parseSettings(
      systemRes.data,
      'system_settings',
      DEFAULT_SYSTEM_SETTINGS,
    )
    if (celeryRes.data) {
      celeryStatus.value = celeryRes.data as typeof celeryStatus.value
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    loadError.value = '加载配置失败，已显示默认值，可修改后保存或点击重试'
    migrationSettings.value = { ...DEFAULT_MIGRATION_SETTINGS }
    systemSettings.value = { ...DEFAULT_SYSTEM_SETTINGS }
  } finally {
    loading.value = false
  }
}

const saveMigrationSettings = async () => {
  if (!migrationSettings.value) return
  saving.value = true
  try {
    await configApi.saveMigrationSettings(migrationSettings.value)
    alert('迁移配置保存成功')
  } catch (error) {
    console.error('保存迁移配置失败:', error)
    alert('保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

const saveSystemSettings = async () => {
  if (!systemSettings.value) return
  saving.value = true
  try {
    await configApi.saveSystemSettings(systemSettings.value)
    alert('系统设置保存成功')
  } catch (error) {
    console.error('保存系统设置失败:', error)
    alert('保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

const loadLogs = async () => {
  loadingLogs.value = true
  logsError.value = ''
  try {
    const res = await logsApi.getLogs({ limit: 200 })
    logs.value = formatLogsResponse(res.data?.logs)
  } catch (error) {
    console.error('加载日志失败:', error)
    logsError.value = '加载日志失败'
    logs.value = ''
  } finally {
    loadingLogs.value = false
  }
}

onMounted(async () => {
  await loadSettings()
  // 配置加载完成后再拉取日志，避免并发请求加重卡顿
  loadLogs()
})
</script>

<style scoped>
.config-view {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-header h5 {
  font-size: 15px;
  display: flex;
  align-items: center;
}

.form-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
  margin-bottom: 6px;
}

.form-check-label {
  font-size: 13px;
  color: var(--text);
}

.log-container {
  background: var(--log-bg, #1e1e2e);
  border-radius: 8px;
  padding: 12px 16px;
  max-height: 360px;
  overflow-y: auto;
}

.log-content {
  color: var(--log-fg, #cdd6f4);
  font-family: ui-monospace, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

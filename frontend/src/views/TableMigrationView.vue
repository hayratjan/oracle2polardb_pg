<template>
  <div class="table-migration-view">
    <PageHeader
      title="表级迁移向导"
      subtitle="按表选择、配置目标环境并支持增量同步"
      icon="bi-table"
    />

    <!-- 步骤条 -->
    <div class="steps-bar mb-4">
      <div
        v-for="(label, idx) in stepLabels"
        :key="idx"
        class="step-item"
        :class="{ active: currentStep === idx, done: currentStep > idx }"
      >
        <span class="step-num">{{ idx + 1 }}</span>
        <span class="step-label">{{ label }}</span>
      </div>
    </div>

    <div class="card">
      <div class="card-body">
        <!-- 步骤 1：源端 -->
        <div v-show="currentStep === 0">
          <h5 class="mb-3"><i class="bi bi-database me-1"></i>源数据库配置</h5>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Oracle 连接</label>
              <select v-model="form.oracle_connection" class="form-select-sm" @change="onOracleChange">
                <option :value="0">请选择</option>
                <option v-for="c in oracleConnections" :key="c.id" :value="c.id">
                  {{ c.name }} ({{ c.host }}:{{ c.port }})
                </option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label">源 Schema</label>
              <select v-model="form.source_schema" class="form-select-sm" @change="onSchemaChange">
                <option value="">请选择</option>
                <option v-for="s in schemas" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 步骤 2：选表 -->
        <div v-show="currentStep === 1">
          <h5 class="mb-3"><i class="bi bi-check2-square me-1"></i>选择要迁移的表</h5>
          <div class="source-objects-controls mb-2">
            <button type="button" class="btn btn-sm btn-outline-primary me-2" @click="reloadTables" :disabled="!form.oracle_connection || !form.source_schema">
              <i class="bi bi-arrow-clockwise me-1"></i>刷新
            </button>
            <button type="button" class="btn btn-sm btn-outline-secondary me-2" @click="selectAllObjects" :disabled="filteredObjects.length === 0">全选</button>
            <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearAllObjects" :disabled="selectedSourceObjects.length === 0">清空</button>
            <span class="text-muted ms-3">已选 <strong>{{ selectedSourceObjects.length }}</strong> / {{ filteredObjects.length }}</span>
          </div>
          <input v-model="searchTerm" type="text" class="form-control-sm mb-2" placeholder="搜索表名...">
          <div v-if="loadingObjects" class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-primary"></div>
          </div>
          <div v-else class="source-objects-list" style="max-height: 320px; overflow-y: auto;">
            <div v-for="obj in filteredObjects" :key="obj" class="form-check">
              <input class="form-check-input" type="checkbox" :id="'tbl-' + obj" :value="obj" v-model="selectedSourceObjects">
              <label class="form-check-label" :for="'tbl-' + obj">{{ obj }}</label>
            </div>
            <p v-if="!filteredObjects.length" class="text-muted text-center py-3">暂无表，请先选择源 Schema</p>
          </div>
        </div>

        <!-- 步骤 3：目标环境 -->
        <div v-show="currentStep === 2">
          <h5 class="mb-3"><i class="bi bi-server me-1"></i>目标环境配置</h5>
          <TargetEnvWizard
            v-model:postgres-connection="form.postgres_connection"
            :postgres-connections="postgresConnections"
            @update:config="targetConfig = $event"
            @prepared="onTargetPrepared"
          />
        </div>

        <!-- 步骤 4：增量策略 -->
        <div v-show="currentStep === 3">
          <h5 class="mb-3"><i class="bi bi-arrow-repeat me-1"></i>增量与定时（可选）</h5>
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">增量模式</label>
              <select v-model="form.incremental_mode" class="form-select-sm" @change="onIncrementalChange">
                <option value="none">全量</option>
                <option value="timestamp">按水位列增量</option>
                <option value="pk_mirror">主键对齐增量</option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label">水位列名</label>
              <input v-model="form.watermark_column" type="text" class="form-control-sm" placeholder="如 UPDATED_AT" :disabled="form.incremental_mode !== 'timestamp'">
            </div>
            <div class="col-md-4">
              <label class="form-label">冲突策略</label>
              <select v-model="form.conflict_strategy" class="form-select-sm">
                <option value="error">遇到冲突时报错</option>
                <option value="replace">删除并替换</option>
                <option value="skip">跳过已存在</option>
                <option value="append">追加数据</option>
                <option value="truncate">清空并重新加载</option>
              </select>
            </div>
            <div class="col-md-4 d-flex align-items-end">
              <div class="form-check">
                <input v-model="form.schedule_enabled" class="form-check-input" type="checkbox" id="schedEn" :disabled="!scheduleAllowed">
                <label class="form-check-label" for="schedEn">启用定时执行</label>
              </div>
            </div>
            <div class="col-md-4">
              <label class="form-label">定时间隔（分钟）</label>
              <input v-model.number="form.schedule_interval_minutes" type="number" min="1" class="form-control-sm" :disabled="!form.schedule_enabled">
            </div>
            <div class="col-md-4">
              <label class="form-label">标识符大小写</label>
              <select v-model="form.identifier_case" class="form-select-sm">
                <option value="lower">全部小写</option>
                <option value="upper">全部大写</option>
                <option value="preserve">保持原样</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 步骤 5：确认 -->
        <div v-show="currentStep === 4">
          <h5 class="mb-3"><i class="bi bi-check-circle me-1"></i>确认并提交</h5>
          <div class="row g-3 mb-3">
            <div class="col-md-6">
              <label class="form-label">任务名称</label>
              <input v-model="form.name" type="text" class="form-control-sm" required placeholder="输入任务名称">
            </div>
          </div>
          <table class="table table-sm">
            <tbody>
              <tr><th>源端</th><td>{{ form.source_schema }} · {{ selectedSourceObjects.length }} 张表</td></tr>
              <tr><th>目标库</th><td>{{ resolvedDatabase || '（连接默认）' }}</td></tr>
              <tr><th>目标 Schema</th><td>{{ resolvedSchema }}</td></tr>
              <tr><th>增量模式</th><td>{{ incrementalLabel }}</td></tr>
              <tr><th>冲突策略</th><td>{{ form.conflict_strategy }}</td></tr>
            </tbody>
          </table>
          <div class="form-check mb-3">
            <input v-model="prepareTarget" class="form-check-input" type="checkbox" id="prepTarget">
            <label class="form-check-label" for="prepTarget">提交前自动准备目标环境（建库/用户/Schema 等）</label>
          </div>
        </div>

        <!-- 导航按钮 -->
        <div class="d-flex justify-content-between mt-4">
          <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="currentStep === 0" @click="currentStep--">
            <i class="bi bi-chevron-left"></i> 上一步
          </button>
          <button v-if="currentStep < 4" type="button" class="btn btn-sm btn-primary" :disabled="!canNext" @click="currentStep++">
            下一步 <i class="bi bi-chevron-right"></i>
          </button>
          <button v-else type="button" class="btn btn-sm btn-primary" :disabled="submitting || !form.name" @click="handleSubmit">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-rocket-takeoff me-1"></i>
            创建迁移任务
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import TargetEnvWizard from '@/components/TargetEnvWizard.vue'
import { useMigrationSource } from '@/composables/useMigrationSource'
import { migrationPlanApi } from '@/api'
import type { TargetProvisioningConfig } from '@/api'

const router = useRouter()
const stepLabels = ['源端配置', '选择表', '目标环境', '增量策略', '确认提交']
const currentStep = ref(0)
const submitting = ref(false)
const prepareTarget = ref(false)
const targetConfig = ref<TargetProvisioningConfig>({})
const resolvedDatabase = ref('')
const resolvedSchema = ref('public')

const {
  oracleConnections, postgresConnections, schemas,
  selectedSourceObjects, loadingObjects, searchTerm, filteredObjects,
  loadConnections, loadOracleSchemas, loadSourceObjects,
  selectAllObjects, clearAllObjects,
} = useMigrationSource()

const form = ref({
  name: '',
  oracle_connection: 0,
  postgres_connection: 0,
  source_schema: '',
  target_schema: 'public',
  postgres_database: '',
  incremental_mode: 'none',
  watermark_column: '',
  schedule_enabled: false,
  schedule_interval_minutes: 60,
  conflict_strategy: 'error',
  identifier_case: 'lower',
})

const scheduleAllowed = computed(() =>
  form.value.incremental_mode === 'timestamp' || form.value.incremental_mode === 'pk_mirror',
)

const incrementalLabel = computed(() => {
  const m: Record<string, string> = { none: '全量', timestamp: '水位列增量', pk_mirror: '主键对齐' }
  return m[form.value.incremental_mode] || form.value.incremental_mode
})

const canNext = computed(() => {
  if (currentStep.value === 0) return form.value.oracle_connection && form.value.source_schema
  if (currentStep.value === 1) return selectedSourceObjects.value.length > 0
  if (currentStep.value === 2) return form.value.postgres_connection > 0
  return true
})

const onOracleChange = async () => {
  form.value.source_schema = ''
  selectedSourceObjects.value = []
  await loadOracleSchemas(form.value.oracle_connection)
}

const onSchemaChange = async () => {
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    await loadSourceObjects(form.value.oracle_connection, form.value.source_schema, 'TABLE')
  }
}

const reloadTables = () => onSchemaChange()

const onIncrementalChange = () => {
  if (form.value.incremental_mode === 'pk_mirror') {
    form.value.conflict_strategy = 'append'
  }
  if (!scheduleAllowed.value) form.value.schedule_enabled = false
}

const onTargetPrepared = (resolved: { database?: string; schema?: string }) => {
  if (resolved.database) {
    resolvedDatabase.value = resolved.database
    form.value.postgres_database = resolved.database
  }
  if (resolved.schema) {
    resolvedSchema.value = resolved.schema
    form.value.target_schema = resolved.schema
  }
}

const handleSubmit = async () => {
  submitting.value = true
  const cfg = targetConfig.value
  const dbName = resolvedDatabase.value || cfg.database?.name || form.value.postgres_database
  const schemaName = resolvedSchema.value || cfg.schema?.name || form.value.target_schema || 'public'
  try {
    const payload: Record<string, unknown> = {
      name: form.value.name,
      oracle_connection: form.value.oracle_connection,
      postgres_connection: form.value.postgres_connection,
      source_schema: form.value.source_schema,
      target_schema: schemaName,
      postgres_database: dbName,
      source_objects: selectedSourceObjects.value,
      incremental_mode: form.value.incremental_mode,
      watermark_column: form.value.watermark_column,
      schedule_enabled: form.value.schedule_enabled,
      schedule_interval_minutes: form.value.schedule_interval_minutes,
      conflict_strategy: form.value.conflict_strategy,
      identifier_case: form.value.identifier_case,
      prepare_target: prepareTarget.value,
      target_provisioning: targetConfig.value,
    }
    const res = await migrationPlanApi.createTableMigration(payload)
    if (res.data.status === 'success') {
      router.push(`/task/${res.data.task_id}`)
    } else {
      alert(res.data.message || '创建失败')
    }
  } catch (err: any) {
    alert(err?.response?.data?.message || '创建任务失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadConnections()
})
</script>

<style scoped>
.steps-bar {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  background: var(--bs-light, #f0f0f0);
  opacity: 0.6;
}
.step-item.active { opacity: 1; background: var(--bs-primary-bg-subtle, #cfe2ff); }
.step-item.done { opacity: 0.85; }
.step-num {
  width: 1.5rem; height: 1.5rem;
  border-radius: 50%;
  background: var(--bs-primary, #0d6efd);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 600;
}
.step-item:not(.active):not(.done) .step-num { background: #6c757d; }
</style>

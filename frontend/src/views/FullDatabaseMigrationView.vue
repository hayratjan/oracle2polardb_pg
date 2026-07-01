<template>
  <div class="full-database-migration-view">
    <PageHeader
      title="整库一键迁移"
      subtitle="单 Oracle 连接下多 Schema、多对象类型编排迁移"
      icon="bi-cloud-arrow-up"
    />

    <div class="row g-4">
      <div class="col-lg-8">
        <div class="card mb-4">
          <div class="card-body">
            <h5 class="mb-3"><i class="bi bi-database me-1"></i>源端 Oracle 连接</h5>
            <div class="row g-3">
              <div class="col-md-8">
                <select v-model="oracleConnection" class="form-select-sm" @change="loadDiscovery">
                  <option :value="0">请选择 Oracle 连接</option>
                  <option v-for="c in oracleConnections" :key="c.id" :value="c.id">
                    {{ c.name }} ({{ c.host }}:{{ c.port }})
                  </option>
                </select>
              </div>
              <div class="col-md-4">
                <button type="button" class="btn btn-sm btn-outline-primary w-100" :disabled="!oracleConnection || discovering" @click="loadDiscovery">
                  <span v-if="discovering" class="spinner-border spinner-border-sm me-1"></span>
                  刷新发现
                </button>
              </div>
            </div>

            <!-- Schema 发现树 -->
            <div v-if="discoverySchemas.length" class="mt-3">
              <p class="text-muted small">共发现 <strong>{{ discoverySchemas.length }}</strong> 个 Schema</p>
              <div class="table-responsive" style="max-height: 240px; overflow-y: auto;">
                <table class="table table-sm table-hover mb-0">
                  <thead>
                    <tr>
                      <th>Oracle Schema</th>
                      <th>表</th>
                      <th>视图</th>
                      <th>序列</th>
                      <th>触发器</th>
                      <th>例程</th>
                      <th>目标 Schema</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, i) in schemaMappings" :key="item.source_schema">
                      <td><code>{{ item.source_schema }}</code></td>
                      <td>{{ discoverySchemas[i]?.stats?.tables ?? 0 }}</td>
                      <td>{{ discoverySchemas[i]?.stats?.views ?? 0 }}</td>
                      <td>{{ discoverySchemas[i]?.stats?.sequences ?? 0 }}</td>
                      <td>{{ discoverySchemas[i]?.stats?.triggers ?? 0 }}</td>
                      <td>{{ discoverySchemas[i]?.stats?.routines ?? 0 }}</td>
                      <td>
                        <input v-model="item.target_schema" type="text" class="form-control-sm" style="min-width: 100px;">
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <p v-else-if="oracleConnection && !discovering" class="text-muted mt-3 mb-0">点击「刷新发现」加载 Schema 统计</p>

            <div v-if="discoveryWarnings.length" class="alert alert-warning mt-3 mb-0" role="alert">
              <strong><i class="bi bi-exclamation-triangle me-1"></i>Discovery 告警</strong>
              <ul class="mb-0 mt-2 small ps-3">
                <li v-for="(w, i) in discoveryWarnings" :key="i">{{ w }}</li>
              </ul>
            </div>
          </div>
        </div>

        <div class="card mb-4">
          <div class="card-body">
            <h5 class="mb-3"><i class="bi bi-server me-1"></i>目标环境</h5>
            <TargetEnvWizard
              v-model:postgres-connection="postgresConnection"
              :postgres-connections="postgresConnections"
              @update:config="targetConfig = $event"
              @prepared="onTargetPrepared"
            />
          </div>
        </div>

        <div class="card mb-4">
          <div class="card-body">
            <h5 class="mb-3"><i class="bi bi-sliders me-1"></i>迁移选项</h5>
            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label class="form-label">任务名称</label>
                <input v-model="taskName" type="text" class="form-control-sm" placeholder="整库迁移任务名称">
              </div>
              <div class="col-md-3">
                <label class="form-label">冲突策略</label>
                <select v-model="conflictStrategy" class="form-select-sm">
                  <option value="error">遇到冲突报错</option>
                  <option value="replace">删除并替换</option>
                  <option value="skip">跳过已存在</option>
                </select>
              </div>
              <div class="col-md-3">
                <label class="form-label">标识符大小写</label>
                <select v-model="identifierCase" class="form-select-sm">
                  <option value="lower">小写</option>
                  <option value="upper">大写</option>
                  <option value="preserve">保持原样</option>
                </select>
              </div>
            </div>
            <p class="text-muted small mb-2">迁移对象类型（按依赖顺序执行）</p>
            <div class="object-type-grid">
              <div
                v-for="item in objectTypeOptions"
                :key="item.key"
                class="object-type-card"
                :class="{ active: objectTypes[item.key] }"
                @click="toggleObjectType(item.key)"
              >
                <div class="d-flex align-items-center gap-2">
                  <div class="object-type-icon" :style="{ background: item.bg, color: item.color }">
                    <i :class="['bi', item.icon]"></i>
                  </div>
                  <div class="object-type-info">
                    <div class="object-type-name">{{ item.label }}</div>
                    <div class="object-type-desc">{{ item.desc }}</div>
                  </div>
                  <input class="form-check-input ms-auto" type="checkbox" :id="'ot-' + item.key" v-model="objectTypes[item.key]" @click.stop>
                </div>
              </div>
            </div>
            <div class="d-flex gap-2 mt-2">
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="selectAllObjectTypes">全选</button>
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="invertObjectTypes">反选</button>
              <span class="text-muted small ms-auto align-self-center">已选 {{ selectedObjectTypeCount }} / {{ objectTypeOptions.length }}</span>
            </div>
            <div class="form-check mt-3">
              <input v-model="autoPrepare" class="form-check-input" type="checkbox" id="autoPrep">
              <label class="form-check-label" for="autoPrep">启动前自动准备目标环境</label>
            </div>
          </div>
        </div>

        <div class="d-flex gap-2">
          <button type="button" class="btn btn-primary" :disabled="submitting || !canSubmit" @click="handleCreate(false)">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-plus-circle me-1"></i>
            创建任务
          </button>
          <button type="button" class="btn btn-success" :disabled="submitting || !canSubmit" @click="handleCreate(true)">
            <i class="bi bi-rocket-takeoff me-1"></i>
            创建并立即启动
          </button>
        </div>
      </div>

      <div class="col-lg-4">
        <div class="card">
          <div class="card-header"><h6 class="mb-0">迁移阶段</h6></div>
          <div class="card-body">
            <ol class="small mb-0 ps-3">
              <li>准备目标环境</li>
              <li>迁移序列</li>
              <li>迁移物理表</li>
              <li>回放外键约束</li>
              <li>迁移视图</li>
              <li>迁移物化视图</li>
              <li>导出触发器</li>
              <li>迁移例程</li>
            </ol>
            <p class="text-muted small mt-3 mb-0">触发器仅导出源码模板，需人工改写后在目标库执行。</p>
          </div>
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
import { databaseApi, migrationPlanApi, migrationTaskApi } from '@/api'
import type { TargetProvisioningConfig } from '@/api'

const router = useRouter()
const { oracleConnections, postgresConnections, loadConnections } = useMigrationSource()

const oracleConnection = ref(0)
const postgresConnection = ref(0)
const discovering = ref(false)
const submitting = ref(false)
const discoverySchemas = ref<{ name: string; stats: Record<string, number> }[]>([])
const discoveryWarnings = ref<string[]>([])
const schemaMappings = ref<{ source_schema: string; target_schema: string }[]>([])
const targetConfig = ref<TargetProvisioningConfig>({})
const resolvedDatabase = ref('')
const taskName = ref('')
const conflictStrategy = ref('error')
const identifierCase = ref('lower')
const autoPrepare = ref(true)

const objectTypeOptions = [
  { key: 'sequences',         label: '序列',         icon: 'bi-list-ol',          desc: '序号发生器',          bg: 'rgba(245, 158, 11, 0.15)', color: '#d97706' },
  { key: 'tables',            label: '物理表',       icon: 'bi-table',           desc: '表结构 + 数据',       bg: 'rgba(37, 99, 235, 0.15)',  color: '#2563eb' },
  { key: 'views',             label: '视图',         icon: 'bi-eye',             desc: 'CREATE VIEW DDL',     bg: 'rgba(139, 92, 246, 0.15)', color: '#7c3aed' },
  { key: 'materialized_views',label: '物化视图',     icon: 'bi-eye-fill',        desc: '物化查询结果',        bg: 'rgba(168, 85, 247, 0.15)', color: '#9333ea' },
  { key: 'triggers',          label: '触发器',       icon: 'bi-lightning',       desc: '导出源码 + 模板',     bg: 'rgba(220, 38, 38, 0.15)',  color: '#dc2626' },
  { key: 'routines',          label: '例程',         icon: 'bi-code-square',     desc: '过程 / 函数',         bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981' },
]

const objectTypes = ref<Record<string, boolean>>({
  sequences: true,
  tables: true,
  views: true,
  materialized_views: true,
  triggers: true,
  routines: true,
})

const toggleObjectType = (key: string) => {
  objectTypes.value[key] = !objectTypes.value[key]
}

const selectAllObjectTypes = () => {
  objectTypeOptions.forEach(o => { objectTypes.value[o.key] = true })
}

const invertObjectTypes = () => {
  objectTypeOptions.forEach(o => { objectTypes.value[o.key] = !objectTypes.value[o.key] })
}

const selectedObjectTypeCount = computed(() =>
  objectTypeOptions.filter(o => objectTypes.value[o.key]).length
)

const canSubmit = computed(() =>
  oracleConnection.value > 0 &&
  postgresConnection.value > 0 &&
  taskName.value.trim() &&
  schemaMappings.value.length > 0,
)

/** 加载 Oracle 整库发现 */
const loadDiscovery = async () => {
  if (!oracleConnection.value) return
  discovering.value = true
  try {
    const res = await databaseApi.getOracleDiscovery({ connection_id: oracleConnection.value })
    discoverySchemas.value = res.data.schemas || []
    discoveryWarnings.value = res.data.warnings || []
    schemaMappings.value = discoverySchemas.value.map((s: { name: string }) => ({
      source_schema: s.name,
      target_schema: s.name.toLowerCase(),
    }))
    if (!taskName.value) {
      const conn = oracleConnections.value.find((c: any) => c.id === oracleConnection.value)
      taskName.value = `整库迁移-${conn?.name || oracleConnection.value}`
    }
  } catch (err) {
    console.error('发现失败:', err)
  } finally {
    discovering.value = false
  }
}

const onTargetPrepared = (resolved: { database?: string; schema?: string }) => {
  if (resolved.database) resolvedDatabase.value = resolved.database
}

const handleCreate = async (autoStart: boolean) => {
  submitting.value = true
  try {
    const payload: Record<string, unknown> = {
      name: taskName.value,
      oracle_connection: oracleConnection.value,
      postgres_connection: postgresConnection.value,
      postgres_database: resolvedDatabase.value,
      conflict_strategy: conflictStrategy.value,
      identifier_case: identifierCase.value,
      prepare_target: autoPrepare.value,
      target_provisioning: {
        ...targetConfig.value,
        schema_mappings: schemaMappings.value,
        object_types: { ...objectTypes.value },
        auto_prepare: autoPrepare.value,
        prepare_config: targetConfig.value,
      },
    }
    const res = await migrationPlanApi.createFullDatabaseMigration(payload)
    if (res.data.status !== 'success') {
      alert(res.data.message || '创建失败')
      return
    }
    const taskId = res.data.task_id
    if (autoStart && taskId) {
      await migrationTaskApi.start(taskId, { postgres_database: resolvedDatabase.value || undefined })
    }
    router.push(`/task/${taskId}`)
  } catch (err: any) {
    alert(err?.response?.data?.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadConnections)
</script>

<style scoped>
.full-database-migration-view {
  animation: fadeIn 0.4s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.object-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
}

.object-type-card {
  border: 2px solid var(--border, #e2e8f0);
  border-radius: 0.6rem;
  padding: 0.75rem;
  background: var(--surface, #fff);
  cursor: pointer;
  transition: all 0.2s ease;
}

.object-type-card:hover {
  border-color: var(--primary, #2563eb);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
  transform: translateY(-1px);
}

.object-type-card.active {
  border-color: var(--primary, #2563eb);
  background: rgba(37, 99, 235, 0.04);
  box-shadow: 0 0 0 1px var(--primary, #2563eb) inset;
}

.object-type-icon {
  width: 36px;
  height: 36px;
  border-radius: 0.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.05rem;
  flex-shrink: 0;
}

.object-type-info {
  flex: 1;
  min-width: 0;
}

.object-type-name {
  font-weight: 600;
  font-size: 0.92rem;
  color: var(--text, #1f2937);
}

.object-type-desc {
  font-size: 0.75rem;
  color: var(--text-muted, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

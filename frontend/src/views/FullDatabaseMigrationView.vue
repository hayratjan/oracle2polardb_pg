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
            <div class="d-flex flex-wrap gap-3">
              <div v-for="(label, key) in objectTypeLabels" :key="key" class="form-check">
                <input class="form-check-input" type="checkbox" :id="'ot-' + key" v-model="objectTypes[key]">
                <label class="form-check-label" :for="'ot-' + key">{{ label }}</label>
              </div>
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
const schemaMappings = ref<{ source_schema: string; target_schema: string }[]>([])
const targetConfig = ref<TargetProvisioningConfig>({})
const resolvedDatabase = ref('')
const taskName = ref('')
const conflictStrategy = ref('error')
const identifierCase = ref('lower')
const autoPrepare = ref(true)

const objectTypeLabels: Record<string, string> = {
  sequences: '序列',
  tables: '物理表',
  views: '视图',
  materialized_views: '物化视图',
  triggers: '触发器',
  routines: '例程',
}

const objectTypes = ref<Record<string, boolean>>({
  sequences: true,
  tables: true,
  views: true,
  materialized_views: true,
  triggers: true,
  routines: true,
})

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

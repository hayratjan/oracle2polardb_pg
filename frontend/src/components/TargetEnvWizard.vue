<template>
  <div class="target-env-wizard">
    <!-- PolarDB 连接 -->
    <div class="row g-3 mb-3">
      <div class="col-12">
        <label class="form-label">PolarDB/PostgreSQL 连接</label>
        <select
          :value="postgresConnection"
          class="form-select-sm"
          @change="onConnectionChange"
        >
          <option :value="0">请选择连接</option>
          <option v-for="conn in postgresConnections" :key="conn.id" :value="conn.id">
            {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
          </option>
        </select>
      </div>
    </div>

    <!-- 目标数据库 -->
    <div class="resource-block border rounded p-3 mb-3">
      <h6 class="mb-3"><i class="bi bi-database me-1"></i>目标数据库</h6>
      <div class="row g-2">
        <div class="col-md-4">
          <select v-model="local.database.mode" class="form-select-sm">
            <option value="existing">选择已有</option>
            <option value="create">新建数据库</option>
            <option value="skip">跳过（使用连接默认库）</option>
          </select>
        </div>
        <div class="col-md-4" v-if="local.database.mode === 'existing'">
          <select v-model="local.database.name" class="form-select-sm" @change="onDatabaseChange">
            <option value="">请选择</option>
            <option v-for="db in pgDatabases" :key="db" :value="db">{{ db }}</option>
          </select>
        </div>
        <template v-if="local.database.mode === 'create'">
          <div class="col-md-4">
            <input v-model="local.database.name" type="text" class="form-control-sm" placeholder="新数据库名">
          </div>
          <div class="col-md-4">
            <input v-model="local.database.encoding" type="text" class="form-control-sm" placeholder="编码 UTF8">
          </div>
        </template>
      </div>
    </div>

    <!-- 表空间 -->
    <div class="resource-block border rounded p-3 mb-3">
      <h6 class="mb-3"><i class="bi bi-hdd me-1"></i>表空间</h6>
      <div class="row g-2">
        <div class="col-md-4">
          <select v-model="local.tablespace.mode" class="form-select-sm">
            <option value="skip">使用默认表空间</option>
            <option value="existing">选择已有</option>
            <option value="create">新建表空间</option>
          </select>
        </div>
        <div class="col-md-4" v-if="local.tablespace.mode === 'existing'">
          <select v-model="local.tablespace.name" class="form-select-sm">
            <option value="">请选择</option>
            <option v-for="ts in tablespaces" :key="ts" :value="ts">{{ ts }}</option>
          </select>
        </div>
        <template v-if="local.tablespace.mode === 'create'">
          <div class="col-md-4">
            <input v-model="local.tablespace.name" type="text" class="form-control-sm" placeholder="表空间名">
          </div>
          <div class="col-md-4">
            <input v-model="local.tablespace.location" type="text" class="form-control-sm" placeholder="服务器路径 LOCATION">
          </div>
        </template>
      </div>
      <p class="text-muted small mb-0 mt-2">创建表空间需超级用户权限及服务器目录路径。</p>
    </div>

    <!-- 用户 -->
    <div class="resource-block border rounded p-3 mb-3">
      <h6 class="mb-3"><i class="bi bi-person me-1"></i>数据库用户</h6>
      <div class="row g-2">
        <div class="col-md-4">
          <select v-model="local.user.mode" class="form-select-sm">
            <option value="skip">跳过</option>
            <option value="existing">选择已有</option>
            <option value="create">新建用户</option>
          </select>
        </div>
        <div class="col-md-4" v-if="local.user.mode === 'existing'">
          <select v-model="local.user.username" class="form-select-sm">
            <option value="">请选择</option>
            <option v-for="u in pgUsers" :key="u" :value="u">{{ u }}</option>
          </select>
        </div>
        <template v-if="local.user.mode === 'create'">
          <div class="col-md-4">
            <input v-model="local.user.username" type="text" class="form-control-sm" placeholder="用户名">
          </div>
          <div class="col-md-4">
            <input v-model="local.user.password" type="password" class="form-control-sm" placeholder="密码">
          </div>
          <div class="col-md-4 d-flex align-items-center">
            <div class="form-check">
              <input v-model="local.user.createdb" class="form-check-input" type="checkbox" id="userCreatedb">
              <label class="form-check-label" for="userCreatedb">允许 CREATEDB</label>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Schema -->
    <div class="resource-block border rounded p-3 mb-3">
      <h6 class="mb-3"><i class="bi bi-diagram-3 me-1"></i>目标 Schema</h6>
      <div class="row g-2">
        <div class="col-md-4">
          <select v-model="local.schema.mode" class="form-select-sm">
            <option value="existing">选择已有</option>
            <option value="create">新建 Schema</option>
          </select>
        </div>
        <div class="col-md-4" v-if="local.schema.mode === 'existing'">
          <select v-model="local.schema.name" class="form-select-sm">
            <option value="public">public (默认)</option>
            <option v-for="s in pgSchemas" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <template v-if="local.schema.mode === 'create'">
          <div class="col-md-4">
            <input v-model="local.schema.name" type="text" class="form-control-sm" placeholder="Schema 名">
          </div>
          <div class="col-md-4">
            <input v-model="local.schema.owner" type="text" class="form-control-sm" placeholder="所有者（可选）">
          </div>
        </template>
      </div>
    </div>

    <!-- 准备环境按钮 -->
    <div v-if="showPrepareButton" class="d-flex gap-2 align-items-center">
      <button
        type="button"
        class="btn btn-sm btn-outline-primary"
        :disabled="!postgresConnection || preparing"
        @click="handlePrepare"
      >
        <span v-if="preparing" class="spinner-border spinner-border-sm me-1"></span>
        <i v-else class="bi bi-tools me-1"></i>
        测试并准备环境
      </button>
      <span v-if="prepareMessage" :class="prepareOk ? 'text-success' : 'text-danger'" class="small">
        {{ prepareMessage }}
      </span>
    </div>

    <!-- 准备步骤明细 -->
    <ul v-if="prepareSteps.length" class="list-unstyled small mt-2 mb-0">
      <li v-for="(step, i) in prepareSteps" :key="i" class="text-muted">
        [{{ step.step }}] {{ step.status }}: {{ step.message }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { databaseApi, targetEnvApi } from '@/api'
import type { TargetProvisioningConfig } from '@/api'

const props = withDefaults(defineProps<{
  postgresConnection: number
  postgresConnections: any[]
  showPrepareButton?: boolean
}>(), {
  showPrepareButton: true,
})

const emit = defineEmits<{
  'update:postgresConnection': [value: number]
  'update:config': [value: TargetProvisioningConfig]
  'prepared': [result: { database?: string; schema?: string; user?: string }]
}>()

/** 本地资源配置 */
const local = reactive<TargetProvisioningConfig>({
  database: { mode: 'existing', name: '', encoding: 'UTF8' },
  tablespace: { mode: 'skip', name: '', location: '' },
  user: { mode: 'skip', username: '', password: '', createdb: false },
  schema: { mode: 'existing', name: 'public' },
})

const pgDatabases = ref<string[]>([])
const pgSchemas = ref<string[]>([])
const pgUsers = ref<string[]>([])
const tablespaces = ref<string[]>([])
const preparing = ref(false)
const prepareMessage = ref('')
const prepareOk = ref(false)
const prepareSteps = ref<{ step: string; status: string; message: string }[]>([])

/** 向父组件同步配置 */
const emitConfig = () => {
  emit('update:config', {
    connection_id: props.postgresConnection,
    database: { ...local.database },
    tablespace: { ...local.tablespace },
    user: { ...local.user },
    schema: { ...local.schema },
  })
}

watch(local, emitConfig, { deep: true })

const onConnectionChange = async (e: Event) => {
  const id = Number((e.target as HTMLSelectElement).value)
  emit('update:postgresConnection', id)
  await refreshLists(id)
}

const onDatabaseChange = async () => {
  if (props.postgresConnection && local.database.name) {
    await loadSchemasAndUsers(props.postgresConnection, local.database.name)
  }
  emitConfig()
}

/** 刷新 PG 侧列表 */
const refreshLists = async (connId: number) => {
  if (!connId) return
  try {
    const dbRes = await databaseApi.getPostgresDatabases({ connection_id: connId })
    pgDatabases.value = dbRes.data.databases || []
    const conn = props.postgresConnections.find((c: any) => c.id === connId)
    if (conn?.database && !local.database.name) {
      local.database.name = conn.database
    }
    const db = local.database.name || conn?.database
    if (db) {
      await loadSchemasAndUsers(connId, db)
    }
    const tsRes = await databaseApi.getPgTablespaces({ connection_id: connId, database: db })
    tablespaces.value = tsRes.data.tablespaces || []
  } catch (err) {
    console.error('刷新目标环境列表失败:', err)
  }
}

const loadSchemasAndUsers = async (connId: number, database: string) => {
  const [schemaRes, userRes] = await Promise.all([
    databaseApi.getPgSchemas({ connection_id: connId, database }),
    databaseApi.getPgUsers({ connection_id: connId, database }),
  ])
  pgSchemas.value = schemaRes.data.schemas || []
  pgUsers.value = userRes.data.users || []
}

/** 测试并准备目标环境 */
const handlePrepare = async () => {
  if (!props.postgresConnection) return
  preparing.value = true
  prepareMessage.value = ''
  prepareSteps.value = []
  try {
    const payload = {
      connection_id: props.postgresConnection,
      database: local.database,
      tablespace: local.tablespace,
      user: local.user,
      schema: local.schema,
    }
    const res = await targetEnvApi.prepare(payload)
    prepareSteps.value = res.data.steps || []
    prepareOk.value = res.data.status === 'success'
    prepareMessage.value = res.data.message || (prepareOk.value ? '准备完成' : '准备失败')
    const resolved = res.data.resolved || {}
    if (resolved.database) local.database.name = resolved.database
    if (resolved.schema) local.schema.name = resolved.schema
    emit('prepared', resolved)
    emitConfig()
  } catch (err: any) {
    prepareOk.value = false
    prepareMessage.value = err?.response?.data?.message || '准备环境失败'
  } finally {
    preparing.value = false
  }
}

watch(() => props.postgresConnection, (id) => {
  if (id) refreshLists(id)
}, { immediate: true })

/** 暴露当前有效目标库名和 Schema 名 */
const getResolvedTarget = () => ({
  postgres_database: local.database.mode === 'skip'
    ? undefined
    : local.database.name,
  target_schema: local.schema.name || 'public',
})

defineExpose({ getResolvedTarget, handlePrepare })
</script>

<style scoped>
.resource-block {
  background: var(--bs-light, #f8f9fa);
}
</style>

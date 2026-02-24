<template>
  <div class="create-task-view">
    <div class="page-header mb-4">
      <h1>
        <i class="bi bi-plus-circle me-2"></i>
        创建迁移任务
      </h1>
      <p class="text-muted mb-0">配置并创建新的数据库迁移任务</p>
    </div>
    
    <div class="row">
      <div class="col-lg-8">
        <div class="card">
          <div class="card-body">
            <form @submit.prevent="handleSubmit">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">
                    <i class="bi bi-type me-1"></i>
                    任务名称
                  </label>
                  <input v-model="form.name" type="text" class="form-control-sm" required placeholder="输入任务名称">
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">
                    <i class="bi bi-tag me-1"></i>
                    任务类型
                  </label>
                  <select v-model="form.task_type" class="form-select-sm" required>
                    <option value="table">表</option>
                    <option value="materialized_view">物化视图</option>
                    <option value="view">视图</option>
                    <option value="routine">例程</option>
                    <option value="all_tables">所有表</option>
                    <option value="view_to_table">视图数据迁移到表</option>
                    <option value="view_to_sqlite">视图数据迁移到SQLite</option>
                  </select>
                </div>
              </div>
              
              <hr class="my-4">
              
              <h5 class="mb-3">
                <i class="bi bi-database me-1"></i>
                源数据库配置
              </h5>
              
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">Oracle连接</label>
                  <select v-model="form.oracle_connection" class="form-select-sm" required @change="loadSchemas">
                    <option value="">请选择</option>
                    <option v-for="conn in oracleConnections" :key="conn.id" :value="conn.id">
                      {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
                    </option>
                  </select>
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">源Schema</label>
                  <select v-model="form.source_schema" class="form-select-sm" required>
                    <option value="">请选择</option>
                    <option v-for="schema in schemas" :key="schema" :value="schema">{{ schema }}</option>
                  </select>
                </div>
              </div>
              
              <div class="row g-3 mt-3">
                <div class="col-md-12">
                  <label class="form-label">源对象</label>
                  <div class="source-objects-container">
                    <div class="source-objects-controls mb-2">
                      <button type="button" class="btn btn-sm btn-outline-primary me-2" @click="loadSourceObjects" :disabled="!form.oracle_connection || !form.source_schema">
                        <i class="bi bi-arrow-clockwise me-1"></i>
                        刷新对象列表
                      </button>
                      <button type="button" class="btn btn-sm btn-outline-secondary me-2" @click="selectAllObjects" :disabled="filteredObjects.length === 0">
                        <i class="bi bi-check-all me-1"></i>
                        全选
                      </button>
                      <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearAllObjects" :disabled="selectedSourceObjects.length === 0">
                        <i class="bi bi-x-lg me-1"></i>
                        清空
                      </button>
                      <span class="selected-count text-muted ms-3">
                        已选择: <strong>{{ selectedSourceObjects.length }}</strong> / {{ filteredObjects.length }}
                      </span>
                    </div>
                    <div class="search-box mb-2">
                      <input v-model="searchTerm" type="text" class="form-control-sm" placeholder="搜索对象名称..." :disabled="sourceObjects.length === 0">
                    </div>
                    <div v-if="loadingObjects" class="text-center py-3">
                      <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                      </div>
                      <span class="ms-2 text-muted">加载对象列表中...</span>
                    </div>
                    <div v-else-if="sourceObjects.length === 0 && form.oracle_connection && form.source_schema" class="text-center py-3 text-muted">
                      <i class="bi bi-inbox mb-2"></i>
                      <p class="mb-0">点击"刷新对象列表"按钮加载可用对象</p>
                    </div>
                    <div v-else-if="filteredObjects.length > 0" class="source-objects-list">
                      <div class="form-check" v-for="obj in filteredObjects" :key="obj">
                        <input class="form-check-input" type="checkbox" :id="'obj-' + obj" :value="obj" v-model="selectedSourceObjects">
                        <label class="form-check-label" :for="'obj-' + obj">
                          {{ obj }}
                          <span v-if="sourceObjectTypes[obj]" class="badge bg-secondary ms-1">{{ sourceObjectTypes[obj] }}</span>
                        </label>
                      </div>
                    </div>
                    <div v-else-if="sourceObjects.length > 0 && filteredObjects.length === 0" class="text-center py-3 text-muted">
                      <p class="mb-0">没有找到匹配的对象</p>
                    </div>
                    <div v-else class="text-center py-3 text-muted">
                      <p class="mb-0">请先选择Oracle连接和源Schema</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <hr class="my-4">
              
              <h5 class="mb-3">
                <i class="bi bi-server me-1"></i>
                目标数据库配置
              </h5>
              
              <template v-if="form.task_type !== 'view_to_sqlite'">
                <div class="row g-3">
                  <div class="col-md-12">
                    <label class="form-label">第一步：PolarDB/PostgreSQL 连接</label>
                    <select v-model="form.postgres_connection" class="form-select-sm" :required="form.task_type !== 'view_to_sqlite'" @change="onPostgresConnectionChange">
                      <option value="">请选择数据库链接</option>
                      <option v-for="conn in postgresConnections" :key="conn.id" :value="conn.id">
                        {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
                      </option>
                    </select>
                  </div>
                  <div class="col-md-12">
                    <label class="form-label">第二步：目标数据库</label>
                    <select v-model="form.postgres_database" class="form-select-sm" :disabled="!form.postgres_connection || pgDatabases.length === 0" @change="loadPgSchemas">
                      <option value="">请先选择连接，再选择数据库</option>
                      <option v-for="db in pgDatabases" :key="db" :value="db">{{ db }}</option>
                    </select>
                  </div>
                  <div class="col-md-12">
                    <label class="form-label">第三步：目标 Schema</label>
                    <select v-model="form.target_schema" class="form-select-sm" :disabled="!form.postgres_database">
                      <option value="">请先选择数据库，再选择 Schema</option>
                      <option value="public">public (默认)</option>
                      <option v-for="schema in pgSchemas" :key="schema" :value="schema">{{ schema }}</option>
                    </select>
                  </div>
                </div>
                
                <div class="row g-3 mt-3">
                  <div class="col-md-6">
                    <label class="form-label">目标对象名称</label>
                    <input v-model="form.target_object" type="text" class="form-control-sm" placeholder="可选">
                  </div>
                  
                  <div class="col-md-6">
                    <label class="form-label">字段过滤</label>
                    <textarea v-model="form.selected_fields" class="form-control-sm" rows="1"
                              placeholder="逗号或换行分隔的字段名"></textarea>
                  </div>
                </div>
              </template>
              
              <hr class="my-4">
              
              <h5 class="mb-3">
                <i class="bi bi-gear me-1"></i>
                高级配置
              </h5>
              
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">标识符大小写策略</label>
                  <select v-model="form.identifier_case" class="form-select-sm">
                    <option value="lower">全部小写</option>
                    <option value="upper">全部大写</option>
                    <option value="preserve">保持原样</option>
                  </select>
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">冲突处理策略</label>
                  <select v-model="form.conflict_strategy" class="form-select-sm">
                    <option value="error">遇到冲突时报错</option>
                    <option value="replace">删除并替换已存在对象</option>
                    <option value="skip">跳过已存在对象</option>
                    <option value="append">追加数据（仅适用于表）</option>
                    <option value="truncate">清空表并重新加载数据</option>
                  </select>
                </div>
              </div>
              
              <div class="form-check form-switch mt-3">
                <input v-model="form.is_batch" type="checkbox" class="form-check-input" id="isBatch">
                <label class="form-check-label" for="isBatch">批量迁移</label>
              </div>
              
              <div v-if="form.task_type === 'view_to_sqlite'" class="row g-3 mt-3">
                <div class="col-12">
                  <p class="text-muted small mb-2">可指定任意目录与文件名；若文件不存在将自动创建新 SQLite 数据库。</p>
                </div>
                <div class="col-md-6">
                  <label class="form-label">SQLite目录</label>
                  <div class="d-flex gap-1">
                    <input v-model="form.sqlite_directory" type="text" class="form-control-sm flex-grow-1"
                           placeholder="SQLite 文件保存目录" :required="form.task_type === 'view_to_sqlite'">
                    <button type="button" class="btn btn-sm btn-outline-secondary" @click="openBrowseDirectories" title="浏览目录">
                      <i class="bi bi-folder2-open"></i> 浏览
                    </button>
                  </div>
                </div>
                <div class="col-md-6">
                  <label class="form-label">SQLite文件名</label>
                  <input v-model="form.sqlite_file_name" type="text" class="form-control-sm"
                         placeholder="如 mydb.sqlite3" :required="form.task_type === 'view_to_sqlite'">
                </div>
              </div>
              
              <hr class="my-4">
              
              <div class="d-flex gap-2">
                <button type="submit" class="btn btn-sm btn-primary flex-grow-1" :disabled="loading">
                  <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                  <i v-if="!loading" class="bi bi-rocket-takeoff me-2"></i>
                  {{ loading ? '创建中...' : '创建任务' }}
                </button>
                <router-link to="/tasks" class="btn btn-sm btn-outline-secondary">取消</router-link>
              </div>
            </form>
          </div>
        </div>
      </div>
      
      <div class="col-lg-4">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <i class="bi bi-info-circle me-1"></i>
              使用提示
            </h5>
          </div>
          <div class="card-body">
            <ul class="list-unstyled">
              <li class="mb-3">
                <strong class="d-block mb-1">任务类型说明</strong>
                <p class="text-muted small mb-0">选择合适的迁移类型，不同类型支持不同的对象迁移。</p>
              </li>
              <li class="mb-3">
                <strong class="d-block mb-1">连接配置</strong>
                <p class="text-muted small mb-0">确保源数据库和目标数据库连接配置正确且可访问。</p>
              </li>
              <li class="mb-3">
                <strong class="d-block mb-1">冲突处理</strong>
                <p class="text-muted small mb-0">根据需求选择合适的冲突处理策略，避免数据丢失。</p>
              </li>
              <li class="mb-0">
                <strong class="d-block mb-1">批量迁移</strong>
                <p class="text-muted small mb-0">批量迁移可以提高效率，但需要确保所有对象配置正确。</p>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- 目录浏览弹窗 -->
    <div v-if="showBrowseModal" class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">选择 SQLite 保存目录</h5>
            <button type="button" class="btn-close" @click="showBrowseModal = false"></button>
          </div>
          <div class="modal-body">
            <p class="text-muted small mb-2">当前路径: <code>{{ browseCurrentPath }}</code></p>
            <div v-if="browseLoading" class="text-center py-3">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </div>
            <ul v-else class="list-group list-group-flush">
              <li v-for="dir in browseDirectoriesList" :key="dir.path"
                  class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                  @click="navigateBrowseDir(dir)">
                <span><i class="bi bi-folder2 me-2"></i>{{ dir.name }}</span>
                <i v-if="!dir.is_parent" class="bi bi-chevron-right"></i>
              </li>
              <li v-if="browseDirectoriesList.length === 0" class="list-group-item text-muted">此目录下无子目录</li>
            </ul>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showBrowseModal = false">取消</button>
            <button type="button" class="btn btn-primary" @click="confirmBrowsePath">选择此目录</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { oracleConnectionApi, postgresConnectionApi, databaseApi, migrationTaskApi } from '@/api'
import type { MigrationTask } from '@/api'

const router = useRouter()
const loading = ref(false)
const oracleConnections = ref<any[]>([])
const postgresConnections = ref<any[]>([])
const pgDatabases = ref<string[]>([])
const schemas = ref<string[]>([])
const pgSchemas = ref<string[]>([])
const sourceObjects = ref<string[]>([])
const sourceObjectTypes = ref<Record<string, string>>({})
const selectedSourceObjects = ref<string[]>([])
const loadingObjects = ref(false)
const searchTerm = ref('')
const showBrowseModal = ref(false)
const browseCurrentPath = ref('')
const browseDirectoriesList = ref<{ name: string; path: string; is_parent: boolean }[]>([])
const browseLoading = ref(false)

const filteredObjects = computed(() => {
  if (!searchTerm.value) {
    return sourceObjects.value
  }
  
  const term = searchTerm.value.toLowerCase()
  return sourceObjects.value.filter(obj => 
    obj.toLowerCase().includes(term)
  )
})

const form = ref<MigrationTask>({
  name: '',
  task_type: 'table',
  oracle_connection: 0,
  postgres_connection: 0,
  postgres_database: '',
  source_schema: '',
  target_schema: '',
  target_object: '',
  source_object: '',
  source_objects: '',
  selected_fields: '',
  identifier_case: 'lower',
  is_batch: false,
  conflict_strategy: 'error',
  status: 'pending',
  cancel_requested: false,
  progress: 0,
})

const loadConnections = async () => {
  try {
    const [oracleRes, postgresRes] = await Promise.all([
      oracleConnectionApi.list(),
      postgresConnectionApi.list(),
    ])
    oracleConnections.value = oracleRes.data.results || oracleRes.data
    postgresConnections.value = postgresRes.data.results || postgresRes.data
  } catch (error) {
    console.error('Failed to load connections:', error)
  }
}

const loadSchemas = async () => {
  if (!form.value.oracle_connection) return
  
  try {
    const res = await databaseApi.getOracleSchemas({
      connection_id: form.value.oracle_connection,
    })
    schemas.value = res.data.schemas || []
  } catch (error) {
    console.error('Failed to load schemas:', error)
  }
}

// 选择 PolarDB 连接后：加载该连接下的数据库列表
const onPostgresConnectionChange = async () => {
  pgDatabases.value = []
  form.value.postgres_database = ''
  pgSchemas.value = []
  form.value.target_schema = ''
  if (!form.value.postgres_connection) return
  await loadPgDatabases()
}

// 加载 PolarDB 连接下的数据库列表
const loadPgDatabases = async () => {
  if (!form.value.postgres_connection) return
  try {
    const res = await databaseApi.getPostgresDatabases({
      connection_id: form.value.postgres_connection,
    })
    pgDatabases.value = res.data.databases || []
    const conn = postgresConnections.value.find((c: any) => c.id === form.value.postgres_connection)
    if (conn?.database && pgDatabases.value.includes(conn.database)) {
      form.value.postgres_database = conn.database
      await loadPgSchemas()
    }
  } catch (error) {
    console.error('Failed to load PostgreSQL databases:', error)
    pgDatabases.value = []
  }
}

// 根据选中的连接与目标数据库加载 Schema 列表
const loadPgSchemas = async () => {
  if (!form.value.postgres_connection) return
  const database = form.value.postgres_database || undefined
  if (!database) {
    pgSchemas.value = []
    return
  }
  try {
    const res = await databaseApi.getPgSchemas({
      connection_id: form.value.postgres_connection,
      database,
    })
    pgSchemas.value = res.data.schemas || []
  } catch (error) {
    console.error('Failed to load PostgreSQL schemas:', error)
    pgSchemas.value = []
  }
}

const loadSourceObjects = async () => {
  if (!form.value.oracle_connection || !form.value.source_schema) return
  
  loadingObjects.value = true
  try {
    const object_type = form.value.task_type === 'view_to_sqlite' ? 'view_to_sqlite' :
                       form.value.task_type === 'table' ? 'TABLE' :
                       form.value.task_type === 'view' ? 'VIEW' :
                       form.value.task_type === 'materialized_view' ? 'MATERIALIZED_VIEW' :
                       form.value.task_type === 'view_to_table' ? 'VIEW_TO_TABLE' : 'TABLE'
    
    const res = await databaseApi.getDatabaseObjects({
      connection_id: form.value.oracle_connection,
      schema: form.value.source_schema,
      object_type: object_type,
    })
    const raw = res.data.objects || []
    sourceObjects.value = raw.map((o: string | { name: string; object_type?: string }) =>
      typeof o === 'string' ? o : o.name
    )
    sourceObjectTypes.value = {}
    if (form.value.task_type === 'view_to_sqlite' && raw.length > 0 && typeof raw[0] === 'object' && raw[0] !== null && 'object_type' in raw[0]) {
      raw.forEach((o: { name: string; object_type?: string }) => {
        if (o && typeof o === 'object' && o.name) sourceObjectTypes.value[o.name] = o.object_type || ''
      })
    }
  } catch (error) {
    console.error('Failed to load source objects:', error)
    sourceObjects.value = []
    sourceObjectTypes.value = {}
  } finally {
    loadingObjects.value = false
  }
}

const selectAllObjects = () => {
  selectedSourceObjects.value = [...filteredObjects.value]
}

const clearAllObjects = () => {
  selectedSourceObjects.value = []
}

const openBrowseDirectories = async () => {
  showBrowseModal.value = true
  browseCurrentPath.value = form.value.sqlite_directory?.trim() || ''
  await loadBrowseDirectories(browseCurrentPath.value || undefined)
}

const loadBrowseDirectories = async (path?: string) => {
  browseLoading.value = true
  try {
    const res = await databaseApi.browseDirectories(path ? { path } : {})
    if (res.data.status === 'success') {
      browseCurrentPath.value = res.data.current_path || ''
      browseDirectoriesList.value = res.data.directories || []
    }
  } catch (e) {
    console.error('Browse directories failed:', e)
    browseDirectoriesList.value = []
  } finally {
    browseLoading.value = false
  }
}

const navigateBrowseDir = async (dir: { path: string; is_parent: boolean }) => {
  browseCurrentPath.value = dir.path
  await loadBrowseDirectories(dir.path)
}

const confirmBrowsePath = () => {
  form.value.sqlite_directory = browseCurrentPath.value
  showBrowseModal.value = false
}

const handleSubmit = async () => {
  if (form.value.task_type === 'view_to_sqlite') {
    if (!form.value.sqlite_directory?.trim()) {
      alert('请填写 SQLite 目录或通过「浏览」选择')
      return
    }
    if (!form.value.sqlite_file_name?.trim()) {
      alert('请填写 SQLite 文件名')
      return
    }
    if (selectedSourceObjects.value.length === 0) {
      alert('请至少选择一个表或视图')
      return
    }
  } else {
    if (!form.value.postgres_connection) {
      alert('请选择 PolarDB/PostgreSQL 连接')
      return
    }
    if (!form.value.postgres_database?.trim()) {
      alert('请选择目标数据库')
      return
    }
    if (!form.value.target_schema?.trim()) {
      alert('请选择目标 Schema')
      return
    }
  }
  loading.value = true
  try {
    const taskData = { ...form.value }
    
    if (selectedSourceObjects.value.length > 0) {
      taskData.source_objects = selectedSourceObjects.value.join(',')
      taskData.source_object = ''
    }
    
    const res = await migrationTaskApi.createValidated(taskData)
    
    if (res.data.status === 'success') {
      router.push('/tasks')
    } else {
      alert('创建任务失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('Failed to create task:', error)
    alert('创建任务失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConnections()
})

watch(() => form.value.oracle_connection, () => {
  schemas.value = []
  form.value.source_schema = ''
  sourceObjects.value = []
  sourceObjectTypes.value = {}
  selectedSourceObjects.value = []
})

watch(() => form.value.source_schema, () => {
  sourceObjects.value = []
  sourceObjectTypes.value = {}
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    loadSourceObjects()
  }
})

watch(() => form.value.task_type, () => {
  sourceObjects.value = []
  sourceObjectTypes.value = {}
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    loadSourceObjects()
  }
})

// 目标数据库变化时重新加载 Schema
watch(() => form.value.postgres_database, () => {
  if (form.value.postgres_connection && form.value.postgres_database) {
    loadPgSchemas()
  } else {
    pgSchemas.value = []
  }
})
</script>

<style scoped>
.create-task-view {
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

.page-header .text-muted {
  font-size: 1rem;
}

.form-label {
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.5rem;
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid var(--input-border);
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
  font-size: 0.95rem;
}

.form-control:focus,
.form-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem var(--shadow);
}

.form-control::placeholder {
  color: var(--text-muted);
}

hr {
  border-color: var(--border);
  margin: 2rem 0;
}

h5 {
  font-weight: 600;
  color: var(--text);
  margin-bottom: 1rem;
}

.form-check-input:checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

.form-check-label {
  font-weight: 500;
  color: #4a5568;
}

.card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 10px 40px var(--shadow);
  overflow: hidden;
}

.card-header {
  background: var(--gradient);
  color: white;
  font-weight: 600;
  border: none;
  padding: 1rem 1.5rem;
}

.card-body {
  padding: 1.5rem;
}

.list-unstyled li {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}

.list-unstyled li:last-child {
  border-bottom: none;
}

.list-unstyled strong {
  color: var(--primary);
  font-weight: 600;
}

.list-unstyled p {
  line-height: 1.6;
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
}

.source-objects-container {
  border: 2px solid var(--input-border);
  border-radius: 0.5rem;
  padding: 1rem;
  background-color: var(--background);
}

.source-objects-controls {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.selected-count {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-left: auto;
}

.search-box input {
  border-radius: 0.375rem;
  border: 1px solid var(--input-border);
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.search-box input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem var(--shadow);
}

.source-objects-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 0.5rem;
  background-color: var(--surface);
  border-radius: 0.375rem;
  border: 1px solid var(--border);
  padding: 30px;
}

.source-objects-list .form-check {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid var(--divider);
  margin-bottom: 0;
  transition: background-color 0.2s ease;
}

.source-objects-list .form-check:hover {
  background-color: var(--background);
}

.source-objects-list .form-check:last-child {
  border-bottom: none;
}

.source-objects-list .form-check-input {
  margin-top: 0.25rem;
  width: 1.125rem;
  height: 1.125rem;
  cursor: pointer;
}

.source-objects-list .form-check-label {
  margin-left: 0.75rem;
  cursor: pointer;
  color: #4a5568;
  font-size: 0.875rem;
  user-select: none;
  flex: 1;
  word-break: break-all;
}

.source-objects-list .form-check-label:hover {
  color: #667eea;
}

.source-objects-list .form-check-input:checked + .form-check-label {
  color: #667eea;
  font-weight: 500;
}

.source-objects-list::-webkit-scrollbar {
  width: 8px;
}

.source-objects-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 4px;
}

.source-objects-list::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 4px;
}

.source-objects-list::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}
</style>
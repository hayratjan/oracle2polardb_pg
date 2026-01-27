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
                        <label class="form-check-label" :for="'obj-' + obj">{{ obj }}</label>
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
              
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">PostgreSQL连接</label>
                  <select v-model="form.postgres_connection" class="form-select-sm" required @change="loadPgSchemas">
                    <option value="">请选择</option>
                    <option v-for="conn in postgresConnections" :key="conn.id" :value="conn.id">
                      {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
                    </option>
                  </select>
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">目标Schema</label>
                  <select v-model="form.target_schema" class="form-select-sm">
                    <option value="">请选择</option>
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
              
              <div v-if="form.task_type.includes('sqlite')" class="row g-3 mt-3">
                <div class="col-md-6">
                  <label class="form-label">SQLite目录</label>
                  <input v-model="form.sqlite_directory" type="text" class="form-control-sm" 
                         placeholder="SQLite文件保存目录">
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">SQLite文件名</label>
                  <input v-model="form.sqlite_file_name" type="text" class="form-control-sm" 
                         placeholder="SQLite文件名">
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
const schemas = ref<string[]>([])
const pgSchemas = ref<string[]>([])
const sourceObjects = ref<string[]>([])
const selectedSourceObjects = ref<string[]>([])
const loadingObjects = ref(false)
const searchTerm = ref('')

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

const loadPgSchemas = async () => {
  if (!form.value.postgres_connection) return
  
  try {
    const res = await databaseApi.getPgSchemas({
      connection_id: form.value.postgres_connection,
    })
    pgSchemas.value = res.data.schemas || []
  } catch (error) {
    console.error('Failed to load PostgreSQL schemas:', error)
  }
}

const loadSourceObjects = async () => {
  if (!form.value.oracle_connection || !form.value.source_schema) return
  
  loadingObjects.value = true
  try {
    const object_type = form.value.task_type === 'table' ? 'TABLE' : 
                       form.value.task_type === 'view' ? 'VIEW' : 
                       form.value.task_type === 'materialized_view' ? 'MATERIALIZED_VIEW' : 'TABLE'
    
    console.log('Loading source objects with params:', {
      connection_id: form.value.oracle_connection,
      schema: form.value.source_schema,
      object_type: object_type,
    })
    
    const res = await databaseApi.getDatabaseObjects({
      connection_id: form.value.oracle_connection,
      schema: form.value.source_schema,
      object_type: object_type,
    })
    sourceObjects.value = res.data.objects || []
    console.log('Loaded source objects:', sourceObjects.value.length, 'items')
  } catch (error) {
    console.error('Failed to load source objects:', error)
    sourceObjects.value = []
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

const handleSubmit = async () => {
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
  selectedSourceObjects.value = []
})

watch(() => form.value.source_schema, () => {
  sourceObjects.value = []
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    loadSourceObjects()
  }
})

watch(() => form.value.task_type, () => {
  sourceObjects.value = []
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    loadSourceObjects()
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
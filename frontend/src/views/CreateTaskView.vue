<template>
  <div class="create-task-view">
    <h1>创建迁移任务</h1>
    
    <div class="card">
      <div class="card-body">
        <form @submit.prevent="handleSubmit">
          <div class="mb-3">
            <label class="form-label">任务名称</label>
            <input v-model="form.name" type="text" class="form-control" required>
          </div>
          
          <div class="mb-3">
            <label class="form-label">任务类型</label>
            <select v-model="form.task_type" class="form-select" required>
              <option value="table">表</option>
              <option value="materialized_view">物化视图</option>
              <option value="view">视图</option>
              <option value="routine">例程</option>
              <option value="all_tables">所有表</option>
              <option value="view_to_table">视图数据迁移到表</option>
              <option value="view_to_sqlite">视图数据迁移到SQLite</option>
            </select>
          </div>
          
          <div class="mb-3">
            <label class="form-label">Oracle连接</label>
            <select v-model="form.oracle_connection" class="form-select" required @change="loadSchemas">
              <option value="">请选择</option>
              <option v-for="conn in oracleConnections" :key="conn.id" :value="conn.id">
                {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
              </option>
            </select>
          </div>
          
          <div class="mb-3">
            <label class="form-label">源Schema</label>
            <select v-model="form.source_schema" class="form-select" required>
              <option value="">请选择</option>
              <option v-for="schema in schemas" :key="schema" :value="schema">{{ schema }}</option>
            </select>
          </div>
          
          <div class="mb-3">
            <label class="form-label">源对象</label>
            <input v-model="form.source_object" type="text" class="form-control" 
                   placeholder="单个对象名称">
          </div>
          
          <div class="mb-3">
            <label class="form-label">多个源对象（逗号分隔）</label>
            <textarea v-model="form.source_objects" class="form-control" rows="3"
                      placeholder="多个对象名称，用逗号分隔"></textarea>
          </div>
          
          <div class="mb-3">
            <label class="form-label">PostgreSQL连接</label>
            <select v-model="form.postgres_connection" class="form-select" required>
              <option value="">请选择</option>
              <option v-for="conn in postgresConnections" :key="conn.id" :value="conn.id">
                {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
              </option>
            </select>
          </div>
          
          <div class="mb-3">
            <label class="form-label">目标Schema</label>
            <input v-model="form.target_schema" type="text" class="form-control" placeholder="默认为public">
          </div>
          
          <div class="mb-3">
            <label class="form-label">目标对象名称</label>
            <input v-model="form.target_object" type="text" class="form-control" placeholder="可选">
          </div>
          
          <div class="mb-3">
            <label class="form-label">字段过滤（逗号或换行分隔）</label>
            <textarea v-model="form.selected_fields" class="form-control" rows="3"
                      placeholder="可选，逗号或换行分隔的字段名"></textarea>
          </div>
          
          <div class="mb-3">
            <label class="form-label">标识符大小写策略</label>
            <select v-model="form.identifier_case" class="form-select">
              <option value="lower">全部小写</option>
              <option value="upper">全部大写</option>
              <option value="preserve">保持原样</option>
            </select>
          </div>
          
          <div class="mb-3">
            <label class="form-label">冲突处理策略</label>
            <select v-model="form.conflict_strategy" class="form-select">
              <option value="error">遇到冲突时报错</option>
              <option value="replace">删除并替换已存在对象</option>
              <option value="skip">跳过已存在对象</option>
              <option value="append">追加数据（仅适用于表）</option>
              <option value="truncate">清空表并重新加载数据</option>
            </select>
          </div>
          
          <div class="mb-3 form-check">
            <input v-model="form.is_batch" type="checkbox" class="form-check-input" id="isBatch">
            <label class="form-check-label" for="isBatch">批量迁移</label>
          </div>
          
          <div class="mb-3">
            <label class="form-label">SQLite目录（仅SQLite迁移）</label>
            <input v-model="form.sqlite_directory" type="text" class="form-control" 
                   placeholder="SQLite文件保存目录">
          </div>
          
          <div class="mb-3">
            <label class="form-label">SQLite文件名（仅SQLite迁移）</label>
            <input v-model="form.sqlite_file_name" type="text" class="form-control" 
                   placeholder="SQLite文件名">
          </div>
          
          <button type="submit" class="btn btn-primary" :disabled="loading">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            {{ loading ? '创建中...' : '创建任务' }}
          </button>
          
          <router-link to="/tasks" class="btn btn-secondary ms-2">取消</router-link>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { oracleConnectionApi, postgresConnectionApi, databaseApi } from '@/api'
import type { MigrationTask } from '@/api'

const router = useRouter()
const loading = ref(false)
const oracleConnections = ref<any[]>([])
const postgresConnections = ref<any[]>([])
const schemas = ref<string[]>([])

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

const handleSubmit = async () => {
  loading.value = true
  try {
    const res = await migrationTaskApi.createValidated(form.value)
    
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
</script>
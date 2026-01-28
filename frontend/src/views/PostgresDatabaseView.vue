<template>
  <div class="postgres-database-view">
    <div v-if="alertMessage.show" :class="['alert', `alert-${alertMessage.type}`, 'alert-dismissible', 'fade', 'show']" role="alert">
      <div class="d-flex align-items-center">
        <i :class="getAlertIcon(alertMessage.type)" class="me-2"></i>
        <div class="flex-grow-1">{{ alertMessage.message }}</div>
        <button type="button" class="btn-close" @click="alertMessage.show = false"></button>
      </div>
    </div>
    
    <div class="page-header mb-4">
      <h1>
        <i class="bi bi-server me-2"></i>
        PostgreSQL数据库管理
      </h1>
      <p class="text-muted mb-0">管理PostgreSQL数据库连接和查看数据库信息</p>
    </div>
    
    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <i class="bi bi-link-45deg me-1"></i>
              PostgreSQL连接
            </h5>
            <button @click="showCreateModal = true" class="btn btn-primary btn-sm">
              <i class="bi bi-plus-lg"></i>
              添加连接
            </button>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载连接列表...</p>
            </div>
            <div v-else-if="connections.length > 0">
              <div class="list-group list-group-flush">
                <div v-for="conn in connections" :key="conn.id" class="list-group-item">
                  <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                      <h6 class="mb-1">{{ conn.name }}</h6>
                      <div class="text-muted small">
                        <i class="bi bi-geo-alt me-1"></i>
                        {{ conn.host }}:{{ conn.port }}
                        <span class="mx-2">/</span>
                        <i class="bi bi-collection me-1"></i>
                        {{ conn.database }}
                      </div>
                      <span class="badge mt-2" :class="getStatusBadgeClass(conn.status)">
                        {{ getStatusText(conn.status) }}
                      </span>
                    </div>
                    <div v-if="conn.id" class="btn-group">
                      <button @click="testConnection(conn.id)" class="btn btn-outline-info btn-xs" title="测试连接">
                        <i class="bi bi-check-lg"></i>
                      </button>
                      <button @click="openEditModal(conn)" class="btn btn-outline-success btn-xs" title="编辑连接">
                        <i class="bi bi-pencil"></i>
                      </button>
                      <button @click="deleteConnection(conn.id)" class="btn btn-outline-danger btn-xs" title="删除连接">
                        <i class="bi bi-trash"></i>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-5 empty-state">
              <i class="bi bi-server text-muted mb-3" style="font-size: 64px;"></i>
              <p class="text-muted mb-3">暂无连接</p>
              <button @click="showCreateModal = true" class="btn btn-sm btn-primary">
                <i class="bi bi-plus-lg me-1"></i>
                添加第一个连接
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <i class="bi bi-info-circle me-1"></i>
              数据库信息
            </h5>
          </div>
          <div class="card-body">
            <div v-if="selectedConnection">
              <div class="mb-4">
                <label class="form-label">选择连接</label>
                <select v-model="selectedConnection" class="form-select-sm" @change="loadDatabaseInfo">
                  <option value="">请选择</option>
                  <option v-for="conn in connections" :key="conn.id" :value="conn.id">
                    {{ conn.name }}
                  </option>
                </select>
              </div>
              
              <div v-if="databaseInfo">
                <h6 class="mb-3">
                  <i class="bi bi-diagram-3 me-1"></i>
                  Schemas
                </h6>
                <div class="list-group list-group-flush mb-4">
                  <div v-for="schema in databaseInfo.schemas" :key="schema" class="list-group-item d-flex align-items-center">
                    <i class="bi bi-folder text-primary me-2" style="font-size: 14px;"></i>
                    {{ schema }}
                  </div>
                </div>
                
                <h6 class="mb-3">
                  <i class="bi bi-database me-1"></i>
                  Databases
                </h6>
                <div class="list-group list-group-flush">
                  <div v-for="db in databaseInfo.databases" :key="db" class="list-group-item d-flex align-items-center">
                    <i class="bi bi-hdd text-secondary me-2" style="font-size: 14px;"></i>
                    {{ db }}
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-5 text-muted">
              <i class="bi bi-server mb-3" style="font-size: 48px;"></i>
              <p>请先选择一个连接</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="modal" v-if="showCreateModal" tabindex="-1" style="display: block; background: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="bi bi-plus-circle me-2"></i>
              添加PostgreSQL连接
            </h5>
            <button type="button" class="btn-close" @click="showCreateModal = false"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="createConnection">
              <div class="mb-3">
                <label class="form-label">连接名称</label>
                <input v-model="newConnection.name" type="text" class="form-control-sm" required placeholder="输入连接名称">
              </div>
              <div class="mb-3">
                <label class="form-label">主机</label>
                <input v-model="newConnection.host" type="text" class="form-control-sm" required placeholder="例如: localhost">
              </div>
              <div class="mb-3">
                <label class="form-label">端口</label>
                <input v-model.number="newConnection.port" type="number" class="form-control-sm" required placeholder="默认: 5432">
              </div>
              <div class="mb-3">
                <label class="form-label">数据库名</label>
                <input v-model="newConnection.database" type="text" class="form-control-sm" required placeholder="例如: postgres">
              </div>
              <div class="mb-3">
                <label class="form-label">用户名</label>
                <input v-model="newConnection.username" type="text" class="form-control-sm" required placeholder="数据库用户名">
              </div>
              <div class="mb-3">
                <label class="form-label">密码</label>
                <input v-model="newConnection.password" type="password" class="form-control-sm" required placeholder="数据库密码">
              </div>
              <button type="submit" class="btn btn-sm btn-primary w-100" :disabled="creating">
                <span v-if="creating" class="spinner-border spinner-border-sm me-2"></span>
                {{ creating ? '创建中...' : '创建连接' }}
              </button>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="showCreateModal = false">取消</button>
          </div>
        </div>
      </div>
    </div>
    
    <div class="modal" v-if="showEditModal" tabindex="-1" style="display: block; background: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="bi bi-pencil-square me-2"></i>
              编辑PostgreSQL连接
            </h5>
            <button type="button" class="btn-close" @click="showEditModal = false"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="updateConnection">
              <input type="hidden" v-model="editedConnection.id">
              <div class="mb-3">
                <label class="form-label">连接名称</label>
                <input v-model="editedConnection.name" type="text" class="form-control-sm" required placeholder="输入连接名称">
              </div>
              <div class="mb-3">
                <label class="form-label">主机</label>
                <input v-model="editedConnection.host" type="text" class="form-control-sm" required placeholder="例如: localhost">
              </div>
              <div class="mb-3">
                <label class="form-label">端口</label>
                <input v-model.number="editedConnection.port" type="number" class="form-control-sm" required placeholder="默认: 5432">
              </div>
              <div class="mb-3">
                <label class="form-label">数据库名</label>
                <input v-model="editedConnection.database" type="text" class="form-control-sm" required placeholder="例如: postgres">
              </div>
              <div class="mb-3">
                <label class="form-label">用户名</label>
                <input v-model="editedConnection.username" type="text" class="form-control-sm" required placeholder="数据库用户名">
              </div>
              <div class="mb-3">
                <label class="form-label">密码</label>
                <input v-model="editedConnection.password" type="password" class="form-control-sm" placeholder="留空表示不修改密码">
              </div>
              <div class="d-flex gap-2">
                <button type="button" class="btn btn-sm btn-outline-info flex-fill" @click="testEditedConnection" :disabled="testing">
                  <span v-if="testing" class="spinner-border spinner-border-sm me-2"></span>
                  {{ testing ? '测试中...' : '测试连接' }}
                </button>
                <button type="submit" class="btn btn-sm btn-success flex-fill" :disabled="updating">
                  <span v-if="updating" class="spinner-border spinner-border-sm me-2"></span>
                  {{ updating ? '更新中...' : '更新连接' }}
                </button>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="showEditModal = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { postgresConnectionApi, databaseApi } from '@/api'
import type { PostgresConnection } from '@/api'

const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testing = ref(false)
const connections = ref<PostgresConnection[]>([])
const selectedConnection = ref<number | null>(null)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const databaseInfo = ref<any>(null)
const alertMessage = ref<{
  show: boolean
  type: 'success' | 'danger' | 'warning' | 'info'
  message: string
}>({
  show: false,
  type: 'success',
  message: '',
})
const editedConnection = ref<any>({
  id: 0,
  name: '',
  host: '',
  port: 5432,
  database: '',
  username: '',
  password: '',
})

const newConnection = ref<PostgresConnection>({
  name: '',
  host: '',
  port: 5432,
  database: '',
  username: '',
  password: '',
})

const getStatusBadgeClass = (status?: string) => {
  const classes: Record<string, string> = {
    active: 'bg-success',
    inactive: 'bg-danger',
    testing: 'bg-warning',
  }
  return classes[status || ''] || 'bg-secondary'
}

const getStatusText = (status?: string) => {
  const texts: Record<string, string> = {
    active: '正常',
    inactive: '异常',
    testing: '测试中',
  }
  return texts[status || ''] || status
}

const getAlertIcon = (type: string) => {
  const icons: Record<string, string> = {
    success: 'bi bi-check-circle-fill',
    danger: 'bi bi-exclamation-triangle-fill',
    warning: 'bi bi-exclamation-circle-fill',
    info: 'bi bi-info-circle-fill',
  }
  return icons[type] || 'bi bi-info-circle-fill'
}

const loadConnections = async () => {
  loading.value = true
  try {
    const res = await postgresConnectionApi.list()
    connections.value = res.data.results || res.data
  } catch (error) {
    console.error('Failed to load connections:', error)
  } finally {
    loading.value = false
  }
}

const createConnection = async () => {
  creating.value = true
  try {
    await postgresConnectionApi.create(newConnection.value)
    showCreateModal.value = false
    newConnection.value = {
      name: '',
      host: '',
      port: 5432,
      database: '',
      username: '',
      password: '',
    }
    await loadConnections()
    alertMessage.value = {
      show: true,
      type: 'success',
      message: '连接创建成功',
    }
    setTimeout(() => {
      alertMessage.value.show = false
    }, 3000)
  } catch (error) {
    console.error('Failed to create connection:', error)
    alertMessage.value = {
      show: true,
      type: 'danger',
      message: '创建连接失败',
    }
    setTimeout(() => {
      alertMessage.value.show = false
    }, 3000)
  } finally {
    creating.value = false
  }
}

const openEditModal = (conn: PostgresConnection) => {
  editedConnection.value = {
    id: conn.id || 0,
    name: conn.name,
    host: conn.host,
    port: conn.port,
    database: conn.database,
    username: conn.username,
    password: '',
  }
  showEditModal.value = true
}

const updateConnection = async () => {
  if (!editedConnection.value.id) return
  updating.value = true
  try {
    await postgresConnectionApi.edit(editedConnection.value.id, {
      name: editedConnection.value.name,
      host: editedConnection.value.host,
      port: editedConnection.value.port,
      database: editedConnection.value.database,
      username: editedConnection.value.username,
      password: editedConnection.value.password || undefined,
    })
    showEditModal.value = false
    await loadConnections()
    alertMessage.value = {
      show: true,
      type: 'success',
      message: '连接更新成功',
    }
    setTimeout(() => {
      alertMessage.value.show = false
    }, 3000)
  } catch (error) {
    console.error('Failed to update connection:', error)
    alertMessage.value = {
      show: true,
      type: 'danger',
      message: '更新连接失败',
    }
    setTimeout(() => {
      alertMessage.value.show = false
    }, 3000)
  } finally {
    updating.value = false
  }
}

const deleteConnection = async (id: number) => {
  if (!id) return
  if (!confirm('确定要删除此连接吗？')) return
  try {
    await postgresConnectionApi.delete(id)
    await loadConnections()
  } catch (error) {
    console.error('Failed to delete connection:', error)
  }
}

const testConnection = async (id: number) => {
  if (!id) return
  try {
    const res = await postgresConnectionApi.test(id)
    if (res.data.status === 'success') {
      alertMessage.value = {
        show: true,
        type: 'success',
        message: '连接测试成功',
      }
      setTimeout(() => {
        alertMessage.value.show = false
      }, 3000)
    } else {
      alertMessage.value = {
        show: true,
        type: 'danger',
        message: '连接测试失败: ' + res.data.message,
      }
      setTimeout(() => {
        alertMessage.value.show = false
      }, 3000)
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
    alertMessage.value = {
      show: true,
      type: 'danger',
      message: '连接测试失败',
    }
    setTimeout(() => {
      alertMessage.value.show = false
    }, 3000)
  }
}

const testEditedConnection = async () => {
  if (!editedConnection.value.id) return
  testing.value = true
  try {
    const res = await postgresConnectionApi.test(editedConnection.value.id)
    if (res.data.status === 'success') {
      alertMessage.value = {
        show: true,
        type: 'success',
        message: '连接测试成功',
      }
      setTimeout(() => {
        alertMessage.value.show = false
      }, 3000)
    } else {
      alertMessage.value = {
        show: true,
        type: 'danger',
        message: '连接测试失败: ' + res.data.message,
      }
      setTimeout(() => {
        alertMessage.value.show = false
      }, 3000)
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
    alertMessage.value = {
      show: true,
      type: 'danger',
      message: '连接测试失败',
    }
    setTimeout(() => {
      alertMessage.value.show = false
    }, 3000)
  } finally {
    testing.value = false
  }
}

const loadDatabaseInfo = async () => {
  if (!selectedConnection.value) return
  
  try {
    const [schemasRes, databasesRes] = await Promise.all([
      databaseApi.getPgSchemas({ connection_id: selectedConnection.value }),
      databaseApi.getPostgresDatabases({ connection_id: selectedConnection.value }),
    ])
    
    databaseInfo.value = {
      schemas: schemasRes.data.schemas || [],
      databases: databasesRes.data.databases || [],
    }
  } catch (error) {
    console.error('Failed to load database info:', error)
  }
}

onMounted(() => {
  loadConnections()
})
</script>

<style scoped>
.alert {
  margin-bottom: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.alert i {
  font-size: 1.25rem;
}

.alert .btn-close {
  padding: 0.5rem;
}

.postgres-database-view {
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

.card-header h5 {
  display: flex;
  align-items: center;
}

.card-body {
  padding: 1.5rem;
}

.list-group-item {
  border: none;
  border-bottom: 1px solid var(--border);
  transition: all 0.3s ease;
  position: relative;
}

.list-group-item:hover {
  background-color: #f0f7ff;
  border-left: 3px solid #2196f3;
  padding-left: calc(1rem - 3px);
}

.list-group-item:hover h6,
.list-group-item:hover .text-muted,
.list-group-item:hover .badge {
  color: #1a1a1a;
}

.list-group-item:last-child {
  border-bottom: none;
}

.btn-group-sm .btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
}

.empty-state {
  background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
  border-radius: 0.5rem;
}

.spinner-border {
  width: 3rem;
  height: 3rem;
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

.form-label {
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.5rem;
}

.modal-content {
  border-radius: 1rem;
  border: none;
}

.modal-header {
  background: var(--gradient);
  color: white;
  border: none;
}

.modal-title {
  display: flex;
  align-items: center;
}

.btn-close {
  filter: brightness(0) invert(1);
}

h6 {
  font-weight: 600;
  color: var(--text);
}

.text-muted small {
  line-height: 1.6;
}

.badge {
  font-weight: 500;
  padding: 0.35em 0.65em;
}
</style>
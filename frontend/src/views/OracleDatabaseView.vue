<template>
  <div class="oracle-database-view">
    <div class="page-header mb-4">
      <h1>
        <i class="bi bi-database me-2"></i>
        Oracle数据库管理
      </h1>
      <p class="text-muted mb-0">管理Oracle数据库连接和查看数据库信息</p>
    </div>
    
    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <i class="bi bi-link-45deg me-1"></i>
              Oracle连接
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
                        {{ conn.service_name }}
                      </div>
                    </div>
                    <div v-if="conn.id" class="btn-group">
                        <button @click="testConnection(conn.id)" class="btn btn-outline-info btn-xs" title="测试连接">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
                            <path d="M10.97 4.97a.235.235 0 00-.02.022L7.477 9.417 5.384 7.323a.75.75 0 00-1.06 1.06L6.97 11.03a.75.75 0 001.079-.02l3.992-4.99a.75.75 0 00-1.071-1.05z"/>
                          </svg>
                        </button>
                        <button @click="openEditModal(conn)" class="btn btn-outline-success btn-xs" title="编辑连接">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M12.146.146a.5.5 0 01.708 0l3 3a.5.5 0 010 .708l-10 10a.5.5 0 01-.168.11l-5 2a.5.5 0 01-.63-.062l-2-2a.5.5 0 01.366-.437l3-3a.5.5 0 01.708 0l3 3a.5.5 0 01-.708.708L12.146.146z"/>
                            <path d="M11.207 2.5L13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 01.5.5v.5h.5a.5.5 0 01.5.5v.5h.293l6.5-6.5zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 015 12.5V12h-.5a.5.5 0 01-.5-.5V11h-.5a.5.5 0 01-.468-.325z"/>
                          </svg>
                        </button>
                        <button @click="deleteConnection(conn.id)" class="btn btn-outline-danger btn-xs" title="删除连接">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                            <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                          </svg>
                        </button>
                      </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-5 empty-state">
              <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" fill="currentColor" class="text-muted mb-3" viewBox="0 0 16 16">
                <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
              </svg>
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
                    <i class="bi bi-folder me-2 text-primary"></i>
                    {{ schema }}
                  </div>
                </div>
                
                <h6 class="mb-3">
                  <i class="bi bi-people me-1"></i>
                  Users
                </h6>
                <div class="list-group list-group-flush">
                  <div v-for="user in databaseInfo.users" :key="user" class="list-group-item d-flex align-items-center">
                    <i class="bi bi-person me-2 text-secondary"></i>
                    {{ user }}
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-5 text-muted">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="mb-3" viewBox="0 0 16 16">
                <path d="M8 16a2 2 0 002-2H6a2 2 0 002 2zm.995-14.901a1 1 0 10-1.99 0A5.002 5.002 0 003 6c0 1.098-.5 6-2 7h14c-1.5-1-2-5.902-2-7 0-2.42-1.72-4.44-4.005-4.901z"/>
              </svg>
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
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-plus-circle me-2" viewBox="0 0 16 16">
                <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
              </svg>
              添加Oracle连接
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
                <input v-model.number="newConnection.port" type="number" class="form-control-sm" required placeholder="默认: 1521">
              </div>
              <div class="mb-3">
                <label class="form-label">服务名</label>
                <input v-model="newConnection.service_name" type="text" class="form-control-sm" required placeholder="例如: ORCL">
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
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                <path d="M15.502 1.94a.5.5 0 010 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 01.707 0l1.293 1.293zm-1.75 2.456l-2-2L4.939 9.21a.5.5 0 00-.121.196l-.805 2.414a.25.25 0 00.316.316l2.414-.805a.5.5 0 00.196-.12l6.813-6.814z"/>
                <path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 002.5 15h11a1.5 1.5 0 001.5-1.5v-6a.5.5 0 00-1 0v6a.5.5 0 01-.5.5h-11a.5.5 0 01-.5-.5v-11a.5.5 0 01.5-.5H9a.5.5 0 000 1h.5v11a1.5 1.5 0 001.5 1.5v-11z"/>
              </svg>
              编辑Oracle连接
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
                <input v-model.number="editedConnection.port" type="number" class="form-control-sm" required placeholder="默认: 1521">
              </div>
              <div class="mb-3">
                <label class="form-label">服务名</label>
                <input v-model="editedConnection.service_name" type="text" class="form-control-sm" required placeholder="例如: ORCL">
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
import { oracleConnectionApi, databaseApi } from '@/api'
import type { OracleConnection } from '@/api'

const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testing = ref(false)
const connections = ref<OracleConnection[]>([])
const selectedConnection = ref<number | null>(null)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const databaseInfo = ref<any>(null)
const editedConnection = ref<any>({
  id: 0,
  name: '',
  host: '',
  port: 1521,
  service_name: '',
  username: '',
  password: '',
})

const newConnection = ref<OracleConnection>({
  name: '',
  host: '',
  port: 1521,
  service_name: '',
  username: '',
  password: '',
})

const loadConnections = async () => {
  loading.value = true
  try {
    const res = await oracleConnectionApi.list()
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
    await oracleConnectionApi.create(newConnection.value)
    showCreateModal.value = false
    newConnection.value = {
      name: '',
      host: '',
      port: 1521,
      service_name: '',
      username: '',
      password: '',
    }
    await loadConnections()
  } catch (error) {
    console.error('Failed to create connection:', error)
    alert('创建连接失败')
  } finally {
    creating.value = false
  }
}

const openEditModal = (conn: OracleConnection) => {
  editedConnection.value = {
    id: conn.id || 0,
    name: conn.name,
    host: conn.host,
    port: conn.port,
    service_name: conn.service_name,
    username: conn.username,
    password: '',
  }
  showEditModal.value = true
}

const updateConnection = async () => {
  if (!editedConnection.value.id) return
  updating.value = true
  try {
    await oracleConnectionApi.edit(editedConnection.value.id, {
      name: editedConnection.value.name,
      host: editedConnection.value.host,
      port: editedConnection.value.port,
      service_name: editedConnection.value.service_name,
      username: editedConnection.value.username,
      password: editedConnection.value.password || undefined,
    })
    showEditModal.value = false
    await loadConnections()
  } catch (error) {
    console.error('Failed to update connection:', error)
    alert('更新连接失败')
  } finally {
    updating.value = false
  }
}

const testEditedConnection = async () => {
  if (!editedConnection.value.id) return
  testing.value = true
  try {
    const res = await oracleConnectionApi.test(editedConnection.value.id)
    if (res.data.status === 'success') {
      alert('连接测试成功')
    } else {
      alert('连接测试失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
    alert('连接测试失败')
  } finally {
    testing.value = false
  }
}

const deleteConnection = async (id: number) => {
  if (!id) return
  if (!confirm('确定要删除此连接吗？')) return
  try {
    await oracleConnectionApi.delete(id)
    await loadConnections()
  } catch (error) {
    console.error('Failed to delete connection:', error)
  }
}

const testConnection = async (id: number) => {
  if (!id) return
  try {
    const res = await oracleConnectionApi.test(id)
    if (res.data.status === 'success') {
      alert('连接测试成功')
    } else {
      alert('连接测试失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('Failed to test connection:', error)
    alert('连接测试失败')
  }
}

const loadDatabaseInfo = async () => {
  if (!selectedConnection.value) return
  
  try {
    const [schemasRes, usersRes] = await Promise.all([
      databaseApi.getOracleSchemas({ connection_id: selectedConnection.value }),
      databaseApi.getOracleUsers({ connection_id: selectedConnection.value }),
    ])
    
    databaseInfo.value = {
      schemas: schemasRes.data.schemas || [],
      users: usersRes.data.users || [],
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
.oracle-database-view {
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
}

.list-group-item:hover {
  background-color: var(--background);
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
</style>
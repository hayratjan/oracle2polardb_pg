<template>
  <div class="oracle-database-view">
    <div class="page-header mb-4">
      <h1>
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-database me-2" viewBox="0 0 16 16">
          <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
        </svg>
        Oracle数据库管理
      </h1>
      <p class="text-muted mb-0">管理Oracle数据库连接和查看数据库信息</p>
    </div>
    
    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-link-45deg me-1" viewBox="0 0 16 16">
                <path d="M4.715 6.542L3.343 7.914a3 3 0 000 4.242l2.829 2.829a3 3 0 004.242 0l1.414-1.414L4.715 6.542zm.707 2.829l2.829-2.829a1 1 0 011.414 0l2.829 2.829a1 1 0 010 1.414l-2.829 2.829a1 1 0 01-1.414 0l-2.829-2.829a1 1 0 010-1.414z"/>
                <path d="M6.586 4.071L8 2.657l8.485 8.485-1.414 1.414L6.586 4.07zM11.371 9.429l2.828-2.829a1 1 0 010-1.414l-2.828-2.828a1 1 0 00-1.414 0l-2.829 2.829 2.829 2.828a1 1 0 001.414 0z"/>
              </svg>
              Oracle连接
            </h5>
            <button @click="showCreateModal = true" class="btn btn-primary btn-sm">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-plus-lg me-1" viewBox="0 0 16 16">
                <path d="M8 0a1 1 0 011 1v6h6a1 1 0 110 2H9v6a1 1 0 11-2 0V9H1a1 1 0 110-2h6V1a1 1 0 011-1z"/>
              </svg>
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
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-geo-alt me-1" viewBox="0 0 16 16">
                          <path d="M12.166 8.94c-.524 1.062-1.234 2.12-1.96 3.07A31.493 31.493 0 018 14.58a31.481 31.481 0 01-2.206-2.57c-.726-.95-1.436-2.008-1.96-3.07C3.304 7.867 3 6.862 3 6a5 5 0 0110 0c0 .862-.305 1.867-.834 2.94zM8 16s6-5.686 6-10A6 6 0 002 6c0 4.314 6 10 6 10z"/>
                          <path d="M8 8a2 2 0 100-4 2 2 0 000 4zm0 1a3 3 0 110-6 3 3 0 010 6z"/>
                        </svg>
                        {{ conn.host }}:{{ conn.port }}
                        <span class="mx-2">/</span>
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-collection me-1" viewBox="0 0 16 16">
                          <path d="M2.5 3.5a.5.5 0 000-1h11a.5.5 0 000 1h-11zm2-2a.5.5 0 000-1h7a.5.5 0 000 1h-7zM0 13a1.5 1.5 0 001.5 1.5h13A1.5 1.5 0 0016 13V6a1.5 1.5 0 00-1.5-1.5h-13A1.5 1.5 0 000 6v7zm1.5.5A.5.5 0 011 13V6a.5.5 0 01.5-.5h13a.5.5 0 01.5.5v7a.5.5 0 01-.5.5h-13z"/>
                        </svg>
                        {{ conn.service_name }}
                      </div>
                    </div>
                    <div v-if="conn.id" class="btn-group btn-group-sm">
                        <button @click="testConnection(conn.id)" class="btn btn-outline-info" title="测试连接">
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-check-circle" viewBox="0 0 16 16">
                            <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
                            <path d="M10.97 4.97a.235.235 0 00-.02.022L7.477 9.417 5.384 7.323a.75.75 0 00-1.06 1.06L6.97 11.03a.75.75 0 001.079-.02l3.992-4.99a.75.75 0 00-1.071-1.05z"/>
                          </svg>
                        </button>
                        <button @click="deleteConnection(conn.id)" class="btn btn-outline-danger" title="删除连接">
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
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
              <button @click="showCreateModal = true" class="btn btn-primary">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-plus-lg me-1" viewBox="0 0 16 16">
                  <path d="M8 0a1 1 0 011 1v6h6a1 1 0 110 2H9v6a1 1 0 11-2 0V9H1a1 1 0 110-2h6V1a1 1 0 011-1z"/>
                </svg>
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
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-info-circle me-1" viewBox="0 0 16 16">
                <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
              </svg>
              数据库信息
            </h5>
          </div>
          <div class="card-body">
            <div v-if="selectedConnection">
              <div class="mb-4">
                <label class="form-label">选择连接</label>
                <select v-model="selectedConnection" class="form-select" @change="loadDatabaseInfo">
                  <option value="">请选择</option>
                  <option v-for="conn in connections" :key="conn.id" :value="conn.id">
                    {{ conn.name }}
                  </option>
                </select>
              </div>
              
              <div v-if="databaseInfo">
                <h6 class="mb-3">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-diagram-3 me-1" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 017.5 2h1A1.5 1.5 0 0110 3.5v1A1.5 1.5 0 018.5 6v1H14a.5.5 0 00.5-.5v-2A.5.5 0 0014 3H6a.5.5 0 00-.5.5v2A.5.5 0 006 6h5.5v-1A1.5 1.5 0 0113 3.5v-1zM14 7H6v2a.5.5 0 00.5.5h7a.5.5 0 00.5-.5V7zm-5 3.5v1a1.5 1.5 0 01-1.5 1.5h-1A1.5 1.5 0 015 11.5v-1A1.5 1.5 0 016.5 9H8a.5.5 0 00.5-.5v-1H2a.5.5 0 00-.5.5v2A.5.5 0 002 11h8a.5.5 0 00.5-.5v-2A.5.5 0 0010 8H5.5v1a1.5 1.5 0 011.5 1.5zm-5 0v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zM2 4.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1z"/>
                  </svg>
                  Schemas
                </h6>
                <div class="list-group list-group-flush mb-4">
                  <div v-for="schema in databaseInfo.schemas" :key="schema" class="list-group-item d-flex align-items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-folder me-2 text-primary" viewBox="0 0 16 16">
                      <path d="M.54 3.87L.5 3a2 2 0 012-2h3.672a2 2 0 011.414.586l.828.828A2 2 0 009.828 3h3.982a2 2 0 011.992 2.181l-.637 7A2 2 0 0113.174 14H2.826a2 2 0 01-1.991-1.819l-.637-7a1.99 1.99 0 01.342-1.31zM2.19 4a1 1 0 00-.996 1.09l.637 7a1 1 0 00.995.91h10.348a1 1 0 00.995-.91l.637-7A1 1 0 0013.81 4H2.19zm4.69-1.707A1 1 0 006.172 2H2.5a1 1 0 00-1 .981l.006.139c.001.07.014.138.036.199h.726a1 1 0 01.866.5l.582 1.006a1 1 0 00.866.5H9.19a1 1 0 00.866-.5l.582-1.006a1 1 0 01.866-.5h.726c.022-.061.035-.13.036-.199l.006-.139a1 1 0 00-1-.981H9.828a1 1 0 00-.707.293l-.828.828z"/>
                    </svg>
                    {{ schema }}
                  </div>
                </div>
                
                <h6 class="mb-3">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-people me-1" viewBox="0 0 16 16">
                    <path d="M15 14s1 0 1-1-1-4-5-4-5 3-5 4 1 1 1 1h8zm-7.978-1A.261.261 0 017 12.996c.001-.264.167-1.03.76-1.72C8.312 10.629 9.282 10 11 10c1.717 0 2.687.63 3.24 1.276.593.69.758 1.457.76 1.72l-.008.002a.274.274 0 01-.014.002H7.022zM11 7a2 2 0 100-4 2 2 0 000 4zm3-2a3 3 0 11-6 0 3 3 0 016 0zM6.936 9.28a5.88 5.88 0 00-1.23-.247A7.35 7.35 0 005 9c-4 0-5 3-5 4 0 .667.333 1 1 1h4.216A2.238 2.238 0 015 13c0-1.01.377-2.042 1.09-2.904.243-.294.526-.569.846-.816zM4.92 10A5.493 5.493 0 004 13H1c0-.26.164-1.03.76-1.724.545-.636 1.492-1.256 3.16-1.275zM1.5 5.5a3 3 0 116 0 3 3 0 01-6 0zm3-2a2 2 0 100 4 2 2 0 000-4z"/>
                  </svg>
                  Users
                </h6>
                <div class="list-group list-group-flush">
                  <div v-for="user in databaseInfo.users" :key="user" class="list-group-item d-flex align-items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-person me-2 text-secondary" viewBox="0 0 16 16">
                      <path d="M8 8a3 3 0 100-6 3 3 0 000 6zm2-3a2 2 0 11-4 0 2 2 0 014 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/>
                    </svg>
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
                <input v-model="newConnection.name" type="text" class="form-control" required placeholder="输入连接名称">
              </div>
              <div class="mb-3">
                <label class="form-label">主机</label>
                <input v-model="newConnection.host" type="text" class="form-control" required placeholder="例如: localhost">
              </div>
              <div class="mb-3">
                <label class="form-label">端口</label>
                <input v-model.number="newConnection.port" type="number" class="form-control" required placeholder="默认: 1521">
              </div>
              <div class="mb-3">
                <label class="form-label">服务名</label>
                <input v-model="newConnection.service_name" type="text" class="form-control" required placeholder="例如: ORCL">
              </div>
              <div class="mb-3">
                <label class="form-label">用户名</label>
                <input v-model="newConnection.username" type="text" class="form-control" required placeholder="数据库用户名">
              </div>
              <div class="mb-3">
                <label class="form-label">密码</label>
                <input v-model="newConnection.password" type="password" class="form-control" required placeholder="数据库密码">
              </div>
              <button type="submit" class="btn btn-primary w-100" :disabled="creating">
                <span v-if="creating" class="spinner-border spinner-border-sm me-2"></span>
                {{ creating ? '创建中...' : '创建连接' }}
              </button>
            </form>
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
const connections = ref<OracleConnection[]>([])
const selectedConnection = ref<number | null>(null)
const showCreateModal = ref(false)
const databaseInfo = ref<any>(null)

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
  color: #2d3748;
}

.page-header .text-muted {
  font-size: 1rem;
}

.card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  border-bottom: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.list-group-item:hover {
  background-color: #f7fafc;
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
  border: 2px solid #e9ecef;
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}

.form-label {
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 0.5rem;
}

.modal-content {
  border-radius: 1rem;
  border: none;
}

.modal-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  color: #2d3748;
  font-size: 0.95rem;
}

.text-muted small {
  line-height: 1.6;
}
</style>
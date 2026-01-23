<template>
  <div class="oracle-database-view">
    <h1>Oracle数据库管理</h1>
    
    <div class="row mt-4">
      <div class="col-md-6">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5>Oracle连接</h5>
            <button @click="showCreateModal = true" class="btn btn-primary btn-sm">添加连接</button>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center">
              <div class="spinner-border" role="status"></div>
            </div>
            <div v-else-if="connections.length > 0">
              <ul class="list-group">
                <li v-for="conn in connections" :key="conn.id" class="list-group-item">
                  <div class="d-flex justify-content-between align-items-center">
                    <div>
                      <strong>{{ conn.name }}</strong><br>
                      <small>{{ conn.host }}:{{ conn.port }} / {{ conn.service_name }}</small>
                    </div>
                    <div class="btn-group btn-group-sm">
                      <button @click="testConnection(conn.id)" class="btn btn-info">测试</button>
                      <button @click="deleteConnection(conn.id)" class="btn btn-danger">删除</button>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
            <div v-else class="text-center text-muted">
              暂无连接
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-md-6">
        <div class="card">
          <div class="card-header">
            <h5>数据库信息</h5>
          </div>
          <div class="card-body">
            <div v-if="selectedConnection">
              <div class="mb-3">
                <label class="form-label">选择连接</label>
                <select v-model="selectedConnection" class="form-select" @change="loadDatabaseInfo">
                  <option value="">请选择</option>
                  <option v-for="conn in connections" :key="conn.id" :value="conn.id">
                    {{ conn.name }}
                  </option>
                </select>
              </div>
              
              <div v-if="databaseInfo">
                <h6>Schemas</h6>
                <ul class="list-group mb-3">
                  <li v-for="schema in databaseInfo.schemas" :key="schema" class="list-group-item">
                    {{ schema }}
                  </li>
                </ul>
                
                <h6>Users</h6>
                <ul class="list-group">
                  <li v-for="user in databaseInfo.users" :key="user" class="list-group-item">
                    {{ user }}
                  </li>
                </ul>
              </div>
            </div>
            <div v-else class="text-muted">
              请先选择一个连接
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="modal" v-if="showCreateModal" tabindex="-1" style="display: block; background: rgba(0,0,0,0.5)">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">添加Oracle连接</h5>
            <button type="button" class="btn-close" @click="showCreateModal = false"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="createConnection">
              <div class="mb-3">
                <label class="form-label">连接名称</label>
                <input v-model="newConnection.name" type="text" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">主机</label>
                <input v-model="newConnection.host" type="text" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">端口</label>
                <input v-model.number="newConnection.port" type="number" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">服务名</label>
                <input v-model="newConnection.service_name" type="text" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">用户名</label>
                <input v-model="newConnection.username" type="text" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">密码</label>
                <input v-model="newConnection.password" type="password" class="form-control" required>
              </div>
              <button type="submit" class="btn btn-primary" :disabled="creating">
                {{ creating ? '创建中...' : '创建' }}
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
  if (!confirm('确定要删除此连接吗？')) return
  try {
    await oracleConnectionApi.delete(id)
    await loadConnections()
  } catch (error) {
    console.error('Failed to delete connection:', error)
  }
}

const testConnection = async (id: number) => {
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
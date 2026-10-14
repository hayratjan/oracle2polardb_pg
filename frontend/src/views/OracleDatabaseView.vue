<template>
  <div class="oracle-database-view">
    <div v-if="alertMessage.show" :class="['alert', `alert-${alertMessage.type}`, 'alert-dismissible', 'fade', 'show']" role="alert">
      <div class="d-flex align-items-center">
        <i :class="getAlertIcon(alertMessage.type)" class="me-2"></i>
        <div class="flex-grow-1">{{ alertMessage.message }}</div>
        <button type="button" class="btn-close" @click="alertMessage.show = false"></button>
      </div>
    </div>
    
    <PageHeader
      title="Oracle 数据库管理"
      subtitle="管理 Oracle 数据库连接和查看数据库信息"
      icon="bi-database-gear"
    />
    
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
                          <i class="bi bi-check-circle"></i>
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
              <i class="bi bi-dash-circle text-muted mb-3" style="font-size: 64px;"></i>
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
            <div v-if="connections.length">
              <div class="mb-3">
                <label class="form-label">选择连接</label>
                <select v-model="selectedConnection" class="form-select-sm" @change="loadDatabaseInfo">
                  <option value="">请选择</option>
                  <option v-for="conn in connections" :key="conn.id" :value="conn.id">
                    {{ conn.name }}
                  </option>
                </select>
              </div>

              <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0">
                  <i class="bi bi-speedometer2 me-1"></i>运行指标
                </h6>
                <button type="button" class="btn btn-sm btn-outline-secondary py-0 px-2"
                        :disabled="dbInfoLoading || !selectedConnection" @click="loadDatabaseInfo">
                  <i class="bi bi-arrow-clockwise me-1"></i>刷新
                </button>
              </div>

              <div v-if="dbInfoLoading" class="text-muted small py-3">
                <span class="spinner-border spinner-border-sm me-2"></span>正在采集源库指标…
              </div>
              <div v-else-if="dbInfoError" class="alert alert-danger py-2 small mb-3">
                <div class="fw-semibold">{{ dbInfoError.message }}</div>
                <div v-if="dbInfoError.hint" class="mt-1">{{ dbInfoError.hint }}</div>
                <pre v-if="dbInfoError.detail" class="bg-white border rounded p-2 mt-2 mb-0 small"
                     style="max-height: 140px; overflow: auto; white-space: pre-wrap;">{{ dbInfoError.detail }}</pre>
              </div>

              <template v-else-if="dbInfo">
                <div class="d-flex flex-wrap gap-2 mb-3">
                  <span class="badge text-bg-light border"
                        :title="'取连接耗时 ' + dbInfo.acquire_ms + ' ms（连接池命中时接近 0；首次建连包含 TCP+认证握手）'">
                    <i class="bi bi-stopwatch me-1"></i>往返 {{ dbInfo.ping_ms }} ms · 取连接 {{ dbInfo.acquire_ms }} ms
                  </span>
                  <span class="badge text-bg-light border">
                    {{ dbInfo.version?.release || '版本未知' }}
                  </span>
                  <span class="badge text-bg-light border">{{ dbInfo.connection_name }}</span>
                </div>

                <div class="row g-2 mb-3">
                  <div v-for="stat in dbInfoStats" :key="stat.label" class="col-6 col-xl-4">
                    <div class="border rounded p-2 h-100">
                      <div class="text-muted" style="font-size: .72rem;">{{ stat.label }}</div>
                      <div class="fw-semibold text-truncate" :title="String(stat.value)">{{ stat.value }}</div>
                    </div>
                  </div>
                </div>

                <div v-for="bar in memoryBars" :key="bar.label" class="mb-2">
                  <div class="d-flex justify-content-between small">
                    <span>{{ bar.label }} 内存</span>
                    <span class="text-muted">{{ bar.usedText }} / {{ bar.totalText }}</span>
                  </div>
                  <div class="progress" style="height: 6px;">
                    <div class="progress-bar bg-primary" role="progressbar"
                         :style="{ width: (bar.pct ?? 0) + '%' }"></div>
                  </div>
                </div>

                <div v-if="dbInfo.storage?.tablespaces?.length" class="mt-3">
                  <div class="small text-muted mb-1">表空间占用 Top {{ dbInfo.storage.tablespaces.length }}</div>
                  <div v-for="ts in dbInfo.storage.tablespaces" :key="ts.name" class="mb-2">
                    <div class="d-flex justify-content-between small">
                      <span>{{ ts.name }}</span>
                      <span class="text-muted">
                        {{ ts.used_pct }}% · {{ formatBytes(ts.used_bytes) }} / {{ formatBytes(ts.size_bytes) }}
                      </span>
                    </div>
                    <div class="progress" style="height: 6px;">
                      <div class="progress-bar" role="progressbar"
                           :class="ts.used_pct >= 90 ? 'bg-danger' : 'bg-info'"
                           :style="{ width: (ts.used_pct ?? 0) + '%' }"></div>
                    </div>
                  </div>
                </div>

                <div v-if="dbInfoErrorSummary" class="small text-muted mt-2">
                  <i class="bi bi-exclamation-triangle me-1"></i>
                  部分指标因权限或版本不可用：{{ dbInfoErrorSummary }}
                </div>
              </template>

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
              <i class="bi bi-bell mb-3" style="font-size: 48px;"></i>
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
              <i class="bi bi-pencil-square me-2"></i>
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

    <div class="modal" v-if="testResultModal.show" tabindex="-1" style="display: block; background: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="bi bi-plug me-2"></i>
              连接测试结果
            </h5>
            <button type="button" class="btn-close" @click="testResultModal.show = false"></button>
          </div>
          <div class="modal-body text-center py-4">
            <div v-if="testResultModal.loading" class="py-3">
              <div class="spinner-border text-primary mb-3" role="status"></div>
              <p class="mb-0 text-muted">正在测试连接…</p>
            </div>
            <template v-else>
              <i v-if="testResultModal.success" class="bi bi-check-circle-fill text-success mb-3" style="font-size: 3rem;"></i>
              <i v-else class="bi bi-x-circle-fill text-danger mb-3" style="font-size: 3rem;"></i>
              <p class="mb-0">{{ testResultModal.message }}</p>
              <div v-if="testResultModal.hint" class="alert alert-warning text-start mt-3 mb-0 py-2 small">
                <i class="bi bi-lightbulb me-1"></i>{{ testResultModal.hint }}
              </div>
              <div v-if="testResultModal.detail" class="mt-3 text-start">
                <button type="button" class="btn btn-link btn-sm p-0 text-muted" @click="showRawError = !showRawError">
                  {{ showRawError ? '收起' : '查看' }}原始数据库错误
                </button>
                <pre v-if="showRawError" class="bg-light border rounded p-2 mt-2 mb-0 small text-start"
                     style="max-height: 180px; overflow: auto; white-space: pre-wrap;">{{ testResultModal.detail }}</pre>
              </div>
            </template>
          </div>
          <div class="modal-footer" v-if="!testResultModal.loading">
            <button type="button" class="btn btn-primary" @click="testResultModal.show = false">确定</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { oracleConnectionApi, databaseApi } from '@/api'
import type { OracleConnection } from '@/api'
import PageHeader from '@/components/PageHeader.vue'

const loading = ref(false)
const creating = ref(false)
const updating = ref(false)
const testing = ref(false)
const connections = ref<OracleConnection[]>([])
const selectedConnection = ref<number | null>(null)
const showCreateModal = ref(false)
const showEditModal = ref(false)
const testResultModal = ref<{
  show: boolean
  loading: boolean
  success: boolean
  message: string
  hint: string
  detail: string
}>({
  show: false,
  loading: false,
  success: false,
  message: '',
  hint: '',
  detail: '',
})
const showRawError = ref(false)
const databaseInfo = ref<any>(null)
const dbInfo = ref<any>(null)
const dbInfoLoading = ref(false)
const dbInfoError = ref<{ message: string; hint: string; detail: string } | null>(null)

const formatBytes = (bytes?: number | null): string => {
  if (bytes === null || bytes === undefined) return '—'
  const gb = bytes / 1073741824
  return gb >= 1 ? `${gb.toFixed(2)} GB` : `${(bytes / 1048576).toFixed(1)} MB`
}

const formatNumber = (value: any): string => (value === null || value === undefined ? '—' : String(value))

const dbInfoStats = computed(() => {
  const d: any = dbInfo.value
  if (!d) return []
  const c = d.counts || {}
  const p = d.processes || {}
  const s = d.sessions || {}
  const st = d.storage || {}
  const inst = d.instance || {}
  return [
    { label: '数据库名', value: formatNumber(c.database_name) },
    { label: '可插拔库', value: c.pdb_count ? `${c.pdb_count} 个 PDB` : '1（非 CDB / 11g）' },
    { label: '实例 @ 主机', value: inst.instance_name ? `${inst.instance_name} @ ${inst.host_name}` : '—' },
    { label: '实例状态', value: formatNumber(inst.status) },
    { label: '用户数', value: formatNumber(c.users) },
    { label: c.schema ? `表数量（${c.schema}）` : '表数量（全库）', value: formatNumber(c.tables) },
    { label: '会话（活跃/总）', value: s.total === null || s.total === undefined ? '—' : `${s.active_user ?? 0} / ${s.total}` },
    { label: '进程（当前/上限）', value: p.current === null || p.current === undefined ? '—' : `${p.current} / ${formatNumber(p.limit)}` },
    { label: '数据文件', value: st.datafile_count ? `${st.datafile_count} 个 / ${formatBytes(st.datafile_bytes)}` : '—' },
    { label: '实例启动时间', value: formatNumber(inst.startup_time) },
  ]
})

const memoryBars = computed(() => {
  const m: any = dbInfo.value?.memory
  if (!m) return []
  const build = (label: string, used?: number | null, total?: number | null) => ({
    label,
    usedText: formatBytes(used),
    totalText: formatBytes(total),
    pct: used && total ? Math.min(100, Math.round((used / total) * 1000) / 10) : null,
  })
  return [
    build('SGA', m.sga_used_bytes, m.sga_target_bytes),
    build('PGA', m.pga_allocated_bytes, m.pga_target_bytes),
  ]
})

const dbInfoErrorSummary = computed(() => {
  const errors = dbInfo.value?.errors || {}
  const keys = Object.keys(errors)
  if (!keys.length) return ''
  return keys.map((k) => `${k}（${errors[k]}）`).join('、')
})
const alertMessage = ref<{
  show: boolean
  type: 'success' | 'danger' | 'warning' | 'info'
  message: string
}>({
  show: false,
  type: 'success',
  message: '',
})

const getAlertIcon = (type: string) => {
  const icons: Record<string, string> = {
    success: 'bi bi-check-circle-fill',
    danger: 'bi bi-exclamation-triangle-fill',
    warning: 'bi bi-exclamation-circle-fill',
    info: 'bi bi-info-circle-fill',
  }
  return icons[type] || 'bi bi-info-circle-fill'
}
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

const testEditedConnection = async () => {
  const ed = editedConnection.value
  if (!ed.id) return
  if (!ed.host?.trim() || !ed.service_name?.trim() || !ed.username?.trim()) {
    testResultModal.value = { show: true, loading: false, success: false, message: '请先填写主机、服务名和用户名', hint: '', detail: '' }
    return
  }
  testing.value = true
  showRawError.value = false
  testResultModal.value = { show: true, loading: true, success: false, message: '', hint: '', detail: '' }
  try {
    const res = await oracleConnectionApi.testWithParams({
      connection_id: ed.id,
      host: ed.host.trim(),
      port: Number(ed.port) || 1521,
      service_name: ed.service_name.trim(),
      username: ed.username.trim(),
      password: ed.password || undefined,
    })
    testResultModal.value.loading = false
    testResultModal.value.success = res.data.status === 'success'
    if (testResultModal.value.success) {
      testResultModal.value.message = '连接测试成功'
    } else {
      testResultModal.value.message = res.data.message || '连接测试失败'
      testResultModal.value.hint = res.data.hint || ''
      testResultModal.value.detail = res.data.detail || ''
    }
  } catch (error: any) {
    console.error('Failed to test connection:', error)
    const data = error?.response?.data
    testResultModal.value.loading = false
    testResultModal.value.success = false
    testResultModal.value.message = data?.message || '连接测试失败'
    testResultModal.value.hint = data?.hint || ''
    testResultModal.value.detail = data?.detail || ''
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
  showRawError.value = false
  testResultModal.value = { show: true, loading: true, success: false, message: '', hint: '', detail: '' }
  try {
    const res = await oracleConnectionApi.test(id)
    testResultModal.value.loading = false
    testResultModal.value.success = res.data.status === 'success'
    if (testResultModal.value.success) {
      testResultModal.value.message = '连接测试成功'
    } else {
      testResultModal.value.message = res.data.message || '连接测试失败'
      testResultModal.value.hint = res.data.hint || ''
      testResultModal.value.detail = res.data.detail || ''
    }
  } catch (error: any) {
    console.error('Failed to test connection:', error)
    const data = error?.response?.data
    testResultModal.value.loading = false
    testResultModal.value.success = false
    testResultModal.value.message = data?.message || '连接测试失败'
    testResultModal.value.hint = data?.hint || ''
    testResultModal.value.detail = data?.detail || ''
  }
}

const loadDatabaseInfo = async () => {
  if (!selectedConnection.value) return
  const connectionId = selectedConnection.value

  dbInfoLoading.value = true
  dbInfoError.value = null
  dbInfo.value = null
  try {
    const res = await databaseApi.getDatabaseInfo({ connection_id: connectionId })
    if (res.data.status === 'success') {
      dbInfo.value = res.data
    } else {
      dbInfoError.value = {
        message: res.data.message || '获取数据库信息失败',
        hint: res.data.hint || '',
        detail: res.data.detail || '',
      }
    }
  } catch (error: any) {
    const data = error?.response?.data
    dbInfoError.value = {
      message: data?.message || '获取数据库信息失败',
      hint: data?.hint || '',
      detail: data?.detail || '',
    }
  } finally {
    dbInfoLoading.value = false
  }

  // 指标与对象列表相互独立：指标失败不影响 Schemas/Users 展示
  try {
    const [schemasRes, usersRes] = await Promise.all([
      databaseApi.getOracleSchemas({ connection_id: connectionId }),
      databaseApi.getOracleUsers({ connection_id: connectionId }),
    ])

    databaseInfo.value = {
      schemas: schemasRes.data.schemas || [],
      users: usersRes.data.users || [],
    }
  } catch (error) {
    console.error('Failed to load database objects:', error)
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
.list-group-item:hover .text-muted {
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
</style>
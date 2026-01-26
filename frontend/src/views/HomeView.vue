<template>
  <div class="home-view">
    <div class="hero-section">
      <div class="container">
        <div class="row align-items-center">
          <div class="col-lg-8">
            <h1 class="display-4 fw-bold mb-3">Oracle到PolarDB-PG迁移平台</h1>
            <p class="lead mb-4">高效、安全、可靠的数据库迁移解决方案</p>
            <div class="d-flex gap-3">
              <router-link to="/task/create" class="btn btn-lg btn-light btn-gradient">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-rocket-takeoff me-2" viewBox="0 0 16 16">
                  <path d="M9.752 6.193c.599.6 1.73.437 2.182-.33.47-.779.492-2.055.04-2.73-.47-.795-1.673-.908-2.228-.52-.527.367-.74.89-.299 1.432l.333 1.51c.024.11.034.219.028.327-.004.1-.014.197-.032.292l.266.136c.143.074.288.144.435.21.149.067.297.13.445.188zM12.418 8.48c.718.007 1.336.402 1.632 1.04.3.646.234 1.39-.18 1.977-.438.62-1.187.92-1.914.79-.725-.13-1.32-.648-1.541-1.343-.22-.694.03-1.45.632-1.896.523-.383 1.07-.457 1.371-.568zm-4.144 1.352c.66.007 1.226.368 1.498.954.275.594.215 1.278-.163 1.819-.403.568-1.09.845-1.758.724-.664-.12-1.208-.593-1.413-1.229-.201-.635.027-1.327.58-1.739.48-.351.986-.42 1.256-.529zM7.08 5.813c.6.006 1.115.335 1.36.868.25.54.195 1.162-.148 1.656-.366.516-.99.77-1.6.662-.604-.108-1.098-.538-1.284-1.116-.183-.576.025-1.203.527-1.583.435-.319.894-.381 1.145-.487zM5.353 3.326c.532.005.99.297 1.206.77.22.478.173 1.03-.131 1.466-.324.458-.878.683-1.419.587-.536-.096-.973-.477-1.139-.99-.163-.51.022-1.067.468-1.404.386-.283.793-.338 1.015-.429zM3.647.9c.464.005.864.259 1.053.67.193.418.151.9-.115 1.282-.283.4-.768.597-1.242.513-.468-.084-.85-.418-.996-.865-.142-.444.02-.933.409-1.228.337-.247.693-.295.891-.372zM2.08 6.78c.432.004.804.242.981.626.18.389.14.836-.107 1.19-.264.373-.718.557-1.158.48-.436-.078-.79-.386-.925-.795-.133-.406.018-.863.383-1.138.314-.23.648-.273.826-.343zM.715 10.923c.4.004.745.224.908.58.167.361.13.774-.1 1.103-.244.346-.664.517-1.073.445-.404-.072-.732-.358-.857-.737-.123-.376.017-.8.355-1.055.291-.214.6-.253.767-.318zm1.896 3.63c.37.003.69.207.84.538.154.335.12.718-.092 1.022-.226.32-.615.48-.993.412-.374-.067-.678-.332-.794-.683-.114-.347.016-.742.329-.978.27-.199.556-.234.71-.296zm2.98 2.917c.34.003.634.19.772.494.141.308.11.66-.084.938-.208.293-.565.44-.912.378-.344-.062-.624-.305-.73-.626-.105-.318.015-.68.302-.898.248-.182.51-.214.652-.27zm3.058 2.02c.31.003.578.173.704.45.13.281.101.601-.077.855-.19.27-.516.403-.832.345-.313-.056-.568-.278-.665-.57-.096-.29.014-.62.275-.819.226-.166.464-.195.595-.246zm3.012.913c.28.002.524.156.639.408.117.255.09.546-.07.776-.173.244-.468.365-.754.312-.283-.05-.514-.252-.603-.517-.087-.263.013-.563.25-.743.204-.15.42-.177.538-.223zm2.858-.288c.25.002.47.14.575.366.105.228.082.49-.063.697-.156.22-.421.33-.676.282-.254-.045-.461-.226-.541-.464-.078-.236.012-.505.224-.667.183-.135.377-.159.481-.2zm2.557-1.345c.22.002.414.123.507.321.093.201.072.431-.055.613-.138.194-.371.29-.598.247-.224-.04-.407-.2-.479-.408-.07-.208.01-.443.197-.587.16-.119.332-.14.428-.176zm2.12-2.12c.19.002.362.106.445.277.082.173.064.376-.048.537-.122.17-.326.254-.525.216-.196-.035-.357-.176-.42-.357-.062-.18.009-.388.173-.514.14-.104.291-.123.375-.155zm1.577-2.645c.17.001.317.094.393.246.073.152.057.33-.043.473-.108.15-.29.226-.46.193-.17-.032-.31-.16-.366-.324-.055-.163.008-.35.152-.463.124-.092.258-.108.324-.136zm.95-2.99c.148.001.277.082.344.214.064.132.05.289-.038.413-.095.132-.255.198-.404.168-.148-.028-.27-.14-.319-.283-.048-.142.007-.306.133-.405.108-.08.226-.094.284-.118zm.268-3.094c.127.001.238.07.296.184.055.113.043.248-.033.353-.081.113-.218.17-.346.144-.127-.024-.231-.12-.274-.243-.041-.122.006-.262.114-.347.092-.068.193-.08.242-.101zm-.378-2.99c.107.001.2.06.25.155.047.095.037.21-.028.299-.068.096-.187.145-.296.121-.109-.02-.198-.103-.235-.206-.035-.103.005-.222.097-.295.078-.058.165-.068.208-.087zm-.976-2.635c.087.001.163.049.203.126.038.077.03.171-.023.244-.055.078-.151.118-.24.099-.088-.017-.16-.083-.191-.167-.028-.084.004-.18.079-.239.063-.047.133-.055.172-.07zm-1.438-2.09c.067.001.125.038.156.097.03.059.023.131-.018.188-.043.06-.117.091-.186.076-.068-.013-.123-.064-.148-.129-.022-.065.003-.139.061-.184.049-.036.103-.043.135-.056zm-1.75-1.458c.047.001.088.027.11.068.021.041.016.091-.012.131-.03.042-.082.064-.13.053-.048-.009-.086-.045-.104-.09-.016-.045.002-.097.043-.127.034-.025.072-.03.094-.038zm-1.926-.765c.027.001.05.015.063.039.012.024.009.052-.007.075-.017.024-.047.037-.075.03-.028-.005-.05-.026-.06-.046-.009-.026.001-.056.025-.072.02-.014.041-.017.054-.022z"/>
                </svg>
                立即开始
              </router-link>
              <router-link to="/tasks" class="btn btn-lg btn-outline-light">
                查看任务
              </router-link>
            </div>
          </div>
          <div class="col-lg-4 d-none d-lg-block">
            <div class="hero-image">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" class="floating">
                <defs>
                  <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
                  </linearGradient>
                </defs>
                <circle cx="200" cy="200" r="150" fill="url(#grad1)" opacity="0.2"/>
                <circle cx="200" cy="200" r="100" fill="url(#grad1)" opacity="0.4"/>
                <circle cx="200" cy="200" r="50" fill="url(#grad1)" opacity="0.6"/>
                <path d="M150 200 L200 150 L250 200 L200 250 Z" fill="white" opacity="0.8"/>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="container mt-5">
      <div class="row g-4">
        <div class="col-md-4">
          <div class="card feature-card">
            <div class="card-body text-center">
              <div class="feature-icon mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-list-task" viewBox="0 0 16 16">
                  <path fill-rule="evenodd" d="M2 2.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5V3a.5.5 0 00-.5-.5H2zM3 3H2v1h1V3z"/>
                  <path d="M5 3.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zM5.5 7a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM6 8H5v1h1V8z"/>
                  <path d="M8 7.5a.5.5 0 01.5-.5h9a.5.5 0 010 1h-9a.5.5 0 01-.5-.5zm.5 4a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM9 13H8v1h1v-1z"/>
                </svg>
              </div>
              <h5 class="card-title">迁移任务</h5>
              <p class="card-text">管理和监控数据库迁移任务，实时查看进度和状态</p>
              <router-link to="/tasks" class="btn btn-primary mt-3">查看任务</router-link>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card feature-card">
            <div class="card-body text-center">
              <div class="feature-icon mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-plus-circle" viewBox="0 0 16 16">
                  <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
                </svg>
              </div>
              <h5 class="card-title">创建任务</h5>
              <p class="card-text">快速创建新的数据库迁移任务，支持多种迁移类型</p>
              <router-link to="/task/create" class="btn btn-success mt-3">创建任务</router-link>
            </div>
          </div>
        </div>
        
        <div class="col-md-4">
          <div class="card feature-card">
            <div class="card-body text-center">
              <div class="feature-icon mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-database-gear" viewBox="0 0 16 16">
                  <path d="M6.5 1A.5.5 0 017 .5h2a.5.5 0 01.5.5v1a.5.5 0 01-.5.5H7a.5.5 0 01-.5-.5v-1zM2.5 4.5A.5.5 0 013 4h10a.5.5 0 01.5.5v1a.5.5 0 01-.5.5H3a.5.5 0 01-.5-.5v-1zm6.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM1 8a2 2 0 012-2h10a2 2 0 012 2v5a2 2 0 01-2 2H3a2 2 0 01-2-2V8zm1 0v5a1 1 0 001 1h10a1 1 0 001-1V8a1 1 0 00-1-1H3a1 1 0 00-1 1z"/>
                </svg>
              </div>
              <h5 class="card-title">数据库连接</h5>
              <p class="card-text">管理Oracle和PostgreSQL数据库连接，一键测试连接状态</p>
              <router-link to="/oracle" class="btn btn-info mt-3">管理连接</router-link>
            </div>
          </div>
        </div>
      </div>
      
      <div class="row mt-5 g-4">
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-clock-history me-2" viewBox="0 0 16 16">
                  <path d="M8.515 1.019A7 7 0 008 1V0a8 8 0 01.589.022l-.074.997zm2.004.45a7.003 7.003 0 00-.985-.299l.219-.976c.383.086.76.2 1.126.342l-.36.933zm1.37.71a7.01 7.01 0 00-.439-.27l.493-.87a8.025 8.025 0 01.979.654l-.615.789a6.996 6.996 0 00-.418-.302zm1.834 1.79a6.99 6.99 0 00-.653-.796l.79-.615c.32.312.612.648.873 1.006l-.818.584c-.064-.06-.138-.1-.192-.18zm1.48 2.283a7.028 7.028 0 00-.4-.528l.928-.615c.3.448.543.922.719 1.414l-.994.197c-.07-.16-.15-.314-.253-.468zm.66 2.735a7.023 7.023 0 00-.068-.648l.996-.083c.043.387.053.78.03 1.175l-.996-.12c.017-.11.023-.223.038-.324zM9.5 11.5a.5.5 0 01-.5.5H3a.5.5 0 01-.5-.5V9a.5.5 0 01.5-.5h6a.5.5 0 01.5.5v2.5z"/>
                </svg>
                最近任务
              </h5>
            </div>
            <div class="card-body">
              <div v-if="loading" class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">加载中...</p>
              </div>
              <div v-else-if="recentTasks.length > 0">
                <ul class="list-group list-group-flush">
                  <li v-for="task in recentTasks" :key="task.id" class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                      <router-link :to="`/task/${task.id}`" class="text-decoration-none fw-bold">
                        {{ task.name }}
                      </router-link>
                      <div class="small text-muted mt-1">
                        {{ formatDate(task.created_at) }}
                      </div>
                    </div>
                    <span class="badge" :class="getStatusBadgeClass(task.status)">
                      {{ getStatusText(task.status) }}
                    </span>
                  </li>
                </ul>
              </div>
              <div v-else class="text-center py-4 text-muted">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-inbox mb-3" viewBox="0 0 16 16">
                  <path d="M4.98 4a.5.5 0 00-.39.188L1.54 8H6a.5.5 0 01.5.5 1.5 1.5 0 003 0A.5.5 0 0110 8h4.46l-3.05-3.812A.5.5 0 0011.02 4H4.98zm9.954 5H10.45a2.5 2.5 0 01-4.9 0H1.066l.32 2.562a.5.5 0 00.497.438h12.234a.5.5 0 00.496-.438L14.933 9zM3.809 3.563A1.5 1.5 0 014.981 3h6.038a1.5 1.5 0 011.172.563l3.7 4.625a.5.5 0 01.105.374l-.39 3.124A1.5 1.5 0 0114.117 13H1.883a1.5 1.5 0 01-1.489-1.314l-.39-3.124a.5.5 0 01.105-.374l3.7-4.625z"/>
                </svg>
                <p>暂无任务</p>
                <router-link to="/task/create" class="btn btn-sm btn-primary mt-2">创建第一个任务</router-link>
              </div>
            </div>
          </div>
        </div>
        
        <div class="col-md-6">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-diagram-3 me-2" viewBox="0 0 16 16">
                  <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 017.5 2h1A1.5 1.5 0 0110 3.5v1A1.5 1.5 0 018.5 6v1H14a.5.5 0 01.5.5v1a.5.5 0 01-1 0V8h-1v.5a.5.5 0 01-1 0V8h-1v.5a.5.5 0 01-1 0V8h-1v.5a.5.5 0 01-1 0V8h-1v.5a.5.5 0 01-1 0V8h-1v.5a.5.5 0 01-1 0V8H2v.5a.5.5 0 01-1 0v-1A.5.5 0 011.5 7h5.5V6A1.5 1.5 0 016 4.5v-1zM8.5 5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1zM0 11.5A1.5 1.5 0 011.5 10h1A1.5 1.5 0 014 11.5v1A1.5 1.5 0 012.5 14h-1A1.5 1.5 0 010 12.5v-1zm1.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zm4.5.5a1.5 1.5 0 011.5-1.5h1A1.5 1.5 0 0110 11.5v1A1.5 1.5 0 018.5 14h-1A1.5 1.5 0 016 12.5v-1zm1.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zm4.5.5a1.5 1.5 0 011.5-1.5h1a1.5 1.5 0 011.5 1.5v1a1.5 1.5 0 01-1.5 1.5h-1a1.5 1.5 0 01-1.5-1.5v-1zm1.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1z"/>
                </svg>
                数据库连接
              </h5>
            </div>
            <div class="card-body">
              <div v-if="loading" class="text-center py-4">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">加载中...</p>
              </div>
              <div v-else>
                <div class="row text-center">
                  <div class="col-6">
                    <div class="connection-stat">
                      <div class="stat-icon oracle-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-database" viewBox="0 0 16 16">
                          <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
                        </svg>
                      </div>
                      <div class="stat-number">{{ oracleConnections.length }}</div>
                      <div class="stat-label">Oracle连接</div>
                    </div>
                  </div>
                  <div class="col-6">
                    <div class="connection-stat">
                      <div class="stat-icon postgres-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-server" viewBox="0 0 16 16">
                          <path d="M1.5 0h11.586a1.5 1.5 0 011.06.44l1.415 1.414A1.5 1.5 0 0116 2.914V14.5a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5v-11A1.5 1.5 0 011.5 2zM1 1.5v1a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zm0 4v9a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-9a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zM2 7a1 1 0 011-1h10a1 1 0 011 1v2a1 1 0 01-1 1H3a1 1 0 01-1-1V7zm0 5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1z"/>
                        </svg>
                      </div>
                      <div class="stat-number">{{ postgresConnections.length }}</div>
                      <div class="stat-label">PostgreSQL连接</div>
                    </div>
                  </div>
                </div>
                <div class="mt-4 text-center">
                  <router-link to="/oracle" class="btn btn-outline-primary me-2">管理Oracle</router-link>
                  <router-link to="/postgres" class="btn btn-outline-info">管理PostgreSQL</router-link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { migrationTaskApi, oracleConnectionApi, postgresConnectionApi } from '@/api'
import type { MigrationTask } from '@/api'

const loading = ref(false)
const recentTasks = ref<MigrationTask[]>([])
const oracleConnections = ref<any[]>([])
const postgresConnections = ref<any[]>([])

const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    partial: 'bg-warning',
    canceled: 'bg-dark',
  }
  return classes[status] || 'bg-secondary'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    partial: '部分完成',
    canceled: '已取消',
  }
  return texts[status] || status
}

const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

onMounted(async () => {
  loading.value = true
  try {
    const [tasksRes, oracleRes, postgresRes] = await Promise.all([
      migrationTaskApi.list(),
      oracleConnectionApi.list(),
      postgresConnectionApi.list(),
    ])
    recentTasks.value = tasksRes.data.results?.slice(0, 5) || tasksRes.data.slice(0, 5)
    oracleConnections.value = oracleRes.data.results || oracleRes.data
    postgresConnections.value = postgresRes.data.results || postgresRes.data
  } catch (error) {
    console.error('Failed to load data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.home-view {
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

.hero-section {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.95) 0%, rgba(118, 75, 162, 0.95) 100%);
  color: white;
  padding: 4rem 0;
  border-radius: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.hero-section h1 {
  color: white;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.hero-section .lead {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.5rem;
}

.btn-gradient {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border: none;
  color: white;
}

.btn-gradient:hover {
  background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
  color: white;
  transform: translateY(-3px);
  box-shadow: 0 10px 30px rgba(240, 147, 251, 0.4);
}

.hero-image {
  position: relative;
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-image svg {
  width: 100%;
  height: 100%;
}

.floating {
  animation: floating 3s ease-in-out infinite;
}

@keyframes floating {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.feature-card {
  height: 100%;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-10px);
  box-shadow: 0 25px 80px rgba(0, 0, 0, 0.15);
}

.feature-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon {
  transform: scale(1.1) rotate(5deg);
}

.feature-icon svg {
  width: 40px;
  height: 40px;
}

.connection-stat {
  padding: 1.5rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  transition: all 0.3s ease;
}

.connection-stat:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
}

.stat-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.oracle-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.postgres-icon {
  background: linear-gradient(135deg, #2193b0 0%, #6dd5ed 100%);
}

.stat-number {
  font-size: 2.5rem;
  font-weight: 800;
  color: #667eea;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  color: #6c757d;
  font-weight: 500;
}

.list-group-item {
  border: none;
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
}

.list-group-item:hover {
  background-color: rgba(102, 126, 234, 0.1);
  transform: translateX(5px);
}
</style>
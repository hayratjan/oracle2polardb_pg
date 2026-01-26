<template>
  <div class="task-detail-view">
    <div class="page-header mb-4">
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <h1>
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-file-earmark-text me-2" viewBox="0 0 16 16">
              <path d="M5.5 7a.5.5 0 000 1h5a.5.5 0 000-1h-5zM5 9.5a.5.5 0 01.5-.5h5a.5.5 0 010 1h-5a.5.5 0 01-.5-.5zm0 2a.5.5 0 01.5-.5h2a.5.5 0 010 1h-2a.5.5 0 01-.5-.5z"/>
              <path d="M9.5 0H4a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V4.5L9.5 0zm0 1v2A1.5 1.5 0 018 4.5h2V14a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1h5.5v2z"/>
            </svg>
            任务详情
          </h1>
          <p class="text-muted mb-0">查看和管理迁移任务的详细信息</p>
        </div>
        <router-link to="/tasks" class="btn btn-outline-secondary">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-left me-1" viewBox="0 0 16 16">
            <path fill-rule="evenodd" d="M15 8a.5.5 0 01-.5.5H2.707l3.147 3.146a.5.5 0 01-.708.708l-4-4a.5.5 0 010-.708l4-4a.5.5 0 11.708.708L2.707 7.5H14.5A.5.5 0 0115 8z"/>
          </svg>
          返回列表
        </router-link>
      </div>
    </div>
    
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-3 text-muted">加载任务详情...</p>
    </div>
    
    <div v-else-if="task">
      <div class="row g-4">
        <div class="col-lg-8">
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-info-circle me-1" viewBox="0 0 16 16">
                  <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
                </svg>
                {{ task.name }}
              </h5>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-tag me-1" viewBox="0 0 16 16">
                      <path d="M6 4.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM4.5 6a1.5 1.5 0 100 3 1.5 1.5 0 000-3zM6 8.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM4.5 10a1.5 1.5 0 100 3 1.5 1.5 0 000-3z"/>
                    </svg>
                    任务类型
                  </label>
                  <div class="info-value">{{ getTaskTypeText(task.task_type) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-activity me-1" viewBox="0 0 16 16">
                      <path fill-rule="evenodd" d="M6 2a.5.5 0 01.47.33L10 12.036l1.53-4.208A.5.5 0 0112 7.5h3.5a.5.5 0 010-1h-3.5a.5.5 0 01-.47.33L6 3.964 4.47 8.171A.5.5 0 014 8.5H.5a.5.5 0 010-1h3.5a.5.5 0 01.47.33L6 3.964z"/>
                    </svg>
                    状态
                  </label>
                  <div class="info-value">
                    <span class="badge status-badge" :class="getStatusBadgeClass(task.status)">
                      <span class="status-dot"></span>
                      {{ getStatusText(task.status) }}
                    </span>
                  </div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-database me-1" viewBox="0 0 16 16">
                      <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
                    </svg>
                    源数据库
                  </label>
                  <div class="info-value">{{ task.source_db || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-server me-1" viewBox="0 0 16 16">
                      <path d="M1.5 0h11.586a1.5 1.5 0 011.06.44l1.415 1.414A1.5 1.5 0 0116 2.914V14.5a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5v-11A1.5 1.5 0 011.5 2zM1 1.5v1a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zm0 4v9a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-9a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zM2 7a1 1 0 011-1h10a1 1 0 011 1v2a1 1 0 01-1 1H3a1 1 0 01-1-1V7zm0 5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1z"/>
                    </svg>
                    目标数据库
                  </label>
                  <div class="info-value">{{ task.target_db || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-diagram-3 me-1" viewBox="0 0 16 16">
                      <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 017.5 2h1A1.5 1.5 0 0110 3.5v1A1.5 1.5 0 018.5 6v1H14a.5.5 0 00.5-.5v-2A.5.5 0 0014 3H6a.5.5 0 00-.5.5v2A.5.5 0 006 6h5.5v-1A1.5 1.5 0 0113 3.5v-1zM14 7H6v2a.5.5 0 00.5.5h7a.5.5 0 00.5-.5V7zm-5 3.5v1a1.5 1.5 0 01-1.5 1.5h-1A1.5 1.5 0 015 11.5v-1A1.5 1.5 0 016.5 9H8a.5.5 0 00.5-.5v-1H2a.5.5 0 00-.5.5v2A.5.5 0 002 11h8a.5.5 0 00.5-.5v-2A.5.5 0 0010 8H5.5v1a1.5 1.5 0 011.5 1.5zm-5 0v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zM2 4.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1z"/>
                    </svg>
                    源Schema
                  </label>
                  <div class="info-value">{{ task.source_schema || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-diagram-3 me-1" viewBox="0 0 16 16">
                      <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 017.5 2h1A1.5 1.5 0 0110 3.5v1A1.5 1.5 0 018.5 6v1H14a.5.5 0 00.5-.5v-2A.5.5 0 0014 3H6a.5.5 0 00-.5.5v2A.5.5 0 006 6h5.5v-1A1.5 1.5 0 0113 3.5v-1zM14 7H6v2a.5.5 0 00.5.5h7a.5.5 0 00.5-.5V7zm-5 3.5v1a1.5 1.5 0 01-1.5 1.5h-1A1.5 1.5 0 015 11.5v-1A1.5 1.5 0 016.5 9H8a.5.5 0 00.5-.5v-1H2a.5.5 0 00-.5.5v2A.5.5 0 002 11h8a.5.5 0 00.5-.5v-2A.5.5 0 0010 8H5.5v1a1.5 1.5 0 011.5 1.5zm-5 0v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5zM2 4.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1z"/>
                    </svg>
                    目标Schema
                  </label>
                  <div class="info-value">{{ task.target_schema || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-box me-1" viewBox="0 0 16 16">
                      <path d="M8.186 1.113a.5.5 0 00-.372 0L1.846 3.5l2.404.961L10.404 2l-2.218-.887zm3.564 1.426L5.596 5 8 5.961 14.154 5l-2.404-.961zm3.25 1.7l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923l6.5 2.6zM7.443.184a1.5 1.5 0 011.114 0l7.129 2.852A.5.5 0 0116 3.5v8.662a1 1 0 01-.629.928l-7.185 2.874a.5.5 0 01-.372 0L.63 13.09a1 1 0 01-.63-.928V3.5a.5.5 0 01.314-.464L7.443.184z"/>
                    </svg>
                    源对象
                  </label>
                  <div class="info-value">{{ task.source_object || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-box me-1" viewBox="0 0 16 16">
                      <path d="M8.186 1.113a.5.5 0 00-.372 0L1.846 3.5l2.404.961L10.404 2l-2.218-.887zm3.564 1.426L5.596 5 8 5.961 14.154 5l-2.404-.961zm3.25 1.7l-6.5 2.6v7.922l6.5-2.6V4.24zM7.5 14.762V6.838L1 4.239v7.923l6.5 2.6zM7.443.184a1.5 1.5 0 011.114 0l7.129 2.852A.5.5 0 0116 3.5v8.662a1 1 0 01-.629.928l-7.185 2.874a.5.5 0 01-.372 0L.63 13.09a1 1 0 01-.63-.928V3.5a.5.5 0 01.314-.464L7.443.184z"/>
                    </svg>
                    目标对象
                  </label>
                  <div class="info-value">{{ task.target_object || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-gear me-1" viewBox="0 0 16 16">
                      <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
                      <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
                    </svg>
                    冲突策略
                  </label>
                  <div class="info-value">{{ getConflictStrategyText(task.conflict_strategy) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-calendar-plus me-1" viewBox="0 0 16 16">
                      <path d="M8 7a.5.5 0 01.5.5V9H10a.5.5 0 010 1H8.5v1.5a.5.5 0 01-1 0V10H6a.5.5 0 010-1h1.5V7.5A.5.5 0 018 7z"/>
                      <path d="M3.5 0a.5.5 0 01.5.5V1h8V.5a.5.5 0 001 0V1h1a2 2 0 012 2v11a2 2 0 01-2 2H2a2 2 0 01-2-2V3a2 2 0 012-2h1V.5a.5.5 0 01.5-.5zM1 4v10a1 1 0 001 1h12a1 1 0 001-1V4H1z"/>
                    </svg>
                    创建时间
                  </label>
                  <div class="info-value">{{ formatDate(task.created_at) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-play-circle me-1" viewBox="0 0 16 16">
                      <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
                      <path d="M6.271 5.055a.5.5 0 01.52.038l3.5 2.5a.5.5 0 010 .814l-3.5 2.5A.5.5 0 016 10.5v-5a.5.5 0 01.271-.445z"/>
                    </svg>
                    开始时间
                  </label>
                  <div class="info-value">{{ formatDate(task.started_at) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-circle me-1" viewBox="0 0 16 16">
                      <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
                      <path d="M10.97 4.97a.235.235 0 00-.02.022L7.477 9.417 5.384 7.323a.75.75 0 00-1.06 1.06L6.97 11.03a.75.75 0 001.079-.02l3.992-4.99a.75.75 0 00-1.071-1.05z"/>
                    </svg>
                    完成时间
                  </label>
                  <div class="info-value">{{ formatDate(task.completed_at) }}</div>
                </div>
              </div>
              
              <div class="progress-section mt-4">
                <label class="form-label">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-bar-chart me-1" viewBox="0 0 16 16">
                    <path d="M4 11a1 1 0 112 0v1a1 1 0 11-2 0v-1zm6-4a1 1 0 112 0v5a1 1 0 11-2 0V7zM7 9a1 1 0 012 0v3a1 1 0 11-2 0V9z"/>
                    <path d="M4 1.5H3a2 2 0 00-2 2V14a2 2 0 002 2h10a2 2 0 002-2V3.5a2 2 0 00-2-2h-1v1h1a1 1 0 011 1V14a1 1 0 01-1 1H3a1 1 0 01-1-1V3.5a1 1 0 011-1h1v-1z"/>
                  </svg>
                  进度
                </label>
                <div class="progress-wrapper">
                  <div class="progress">
                    <div class="progress-bar" :class="getProgressBarClass(task.status)"
                         :style="{ width: task.progress + '%' }"></div>
                  </div>
                  <span class="progress-text">{{ task.progress.toFixed(1) }}%</span>
                </div>
              </div>
              
              <div class="action-buttons mt-4">
                <button v-if="task.status === 'pending'" @click="startTask" 
                        class="btn btn-lg btn-success flex-grow-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-play-fill me-2" viewBox="0 0 16 16">
                    <path d="M11.596 8.697l-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 010 1.393z"/>
                  </svg>
                  开始任务
                </button>
                <button v-if="task.status === 'running'" @click="cancelTask" 
                        class="btn btn-lg btn-warning flex-grow-1">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-x-circle me-2" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 118 1a7 7 0 010 14zm0 1A8 8 0 108 0a8 8 0 000 16z"/>
                    <path d="M4.646 4.646a.5.5 0 01.708 0L8 7.293l2.646-2.647a.5.5 0 01.708.708L8.707 8l2.647 2.646a.5.5 0 01-.708.708L8 8.707l-2.646 2.647a.5.5 0 01-.708-.708L7.293 8 4.646 5.354a.5.5 0 010-.708z"/>
                  </svg>
                  取消任务
                </button>
                <button @click="refreshStatus" class="btn btn-lg btn-outline-info">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-arrow-clockwise me-2" viewBox="0 0 16 16">
                    <path fill-rule="evenodd" d="M8 3a5 5 0 104.546 2.914.5.5 0 01.908-.417A6 6 0 118 2v1z"/>
                    <path d="M8 4.466V.534a.25.25 0 01.41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 018 4.466z"/>
                  </svg>
                  刷新状态
                </button>
                <button @click="deleteTask" class="btn btn-lg btn-outline-danger">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-trash me-2" viewBox="0 0 16 16">
                    <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
                    <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                  </svg>
                  删除任务
                </button>
              </div>
            </div>
          </div>
          
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-terminal me-1" viewBox="0 0 16 16">
                  <path d="M6 9a.5.5 0 01.5-.5h3a.5.5 0 010 1H6.5a.5.5 0 01-.5-.5zM1.5 0h13a1.5 1.5 0 011.5 1.5V13a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5V1.5A1.5 1.5 0 011.5 0zM1 1.5V13a.5.5 0 00.5.5h13a.5.5 0 00.5-.5V1.5a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5z"/>
                  <path d="M3.71 8.86a.5.5 0 01.634-.06l5.663 4.413a.5.5 0 01-.142.854l-5.5-4.22a.5.5 0 01-.055-.987zM5.71 8.86a.5.5 0 01-.634-.06l-5.663 4.413a.5.5 0 01.142.854l5.5-4.22a.5.5 0 01.055-.987z"/>
                </svg>
                日志
              </h5>
            </div>
            <div class="card-body">
              <div class="log-container">
                <pre class="log-content">{{ task.log || '暂无日志' }}</pre>
              </div>
            </div>
          </div>
        </div>
        
        <div class="col-lg-4">
          <div class="card">
            <div class="card-header">
              <h5 class="mb-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-gear me-1" viewBox="0 0 16 16">
                  <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
                  <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
                </svg>
                任务操作
              </h5>
            </div>
            <div class="card-body">
              <div class="mb-4">
                <label class="form-label">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-repeat me-1" viewBox="0 0 16 16">
                    <path d="M11.534 7h3.932a.25.25 0 01.192.41l-1.966 2.36a.25.25 0 01-.384 0l-1.966-2.36a.25.25 0 01.192-.41h3.932a.5.5 0 000-1H11.534a1.5 1.5 0 00-1.5 1.5v3.932a.25.25 0 01-.41.192l-2.36-1.966a.25.25 0 010-.384l2.36-1.966a.25.25 0 01.41.192V8.5a.5.5 0 001 0v-3.932a1.5 1.5 0 00-1.5-1.5zM1 4.5a1.5 1.5 0 011.5-1.5h3.932a.25.25 0 01.192.41l-1.966 2.36a.25.25 0 01-.384 0l-1.966-2.36a.25.25 0 01.192-.41H2.5a.5.5 0 000-1h3.932a1.5 1.5 0 001.5 1.5v3.932a.25.25 0 01-.41.192l-2.36-1.966a.25.25 0 010-.384l2.36-1.966a.25.25 0 01.41.192V8.5a.5.5 0 001 0v-3.932a1.5 1.5 0 00-1.5-1.5z"/>
                  </svg>
                  切换目标数据库
                </label>
                <select v-model="selectedDatabase" class="form-select mb-3">
                  <option value="">请选择数据库</option>
                  <option v-for="db in databases" :key="db" :value="db">{{ db }}</option>
                </select>
                <button @click="switchDatabase" class="btn btn-primary w-100">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-repeat me-1" viewBox="0 0 16 16">
                    <path d="M11.534 7h3.932a.25.25 0 01.192.41l-1.966 2.36a.25.25 0 01-.384 0l-1.966-2.36a.25.25 0 01.192-.41h3.932a.5.5 0 000-1H11.534a1.5 1.5 0 00-1.5 1.5v3.932a.25.25 0 01-.41.192l-2.36-1.966a.25.25 0 010-.384l2.36-1.966a.25.25 0 01.41.192V8.5a.5.5 0 001 0v-3.932a1.5 1.5 0 00-1.5-1.5zM1 4.5a1.5 1.5 0 011.5-1.5h3.932a.25.25 0 01.192.41l-1.966 2.36a.25.25 0 01-.384 0l-1.966-2.36a.25.25 0 01.192-.41H2.5a.5.5 0 000-1h3.932a1.5 1.5 0 001.5 1.5v3.932a.25.25 0 01-.41.192l-2.36-1.966a.25.25 0 010-.384l2.36-1.966a.25.25 0 01.41.192V8.5a.5.5 0 001 0v-3.932a1.5 1.5 0 00-1.5-1.5z"/>
                  </svg>
                  切换数据库
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { migrationTaskApi, databaseApi } from '@/api'
import type { MigrationTask } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const task = ref<MigrationTask | null>(null)
const databases = ref<string[]>([])
const selectedDatabase = ref('')
let statusInterval: number | null = null

const getTaskTypeText = (type: string) => {
  const texts: Record<string, string> = {
    table: '表',
    materialized_view: '物化视图',
    view: '视图',
    routine: '例程',
    all_tables: '所有表',
    view_to_table: '视图数据迁移到表',
    view_to_sqlite: '视图数据迁移到SQLite',
  }
  return texts[type] || type
}

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

const getProgressBarClass = (status: string) => {
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

const getConflictStrategyText = (strategy: string) => {
  const texts: Record<string, string> = {
    error: '遇到冲突时报错',
    replace: '删除并替换已存在对象',
    skip: '跳过已存在对象',
    append: '追加数据（仅适用于表）',
    truncate: '清空表并重新加载数据',
  }
  return texts[strategy] || strategy
}

const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const loadTask = async () => {
  loading.value = true
  try {
    const res = await migrationTaskApi.get(Number(route.params.id))
    task.value = res.data
  } catch (error) {
    console.error('Failed to load task:', error)
  } finally {
    loading.value = false
  }
}

const loadDatabases = async () => {
  if (!task.value?.postgres_connection) return
  
  try {
    const res = await databaseApi.getPostgresDatabases({
      connection_id: task.value.postgres_connection,
    })
    databases.value = res.data.databases || []
  } catch (error) {
    console.error('Failed to load databases:', error)
  }
}

const startTask = async () => {
  try {
    await migrationTaskApi.start(Number(route.params.id))
    await loadTask()
  } catch (error) {
    console.error('Failed to start task:', error)
  }
}

const cancelTask = async () => {
  if (!confirm('确定要取消此任务吗？')) return
  try {
    await migrationTaskApi.cancel(Number(route.params.id))
    await loadTask()
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const deleteTask = async () => {
  if (!confirm('确定要删除此任务吗？')) return
  try {
    await migrationTaskApi.delete(Number(route.params.id))
    router.push('/tasks')
  } catch (error) {
    console.error('Failed to delete task:', error)
  }
}

const refreshStatus = async () => {
  await loadTask()
}

const switchDatabase = async () => {
  if (!selectedDatabase.value) {
    alert('请选择数据库')
    return
  }
  
  try {
    await migrationTaskApi.switchDatabase(Number(route.params.id), {
      postgres_database: selectedDatabase.value,
    })
    await loadTask()
    alert('切换成功')
  } catch (error) {
    console.error('Failed to switch database:', error)
    alert('切换失败')
  }
}

onMounted(async () => {
  await loadTask()
  await loadDatabases()
  
  if (task.value?.status === 'running') {
    statusInterval = window.setInterval(async () => {
      await loadTask()
      if (task.value?.status !== 'running' && statusInterval) {
        clearInterval(statusInterval)
        statusInterval = null
      }
    }, 3000)
  }
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
})
</script>

<style scoped>
.task-detail-view {
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

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-label {
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
}

.info-value {
  color: #2d3748;
  font-size: 1rem;
  padding: 0.5rem 0.75rem;
  background: #f7fafc;
  border-radius: 0.5rem;
  border-left: 3px solid #667eea;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-weight: 500;
  border-radius: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: white;
  margin-right: 0.5rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.progress-section {
  padding: 1.5rem;
  background: #f7fafc;
  border-radius: 0.5rem;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress {
  flex-grow: 1;
  height: 1.5rem;
  border-radius: 0.75rem;
  background: #e9ecef;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 0.75rem;
}

.progress-text {
  font-weight: 600;
  color: #667eea;
  min-width: 60px;
  text-align: right;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-lg {
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  border-radius: 0.5rem;
  transition: all 0.3s ease;
}

.btn-lg:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

.log-container {
  background: #1e1e1e;
  border-radius: 0.5rem;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
}

.log-content {
  color: #d4d4d4;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
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

.spinner-border {
  width: 3rem;
  height: 3rem;
}
</style>
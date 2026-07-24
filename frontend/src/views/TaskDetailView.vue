<template>
  <div class="task-detail-view">
    <PageHeader
      title="任务详情"
      subtitle="查看和管理迁移任务的详细信息"
      icon="bi-file-earmark-text"
    >
      <template #actions>
        <router-link to="/tasks" class="btn btn-sm btn-outline-secondary">
          <i class="bi bi-arrow-left"></i>
          返回列表
        </router-link>
      </template>
    </PageHeader>
    
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="mt-3 text-muted">加载任务详情...</p>
    </div>
    
    <div v-else-if="task">
      <div v-if="task.status === 'aborted'" class="alert alert-danger d-flex align-items-start mb-4" role="alert">
        <i class="bi bi-exclamation-octagon-fill me-2 flex-shrink-0" style="font-size: 1.25rem;"></i>
        <div>
          <strong>异常停止</strong>
          <p class="mb-0 small mt-1">
            迁移进程已中断，任务未正常结束。常见原因：服务重启、进程被终止、Worker 异常退出或开发服务器热重载。
            <template v-if="showResumeHint">可点击「继续迁移」从断点恢复，或「重新运行」从头执行。</template>
            <template v-else>可查看下方日志后重新运行。</template>
          </p>
        </div>
      </div>
      <div v-else-if="task.status === 'partial'" class="alert alert-warning d-flex align-items-start mb-4" role="alert">
        <i class="bi bi-pause-circle-fill me-2 flex-shrink-0" style="font-size: 1.25rem;"></i>
        <div>
          <strong>迁移已中断</strong>
          <p class="mb-0 small mt-1">
            任务未全部完成（可能为用户取消、部分表失败或进程退出）。
            <template v-if="showResumeHint">已完成的表将跳过，可点击「继续迁移」从断点恢复。</template>
            <template v-else>可查看日志后使用「重新运行」。</template>
          </p>
        </div>
      </div>
      <div v-else-if="task.status === 'exported'" class="alert alert-info d-flex align-items-start mb-4" role="alert">
        <i class="bi bi-file-earmark-code me-2 flex-shrink-0" style="font-size: 1.25rem;"></i>
        <div>
          <strong>已导出待人工处理</strong>
          <p class="mb-0 small mt-1">
            触发器源码与 PL/pgSQL 改写模板已写入下方日志，目标库未自动创建触发器。请人工完成改写后在 PolarDB-PG 执行。
          </p>
        </div>
      </div>
      <div v-else-if="task.status === 'canceled'" class="alert alert-secondary d-flex align-items-start mb-4" role="alert">
        <i class="bi bi-slash-circle me-2 flex-shrink-0" style="font-size: 1.25rem;"></i>
        <div>
          <strong>已取消</strong>
          <p class="mb-0 small mt-1">
            任务已被手动取消。
            <template v-if="showResumeHint">若需保留已迁移数据并继续，可点击「继续迁移」。</template>
          </p>
        </div>
      </div>
      <div class="row g-4">
        <div class="col-12">
          <section class="task-detail-section mb-4">
            <h5 class="section-title mb-3">
              <i class="bi bi-info-circle me-1" style="font-size: 20px;"></i>
              {{ task.name }}
            </h5>
              <div class="info-grid">
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-tag me-1" style="font-size: 16px;"></i>
                    任务类型
                  </label>
                  <div class="info-value">{{ getTaskTypeText(task.task_type) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-activity me-1" style="font-size: 16px;"></i>
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
                    <i class="bi bi-database me-1" style="font-size: 16px;"></i>
                    源数据库
                  </label>
                  <div class="info-value">{{ task.source_db || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-server me-1" style="font-size: 16px;"></i>
                    目标概览
                  </label>
                  <div class="info-value">{{ task.target_db || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    源Schema
                  </label>
                  <div class="info-value">{{ task.source_schema || '-' }}</div>
                </div>
                
                <!-- PolarDB 目标：连接、数据库、Schema -->
                <template v-if="task.task_type !== 'view_to_sqlite' && task.postgres_connection_name">
                  <div class="info-item">
                    <label class="info-label">
                      <i class="bi bi-link-45deg me-1" style="font-size: 16px;"></i>
                    PolarDB/PostgreSQL 连接
                    </label>
                    <div class="info-value">{{ task.postgres_connection_name || '-' }}</div>
                  </div>
                  <div class="info-item">
                    <label class="info-label">
                      <i class="bi bi-database me-1" style="font-size: 16px;"></i>
                    目标数据库
                    </label>
                    <div class="info-value">{{ task.postgres_database || '-' }}</div>
                  </div>
                  <div class="info-item">
                    <label class="info-label">
                      <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    目标 Schema
                    </label>
                    <div class="info-value">{{ task.target_schema || '-' }}</div>
                  </div>
                </template>
                <div v-else class="info-item">
                  <label class="info-label">
                    <i class="bi bi-diagram-3 me-1" style="font-size: 16px;"></i>
                    目标Schema
                  </label>
                  <div class="info-value">{{ task.target_schema || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-box me-1" style="font-size: 16px;"></i>
                    源对象（表/视图）
                  </label>
                  <div class="info-value">
                    <template v-if="task.source_objects && task.source_objects.trim()">
                      <div v-if="sourceObjectsList.length > sourceListInlineMax" class="source-objects-compact">
                        <div class="text-muted small mb-1">
                          共 {{ sourceObjectsList.length }} 个对象（列表可滚动，避免一次渲染数千行顿卡）
                        </div>
                        <pre class="source-objects-monolist">{{ sourceObjectsMonolist }}</pre>
                      </div>
                      <template v-else>
                        <span v-for="(obj, i) in sourceObjectsList" :key="i">{{ obj }}{{ i < sourceObjectsList.length - 1 ? '、' : '' }}</span>
                      </template>
                    </template>
                    <template v-else>{{ task.source_object || '-' }}</template>
                  </div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-box me-1" style="font-size: 16px;"></i>
                    目标对象
                  </label>
                  <div class="info-value">{{ task.target_object || '-' }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-gear me-1" style="font-size: 16px;"></i>
                    冲突策略
                  </label>
                  <div class="info-value">{{ getConflictStrategyText(task.conflict_strategy) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-calendar-plus me-1" style="font-size: 16px;"></i>
                    创建时间
                  </label>
                  <div class="info-value">{{ formatDate(task.created_at) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-play-circle me-1" style="font-size: 16px;"></i>
                    开始时间
                  </label>
                  <div class="info-value">{{ formatDate(task.started_at) }}</div>
                </div>
                
                <div class="info-item">
                  <label class="info-label">
                    <i class="bi bi-check-circle me-1" style="font-size: 16px;"></i>
                    完成时间
                  </label>
                  <div class="info-value">{{ formatDate(task.completed_at) }}</div>
                </div>
              </div>
              
              <div class="progress-section mt-4">
                <label class="form-label">
                  <i class="bi bi-bar-chart me-1" style="font-size: 16px;"></i>
                  进度
                </label>
                <div class="progress-wrapper">
                  <div class="progress">
                    <div class="progress-bar" :class="getProgressBarClass(task.status)"
                         :style="{ width: task.progress + '%' }"></div>
                  </div>
                  <span class="progress-text">{{ task.progress.toFixed(1) }}%</span>
                </div>
                <!-- 多表批量或「所有表」：view_progress 为 { current, total, current_table, failed_count } -->
                <div v-if="allTablesProgress" class="all-tables-progress mt-3 p-3 rounded bg-light">
                  <div class="d-flex align-items-center mb-1">
                    <i class="bi bi-collection me-2 text-primary"></i>
                    <span class="text-muted">当前进度：</span>
                    <strong class="ms-1">第 {{ allTablesProgress.current }} / {{ allTablesProgress.total }} 张表</strong>
                  </div>
                  <div v-if="allTablesProgress.current_table" class="text-muted small">
                    正在迁移：<code>{{ allTablesProgress.current_table }}</code>
                  </div>
                  <div v-if="parallelRunningTables.length" class="text-primary small mt-1">
                    <i class="bi bi-layers me-1"></i>
                    并行进行中（{{ parallelRunningTables.length }} 张）：
                    <code>{{ parallelRunningPreview }}</code>
                  </div>
                  <div v-if="completedTablesCount > 0" class="text-success small mt-1">
                    已完成 {{ completedTablesCount }} 张表（继续迁移时将跳过）
                  </div>
                  <div v-if="allTablesProgress.failed_count != null && allTablesProgress.failed_count > 0" class="text-warning small mt-1">
                    已失败 {{ allTablesProgress.failed_count }} 张表
                  </div>
                  <!-- 当前正在迁移的表：行级进度条 -->
                  <div v-if="currentTableProgress" class="current-table-progress mt-3 pt-3 border-top">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                      <span class="small fw-medium">
                        <i class="bi bi-table me-1 text-primary"></i>当前表进度
                      </span>
                      <span class="view-progress-stats text-muted small">
                        <template v-if="currentTableProgress.total_rows != null">
                          已迁移 <strong>{{ formatNumber(currentTableProgress.migrated_rows) }}</strong>
                          / {{ formatNumber(currentTableProgress.total_rows) }} 行
                        </template>
                        <template v-else>
                          已迁移 <strong>{{ formatNumber(currentTableProgress.migrated_rows) }}</strong> 行
                        </template>
                        · {{ (currentTableProgress.progress ?? 0).toFixed(1) }}%
                      </span>
                    </div>
                    <div class="progress thin">
                      <div
                        class="progress-bar progress-bar-striped progress-bar-animated"
                        :class="getProgressBarClass(task.status)"
                        :style="{ width: (currentTableProgress.progress ?? 0) + '%' }"
                      ></div>
                    </div>
                  </div>
                </div>
                <!-- 整库一键迁移：多阶段编排进度 -->
                <div v-else-if="fullDatabaseProgress" class="full-db-progress mt-3 p-3 rounded bg-light">
                  <div class="d-flex align-items-center mb-2">
                    <i class="bi bi-diagram-3 me-2 text-primary"></i>
                    <strong>整库编排进度</strong>
                  </div>
                  <div class="d-flex flex-wrap gap-2 mb-2">
                    <span
                      v-for="ph in fullDatabaseProgress.phases"
                      :key="ph"
                      class="badge"
                      :class="phaseBadgeClass(ph)"
                    >{{ phaseLabel(ph) }}</span>
                  </div>
                  <div v-if="fullDatabaseProgress.currentSchema" class="text-muted small">
                    当前 Schema：<code>{{ fullDatabaseProgress.currentSchema }}</code>
                    （{{ (fullDatabaseProgress.schemaIndex ?? 0) + 1 }} / {{ fullDatabaseProgress.schemaTotal }}）
                  </div>
                  <div v-if="fullDatabaseProgress.completedCount" class="text-success small mt-1">
                    已完成对象 {{ fullDatabaseProgress.completedCount }} 个（续传时将跳过）
                  </div>
                  <div v-if="fullDatabaseProgress.failedCount" class="text-warning small mt-1">
                    失败对象 {{ fullDatabaseProgress.failedCount }} 个
                  </div>
                  <ul v-if="fullDatabaseProgress.failedObjects?.length" class="small text-danger mb-0 mt-2 ps-3">
                    <li v-for="(fo, i) in fullDatabaseProgress.failedObjects.slice(0, 5)" :key="i">
                      [{{ fo.phase }}] {{ fo.object }}: {{ fo.error }}
                    </li>
                    <li v-if="fullDatabaseProgress.failedObjects.length > 5" class="text-muted">
                      … 另有 {{ fullDatabaseProgress.failedObjects.length - 5 }} 个
                    </li>
                  </ul>
                </div>
                <!-- 表/视图级进度：非「所有表」汇总格式时显示各对象 progress、total_rows、migrated_rows -->
                <div v-else-if="viewProgressEntries.length" class="view-progress-list mt-3">
                  <div v-for="[objName, info] in viewProgressEntries" :key="objName" class="view-progress-item">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                      <span class="view-progress-name">
                        <i class="bi bi-table me-1"></i>{{ objName }}
                      </span>
                      <span class="view-progress-stats text-muted small">
                        <template v-if="info && typeof info === 'object' && info.total_rows != null">
                          已迁移 <strong>{{ formatNumber(info.migrated_rows) }}</strong> / {{ formatNumber(info.total_rows) }} 行
                        </template>
                        <template v-else-if="info && typeof info === 'object'">
                          已迁移 <strong>{{ formatNumber(info.migrated_rows) }}</strong> 行
                        </template>
                        <template v-else>—</template>
                        <template v-if="info && typeof info === 'object'"> · {{ (info.progress ?? 0).toFixed(1) }}%</template>
                      </span>
                    </div>
                    <div v-if="info && typeof info === 'object' && (info.progress != null || info.total_rows != null)" class="progress thin">
                      <div class="progress-bar" :class="getProgressBarClass(task.status)"
                           :style="{ width: (info.progress ?? 0) + '%' }"></div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="action-buttons mt-4">
                <button v-if="task.status === 'pending'" @click="startTask" 
                        class="btn btn-sm btn-success flex-grow-1">
                  <i class="bi bi-play-fill me-2" style="font-size: 18px;"></i>
                  开始任务
                </button>
                <button v-if="task.status === 'running'" @click="cancelTask" 
                        class="btn btn-sm btn-warning flex-grow-1">
                  <i class="bi bi-x-circle me-2" style="font-size: 18px;"></i>
                  取消任务
                </button>
                <button v-if="canResume(task.status)" @click="resumeTask" 
                        class="btn btn-sm btn-success flex-grow-1">
                  <i class="bi bi-skip-forward-fill me-2" style="font-size: 18px;"></i>
                  继续迁移
                </button>
                <button v-if="canRerun(task.status)" @click="restartTask" 
                        class="btn btn-sm btn-primary flex-grow-1">
                  <i class="bi bi-arrow-repeat me-2" style="font-size: 18px;"></i>
                  重新运行
                </button>
                <button @click="refreshStatus" class="btn btn-sm btn-outline-info">
                  <i class="bi bi-arrow-clockwise me-2" style="font-size: 18px;"></i>
                  刷新状态
                </button>
                <button @click="deleteTask" class="btn btn-sm btn-outline-danger">
                  <i class="bi bi-trash me-2" style="font-size: 18px;"></i>
                  删除任务
                </button>
              </div>

              <!-- v2.4: 数据库对比与立即增量同步按钮 -->
              <div v-if="canCompare || canSyncNow" class="action-buttons mt-2">
                <button v-if="canCompare" @click="comparePreview" :disabled="diffLoading"
                        class="btn btn-sm btn-outline-primary flex-grow-1">
                  <i class="bi bi-arrow-left-right me-2" style="font-size: 18px;"></i>
                  {{ diffLoading ? '对比中...' : '对比预览' }}
                </button>
                <button v-if="canSyncNow" @click="syncNow" :disabled="syncing || syncDisabledByRunning"
                        :title="syncDisabledByRunning ? '任务执行中,暂不可立即同步' : ''"
                        class="btn btn-sm btn-outline-success flex-grow-1">
                  <i class="bi bi-lightning-charge me-2" style="font-size: 18px;"></i>
                  {{ syncing ? '同步中...' : (syncDisabledByRunning ? '执行中不可同步' : '立即增量同步') }}
                </button>
              </div>

              <!-- v2.4: 对比结果展示 -->
              <div v-if="diffResult" class="diff-result-card mt-3 p-3" style="background: var(--bs-tertiary-bg, #f8f9fa); border: 1px solid var(--bs-border-color, #dee2e6); border-radius: 4px;">
                <div class="d-flex justify-content-between align-items-center mb-2">
                  <strong><i class="bi bi-clipboard-data me-1"></i>对比结果</strong>
                  <button type="button" class="btn-close btn-sm" @click="diffResult = null"></button>
                </div>
                <table class="table table-sm mb-2">
                  <tbody>
                    <tr><td class="text-muted" style="width:140px;">源表</td><td>{{ diffResult.source_schema }}.{{ diffResult.table_name }} ({{ diffResult.source_count }} 行)</td></tr>
                    <tr><td class="text-muted">目标表</td><td>{{ diffResult.target_schema }}.{{ diffResult.pg_table }} ({{ diffResult.target_count }} 行)</td></tr>
                    <tr v-if="diffResult.target_exists"><td class="text-muted">主键列</td><td>{{ diffResult.pk_columns.join(', ') || '(无)' }}</td></tr>
                    <tr v-if="diffResult.to_insert !== null"><td class="text-success">待插入(源有目标无)</td><td>{{ diffResult.to_insert }} 行</td></tr>
                    <tr v-if="diffResult.to_delete !== null"><td class="text-danger">待删除(目标有源无)</td><td>{{ diffResult.to_delete }} 行</td></tr>
                    <tr v-if="diffResult.common !== null"><td class="text-muted">两端共存</td><td>{{ diffResult.common }} 行</td></tr>
                  </tbody>
                </table>
                <div v-if="diffResult.note" class="small text-muted"><i class="bi bi-info-circle me-1"></i>{{ diffResult.note }}</div>
              </div>
          </section>

          <section v-if="migrationReport && isTerminalStatus(task.status)" class="task-detail-section mb-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h5 class="section-title mb-0">
                <i class="bi bi-file-earmark-bar-graph me-1" style="font-size: 20px;"></i>
                迁移报告
              </h5>
              <button type="button" class="btn btn-sm btn-outline-secondary" @click="downloadReport">
                <i class="bi bi-download me-1"></i>导出 JSON
              </button>
            </div>
            <div v-if="migrationReport.manual_review_items?.length" class="alert alert-warning py-2 small">
              <strong>需人工审查 {{ migrationReport.summary?.manual_review_count ?? 0 }} 项</strong>
              <ul class="mb-0 mt-2 ps-3">
                <li v-for="(item, idx) in (migrationReport.manual_review_items as string[]).slice(0, 8)" :key="idx">{{ item }}</li>
              </ul>
            </div>
            <div v-if="migrationReport.row_checks?.length" class="table-responsive">
              <table class="table table-sm table-bordered mb-0">
                <thead><tr><th>对象</th><th>源行数</th><th>目标行数</th><th>差异</th><th>结果</th></tr></thead>
                <tbody>
                  <tr v-for="(row, idx) in (migrationReport.row_checks as any[]).slice(0, 20)" :key="idx">
                    <td><code>{{ row.object }}</code></td>
                    <td>{{ row.source_rows }}</td>
                    <td>{{ row.target_rows }}</td>
                    <td>{{ row.row_diff }}</td>
                    <td><span :class="row.passed ? 'text-success' : 'text-danger'">{{ row.passed ? '通过' : '失败' }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="text-muted small mb-0">暂无行数校验明细。</p>
          </section>
          
          <section class="task-detail-section mb-4">
            <h5 class="section-title mb-3">
              <i class="bi bi-terminal me-1" style="font-size: 20px;"></i>
              日志
              <span v-if="task.log" class="text-muted small ms-2">({{ logTotalLines }} 行)</span>
            </h5>
            <div class="log-toolbar mb-2">
              <div class="input-group input-group-sm">
                <span class="input-group-text"><i class="bi bi-funnel"></i></span>
                <select v-model="logLevelFilter" class="form-select">
                  <option value="">全部级别</option>
                  <option value="STEP">STEP · 阶段</option>
                  <option value="INFO">INFO · 信息</option>
                  <option value="OK">OK · 成功</option>
                  <option value="WARN">WARN · 警告</option>
                  <option value="ERROR">ERROR · 错误</option>
                  <option value="DATA">DATA · 数据</option>
                  <option value="SQL">SQL · 语句</option>
                  <option value="META">META · 元数据</option>
                </select>
                <input v-model="logSearchTerm" type="text" class="form-control" placeholder="搜索日志内容...">
              </div>
              <div class="btn-group btn-group-sm ms-2">
                <button type="button" class="btn btn-outline-secondary" :class="{ active: autoScrollLog }" @click="autoScrollLog = !autoScrollLog" title="自动滚动到底部">
                  <i class="bi bi-arrow-down-circle"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary" @click="scrollLogToBottom" title="跳到底部">
                  <i class="bi bi-chevron-double-down"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary" @click="copyLog" title="复制全文">
                  <i class="bi bi-clipboard"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary" @click="downloadLog" title="下载日志">
                  <i class="bi bi-download"></i>
                </button>
              </div>
            </div>
            <div ref="logContainer" class="log-container">
              <template v-if="filteredLogLines.length">
                <div
                  v-for="(line, idx) in filteredLogLines"
                  :key="idx"
                  class="log-line"
                  :class="'log-' + line.level.toLowerCase()"
                >
                  <span class="log-level-tag">[{{ line.level }}]</span>
                  <span class="log-text">{{ line.text }}</span>
                </div>
              </template>
              <p v-else-if="task.log" class="text-muted small p-3 mb-0">没有匹配的日志行</p>
              <p v-else class="text-muted small p-3 mb-0">暂无日志</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { migrationTaskApi } from '@/api'
import type { MigrationTask, TableDiffResult } from '@/api'
import PageHeader from '@/components/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const task = ref<MigrationTask | null>(null)
let statusInterval: ReturnType<typeof setInterval> | null = null

// ===== v2.4: 数据库对比与立即增量同步 =====
const diffResult = ref<TableDiffResult | null>(null)
const diffLoading = ref(false)
const syncing = ref(false)
/** 对比预览按钮显示条件:表类型任务且有 PG 连接 */
const canCompare = computed(() => {
  if (!task.value) return false
  return !!task.value.postgres_connection
    && ['table', 'view_to_table', 'all_tables', 'table_batch'].includes(task.value.task_type)
})
/** 立即同步按钮显示条件:增量模式为 pk_mirror(任务执行中时按钮禁用而非隐藏) */
const canSyncNow = computed(() => {
  return !!task.value && task.value.incremental_mode === 'pk_mirror'
})
/** 任务正在执行中,立即同步需禁用以避免并发主键对齐冲突 */
const syncDisabledByRunning = computed(() => {
  return !!task.value && task.value.status === 'running'
})
/** 执行中任务自动刷新间隔（毫秒） */
const POLL_INTERVAL_MS = 3000

// ===== 日志面板相关 =====
const logLevelFilter = ref('')
const logSearchTerm = ref('')
const autoScrollLog = ref(true)
const logContainer = ref<HTMLElement | null>(null)

interface ParsedLogLine {
  level: string
  text: string
}

const LEVEL_REGEX = /^\[(STEP|INFO|OK|WARN|ERROR|DATA|SQL|META)\]\s?(.*)$/

/** 把 task.log 拆成带 level 的行列表 */
const parsedLogLines = computed<ParsedLogLine[]>(() => {
  const text = task.value?.log || ''
  if (!text) return []
  return text.split('\n').map(line => {
    const m = line.match(LEVEL_REGEX)
    if (m) return { level: m[1], text: m[2] }
    // 旧格式（无 [LEVEL] 前缀）：依据内容启发式判断
    const upper = line.toUpperCase()
    if (line.startsWith('错误') || upper.includes('失败') || upper.includes('FAILED')) {
      return { level: 'ERROR', text: line }
    }
    if (line.startsWith('警告') || upper.includes('WARN')) {
      return { level: 'WARN', text: line }
    }
    if (line.startsWith('成功') || upper.includes('SUCCESS') || upper.includes('校验通过')) {
      return { level: 'OK', text: line }
    }
    return { level: 'INFO', text: line }
  })
})

const logTotalLines = computed(() => parsedLogLines.value.length)

const filteredLogLines = computed<ParsedLogLine[]>(() => {
  let list = parsedLogLines.value
  if (logLevelFilter.value) {
    list = list.filter(l => l.level === logLevelFilter.value)
  }
  if (logSearchTerm.value.trim()) {
    const term = logSearchTerm.value.trim().toLowerCase()
    list = list.filter(l => l.text.toLowerCase().includes(term))
  }
  // 限制最多展示行数，避免大量日志拖慢渲染
  const MAX = 2000
  if (list.length > MAX) {
    return list.slice(-MAX)
  }
  return list
})

function scrollLogToBottom() {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

async function copyLog() {
  const text = task.value?.log || ''
  if (!text) {
    alert('暂无日志可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    alert('日志已复制到剪贴板')
  } catch {
    // 回退方案
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    alert('日志已复制到剪贴板')
  }
}

function downloadLog() {
  const text = task.value?.log || ''
  if (!text) {
    alert('暂无日志可下载')
    return
  }
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `migration_log_task_${task.value?.id ?? 'unknown'}.log`
  a.click()
  URL.revokeObjectURL(url)
}

// 日志更新时自动滚动到底部
watch(() => task.value?.log, () => {
  if (autoScrollLog.value) scrollLogToBottom()
})

watch(autoScrollLog, v => {
  if (v) scrollLogToBottom()
})

// 源对象列表（表/视图）：来自 source_objects 或 source_object
const sourceListInlineMax = 40

const sourceObjectsList = computed(() => {
  if (!task.value) return []
  const so = task.value.source_objects?.trim()
  if (so) return so.split(/[,，]/).map((s: string) => s.trim()).filter(Boolean)
  if (task.value.source_object?.trim()) return [task.value.source_object.trim()]
  return []
})

/** 大量表名时用换行拼接，配合 pre 滚动，比数千个 span 轻量 */
const sourceObjectsMonolist = computed(() => sourceObjectsList.value.join('\n'))

// 「所有表」任务进度：view_progress 为 { current, total, current_table, failed_count } 时使用
const ALL_TABLES_KEYS = [
  'current', 'total', 'current_table', 'failed_count', 'completed_tables',
  'running_tables', 'parallel_workers',
]
const allTablesProgress = computed(() => {
  const vp = task.value?.view_progress
  if (vp == null || typeof vp !== 'object' || Array.isArray(vp)) return null
  const raw = typeof vp === 'string' ? (() => { try { return JSON.parse(vp) } catch { return null } })() : vp
  if (raw == null || typeof raw !== 'object') return null
  if (raw.current != null && raw.total != null) {
    return {
      current: Number(raw.current),
      total: Number(raw.total),
      current_table: raw.current_table ?? '',
      failed_count: raw.failed_count != null ? Number(raw.failed_count) : 0,
    }
  }
  return null
})

const parallelRunningTables = computed(() => {
  let vp = task.value?.view_progress
  if (vp == null) return [] as string[]
  if (typeof vp === 'string') {
    try { vp = JSON.parse(vp) } catch { return [] }
  }
  if (typeof vp !== 'object' || Array.isArray(vp)) return []
  const rt = (vp as Record<string, unknown>).running_tables
  return Array.isArray(rt) ? rt.map(String) : []
})

const parallelRunningPreview = computed(() => {
  const list = parallelRunningTables.value
  if (!list.length) return ''
  if (list.length <= 4) return list.join(', ')
  return `${list.slice(0, 4).join(', ')} …`
})

const completedTablesCount = computed(() => {
  let vp = task.value?.view_progress
  if (vp == null) return 0
  if (typeof vp === 'string') {
    try { vp = JSON.parse(vp) } catch { return 0 }
  }
  if (typeof vp !== 'object' || Array.isArray(vp)) return 0
  const list = (vp as Record<string, unknown>).completed_tables
  return Array.isArray(list) ? list.length : 0
})

/** 当前正在迁移的表行级进度（所有表 / 多表批量任务） */
const currentTableProgress = computed(() => {
  const at = allTablesProgress.value
  if (!at?.current_table) return null
  let vp = task.value?.view_progress
  if (vp == null) return null
  if (typeof vp === 'string') {
    try {
      vp = JSON.parse(vp)
    } catch {
      return null
    }
  }
  if (typeof vp !== 'object' || Array.isArray(vp)) return null
  const info = (vp as Record<string, unknown>)[at.current_table]
  if (!info || typeof info !== 'object' || Array.isArray(info)) return null
  const row = info as Record<string, number | undefined>
  return {
    name: at.current_table,
    progress: row.progress ?? 0,
    total_rows: row.total_rows,
    migrated_rows: row.migrated_rows ?? 0,
  }
})

// view_progress 条目列表，用于展示每个表/视图的 progress、total_rows、migrated_rows（排除「所有表」汇总字段）
const viewProgressEntries = computed(() => {
  let vp = task.value?.view_progress
  if (vp == null) return []
  if (typeof vp === 'string') {
    try {
      vp = JSON.parse(vp)
    } catch {
      return []
    }
  }
  if (typeof vp !== 'object' || Array.isArray(vp)) return []
  return Object.entries(vp).filter(([k]) => !ALL_TABLES_KEYS.includes(k)) as [string, any][]
})

const formatNumber = (n?: number | null) => {
  if (n == null || Number.isNaN(n)) return '-'
  return Number(n).toLocaleString('zh-CN')
}

/** 支持断点续传的任务类型 */
const RESUMABLE_TASK_TYPES = ['all_tables', 'table', 'full_schema', 'full_database', 'table_batch'] as const

const FULL_DB_PHASE_LABELS: Record<string, string> = {
  prepare: '准备环境',
  sequences: '序列',
  tables: '物理表',
  views: '视图',
  materialized_views: '物化视图',
  triggers: '触发器',
  routines: '例程',
  done: '完成',
}

const getTaskTypeText = (type: string) => {
  const texts: Record<string, string> = {
    table: '表',
    materialized_view: '物化视图',
    view: '视图',
    routine: '例程',
    all_tables: '所有表',
    full_schema: '全Schema编排',
    full_database: '整库一键迁移',
    table_batch: '表级批量迁移',
    view_to_table: '视图数据迁移到表',
    view_to_sqlite: '视图数据迁移到SQLite',
    sequence: '序列',
    trigger: '触发器',
  }
  return texts[type] || type
}

/** 整库迁移多阶段进度 */
const fullDatabaseProgress = computed(() => {
  if (task.value?.task_type !== 'full_database') return null
  let vp = task.value?.view_progress
  if (vp == null) return null
  if (typeof vp === 'string') {
    try { vp = JSON.parse(vp) } catch { return null }
  }
  if (typeof vp !== 'object' || Array.isArray(vp)) return null
  const row = vp as Record<string, unknown>
  if (row.orchestration !== 'full_database') return null
  const schemas = row.schemas as string[] | undefined
  const schemaIndex = row.schema_index as number | undefined
  const completed = row.completed_objects as string[] | undefined
  const failed = row.failed_objects as { object: string; phase: string; error: string }[] | undefined
  return {
    phase: String(row.phase || ''),
    phases: (row.phases as string[]) || Object.keys(FULL_DB_PHASE_LABELS),
    currentSchema: schemaIndex != null && schemas ? schemas[schemaIndex] : null,
    schemaIndex,
    schemaTotal: schemas?.length ?? 0,
    completedCount: completed?.length ?? 0,
    failedCount: failed?.length ?? 0,
    failedObjects: failed || [],
  }
})

const phaseLabel = (ph: string) => FULL_DB_PHASE_LABELS[ph] || ph

const phaseBadgeClass = (ph: string) => {
  const cur = fullDatabaseProgress.value?.phase
  if (ph === cur) return 'bg-primary'
  const phases = fullDatabaseProgress.value?.phases || []
  const curIdx = phases.indexOf(cur || '')
  const idx = phases.indexOf(ph)
  if (idx >= 0 && curIdx >= 0 && idx < curIdx) return 'bg-success'
  if (ph === 'done' && cur === 'done') return 'bg-success'
  return 'bg-secondary'
}

const getStatusBadgeClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'bg-secondary',
    running: 'bg-primary',
    completed: 'bg-success',
    failed: 'bg-danger',
    partial: 'bg-warning',
    canceled: 'bg-dark',
    aborted: 'bg-danger',
    exported: 'bg-info',
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
    aborted: 'bg-danger',
    exported: 'bg-info',
  }
  return classes[status] || 'bg-secondary'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    partial: '已中断',
    canceled: '已取消',
    aborted: '异常停止',
    exported: '已导出待处理',
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

/**
 * 加载任务详情
 * @param showLoading 是否显示全屏加载（轮询刷新时传 false，避免整页闪烁）
 */
const loadTask = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const res = await migrationTaskApi.get(Number(route.params.id), { reconcile: true })
    const data = res.data
    // 若已有任务数据且为后台刷新：只更新会变的字段，减少整块 DOM 重绘
    if (!showLoading && task.value && data) {
      task.value.status = data.status
      task.value.progress = data.progress ?? task.value.progress
      task.value.log = data.log
      task.value.view_progress = data.view_progress
      task.value.started_at = data.started_at
      task.value.completed_at = data.completed_at
      task.value.cancel_requested = data.cancel_requested
    } else {
      task.value = data
    }
    ensureStatusPolling()
  } catch (error) {
    console.error('Failed to load task:', error)
  } finally {
    if (showLoading) loading.value = false
  }
}

/** 将接口返回的进度/状态合并到当前任务（轮询共用） */
const applyTaskPollData = (data: Record<string, unknown>) => {
  if (!task.value || !data) return
  if (data.status != null) task.value.status = String(data.status)
  if (data.progress != null) task.value.progress = Number(data.progress)
  if (data.view_progress != null) task.value.view_progress = data.view_progress
  if (data.log) task.value.log = String(data.log)
  if (data.started_at != null) task.value.started_at = String(data.started_at)
  if (data.completed_at != null) task.value.completed_at = String(data.completed_at)
  if (data.cancel_requested != null) task.value.cancel_requested = Boolean(data.cancel_requested)
}

/** 轻量轮询：/api/tasks/{id}/status/?light=1；失败时回退 GET /api/tasks/{id}/ */
const pollTaskStatus = async () => {
  const taskId = Number(route.params.id)
  if (!taskId || Number.isNaN(taskId)) return
  try {
    const res = await migrationTaskApi.statusLight(taskId)
    applyTaskPollData(res.data as Record<string, unknown>)
  } catch (error) {
    console.warn('轻量状态轮询失败，回退完整详情:', error)
    try {
      const res = await migrationTaskApi.get(taskId)
      applyTaskPollData(res.data as Record<string, unknown>)
    } catch (e2) {
      console.error('任务详情轮询失败:', e2)
    }
  }
}

const stopStatusPolling = () => {
  if (statusInterval) {
    clearInterval(statusInterval)
    statusInterval = null
  }
}

/** 任务为 running 时启动定时轮询 */
const startStatusPolling = () => {
  if (statusInterval || task.value?.status !== 'running') return
  void pollTaskStatus()
  statusInterval = setInterval(async () => {
    await pollTaskStatus()
    if (task.value?.status !== 'running') {
      stopStatusPolling()
      await loadTask(false)
    }
  }, POLL_INTERVAL_MS)
}

const ensureStatusPolling = () => {
  if (task.value?.status === 'running') startStatusPolling()
  else stopStatusPolling()
}

const canRerun = (status: string) =>
  ['failed', 'completed', 'partial', 'canceled', 'aborted', 'exported'].includes(status)

const isTerminalStatus = (status: string) => canRerun(status)

const migrationReport = computed(() => {
  const r = task.value?.migration_report
  return r && typeof r === 'object' ? (r as any) : null
})

const downloadReport = async () => {
  const taskId = Number(route.params.id)
  if (!taskId) return
  try {
    const res = await migrationTaskApi.report(taskId, { refresh: true })
    const report = (res.data as { report?: unknown }).report ?? res.data
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `migration_report_task_${taskId}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    alert('导出报告失败')
  }
}

/** 是否展示「继续迁移」按钮 */
const canResume = (status: string) => {
  if (!['failed', 'partial', 'canceled', 'aborted'].includes(status)) return false
  const t = task.value
  if (!t) return false
  return RESUMABLE_TASK_TYPES.includes(t.task_type as (typeof RESUMABLE_TASK_TYPES)[number])
}

/** 详情页提示条是否说明可继续迁移 */
const showResumeHint = computed(() => {
  if (!task.value) return false
  return canResume(task.value.status)
})

const startTask = async () => {
  try {
    await migrationTaskApi.start(Number(route.params.id), { resume: false })
    await loadTask()
    ensureStatusPolling()
  } catch (error) {
    console.error('Failed to start task:', error)
  }
}

const resumeTask = async () => {
  if (!confirm('从上次断点继续迁移？已成功的表将跳过，未完成的表会重新迁移。')) return
  try {
    await migrationTaskApi.start(Number(route.params.id), { resume: true })
    await loadTask()
    ensureStatusPolling()
  } catch (error) {
    console.error('Failed to resume task:', error)
    alert('继续迁移失败，请查看控制台或任务日志')
  }
}

const restartTask = async () => {
  if (!confirm('确定从头重新运行？将清空已完成记录并重新迁移全部表。')) return
  try {
    await migrationTaskApi.start(Number(route.params.id), { resume: false })
    await loadTask()
    ensureStatusPolling()
  } catch (error) {
    console.error('Failed to restart task:', error)
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

// ===== v2.4: 数据库对比与立即增量同步 =====
const comparePreview = async () => {
  diffLoading.value = true
  diffResult.value = null
  try {
    const res = await migrationTaskApi.comparePreview(Number(route.params.id))
    diffResult.value = res.data.diff
  } catch (error: any) {
    const msg = error?.response?.data?.message || error?.message || '对比失败'
    alert('对比预览失败: ' + msg)
    console.error('comparePreview failed:', error)
  } finally {
    diffLoading.value = false
  }
}

const syncNow = async () => {
  if (!confirm('确定立即执行主键对齐增量同步？\n将对比源/目标主键差异,自动补插缺失行、删除多余行、检测更新行。\n适用中小表(50万行内),大表请用定时增量。')) return
  syncing.value = true
  try {
    const res = await migrationTaskApi.syncNow(Number(route.params.id))
    const dur = res.data.duration_seconds
    const logTail = res.data.log_tail || []
    alert(`增量同步完成,耗时 ${dur} 秒\n${logTail.slice(-5).join('\n')}`)
    await loadTask()
  } catch (error: any) {
    const msg = error?.response?.data?.message || error?.message || '同步失败'
    alert('立即同步失败: ' + msg)
    console.error('syncNow failed:', error)
  } finally {
    syncing.value = false
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

// 点击刷新：静默更新进度/状态/日志，不闪界面、不重新渲染整页
const refreshStatus = async () => {
  await loadTask(false)
}

watch(
  () => route.params.id,
  async (newId, oldId) => {
    if (!newId || newId === oldId) return
    stopStatusPolling()
    await loadTask()
  },
)

watch(
  () => task.value?.status,
  (status) => {
    if (status === 'running') startStatusPolling()
    else stopStatusPolling()
  },
)

onMounted(async () => {
  await loadTask()
})

onUnmounted(() => {
  stopStatusPolling()
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
  color: var(--text);
}

.page-header .text-muted {
  font-size: 1rem;
}

.section-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: var(--text);
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
  color: var(--text);
  font-size: 1rem;
  padding: 0.5rem 0.75rem;
  background: var(--background);
  border-radius: 0.5rem;
  border-left: 3px solid var(--primary);
}

/* 任务详情：大量源表名可滚动展示 */
.source-objects-compact .source-objects-monolist {
  max-height: 14rem;
  overflow: auto;
  margin: 0;
  padding: 0.5rem 0.65rem;
  font-size: 0.8rem;
  line-height: 1.35;
  white-space: pre;
  word-break: break-all;
  background: var(--background);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 0.35rem;
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
  background: var(--border);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 0.75rem;
}

.progress-text {
  font-weight: 600;
  color: var(--primary);
  min-width: 60px;
  text-align: right;
}

.view-progress-list {
  border-top: 1px solid var(--border);
  padding-top: 1rem;
}

.view-progress-item {
  margin-bottom: 1rem;
}
.view-progress-item:last-child {
  margin-bottom: 0;
}

.view-progress-name {
  font-weight: 500;
  color: var(--text);
}

.view-progress-stats strong {
  color: var(--primary);
}

.progress.thin {
  height: 0.5rem;
  border-radius: 0.25rem;
  background: var(--border);
}

.current-table-progress .border-top {
  border-color: var(--border) !important;
}

.action-buttons {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.log-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.log-toolbar .input-group {
  flex: 1;
  min-width: 280px;
}

.log-container {
  background: #0f172a;
  border-radius: 0.5rem;
  padding: 0.75rem;
  max-height: 520px;
  overflow-y: auto;
  border: 1px solid #1e293b;
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.8rem;
  line-height: 1.55;
  color: #cbd5e1;
}

.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

.log-line {
  padding: 0.1rem 0.25rem;
  border-radius: 0.15rem;
  white-space: pre-wrap;
  word-break: break-all;
  border-left: 3px solid transparent;
  padding-left: 0.5rem;
  margin-bottom: 0.05rem;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.03);
}

.log-level-tag {
  display: inline-block;
  min-width: 56px;
  font-weight: 600;
  margin-right: 0.4rem;
  color: #94a3b8;
  font-size: 0.72rem;
}

.log-text {
  color: #cbd5e1;
}

.log-step {
  color: #38bdf8;
  border-left-color: #0ea5e9;
  background: rgba(14, 165, 233, 0.05);
  font-weight: 500;
}
.log-step .log-level-tag { color: #38bdf8; }

.log-info {
  color: #93c5fd;
}
.log-info .log-level-tag { color: #60a5fa; }

.log-ok {
  color: #86efac;
  border-left-color: #22c55e;
  background: rgba(34, 197, 94, 0.06);
}
.log-ok .log-level-tag { color: #4ade80; }

.log-warn {
  color: #fde68a;
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.06);
}
.log-warn .log-level-tag { color: #fbbf24; }

.log-error {
  color: #fca5a5;
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
  font-weight: 500;
}
.log-error .log-level-tag { color: #f87171; }

.log-data {
  color: #d8b4fe;
  border-left-color: #a855f7;
  background: rgba(168, 85, 247, 0.05);
}
.log-data .log-level-tag { color: #c084fc; }

.log-sql {
  color: #fbcfe8;
  border-left-color: #ec4899;
  background: rgba(236, 72, 153, 0.05);
}
.log-sql .log-level-tag { color: #f472b6; }

.log-meta {
  color: #a7f3d0;
  border-left-color: #14b8a6;
  background: rgba(20, 184, 166, 0.05);
}
.log-meta .log-level-tag { color: #5eead4; }

.log-content {
  color: var(--text);
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

.spinner-border {
  width: 3rem;
  height: 3rem;
}
</style>
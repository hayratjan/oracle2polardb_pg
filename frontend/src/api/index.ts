import apiClient from './client'

export interface OracleConnection {
  id?: number
  name: string
  host: string
  port: number
  service_name: string
  username: string
  password: string
  created_at?: string
}

export interface PostgresConnection {
  id?: number
  user?: number
  name: string
  host: string
  port: number
  database: string
  username: string
  password: string
  sslmode?: string
  status?: string
  created_at?: string
  updated_at?: string
}

export interface MigrationTask {
  id?: number
  name: string
  task_type: string
  oracle_connection: number
  postgres_connection?: number
  /** 目标 PolarDB/PostgreSQL 数据库名（连接下的具体库） */
  postgres_database?: string
  source_schema: string
  target_schema?: string
  target_object?: string
  source_object?: string
  source_objects?: string
  selected_fields?: string
  identifier_case: string
  is_batch: boolean
  parent_task?: number
  conflict_strategy: string
  status: string
  log?: string
  cancel_requested: boolean
  progress: number
  created_at?: string
  started_at?: string
  completed_at?: string
  view_progress?: any
  sqlite_directory?: string
  sqlite_file_name?: string
  source_db?: string
  target_db?: string
  sqlite_path?: string
  oracle_connection_name?: string
  postgres_connection_name?: string
  /** 增量：none | timestamp | pk_mirror（主键对齐定时增删） */
  incremental_mode?: string
  watermark_column?: string
  last_watermark?: string
  schedule_enabled?: boolean
  schedule_interval_minutes?: number
  last_schedule_run?: string
  /** 主键对齐单次允许对比的最大行数（源、目标两侧） */
  sync_max_pkey_rows?: number
  /** 目标环境配置（库/表空间/用户/Schema） */
  target_provisioning?: TargetProvisioningConfig
  migration_report?: Record<string, unknown>
}

/** 目标环境单项配置 */
export interface TargetResourceConfig {
  mode: 'existing' | 'create' | 'skip'
  name?: string
  username?: string
  password?: string
  location?: string
  encoding?: string
  owner?: string
  createdb?: boolean
}

/** 目标环境完整配置 */
export interface TargetProvisioningConfig {
  connection_id?: number
  database?: TargetResourceConfig
  tablespace?: TargetResourceConfig
  user?: TargetResourceConfig
  schema?: TargetResourceConfig
  prepare_config?: Record<string, unknown>
  schema_mappings?: { source_schema: string; target_schema: string }[]
  object_types?: Record<string, boolean>
  auto_prepare?: boolean
}

export const oracleConnectionApi = {
  list: () => apiClient.get('/api/oracle-connections/'),
  get: (id: number) => apiClient.get(`/api/oracle-connections/${id}/`),
  create: (data: OracleConnection) => apiClient.post('/api/oracle-connections/', data),
  update: (id: number, data: OracleConnection) => apiClient.put(`/api/oracle-connections/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/api/oracle-connections/${id}/`),
  test: (id: number) => apiClient.post(`/api/oracle/test-connection/`, { connection_id: id }),
  /** 使用当前表单参数测试（未保存的输入），用于编辑弹窗内测试 */
  testWithParams: (params: { connection_id?: number; host: string; port: number; service_name: string; username: string; password?: string }) =>
    apiClient.post('/api/oracle/test-connection/', params),
  save: (data: OracleConnection) => apiClient.post('/api/oracle/save-connection/', data),
  deleteConnection: (id: number) => apiClient.post('/api/oracle/delete-connection/', { connection_id: id }),
  edit: (id: number, data: OracleConnection) => apiClient.post(`/api/oracle/edit-connection/`, { connection_id: id, ...data }),
}

export const postgresConnectionApi = {
  list: () => apiClient.get('/api/postgres-connections/'),
  get: (id: number) => apiClient.get(`/api/postgres-connections/${id}/`),
  create: (data: PostgresConnection) => apiClient.post('/api/postgres-connections/', data),
  update: (id: number, data: PostgresConnection) => apiClient.put(`/api/postgres-connections/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/api/postgres-connections/${id}/`),
  test: (id: number) => apiClient.post(`/api/postgres/test-connection/`, { connection_id: id }),
  /** 使用当前表单参数测试（未保存的输入），用于编辑弹窗内测试 */
  testWithParams: (params: { connection_id?: number; host: string; port: number; database: string; username: string; password?: string; sslmode?: string }) =>
    apiClient.post('/api/postgres/test-connection/', params),
  save: (data: PostgresConnection) => apiClient.post('/api/postgres/save-connection/', data),
  deleteConnection: (id: number) => apiClient.post('/api/postgres/delete-connection/', { connection_id: id }),
  edit: (id: number, data: PostgresConnection) => apiClient.post(`/api/postgres/edit-connection/`, { connection_id: id, ...data }),
}

/** 任务列表分页响应 */
export interface TaskListResponse {
  count: number
  next: string | null
  previous: string | null
  results: MigrationTask[]
}

export const migrationTaskApi = {
  /** 获取任务列表，支持分页：params.page、params.page_size */
  list: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<TaskListResponse>('/api/tasks/', { params: params || {} }),
  /** reconcile=1 时修正孤儿 running（进程已退出但库中仍为执行中） */
  get: (id: number, options?: { reconcile?: boolean }) =>
    apiClient.get(`/api/tasks/${id}/`, {
      params: options?.reconcile ? { reconcile: 1 } : undefined,
    }),
  create: (data: MigrationTask) => apiClient.post('/api/tasks/', data),
  update: (id: number, data: MigrationTask) => apiClient.put(`/api/tasks/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/api/tasks/${id}/`),
  /** 启动任务；resume=true 时断点续传（跳过已完成表） */
  start: (id: number, data?: { resume?: boolean; conflict_strategy?: string; postgres_database?: string }) =>
    apiClient.post(`/api/tasks/${id}/start/`, data ?? {}),
  cancel: (id: number) => apiClient.post(`/api/tasks/${id}/cancel/`),
  status: (id: number) => apiClient.get(`/api/tasks/${id}/status/`),
  /** 轻量状态轮询（不返回 log），用于任务执行中刷新进度，减少响应体积 */
  statusLight: (id: number) => apiClient.get(`/api/tasks/${id}/status/`, { params: { light: 1 } }),
  info: (id: number) => apiClient.get(`/api/tasks/${id}/info/`),
  switchDatabase: (id: number, data: { postgres_database: string }) => 
    apiClient.post(`/api/tasks/${id}/switch_database/`, data),
  createValidated: (data: MigrationTask) => apiClient.post('/api/create-task/', data),
  /** 结构化任务日志分页，cursor 为上一页最后一条 id */
  logs: (id: number, params?: { page_size?: number; cursor?: string }) =>
    apiClient.get<{ status: string; results: { id: number; level: string; message: string; created_at: string }[]; next_cursor: string | null; task_id: number }>(
      `/api/tasks/${id}/logs/`,
      { params: params || {} },
    ),
  /** 实时任务监控聚合数据 */
  monitor: (params?: { task_limit?: number; log_limit?: number; compare_limit?: number }) =>
    apiClient.get<TaskMonitorResponse>('/api/tasks/monitor/', { params: params || {} }),
  /** 结构化迁移报告 */
  report: (id: number, params?: { refresh?: boolean; format?: string }) =>
    apiClient.get(`/api/tasks/${id}/report/`, {
      params: { refresh: params?.refresh ? 1 : undefined, format: params?.format },
    }),
}

/** 主键对齐对比快照 */
export interface CompareSnapshot {
  task_id: number
  task_name: string
  source_object?: string
  source_schema?: string
  target_schema?: string
  incremental_mode?: string
  schedule_enabled?: boolean
  last_schedule_run?: string | null
  status?: string
  source_rows?: number
  target_rows?: number
  row_diff?: number
  to_delete?: number
  to_insert?: number
  pk_columns?: string
  is_consistent?: boolean
  summary_line?: string
}

export interface TaskMonitorItem {
  id: number
  name: string
  task_type: string
  status: string
  progress: number
  source_db: string
  target_db: string
  incremental_mode?: string
  schedule_enabled?: boolean
  schedule_interval_minutes?: number
  last_schedule_run?: string | null
  cancel_requested?: boolean
  created_at?: string
  started_at?: string
  completed_at?: string
  view_progress?: Record<string, unknown>
  log_tail?: string
  compare?: CompareSnapshot
}

export interface TaskMonitorLogEntry {
  id: number
  task_id: number
  task_name: string
  level: string
  message: string
  created_at: string
}

export interface TaskMonitorResponse {
  status: string
  server_time: string
  summary: {
    total: number
    pending: number
    running: number
    completed: number
    failed: number
    partial: number
    canceled: number
  }
  running_tasks: TaskMonitorItem[]
  tasks: TaskMonitorItem[]
  compare_snapshots: CompareSnapshot[]
  recent_logs: TaskMonitorLogEntry[]
  recent_operations: TaskMonitorLogEntry[]
}

export const databaseApi = {
  getSchemas: (params: any) => apiClient.get('/api/schemas/', { params }),
  getDatabaseObjects: (params: any) => apiClient.get('/api/database-objects/', { params }),
  getPostgresDatabases: (params: any) => apiClient.get('/api/postgres-databases/', { params }),
  browseDirectories: (params: any) => apiClient.get('/api/filesystem/directories/', { params }),
  getDatabaseInfo: (params: any) => apiClient.get('/api/database-info/', { params }),
  getOracleSchemas: (params: any) => apiClient.get('/api/oracle/schemas/', { params }),
  getOracleTables: (params: any) => apiClient.get('/api/oracle/tables/', { params }),
  getOracleUsers: (params: any) => apiClient.get('/api/oracle/users/', { params }),
  getPgSchemas: (params: any) => apiClient.get('/api/polardb/schemas/', { params }),
  getPgTables: (params: any) => apiClient.get('/api/polardb/tables/', { params }),
  getPgUsers: (params: any) => apiClient.get('/api/polardb/users/', { params }),
  /** Oracle 整库发现：Schema 及对象统计 */
  getOracleDiscovery: (params: { connection_id: number }) =>
    apiClient.get('/api/oracle/discovery/', { params }),
  /** 列出 PG 表空间 */
  getPgTablespaces: (params: { connection_id: number; database?: string }) =>
    apiClient.get('/api/polardb/tablespaces/', { params }),
}

/** 目标环境 DDL 与迁移计划 API */
export const targetEnvApi = {
  prepare: (data: Record<string, unknown>) => apiClient.post('/api/target-env/prepare/', data),
  createDatabase: (data: { connection_id: number; name: string; owner?: string; encoding?: string }) =>
    apiClient.post('/api/polardb/databases/create/', data),
  createTablespace: (data: { connection_id: number; name: string; location: string }) =>
    apiClient.post('/api/polardb/tablespaces/create/', data),
  createUser: (data: { connection_id: number; username: string; password: string; database?: string; createdb?: boolean }) =>
    apiClient.post('/api/polardb/users/create/', data),
  createSchema: (data: { connection_id: number; database: string; schema: string; owner?: string }) =>
    apiClient.post('/api/polardb/schemas/create/', data),
}

export const migrationPlanApi = {
  /** 表级迁移向导创建任务 */
  createTableMigration: (data: Record<string, unknown>) =>
    apiClient.post('/api/create-table-migration/', data),
  /** 整库一键迁移创建任务 */
  createFullDatabaseMigration: (data: Record<string, unknown>) =>
    apiClient.post('/api/create-full-database-migration/', data),
}

export const configApi = {
  getMigrationSettings: () => apiClient.get('/api/config/migration/'),
  saveMigrationSettings: (data: any) => apiClient.post('/api/config/migration/', data),
  getSystemSettings: () => apiClient.get('/api/config/system/'),
  saveSystemSettings: (data: any) => apiClient.post('/api/config/system/', data),
  getCeleryStatus: () => apiClient.get('/api/config/celery-status/'),
}

export const logsApi = {
  getLogs: (params?: { limit?: number }) => apiClient.get('/api/logs/', { params }),
}

export const helpApi = {
  getHelp: () => apiClient.get('/api/help/'),
}
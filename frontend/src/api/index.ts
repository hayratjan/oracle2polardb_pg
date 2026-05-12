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
  /** 增量：none | timestamp */
  incremental_mode?: string
  watermark_column?: string
  last_watermark?: string
  schedule_enabled?: boolean
  schedule_interval_minutes?: number
  last_schedule_run?: string
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
  get: (id: number) => apiClient.get(`/api/tasks/${id}/`),
  create: (data: MigrationTask) => apiClient.post('/api/tasks/', data),
  update: (id: number, data: MigrationTask) => apiClient.put(`/api/tasks/${id}/`, data),
  delete: (id: number) => apiClient.delete(`/api/tasks/${id}/`),
  start: (id: number) => apiClient.post(`/api/tasks/${id}/start/`),
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
}

export const configApi = {
  getMigrationSettings: () => apiClient.get('/api/config/migration/'),
  saveMigrationSettings: (data: any) => apiClient.post('/api/config/migration/', data),
  getSystemSettings: () => apiClient.get('/api/config/system/'),
  saveSystemSettings: (data: any) => apiClient.post('/api/config/system/', data),
}

export const logsApi = {
  getLogs: () => apiClient.get('/api/logs/'),
}

export const helpApi = {
  getHelp: () => apiClient.get('/api/help/'),
}
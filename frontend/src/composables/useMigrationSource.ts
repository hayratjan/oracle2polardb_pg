/**
 * 迁移源端逻辑复用：Oracle 连接、Schema、对象列表加载
 */
import { ref, computed } from 'vue'
import { oracleConnectionApi, postgresConnectionApi, databaseApi } from '@/api'

export function useMigrationSource() {
  const oracleConnections = ref<any[]>([])
  const postgresConnections = ref<any[]>([])
  const schemas = ref<string[]>([])
  const pgDatabases = ref<string[]>([])
  const pgSchemas = ref<string[]>([])
  const pgUsers = ref<string[]>([])
  const sourceObjects = ref<string[]>([])
  const sourceObjectTypes = ref<Record<string, string>>({})
  const selectedSourceObjects = ref<string[]>([])
  const loadingObjects = ref(false)
  const searchTerm = ref('')

  const filteredObjects = computed(() => {
    if (!searchTerm.value) return sourceObjects.value
    const term = searchTerm.value.toLowerCase()
    return sourceObjects.value.filter(obj => obj.toLowerCase().includes(term))
  })

  /** 加载 Oracle / PG 连接列表 */
  const loadConnections = async () => {
    const [oracleRes, postgresRes] = await Promise.all([
      oracleConnectionApi.list(),
      postgresConnectionApi.list(),
    ])
    oracleConnections.value = oracleRes.data.results || oracleRes.data
    postgresConnections.value = postgresRes.data.results || postgresRes.data
  }

  /** 加载 Oracle Schema 列表 */
  const loadOracleSchemas = async (connectionId: number) => {
    if (!connectionId) return
    const res = await databaseApi.getOracleSchemas({ connection_id: connectionId })
    schemas.value = res.data.schemas || []
  }

  /** 加载 PG 数据库列表 */
  const loadPgDatabases = async (connectionId: number, defaultDb?: string) => {
    if (!connectionId) return []
    const res = await databaseApi.getPostgresDatabases({ connection_id: connectionId })
    pgDatabases.value = res.data.databases || []
    if (defaultDb && pgDatabases.value.includes(defaultDb)) {
      return defaultDb
    }
    return pgDatabases.value[0] || ''
  }

  /** 加载 PG Schema 列表 */
  const loadPgSchemas = async (connectionId: number, database: string) => {
    if (!connectionId || !database) {
      pgSchemas.value = []
      return
    }
    const res = await databaseApi.getPgSchemas({ connection_id: connectionId, database })
    pgSchemas.value = res.data.schemas || []
  }

  /** 加载 PG 用户列表 */
  const loadPgUsers = async (connectionId: number, database?: string) => {
    if (!connectionId) return
    const res = await databaseApi.getPgUsers({ connection_id: connectionId, database })
    pgUsers.value = res.data.users || []
  }

  /** 加载源对象列表（默认 TABLE 类型） */
  const loadSourceObjects = async (
    connectionId: number,
    schema: string,
    objectType = 'TABLE',
  ) => {
    if (!connectionId || !schema) return
    loadingObjects.value = true
    try {
      const res = await databaseApi.getDatabaseObjects({
        connection_id: connectionId,
        schema,
        object_type: objectType,
      })
      const raw = res.data.objects || []
      sourceObjects.value = raw.map((o: string | { name: string; object_type?: string }) =>
        typeof o === 'string' ? o : o.name,
      )
      sourceObjectTypes.value = {}
      raw.forEach((o: string | { name: string; object_type?: string }) => {
        if (typeof o !== 'string' && o.object_type) {
          sourceObjectTypes.value[o.name] = o.object_type
        }
      })
    } finally {
      loadingObjects.value = false
    }
  }

  const selectAllObjects = () => {
    selectedSourceObjects.value = [...filteredObjects.value]
  }

  const clearAllObjects = () => {
    selectedSourceObjects.value = []
  }

  return {
    oracleConnections,
    postgresConnections,
    schemas,
    pgDatabases,
    pgSchemas,
    pgUsers,
    sourceObjects,
    sourceObjectTypes,
    selectedSourceObjects,
    loadingObjects,
    searchTerm,
    filteredObjects,
    loadConnections,
    loadOracleSchemas,
    loadPgDatabases,
    loadPgSchemas,
    loadPgUsers,
    loadSourceObjects,
    selectAllObjects,
    clearAllObjects,
  }
}

<template>
  <div class="create-task-view">
    <div class="page-header mb-4">
      <h1>
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-plus-circle me-2" viewBox="0 0 16 16">
          <path d="M8 4a.5.5 0 01.5.5v3h3a.5.5 0 010 1h-3v3a.5.5 0 01-1 0v-3h-3a.5.5 0 010-1h3v-3A.5.5 0 018 4z"/>
        </svg>
        创建迁移任务
      </h1>
      <p class="text-muted mb-0">配置并创建新的数据库迁移任务</p>
    </div>
    
    <div class="row">
      <div class="col-lg-8">
        <div class="card">
          <div class="card-body">
            <form @submit.prevent="handleSubmit">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-type me-1" viewBox="0 0 16 16">
                      <path d="M2.244 13.081l.943-9.414A1 1 0 014.109 2.5h6.382a1 1 0 01.922.667l.943 9.414a1 1 0 01-.922 1.083H3.166a1 1 0 01-.922-1.083zM7.814 4.15a.186.186 0 00-.199.021L4.735 7.48l.317.317 2.876-2.876a.187.187 0 00-.014-.271zm.043 3.914l-2.876 2.876.317.317 2.876-2.876a.187.187 0 00-.317-.317zm2.728-3.914a.187.187 0 00-.271 0L7.438 7.48l.317.317 2.876-2.876a.187.187 0 00-.014-.271zm.043 3.914l-2.876 2.876.317.317 2.876-2.876a.187.187 0 00-.317-.317z"/>
                    </svg>
                    任务名称
                  </label>
                  <input v-model="form.name" type="text" class="form-control" required placeholder="输入任务名称">
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-tag me-1" viewBox="0 0 16 16">
                      <path d="M6 4.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM4.5 6a1.5 1.5 0 100 3 1.5 1.5 0 000-3zM6 8.5a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0zM4.5 10a1.5 1.5 0 100 3 1.5 1.5 0 000-3z"/>
                    </svg>
                    任务类型
                  </label>
                  <select v-model="form.task_type" class="form-select" required>
                    <option value="table">表</option>
                    <option value="materialized_view">物化视图</option>
                    <option value="view">视图</option>
                    <option value="routine">例程</option>
                    <option value="all_tables">所有表</option>
                    <option value="view_to_table">视图数据迁移到表</option>
                    <option value="view_to_sqlite">视图数据迁移到SQLite</option>
                  </select>
                </div>
              </div>
              
              <hr class="my-4">
              
              <h5 class="mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-database me-1" viewBox="0 0 16 16">
                  <path d="M4.318 6.318a4.5 4.5 0 000 6.364L7.318 15.4a1.5 1.5 0 002.122 0l2.999-2.999a4.5 4.5 0 000-6.364L9.55 4.55a1.5 1.5 0 00-2.122 0L4.318 6.318zM5.732 7.732l2.999-2.999a.5.5 0 01.707 0l2.999 2.999a3.5 3.5 0 010 4.95l-2.999 2.999a.5.5 0 01-.707 0L5.732 12.682a3.5 3.5 0 010-4.95z"/>
                </svg>
                源数据库配置
              </h5>
              
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">Oracle连接</label>
                  <select v-model="form.oracle_connection" class="form-select" required @change="loadSchemas">
                    <option value="">请选择</option>
                    <option v-for="conn in oracleConnections" :key="conn.id" :value="conn.id">
                      {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
                    </option>
                  </select>
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">源Schema</label>
                  <select v-model="form.source_schema" class="form-select" required>
                    <option value="">请选择</option>
                    <option v-for="schema in schemas" :key="schema" :value="schema">{{ schema }}</option>
                  </select>
                </div>
              </div>
              
              <div class="row g-3 mt-3">
                <div class="col-md-12">
                  <label class="form-label">源对象</label>
                  <div class="source-objects-container">
                    <div class="source-objects-controls mb-2">
                      <button type="button" class="btn btn-sm btn-outline-primary me-2" @click="loadSourceObjects" :disabled="!form.oracle_connection || !form.source_schema">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-arrow-clockwise me-1" viewBox="0 0 16 16">
                          <path fill-rule="evenodd" d="M8 3a5 5 0 105 4.527.5.5 0 001 0A6 6 0 008 2v1z"/>
                          <path d="M8 4.466V.534a.25.25 0 00-.41-.192L5.23 2.308a.25.25 0 000 .384l2.36 1.966A.25.25 0 008 4.466z"/>
                        </svg>
                        刷新对象列表
                      </button>
                      <button type="button" class="btn btn-sm btn-outline-secondary me-2" @click="selectAllObjects" :disabled="filteredObjects.length === 0">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-check-all me-1" viewBox="0 0 16 16">
                          <path d="M8.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L2.324 8.384a.75.75 0 111.06-1.06l2.094 2.093L8.95 4.992a.252.252 0 01.02-.022zm-.92 5.14l6.38-7.75a.75.75 0 00-1.14-.975L6.923 8.823l-2.447-2.447a.75.75 0 00-1.061 1.06l3 3a.75.75 0 001.137-.089zm4.5-6.25a.75.75 0 00-1.5 0v4.5a.75.75 0 001.5 0v-4.5z"/>
                        </svg>
                        全选
                      </button>
                      <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearAllObjects" :disabled="selectedSourceObjects.length === 0">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-x-lg me-1" viewBox="0 0 16 16">
                          <path d="M2.146 2.854a.5.5 0 11.708-.708L8 7.293l5.146-5.147a.5.5 0 01.708.708L8.707 8l5.147 5.146a.5.5 0 01-.708.708L8 8.707l-5.146 5.147a.5.5 0 01-.708-.708L7.293 8 2.146 2.854z"/>
                        </svg>
                        清空
                      </button>
                      <span class="selected-count text-muted ms-3">
                        已选择: <strong>{{ selectedSourceObjects.length }}</strong> / {{ filteredObjects.length }}
                      </span>
                    </div>
                    <div class="search-box mb-2">
                      <input v-model="searchTerm" type="text" class="form-control" placeholder="搜索对象名称..." :disabled="sourceObjects.length === 0">
                    </div>
                    <div v-if="loadingObjects" class="text-center py-3">
                      <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                      </div>
                      <span class="ms-2 text-muted">加载对象列表中...</span>
                    </div>
                    <div v-else-if="sourceObjects.length === 0 && form.oracle_connection && form.source_schema" class="text-center py-3 text-muted">
                      <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-inbox mb-2" viewBox="0 0 16 16">
                        <path d="M4.98 4a.5.5 0 00-.39.188L1.54 8H6a.5.5 0 01.5.5 1.5 1.5 0 003 0A.5.5 0 0110 8h4.46l-3.05-3.812A.5.5 0 0011.02 4H4.98zm9.954 5H10.45a2.5 2.5 0 01-4.9 0H1.066l.32 2.562a.5.5 0 00.497.438h12.234a.5.5 0 00.496-.438L14.933 9zM3.809 3.563A1.5 1.5 0 014.981 3h6.038a1.5 1.5 0 011.172.563l3.7 4.625a.5.5 0 01.105.374l-.39 3.124A1.5 1.5 0 0114.117 13H1.883a1.5 1.5 0 01-1.489-1.314l-.39-3.124a.5.5 0 01.106-.374l3.7-4.625z"/>
                      </svg>
                      <p class="mb-0">点击"刷新对象列表"按钮加载可用对象</p>
                    </div>
                    <div v-else-if="filteredObjects.length > 0" class="source-objects-list">
                      <div class="form-check" v-for="obj in filteredObjects" :key="obj">
                        <input class="form-check-input" type="checkbox" :id="'obj-' + obj" :value="obj" v-model="selectedSourceObjects">
                        <label class="form-check-label" :for="'obj-' + obj">{{ obj }}</label>
                      </div>
                    </div>
                    <div v-else-if="sourceObjects.length > 0 && filteredObjects.length === 0" class="text-center py-3 text-muted">
                      <p class="mb-0">没有找到匹配的对象</p>
                    </div>
                    <div v-else class="text-center py-3 text-muted">
                      <p class="mb-0">请先选择Oracle连接和源Schema</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <hr class="my-4">
              
              <h5 class="mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-server me-1" viewBox="0 0 16 16">
                  <path d="M1.5 0h11.586a1.5 1.5 0 011.06.44l1.415 1.414A1.5 1.5 0 0116 2.914V14.5a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5v-11A1.5 1.5 0 011.5 2zM1 1.5v1a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zm0 4v9a.5.5 0 00.5.5h13a.5.5 0 00.5-.5v-9a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5zM2 7a1 1 0 011-1h10a1 1 0 011 1v2a1 1 0 01-1 1H3a1 1 0 01-1-1V7zm0 5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H3a1 1 0 01-1-1v-1z"/>
                </svg>
                目标数据库配置
              </h5>
              
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">PostgreSQL连接</label>
                  <select v-model="form.postgres_connection" class="form-select" required @change="loadPgSchemas">
                    <option value="">请选择</option>
                    <option v-for="conn in postgresConnections" :key="conn.id" :value="conn.id">
                      {{ conn.name }} ({{ conn.host }}:{{ conn.port }})
                    </option>
                  </select>
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">目标Schema</label>
                  <select v-model="form.target_schema" class="form-select">
                    <option value="">请选择</option>
                    <option value="public">public (默认)</option>
                    <option v-for="schema in pgSchemas" :key="schema" :value="schema">{{ schema }}</option>
                  </select>
                </div>
              </div>
              
              <div class="row g-3 mt-3">
                <div class="col-md-6">
                  <label class="form-label">目标对象名称</label>
                  <input v-model="form.target_object" type="text" class="form-control" placeholder="可选">
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">字段过滤</label>
                  <textarea v-model="form.selected_fields" class="form-control" rows="1"
                            placeholder="逗号或换行分隔的字段名"></textarea>
                </div>
              </div>
              
              <hr class="my-4">
              
              <h5 class="mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-gear me-1" viewBox="0 0 16 16">
                  <path d="M8 4.754a3.246 3.246 0 100 6.492 3.246 3.246 0 000-6.492zM5.754 8a2.246 2.246 0 114.492 0 2.246 2.246 0 01-4.492 0z"/>
                  <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 01-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 01-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 01.52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 011.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 011.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 01.52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 01-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 01-1.255-.52l-.094-.319z"/>
                </svg>
                高级配置
              </h5>
              
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">标识符大小写策略</label>
                  <select v-model="form.identifier_case" class="form-select">
                    <option value="lower">全部小写</option>
                    <option value="upper">全部大写</option>
                    <option value="preserve">保持原样</option>
                  </select>
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">冲突处理策略</label>
                  <select v-model="form.conflict_strategy" class="form-select">
                    <option value="error">遇到冲突时报错</option>
                    <option value="replace">删除并替换已存在对象</option>
                    <option value="skip">跳过已存在对象</option>
                    <option value="append">追加数据（仅适用于表）</option>
                    <option value="truncate">清空表并重新加载数据</option>
                  </select>
                </div>
              </div>
              
              <div class="form-check form-switch mt-3">
                <input v-model="form.is_batch" type="checkbox" class="form-check-input" id="isBatch">
                <label class="form-check-label" for="isBatch">批量迁移</label>
              </div>
              
              <div v-if="form.task_type.includes('sqlite')" class="row g-3 mt-3">
                <div class="col-md-6">
                  <label class="form-label">SQLite目录</label>
                  <input v-model="form.sqlite_directory" type="text" class="form-control" 
                         placeholder="SQLite文件保存目录">
                </div>
                
                <div class="col-md-6">
                  <label class="form-label">SQLite文件名</label>
                  <input v-model="form.sqlite_file_name" type="text" class="form-control" 
                         placeholder="SQLite文件名">
                </div>
              </div>
              
              <hr class="my-4">
              
              <div class="d-flex gap-2">
                <button type="submit" class="btn btn-lg btn-primary flex-grow-1" :disabled="loading">
                  <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                  <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-rocket-takeoff me-2" viewBox="0 0 16 16">
                    <path d="M9.752 6.193c.599.6 1.73.437 2.182-.33.47-.779.492-2.055.04-2.73-.47-.795-1.673-.908-2.228-.52-.527.367-.74.89-.299 1.432l.333 1.51c.024.11.034.219.028.327-.004.1-.014.197-.032.292l.266.136c.143.074.288.144.435.21.149.067.297.13.445.188zM12.418 8.48c.718.007 1.336.402 1.632 1.04.3.646.234 1.39-.18 1.977-.438.62-1.187.92-1.914.79-.725-.13-1.32-.648-1.541-1.343-.22-.694.03-1.45.632-1.896.523-.383 1.07-.457 1.371-.568zm-4.144 1.352c.66.007 1.226.368 1.498.954.275.594.215 1.278-.163 1.819-.403.568-1.09.845-1.758.724-.664-.12-1.208-.593-1.413-1.229-.201-.635.027-1.327.58-1.739.48-.351.986-.42 1.256-.529zM7.08 5.813c.6.006 1.115.335 1.36.868.25.54.195 1.162-.148 1.656-.366.516-.99.77-1.6.662-.604-.108-1.098-.538-1.284-1.116-.183-.576.025-1.203.527-1.583.435-.319.894-.381 1.145-.487zM5.353 3.326c.532.005.99.297 1.206.77.22.478.173 1.03-.131 1.466-.324.458-.878.683-1.419.587-.536-.096-.973-.477-1.139-.99-.163-.51.022-1.067.468-1.404.386-.283.793-.338 1.015-.429zM3.647.9c.464.005.864.259 1.053.67.193.418.151.9-.115 1.282-.283.4-.768.597-1.242.513-.468-.084-.85-.418-.996-.865-.142-.444.02-.933.409-1.228.337-.247.693-.295.891-.372zM2.08 6.78c.432.004.804.242.981.626.18.389.14.836-.107 1.19-.264.373-.718.557-1.158.48-.436-.078-.79-.386-.925-.795-.133-.406.018-.863.383-1.138.314-.23.648-.273.826-.343zM.715 10.923c.4.004.745.224.908.58.167.361.13.774-.1 1.103-.244.346-.664.517-1.073.445-.404-.072-.732-.358-.857-.737-.123-.376.017-.8.355-1.055.291-.214.6-.253.767-.318zm1.896 3.63c.37.003.69.207.84.538.154.335.12.718-.092 1.022-.226.32-.615.48-.993.412-.374-.067-.678-.332-.794-.683-.114-.347.016-.742.329-.978.27-.199.556-.234.71-.296zm2.98 2.917c.34.003.634.19.772.494.141.308.11.66-.084.938-.208.293-.565.44-.912.378-.344-.062-.624-.305-.73-.626-.105-.318.015-.68.302-.898.248-.182.51-.214.652-.27zm3.058 2.02c.31.003.578.173.704.45.13.281.101.601-.077.855-.19.27-.516.403-.832.345-.313-.056-.568-.278-.665-.57-.096-.29.014-.62.275-.819.226-.166.464-.195.595-.246zm3.012.913c.28.002.524.156.639.408.117.255.09.546-.07.776-.173.244-.468.365-.754.312-.283-.05-.514-.252-.603-.517-.087-.263.013-.563.25-.743.204-.15.42-.177.538-.223zm2.858-.288c.25.002.47.14.575.366.105.228.082.49-.063.697-.156.22-.421.33-.676.282-.254-.045-.461-.226-.541-.464-.078-.236.012-.505.224-.667.183-.135.377-.159.481-.2zm2.557-1.345c.22.002.414.123.507.321.093.201.072.431-.055.613-.138.194-.371.29-.598.247-.224-.04-.407-.2-.479-.408-.07-.208.01-.443.197-.587.16-.119.332-.14.428-.176zm2.12-2.12c.19.002.362.106.445.277.082.173.064.376-.048.537-.122.17-.326.254-.525.216-.196-.035-.357-.176-.42-.357-.062-.18.009-.388.173-.514.14-.104.291-.123.375-.155zm1.577-2.645c.17.001.317.094.393.246.073.152.057.33-.043.473-.108.15-.29.226-.46.193-.17-.032-.31-.16-.366-.324-.055-.163.008-.35.152-.463.124-.092.258-.108.324-.136zm.95-2.99c.148.001.277.082.344.214.064.132.05.289-.038.413-.095.132-.255.198-.404.168-.148-.028-.27-.14-.319-.283-.048-.142.007-.306.133-.405.108-.08.226-.094.284-.118zm.268-3.094c.127.001.238.07.296.184.055.113.043.248-.033.353-.081.113-.218.17-.346.144-.127-.024-.231-.12-.274-.243-.041-.122.006-.262.114-.347.092-.068.193-.08.242-.101zm-.378-2.99c.107.001.2.06.25.155.047.095.037.21-.028.299-.068.096-.187.145-.296.121-.109-.02-.198-.103-.235-.206-.035-.103.005-.222.097-.295.078-.058.165-.068.208-.087zm-.976-2.635c.087.001.163.049.203.126.038.077.03.171-.023.244-.055.078-.151.118-.24.099-.088-.017-.16-.083-.191-.167-.028-.084.004-.18.079-.239.063-.047.133-.055.172-.07zm-1.438-2.09c.067.001.125.038.156.097.03.059.023.131-.018.188-.043.06-.117.091-.186.076-.068-.013-.123-.064-.148-.129-.022-.065.003-.139.061-.184.049-.036.103-.043.135-.056zm-1.75-1.458c.047.001.088.027.11.068.021.041.016.091-.012.131-.03.042-.082.064-.13.053-.048-.009-.086-.045-.104-.09-.016-.045.002-.097.043-.127.034-.025.072-.03.094-.038zm-1.926-.765c.027.001.05.015.063.039.012.024.009.052-.007.075-.017.024-.047.037-.075.03-.028-.005-.05-.026-.06-.046-.009-.026.001-.056.025-.072.02-.014.041-.017.054-.022z"/>
                  </svg>
                  {{ loading ? '创建中...' : '创建任务' }}
                </button>
                <router-link to="/tasks" class="btn btn-lg btn-outline-secondary">取消</router-link>
              </div>
            </form>
          </div>
        </div>
      </div>
      
      <div class="col-lg-4">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-info-circle me-1" viewBox="0 0 16 16">
                <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
              </svg>
              使用提示
            </h5>
          </div>
          <div class="card-body">
            <ul class="list-unstyled">
              <li class="mb-3">
                <strong class="d-block mb-1">任务类型说明</strong>
                <p class="text-muted small mb-0">选择合适的迁移类型，不同类型支持不同的对象迁移。</p>
              </li>
              <li class="mb-3">
                <strong class="d-block mb-1">连接配置</strong>
                <p class="text-muted small mb-0">确保源数据库和目标数据库连接配置正确且可访问。</p>
              </li>
              <li class="mb-3">
                <strong class="d-block mb-1">冲突处理</strong>
                <p class="text-muted small mb-0">根据需求选择合适的冲突处理策略，避免数据丢失。</p>
              </li>
              <li class="mb-0">
                <strong class="d-block mb-1">批量迁移</strong>
                <p class="text-muted small mb-0">批量迁移可以提高效率，但需要确保所有对象配置正确。</p>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { oracleConnectionApi, postgresConnectionApi, databaseApi, migrationTaskApi } from '@/api'
import type { MigrationTask } from '@/api'

const router = useRouter()
const loading = ref(false)
const oracleConnections = ref<any[]>([])
const postgresConnections = ref<any[]>([])
const schemas = ref<string[]>([])
const pgSchemas = ref<string[]>([])
const sourceObjects = ref<string[]>([])
const selectedSourceObjects = ref<string[]>([])
const loadingObjects = ref(false)
const searchTerm = ref('')

const filteredObjects = computed(() => {
  if (!searchTerm.value) {
    return sourceObjects.value
  }
  
  const term = searchTerm.value.toLowerCase()
  return sourceObjects.value.filter(obj => 
    obj.toLowerCase().includes(term)
  )
})

const form = ref<MigrationTask>({
  name: '',
  task_type: 'table',
  oracle_connection: 0,
  postgres_connection: 0,
  source_schema: '',
  target_schema: '',
  target_object: '',
  source_object: '',
  source_objects: '',
  selected_fields: '',
  identifier_case: 'lower',
  is_batch: false,
  conflict_strategy: 'error',
  status: 'pending',
  cancel_requested: false,
  progress: 0,
})

const loadConnections = async () => {
  try {
    const [oracleRes, postgresRes] = await Promise.all([
      oracleConnectionApi.list(),
      postgresConnectionApi.list(),
    ])
    oracleConnections.value = oracleRes.data.results || oracleRes.data
    postgresConnections.value = postgresRes.data.results || postgresRes.data
  } catch (error) {
    console.error('Failed to load connections:', error)
  }
}

const loadSchemas = async () => {
  if (!form.value.oracle_connection) return
  
  try {
    const res = await databaseApi.getOracleSchemas({
      connection_id: form.value.oracle_connection,
    })
    schemas.value = res.data.schemas || []
  } catch (error) {
    console.error('Failed to load schemas:', error)
  }
}

const loadPgSchemas = async () => {
  if (!form.value.postgres_connection) return
  
  try {
    const res = await databaseApi.getPgSchemas({
      connection_id: form.value.postgres_connection,
    })
    pgSchemas.value = res.data.schemas || []
  } catch (error) {
    console.error('Failed to load PostgreSQL schemas:', error)
  }
}

const loadSourceObjects = async () => {
  if (!form.value.oracle_connection || !form.value.source_schema) return
  
  loadingObjects.value = true
  try {
    const object_type = form.value.task_type === 'table' ? 'TABLE' : 
                       form.value.task_type === 'view' ? 'VIEW' : 
                       form.value.task_type === 'materialized_view' ? 'MATERIALIZED_VIEW' : 'TABLE'
    
    console.log('Loading source objects with params:', {
      connection_id: form.value.oracle_connection,
      schema: form.value.source_schema,
      object_type: object_type,
    })
    
    const res = await databaseApi.getDatabaseObjects({
      connection_id: form.value.oracle_connection,
      schema: form.value.source_schema,
      object_type: object_type,
    })
    sourceObjects.value = res.data.objects || []
    console.log('Loaded source objects:', sourceObjects.value.length, 'items')
  } catch (error) {
    console.error('Failed to load source objects:', error)
    sourceObjects.value = []
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

const handleSubmit = async () => {
  loading.value = true
  try {
    const taskData = { ...form.value }
    
    if (selectedSourceObjects.value.length > 0) {
      taskData.source_objects = selectedSourceObjects.value.join(',')
      taskData.source_object = ''
    }
    
    const res = await migrationTaskApi.createValidated(taskData)
    
    if (res.data.status === 'success') {
      router.push('/tasks')
    } else {
      alert('创建任务失败: ' + res.data.message)
    }
  } catch (error) {
    console.error('Failed to create task:', error)
    alert('创建任务失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadConnections()
})

watch(() => form.value.oracle_connection, () => {
  schemas.value = []
  form.value.source_schema = ''
  sourceObjects.value = []
  selectedSourceObjects.value = []
})

watch(() => form.value.source_schema, () => {
  sourceObjects.value = []
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    loadSourceObjects()
  }
})

watch(() => form.value.task_type, () => {
  sourceObjects.value = []
  selectedSourceObjects.value = []
  if (form.value.oracle_connection && form.value.source_schema) {
    loadSourceObjects()
  }
})
</script>

<style scoped>
.create-task-view {
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

.form-label {
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 0.5rem;
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid #e9ecef;
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
  font-size: 0.95rem;
}

.form-control:focus,
.form-select:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}

.form-control::placeholder {
  color: #a0aec0;
}

hr {
  border-color: #e2e8f0;
  margin: 2rem 0;
}

h5 {
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 1rem;
}

.form-check-input:checked {
  background-color: #667eea;
  border-color: #667eea;
}

.form-check-label {
  font-weight: 500;
  color: #4a5568;
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

.card-body {
  padding: 1.5rem;
}

.list-unstyled li {
  padding: 0.75rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.list-unstyled li:last-child {
  border-bottom: none;
}

.list-unstyled strong {
  color: #667eea;
  font-weight: 600;
}

.list-unstyled p {
  line-height: 1.6;
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
}

.source-objects-container {
  border: 2px solid #e9ecef;
  border-radius: 0.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
}

.source-objects-controls {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.selected-count {
  font-size: 0.875rem;
  color: #6c757d;
  margin-left: auto;
}

.search-box input {
  border-radius: 0.375rem;
  border: 1px solid #ced4da;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.search-box input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}

.source-objects-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 0.5rem;
  background-color: white;
  border-radius: 0.375rem;
  border: 1px solid #e2e8f0;
  padding: 30px;
}

.source-objects-list .form-check {
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 0;
  transition: background-color 0.2s ease;
}

.source-objects-list .form-check:hover {
  background-color: #f8f9fa;
}

.source-objects-list .form-check:last-child {
  border-bottom: none;
}

.source-objects-list .form-check-input {
  margin-top: 0.25rem;
  width: 1.125rem;
  height: 1.125rem;
  cursor: pointer;
}

.source-objects-list .form-check-label {
  margin-left: 0.75rem;
  cursor: pointer;
  color: #4a5568;
  font-size: 0.875rem;
  user-select: none;
  flex: 1;
  word-break: break-all;
}

.source-objects-list .form-check-label:hover {
  color: #667eea;
}

.source-objects-list .form-check-input:checked + .form-check-label {
  color: #667eea;
  font-weight: 500;
}

.source-objects-list::-webkit-scrollbar {
  width: 8px;
}

.source-objects-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 4px;
}

.source-objects-list::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 4px;
}

.source-objects-list::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}
</style>
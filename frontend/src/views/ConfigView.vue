<template>
  <div class="config-view">
    <div class="page-header mb-4">
      <h1>
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-gear-wide-connected me-2" viewBox="0 0 16 16">
          <path d="M7.068.727c.243-.97 1.62-.97 1.864 0l.071.286a.96.96 0 001.422.561l.205-.211c.695-.719 1.888-.033 1.613.931l-.08.284a.96.96 0 00.76 1.165l.286.071c.97.243.97 1.62 0 1.864l-.286.071a.96.96 0 00-1.165.76l-.08.284c-.275.964-1.918 1.65-1.613.931l.205-.211a.96.96 0 00-.561-1.422l-.286-.071c-.97-.243-.97-1.62 0-1.864l.286-.071a.96.96 0 001.165-.76l.08-.284c.275-.964 1.918-1.65 1.613-.931l-.205.211a.96.96 0 00.561 1.422l.286.071zM7 8a8 8 0 112 0A8 8 0 017 8z"/>
        </svg>
        系统配置
      </h1>
      <p class="text-muted mb-0">管理迁移配置和系统设置</p>
    </div>
    
    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-arrow-left-right me-1" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M1 11.5a.5.5 0 00.5.5h11.793l-3.147 3.146a.5.5 0 00.708.708l4-4a.5.5 0 000-.708l-4-4a.5.5 0 00-.708.708L13.293 11H1.5a.5.5 0 00-.5.5zm14-7a.5.5 0 00-.5-.5H2.707l3.147-3.146a.5.5 0 10-.708-.708l-4 4a.5.5 0 000 .708l4 4a.5.5 0 00.708-.708L2.707 4H14.5a.5.5 0 00.5-.5z"/>
              </svg>
              迁移配置
            </h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载配置中...</p>
            </div>
            <div v-else-if="migrationSettings">
              <form @submit.prevent="saveMigrationSettings">
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-fonts me-1" viewBox="0 0 16 16">
                      <path d="M12.258 3h-8.51l-.083 2.46h.479c.26-1.544.758-1.783 2.693-1.845l.424-.013v7.827c0 .663-.144.82-1.3.923v.52h4.082v-.52c-1.162-.103-1.306-.26-1.306-.923V3.602l.431.013c1.934.062 2.434.301 2.693 1.846h.479L12.258 3z"/>
                    </svg>
                    默认标识符大小写策略
                  </label>
                  <select v-model="migrationSettings.default_identifier_case" class="form-select">
                    <option value="lower">全部小写</option>
                    <option value="upper">全部大写</option>
                    <option value="preserve">保持原样</option>
                  </select>
                </div>
                
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-triangle me-1" viewBox="0 0 16 16">
                      <path d="M8.982 1.566a1.13 1.13 0 00-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 01-1.1 0L7.1 5.995A.905.905 0 018 5zm.002 6a1 1 0 110 2 1 1 0 010-2z"/>
                    </svg>
                    默认冲突处理策略
                  </label>
                  <select v-model="migrationSettings.default_conflict_strategy" class="form-select">
                    <option value="error">遇到冲突时报错</option>
                    <option value="replace">删除并替换已存在对象</option>
                    <option value="skip">跳过已存在对象</option>
                    <option value="append">追加数据（仅适用于表）</option>
                    <option value="truncate">清空表并重新加载数据</option>
                  </select>
                </div>
                
                <div class="mb-4">
                  <div class="form-check form-switch">
                    <input v-model="migrationSettings.enable_batch_migration" type="checkbox" 
                           class="form-check-input" id="enableBatch">
                    <label class="form-check-label" for="enableBatch">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-layers me-1" viewBox="0 0 16 16">
                        <path d="M8 1a.5.5 0 01.5.5v13a.5.5 0 01-1 0v-13A.5.5 0 018 1zM.5 8a.5.5 0 01.5-.5h13a.5.5 0 010 1H1a.5.5 0 01-.5-.5z"/>
                        <path d="M1.5 8a.5.5 0 01.5-.5h13a.5.5 0 010 1H2a.5.5 0 01-.5-.5z"/>
                      </svg>
                      启用批量迁移
                    </label>
                  </div>
                </div>
                
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-stack me-1" viewBox="0 0 16 16">
                      <path d="M1 3.5a.5.5 0 01.5-.5h13a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-13a.5.5 0 01-.5-.5v-1zM1 8a.5.5 0 01.5-.5h13a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-13a.5.5 0 01-.5-.5v-1zM1 12.5a.5.5 0 01.5-.5h13a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-13a.5.5 0 01-.5-.5v-1z"/>
                    </svg>
                    批量大小
                  </label>
                  <input v-model.number="migrationSettings.batch_size" type="number" class="form-control" min="1">
                </div>
                
                <button type="submit" class="btn btn-primary w-100" :disabled="saving">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-lg me-2" viewBox="0 0 16 16">
                    <path d="M12.736 3.97a.733.733 0 011.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 01-1.065.02L3.217 8.384a.757.757 0 010-1.06.733.733 0 011.047 0l3.052 3.093 5.4-6.425a.247.247 0 01.02-.022z"/>
                  </svg>
                  {{ saving ? '保存中...' : '保存配置' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-lg-6">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-sliders me-1" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M2 10.5a.5.5 0 01.5-.5h3a.5.5 0 010 1h-3a.5.5 0 01-.5-.5zm0-3a.5.5 0 01.5-.5h7a.5.5 0 010 1h-7a.5.5 0 01-.5-.5zm0-3a.5.5 0 01.5-.5h11a.5.5 0 010 1h-11a.5.5 0 01-.5-.5zm10.854 6.354a.5.5 0 010-.708l2-2a.5.5 0 01.708.708l-1.5 1.5 1.5 1.5a.5.5 0 01-.708.708l-2-2z"/>
              </svg>
              系统设置
            </h5>
          </div>
          <div class="card-body">
            <div v-if="loading" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载设置中...</p>
            </div>
            <div v-else-if="systemSettings">
              <form @submit.prevent="saveSystemSettings">
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-terminal me-1" viewBox="0 0 16 16">
                      <path d="M6 9a.5.5 0 01.5-.5h3a.5.5 0 010 1h-3a.5.5 0 01-.5-.5zM1.5 0h13a1.5 1.5 0 011.5 1.5V13a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5V1.5A1.5 1.5 0 011.5 0zM1 1.5V13a.5.5 0 00.5.5h13a.5.5 0 00.5-.5V1.5a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5z"/>
                      <path d="M3.71 8.86a.5.5 0 01.634-.06l5.663 4.413a.5.5 0 01-.142.854l-5.5-4.22a.5.5 0 01-.055-.987zM5.71 8.86a.5.5 0 01-.634-.06l-5.663 4.413a.5.5 0 01.142.854l5.5-4.22a.5.5 0 01.055-.987z"/>
                    </svg>
                    日志级别
                  </label>
                  <select v-model="systemSettings.log_level" class="form-select">
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </div>
                
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-diagram-3 me-1" viewBox="0 0 16 16">
                      <path fill-rule="evenodd" d="M6 3.5A1.5 1.5 0 017.5 2h1A1.5 1.5 0 0110 3.5v1A1.5 1.5 0 018.5 6v1H11a.5.5 0 01.5.5v1a.5.5 0 01-1 0V8h-5v.5a.5.5 0 01-1 0v-1A.5.5 0 015 6h2.5V5A1.5 1.5 0 016 3.5zM8.5 5a.5.5 0 01.5-.5V3.5a.5.5 0 00-.5-.5h-1a.5.5 0 00-.5.5V4.5a.5.5 0 01.5.5h1zM0 11.5A1.5 1.5 0 011.5 10h1A1.5 1.5 0 014 11.5v1A1.5 1.5 0 012.5 14h-1A1.5 1.5 0 010 12.5v-1zm1.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zm10.5.5A1.5 1.5 0 0113.5 10h1a1.5 1.5 0 011.5 1.5v1a1.5 1.5 0 01-1.5 1.5h-1A1.5 1.5 0 0112 12.5v-1zm1.5-.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1z"/>
                    </svg>
                    最大并发任务数
                  </label>
                  <input v-model.number="systemSettings.max_concurrent_tasks" type="number" 
                         class="form-control" min="1">
                </div>
                
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clock-history me-1" viewBox="0 0 16 16">
                      <path d="M8.515 1.019A7 7 0 008 1V0a8 8 0 01.589.022l-.074.997zm2.004.45a7.003 7.003 0 00-.985-.299l.219-.976c.383.086.76.2 1.126.342l-.36.933zm1.37.71a7.01 7.01 0 00-.439-.27l.493-.87a8.025 8.025 0 01.979.654l-.615.789a6.996 6.996 0 00-.418-.302zm1.834 1.79a6.99 6.99 0 00-.653-.796l.79-.615c.32.312.612.648.877 1.006l-.814.405zm-.744 1.352a7.08 7.08 0 00-.214-.468l.893-.45a7.976 7.976 0 01.45 1.088l-.95.313a7.023 7.023 0 00-.179-.483zm-.09 2.019a6.99 6.99 0 00.053-.958l.997.057a7.976 7.976 0 01-.06 1.098l-.99-.197zm-.22 2.017a6.996 6.996 0 00-.317-.906l.918-.395a7.976 7.976 0 01.448 1.042l-.99.259zm-.535 1.878a6.99 6.99 0 00-.547-.783l.811-.587a7.976 7.976 0 01.778.947l-.816.423zm-.942 1.555a6.99 6.99 0 00-.727-.58l.6-.783a7.976 7.976 0 01.965.75l-.668.613zm-1.274.975a6.99 6.99 0 00-.838-.325l.348-.937a7.976 7.976 0 01.989.428l-.499.834zm-1.522.438a6.99 6.99 0 00-.874-.082l.053-.998a7.976 7.976 0 01.932.088l-.111.992zm-1.532.05a6.99 6.99 0 00-.828.143l-.193-.981a7.976 7.976 0 01.902-.156l.119.994zm-1.447.322a6.99 6.99 0 00-.724.29l-.415-.91a7.976 7.976 0 01.816-.327l.323.947zm-1.265.555a6.99 6.99 0 00-.576.387l-.587-.809a7.976 7.976 0 01.678-.454l.485.876zm-1.018.694a6.99 6.99 0 00-.394.435l-.712-.704a7.976 7.976 0 01.48-.504l.626.773zm-.765.746a6.99 6.99 0 00-.195.438l-.8-.6a7.976 7.976 0 01.263-.502l.732.664zm-.48.712a6.99 6.99 0 00.006.4l-.944-.329a7.976 7.976 0 01.05-.518l.888.447zm-.16.65a6.99 6.99 0 00.197.352l-.874.486a7.976 7.976 0 01-.254-.445l.931-.393zm.16.65a6.99 6.99 0 01.352.197l-.486.874a7.976 7.976 0 01-.445-.254l.579-.817zm.48.712a6.99 6.99 0 01.438.195l-.6.8a7.976 7.976 0 01-.502-.263l.664-.732zm.765.746a6.99 6.99 0 01.435.394l-.704.712a7.976 7.976 0 01-.504-.48l.773-.626zm1.018.694a6.99 6.99 0 01.387.576l-.809.587a7.976 7.976 0 01-.454-.678l.876-.485zm1.265.555a6.99 6.99 0 01.29.724l-.91.415a7.976 7.976 0 01-.327-.816l.947-.323zm1.447.322a6.99 6.99 0 01.143.828l-.981.193a7.976 7.976 0 01-.156-.902l.994-.119zm1.532.05a6.99 6.99 0 01.082.874l-.937.348a7.976 7.976 0 01-.088-.932l.993-.29zm1.522.438a6.99 6.99 0 01.325.838l-.834.499a7.976 7.976 0 01-.428-.989l.937-.348zm1.274.975a6.99 6.99 0 01.58.727l-.783.6a7.976 7.976 0 01-.75-.965l.953-.362zm.942 1.555a6.99 6.99 0 01.727.547l-.587.811a7.976 7.976 0 01-.947-.778l.807-.58zm.535 1.878a6.99 6.99 0 01.783.535l-.423.816a7.976 7.976 0 01-.965-.778l.605-.573zm.09 2.019a6.99 6.99 0 01.906.317l-.395.918a7.976 7.976 0 01-1.042-.448l.531-.787zm.22 2.017a6.99 6.99 0 01.958.053l-.057.997a7.976 7.976 0 01-1.098-.06l.197-.99zm-.09 2.017a6.99 6.99 0 01.468.214l-.45.893a7.976 7.976 0 01-1.088-.45l.57-.657zm-.535 1.878a6.99 6.99 0 01.796.653l-.789.615a7.976 7.976 0 01-1.006-.877l.999-.391zm-.942 1.555a6.99 6.99 0 01.796.439l-.615.79a7.976 7.976 0 01-.654-.979l.473-.25zm-1.274.975a6.99 6.99 0 01.299.985l-.976.219a7.976 7.976 0 01-.342-1.126l1.019-.078zm-1.522.438a6.99 6.99 0 01.27.439l-.87.493a7.976 7.976 0 01-.654-.979l1.254-.047zm-1.447.322a6.99 6.99 0 01.18.483l-.913.405a7.976 7.976 0 01-.313-.95l1.046.062zm-1.532.05a6.99 6.99 0 01.082.958l-.997-.057a7.976 7.976 0 01-.06-1.098l.975.197zm-1.522-.438a6.99 6.99 0 01-.214.468l-.893-.45a7.976 7.976 0 01.45-1.088l.657 1.07zm-1.265-.555a6.99 6.99 0 01-.387.576l-.809-.587a7.976 7.976 0 01.678-.454l.485.465zm-1.018-.694a6.99 6.99 0 01-.435.394l-.704-.712a7.976 7.976 0 01.504-.48l.635.798zm-.765-.746a6.99 6.99 0 01-.195.438l-.8-.6a7.976 7.976 0 01.263-.502l.732.664zm-.48-.712a6.99 6.99 0 01.006.4l-.944-.329a7.976 7.976 0 01.05-.518l.888.447zm-.16-.65a6.99 6.99 0 01.197.352l-.874.486a7.976 7.976 0 01-.254-.445l.931-.393zm.16-.65a6.99 6.99 0 01.352-.197l-.486-.874a7.976 7.976 0 01-.445.254l.579.817zm.48-.712a6.99 6.99 0 01.438-.195l-.6-.8a7.976 7.976 0 01-.502.263l.664.732zm.765-.746a6.99 6.99 0 01.435-.394l-.704-.712a7.976 7.976 0 01-.504.48l.773.626zm1.018-.694a6.99 6.99 0 01.387-.576l-.809-.587a7.976 7.976 0 01-.454.678l.876.485zm1.265-.555a6.99 6.99 0 01.29-.724l-.91-.415a7.976 7.976 0 01-.327.816l.947.323zm1.447-.322a6.99 6.99 0 01.143-.828l-.981-.193a7.976 7.976 0 01-.156.902l.994.119zm1.532-.05a6.99 6.99 0 01.082-.874l-.937-.348a7.976 7.976 0 01-.088.932l.993.29zm1.522-.438a6.99 6.99 0 01.325-.838l-.834-.499a7.976 7.976 0 01-.428.989l.937.348zm1.274-.975a6.99 6.99 0 01.58-.727l-.783-.6a7.976 7.976 0 01-.75.965l.953.362zm.942-1.555a6.99 6.99 0 01.727-.547l-.587-.811a7.976 7.976 0 01-.947.778l.807.58zm.535-1.878a6.99 6.99 0 01.783-.535l-.423-.816a7.976 7.976 0 01-.965.778l.605.573zm.09-2.019a6.99 6.99 0 01.906-.317l-.395-.918a7.976 7.976 0 01-1.042.448l.531.787zm.22-2.017a6.99 6.99 0 01.958-.053l-.057-.997a7.976 7.976 0 01-1.098.06l.197.99zm-.09-2.017a6.99 6.99 0 01.468-.214l-.45-.893a7.976 7.976 0 01-1.088.45l.57.657zm-.535-1.878a6.99 6.99 0 01.796-.653l-.789-.615a7.976 7.976 0 01-1.006.877l.999.391zm-.942-1.555a6.99 6.99 0 01.796-.439l-.615-.79a7.976 7.976 0 01-.654.979l.473.25zm-1.274-.975a6.99 6.99 0 01.299-.985l-.976-.219a7.976 7.976 0 01-.342 1.126l1.019.078zm-1.522-.438a6.99 6.99 0 01.27-.439l-.87-.493a7.976 7.976 0 01-.654.979l1.254.047zm-1.447-.322a6.99 6.99 0 01.18-.483l-.913-.405a7.976 7.976 0 01-.313.95l1.046-.062zm-1.532-.05a6.99 6.99 0 01.082-.958l-.997.057a7.976 7.976 0 01-.06 1.098l.975-.197zm-1.522.438a6.99 6.99 0 01-.214-.468l-.893.45a7.976 7.976 0 01.45 1.088l.657-1.07zm-1.265.555a6.99 6.99 0 01-.387-.576l-.809.587a7.976 7.976 0 01.678.454l.485-.465zm-1.018.694a6.99 6.99 0 01-.435-.394l-.704.712a7.976 7.976 0 01.504.48l.635-.798zm-.765.746a6.99 6.99 0 01-.195-.438l-.8.6a7.976 7.976 0 01.263.502l.732-.664zm-.48.712a6.99 6.99 0 01.006-.4l-.944.329a7.976 7.976 0 01.05.518l.888-.447z"/>
                    </svg>
                    任务超时时间（秒）
                  </label>
                  <input v-model.number="systemSettings.task_timeout" type="number" 
                         class="form-control" min="1">
                </div>
                
                <div class="mb-4">
                  <div class="form-check form-switch">
                    <input v-model="systemSettings.enable_auto_retry" type="checkbox" 
                           class="form-check-input" id="enableRetry">
                    <label class="form-check-label" for="enableRetry">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-repeat me-1" viewBox="0 0 16 16">
                        <path d="M11.534 7h3.932a.25.25 0 01.192.41l-1.966 2.36a.25.25 0 01-.384 0l-1.966-2.36a.25.25 0 01.192-.41h3.932a.5.5 0 000-1H11.534a1.5 1.5 0 00-1.5 1.5v3.932a.25.25 0 01-.41.192l-2.36-1.966a.25.25 0 010-.384l2.36-1.966a.25.25 0 01.41.192V8.5a.5.5 0 001 0v-3.932a1.5 1.5 0 00-1.5-1.5zM1 4.5a1.5 1.5 0 011.5-1.5h3.932a.25.25 0 01.192.41l-1.966 2.36a.25.25 0 01-.384 0l-1.966-2.36a.25.25 0 01.192-.41H2.5a.5.5 0 000-1h3.932a1.5 1.5 0 001.5 1.5v3.932a.25.25 0 01-.41.192l-2.36-1.966a.25.25 0 010-.384l2.36-1.966a.25.25 0 01.41.192V8.5a.5.5 0 001 0v-3.932a1.5 1.5 0 00-1.5-1.5z"/>
                      </svg>
                      启用自动重试
                    </label>
                  </div>
                </div>
                
                <div class="mb-4">
                  <label class="form-label">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-counterclockwise me-1" viewBox="0 0 16 16">
                      <path fill-rule="evenodd" d="M8 3a5 5 0 104.546 2.914.5.5 0 01.908-.417A6 6 0 118 2v1z"/>
                      <path d="M8 4.466V.534a.25.25 0 01.41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 018 4.466z"/>
                    </svg>
                    最大重试次数
                  </label>
                  <input v-model.number="systemSettings.max_retry_count" type="number" 
                           class="form-control" min="0">
                </div>
                
                <button type="submit" class="btn btn-primary w-100" :disabled="saving">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-lg me-2" viewBox="0 0 16 16">
                    <path d="M12.736 3.97a.733.733 0 011.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 01-1.065.02L3.217 8.384a.757.757 0 010-1.06.733.733 0 011.047 0l3.052 3.093 5.4-6.425a.247.247 0 01.02-.022z"/>
                  </svg>
                  {{ saving ? '保存中...' : '保存设置' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="row mt-4">
      <div class="col-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="bi bi-terminal me-1" viewBox="0 0 16 16">
                <path d="M6 9a.5.5 0 01.5-.5h3a.5.5 0 010 1h-3a.5.5 0 01-.5-.5zM1.5 0h13a1.5 1.5 0 011.5 1.5V13a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 010 14.5V1.5A1.5 1.5 0 011.5 0zM1 1.5V13a.5.5 0 00.5.5h13a.5.5 0 00.5-.5V1.5a.5.5 0 00-.5-.5h-13a.5.5 0 00-.5.5z"/>
                <path d="M3.71 8.86a.5.5 0 01.634-.06l5.663 4.413a.5.5 0 01-.142.854l-5.5-4.22a.5.5 0 01-.055-.987zM5.71 8.86a.5.5 0 01-.634-.06l-5.663 4.413a.5.5 0 01.142.854l5.5-4.22a.5.5 0 01.055-.987z"/>
              </svg>
              迁移日志
            </h5>
            <button @click="loadLogs" class="btn btn-outline-secondary btn-sm">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" class="bi bi-arrow-clockwise me-1" viewBox="0 0 16 16">
                <path fill-rule="evenodd" d="M8 3a5 5 0 104.546 2.914.5.5 0 01.908-.417A6 6 0 118 2v1z"/>
                <path d="M8 4.466V.534a.25.25 0 01.41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 018 4.466z"/>
              </svg>
              刷新日志
            </button>
          </div>
          <div class="card-body">
            <div v-if="loadingLogs" class="text-center py-5">
              <div class="spinner-border text-primary" role="status"></div>
              <p class="mt-3 text-muted">加载日志中...</p>
            </div>
            <div v-else>
              <div class="log-container">
                <pre class="log-content">{{ logs || '暂无日志' }}</pre>
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
import { configApi, logsApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const loadingLogs = ref(false)
const migrationSettings = ref<any>(null)
const systemSettings = ref<any>(null)
const logs = ref('')

const loadSettings = async () => {
  loading.value = true
  try {
    const [migrationRes, systemRes] = await Promise.all([
      configApi.getMigrationSettings(),
      configApi.getSystemSettings(),
    ])
    
    migrationSettings.value = migrationRes.data || {
      default_identifier_case: 'lower',
      default_conflict_strategy: 'error',
      enable_batch_migration: false,
      batch_size: 100,
    }
    
    systemSettings.value = systemRes.data || {
      log_level: 'INFO',
      max_concurrent_tasks: 5,
      task_timeout: 3600,
      enable_auto_retry: false,
      max_retry_count: 3,
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}

const saveMigrationSettings = async () => {
  saving.value = true
  try {
    await configApi.saveMigrationSettings(migrationSettings.value)
    alert('保存成功')
  } catch (error) {
    console.error('Failed to save migration settings:', error)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}

const saveSystemSettings = async () => {
  saving.value = true
  try {
    await configApi.saveSystemSettings(systemSettings.value)
    alert('保存成功')
  } catch (error) {
    console.error('Failed to save system settings:', error)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    const res = await logsApi.getLogs()
    logs.value = res.data.logs || ''
  } catch (error) {
    console.error('Failed to load logs:', error)
  } finally {
    loadingLogs.value = false
  }
}

onMounted(() => {
  loadSettings()
  loadLogs()
})
</script>

<style scoped>
.config-view {
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

.card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 50px rgba(0, 0, 0, 0.15);
}

.card-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  border: none;
  padding: 1rem 1.5rem;
}

.form-label {
  font-weight: 600;
  color: #4a5568;
  display: flex;
  align-items: center;
}

.form-control,
.form-select {
  border-radius: 0.5rem;
  border: 2px solid #e2e8f0;
  padding: 0.75rem 1rem;
  transition: all 0.3s ease;
}

.form-control:focus,
.form-select:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}

.form-check-input {
  width: 3rem;
  height: 1.5rem;
  border-radius: 1rem;
  background-color: #e2e8f0;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.form-check-input:checked {
  background-color: #667eea;
}

.form-check-label {
  cursor: pointer;
  font-weight: 500;
  color: #4a5568;
  display: flex;
  align-items: center;
}

.btn {
  border-radius: 0.5rem;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  transition: all 0.3s ease;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline-secondary {
  border: 2px solid #e2e8f0;
  color: #4a5568;
}

.btn-outline-secondary:hover {
  background-color: #f7fafc;
  border-color: #cbd5e0;
}

.log-container {
  background: #1e1e1e;
  border-radius: 0.5rem;
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.3);
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

.spinner-border {
  width: 3rem;
  height: 3rem;
  border-width: 0.3rem;
}

.spinner-border.text-primary {
  border-color: #667eea;
  border-right-color: transparent;
}
</style>
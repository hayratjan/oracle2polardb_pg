# 前端 TypeScript 编译错误修复说明

> 修复日期：2026-07-02
> 修复范围：`frontend/` 下 `npx vue-tsc --noEmit` 报告的全部 51 个 TypeScript 编译错误

## 一、修复总览

执行 `npx vue-tsc --noEmit` 后从 51 个错误降至 0 个错误，未改变任何业务逻辑，仅做类型安全的适配与未使用标识符的清理。

| 文件 | 错误数 | 修复方式 |
|------|-------:|----------|
| `src/components/TargetEnvWizard.vue` | 36 | 定义 `LocalTargetProvisioning` 类型 |
| `src/views/TaskDetailView.vue` | 11 | 类型断言 `as [string, any][]` / `as any` |
| `src/views/TaskMonitorView.vue` | 2 | 索引断言 + 删除未用函数 |
| `src/router/index.ts` | 1 | 未使用参数加下划线前缀 |
| `src/views/CreateTaskView.vue` | 1 | 未使用参数加下划线前缀 |
| **合计** | **51** | |

## 二、逐文件修复说明

### 1. TargetEnvWizard.vue（36 个错误）

**错误现象**：模板中 `local.database.mode`、`local.tablespace.mode`、`local.user.mode`、`local.schema.mode` 等访问全部报 `__VLS_ctx.local.xxx is possibly 'undefined'`。

**根因**：`local` 用 `reactive<TargetProvisioningConfig>` 声明，而 `TargetProvisioningConfig` 接口中 `database/tablespace/user/schema` 都是可选字段（`?: TargetResourceConfig`）。虽然运行时已用默认对象初始化，但类型层面仍可能为 `undefined`，vue-tsc 严格模板检查据此报错。

**修复方案**：在 `src/components/TargetEnvWizard.vue` 中新增局部类型 `LocalTargetProvisioning`，通过 `Omit` + 交叉类型把这 4 个字段改为必填：

```ts
type LocalTargetProvisioning = Omit<TargetProvisioningConfig, 'database' | 'tablespace' | 'user' | 'schema'> & {
  database: TargetResourceConfig
  tablespace: TargetResourceConfig
  user: TargetResourceConfig
  schema: TargetResourceConfig
}
```

`local` 改用 `reactive<LocalTargetProvisioning>`。由于 `LocalTargetProvisioning` 是 `TargetProvisioningConfig` 的子类型，`emit('update:config', ...)`、`payload`、`getResolvedTarget` 等处的赋值和传递均兼容，无需改动业务逻辑。

### 2. TaskDetailView.vue（11 个错误）

**错误现象**：
- 第 310-323 行：`info.total_rows`、`info.migrated_rows`、`info.progress` 报 `Property 'xxx' does not exist on type 'object'`。
- 第 370-376 行：`migrationReport.manual_review_items?.length`、`migrationReport.summary?.manual_review_count`、`migrationReport.row_checks?.length` 报 `Property 'xxx' does not exist on type '{}'`。

**根因**：
- `viewProgressEntries` 返回 `Object.entries(vp)`，其元素类型为 `[string, unknown]`。模板里 `typeof info === 'object'` 把 `unknown` 收窄为 `object`，而 `object` 类型上不存在具体属性。
- `migrationReport` 计算属性返回 `Record<string, unknown> | null`，对其属性做 `?.length` 访问时类型推断失败。

**修复方案**：
- `viewProgressEntries` 末尾加 `as [string, any][]`，使 `info` 直接为 `any`，绕过窄化导致的 `object` 限制。
- `migrationReport` 把 `r as Record<string, unknown>` 改为 `r as any`，便于在模板里直接访问 `manual_review_items`、`row_checks`、`summary` 等动态字段。

### 3. TaskMonitorView.vue（2 个错误）

**错误现象**：
- 第 31 行：`data.summary[item.key as keyof typeof data.summary]` 报 `Element implicitly has an 'any' type because expression of type 'string' can't be used to index type ...`。
- 第 523 行：`getIncrementalLabel` 声明但从未使用（TS6133）。

**修复方案**：
- 第 31 行改为 `(data.summary as any)[item.key]`，使用 `any` 断言绕过索引签名限制。
- 删除整个未使用的 `getIncrementalLabel` 函数（其依赖的 `TaskMonitorItem` 类型在 `selectTask`、`formatViewProgress` 中仍被使用，无需调整 import）。

### 4. router/index.ts（1 个错误）

`router.beforeEach(async (to, from, next) => {...})` 中 `from` 形参未使用。按 TypeScript 习惯将形参改名为 `_from`，调用方无需调整。

### 5. CreateTaskView.vue（1 个错误）

`getObjectIcon(obj: string)` 形参 `obj` 未被函数体使用，改名为 `_obj`。下划线前缀的形参默认不会被 `noUnusedParameters` 报告，调用处 `getObjectIcon(obj)` 保持不变。

## 三、验证

修复完成后在 `frontend/` 目录执行：

```bash
npx vue-tsc --noEmit
```

退出码为 `0`，输出为空，确认 0 错误。

## 四、相关建议与后续优化

1. **接口字段可选性收敛**：`TargetProvisioningConfig` 中 `database/tablespace/user/schema` 设为可选是 API 层面的合理默认，但前端组件若始终需要这些字段，建议在组件 props/响应式状态层用更严格的局部类型（如本修复引入的 `LocalTargetProvisioning`），避免在模板里到处加可选链。可在其他用到 `TargetProvisioningConfig` 的视图（`TableMigrationView.vue`、`FullDatabaseMigrationView.vue`）统一此类做法。

2. **`any` 的替代方案**：`TaskDetailView.vue` 中 `viewProgressEntries` 和 `migrationReport` 用了 `any` 断言。建议后续为后端返回的 `view_progress` 和 `migration_report` 定义明确的 TS 接口（例如 `interface ViewProgressInfo { total_rows?: number; migrated_rows?: number; progress?: number }`），改用具体类型断言，兼顾类型安全与可维护性。

3. **`noUnusedLocals` / `noUnusedParameters` 工程化**：本次有 2 处未使用变量/参数错误。建议在 CI 中加入 `vue-tsc --noEmit` 检查门禁，避免此类低级问题再次合入。

4. **`TaskMonitorView.summary` 索引签名**：可考虑在 `TaskMonitorResponse.summary` 类型上补充索引签名或使用 `Record<string, number>`，使模板里 `summary[item.key]` 直接类型安全，无需 `as any`。

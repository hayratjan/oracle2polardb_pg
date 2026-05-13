# is_migrate = True 数据表结构说明

本文档列出 `Api/models.py` 中所有标记为 `class IsMigrate: is_migrate = True` 的模型（表），包含表间关系、外键以及每个字段的类型与长度说明，便于数据迁移与结构理解。

---

## 一、表关系总览

### 1.1 核心依赖关系

```
GlaAcctSetTemplate (模板账套)
├── GlaAccountClsTemplate.acct_template_code → 模板账套编号
├── GlaAccountClsEleTemplate.acct_template_code → 模板账套编号
└── GlaAcctSet.acct_template_code → 模板账套编号

GlaAcctSet (账套)
├── GLAAccountCls.acct_set_code → 账套编号
├── GlaVouVchrtype.acct_set_code → 账套编号
├── GlaVouHead.acct_set_code → 账套编号
├── AccountBookName.acct_set_code → 账套
├── ReportForms.acct_set_code → 账套
├── ElePrintSetup.acct_set_code → 账套
└── ElePrintVoucher.acct_set_code → 账套

GlaAccountClsTemplate (模板会计科目)
└── GlaAccountClsEleTemplate.account_cls_id → 科目唯一标识

GLAAccountCls (单位会计科目)
├── GLAAccountClsEle.account_cls → 科目
└── GlaVouDetail.gov_acct_cls → 科目

GlaVouHead (凭证主表)
└── GlaVouDetail.vou → 凭证主表

EleCatalog (基础代码目录)
├── EleUnion.ele_catalog → 基础代码目录
└── ElePrintSetup.ele_catalog_id → 基础代码目录

GlaVouDetail (凭证分录) 引用的辅助/基础表
├── EleBgtproject (pro) - 项目
├── BasDepBgtEco (dep_bgt_eco) - 部门支出经济分类
├── BasGovBgtEco (gov_bgt_eco) - 政府支出经济分类
├── BasInternalDep (internal_dep) - 单位内部机构
├── BasExpFunc (exp_func) - 支出功能分类
├── EleFundtype (fund_type) - 资金性质
├── ElePaytype (pay_type) - 支付方式
├── EleDivBgtEco (acc_item01) - 自定义辅助01
├── EleSrkm (acc_item02) - 自定义辅助02
├── EleCosttype (acc_item05) - 自定义辅助05
├── EleWlDiv (acc_item06) - 自定义辅助06
├── EleWlPerson (acc_item07) - 自定义辅助07
├── EleUnion (acc_item08) - 自定义辅助08
└── EleProcat (acc_item09) - 自定义辅助09
```

### 1.2 无外键的独立表（仅逻辑关联或通过代码关联）

- **GlaAccountClsEnum**：单位会计要素枚举，通过 `acct_template_code` 与模板账套逻辑关联（未建 FK）。
- **EleBgtproject、EleCosttype、EleDivBgtEco、EleFundtype、ElePaytype、EleProcat、EleSrkm、EleWlDiv、EleWlPerson**：各类辅助/元素代码表，通过 `ele_catalog_id`、`acct_set_code` 等与账套/目录逻辑关联。
- **BasDepBgtEco、BasExpFunc、BasGovBgtEco、BasInternalDep**：部门经济分类、支出功能、政府经济分类、内部机构等基础代码表。

---

## 二、各表字段与类型说明

### 2.1 gla_account_cls_template（模板账套会计科目）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| account_cls_id | CharField | 38, PK | 科目唯一标识 |
| set_year | CharField | 4 | 会计年度 |
| mof_div_code | CharField | 9 | 财政区划代码 |
| mof_div_name | CharField | 360, null | 财政区划名称 |
| **acct_template_code** | **ForeignKey → GlaAcctSetTemplate** | 关联 acct_template_code | 模板账套编号 |
| acct_template_name | CharField | 100 | 模板账套名称 |
| agency_code | CharField | 21, null | 单位代码 |
| agency_name | CharField | 300, null | 单位名称 |
| gov_acct_cls_code | CharField | 50 | 单位会计科目代码 |
| gov_acct_cls_name | CharField | 100 | 单位会计科目名称 |
| parent_id | CharField | 38, null | 父级唯一标识（自关联逻辑） |
| level_no | IntegerField | - | 级次 |
| is_leaf | IntegerField | 0/1 | 是否末级 |
| is_enabled | IntegerField | 0/1 | 是否启用 |
| balance_dir | IntegerField | 1借/-1贷 | 余额方向 |
| gov_acct_cls_enum_code | CharField | 1 | 单位会计要素代码 |
| gov_acct_cls_enum_name | CharField | 30 | 单位会计要素名称 |
| executive_acc | CharField | 10 | 执行会计制度类型 |
| agency_type_code | CharField | 10, null | 单位类型 |
| currency_code | CharField | 3, null | 币种代码 |
| currency_name | CharField | 100, null | 币种名称 |
| is_cur | IntegerField | 0/1 | 是否外币核算 |
| is_qty | IntegerField | 0/1 | 是否数量核算 |
| remark | CharField | 2000, null | 备注 |
| is_standard | IntegerField | 1/2 | 是否标准(标准/扩展代码集) |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | IntegerField | 0/1 | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| is_last_inst | IntegerField | 0/1 | 是否终审 |

---

### 2.2 gla_account_cls_ele_template（模板账套会计科目启用辅助核算项表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| cls_ele_id | CharField | 256, PK | 对应关系ID |
| mof_div_code | CharField | 9, null | 财政区划代码 |
| mof_div_name | CharField | 360, null | 财政区划名称 |
| set_year | CharField | 4 | 会计年度 |
| agency_code | CharField | 21, null | 单位代码 |
| agency_name | CharField | 300, null | 单位名称 |
| **acct_template_code** | **ForeignKey → GlaAcctSetTemplate** | 关联 acct_template_code | 模板账套编号 |
| acct_template_name | CharField | 100 | 模板账套名称 |
| **account_cls_id** | **ForeignKey → GlaAccountClsTemplate** | 关联 account_cls_id | 科目唯一标识 |
| gov_acct_cls_code | CharField | 50 | 单位会计科目代码 |
| gov_acct_cls_name | CharField | 100 | 单位会计科目名称 |
| element_code | CharField | 42 | 启用的辅助核算项代码 |
| element_name | CharField | 100, null | 启用的辅助核算项名称 |
| accitem_code | CharField | 38 | 辅助项存储字段名称 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | IntegerField | 0/1 | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| is_last_inst | IntegerField | 0/1 | 是否终审 |

---

### 2.3 ele_bgtproject（预算项目元素表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 64, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 32 | 账套编号 |
| ele_code | CharField | 32, null | 元素代码 |
| ele_name | CharField | 100, null | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 64, null | 父级ID |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf | DecimalField | (10,2), null | 是否末级 |
| is_last_inst | DecimalField | (10,2), null | 是否终审 |
| start_date | DateTimeField | - | 启用日期 |
| end_date | DateTimeField | - | 停用日期 |
| is_enabled | DecimalField | (10,2), null | 是否启用 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| biz_key | CharField | 32 | 业务键 |
| ele_lname | CharField | 1000, null | 名称逐级显示 |

---

### 2.4 ele_costtype（费用类型元素表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 64, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 32 | 账套编号 |
| ele_code | CharField | 100, null | 元素代码 |
| ele_name | CharField | 100, null | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 64, null | 父级ID |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf | DecimalField | (10,2), null | 是否末级 |
| is_last_inst | DecimalField | (10,2), null | 是否终审 |
| start_date | DateTimeField | - | 启用日期 |
| end_date | DateTimeField | - | 停用日期 |
| is_enabled | DecimalField | (10,2), null | 是否启用 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| biz_key | CharField | 32 | 业务键 |
| ele_lname | CharField | 1000, null | 名称逐级显示 |

---

### 2.5 ele_div_bgt_eco（部门预算经济分类元素表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 32, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 32 | 账套编号 |
| ele_code | CharField | 100, null | 元素代码 |
| ele_name | CharField | 100, null | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 32, null | 父级ID |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf | DecimalField | (10,2), null | 是否末级 |
| is_last_inst | DecimalField | (10,2), null | 是否终审 |
| start_date | DateTimeField | - | 启用日期 |
| end_date | DateTimeField | - | 停用日期 |
| is_enabled | DecimalField | (10,2), null | 是否启用 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| biz_key | CharField | 32 | 业务键 |
| ele_lname | CharField | 1000, null | 名称逐级显示 |

---

### 2.6 ele_fundtype（资金性质元素表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 32, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 255, null | 账套编号 |
| ele_code | CharField | 60 | 元素代码 |
| ele_name | CharField | 100 | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 32, null | 父级ID |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf | DecimalField | (10,2), null | 是否末级 |
| is_last_inst | DecimalField | (10,2), null | 是否终审 |
| start_date | DateTimeField | - | 启用日期 |
| end_date | DateTimeField | - | 停用日期 |
| is_enabled | DecimalField | (10,2), null | 是否启用 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| biz_key | CharField | 32 | 业务键 |
| ele_lname | CharField | 1000, null | 名称逐级显示 |

---

### 2.7 ele_paytype（支付方式元素表）

字段与 **ele_fundtype** 结构一致（ele_id 32, ele_code 60, ele_name 100 等），表名 `ele_paytype`。

---

### 2.8 ele_procat（产品分类元素表）

字段与 **ele_fundtype** 结构一致，表名 `ele_procat`。

---

### 2.9 ele_srkm（收入科目元素表）

字段与 **ele_fundtype** 结构一致，表名 `ele_srkm`。

---

### 2.10 ele_union（代码集统一表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 38, PK | 代码集主键 |
| **ele_catalog** | **ForeignKey → EleCatalog** | db_column=ele_catalog_id | 基础代码目录 |
| fiscal_year | CharField | 4, null | 预算年度 |
| mof_div_code | CharField | 9 | 财政区划代码 |
| mof_div_name | CharField | 360, null | 财政区划名称 |
| ele_code | CharField | 20 | 代码集代码 |
| ele_name | CharField | 100 | 代码集名称 |
| is_standard | IntegerField | - | 是否标准 |
| is_leaf | IntegerField | - | 是否末级 |
| is_last_inst | IntegerField | - | 是否终审 |
| is_enabled | IntegerField | - | 是否启用 |
| parent_id | CharField | 38, null | 父级节点ID |
| level_no | IntegerField | - | 级次 |
| start_date | DateTimeField | - | 启用日期 |
| end_date | DateTimeField | - | 停用日期 |
| update_time | DateTimeField | - | 更新时间 |
| create_time | DateTimeField | - | 创建时间 |
| is_deleted | IntegerField | - | 是否删除 |
| biz_key | CharField | 38, null | 业务唯一标识 |
| acct_set_code | CharField | 38, null | 账套编号 |
| ele_lname | CharField | 1000, null | 名称逐级显示 |

唯一约束：`(ele_catalog, ele_code, fiscal_year, mof_div_code)`。

---

### 2.11 ele_wl_div（物流/划分元素表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 32, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 32, null | 账套编号 |
| ele_code | CharField | 32, null | 元素代码 |
| ele_name | CharField | 200, null | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 32, null | 父级ID |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf / is_last_inst | DecimalField | (10,2), null | 是否末级/是否终审 |
| start_date / end_date | DateTimeField | - | 启用/停用日期 |
| is_enabled | DecimalField | (10,2), null | 是否启用 |
| update_time / create_time | DateTimeField | - | 更新/创建时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| biz_key | CharField | 32 | 业务键 |
| ele_lname | CharField | 1000, null | 名称逐级显示 |

---

### 2.12 ele_wl_person（人员元素表）

与 **ele_wl_div** 类似，其中 `parent_id` 为 CharField(1)。表名 `ele_wl_person`。

---

### 2.13 gla_account_cls_enum（单位会计要素枚举表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| gov_acct_cls_enum_id | CharField | 42, PK | 主键 |
| gov_acct_cls_enum_code | CharField | 10 | 要素代码 |
| gov_acct_cls_enum_name | CharField | 100, null | 要素名称 |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| acct_template_code | CharField | 32 | 模板账套编号（逻辑关联，非 FK） |

---

### 2.14 gla_vou_vchrtype（单位会计凭证类型表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| vchr_type_id | CharField | 32, PK | 凭证类型ID |
| set_year | CharField | 100, null | 会计年度 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | 关联 acct_set_code | 账套编码 |
| agency_acct_voucher_type_code | CharField | 10, null | 凭证类型编码 |
| agency_acct_voucher_type_name | CharField | 20, null | 凭证类型名称 |

---

### 2.15 gla_account_cls（单位会计科目表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| account_cls_id | CharField | 64, PK | 科目唯一标识 |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | 关联 acct_set_code | 账套编号 |
| acct_set_name | CharField | 60, null | 账套名称 |
| agency_code | CharField | 32, null | 单位代码 |
| agency_name | CharField | 100, null | 单位名称 |
| gov_acct_cls_code | CharField | 32 | 单位会计科目代码 |
| gov_acct_cls_name | CharField | 100 | 单位会计科目名称 |
| parent_id | CharField | 64, null | 父级唯一标识 |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf | DecimalField | (10,0), null | 是否末级 |
| is_enabled | DecimalField | (10,0), null | 是否启用 |
| balance_dir | DecimalField | (10,0), null | 余额方向 |
| gov_acct_cls_enum_code | CharField | 30, null | 单位会计要素代码 |
| gov_acct_cls_enum_name | CharField | 100, null | 单位会计要素名称 |
| executive_acc | CharField | 2, null | 执行会计制度类型 |
| agency_type_code | CharField | 1, null | 单位类型 |
| currency_code / currency_name | CharField | 255, null | 币种代码/名称 |
| is_cur / is_qty | CharField | 255, null | 是否外币/数量核算 |
| remark | CharField | 255, null | 备注 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| update_time / create_time | CharField | 255, null | 更新/创建时间 |
| is_deleted | CharField | 255, null | 是否删除 |
| is_last_inst | DecimalField | (10,2), null | 是否终审 |
| gov_acct_cls_lname | CharField | 1000, null | 科目名称逐级显示 |

---

### 2.16 gla_account_cls_ele（单位会计科目启用辅助核算项表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| cls_ele_id | CharField | 429, PK | 对应关系ID |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| set_year | CharField | 100, null | 会计年度 |
| agency_code | CharField | 32, null | 单位代码 |
| agency_name | CharField | 100, null | 单位名称 |
| acct_set_code | CharField | 32 | 账套编号 |
| acct_set_name | CharField | 60, null | 账套名称 |
| **account_cls** | **ForeignKey → GlaAccountCls** | - | 科目（account_cls_id） |
| gov_acct_cls_code | CharField | 32 | 单位会计科目代码 |
| gov_acct_cls_name | CharField | 100 | 单位会计科目名称 |
| element_code | CharField | 10, null | 启用的辅助核算项代码 |
| element_name | CharField | 20, null | 启用的辅助核算项名称 |
| accitem_code | CharField | 17, null | 辅助项存储字段名称 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| is_last_inst | DecimalField | (10,2), null | 是否终审 |

唯一约束：`(set_year, mof_div_code, acct_set_code, gov_acct_cls_code, element_code)`。

---

### 2.17 gla_acct_set_template（模板账套表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| acct_template_code | CharField | 38, PK | 模板账套编号 |
| set_year | CharField | 4, null | 会计年度 |
| acct_template_name | CharField | 100, null | 模板账套名称 |
| acct_set_type_code | CharField | 2, null | 会计主体类型代码 |
| acct_set_type_name | CharField | 100, null | 会计主体类型名称 |
| mof_div_code | CharField | 9, null | 财政区划代码 |
| mof_div_name | CharField | 360, null | 财政区划名称 |
| agency_code | CharField | 21, null | 单位代码 |
| agency_name | CharField | 300, null | 单位名称 |
| is_enabled | IntegerField | 0/1, null | 账套状态 |
| fi_leader | CharField | 60, null | 财务负责人 |
| create_user | CharField | 60, null | 创建人 |
| start_date / end_date | DateTimeField | - | 启用/停用日期 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | IntegerField | 0/1, null | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| is_last_inst | IntegerField | 0/1, null | 是否终审 |

---

### 2.18 gla_acct_set（账套设置表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| acct_set_id | CharField | 32, PK | 账套唯一标识 |
| set_year | CharField | 100, null | 会计年度 |
| acct_set_code | CharField | 32, unique | 账套编号 |
| acct_set_name | CharField | 60, null | 账套名称 |
| acct_set_type_code | CharField | 2, null | 会计主体类型代码 |
| acct_set_type_name | CharField | 69, null | 会计主体类型名称 |
| **acct_template_code** | **ForeignKey → GlaAcctSetTemplate** | - | 模板账套编号 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| agency_code | CharField | 32, null | 单位代码 |
| agency_name | CharField | 100, null | 单位名称 |
| is_enabled | BooleanField | - | 账套状态 |
| fi_leader | CharField | 250, null | 财务负责人 |
| create_user | CharField | 255, null | 创建人 |
| start_date / end_date | CharField | 255, null | 启用/停用日期 |
| update_time | CharField | 255, null | 更新时间 |
| is_deleted | BooleanField | - | 是否删除 |
| create_time | DateTimeField | - | 创建时间 |
| is_last_inst | BooleanField | - | 是否终审 |

---

### 2.19 gla_vou_head（单位会计凭证主表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| vou_id | CharField | 34, PK | 凭证主表唯一标识 |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | - | 账套编号 |
| acct_set_name | CharField | 60, null | 账套名称 |
| acct_period | IntegerField | - | 会计期间 |
| agency_code | CharField | 32, null | 单位代码 |
| agency_name | CharField | 100, null | 单位名称 |
| agency_acct_voucher_type_code | CharField | 10, null | 凭证类型代码 |
| agency_acct_voucher_type_name | CharField | 20, null | 凭证类型名称 |
| voucher_no | CharField | 40, null | 记账凭证号 |
| voucher_abs | CharField | 8, null | 凭证摘要 |
| inputer / inputer_date | CharField/DateTimeField | 60/- | 制单人/制单日期 |
| auditor / auditor_date | CharField/DateTimeField | 60/- | 审核人/审核日期 |
| poster / poster_date | CharField/DateTimeField | 60/- | 记账人/记账日期 |
| voucher_date | DateTimeField | - | 记账凭证日期 |
| fi_leader | CharField | 60, null | 财务负责人 |
| cr_amt / dr_amt | DecimalField | (18,2) | 财务贷方/借方金额 |
| cr_ys_amt / dr_ys_amt | DecimalField | (18,2) | 预算贷方/借方金额 |
| red_flag | IntegerField | - | 红冲状态 |
| red_vou_id | CharField | 32, null | 红冲凭证ID |
| is_adjust_period | CharField | 255, null | 是否调整期 |
| vou_status | IntegerField | - | 凭证状态 |
| is_carry_over | IntegerField | - | 是否结转凭证 |
| update_time | DateTimeField | - | 更新时间 |
| is_deleted | IntegerField | - | 是否删除 |
| create_time | CharField | 255, null | 创建时间 |
| is_last_inst | IntegerField | - | 是否终审 |
| checker / checker_date | CharField/DateTimeField | 255/- | 出纳人/出纳日期 |
| vou_cnt | IntegerField | - | 附件数 |
| red_vou_no | CharField | 40, null | 红冲凭证号 |
| vou_source_name | CharField | 8, null | 凭证来源 |
| print_counts | IntegerField | - | 打印次数 |

---

### 2.20 gla_vou_detail（单位会计凭证分录表）

主键与关联：

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| vou_det_id | CharField | 64, PK | 凭证分录唯一标识 |
| **vou** | **ForeignKey → GlaVouHead** | - | 凭证主表 |
| **gov_acct_cls** | **ForeignKey → GlaAccountCls** | - | 单位会计科目 |
| **pro** | **ForeignKey → EleBgtproject** | - | 项目 |
| **dep_bgt_eco** | **ForeignKey → BasDepBgtEco** | - | 部门支出经济分类 |
| **gov_bgt_eco** | **ForeignKey → BasGovBgtEco** | - | 政府支出经济分类 |
| **internal_dep** | **ForeignKey → BasInternalDep** | - | 单位内部机构 |
| **exp_func** | **ForeignKey → BasExpFunc** | - | 支出功能分类 |
| **fund_type** | **ForeignKey → EleFundtype** | - | 资金性质 |
| **pay_type** | **ForeignKey → ElePaytype** | - | 支付方式 |
| **acc_item01** | **ForeignKey → EleDivBgtEco** | - | 自定义辅助01 |
| **acc_item02** | **ForeignKey → EleSrkm** | - | 自定义辅助02 |
| **acc_item05** | **ForeignKey → EleCosttype** | - | 自定义辅助05 |
| **acc_item06** | **ForeignKey → EleWlDiv** | - | 自定义辅助06 |
| **acc_item07** | **ForeignKey → EleWlPerson** | - | 自定义辅助07 |
| **acc_item08** | **ForeignKey → EleUnion** | - | 自定义辅助08 |
| **acc_item09** | **ForeignKey → EleProcat** | - | 自定义辅助09 |

其他主要字段：set_year(100), mof_div_code(253), mof_div_name(255), acct_set_code(32), acct_set_name(60), acct_period(Integer), agency_id/agency_code/agency_name(32/32/100), voucher_no(40), vou_seq/vou_detail_seq(Decimal 18,2), vou_det_desc(250), gov_acct_cls_code(64), gov_acct_cls_name(100), dr_cr/amt/foreign_amt/ext_rat(Decimal), currency_code(3), currency_name(6), qty(Decimal 18,2)，以及 pro_code/pro_name、dep_bgt_eco_code/name、gov_bgt_eco_code/name、internal_dep_code/name、exp_func_code/name、fund_type_code/name、pay_type_code/name 等冗余字段（多为 32/60/100/200/255）。另有 acc_item01～acc_item32 的 id/code/name（部分为 FK，部分为 CharField 32/60/100/255）。系统字段：update_time, is_deleted, create_time, is_last_inst。

---

### 2.21 bas_dep_bgt_eco（部门支出经济分类表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 32, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 255, null | 账套编号 |
| ele_code | CharField | 60 | 元素代码 |
| ele_name | CharField | 100 | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 32, null | 父级ID |
| level_no | DecimalField | (10,2), null | 级次 |
| is_leaf / is_last_inst | DecimalField | (10,2), null | 是否末级/是否终审 |
| start_date / end_date | DateTimeField | - | 启用/停用日期 |
| is_enabled | DecimalField | (10,2), null | 是否启用 |
| update_time / create_time | DateTimeField | - | 更新/创建时间 |
| is_deleted | DecimalField | (10,2), null | 是否删除 |
| biz_key | CharField | 32 | 业务键 |

---

### 2.22 bas_exp_func（支出功能分类表）

字段与 **bas_dep_bgt_eco** 一致，表名 `bas_exp_func`。

---

### 2.23 bas_gov_bgt_eco（政府支出经济分类表）

字段与 **bas_dep_bgt_eco** 一致，表名 `bas_gov_bgt_eco`。

---

### 2.24 bas_internal_dep（单位内部机构表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_id | CharField | 32, PK | 主键 |
| ele_catalog_id | CharField | 32, null | 代码目录ID |
| set_year | CharField | 100, null | 会计年度 |
| mof_div_code | CharField | 253, null | 财政区划代码 |
| mof_div_name | CharField | 255, null | 财政区划名称 |
| acct_set_code | CharField | 32, null | 账套编号 |
| ele_code | CharField | 32, null | 元素代码 |
| ele_name | CharField | 200, null | 元素名称 |
| is_standard | DecimalField | (10,2), null | 是否标准 |
| parent_id | CharField | 32, null | 父级ID |
| level_no～is_deleted | 同前 | - | 级次/末级/终审/启用/日期/删除等 |
| biz_key | CharField | 32 | 业务键 |

---

### 2.25 ele_catalog（基础代码目录表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| ele_catalog_id | CharField | 38, PK | 基础代码目录主键 |
| fiscal_year | CharField | 4 | 预算年度 |
| mof_div_code | CharField | 9, null | 财政区划代码 |
| mof_div_name | CharField | 360, null | 财政区划名称 |
| acct_template_code | CharField | 38, null | 账套模板代码 |
| ele_catalog_code | CharField | 42 | 基础代码目录代码 |
| ele_catalog_name | CharField | 60 | 基础代码中文名称 |
| ele_cod_rules | CharField | 60, null | 代码集编码规则 |
| ele_source | CharField | 30 | 库表名称 |
| ele_extend_type | IntegerField | - | 扩展类型 |
| ele_manage_type | IntegerField | - | 管理方式 |
| is_last_inst | IntegerField | - | 是否终审 |
| is_standard | IntegerField | - | 是否标准 |
| is_enabled | IntegerField | - | 是否启用 |
| start_date / end_date | DateTimeField | - | 启用/停用日期 |
| update_time / create_time | DateTimeField | - | 更新/创建时间 |
| is_deleted | IntegerField | - | 是否删除 |
| accitem_code | CharField | 38, null | 辅助项存储字段名称 |
| accitem_id | CharField | 38, null | 辅助项存储字段ID |

---

### 2.26 account_book_name（账簿名称表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| id | AutoField | PK | 主键 |
| account_book_name | CharField | 38 | 账簿名称 |
| account_book_code | CharField | 38 | 账簿编码 |
| mof_div_code | CharField | 38, null | 财政区划编码 |
| set_year | CharField | 38, null | 会计年度 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | - | 账套 |
| account_book_type | CharField | 38 | 账簿类型(0总账/1明细账等) |
| account_book_group_element | JSONField | - | 分组要素 |
| account_book_element | JSONField | - | 条件要素 |
| condition_info | JSONField | - | 条件信息 |
| export_type | CharField | 38 | 导出类型 |
| balance_direction | CharField | 38 | 余额方向 |
| balance_negative_direction | CharField | 38 | 余额为负改变方向 |
| statistical_method | CharField | 38 | 统计方式 |
| account_type | CharField | 38 | 核算类型 |
| update_time / create_time | DateTimeField | - | 更新/创建时间 |

唯一约束：`(account_book_code, acct_set_code, account_book_type)`。

---

### 2.27 report_forms（报表数据表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| id | AutoField | PK | 主键 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | - | 账套 |
| report_code | CharField | 38 | 报表编码 |
| report_name | CharField | 38 | 报表名称 |
| report_type | CharField | 38 | 报表类型(旬/月/年/季/半年/年度/一次性) |
| generate_method | CharField | 38 | 生成方式(自动/手动) |
| report_category | CharField | 38 | 报表区分(财务/预算会计) |
| create_date / update_date | DateTimeField | - | 创建/更新时间 |
| is_deleted | IntegerField | - | 是否删除 |
| **create_user** | **ForeignKey → User** | - | 创建人 |
| data_source | JSONField | - | 数据源 |

---

### 2.28 ele_prit_setup（打印设置表，表名拼写为 prit）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| id | AutoField | PK | 主键 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | - | 账套编码 |
| set_year | CharField | 4, null | 年度 |
| mof_div_code | CharField | 9, null | 财政区划代码 |
| is_check | BooleanField | - | 是否选择 |
| order_rule | IntegerField | - | 排序规则 |
| display_level | IntegerField | - | 显示级别(0末级/1逐级) |
| is_print_code | BooleanField | - | 是否打印编码 |
| **ele_catalog_id** | **ForeignKey → EleCatalog** | - | 基础代码目录主键 |
| create_time / update_time | DateTimeField | - | 创建/更新时间 |

---

### 2.29 ele_print_voucher（打印凭证设置表）

| 字段名 | 类型 | 长度/精度 | 说明 |
|--------|------|-----------|------|
| id | AutoField | PK | 主键 |
| set_year | CharField | 4, null | 年度 |
| mof_div_code | CharField | 9, null | 财政区划代码 |
| **acct_set_code** | **ForeignKey → GlaAcctSet** | - | 账套（打印格式设置主键） |
| data | JSONField | - | 数据 |
| create_time / update_time | DateTimeField | - | 创建/更新时间 |

---

## 三、is_migrate = True 表清单（按表名）

| 序号 | 数据库表名 | 模型类名 | 说明 |
|------|------------|----------|------|
| 1 | gla_account_cls_template | GlaAccountClsTemplate | 模板账套会计科目 |
| 2 | gla_account_cls_ele_template | GlaAccountClsEleTemplate | 模板账套科目辅助核算项 |
| 3 | ele_bgtproject | EleBgtproject | 预算项目元素 |
| 4 | ele_costtype | EleCosttype | 费用类型元素 |
| 5 | ele_div_bgt_eco | EleDivBgtEco | 部门预算经济分类元素 |
| 6 | ele_fundtype | EleFundtype | 资金性质元素 |
| 7 | ele_paytype | ElePaytype | 支付方式元素 |
| 8 | ele_procat | EleProcat | 产品分类元素 |
| 9 | ele_srkm | EleSrkm | 收入科目元素 |
| 10 | ele_union | EleUnion | 代码集统一表 |
| 11 | ele_wl_div | EleWlDiv | 物流/划分元素 |
| 12 | ele_wl_person | EleWlPerson | 人员元素 |
| 13 | gla_account_cls_enum | GlaAccountClsEnum | 单位会计要素枚举 |
| 14 | gla_vou_vchrtype | GlaVouVchrtype | 凭证类型 |
| 15 | gla_account_cls | GLAAccountCls | 单位会计科目 |
| 16 | gla_account_cls_ele | GLAAccountClsEle | 单位会计科目辅助核算项 |
| 17 | gla_acct_set_template | GlaAcctSetTemplate | 模板账套 |
| 18 | gla_acct_set | GlaAcctSet | 账套设置 |
| 19 | gla_vou_head | GlaVouHead | 凭证主表 |
| 20 | gla_vou_detail | GlaVouDetail | 凭证分录 |
| 21 | bas_dep_bgt_eco | BasDepBgtEco | 部门支出经济分类 |
| 22 | bas_exp_func | BasExpFunc | 支出功能分类 |
| 23 | bas_gov_bgt_eco | BasGovBgtEco | 政府支出经济分类 |
| 24 | bas_internal_dep | BasInternalDep | 单位内部机构 |
| 25 | ele_catalog | EleCatalog | 基础代码目录 |
| 26 | account_book_name | AccountBookName | 账簿名称 |
| 27 | report_forms | ReportForms | 报表数据 |
| 28 | ele_prit_setup | ElePrintSetup | 打印设置 |
| 29 | ele_print_voucher | ElePrintVoucher | 打印凭证设置 |

---

## 四、使用说明

- **迁移顺序建议**：先迁移无外键或仅依赖“模板/目录”的表（如 GlaAcctSetTemplate、EleCatalog），再迁移账套（GlaAcctSet）、模板科目与科目辅助（GlaAccountClsTemplate、GlaAccountClsEleTemplate），再迁移单位科目与凭证相关表（GLAAccountCls、GLAAccountClsEle、GlaVouHead、GlaVouDetail），最后迁移依赖账套的配置表（AccountBookName、ReportForms、ElePrintSetup、ElePrintVoucher）。
- **长度说明**：CharField 为最大字符数；DecimalField 表示为 (max_digits, decimal_places)；IntegerField/BooleanField/DateTimeField 等未单独列长度，以“-”表示按数据库默认。
- 外键在表中以 **粗体** 标出，并在第一节中汇总了与其它表的关系，便于做数据迁移与一致性检查。

# 报表统计模块 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-02  
**作者**: 高级项目经理  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-模块划分设计.md (报表统计API部分)  
**实际代码参考**: backend/src/api/v1/reports.py, backend/src/api/v1/stats.py, backend/src/api/v1/dashboards.py  
**数据库模型**: models_generated.py (ReportTemplates, ReportSchedules, ReportExecutions, StatisticsCache等)

## 1. 设计概述

### 1.1 设计目标
提供完整的报表统计RESTful API接口，支持：
- 报表模板管理和拖拽式配置
- 报表查询执行和异步生成
- 多维数据统计和KPI计算
- 仪表盘创建、配置和实时数据
- 报表计划任务和导出功能

### 1.2 设计原则
1. **RESTful规范**：资源导向，HTTP方法语义明确
2. **版本控制**：API版本前缀 `/api/v1/`
3. **一致性**：统一响应格式、错误处理、分页规范
4. **安全性**：JWT认证，RBAC权限控制，行级数据权限
5. **性能**：查询缓存、异步处理、流式响应
6. **文档化**：OpenAPI规范，代码即文档

### 1.3 技术约束
- **框架**: FastAPI 0.104+ (Python 3.11+)
- **认证**: JWT (JSON Web Token)
- **序列化**: Pydantic v2 模型验证
- **数据库**: SQLAlchemy 2.0 + MySQL 8.0
- **缓存**: Redis 7.0 (多级缓存)
- **异步任务**: Celery + Redis (报表异步生成)
- **导出格式**: Excel (openpyxl), PDF (reportlab), CSV

## 2. 通用设计规范

### 2.1 请求/响应格式

#### 成功响应格式
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},  // 具体数据
  "meta": {       // 分页元数据
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### 错误响应格式
```json
{
  "code": 400,
  "message": "请求参数错误",
  "detail": {     // 错误详情
    "field": "template_code",
    "error": "模板编码已存在"
  },
  "timestamp": "2026-04-02T00:25:00Z"
}
```

### 2.2 分页规范
- **参数**: `page` (默认1), `page_size` (默认20, 最大100)
- **响应**: 包含`data`数组和`meta`分页信息
- **性能**: 大数据集使用游标分页

### 2.3 过滤和排序
- **过滤**: `filter[name]=value&filter[category]=device`
- **范围过滤**: `filter[created_at][gte]=2026-01-01&filter[created_at][lte]=2026-12-31`
- **排序**: `sort=created_at.desc,template_name.asc`
- **字段选择**: `fields=id,template_code,template_name,category`

### 2.4 认证和授权
- **认证头**: `Authorization: Bearer <jwt_token>`
- **权限**: 基于角色的访问控制 (RBAC) + 行级数据权限
- **操作审计**: 记录报表查询、导出等敏感操作

## 3. API端点详细设计

### 3.1 报表模板管理接口

#### 3.1.1 获取报表模板列表
**端点**: `GET /api/v1/reports/templates`  
**描述**: 查询报表模板列表，支持分页、过滤、排序

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| page | int | 否 | 页码，默认1 | `1` |
| page_size | int | 否 | 每页数量，默认20，最大100 | `20` |
| filter | object | 否 | 过滤条件 | `{"category": "device", "is_active": true}` |
| sort | string | 否 | 排序字段 | `created_at.desc,template_name.asc` |
| fields | string | 否 | 返回字段，逗号分隔 | `id,template_code,template_name,category` |
| search | string | 否 | 全文搜索（模板编码/名称） | `设备统计` |
| access_level | string | 否 | 访问级别过滤 | `public` |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `report:template:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "template_001",
      "template_code": "DEVICE_AVAILABILITY_DAILY",
      "template_name": "设备可用率日报",
      "category": "device",
      "sub_category": "availability",
      "description": "统计每日设备可用率",
      "data_source_type": "sql",
      "parameter_definitions": [
        {
          "name": "station_id",
          "type": "string",
          "label": "场站",
          "required": false,
          "default": null
        }
      ],
      "created_by": "user_001",
      "created_at": "2026-04-01T09:00:00Z",
      "updated_at": "2026-04-01T09:00:00Z",
      "version": 1,
      "is_active": true
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 45,
    "total_pages": 3
  }
}
```

#### 3.1.2 创建报表模板
**端点**: `POST /api/v1/reports/templates`  
**描述**: 创建新的报表模板

**请求体**:
```json
{
  "template_code": "ENERGY_PRODUCTION_MONTHLY",
  "template_name": "能源生产月报",
  "category": "energy",
  "sub_category": "production",
  "description": "统计月度能源生产数据",
  "data_source_type": "sql",
  "data_source_config": {
    "query": "SELECT DATE_FORMAT(collect_time, '%Y-%m') as month, station_id, SUM(energy_output) as total_output FROM device_metrics WHERE collect_time >= :start_date AND collect_time <= :end_date GROUP BY DATE_FORMAT(collect_time, '%Y-%m'), station_id",
    "parameters": [
      {"name": "start_date", "type": "date", "required": true},
      {"name": "end_date", "type": "date", "required": true}
    ]
  },
  "parameter_definitions": [
    {
      "name": "start_date",
      "type": "date",
      "label": "开始日期",
      "required": true,
      "default": "2026-01-01"
    },
    {
      "name": "end_date",
      "type": "date",
      "label": "结束日期",
      "required": true,
      "default": "2026-12-31"
    }
  ],
  "column_definitions": [
    {
      "field": "month",
      "display_name": "月份",
      "data_type": "string",
      "format": null
    },
    {
      "field": "station_id",
      "display_name": "场站",
      "data_type": "string",
      "format": null
    },
    {
      "field": "total_output",
      "display_name": "总产出(kWh)",
      "data_type": "number",
      "format": "#,##0.00"
    }
  ],
  "visualization_config": {
    "chart_type": "bar",
    "x_axis": "month",
    "y_axis": "total_output",
    "group_by": "station_id"
  },
  "access_level": "shared"
}
```

**权限要求**:
- 角色: `admin` (管理员) 或 `report_designer` (报表设计师)
- 权限: `report:template:create`

**成功响应** (201):
```json
{
  "code": 201,
  "message": "报表模板创建成功",
  "data": {
    "id": "template_002",
    "template_code": "ENERGY_PRODUCTION_MONTHLY",
    "template_name": "能源生产月报",
    "created_at": "2026-04-02T00:30:00Z"
  }
}
```

#### 3.1.3 获取报表模板详情
**端点**: `GET /api/v1/reports/templates/{template_id}`  
**描述**: 获取指定ID的报表模板详情

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| template_id | string | 是 | 报表模板ID |

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| include_config | boolean | 否 | 是否包含完整配置，默认false |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `report:template:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "template_001",
    "template_code": "DEVICE_AVAILABILITY_DAILY",
    "template_name": "设备可用率日报",
    "category": "device",
    "sub_category": "availability",
    "description": "统计每日设备可用率",
    "data_source_type": "sql",
    "data_source_config": {...},
    "parameter_definitions": [...],
    "column_definitions": [...],
    "visualization_config": {...},
    "layout_config": {...},
    "export_config": {...},
    "access_level": "public",
    "created_by": "user_001",
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-04-01T09:00:00Z",
    "version": 1,
    "is_active": true
  }
}
```

#### 3.1.4 更新报表模板
**端点**: `PUT /api/v1/reports/templates/{template_id}`  
**描述**: 更新指定ID的报表模板

**权限要求**:
- 角色: `admin` (管理员) 或 `report_designer` (报表设计师)
- 权限: `report:template:update`

#### 3.1.5 删除报表模板
**端点**: `DELETE /api/v1/reports/templates/{template_id}`  
**描述**: 删除指定ID的报表模板（软删除）

**权限要求**:
- 角色: `admin` (管理员)
- 权限: `report:template:delete`

### 3.2 报表查询执行接口

#### 3.2.1 执行报表查询
**端点**: `POST /api/v1/reports/query`  
**描述**: 执行报表查询，返回结果数据

**请求体**:
```json
{
  "template_id": "template_001",
  "parameters": {
    "station_id": "station_001",
    "start_date": "2026-04-01",
    "end_date": "2026-04-30"
  },
  "options": {
    "format": "json",
    "page": 1,
    "page_size": 100,
    "enable_cache": true,
    "cache_ttl": 300
  }
}
```

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `report:execute`
- **行级权限**: 只能查询有权限的场站数据

**成功响应** (200):
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "columns": [
      {"field": "date", "display_name": "日期", "data_type": "date"},
      {"field": "station_name", "display_name": "场站", "data_type": "string"},
      {"field": "availability_rate", "display_name": "可用率(%)", "data_type": "number"}
    ],
    "rows": [
      {"date": "2026-04-01", "station_name": "阳光光伏电站", "availability_rate": 98.5},
      {"date": "2026-04-02", "station_name": "阳光光伏电站", "availability_rate": 99.2}
    ],
    "summary": {
      "total_rows": 30,
      "execution_time_ms": 125,
      "cache_hit": true,
      "data_source": "device_metrics_agg"
    }
  },
  "meta": {
    "page": 1,
    "page_size": 100,
    "total": 30,
    "total_pages": 1
  }
}
```

#### 3.2.2 异步生成报表
**端点**: `POST /api/v1/reports/async`  
**描述**: 异步生成报表，返回任务ID，支持大数据量

**请求体**:
```json
{
  "template_id": "template_001",
  "parameters": {
    "station_id": "station_001",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31"
  },
  "options": {
    "format": "excel",
    "filename": "设备可用率年报_2026.xlsx",
    "notification": true
  }
}
```

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `report:execute:async`

**成功响应** (202 Accepted):
```json
{
  "code": 202,
  "message": "报表生成任务已提交",
  "data": {
    "task_id": "task_1234567890",
    "status": "pending",
    "estimated_completion_time": "2026-04-02T00:35:00Z",
    "progress_url": "/api/v1/tasks/task_1234567890"
  }
}
```

#### 3.2.3 导出报表
**端点**: `POST /api/v1/reports/{template_id}/export`  
**描述**: 导出报表为指定格式（Excel/PDF/CSV）

**请求体**:
```json
{
  "parameters": {
    "station_id": "station_001",
    "start_date": "2026-04-01",
    "end_date": "2026-04-30"
  },
  "format": "excel",
  "options": {
    "include_charts": true,
    "landscape": false,
    "watermark": "CONFIDENTIAL"
  }
}
```

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `report:export`
- **审批流程**: 敏感数据导出需要审批

**成功响应** (200):
```json
{
  "code": 200,
  "message": "导出成功",
  "data": {
    "download_url": "/api/v1/reports/download/export_1234567890.xlsx",
    "filename": "设备可用率月报_2026-04.xlsx",
    "file_size": 2048576,
    "expires_at": "2026-04-02T12:00:00Z"
  }
}
```

### 3.3 统计API接口

#### 3.3.1 设备运行统计
**端点**: `GET /api/v1/stats/device`  
**描述**: 获取设备运行统计（可用率、效率、OEE等）

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| station_id | string | 否 | 场站ID，不传则查询所有有权限的场站 |
| device_type_id | string | 否 | 设备类型ID |
| period | string | 是 | 统计周期：today/yesterday/week/month/quarter/year/custom |
| start_date | date | 否 | 自定义开始日期（period=custom时必填） |
| end_date | date | 否 | 自定义结束日期（period=custom时必填） |
| metrics | array | 否 | 统计指标：availability,performance,quality,oee,runtime,downtime |

**权限要求**:
- 角色: `viewer` (查看者) 及以上
- 权限: `stats:device:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "summary": {
      "total_devices": 150,
      "online_devices": 142,
      "offline_devices": 5,
      "fault_devices": 3,
      "avg_availability": 96.8,
      "avg_oee": 92.5
    },
    "by_station": [
      {
        "station_id": "station_001",
        "station_name": "阳光光伏电站",
        "device_count": 50,
        "availability": 98.2,
        "performance": 94.5,
        "quality": 98.0,
        "oee": 91.2
      }
    ],
    "by_device_type": [
      {
        "device_type_id": "type_pv_inverter",
        "device_type_name": "光伏逆变器",
        "device_count": 30,
        "availability": 97.8,
        "oee": 90.5
      }
    ],
    "trend": {
      "daily": [...],
      "weekly": [...],
      "monthly": [...]
    }
  }
}
```

#### 3.3.2 能源生产统计
**端点**: `GET /api/v1/stats/energy`  
**描述**: 获取能源生产统计（发电量、收益、效率等）

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| station_id | string | 否 | 场站ID |
| period | string | 是 | 统计周期 |
| group_by | string | 否 | 分组维度：station/device_type/hour/day/month |
| include_revenue | boolean | 否 | 是否包含收益数据，默认false（需要权限） |

**权限要求**:
- 角色: `viewer` (查看者) 及以上
- 权限: `stats:energy:read`
- **敏感数据**: 收益数据需要`stats:revenue:read`权限

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "total_energy": 1250000.5,
    "total_revenue": 625000.25,
    "avg_efficiency": 85.2,
    "peak_power": 9500.0,
    "by_time_period": [
      {
        "period": "2026-04",
        "energy": 125000.5,
        "revenue": 62500.25,
        "avg_power": 8500.0
      }
    ],
    "by_station": [...],
    "comparison": {
      "vs_previous_period": 5.2,
      "vs_target": -2.8
    }
  }
}
```

#### 3.3.3 维护成本统计
**端点**: `GET /api/v1/stats/maintenance`  
**描述**: 获取维护成本统计（MTTR、MTBF、维修成本等）

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| station_id | string | 否 | 场站ID |
| period | string | 是 | 统计周期 |
| cost_type | string | 否 | 成本类型：labor/parts/external/other |

**权限要求**:
- 角色: `viewer` (查看者) 及以上
- 权限: `stats:maintenance:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "total_workorders": 45,
    "completed_workorders": 42,
    "pending_workorders": 3,
    "avg_mttr_hours": 3.5,
    "avg_mtbf_days": 45.2,
    "total_cost": 125000.0,
    "cost_breakdown": {
      "labor": 65000.0,
      "parts": 45000.0,
      "external": 10000.0,
      "other": 5000.0
    },
    "by_device_type": [...],
    "trend": {
      "monthly_cost": [...],
      "monthly_workorders": [...]
    }
  }
}
```

#### 3.3.4 KPI指标统计
**端点**: `GET /api/v1/stats/kpi`  
**描述**: 获取KPI指标统计（OEE、设备利用率、能效比等）

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| kpi_type | string | 是 | KPI类型：oee/utilization/efficiency/availability |
| period | string | 是 | 统计周期 |
| benchmark | boolean | 否 | 是否包含行业基准，默认false |

**权限要求**:
- 角色: `viewer` (查看者) 及以上
- 权限: `stats:kpi:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "kpi_type": "oee",
    "current_value": 92.5,
    "target_value": 95.0,
    "variance": -2.5,
    "achievement_rate": 97.4,
    "trend": [
      {"period": "2026-01", "value": 90.2},
      {"period": "2026-02", "value": 91.5},
      {"period": "2026-03", "value": 92.8},
      {"period": "2026-04", "value": 92.5}
    ],
    "benchmark": {
      "industry_average": 88.5,
      "top_quartile": 94.2,
      "position": "above_average"
    },
    "breakdown": {
      "availability": 96.8,
      "performance": 95.2,
      "quality": 98.0
    }
  }
}
```

### 3.4 仪表盘API接口

#### 3.4.1 获取仪表盘列表
**端点**: `GET /api/v1/dashboards`  
**描述**: 获取用户有权限访问的仪表盘列表

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| dashboard_type | string | 否 | 仪表盘类型：personal/shared/public |
| include_default | boolean | 否 | 是否包含默认仪表盘，默认true |

**权限要求**:
- 角色: `viewer` (查看者) 及以上
- 权限: `dashboard:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "dashboard_001",
      "dashboard_name": "运营总览",
      "dashboard_type": "shared",
      "description": "关键运营指标总览",
      "created_by": "user_001",
      "created_at": "2026-04-01T10:00:00Z",
      "updated_at": "2026-04-01T10:00:00Z",
      "last_viewed_at": "2026-04-02T00:25:00Z",
      "view_count": 45,
      "is_default": true,
      "widget_count": 8
    }
  ]
}
```

#### 3.4.2 创建仪表盘
**端点**: `POST /api/v1/dashboards`  
**描述**: 创建新的仪表盘

**请求体**:
```json
{
  "dashboard_name": "设备监控仪表盘",
  "dashboard_type": "personal",
  "description": "个人设备监控仪表盘",
  "layout_config": {
    "grid_size": 12,
    "row_height": 100,
    "margin": [10, 10]
  },
  "widgets": [
    {
      "widget_id": "widget_1",
      "widget_type": "chart",
      "title": "设备可用率趋势",
      "data_source": {
        "type": "report",
        "template_id": "template_001",
        "parameters": {
          "station_id": "station_001"
        }
      },
      "position": {
        "x": 0,
        "y": 0,
        "w": 6,
        "h": 4
      },
      "config": {
        "chart_type": "line",
        "refresh_interval": 60
      }
    }
  ],
  "refresh_interval": 60,
  "theme": "light"
}
```

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `dashboard:create`

#### 3.4.3 获取仪表盘详情和数据
**端点**: `GET /api/v1/dashboards/{dashboard_id}/data`  
**描述**: 获取仪表盘配置和实时数据

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| include_data | boolean | 否 | 是否包含数据，默认true |
| refresh | boolean | 否 | 强制刷新数据，默认false |

**权限要求**:
- 角色: `viewer` (查看者) 及以上
- 权限: `dashboard:read`
- **行级权限**: 只能查看有权限的数据

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "dashboard": {
      "id": "dashboard_001",
      "dashboard_name": "运营总览",
      "dashboard_type": "shared",
      "layout_config": {...},
      "widgets": [...],
      "theme": "light",
      "refresh_interval": 60,
      "created_at": "2026-04-01T10:00:00Z",
      "updated_at": "2026-04-01T10:00:00Z"
    },
    "widgets_data": {
      "widget_1": {
        "status": "success",
        "data": {...},
        "last_updated": "2026-04-02T00:30:00Z"
      },
      "widget_2": {
        "status": "success",
        "data": {...},
        "last_updated": "2026-04-02T00:30:00Z"
      }
    },
    "last_updated": "2026-04-02T00:30:00Z"
  }
}
```

#### 3.4.4 更新仪表盘布局
**端点**: `PUT /api/v1/dashboards/{dashboard_id}`  
**描述**: 更新仪表盘布局和配置

**权限要求**:
- 角色: `operator` (操作员) 及以上（个人仪表盘）
- 角色: `admin` (管理员) 或创建者（共享/公共仪表盘）
- 权限: `dashboard:update`

### 3.5 异步任务API接口

#### 3.5.1 查询任务状态
**端点**: `GET /api/v1/tasks/{task_id}`  
**描述**: 查询异步任务状态和进度

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `task:read`
- **限制**: 只能查询自己创建的任务（管理员除外）

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "task_id": "task_1234567890",
    "task_type": "report_generation",
    "status": "running",
    "progress": 65,
    "estimated_completion_time": "2026-04-02T00:35:00Z",
    "started_at": "2026-04-02T00:30:00Z",
    "updated_at": "2026-04-02T00:32:00Z",
    "result": {
      "download_url": null,
      "error_message": null
    },
    "metadata": {
      "template_id": "template_001",
      "parameters": {...},
      "created_by": "user_001"
    }
  }
}
```

#### 3.5.2 取消任务
**端点**: `POST /api/v1/tasks/{task_id}/cancel`  
**描述**: 取消正在执行的异步任务

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `task:cancel`
- **限制**: 只能取消自己创建的任务（管理员除外）

## 4. 性能优化设计

### 4.1 缓存策略API
- **查询缓存**: 自动缓存查询结果，支持TTL配置
- **预取缓存**: 热门报表数据预取到缓存
- **缓存清除**: 支持按模板、数据源清除缓存

### 4.2 流式响应
- **大数据集**: 使用Server-Sent Events (SSE) 或分块传输
- **进度反馈**: 长时间任务提供进度回调

### 4.3 并发控制
- **限流**: 基于用户/IP的请求限流
- **队列**: 异步任务队列管理，防止资源耗尽
- **优先级**: 任务优先级设置（高/中/低）

## 5. 安全设计

### 5.1 权限验证
- **接口级别**: JWT认证 + RBAC权限
- **数据级别**: 行级权限过滤（基于场站/部门）
- **操作级别**: 敏感操作审计日志

### 5.2 数据脱敏
- **敏感字段**: 成本、收益等敏感数据脱敏显示
- **导出控制**: 敏感数据导出需要审批流程
- **访问日志**: 记录数据访问日志

### 5.3 防注入保护
- **参数化查询**: 所有动态SQL使用参数化查询
- **输入验证**: 严格的输入验证和清理
- **查询限制**: 限制查询复杂度、返回行数、执行时间

## 6. 错误处理

### 6.1 错误码定义
| 错误码 | 描述 | HTTP状态 |
|--------|------|----------|
| 40001 | 参数验证错误 | 400 |
| 40002 | 查询语法错误 | 400 |
| 40101 | 未认证 | 401 |
| 40301 | 权限不足 | 403 |
| 40302 | 数据权限不足 | 403 |
| 40401 | 报表模板不存在 | 404 |
| 42901 | 请求频率超限 | 429 |
| 50001 | 报表生成失败 | 500 |
| 50002 | 数据源连接失败 | 500 |
| 50301 | 系统繁忙，请稍后重试 | 503 |

### 6.2 错误恢复
- **重试机制**: 可重试错误自动重试
- **降级策略**: 主数据源失败时使用备用数据源
- **优雅降级**: 复杂图表降级为简单表格

---

**设计完成时间**: 2026-04-02 00:35  
**下一步**: 业务逻辑详细设计
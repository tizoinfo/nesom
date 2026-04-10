# 设备监控模块 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-01  
**作者**: 工作流架构师  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-模块划分设计.md (设备监控API部分)  
**实际代码参考**: backend/src/api/v1/devices.py  
**数据库模型**: models_generated.py (Devices, DeviceTypes, DeviceMetrics, DeviceAlerts等)

## 1. 设计概述

### 1.1 设计目标
提供完整的设备监控RESTful API接口，支持：
- 设备全生命周期管理（增删改查）
- 设备实时数据采集和查询
- 设备状态监控和告警管理
- 设备维护计划和记录管理
- 设备数据统计和分析

### 1.2 设计原则
1. **RESTful规范**：资源导向，HTTP方法语义明确
2. **版本控制**：API版本前缀 `/api/v1/`
3. **一致性**：统一响应格式、错误处理、分页规范
4. **安全性**：JWT认证，RBAC权限控制
5. **性能**：支持过滤、分页、字段选择、数据压缩
6. **文档化**：OpenAPI规范，代码即文档

### 1.3 技术约束
- **框架**: FastAPI 0.104+ (Python 3.11+)
- **认证**: JWT (JSON Web Token)
- **序列化**: Pydantic v2 模型验证
- **数据库**: SQLAlchemy 2.0 + MySQL 8.0
- **缓存**: Redis 7.0 (热点数据缓存)

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
    "field": "device_code",
    "error": "设备编码已存在"
  },
  "timestamp": "2026-04-01T10:30:00Z"
}
```

### 2.2 分页规范
- **参数**: `page` (默认1), `page_size` (默认20, 最大100)
- **响应**: 包含`data`数组和`meta`分页信息
- **性能**: 使用游标分页优化大数据集

### 2.3 过滤和排序
- **过滤**: `filter[name]=value&filter[status]=online`
- **范围过滤**: `filter[created_at][gte]=2026-01-01&filter[created_at][lte]=2026-12-31`
- **排序**: `sort=created_at.desc,device_name.asc`
- **字段选择**: `fields=id,device_code,device_name,status`

### 2.4 认证和授权
- **认证头**: `Authorization: Bearer <jwt_token>`
- **权限**: 基于角色的访问控制 (RBAC)
- **操作审计**: 记录操作日志

## 3. API端点详细设计

### 3.1 设备管理接口

#### 3.1.1 获取设备列表
**端点**: `GET /api/v1/devices`  
**描述**: 查询设备列表，支持分页、过滤、排序、字段选择

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| page | int | 否 | 页码，默认1 | `1` |
| page_size | int | 否 | 每页数量，默认20，最大100 | `20` |
| filter | object | 否 | 过滤条件 | `{"status": "online", "station_id": "123"}` |
| sort | string | 否 | 排序字段 | `created_at.desc,device_name.asc` |
| fields | string | 否 | 返回字段，逗号分隔 | `id,device_code,device_name,status` |
| expand | string | 否 | 关联数据展开 | `device_type,station` |
| search | string | 否 | 全文搜索（设备编码/名称） | `PV-001` |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `device:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "dev_001",
      "device_code": "PV-001",
      "device_name": "光伏逆变器1号",
      "device_type_id": "type_pv_inverter",
      "device_type": {
        "id": "type_pv_inverter",
        "type_name": "光伏逆变器"
      },
      "station_id": "station_001",
      "station": {
        "id": "station_001",
        "name": "阳光光伏电站"
      },
      "status": "online",
      "manufacturer": "华为",
      "model": "SUN2000-10KTL",
      "rated_power": 10.00,
      "health_score": 95,
      "last_heartbeat": "2026-04-01T10:25:30Z",
      "created_at": "2026-01-15T09:00:00Z",
      "updated_at": "2026-04-01T10:25:30Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

**错误响应**:
- `401 Unauthorized`: 未认证或Token过期
- `403 Forbidden`: 权限不足
- `500 Internal Server Error`: 服务器内部错误

**实现要点**:
1. 支持复杂的过滤条件组合
2. 关联数据懒加载或预加载控制
3. 全文搜索使用数据库全文索引或Elasticsearch
4. 敏感字段过滤（如设备密码）

#### 3.1.2 获取单个设备
**端点**: `GET /api/v1/devices/{device_id}`  
**描述**: 获取设备详细信息

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| expand | string | 否 | 关联数据展开 | `device_type,station,thresholds` |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `device:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "dev_001",
    "device_code": "PV-001",
    "device_name": "光伏逆变器1号",
    "device_type_id": "type_pv_inverter",
    "device_type": {
      "id": "type_pv_inverter",
      "type_code": "pv_inverter",
      "type_name": "光伏逆变器",
      "parameter_template": {...}
    },
    "station_id": "station_001",
    "station": {
      "id": "station_001",
      "name": "阳光光伏电站",
      "code": "SUN-PV"
    },
    "status": "online",
    "manufacturer": "华为",
    "model": "SUN2000-10KTL",
    "serial_number": "SN20260115001",
    "rated_power": 10.00,
    "rated_voltage": 380.00,
    "rated_current": 15.20,
    "parameters": {
      "mppt_count": 2,
      "max_dc_voltage": 1100,
      "start_voltage": 200
    },
    "installation_date": "2026-01-20",
    "commissioning_date": "2026-01-25",
    "warranty_period": 60,
    "warranty_expiry": "2031-01-24",
    "health_score": 95,
    "last_maintenance_date": "2026-03-15",
    "next_maintenance_date": "2026-06-15",
    "location_description": "1号厂房西侧",
    "longitude": 116.407526,
    "latitude": 39.904030,
    "altitude": 50.5,
    "description": "10kW光伏逆变器，用于屋顶光伏系统",
    "images": [
      {"url": "/storage/devices/dev_001/photo1.jpg", "title": "正面图"}
    ],
    "documents": [
      {"url": "/storage/devices/dev_001/manual.pdf", "title": "使用手册"}
    ],
    "qr_code": "https://nesom.example.com/devices/dev_001",
    "responsible_person_id": "user_001",
    "responsible_person_name": "张三",
    "last_heartbeat": "2026-04-01T10:25:30Z",
    "data_collection_status": "enabled",
    "data_collection_config": {
      "protocol": "modbus_tcp",
      "frequency": 60,
      "address": "192.168.1.100:502",
      "registers": [...]
    },
    "created_at": "2026-01-15T09:00:00Z",
    "updated_at": "2026-04-01T10:25:30Z"
  }
}
```

**错误响应**:
- `404 Not Found`: 设备不存在
- 其他错误同3.1.1

#### 3.1.3 创建设备
**端点**: `POST /api/v1/devices`  
**描述**: 创建新设备

**请求头**:
- `Content-Type: application/json`

**请求体** (JSON Schema):
```json
{
  "type": "object",
  "required": ["device_code", "device_name", "device_type_id", "station_id"],
  "properties": {
    "device_code": {
      "type": "string",
      "minLength": 1,
      "maxLength": 50,
      "pattern": "^[A-Za-z0-9_-]+$",
      "description": "设备编码，场站内唯一"
    },
    "device_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "description": "设备名称"
    },
    "device_type_id": {
      "type": "string",
      "format": "uuid",
      "description": "设备类型ID"
    },
    "station_id": {
      "type": "string",
      "format": "uuid",
      "description": "所属场站ID"
    },
    "status": {
      "type": "string",
      "enum": ["offline", "online", "fault", "maintenance", "testing", "standby"],
      "default": "offline",
      "description": "设备状态"
    },
    "manufacturer": {
      "type": "string",
      "maxLength": 100,
      "description": "制造商"
    },
    "model": {
      "type": "string",
      "maxLength": 100,
      "description": "型号"
    },
    "serial_number": {
      "type": "string",
      "maxLength": 100,
      "description": "序列号"
    },
    "rated_power": {
      "type": "number",
      "minimum": 0,
      "description": "额定功率(kW)"
    },
    "installation_date": {
      "type": "string",
      "format": "date",
      "description": "安装日期"
    },
    "description": {
      "type": "string",
      "description": "设备描述"
    },
    "parameters": {
      "type": "object",
      "description": "设备参数，JSON格式"
    },
    "data_collection_config": {
      "type": "object",
      "description": "数据采集配置"
    }
  }
}
```

**权限要求**:
- 角色: `admin` (管理员) 或 `engineer` (工程师)
- 权限: `device:create`

**成功响应** (201):
```json
{
  "code": 201,
  "message": "设备创建成功",
  "data": {
    "id": "dev_new_001",
    "device_code": "PV-001",
    "device_name": "光伏逆变器1号",
    "status": "offline",
    "created_at": "2026-04-01T10:30:00Z"
  },
  "links": {
    "self": "/api/v1/devices/dev_new_001",
    "metrics": "/api/v1/devices/dev_new_001/metrics",
    "alerts": "/api/v1/devices/dev_new_001/alerts"
  }
}
```

**错误响应**:
- `400 Bad Request`: 请求参数错误，如设备编码重复
- `422 Unprocessable Entity`: 数据验证失败
- `409 Conflict`: 资源冲突（如设备编码已存在）

**业务规则**:
1. 设备编码在场站内必须唯一
2. 设备类型必须存在且有效
3. 场站必须存在且有效
4. 创建设备后自动生成二维码
5. 记录操作审计日志

#### 3.1.4 更新设备
**端点**: `PUT /api/v1/devices/{device_id}`  
**描述**: 更新设备信息

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**请求体**: 同创建设备，但所有字段可选

**权限要求**:
- 角色: `admin` (管理员) 或 `engineer` (工程师)
- 权限: `device:update`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "设备更新成功",
  "data": {
    "id": "dev_001",
    "device_name": "光伏逆变器1号(更新)",
    "status": "online",
    "updated_at": "2026-04-01T10:35:00Z"
  }
}
```

**错误响应**:
- `404 Not Found`: 设备不存在
- `400 Bad Request`: 请求参数错误
- `403 Forbidden`: 无权修改设备（如设备在线状态不可修改某些字段）

**业务规则**:
1. 在线设备不能修改数据采集配置
2. 关键字段修改需记录审计日志
3. 状态变更触发相应事件（如online→maintenance触发维护事件）

#### 3.1.5 删除设备
**端点**: `DELETE /api/v1/devices/{device_id}`  
**描述**: 删除设备（软删除）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| force | boolean | 否 | 是否强制删除，默认false | `true` |

**权限要求**:
- 角色: `admin` (管理员)
- 权限: `device:delete`

**成功响应** (204):
```json
{
  "code": 204,
  "message": "设备删除成功"
}
```

**错误响应**:
- `404 Not Found`: 设备不存在
- `400 Bad Request`: 设备存在关联数据（告警、指标等）且force=false
- `409 Conflict`: 设备在线，无法删除

**业务规则**:
1. 默认软删除，标记deleted_at字段
2. 存在关联数据时需先清理或使用force=true
3. 在线设备不能删除
4. 记录删除审计日志

### 3.2 设备数据接口

#### 3.2.1 获取设备实时数据
**端点**: `GET /api/v1/devices/{device_id}/metrics/realtime`  
**描述**: 获取设备最新指标数据

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| metric_types | string | 否 | 指标类型，逗号分隔 | `voltage,current,power` |
| limit | int | 否 | 每种指标返回最新数据点数，默认1 | `5` |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `device:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "device_id": "dev_001",
    "device_name": "光伏逆变器1号",
    "collected_at": "2026-04-01T10:29:30Z",
    "metrics": [
      {
        "metric_type": "voltage",
        "metric_value": 382.5,
        "metric_unit": "V",
        "collected_at": "2026-04-01T10:29:30Z",
        "quality": 98
      },
      {
        "metric_type": "current",
        "metric_value": 15.1,
        "metric_unit": "A",
        "collected_at": "2026-04-01T10:29:30Z",
        "quality": 95
      },
      {
        "metric_type": "active_power",
        "metric_value": 5.78,
        "metric_unit": "kW",
        "collected_at": "2026-04-01T10:29:30Z",
        "quality": 96
      }
    ]
  }
}
```

#### 3.2.2 查询设备历史数据
**端点**: `GET /api/v1/devices/{device_id}/metrics/historical`  
**描述**: 查询设备历史指标数据，支持聚合

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| metric_type | string | 是 | 指标类型 | `active_power` |
| start_time | string | 是 | 开始时间(ISO8601) | `2026-04-01T00:00:00Z` |
| end_time | string | 是 | 结束时间(ISO8601) | `2026-04-01T23:59:59Z` |
| aggregation | string | 否 | 聚合方式: avg, max, min, sum, count, none | `avg` |
| interval | string | 否 | 聚合间隔: 1m, 5m, 15m, 1h, 1d | `15m` |
| fill | string | 否 | 空值填充: null, previous, linear, zero | `previous` |
| limit | int | 否 | 返回数据点数量，默认1000 | `1000` |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `device:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "device_id": "dev_001",
    "metric_type": "active_power",
    "metric_unit": "kW",
    "aggregation": "avg",
    "interval": "15m",
    "data": [
      {
        "time": "2026-04-01T00:00:00Z",
        "value": 0.5,
        "quality": 95
      },
      {
        "time": "2026-04-01T00:15:00Z",
        "value": 2.3,
        "quality": 96
      },
      // ... 更多数据点
    ],
    "summary": {
      "avg": 5.78,
      "max": 9.85,
      "min": 0.12,
      "count": 96
    }
  }
}
```

**性能优化**:
1. 大数据量查询使用时间分区索引
2. 常用查询结果缓存5分钟
3. 支持数据采样避免返回过多点

### 3.3 设备告警接口

#### 3.3.1 获取设备告警列表
**端点**: `GET /api/v1/devices/{device_id}/alerts`  
**描述**: 获取设备的告警记录

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| status | string | 否 | 告警状态 | `active,acknowledged` |
| alert_level | string | 否 | 告警级别 | `error,critical` |
| start_time | string | 否 | 开始时间 | `2026-04-01T00:00:00Z` |
| end_time | string | 否 | 结束时间 | `2026-04-01T23:59:59Z` |
| page, page_size | int | 否 | 分页参数 | 同3.1.1 |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `device:read`, `alert:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "alert_001",
      "alert_code": "ALERT-PV-001-202604011025-001",
      "alert_type": "threshold",
      "alert_level": "error",
      "alert_title": "电压超上限",
      "alert_message": "设备PV-001电压值382.5V超过上限380V",
      "trigger_value": 382.5,
      "threshold_value": 380.0,
      "start_time": "2026-04-01T10:25:30Z",
      "status": "active",
      "acknowledged_at": null,
      "resolved_at": null,
      "created_at": "2026-04-01T10:25:30Z"
    }
  ],
  "meta": {...}
}
```

#### 3.3.2 确认告警
**端点**: `POST /api/v1/devices/{device_id}/alerts/{alert_id}/acknowledge`  
**描述**: 确认告警，表示已关注

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |
| alert_id | string | 是 | 告警ID |

**请求体** (可选):
```json
{
  "notes": "已通知现场人员检查"
}
```

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `alert:update`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "告警确认成功",
  "data": {
    "alert_id": "alert_001",
    "status": "acknowledged",
    "acknowledged_at": "2026-04-01T10:35:00Z",
    "acknowledged_by": "user_001",
    "acknowledged_by_name": "张三"
  }
}
```

**业务规则**:
1. 只有active状态的告警可以确认
2. 确认后状态变为acknowledged
3. 记录确认人和时间

#### 3.3.3 解决告警
**端点**: `POST /api/v1/devices/{device_id}/alerts/{alert_id}/resolve`  
**描述**: 标记告警为已解决

**路径参数**: 同确认告警

**请求体**:
```json
{
  "resolution_notes": "现场检查发现传感器故障，已更换",
  "create_work_order": true  // 可选：是否创建关联工单
}
```

**权限要求**:
- 角色: `engineer` (工程师) 及以上
- 权限: `alert:update`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "告警解决成功",
  "data": {
    "alert_id": "alert_001",
    "status": "resolved",
    "resolved_at": "2026-04-01T11:00:00Z",
    "resolved_by": "user_002",
    "resolved_by_name": "李四",
    "resolution_notes": "现场检查发现传感器故障，已更换",
    "related_work_order_id": "wo_001"  // 如创建了工单
  }
}
```

**业务规则**:
1. 只有active或acknowledged状态的告警可以解决
2. 解决后状态变为resolved
3. 必须填写解决说明
4. 可选择自动创建关联工单

### 3.4 设备状态和控制接口

#### 3.4.1 获取设备状态
**端点**: `GET /api/v1/devices/{device_id}/status`  
**描述**: 获取设备详细状态信息

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**权限要求**:
- 角色: `operator` (操作员) 及以上
- 权限: `device:read`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "device_id": "dev_001",
    "status": "online",
    "health_score": 95,
    "last_heartbeat": "2026-04-01T10:29:30Z",
    "uptime": {
      "current": "15天2小时",
      "total": "75天8小时"
    },
    "data_collection": {
      "status": "enabled",
      "last_collected": "2026-04-01T10:29:30Z",
      "success_rate": 99.8
    },
    "alerts_summary": {
      "active": 2,
      "critical": 0,
      "error": 1,
      "warning": 1
    },
    "maintenance": {
      "last_maintenance": "2026-03-15",
      "next_maintenance": "2026-06-15",
      "overdue": false
    },
    "performance": {
      "today_energy": 45.8,
      "month_energy": 1250.3,
      "efficiency": 98.2
    }
  }
}
```

#### 3.4.2 控制设备（启停/模式切换）
**端点**: `POST /api/v1/devices/{device_id}/control`  
**描述**: 发送控制指令到设备

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| device_id | string | 是 | 设备ID |

**请求体**:
```json
{
  "command": "start",  // start, stop, reset, mode_switch
  "parameters": {
    "mode": "grid_tied"  // 命令参数
  },
  "reason": "计划性启机",
  "scheduled_time": "2026-04-01T11:00:00Z"  // 可选：计划执行时间
}
```

**权限要求**:
- 角色: `engineer` (工程师) 及以上
- 权限: `device:control`

**成功响应** (202 Accepted):
```json
{
  "code": 202,
  "message": "控制指令已接受",
  "data": {
    "command_id": "cmd_001",
    "command": "start",
    "status": "pending",
    "device_id": "dev_001",
    "submitted_at": "2026-04-01T10:40:00Z",
    "estimated_completion": "2026-04-01T10:40:30Z"
  }
}
```

**业务规则**:
1. 异步执行，返回command_id用于查询状态
2. 记录详细的操作审计日志
3. 支持立即执行和计划执行
4. 设备必须在线且支持远程控制

### 3.5 批量操作接口

#### 3.5.1 批量更新设备状态
**端点**: `POST /api/v1/devices/batch/status`  
**描述**: 批量更新多个设备状态

**请求体**:
```json
{
  "device_ids": ["dev_001", "dev_002", "dev_003"],
  "status": "maintenance",
  "reason": "计划性维护",
  "maintenance_duration_hours": 4
}
```

**权限要求**:
- 角色: `engineer` (工程师) 及以上
- 权限: `device:update`

**成功响应** (200):
```json
{
  "code": 200,
  "message": "批量操作完成",
  "data": {
    "total": 3,
    "success": 3,
    "failed": 0,
    "results": [
      {
        "device_id": "dev_001",
        "status": "success",
        "message": "状态已更新"
      }
    ]
  }
}
```

#### 3.5.2 批量导入设备
**端点**: `POST /api/v1/devices/batch/import`  
**描述**: 批量导入设备数据（Excel/CSV）

**请求头**:
- `Content-Type: multipart/form-data`

**表单参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| file | file | 是 | Excel或CSV文件 |
| template | string | 否 | 模板类型: standard/custom |
| update_existing | boolean | 否 | 是否更新已存在设备，默认false |

**权限要求**:
- 角色: `admin` (管理员)
- 权限: `device:create`, `device:update`

**成功响应** (202):
```json
{
  "code": 202,
  "message": "导入任务已提交",
  "data": {
    "task_id": "import_001",
    "status": "processing",
    "estimated_completion": "2026-04-01T10:45:00Z"
  }
}
```

## 4. WebSocket实时接口

### 4.1 设备实时数据推送
**端点**: `WS /api/v1/ws/devices/{device_id}/metrics`  
**描述**: WebSocket连接，实时推送设备指标数据

**连接参数**:
- 认证: 通过URL参数`token`传递JWT

**订阅消息** (客户端→服务器):
```json
{
  "action": "subscribe",
  "metric_types": ["voltage", "current", "active_power"],
  "interval": 1000  // 推送间隔(ms)
}
```

**数据消息** (服务器→客户端):
```json
{
  "type": "metrics",
  "device_id": "dev_001",
  "timestamp": "2026-04-01T10:30:00Z",
  "data": [
    {
      "metric_type": "voltage",
      "value": 382.5,
      "unit": "V"
    }
  ]
}
```

**状态消息** (服务器→客户端):
```json
{
  "type": "status",
  "device_id": "dev_001",
  "status": "online",
  "health_score": 95
}
```

**告警消息** (服务器→客户端):
```json
{
  "type": "alert",
  "alert": {
    "id": "alert_001",
    "alert_level": "error",
    "alert_title": "电压超上限",
    "start_time": "2026-04-01T10:30:00Z"
  }
}
```

## 5. 错误码定义

### 5.1 通用错误码
| 错误码 | HTTP状态 | 描述 | 解决方案 |
|--------|----------|------|----------|
| DEVICE_001 | 400 | 设备编码已存在 | 使用其他设备编码 |
| DEVICE_002 | 404 | 设备不存在 | 检查设备ID |
| DEVICE_003 | 400 | 设备类型不存在 | 检查设备类型ID |
| DEVICE_004 | 400 | 场站不存在 | 检查场站ID |
| DEVICE_005 | 403 | 无权操作该设备 | 检查权限或联系管理员 |
| DEVICE_006 | 409 | 设备在线，无法删除 | 先将设备设为离线 |
| DEVICE_007 | 400 | 设备存在关联数据 | 先清理关联数据或使用force参数 |
| DEVICE_008 | 400 | 数据采集配置错误 | 检查配置格式和参数 |
| DEVICE_009 | 503 | 设备通信失败 | 检查设备网络连接 |
| DEVICE_010 | 429 | 操作频率过高 | 降低操作频率 |

### 5.2 数据相关错误码
| 错误码 | HTTP状态 | 描述 |
|--------|----------|------|
| METRIC_001 | 400 | 查询时间范围过大 |
| METRIC_002 | 400 | 不支持的聚合方式 |
| METRIC_003 | 404 | 指标类型不存在 |
| METRIC_004 | 503 | 数据服务暂时不可用 |

### 5.3 告警相关错误码
| 错误码 | HTTP状态 | 描述 |
|--------|----------|------|
| ALERT_001 | 404 | 告警不存在 |
| ALERT_002 | 400 | 告警状态不允许此操作 |
| ALERT_003 | 400 | 缺少解决说明 |
| ALERT_004 | 429 | 告警确认频率过高 |

## 6. 权限设计

### 6.1 角色权限矩阵
| 权限代码 | 描述 | admin | engineer | operator | viewer |
|----------|------|-------|----------|----------|--------|
| device:read | 查看设备 | ✓ | ✓ | ✓ | ✓ |
| device:create | 创建设备 | ✓ | ✓ | - | - |
| device:update | 更新设备 | ✓ | ✓ | 有限 | - |
| device:delete | 删除设备 | ✓ | - | - | - |
| device:control | 控制设备 | ✓ | ✓ | - | - |
| metric:read | 查看指标 | ✓ | ✓ | ✓ | ✓ |
| metric:export | 导出数据 | ✓ | ✓ | ✓ | - |
| alert:read | 查看告警 | ✓ | ✓ | ✓ | ✓ |
| alert:acknowledge | 确认告警 | ✓ | ✓ | ✓ | - |
| alert:resolve | 解决告警 | ✓ | ✓ | - | - |
| alert:config | 配置告警 | ✓ | ✓ | - | - |

### 6.2 数据权限范围
1. **场站范围**: 用户只能操作所属场站的设备
2. **设备类型**: 某些角色只能操作特定类型设备
3. **时间范围**: 历史数据查询时间范围限制

## 7. 性能优化

### 7.1 缓存策略
| 接口 | 缓存策略 | TTL | 缓存键 |
|------|----------|-----|--------|
| 设备列表 | Redis缓存 | 30s | `devices:list:{filter_hash}` |
| 设备详情 | Redis缓存 | 60s | `device:{id}:detail` |
| 实时数据 | 内存缓存 | 5s | `device:{id}:realtime` |
| 历史数据 | Redis缓存 | 5分钟 | `device:{id}:history:{query_hash}` |

### 7.2 数据库优化
1. **查询优化**: 使用覆盖索引，避免SELECT *
2. **分页优化**: 使用游标分页替代OFFSET分页
3. **连接池**: 合理的数据库连接池配置
4. **读写分离**: 报表查询走只读副本

### 7.3 异步处理
1. **批量操作**: 使用Celery异步任务
2. **数据导出**: 后台生成，提供下载链接
3. **控制指令**: 异步执行，轮询状态

## 8. 测试设计

### 8.1 单元测试用例
1. **设备创建测试**: 验证各种边界条件
2. **数据查询测试**: 验证过滤、排序、分页
3. **状态转换测试**: 验证设备状态机
4. **权限测试**: 验证角色权限控制

### 8.2 集成测试用例
1. **端到端流程**: 创建设备→采集数据→产生告警→处理告警
2. **并发测试**: 多用户同时操作设备
3. **性能测试**: 大数据量查询性能

### 8.3 压力测试场景
1. **高频数据写入**: 模拟1000台设备分钟级数据采集
2. **实时查询**: 50个并发用户实时监控
3. **历史查询**: 复杂聚合查询性能

## 9. 安全设计

### 9.1 输入验证
1. **SQL注入防护**: 参数化查询，ORM使用
2. **XSS防护**: 输出编码，CSP策略
3. **数据验证**: Pydantic模型验证，正则表达式

### 9.2 访问控制
1. **JWT验证**: Token过期、刷新机制
2. **角色权限**: 细粒度权限控制
3. **速率限制**: API调用频率限制

### 9.3 数据安全
1. **敏感数据加密**: 设备密码、配置加密存储
2. **数据传输安全**: HTTPS强制，WSS for WebSocket
3. **审计日志**: 记录所有关键操作

## 10. 附录

### 10.1 OpenAPI规范片段
```yaml
openapi: 3.0.3
info:
  title: NESOM设备监控API
  version: 1.0.0
  description: 新能源运维管理系统设备监控模块API

paths:
  /api/v1/devices:
    get:
      tags:
        - 设备管理
      summary: 获取设备列表
      description: 查询设备列表，支持分页、过滤、排序
      parameters:
        - $ref: '#/components/parameters/PageParam'
        - $ref: '#/components/parameters/PageSizeParam'
        - $ref: '#/components/parameters/FilterParam'
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DeviceListResponse'
```

### 10.2 Pydantic模型示例
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class DeviceCreate(BaseModel):
    device_code: str = Field(..., min_length=1, max_length=50, regex=r'^[A-Za-z0-9_-]+$')
    device_name: str = Field(..., min_length=1, max_length=100)
    device_type_id: str = Field(..., description="设备类型ID")
    station_id: str = Field(..., description="场站ID")
    status: Optional[str] = Field("offline", regex="^(online|offline|fault|maintenance|testing|standby)$")
    
    @validator('device_code')
    def validate_device_code(cls, v):
        # 自定义验证逻辑
        return v.upper()
```

### 10.3 部署配置
```yaml
# 环境变量配置
API_PREFIX: "/api/v1"
API_VERSION: "1.0"
CACHE_TTL_DEVICE_LIST: 30
CACHE_TTL_DEVICE_DETAIL: 60
RATE_LIMIT_PER_MINUTE: 100
WEBSOCKET_HEARTBEAT_INTERVAL: 30
```

---

**下一步**：
1. 评审本API设计
2. 实现Pydantic模型和路由
3. 编写单元测试和集成测试
4. 生成OpenAPI文档

**评审人**：后端架构师、前端开发、测试工程师  
**评审日期**：2026-04-02
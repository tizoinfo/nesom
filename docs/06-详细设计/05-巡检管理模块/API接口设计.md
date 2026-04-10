# 巡检管理模块 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-01  
**作者**: 智能体编排者  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-模块划分设计.md (巡检管理API部分)  
**实际代码参考**: backend/src/api/v1/inspection.py  
**数据库模型**: models_generated.py (巡检相关模型)

## 1. 设计概述

### 1.1 设计目标
提供完整的巡检管理RESTful API接口，支持：
- 巡检计划制定和管理
- 巡检路线和检查点管理
- 巡检任务分配和执行
- 现场巡检数据采集和结果提交
- 巡检报告生成和统计分析
- 移动端离线巡检支持

### 1.2 设计原则
1. **RESTful规范**：资源导向，HTTP方法语义明确
2. **版本控制**：API版本前缀 `/api/v1/`
3. **一致性**：统一响应格式、错误处理、分页规范
4. **安全性**：JWT认证，RBAC权限控制
5. **移动端友好**：支持离线操作、断点续传、冲突解决
6. **性能**：支持过滤、分页、字段选择、数据压缩
7. **文档化**：OpenAPI规范，代码即文档

### 1.3 技术约束
- **框架**: FastAPI 0.104+ (Python 3.11+)
- **认证**: JWT (JSON Web Token)
- **序列化**: Pydantic v2 模型验证
- **数据库**: SQLAlchemy 2.0 + MySQL 8.0
- **缓存**: Redis 7.0 (热点数据缓存)
- **文件存储**: MinIO/S3 (现场照片、音视频)
- **消息队列**: RabbitMQ/Kafka (异步任务处理)

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
  },
  "timestamp": "2026-04-01T12:00:00Z"
}
```

#### 错误响应格式
```json
{
  "code": 400,
  "message": "请求参数错误",
  "errors": [
    {
      "field": "plan_name",
      "message": "计划名称不能为空"
    }
  ],
  "timestamp": "2026-04-01T12:00:00Z"
}
```

#### 标准错误码
| 错误码 | 含义 | HTTP状态码 |
|--------|------|------------|
| 200 | 成功 | 200 OK |
| 400 | 请求参数错误 | 400 Bad Request |
| 401 | 未认证 | 401 Unauthorized |
| 403 | 无权限 | 403 Forbidden |
| 404 | 资源不存在 | 404 Not Found |
| 409 | 资源冲突 | 409 Conflict |
| 422 | 业务逻辑错误 | 422 Unprocessable Entity |
| 500 | 服务器内部错误 | 500 Internal Server Error |

### 2.2 分页规范
```json
// 请求参数
GET /api/v1/inspection/plans?page=1&page_size=20&sort_by=created_at&sort_order=desc

// 响应元数据
{
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_previous": false,
    "has_next": true
  }
}
```

### 2.3 过滤和搜索
```json
// 多条件过滤
GET /api/v1/inspection/tasks?status=assigned,in_progress&scheduled_date_gte=2026-04-01&scheduled_date_lte=2026-04-30

// 搜索
GET /api/v1/inspection/plans?search=光伏设备巡检

// 字段选择
GET /api/v1/inspection/plans?fields=id,plan_name,status,created_at
```

### 2.4 认证和授权
- **认证方式**: Bearer Token (JWT)
- **权限验证**: 基于角色的访问控制 (RBAC)
- **移动端特殊令牌**: 支持长期有效的设备令牌
- **离线令牌**: 支持离线操作临时令牌

## 3. 巡检计划API

### 3.1 获取巡检计划列表
**端点**: `GET /api/v1/inspection/plans`  
**描述**: 获取巡检计划列表，支持分页、过滤、搜索

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20，最大100 |
| status | string | 否 | 状态过滤，多个用逗号分隔 |
| inspection_type | string | 否 | 巡检类型过滤 |
| created_by | string | 否 | 创建人ID过滤 |
| search | string | 否 | 搜索计划名称和描述 |
| sort_by | string | 否 | 排序字段，默认created_at |
| sort_order | string | 否 | 排序方向，asc/desc，默认desc |

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "plan_001",
      "plan_code": "INSP-PLAN-202604-001",
      "plan_name": "光伏场站月度巡检",
      "inspection_type": "routine",
      "priority": "medium",
      "status": "active",
      "frequency_type": "monthly",
      "start_date": "2026-04-01",
      "end_date": "2026-12-31",
      "created_by_name": "张三",
      "created_at": "2026-04-01T10:00:00Z",
      "task_count": 8,
      "completed_task_count": 3
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

### 3.2 创建巡检计划
**端点**: `POST /api/v1/inspection/plans`  
**描述**: 创建新的巡检计划

**请求体**:
```json
{
  "plan_name": "光伏场站月度巡检",
  "description": "每月对光伏场站进行全面检查",
  "inspection_type": "routine",
  "priority": "medium",
  "route_id": "route_001",
  "template_id": "template_001",
  "frequency_type": "monthly",
  "frequency_value": 1,
  "frequency_days": [15], // 每月15号执行
  "start_date": "2026-04-01",
  "end_date": "2026-12-31",
  "start_time": "08:00:00",
  "end_time": "17:00:00",
  "estimated_duration": 240,
  "auto_assign": true,
  "assign_strategy": "skill_based",
  "require_photo": true,
  "require_gps": true,
  "require_signature": false
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检计划创建成功",
  "data": {
    "id": "plan_001",
    "plan_code": "INSP-PLAN-202604-001",
    "plan_name": "光伏场站月度巡检",
    "status": "draft",
    "created_at": "2026-04-01T10:00:00Z"
  }
}
```

### 3.3 获取巡检计划详情
**端点**: `GET /api/v1/inspection/plans/{plan_id}`  
**描述**: 获取指定巡检计划的详细信息

**路径参数**:
- `plan_id`: 巡检计划ID

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "plan_001",
    "plan_code": "INSP-PLAN-202604-001",
    "plan_name": "光伏场站月度巡检",
    "description": "每月对光伏场站进行全面检查",
    "inspection_type": "routine",
    "priority": "medium",
    "route": {
      "id": "route_001",
      "route_name": "光伏场站主路线",
      "total_checkpoints": 12
    },
    "template": {
      "id": "template_001",
      "template_name": "光伏设备标准巡检模板"
    },
    "frequency_type": "monthly",
    "frequency_value": 1,
    "frequency_days": [15],
    "start_date": "2026-04-01",
    "end_date": "2026-12-31",
    "start_time": "08:00:00",
    "end_time": "17:00:00",
    "estimated_duration": 240,
    "auto_assign": true,
    "assign_strategy": "skill_based",
    "require_photo": true,
    "require_gps": true,
    "require_signature": false,
    "status": "active",
    "created_by": "user_001",
    "created_by_name": "张三",
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-01T10:00:00Z",
    "generated_tasks": [
      {
        "scheduled_date": "2026-04-15",
        "task_count": 1,
        "status": "pending"
      },
      {
        "scheduled_date": "2026-05-15",
        "task_count": 1,
        "status": "pending"
      }
    ]
  }
}
```

### 3.4 更新巡检计划
**端点**: `PUT /api/v1/inspection/plans/{plan_id}`  
**描述**: 更新巡检计划信息

**路径参数**:
- `plan_id`: 巡检计划ID

**请求体**: 同创建接口，仅包含需要更新的字段

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检计划更新成功",
  "data": {
    "id": "plan_001",
    "updated_at": "2026-04-01T11:00:00Z"
  }
}
```

### 3.5 删除巡检计划
**端点**: `DELETE /api/v1/inspection/plans/{plan_id}`  
**描述**: 删除巡检计划（软删除）

**路径参数**:
- `plan_id`: 巡检计划ID

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检计划删除成功"
}
```

### 3.6 生成巡检任务
**端点**: `POST /api/v1/inspection/plans/{plan_id}/generate-tasks`  
**描述**: 为巡检计划生成指定日期的巡检任务

**路径参数**:
- `plan_id`: 巡检计划ID

**请求体**:
```json
{
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "override_existing": false // 是否覆盖已存在的任务
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "成功生成3个巡检任务",
  "data": {
    "generated_count": 3,
    "skipped_count": 0,
    "tasks": [
      {
        "id": "task_001",
        "task_code": "TASK-20260415-001",
        "scheduled_date": "2026-04-15",
        "status": "pending"
      }
    ]
  }
}
```

## 4. 巡检任务API

### 4.1 获取巡检任务列表
**端点**: `GET /api/v1/inspection/tasks`  
**描述**: 获取巡检任务列表，支持多种过滤条件

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |
| status | string | 否 | 状态过滤，多个用逗号分隔 |
| assigned_to | string | 否 | 分配人员ID过滤 |
| plan_id | string | 否 | 计划ID过滤 |
| scheduled_date_gte | string | 否 | 计划日期起始 |
| scheduled_date_lte | string | 否 | 计划日期结束 |
| priority | string | 否 | 优先级过滤 |
| is_offline | boolean | 否 | 是否离线任务 |
| search | string | 否 | 搜索任务编码、计划名称 |

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "task_001",
      "task_code": "TASK-20260415-001",
      "plan_name": "光伏场站月度巡检",
      "scheduled_date": "2026-04-15",
      "scheduled_start_time": "08:00:00",
      "scheduled_end_time": "12:00:00",
      "assigned_to_name": "李四",
      "status": "assigned",
      "priority": "medium",
      "total_checkpoints": 12,
      "completed_checkpoints": 0,
      "completion_rate": 0.0,
      "problem_count": 0,
      "is_offline": false,
      "created_at": "2026-04-01T10:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 85,
    "total_pages": 5
  }
}
```

### 4.2 获取巡检任务详情
**端点**: `GET /api/v1/inspection/tasks/{task_id}`  
**描述**: 获取巡检任务详细信息，包含检查点列表

**路径参数**:
- `task_id`: 巡检任务ID

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "task_001",
    "task_code": "TASK-20260415-001",
    "plan": {
      "id": "plan_001",
      "plan_name": "光伏场站月度巡检",
      "inspection_type": "routine"
    },
    "route": {
      "id": "route_001",
      "route_name": "光伏场站主路线",
      "total_checkpoints": 12,
      "estimated_duration": 240,
      "estimated_distance": 5.2
    },
    "assigned_to": "user_002",
    "assigned_to_name": "李四",
    "assigned_at": "2026-04-01T10:30:00Z",
    "scheduled_date": "2026-04-15",
    "scheduled_start_time": "08:00:00",
    "scheduled_end_time": "12:00:00",
    "actual_start_time": null,
    "actual_end_time": null,
    "status": "assigned",
    "priority": "medium",
    "total_checkpoints": 12,
    "completed_checkpoints": 0,
    "completion_rate": 0.0,
    "problem_count": 0,
    "is_offline": false,
    "offline_sync_status": null,
    "gps_track": null,
    "notes": null,
    "checkpoints": [
      {
        "id": "cp_001",
        "sequence": 1,
        "checkpoint_name": "1号光伏阵列",
        "checkpoint_type": "device",
        "device": {
          "id": "device_001",
          "device_code": "PV-ARRAY-001",
          "device_name": "1号光伏阵列",
          "status": "online"
        },
        "longitude": 116.397128,
        "latitude": 39.916527,
        "required_actions": ["photo", "temperature"],
        "estimated_duration": 15,
        "is_mandatory": true,
        "previous_result": {
          "completed_time": "2026-03-15T09:30:00Z",
          "overall_status": "normal",
          "problem_description": null
        }
      }
    ],
    "created_at": "2026-04-01T10:00:00Z",
    "updated_at": "2026-04-01T10:30:00Z"
  }
}
```

### 4.3 开始巡检任务
**端点**: `POST /api/v1/inspection/tasks/{task_id}/start`  
**描述**: 开始执行巡检任务，记录开始时间

**路径参数**:
- `task_id`: 巡检任务ID

**请求体**:
```json
{
  "start_location": {
    "longitude": 116.397128,
    "latitude": 39.916527,
    "address": "北京市东城区"
  },
  "notes": "开始巡检",
  "is_offline": false // 是否离线模式
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检任务开始成功",
  "data": {
    "task_id": "task_001",
    "status": "in_progress",
    "actual_start_time": "2026-04-15T08:05:00Z"
  }
}
```

### 4.4 完成巡检任务
**端点**: `POST /api/v1/inspection/tasks/{task_id}/complete`  
**描述**: 标记巡检任务为已完成

**路径参数**:
- `task_id`: 巡检任务ID

**请求体**:
```json
{
  "end_location": {
    "longitude": 116.397500,
    "latitude": 39.916800,
    "address": "北京市东城区"
  },
  "notes": "巡检完成",
  "signature": "data:image/png;base64,..." // 电子签名
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检任务完成成功",
  "data": {
    "task_id": "task_001",
    "status": "completed",
    "actual_end_time": "2026-04-15T11:45:00Z",
    "duration_minutes": 220,
    "completion_rate": 100.0,
    "problem_count": 2
  }
}
```

### 4.5 提交巡检结果
**端点**: `POST /api/v1/inspection/tasks/{task_id}/submit`  
**描述**: 提交巡检任务的所有检查点结果（批量提交）

**路径参数**:
- `task_id`: 巡检任务ID

**请求体**:
```json
{
  "results": [
    {
      "checkpoint_id": "cp_001",
      "arrived_time": "2026-04-15T08:15:00Z",
      "started_time": "2026-04-15T08:16:00Z",
      "completed_time": "2026-04-15T08:25:00Z",
      "longitude": 116.397128,
      "latitude": 39.916527,
      "location_verified": true,
      "check_items": [
        {
          "item": "外观检查",
          "status": "normal",
          "value": "完好",
          "notes": "无破损"
        },
        {
          "item": "温度检测",
          "status": "warning",
          "value": "65.5",
          "unit": "℃",
          "notes": "温度偏高，需关注"
        }
      ],
      "overall_status": "warning",
      "problem_description": "光伏板温度偏高",
      "photos": [
        {
          "filename": "photo_001.jpg",
          "description": "光伏板外观"
        }
      ],
      "temperature": 65.5,
      "notes": "温度偏高，建议后续监控"
    }
  ],
  "is_offline": false,
  "sync_token": "sync_001" // 离线同步令牌
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检结果提交成功",
  "data": {
    "task_id": "task_001",
    "submitted_count": 12,
    "completed_checkpoints": 12,
    "completion_rate": 100.0,
    "problem_count": 2,
    "generated_work_orders": 1
  }
}
```

### 4.6 重新分配巡检任务
**端点**: `PUT /api/v1/inspection/tasks/{task_id}/reassign`  
**描述**: 重新分配巡检任务给其他人员

**路径参数**:
- `task_id`: 巡检任务ID

**请求体**:
```json
{
  "assigned_to": "user_003",
  "reason": "原巡检人员请假"
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检任务重新分配成功",
  "data": {
    "task_id": "task_001",
    "assigned_to": "user_003",
    "assigned_to_name": "王五",
    "assigned_at": "2026-04-15T09:00:00Z"
  }
}
```

## 5. 移动端专用API

### 5.1 获取移动端巡检任务
**端点**: `GET /api/v1/mobile/inspection/tasks`  
**描述**: 移动端获取当前用户的巡检任务，支持离线数据同步

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| status | string | 否 | 任务状态过滤 |
| scheduled_date | string | 否 | 计划日期过滤 |
| limit | integer | 否 | 返回数量，默认50 |
| since | string | 否 | 仅返回此时间之后更新的任务 |
| include_details | boolean | 否 | 是否包含检查点详情 |

**请求头**:
- `X-Device-Id`: 设备唯一标识
- `X-Offline-Mode`: 离线模式标识

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "tasks": [
      {
        "id": "task_001",
        "task_code": "TASK-20260415-001",
        "plan_name": "光伏场站月度巡检",
        "scheduled_date": "2026-04-15",
        "status": "assigned",
        "priority": "medium",
        "total_checkpoints": 12,
        "completed_checkpoints": 0,
        "checkpoints": [
          {
            "id": "cp_001",
            "sequence": 1,
            "checkpoint_name": "1号光伏阵列",
            "checkpoint_type": "device",
            "device_code": "PV-ARRAY-001",
            "longitude": 116.397128,
            "latitude": 39.916527,
            "required_actions": ["photo", "temperature"],
            "inspection_items": [
              {
                "item": "外观检查",
                "type": "visual",
                "standard": "无破损、无污渍",
                "options": ["正常", "轻微破损", "严重破损"]
              }
            ],
            "is_mandatory": true,
            "tolerance_radius": 50
          }
        ],
        "sync_token": "sync_001",
        "last_updated": "2026-04-15T08:00:00Z"
      }
    ],
    "sync_info": {
      "server_time": "2026-04-15T08:05:00Z",
      "has_more": false,
      "next_sync_token": "sync_002"
    }
  }
}
```

### 5.2 提交移动端巡检结果
**端点**: `POST /api/v1/mobile/inspection/results`  
**描述**: 移动端提交巡检结果，支持离线数据批量同步

**请求体**:
```json
{
  "device_id": "device_001", // 移动设备ID
  "sync_token": "sync_001", // 同步令牌
  "results": [
    {
      "task_id": "task_001",
      "checkpoint_id": "cp_001",
      "local_id": "local_001", // 本地记录ID（离线时生成）
      "arrived_time": "2026-04-15T08:15:00Z",
      "completed_time": "2026-04-15T08:25:00Z",
      "longitude": 116.397128,
      "latitude": 39.916527,
      "check_items": [...],
      "overall_status": "warning",
      "photos": [...],
      "is_offline": true,
      "created_at": "2026-04-15T08:25:00Z", // 本地创建时间
      "updated_at": "2026-04-15T08:25:00Z"  // 本地更新时间
    }
  ],
  "conflict_resolution": "server_wins" // 冲突解决策略：server_wins/client_wins/merge
}
```

**响应示例**:
```json
{
  "code": 200,
  "message": "巡检结果同步成功",
  "data": {
    "synced_count": 12,
    "conflict_count": 0,
    "conflicts": [],
    "generated_work_orders": 1,
    "next_sync_token": "sync_002",
    "server_time": "2026-04-15T10:00:00Z"
  }
}
```

### 5.3 上传巡检附件
**端点**: `POST /api/v1/mobile/inspection/upload`  
**描述**: 上传巡检现场照片、视频、录音等附件

**请求格式**: `multipart/form-data`

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| file | file | 是 | 附件文件 |
| task_id | string | 是 | 关联任务ID |
| checkpoint_id | string | 是 | 关联检查点ID |
| file_type | string | 是 | 文件类型：photo/video/audio/document |
| description | string | 否 | 文件描述 |
| latitude | number | 否 | 拍摄纬度 |
| longitude | number | 否 | 拍摄经度 |
| timestamp | string | 否 | 拍摄时间 |

**响应示例**:
```json
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "file_id": "file_001",
    "filename": "photo_001.jpg",
    "url": "https://storage.example.com/inspection/photo_001.jpg",
    "thumbnail_url": "https://storage.example.com/inspection/thumb_photo_001.jpg",
    "size": 2048576,
    "content_type": "image/jpeg",
    "uploaded_at": "2026-04-15T08:25:00Z"
  }
}
```

### 5.4 离线同步状态检查
**端点**: `GET /api/v1/mobile/inspection/sync-status`  
**描述**: 检查离线数据同步状态和冲突

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| device_id | string | 是 | 设备ID |
| last_sync_time | string | 否 | 最后同步时间 |

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "device_id": "device_001",
    "last_sync_time": "2026-04-15T09:00:00Z",
    "pending_changes": {
      "results": 5,
      "photos": 3,
      "tasks": 2
    },
    "conflicts": [
      {
        "local_id": "local_001",
        "server_id": "result_001",
        "resource_type": "inspection_result",
        "local_updated": "2026-04-15T08:25:00Z",
        "server_updated": "2026-04-15T08:30:00Z",
        "differences": ["temperature_value"]
      }
    ],
    "server_time": "2026-04-15T10:00:00Z",
    "recommended_action": "review_conflicts"
  }
}
```

## 6. 巡检统计API

### 6.1 获取巡检统计
**端点**: `GET /api/v1/inspection/stats`  
**描述**: 获取巡检统计概览数据

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| station_id | string | 否 | 场站ID过滤 |
| start_date | string | 否 | 统计开始日期 |
| end_date | string | 否 | 统计结束日期 |
| group_by | string | 否 | 分组维度：day/week/month |

**响应示例**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "overview": {
      "total_tasks": 156,
      "completed_tasks": 142,
      "completion_rate": 91.0,
      "on_time_rate": 85.3,
      "problem_count": 28,
      "avg_duration": 215.5,
      "total_distance": 856.2
    },
    "by_status": {
      "pending": 5,
      "assigned": 8,
      "in_progress": 1,
      "completed": 142,
      "overdue": 3
    },
    "by_type": {
      "routine": 120,
      "special": 30,
      "emergency": 6
    },
    "trend": [
      {
        "date": "2026-04-01",
        "tasks": 12,
        "completed": 11,
        "problems": 2
      }
    ],
    "top_problem_devices": [
      {
        "device_id": "device_001",
        "device_name": "1号光伏阵列",
        "problem_count": 5,
        "last_problem": "温度偏高"
      }
    ],
    "inspector_performance": [
      {
        "user_id": "user_002",
        "user_name": "李四",
        "completed_tasks": 45,
        "completion_rate": 95.7,
        "avg_duration": 210.2,
        "problem_discovery_rate": 12.3
      }
    ]
  }
}
```

### 6.2 获取巡检报告
**端点**: `GET /api/v1/inspection/reports`  
**描述**: 生成和获取巡检报告

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| report_type | string | 是 | 报告类型：daily/weekly/monthly/quarterly/custom |
| station_id | string | 否 | 场站ID |
| start_date | string | 是 | 报告开始日期 |
| end_date | string | 是 | 报告结束日期 |
| format | string | 否 | 报告格式：json/pdf/excel，默认json |

**响应示例** (JSON格式):
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "report_id": "report_001",
    "report_type": "monthly",
    "period": "2026-04-01 至 2026-04-30",
    "generated_at": "2026-05-01T10:00:00Z",
    "summary": {
      "total_tasks": 156,
      "completed_tasks": 142,
      "completion_rate": 91.0,
      "problem_count": 28,
      "generated_work_orders": 15,
      "resolved_problems": 10
    },
    "detailed_analysis": {
      "task_distribution": {...},
      "problem_categories": {...},
      "device_health": {...},
      "inspector_efficiency": {...}
    },
    "recommendations": [
      "加强1号光伏阵列的温度监控",
      "优化巡检路线以减少巡检时间",
      "对巡检人员李四进行专项培训"
    ],
    "download_url": "https://storage.example.com/reports/report_001.pdf"
  }
}
```

### 6.3 导出巡检数据
**端点**: `GET /api/v1/inspection/export`  
**描述**: 导出巡检数据为Excel/CSV格式

**请求参数**:
| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| data_type | string | 是 | 数据类型：tasks/results/problems |
| format | string | 是 | 格式：excel/csv |
| start_date | string | 是 | 开始日期 |
| end_date | string | 是 | 结束日期 |
| station_id | string | 否 | 场站ID |
| include_attachments | boolean | 否 | 是否包含附件链接 |

**响应**: 返回文件流，Content-Type根据格式设置

## 7. 巡检路线和检查点API

### 7.1 获取巡检路线列表
**端点**: `GET /api/v1/inspection/routes`  
**描述**: 获取巡检路线列表

### 7.2 创建巡检路线
**端点**: `POST /api/v1/inspection/routes`  
**描述**: 创建新的巡检路线

### 7.3 获取巡检路线详情
**端点**: `GET /api/v1/inspection/routes/{route_id}`  
**描述**: 获取巡检路线详细信息，包含检查点列表

### 7.4 更新巡检路线
**端点**: `PUT /api/v1/inspection/routes/{route_id}`  
**描述**: 更新巡检路线信息

### 7.5 优化巡检路线
**端点**: `POST /api/v1/inspection/routes/{route_id}/optimize`  
**描述**: 优化巡检路线顺序

## 8. 巡检模板API

### 8.1 获取巡检模板列表
**端点**: `GET /api/v1/inspection/templates`  
**描述**: 获取巡检模板列表

### 8.2 创建巡检模板
**端点**: `POST /api/v1/inspection/templates`  
**描述**: 创建新的巡检模板

### 8.3 获取巡检模板详情
**端点**: `GET /api/v1/inspection/templates/{template_id}`  
**描述**: 获取巡检模板详细信息

### 8.4 复制巡检模板
**端点**: `POST /api/v1/inspection/templates/{template_id}/copy`  
**描述**: 复制巡检模板创建新版本

## 9. 错误处理

### 9.1 业务逻辑错误
```json
{
  "code": 422,
  "message": "业务逻辑错误",
  "errors": [
    {
      "code": "INSPECTION_TASK_ALREADY_STARTED",
      "message": "巡检任务已开始，不能重复开始",
      "details": {
        "task_id": "task_001",
        "started_at": "2026-04-15T08:05:00Z"
      }
    }
  ]
}
```

### 9.2 离线同步冲突错误
```json
{
  "code": 409,
  "message": "数据同步冲突",
  "errors": [
    {
      "code": "SYNC_CONFLICT",
      "message": "服务器数据已被修改",
      "conflicts": [
        {
          "field": "temperature",
          "local_value": 65.5,
          "server_value": 62.3,
          "resolution": "server_wins"
        }
      ]
    }
  ]
}
```

### 9.3 移动端离线错误
```json
{
  "code": 503,
  "message": "当前处于离线模式",
  "errors": [
    {
      "code": "OFFLINE_MODE",
      "message": "网络连接不可用，数据已保存到本地",
      "local_id": "local_001",
      "retry_after": 300 // 建议重试时间（秒）
    }
  ]
}
```

## 10. 性能优化建议

### 10.1 缓存策略
1. **巡检模板缓存**: Redis缓存，TTL 1小时
2. **路线数据缓存**: Redis缓存，TTL 30分钟
3. **用户任务列表缓存**: Redis缓存，TTL 5分钟

### 10.2 数据库优化
1. **查询优化**: 巡检任务列表使用覆盖索引
2. **分区策略**: 巡检结果表按时间分区
3. **读写分离**: 报表查询使用只读副本

### 10.3 移动端优化
1. **增量同步**: 只同步变更数据
2. **数据压缩**: 使用gzip压缩传输数据
3. **图片优化**: 自动生成缩略图，分片上传

## 11. 安全考虑

### 11.1 认证授权
1. **JWT令牌**: 短期访问令牌 + 长期刷新令牌
2. **设备绑定**: 移动端设备与用户绑定
3. **权限验证**: 基于场站、区域的细粒度权限控制

### 11.2 数据安全
1. **照片加密**: 上传前本地加密，存储加密
2. **GPS隐私**: 支持轨迹数据脱敏
3. **离线数据**: 本地数据库加密存储

### 11.3 防篡改设计
1. **数据签名**: 重要操作记录数字签名
2. **时间戳验证**: 服务器验证操作时间合理性
3. **位置验证**: GPS位置与服务端验证

## 12. 附录

### 12.1 API调用频率限制
| 接口类别 | 频率限制 | 说明 |
|----------|----------|------|
| 巡检结果提交 | 10次/分钟 | 防止恶意提交 |
| 文件上传 | 5次/分钟 | 防止滥用存储 |
| 统计查询 | 30次/分钟 | 减轻数据库压力 |
| 移动端同步 | 1次/10秒 | 平衡实时性和性能 |

### 12.2 移动端离线存储结构
```json
{
  "local_db": {
    "tasks": "本地任务表",
    "results": "本地结果表",
    "photos": "本地照片元数据",
    "sync_queue": "同步队列",
    "conflicts": "冲突记录"
  },
  "files": {
    "photos": "照片文件",
    "videos": "视频文件",
    "audio": "录音文件"
  }
}
```

### 12.3 后续扩展接口
1. **AR巡检接口**: 支持AR眼镜巡检数据采集
2. **AI分析接口**: 集成AI进行照片自动分析
3. **实时监控接口**: WebSocket实时推送巡检状态
4. **第三方集成接口**: 与第三方系统对接

---

**下一步**:
1. 评审本API设计
2. 生成OpenAPI/Swagger文档
3. 实现API接口代码
4. 编写API测试用例

**评审人**: 后端架构师、移动端开发、测试工程师、模块负责人  
**评审日期**: 2026-04-02
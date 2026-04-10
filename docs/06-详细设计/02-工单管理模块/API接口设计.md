# 工单管理模块 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-02  
**作者**: 高级项目经理  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-模块划分设计.md (工单管理API部分)  
**技术栈**: Vue 3.4 + Python 3.11 + FastAPI + MySQL 8.0 + Redis + Docker

## 1. 设计概述

### 1.1 设计目标
提供完整的工单管理RESTful API接口，支持：
- 工单全生命周期管理（创建、分配、处理、关闭、归档）
- 多种工单类型支持（维修、巡检、保养、故障）
- 工单优先级和紧急程度管理
- 工单流转状态机操作
- 工单与设备、备件、人员的关联管理
- 工单统计和绩效分析

### 1.2 设计原则
1. **RESTful规范**：资源导向，HTTP方法语义明确
2. **版本控制**：API版本前缀 `/api/v1/`
3. **一致性**：统一响应格式、错误处理、分页规范
4. **安全性**：JWT认证，RBAC权限控制
5. **移动端优化**：支持扫码、拍照、离线同步
6. **事务完整性**：关键操作保证数据一致性

### 1.3 技术约束
- **框架**: FastAPI 0.104+ (Python 3.11+)
- **认证**: JWT (JSON Web Token)
- **序列化**: Pydantic v2 模型验证
- **数据库**: SQLAlchemy 2.0 + MySQL 8.0
- **缓存**: Redis 7.0 (工单状态缓存)
- **消息队列**: RabbitMQ/Celery (异步通知)

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
    "field": "work_order_no",
    "error": "工单编号已存在"
  },
  "timestamp": "2026-04-02T10:30:00Z"
}
```

### 2.2 分页规范
- **参数**: `page` (默认1), `page_size` (默认20, 最大100)
- **响应**: 包含`data`数组和`meta`分页信息
- **性能**: 基于创建时间的游标分页优化

### 2.3 过滤和排序
- **过滤**: `filter[status]=pending&filter[work_order_type]=repair`
- **范围过滤**: `filter[reported_at][gte]=2026-01-01&filter[reported_at][lte]=2026-12-31`
- **排序**: `sort=reported_at.desc,priority.asc`
- **字段选择**: `fields=id,work_order_no,title,status,priority`

### 2.4 认证和授权
- **认证头**: `Authorization: Bearer <jwt_token>`
- **权限**: 基于角色的访问控制 (RBAC)
  - `work_order:read` - 查看工单
  - `work_order:create` - 创建工单
  - `work_order:update` - 更新工单
  - `work_order:delete` - 删除工单
  - `work_order:assign` - 分配工单
  - `work_order:close` - 关闭工单
- **操作审计**: 所有变更记录操作日志

## 3. API端点详细设计

### 3.1 工单管理接口

#### 3.1.1 获取工单列表
**端点**: `GET /api/v1/work-orders`  
**描述**: 查询工单列表，支持分页、过滤、排序、字段选择

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| page | int | 否 | 页码，默认1 | `1` |
| page_size | int | 否 | 每页数量，默认20，最大100 | `20` |
| filter | object | 否 | 过滤条件 | `{"status": "pending", "work_order_type": "repair"}` |
| sort | string | 否 | 排序字段 | `reported_at.desc,priority.asc` |
| fields | string | 否 | 返回字段，逗号分隔 | `id,work_order_no,title,status,priority` |
| include | string | 否 | 包含关联数据 | `device,assigned_user` |
| my_work_orders | boolean | 否 | 仅查询分配给当前用户的工单 | `true` |
| overdue_only | boolean | 否 | 仅查询超时工单 | `true` |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": "wo_123456",
      "work_order_no": "WO-SH01-20260402-001",
      "title": "光伏逆变器故障维修",
      "work_order_type": "repair",
      "status": "assigned",
      "priority": "high",
      "emergency_level": "urgent",
      "device_name": "光伏逆变器 #001",
      "device_code": "PV-INV-001",
      "reported_by_name": "张三",
      "reported_at": "2026-04-02T09:30:00Z",
      "assigned_to_name": "李四",
      "scheduled_start": "2026-04-02T10:00:00Z",
      "scheduled_end": "2026-04-02T12:00:00Z",
      "completion_rate": 0,
      "location": "A区光伏阵列"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 125,
    "total_pages": 7
  }
}
```

**权限要求**: `work_order:read`

#### 3.1.2 创建工单
**端点**: `POST /api/v1/work-orders`  
**描述**: 创建新的工单，支持从模板创建

**请求体**:
```json
{
  "work_order_type": "repair",
  "title": "光伏逆变器故障维修",
  "description": "逆变器显示故障代码E001，需要立即检查",
  "priority": "high",
  "emergency_level": "urgent",
  "station_id": "st_001",
  "device_id": "dev_123",
  "scheduled_start": "2026-04-02T10:00:00Z",
  "scheduled_end": "2026-04-02T12:00:00Z",
  "estimated_duration": 120,
  "cost_estimate": 500.00,
  "location": "A区光伏阵列",
  "longitude": 121.4737,
  "latitude": 31.2304,
  "images": ["data:image/jpeg;base64,..."],
  "attachments": [],
  "tags": {"fault_code": "E001", "weather": "sunny"},
  "template_id": "tmp_001"  // 可选：从模板创建
}
```

**响应数据**:
```json
{
  "code": 201,
  "message": "工单创建成功",
  "data": {
    "id": "wo_123456",
    "work_order_no": "WO-SH01-20260402-001",
    "status": "draft",
    "created_at": "2026-04-02T09:30:00Z",
    "qr_code": "data:image/png;base64,..."
  }
}
```

**权限要求**: `work_order:create`

#### 3.1.3 获取工单详情
**端点**: `GET /api/v1/work-orders/{work_order_id}`  
**描述**: 获取工单详细信息，包括关联数据和历史记录

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| include | string | 否 | 包含关联数据: `details,status_history,evaluation,spare_parts` |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": "wo_123456",
    "work_order_no": "WO-SH01-20260402-001",
    "work_order_type": "repair",
    "title": "光伏逆变器故障维修",
    "description": "逆变器显示故障代码E001，需要立即检查",
    "status": "assigned",
    "priority": "high",
    "emergency_level": "urgent",
    "station": {
      "id": "st_001",
      "name": "上海光伏电站"
    },
    "device": {
      "id": "dev_123",
      "name": "光伏逆变器 #001",
      "code": "PV-INV-001",
      "status": "fault"
    },
    "reported_by": {
      "id": "user_001",
      "name": "张三",
      "avatar": "https://..."
    },
    "assigned_to": {
      "id": "user_002",
      "name": "李四",
      "avatar": "https://..."
    },
    "scheduled_start": "2026-04-02T10:00:00Z",
    "scheduled_end": "2026-04-02T12:00:00Z",
    "actual_start": null,
    "actual_end": null,
    "estimated_duration": 120,
    "actual_duration": null,
    "completion_rate": 0,
    "cost_estimate": 500.00,
    "actual_cost": null,
    "location": "A区光伏阵列",
    "longitude": 121.4737,
    "latitude": 31.2304,
    "images": [...],
    "attachments": [...],
    "tags": {"fault_code": "E001", "weather": "sunny"},
    "created_at": "2026-04-02T09:30:00Z",
    "updated_at": "2026-04-02T09:35:00Z",
    "details": [
      {
        "id": 1,
        "step_number": 1,
        "step_title": "故障诊断",
        "step_description": "检查逆变器故障代码和运行状态",
        "status": "pending"
      }
    ],
    "status_history": [
      {
        "old_status": "draft",
        "new_status": "pending",
        "changed_by_name": "张三",
        "changed_at": "2026-04-02T09:31:00Z"
      }
    ]
  }
}
```

**权限要求**: `work_order:read`

#### 3.1.4 更新工单
**端点**: `PATCH /api/v1/work-orders/{work_order_id}`  
**描述**: 更新工单信息（部分更新）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "title": "光伏逆变器故障维修（更新）",
  "description": "逆变器显示故障代码E001，需要立即检查，现场发现还有其他问题",
  "priority": "emergency",
  "scheduled_end": "2026-04-02T14:00:00Z",
  "estimated_duration": 240,
  "cost_estimate": 800.00,
  "images": ["data:image/jpeg;base64,..."]  // 追加图片
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单更新成功",
  "data": {
    "id": "wo_123456",
    "updated_at": "2026-04-02T10:15:00Z"
  }
}
```

**权限要求**: `work_order:update` (注：已关闭工单不可更新)

#### 3.1.5 删除工单
**端点**: `DELETE /api/v1/work-orders/{work_order_id}`  
**描述**: 删除工单（仅限草稿状态或已取消状态）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**响应数据**:
```json
{
  "code": 200,
  "message": "工单删除成功"
}
```

**权限要求**: `work_order:delete` + `work_order:cancel` (仅限特定状态)

### 3.2 工单状态流转接口

#### 3.2.1 提交工单
**端点**: `POST /api/v1/work-orders/{work_order_id}/submit`  
**描述**: 将草稿状态工单提交为待分配状态

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "submit_notes": "故障已确认，需要立即处理"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单提交成功",
  "data": {
    "old_status": "draft",
    "new_status": "pending",
    "changed_at": "2026-04-02T10:20:00Z"
  }
}
```

**权限要求**: `work_order:update` (创建者或管理员)

#### 3.2.2 分配工单
**端点**: `POST /api/v1/work-orders/{work_order_id}/assign`  
**描述**: 将待分配工单分配给指定执行人

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "assigned_to": "user_002",
  "assign_notes": "李师傅有相关设备维修经验",
  "scheduled_start": "2026-04-02T10:30:00Z",
  "scheduled_end": "2026-04-02T12:30:00Z"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单分配成功",
  "data": {
    "old_status": "pending",
    "new_status": "assigned",
    "assigned_to": {
      "id": "user_002",
      "name": "李四"
    },
    "assigned_at": "2026-04-02T10:25:00Z"
  }
}
```

**权限要求**: `work_order:assign` (调度员或管理员)

#### 3.2.3 开始处理工单
**端点**: `POST /api/v1/work-orders/{work_order_id}/start`  
**描述**: 执行人开始处理工单（移动端扫码开始）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "location": "A区光伏阵列",
  "longitude": 121.4737,
  "latitude": 31.2304,
  "start_notes": "已到达现场，开始检查"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单开始处理",
  "data": {
    "old_status": "assigned",
    "new_status": "in_progress",
    "actual_start": "2026-04-02T10:30:00Z"
  }
}
```

**权限要求**: `work_order:update` (仅限分配的执行人)

#### 3.2.4 提交审核
**端点**: `POST /api/v1/work-orders/{work_order_id}/submit-review`  
**描述**: 执行人完成处理后提交审核

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "completion_notes": "故障已修复，测试运行正常",
  "completion_rate": 100,
  "actual_duration": 110,
  "images": ["data:image/jpeg;base64,..."]  // 完工照片
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单已提交审核",
  "data": {
    "old_status": "in_progress",
    "new_status": "pending_review",
    "actual_end": "2026-04-02T12:20:00Z",
    "completion_rate": 100,
    "actual_duration": 110
  }
}
```

**权限要求**: `work_order:update` (仅限分配的执行人)

#### 3.2.5 审核通过
**端点**: `POST /api/v1/work-orders/{work_order_id}/approve`  
**描述**: 审核人审核通过工单

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "approve_notes": "维修质量合格，符合标准",
  "quality_check": "pass",
  "actual_cost": 450.00
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单审核通过",
  "data": {
    "old_status": "pending_review",
    "new_status": "completed",
    "approved_at": "2026-04-02T14:00:00Z"
  }
}
```

**权限要求**: `work_order:review` (审核人角色)

#### 3.2.6 关闭工单
**端点**: `POST /api/v1/work-orders/{work_order_id}/close`  
**描述**: 关闭已完成的工单

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "close_notes": "工单所有流程已完成",
  "archive_reason": "normal_completion"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单已关闭",
  "data": {
    "old_status": "completed",
    "new_status": "closed",
    "closed_at": "2026-04-02T15:00:00Z"
  }
}
```

**权限要求**: `work_order:close` (创建者、审核人或管理员)

#### 3.2.7 取消工单
**端点**: `POST /api/v1/work-orders/{work_order_id}/cancel`  
**描述**: 取消工单（仅限特定状态）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "cancel_reason": "设备已更换，无需维修",
  "cancel_notes": "用户取消维修请求"
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "工单已取消",
  "data": {
    "old_status": "pending",
    "new_status": "cancelled",
    "cancelled_at": "2026-04-02T10:10:00Z"
  }
}
```

**权限要求**: `work_order:cancel` (创建者、分配人或管理员)

### 3.3 工单明细管理接口

#### 3.3.1 添加工单处理步骤
**端点**: `POST /api/v1/work-orders/{work_order_id}/details`  
**描述**: 为工单添加处理步骤（移动端记录）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "step_title": "更换故障模块",
  "step_description": "发现电源模块损坏，更换新模块",
  "findings": "电源模块烧毁，可能由于电压不稳",
  "actions_taken": "断开电源，拆除旧模块，安装新模块",
  "tools_used": ["万用表", "螺丝刀", "电烙铁"],
  "parts_used": [
    {
      "spare_part_id": "sp_001",
      "quantity": 1,
      "unit": "piece"
    }
  ],
  "before_images": ["data:image/jpeg;base64,..."],
  "after_images": ["data:image/jpeg;base64,..."],
  "test_results": {
    "voltage": "220V",
    "current": "5A",
    "status": "normal"
  },
  "notes": "更换后测试正常",
  "started_at": "2026-04-02T11:00:00Z",
  "completed_at": "2026-04-02T11:45:00Z"
}
```

**响应数据**:
```json
{
  "code": 201,
  "message": "处理步骤添加成功",
  "data": {
    "id": 1,
    "step_number": 1,
    "created_at": "2026-04-02T11:50:00Z"
  }
}
```

**权限要求**: `work_order:update` (仅限分配的执行人且工单状态为in_progress)

#### 3.3.2 更新处理步骤
**端点**: `PATCH /api/v1/work-orders/{work_order_id}/details/{detail_id}`  
**描述**: 更新工单处理步骤

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |
| detail_id | int | 是 | 步骤ID |

**权限要求**: `work_order:update` (仅限步骤创建者)

#### 3.3.3 删除处理步骤
**端点**: `DELETE /api/v1/work-orders/{work_order_id}/details/{detail_id}`  
**描述**: 删除工单处理步骤

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |
| detail_id | int | 是 | 步骤ID |

**权限要求**: `work_order:update` (仅限步骤创建者且工单未关闭)

### 3.4 工单评价接口

#### 3.4.1 添加工单评价
**端点**: `POST /api/v1/work-orders/{work_order_id}/evaluation`  
**描述**: 为已关闭工单添加评价

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "satisfaction_score": 5,
  "timeliness_score": 4,
  "quality_score": 5,
  "communication_score": 4,
  "positive_comments": "师傅技术好，解决问题快",
  "improvement_suggestions": "可以提前告知需要的备件",
  "would_recommend": true,
  "evaluator_role": "customer"
}
```

**响应数据**:
```json
{
  "code": 201,
  "message": "评价提交成功",
  "data": {
    "id": 1,
    "overall_score": 4.5,
    "evaluated_at": "2026-04-02T16:00:00Z"
  }
}
```

**权限要求**: 工单相关人员（客户、执行人、主管等）

#### 3.4.2 回复评价
**端点**: `POST /api/v1/work-orders/{work_order_id}/evaluation/response`  
**描述**: 回复工单评价

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_id | string | 是 | 工单ID |

**请求体**:
```json
{
  "response_content": "感谢您的反馈，我们会改进备件通知流程",
  "response_by": "user_002"
}
```

**权限要求**: `work_order:review` (管理员或执行人主管)

### 3.5 工单模板接口

#### 3.5.1 获取工单模板列表
**端点**: `GET /api/v1/work-order-templates`  
**描述**: 查询工单模板列表

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| work_order_type | string | 否 | 按工单类型过滤 |
| device_type_id | string | 否 | 按设备类型过滤 |
| is_active | boolean | 否 | 是否启用 |

**权限要求**: `work_order:read`

#### 3.5.2 创建工单模板
**端点**: `POST /api/v1/work-order-templates`  
**描述**: 创建新的工单模板

**请求体**:
```json
{
  "template_code": "TMP-REPAIR-PV-INV",
  "template_name": "光伏逆变器维修模板",
  "work_order_type": "repair",
  "device_type_id": "dt_001",
  "priority": "high",
  "estimated_duration": 180,
  "cost_estimate": 500.00,
  "description_template": "${device_name}出现故障，需要维修",
  "steps_template": [
    {
      "step_title": "故障诊断",
      "step_description": "检查逆变器故障代码和运行状态",
      "estimated_duration": 30
    },
    {
      "step_title": "故障修复",
      "step_description": "根据诊断结果进行修复",
      "estimated_duration": 120
    }
  ],
  "required_tools": ["万用表", "螺丝刀"],
  "required_parts": ["电源模块", "保险丝"],
  "safety_instructions": "操作前必须断开电源",
  "quality_standards": "修复后需测试运行30分钟"
}
```

**权限要求**: `work_order:create` + 模板管理权限

#### 3.5.3 使用模板创建工单
**端点**: `POST /api/v1/work-orders/from-template/{template_id}`  
**描述**: 使用模板快速创建工单

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| template_id | string | 是 | 模板ID |

**请求体**:
```json
{
  "station_id": "st_001",
  "device_id": "dev_123",
  "title": "光伏逆变器故障维修",
  "description": "逆变器显示故障代码，需要维修",
  "priority": "high",
  "scheduled_start": "2026-04-02T10:00:00Z"
}
```

**响应数据**:
```json
{
  "code": 201,
  "message": "工单创建成功",
  "data": {
    "id": "wo_123457",
    "work_order_no": "WO-SH01-20260402-002",
    "steps_generated": 2,
    "estimated_duration": 180,
    "cost_estimate": 500.00
  }
}
```

**权限要求**: `work_order:create`

### 3.6 工单统计接口

#### 3.6.1 工单数量统计
**端点**: `GET /api/v1/work-orders/statistics/count`  
**描述**: 获取工单数量统计（按状态、类型、优先级等）

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| station_id | string | 否 | 场站ID |
| time_range | string | 否 | 时间范围: today,week,month,year |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "total": 156,
    "by_status": {
      "pending": 12,
      "assigned": 8,
      "in_progress": 15,
      "pending_review": 5,
      "completed": 98,
      "closed": 15,
      "cancelled": 3
    },
    "by_type": {
      "repair": 85,
      "inspection": 45,
      "maintenance": 20,
      "fault": 6
    },
    "by_priority": {
      "low": 30,
      "medium": 90,
      "high": 30,
      "emergency": 6
    }
  }
}
```

**权限要求**: `work_order:read` + 统计权限

#### 3.6.2 工单时效统计
**端点**: `GET /api/v1/work-orders/statistics/timeliness`  
**描述**: 获取工单处理时效统计

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "avg_processing_time": 135.5,  // 平均处理时间（分钟）
    "avg_response_time": 25.3,     // 平均响应时间（分钟）
    "on_time_rate": 0.87,          // 按时完成率
    "overdue_count": 8,            // 超时工单数
    "by_priority": {
      "low": {"avg_time": 180.2, "on_time_rate": 0.95},
      "medium": {"avg_time": 135.5, "on_time_rate": 0.88},
      "high": {"avg_time": 90.3, "on_time_rate": 0.82},
      "emergency": {"avg_time": 65.1, "on_time_rate": 0.75}
    }
  }
}
```

#### 3.6.3 人员绩效统计
**端点**: `GET /api/v1/work-orders/statistics/performance`  
**描述**: 获取人员工单处理绩效统计

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| user_id | string | 否 | 用户ID（不传则统计所有人员） |
| time_range | string | 否 | 时间范围 |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "user_id": "user_002",
      "user_name": "李四",
      "total_assigned": 45,
      "total_completed": 42,
      "completion_rate": 0.93,
      "avg_processing_time": 125.3,
      "avg_satisfaction_score": 4.6,
      "on_time_rate": 0.89
    }
  ]
}
```

**权限要求**: `work_order:read` + 绩效管理权限

### 3.7 移动端专用接口

#### 3.7.1 扫码获取工单
**端点**: `GET /api/v1/work-orders/qr/{qr_content}`  
**描述**: 通过扫描二维码获取工单信息（移动端）

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| qr_content | string | 是 | 二维码内容 |

**响应数据**:
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "work_order_id": "wo_123456",
    "work_order_no": "WO-SH01-20260402-001",
    "title": "光伏逆变器故障维修",
    "status": "assigned",
    "assigned_to": "user_002",
    "assigned_to_name": "李四",
    "device_name": "光伏逆变器 #001",
    "location": "A区光伏阵列",
    "scheduled_start": "2026-04-02T10:00:00Z",
    "qr_code_valid": true
  }
}
```

**权限要求**: 移动端认证用户

#### 3.7.2 移动端签到
**端点**: `POST /api/v1/work-orders/{work_order_id}/mobile-checkin`  
**描述**: 移动端到达现场签到（记录位置和时间）

**请求体**:
```json
{
  "longitude": 121.4737,
  "latitude": 31.2304,
  "accuracy": 10.5,
  "checkin_notes": "已到达现场",
  "photo": "data:image/jpeg;base64,..."  // 现场照片
}
```

#### 3.7.3 离线工单同步
**端点**: `POST /api/v1/work-orders/offline-sync`  
**描述**: 移动端离线数据同步（批量上传）

**请求体**:
```json
{
  "sync_id": "sync_001",
  "device_id": "mobile_device_001",
  "operations": [
    {
      "type": "work_order_start",
      "work_order_id": "wo_123456",
      "data": {...},
      "local_timestamp": "2026-04-02T10:30:00Z"
    },
    {
      "type": "work_order_detail",
      "work_order_id": "wo_123456",
      "data": {...},
      "local_timestamp": "2026-04-02T11:00:00Z"
    }
  ]
}
```

**响应数据**:
```json
{
  "code": 200,
  "message": "同步成功",
  "data": {
    "success_count": 2,
    "failed_count": 0,
    "conflicts": []
  }
}
```

## 4. 错误码设计

### 4.1 通用错误码
| 错误码 | 描述 | HTTP状态码 |
|--------|------|------------|
| 40001 | 请求参数错误 | 400 |
| 40101 | 未认证 | 401 |
| 40301 | 权限不足 | 403 |
| 40401 | 资源不存在 | 404 |
| 40901 | 资源冲突 | 409 |
| 42201 | 业务规则验证失败 | 422 |
| 50001 | 服务器内部错误 | 500 |

### 4.2 工单特定错误码
| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| 42001 | 工单状态不允许此操作 | 检查工单当前状态 |
| 42002 | 工单已关闭，不可修改 | 工单关闭后为只读状态 |
| 42003 | 工单分配人员不存在或无权限 | 检查人员信息和权限 |
| 42004 | 设备不存在或不可用 | 检查设备状态 |
| 42005 | 备件库存不足 | 检查备件库存 |
| 42006 | 工单模板不存在或已禁用 | 选择有效模板 |

## 5. 性能优化

### 5.1 缓存策略
1. **工单列表缓存**: Redis缓存热门查询结果，TTL 5分钟
2. **工单详情缓存**: 高频访问工单缓存，TTL 2分钟
3. **统计结果缓存**: 预计算统计结果，TTL 15分钟

### 5.2 数据库优化
1. **索引优化**: 为查询频繁字段建立组合索引
2. **读写分离**: 报表查询走只读副本
3. **分页优化**: 使用游标分页替代OFFSET分页

### 5.3 异步处理
1. **通知发送**: 工单状态变更通知异步发送
2. **统计计算**: 非实时统计异步计算
3. **文件处理**: 图片上传和处理异步进行

## 6. 安全设计

### 6.1 认证授权
1. **JWT认证**: 短期token + 刷新token机制
2. **权限校验**: 接口级别细粒度权限控制
3. **操作审计**: 记录所有工单变更操作

### 6.2 数据安全
1. **输入验证**: Pydantic模型严格验证
2. **SQL防注入**: 使用ORM参数化查询
3. **敏感数据脱敏**: 对外接口敏感字段脱敏

### 6.3 移动端安全
1. **离线数据加密**: 本地存储数据加密
2. **传输安全**: HTTPS + 证书绑定
3. **会话管理**: 移动端会话超时控制

## 7. 监控和日志

### 7.1 监控指标
1. **API响应时间**: P95 < 500ms
2. **错误率**: < 0.1%
3. **并发连接数**: 监控活跃连接
4. **缓存命中率**: > 85%

### 7.2 日志记录
1. **访问日志**: 记录所有API请求
2. **错误日志**: 记录异常和错误详情
3. **审计日志**: 记录工单关键操作
4. **性能日志**: 记录慢查询和耗时操作

---

**下一步**：
1. 评审本API设计
2. 生成OpenAPI规范文档
3. 实现API接口代码
4. 编写API测试用例

**评审人**：后端架构师、前端开发、测试工程师  
**评审日期**：2026-04-02
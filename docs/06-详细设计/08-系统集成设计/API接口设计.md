# 系统集成设计 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-02  
**作者**: 工作流架构师  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-系统架构设计.md (集成API部分)  
**实际代码参考**: backend/src/api/v1/integration/ 目录下的集成API  
**数据库模型**: integration_events, data_sync_records, api_call_logs等表

## 1. 设计概述

### 1.1 设计目标
提供标准化的跨模块集成API接口，支持NESOM系统7个MVP模块间的高效、可靠、可监控的数据交互，包括：
- 事件发布和订阅API
- 数据同步和批量传输API
- 集成健康状态监控API
- 集成配置和管理API
- 故障诊断和排查API

### 1.2 设计原则
1. **标准化**：统一API设计规范、错误处理、认证授权
2. **可观测性**：每个API调用可追踪、可监控、可审计
3. **可靠性**：支持重试、幂等、降级、熔断
4. **安全性**：严格的身份验证、授权、输入验证
5. **性能**：支持批量操作、异步处理、缓存
6. **版本管理**：支持API版本演进和兼容性

### 1.3 技术约束
- **API网关**: Kong 3.4+ (OpenResty + Lua)
- **认证**: JWT (HS256/RSA256) + OAuth2.0
- **序列化**: JSON + Protobuf (高性能场景)
- **传输协议**: HTTP/2 + gRPC (内部服务)
- **消息队列**: RabbitMQ 3.12 + Kafka 3.5 (事件驱动)
- **监控**: Prometheus + Grafana (指标收集)

### 1.4 API分类
| 类别 | 功能 | 协议 | 认证 | 典型场景 |
|------|------|------|------|----------|
| 事件API | 事件发布、订阅、查询 | HTTP/2 + WebSocket | JWT | 实时状态变更通知 |
| 数据API | 数据同步、批量传输 | HTTP/2 + gRPC | 服务间证书 | 批量数据同步 |
| 管理API | 集成配置、监控、管理 | HTTP/1.1 | JWT + RBAC | 运维管理 |
| 诊断API | 健康检查、链路追踪 | HTTP/1.1 | 内部Token | 故障排查 |

## 2. 通用设计规范

### 2.1 请求/响应格式

#### 2.1.1 标准请求头
```http
Authorization: Bearer {jwt_token}
X-Request-ID: {uuid}
X-Correlation-ID: {uuid}
X-Client-Version: 1.0.0
X-Client-Module: {module_name}
Content-Type: application/json
Accept: application/json
```

#### 2.1.2 成功响应格式
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},               // 响应数据
  "meta": {                   // 分页/元数据
    "request_id": "req_123",
    "timestamp": "2026-04-02T10:30:00Z",
    "version": "1.0"
  }
}
```

#### 2.1.3 错误响应格式
```json
{
  "code": 400,
  "message": "请求参数错误",
  "errors": [                 // 错误详情数组
    {
      "field": "event_type",
      "code": "INVALID_VALUE",
      "message": "事件类型无效"
    }
  ],
  "meta": {
    "request_id": "req_123",
    "timestamp": "2026-04-02T10:30:00Z",
    "documentation": "https://docs.nesom.com/errors/INVALID_VALUE"
  }
}
```

### 2.2 错误码规范
| 错误码范围 | 类别 | 描述 |
|------------|------|------|
| 2xx | 成功 | 请求成功处理 |
| 400-499 | 客户端错误 | 请求参数、认证、权限等问题 |
| 500-599 | 服务器错误 | 服务端处理失败 |
| 600-699 | 集成错误 | 跨模块集成特定错误 |

#### 2.2.1 集成特定错误码
| 错误码 | 错误常量 | 描述 |
|--------|----------|------|
| 600 | INTEGRATION_EVENT_VALIDATION_FAILED | 事件验证失败 |
| 601 | INTEGRATION_EVENT_PUBLISH_FAILED | 事件发布失败 |
| 602 | INTEGRATION_SYNC_JOB_FAILED | 数据同步作业失败 |
| 603 | INTEGRATION_QUEUE_OVERFLOW | 消息队列溢出 |
| 604 | INTEGRATION_TIMEOUT | 集成调用超时 |
| 605 | INTEGRATION_CIRCUIT_BREAKER_OPEN | 熔断器打开 |
| 606 | INTEGRATION_DATA_MAPPING_FAILED | 数据映射失败 |

### 2.3 分页规范
- **参数**: `page` (默认1), `page_size` (默认20, 最大1000)
- **游标分页**: `cursor` + `limit` (用于大数据集)
- **响应**: 包含`data`数组和`pagination`信息

### 2.4 认证和授权
- **服务间认证**: mTLS双向证书认证
- **用户认证**: JWT + OAuth2.0授权码模式
- **权限控制**: 基于角色的细粒度权限(RBAC)
- **审计日志**: 记录所有API调用和操作

### 2.5 限流和熔断
- **限流策略**: 令牌桶算法，基于用户/模块/IP
- **熔断配置**: 错误率>50%或响应时间>5秒触发
- **降级策略**: 返回缓存数据或默认值

## 3. 事件API详细设计

### 3.1 事件发布接口

#### 3.1.1 发布单个事件
**端点**: `POST /api/v1/integration/events`  
**描述**: 发布一个集成事件到事件总线

**请求头**:
```
Authorization: Bearer {jwt_token}
X-Request-ID: {uuid}
Content-Type: application/json
```

**请求体**:
```json
{
  "event_type": "entity_updated",
  "source_module": "device_monitoring",
  "entity_type": "device",
  "entity_id": "dev_123456",
  "payload": {
    "before": {"status": "online"},
    "after": {"status": "offline"},
    "changed_fields": ["status"]
  },
  "metadata": {
    "triggered_by": "user_123",
    "correlation_id": "req_789"
  }
}
```

**响应体** (成功):
```json
{
  "code": 200,
  "message": "事件发布成功",
  "data": {
    "event_id": "DM-DEVICE-UPDATE-20260402103000123-ABC123",
    "published_at": "2026-04-02T10:30:00.123Z",
    "queue_position": 5
  }
}
```

**错误响应**:
- `400 INTEGRATION_EVENT_VALIDATION_FAILED`: 事件数据验证失败
- `401 UNAUTHORIZED`: 认证失败
- `403 FORBIDDEN`: 无事件发布权限
- `503 INTEGRATION_QUEUE_OVERFLOW`: 消息队列满，请稍后重试

#### 3.1.2 批量发布事件
**端点**: `POST /api/v1/integration/events/batch`  
**描述**: 批量发布多个事件，提高吞吐量

**请求体**:
```json
{
  "events": [
    {
      "event_type": "entity_updated",
      "source_module": "device_monitoring",
      "entity_type": "device",
      "entity_id": "dev_123456",
      "payload": {...}
    },
    // 最多100个事件
  ]
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "批量事件发布完成",
  "data": {
    "total": 10,
    "success": 10,
    "failed": 0,
    "failed_events": []
  }
}
```

### 3.2 事件订阅接口

#### 3.2.1 创建事件订阅
**端点**: `POST /api/v1/integration/subscriptions`  
**描述**: 创建事件订阅，指定订阅条件和目标

**请求体**:
```json
{
  "subscription_name": "device_alerts_subscription",
  "module_name": "alarm_mgmt",
  "event_types": ["entity_updated", "entity_created"],
  "entity_types": ["device", "device_metric"],
  "filter_conditions": {
    "source_module": ["device_monitoring", "data_collection"],
    "payload.status": ["offline", "fault"]
  },
  "target_endpoint": "https://alarm-mgmt.internal/api/v1/events",
  "target_method": "POST",
  "retry_policy": {
    "max_retries": 3,
    "backoff_ms": [1000, 3000, 5000]
  },
  "dead_letter_queue": "dlq_device_alerts",
  "enabled": true
}
```

**响应体**:
```json
{
  "code": 201,
  "message": "订阅创建成功",
  "data": {
    "subscription_id": "sub_123456",
    "created_at": "2026-04-02T10:30:00Z"
  }
}
```

#### 3.2.2 WebSocket事件流
**端点**: `GET /api/v1/integration/events/stream`  
**描述**: 通过WebSocket实时接收事件流

**连接参数**:
```
ws://integration.internal/api/v1/integration/events/stream
?subscription_id=sub_123456
&token={jwt_token}
```

**消息格式**:
```json
{
  "type": "event",
  "data": {
    "event_id": "DM-DEVICE-UPDATE-20260402103000123-ABC123",
    "event_type": "entity_updated",
    // ... 完整事件数据
  }
}
```

### 3.3 事件查询接口

#### 3.3.1 查询事件历史
**端点**: `GET /api/v1/integration/events`  
**描述**: 查询历史事件，支持复杂过滤和分页

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| event_type | string | 否 | 事件类型过滤 |
| source_module | string | 否 | 来源模块过滤 |
| entity_type | string | 否 | 实体类型过滤 |
| entity_id | string | 否 | 实体ID过滤 |
| start_time | datetime | 否 | 开始时间(ISO8601) |
| end_time | datetime | 否 | 结束时间(ISO8601) |
| status | string | 否 | 事件状态过滤 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "event_id": "DM-DEVICE-UPDATE-20260402103000123-ABC123",
      "event_type": "entity_updated",
      "source_module": "device_monitoring",
      "entity_type": "device",
      "entity_id": "dev_123456",
      "published_at": "2026-04-02T10:30:00.123Z",
      "status": "completed"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 150,
      "total_pages": 8
    }
  }
}
```

## 4. 数据同步API详细设计

### 4.1 同步作业管理

#### 4.1.1 创建同步作业
**端点**: `POST /api/v1/integration/sync/jobs`  
**描述**: 创建数据同步作业，支持全量/增量同步

**请求体**:
```json
{
  "job_name": "device_metrics_daily_sync",
  "source_module": "data_collection",
  "target_module": "report_mgmt",
  "entity_type": "device_metrics",
  "sync_type": "incremental",
  "filter_criteria": {
    "collected_at": {
      "gte": "2026-04-01T00:00:00Z",
      "lte": "2026-04-01T23:59:59Z"
    }
  },
  "mapping_rules": [
    {
      "source_field": "device_id",
      "target_field": "device_id",
      "transformation": "direct"
    },
    {
      "source_field": "metric_value",
      "target_field": "value",
      "transformation": "round(2)"
    }
  ],
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *"  // 每天凌晨2点
  },
  "notifications": {
    "on_success": ["slack:#reports"],
    "on_failure": ["email:admin@nesom.com", "slack:#alerts"]
  }
}
```

**响应体**:
```json
{
  "code": 201,
  "message": "同步作业创建成功",
  "data": {
    "job_id": "job_123456",
    "next_run_time": "2026-04-03T02:00:00Z"
  }
}
```

#### 4.1.2 触发同步作业
**端点**: `POST /api/v1/integration/sync/jobs/{job_id}/trigger`  
**描述**: 立即触发同步作业执行

**响应体**:
```json
{
  "code": 200,
  "message": "同步作业已触发",
  "data": {
    "execution_id": "exec_789012",
    "estimated_duration": "5分钟"
  }
}
```

### 4.2 数据批量传输

#### 4.2.1 上传批量数据
**端点**: `POST /api/v1/integration/data/batch/upload`  
**描述**: 上传批量数据文件，支持多种格式

**请求头**:
```
Content-Type: multipart/form-data
```

**表单参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| file | file | 是 | 数据文件(CSV/JSON/Parquet) |
| format | string | 是 | 文件格式: csv/json/parquet |
| entity_type | string | 是 | 数据实体类型 |
| target_module | string | 是 | 目标模块 |
| mapping_config | string | 否 | 映射配置JSON字符串 |

**响应体**:
```json
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "file_id": "file_123456",
    "total_records": 10000,
    "estimated_processing_time": "2分钟"
  }
}
```

#### 4.2.2 查询批量传输状态
**端点**: `GET /api/v1/integration/data/batch/{file_id}/status`  
**描述**: 查询批量数据处理状态

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "file_id": "file_123456",
    "status": "processing",
    "processed_records": 5000,
    "failed_records": 10,
    "start_time": "2026-04-02T10:30:00Z",
    "estimated_completion_time": "2026-04-02T10:32:00Z",
    "errors": [
      {
        "record_index": 123,
        "error": "数据格式无效",
        "details": "字段device_id为空"
      }
    ]
  }
}
```

## 5. 集成管理API详细设计

### 5.1 集成配置管理

#### 5.1.1 获取集成配置
**端点**: `GET /api/v1/integration/config`  
**描述**: 获取当前集成系统配置

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| module | string | 否 | 模块名称过滤 |
| config_type | string | 否 | 配置类型: event/sync/api |

**响应体**:
```json
{
  "code": 200,
  "message": "配置查询成功",
  "data": {
    "event_config": {
      "max_batch_size": 100,
      "retry_policy": {
        "max_retries": 3,
        "backoff_multiplier": 2
      },
      "queues": {
        "default": {"capacity": 10000},
        "priority": {"capacity": 5000}
      }
    },
    "sync_config": {
      "default_page_size": 1000,
      "max_concurrent_jobs": 5,
      "timeout_seconds": 3600
    },
    "api_config": {
      "rate_limit_per_minute": 1000,
      "timeout_ms": 5000,
      "circuit_breaker": {
        "failure_threshold": 5,
        "reset_timeout_seconds": 60
      }
    }
  }
}
```

#### 5.1.2 更新集成配置
**端点**: `PUT /api/v1/integration/config`  
**描述**: 更新集成系统配置（需要管理员权限）

**请求体**:
```json
{
  "event_config": {
    "max_batch_size": 200
  },
  "sync_config": {
    "max_concurrent_jobs": 10
  }
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "配置更新成功",
  "data": {
    "updated_fields": ["event_config.max_batch_size", "sync_config.max_concurrent_jobs"],
    "requires_restart": false
  }
}
```

### 5.2 集成监控API

#### 5.2.1 获取集成健康状态
**端点**: `GET /api/v1/integration/health`  
**描述**: 获取集成系统各组件健康状态

**响应体**:
```json
{
  "code": 200,
  "message": "健康状态查询成功",
  "data": {
    "overall_status": "healthy",
    "components": [
      {
        "name": "event_bus",
        "type": "message_queue",
        "status": "healthy",
        "response_time_ms": 45,
        "last_check": "2026-04-02T10:30:00Z"
      },
      {
        "name": "data_sync_service",
        "type": "service",
        "status": "degraded",
        "response_time_ms": 1200,
        "last_check": "2026-04-02T10:30:00Z",
        "details": "高延迟，正在调查"
      }
    ],
    "metrics": {
      "event_throughput_per_minute": 500,
      "sync_success_rate": 99.8,
      "api_error_rate": 0.2
    }
  }
}
```

#### 5.2.2 获取集成性能指标
**端点**: `GET /api/v1/integration/metrics`  
**描述**: 获取集成系统性能指标数据

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| metric_name | string | 否 | 指标名称过滤 |
| start_time | datetime | 是 | 开始时间 |
| end_time | datetime | 是 | 结束时间 |
| interval | string | 否 | 聚合间隔: 1m/5m/1h |

**响应体**:
```json
{
  "code": 200,
  "message": "指标查询成功",
  "data": {
    "metrics": [
      {
        "name": "event_publish_rate",
        "unit": "events/second",
        "data": [
          {"timestamp": "2026-04-02T10:00:00Z", "value": 8.5},
          {"timestamp": "2026-04-02T10:05:00Z", "value": 9.2}
        ]
      },
      {
        "name": "sync_job_duration",
        "unit": "seconds",
        "data": [
          {"timestamp": "2026-04-02T10:00:00Z", "value": 45.2},
          {"timestamp": "2026-04-02T10:05:00Z", "value": 48.7}
        ]
      }
    ]
  }
}
```

### 5.3 集成诊断API

#### 5.3.1 诊断集成问题
**端点**: `POST /api/v1/integration/diagnose`  
**描述**: 诊断集成系统问题，提供修复建议

**请求体**:
```json
{
  "problem_type": "event_delayed",
  "module_name": "alarm_mgmt",
  "time_range": {
    "start": "2026-04-02T10:00:00Z",
    "end": "2026-04-02T11:00:00Z"
  },
  "entity_filter": {
    "entity_type": "device",
    "entity_id": "dev_123456"
  }
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "诊断完成",
  "data": {
    "problem_found": true,
    "root_cause": "消息队列消费者处理能力不足",
    "affected_components": ["event_consumer_alarm_mgmt", "rabbitmq_queue_events"],
    "metrics_analysis": {
      "queue_backlog": 1500,
      "consumer_throughput": 5,
      "recommended_throughput": 20
    },
    "recommendations": [
      "增加消费者实例数量",
      "优化事件处理逻辑",
      "增加队列分区"
    ],
    "auto_fix_available": true,
    "auto_fix_action": "scale_consumers",
    "estimated_fix_time": "5分钟"
  }
}
```

#### 5.3.2 重放集成事件
**端点**: `POST /api/v1/integration/events/replay`  
**描述**: 重放历史事件，用于故障恢复或测试

**请求体**:
```json
{
  "event_ids": ["event_123", "event_456"],
  "target_modules": ["alarm_mgmt", "report_mgmt"],
  "replay_mode": "full",  // full/partial
  "dry_run": false
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "事件重放完成",
  "data": {
    "total_events": 2,
    "successful": 2,
    "failed": 0,
    "replay_results": [
      {
        "event_id": "event_123",
        "status": "replayed",
        "new_event_id": "event_123_replay_001",
        "target_module": "alarm_mgmt",
        "result": "成功触发告警"
      }
    ]
  }
}
```

## 6. 安全API详细设计

### 6.1 集成认证API

#### 6.1.1 获取服务间访问令牌
**端点**: `POST /api/v1/integration/auth/token`  
**描述**: 获取服务间调用的JWT令牌（基于mTLS）

**请求头**:
```
X-Client-Certificate: {base64_client_cert}
```

**响应体**:
```json
{
  "code": 200,
  "message": "令牌获取成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "integration:read integration:write",
    "module_name": "device_monitoring"
  }
}
```

#### 6.1.2 验证集成请求
**端点**: `POST /api/v1/integration/auth/verify`  
**描述**: 验证集成请求的合法性和权限

**请求体**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "request_path": "/api/v1/integration/events",
  "request_method": "POST",
  "source_module": "device_monitoring"
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "验证通过",
  "data": {
    "valid": true,
    "module_name": "device_monitoring",
    "permissions": ["integration:events:publish"],
    "expires_at": "2026-04-02T11:30:00Z"
  }
}
```

### 6.2 审计日志API

#### 6.2.1 查询集成审计日志
**端点**: `GET /api/v1/integration/audit/logs`  
**描述**: 查询集成系统的审计日志（需要审计员权限）

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| action | string | 否 | 操作类型: publish/subscribe/sync |
| module | string | 否 | 模块名称 |
| user_id | string | 否 | 用户ID |
| start_time | datetime | 是 | 开始时间 |
| end_time | datetime | 是 | 结束时间 |
| page | int | 否 | 页码 |

**响应体**:
```json
{
  "code": 200,
  "message": "日志查询成功",
  "data": [
    {
      "id": "log_123456",
      "timestamp": "2026-04-02T10:30:00Z",
      "action": "event_publish",
      "module": "device_monitoring",
      "user_id": "user_123",
      "resource": "event:DM-DEVICE-UPDATE-20260402103000123-ABC123",
      "status": "success",
      "ip_address": "10.0.1.100",
      "details": {
        "event_type": "entity_updated",
        "entity_type": "device"
      }
    }
  ]
}
```

## 7. API性能优化设计

### 7.1 批量操作支持
- **事件批量发布**: 单次请求最多100个事件
- **数据批量同步**: 支持大文件分片上传
- **并行处理**: 多个API请求并行处理
- **异步响应**: 长时间操作返回作业ID，轮询结果

### 7.2 缓存策略
| API端点 | 缓存策略 | TTL | 刷新机制 |
|---------|----------|-----|----------|
| GET /config | 内存缓存 | 5分钟 | 配置变更时失效 |
| GET /health | 内存缓存 | 30秒 | 定时刷新 |
| GET /metrics | Redis缓存 | 1分钟 | 指标更新时刷新 |
| GET /audit/logs | 不缓存 | - | 实时查询 |

### 7.3 压缩和分页
- **响应压缩**: 支持gzip/brotli压缩
- **分页优化**: 游标分页避免深度翻页性能问题
- **字段选择**: `fields`参数只返回必要字段
- **条件过滤**: 复杂过滤条件推送到数据库层

## 8. 监控和告警配置

### 8.1 API监控指标
| 指标名称 | 采集频率 | 告警阈值 | 告警级别 |
|----------|----------|----------|----------|
| API请求成功率 | 每1分钟 | < 99% | 严重 |
| API平均响应时间 | 每1分钟 | > 3000ms | 警告 |
| API错误率 | 每1分钟 | > 5% | 严重 |
| API请求量 | 每5分钟 | 突增100% | 警告 |
| API超时率 | 每1分钟 | > 10% | 严重 |

### 8.2 集成健康检查
- **就绪检查**: `GET /health/ready` - 服务是否就绪
- **存活检查**: `GET /health/live` - 服务是否存活
- **深度检查**: `GET /health/deep` - 检查所有依赖组件

### 8.3 告警通知渠道
- **紧急告警**: 短信 + 电话 + Slack
- **重要告警**: 邮件 + Slack + 企业微信
- **一般告警**: Slack + 系统内通知

## 9. 安全设计

### 9.1 认证授权矩阵
| API类别 | 认证方式 | 授权要求 | 审计级别 |
|---------|----------|----------|----------|
| 事件API | JWT + 服务证书 | 模块特定权限 | 详细审计 |
| 数据API | mTLS双向证书 | 服务间信任 | 操作审计 |
| 管理API | JWT + RBAC | 管理员角色 | 完整审计 |
| 诊断API | 内部Token | 运维人员 | 操作审计 |

### 9.2 输入验证
- **Schema验证**: JSON Schema严格验证所有输入
- **业务验证**: 业务规则引擎验证逻辑合法性
- **大小限制**: 请求体大小限制（JSON 10MB，文件1GB）
- **频率限制**: 基于令牌桶算法的API限流

### 9.3 数据保护
- **传输加密**: TLS 1.3 + 前向保密
- **敏感信息脱敏**: 日志中的敏感字段脱敏
- **访问日志**: 记录所有API访问，保留180天
- **防重放攻击**: 请求时间戳+随机数校验

## 10. 附录

### 10.1 OpenAPI规范文件位置
```
backend/docs/openapi/integration.yaml
backend/docs/openapi/integration.json
```

### 10.2 API客户端SDK
- **Python SDK**: `pip install nesom-integration-sdk`
- **JavaScript SDK**: `npm install @nesom/integration-sdk`
- **Java SDK**: Maven坐标 `com.nesom:integration-sdk:1.0.0`

### 10.3 API测试用例
```yaml
- name: 测试事件发布
  request:
    method: POST
    url: /api/v1/integration/events
    body:
      event_type: entity_updated
      source_module: device_monitoring
  expect:
    status_code: 200
    body:
      code: 200
      data.event_id: {type: string}

- name: 测试健康检查
  request:
    method: GET
    url: /api/v1/integration/health
  expect:
    status_code: 200
    body:
      data.overall_status: "healthy"
```

### 10.4 部署和配置
```yaml
# docker-compose.yml 集成API服务配置
integration-api:
  image: nesom/integration-api:1.0.0
  ports:
    - "8080:8080"
  environment:
    - DATABASE_URL=mysql://user:pass@mysql:3306/integration
    - REDIS_URL=redis://redis:6379
    - JWT_SECRET=${JWT_SECRET}
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health/live"]
    interval: 30s
    timeout: 5s
    retries: 3
```

---

**下一步**：
1. 评审本API设计
2. 生成OpenAPI规范文档
3. 开发API客户端SDK
4. 编写API集成测试用例

**评审人**: API架构师、安全工程师、各模块开发负责人  
**评审日期**: 2026-04-02
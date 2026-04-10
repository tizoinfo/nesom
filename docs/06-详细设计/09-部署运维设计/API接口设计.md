# 部署运维设计 - API接口详细设计

**版本**: 1.0  
**日期**: 2026-04-02  
**作者**: 工作流架构师  
**状态**: Draft  
**审核状态**: 待评审  
**继承自**: 概要设计-部署架构设计.md (运维API部分)  
**实际代码参考**: backend/src/api/v1/operations/ 目录下的运维API  
**数据库模型**: environments, deployment_configs, deployment_history等表

## 1. 设计概述

### 1.1 设计目标
提供完整的NESOM系统部署运维管理API接口，支持多环境部署、监控告警、备份恢复、容量规划等核心运维功能，包括：
- 多环境部署配置和版本管理
- 自动化部署和回滚操作
- 监控数据查询和告警管理
- 备份策略和恢复操作
- 运维工单和变更管理
- 容量规划和性能优化

### 1.2 设计原则
1. **声明式API**：用户声明期望状态，系统自动实现
2. **幂等性**：相同请求多次执行结果一致
3. **异步操作**：长时间操作返回作业ID，支持轮询和回调
4. **安全优先**：严格的身份验证和授权控制
5. **可观测性**：每个API调用可追踪、可监控、可审计
6. **版本兼容**：支持API版本演进，保持向后兼容

### 1.3 技术约束
- **API网关**: Kong 3.4+ (OpenResty + Lua)
- **认证**: JWT + mTLS (服务间认证)
- **序列化**: JSON + Protobuf (高性能场景)
- **异步任务**: Celery 5.3 + Redis 7.0
- **实时通知**: WebSocket + Server-Sent Events
- **文档**: OpenAPI 3.0 + Swagger UI

### 1.4 API分类
| 类别 | 功能 | 协议 | 认证 | 典型场景 |
|------|------|------|------|----------|
| 环境管理 | 环境CRUD、状态查询 | HTTP/1.1 | JWT + RBAC | 环境初始化、状态监控 |
| 部署管理 | 配置管理、部署操作 | HTTP/1.1 | JWT + 审批流程 | 服务部署、版本升级 |
| 监控查询 | 指标查询、告警管理 | HTTP/1.1 + WebSocket | JWT | 监控仪表盘、告警处理 |
| 备份恢复 | 备份策略、恢复操作 | HTTP/1.1 | JWT + 特殊权限 | 数据备份、灾难恢复 |
| 运维工单 | 工单CRUD、流程管理 | HTTP/1.1 | JWT + 工作流 | 变更管理、事件处理 |
| 容量规划 | 资源分析、扩容建议 | HTTP/1.1 | JWT | 容量分析、规划决策 |

## 2. 通用设计规范

### 2.1 请求/响应格式

#### 2.1.1 标准请求头
```http
Authorization: Bearer {jwt_token}
X-Request-ID: {uuid}
X-Client-Version: 1.0.0
X-Client-Module: {module_name}
Content-Type: application/json
Accept: application/json
X-Async-Callback: {callback_url}  # 异步操作回调地址（可选）
```

#### 2.1.2 同步成功响应
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},
  "meta": {
    "request_id": "req_123",
    "timestamp": "2026-04-02T10:30:00Z",
    "version": "1.0"
  }
}
```

#### 2.1.3 异步操作响应
```json
{
  "code": 202,
  "message": "操作已接受，正在处理",
  "data": {
    "job_id": "job_123456",
    "status_url": "/api/v1/operations/jobs/job_123456",
    "estimated_completion": "2026-04-02T10:35:00Z",
    "progress": 0
  }
}
```

#### 2.1.4 错误响应
```json
{
  "code": 400,
  "message": "请求参数错误",
  "errors": [
    {
      "field": "config_version",
      "code": "INVALID_FORMAT",
      "message": "版本号格式无效，应为v1.0.0格式"
    }
  ],
  "meta": {
    "request_id": "req_123",
    "timestamp": "2026-04-02T10:30:00Z",
    "documentation": "https://docs.nesom.com/errors/INVALID_FORMAT"
  }
}
```

### 2.2 错误码规范
| 错误码范围 | 类别 | 描述 |
|------------|------|------|
| 200-299 | 成功 | 请求成功处理 |
| 400-499 | 客户端错误 | 请求参数、认证、权限等问题 |
| 500-599 | 服务器错误 | 服务端处理失败 |
| 600-699 | 运维特定错误 | 部署运维相关错误 |

#### 2.2.1 运维特定错误码
| 错误码 | 错误常量 | 描述 |
|--------|----------|------|
| 600 | DEPLOYMENT_CONFIG_VALIDATION_FAILED | 部署配置验证失败 |
| 601 | DEPLOYMENT_EXECUTION_FAILED | 部署执行失败 |
| 602 | ENVIRONMENT_NOT_READY | 环境未就绪 |
| 603 | BACKUP_EXECUTION_FAILED | 备份执行失败 |
| 604 | RECOVERY_NOT_ALLOWED | 恢复操作不被允许 |
| 605 | MONITORING_DATA_UNAVAILABLE | 监控数据不可用 |
| 606 | CAPACITY_PLANNING_CALCULATION_FAILED | 容量规划计算失败 |
| 607 | OPERATION_TICKET_WORKFLOW_ERROR | 运维工单工作流错误 |

### 2.3 分页和排序
- **分页参数**: `page` (默认1), `page_size` (默认20, 最大1000)
- **游标分页**: `cursor` + `limit` (用于时间序列数据)
- **排序参数**: `sort` (字段名), `order` (asc/desc)
- **字段选择**: `fields` (逗号分隔的字段列表)

### 2.4 异步操作处理
```yaml
# 异步操作状态流转
async_operation_states:
  pending: "操作已接受，等待执行"
  scheduled: "已调度，等待资源"
  running: "正在执行"
  succeeded: "执行成功"
  failed: "执行失败"
  cancelled: "已取消"
  retrying: "重试中"

# 进度报告
progress_report:
  format: "0-100百分比"
  update_frequency: "每10秒"
  notification: "状态变更时发送"
```

## 3. 环境管理API

### 3.1 环境管理接口

#### 3.1.1 获取环境列表
**端点**: `GET /api/v1/operations/environments`  
**描述**: 查询环境列表，支持过滤和分页

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| env_type | string | 否 | 环境类型过滤 |
| status | string | 否 | 环境状态过滤 |
| region | string | 否 | 区域过滤 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "id": "env_123456",
      "env_id": "prod",
      "env_name": "生产环境",
      "env_type": "production",
      "region": "cn-east-1",
      "status": "active",
      "health_status": "healthy",
      "created_at": "2026-04-01T08:00:00Z",
      "updated_at": "2026-04-02T10:30:00Z",
      "tags": {"criticality": "high", "team": "platform"}
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

#### 3.1.2 获取环境详情
**端点**: `GET /api/v1/operations/environments/{env_id}`  
**描述**: 获取指定环境的详细信息

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| env_id | string | 是 | 环境ID |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "id": "env_123456",
    "env_id": "prod",
    "env_name": "生产环境",
    "env_type": "production",
    "description": "线上生产环境，服务真实用户",
    "region": "cn-east-1",
    "availability_zone": "cn-east-1a",
    "network_cidr": "10.0.0.0/16",
    "vpc_id": "vpc-123456",
    "k8s_cluster_name": "nesom-prod-cluster",
    "status": "active",
    "health_status": "healthy",
    "last_health_check": "2026-04-02T10:30:00Z",
    "resources": {
      "nodes": 10,
      "pods": 150,
      "services": 25
    },
    "metrics": {
      "cpu_usage": "45%",
      "memory_usage": "68%",
      "disk_usage": "52%"
    },
    "tags": {"criticality": "high", "team": "platform"},
    "metadata": {
      "created_by": "admin",
      "created_at": "2026-04-01T08:00:00Z",
      "updated_at": "2026-04-02T10:30:00Z"
    }
  }
}
```

#### 3.1.3 创建环境
**端点**: `POST /api/v1/operations/environments`  
**描述**: 创建新的环境（需要管理员权限）

**请求体**:
```json
{
  "env_id": "staging-2",
  "env_name": "预发布环境2",
  "env_type": "staging",
  "description": "新的预发布测试环境",
  "region": "cn-east-1",
  "availability_zone": "cn-east-1b",
  "network_cidr": "10.1.0.0/16",
  "vpc_id": "vpc-789012",
  "tags": {"purpose": "testing", "team": "qa"},
  "configuration": {
    "k8s_version": "1.28",
    "node_count": 3,
    "node_type": "c6a.large",
    "storage_class": "gp3"
  }
}
```

**响应体** (异步):
```json
{
  "code": 202,
  "message": "环境创建任务已提交",
  "data": {
    "job_id": "env_create_123456",
    "status_url": "/api/v1/operations/jobs/env_create_123456",
    "estimated_completion": "2026-04-02T11:30:00Z",
    "progress": 0
  }
}
```

#### 3.1.4 环境健康检查
**端点**: `POST /api/v1/operations/environments/{env_id}/health-check`  
**描述**: 触发环境健康检查

**响应体**:
```json
{
  "code": 200,
  "message": "健康检查已触发",
  "data": {
    "check_id": "health_check_123",
    "started_at": "2026-04-02T10:30:00Z",
    "components": [
      {"name": "kubernetes", "status": "healthy"},
      {"name": "networking", "status": "healthy"},
      {"name": "storage", "status": "warning", "details": "磁盘使用率85%"},
      {"name": "database", "status": "healthy"}
    ],
    "overall_status": "warning",
    "recommendations": ["考虑扩容存储"]
  }
}
```

## 4. 部署管理API

### 4.1 部署配置管理

#### 4.1.1 获取部署配置列表
**端点**: `GET /api/v1/operations/deployments/configs`  
**描述**: 查询部署配置列表

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| environment_id | string | 否 | 环境ID过滤 |
| service_name | string | 否 | 服务名称过滤 |
| is_active | boolean | 否 | 是否激活过滤 |
| config_type | string | 否 | 配置类型过滤 |
| page | int | 否 | 页码 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "config_id": "device-monitoring-prod-v1.2.0",
      "service_name": "device-monitoring",
      "environment_id": "prod",
      "config_version": "v1.2.0",
      "config_type": "kubernetes",
      "is_active": true,
      "deployed_at": "2026-04-01T20:00:00Z",
      "deployed_by": "ci-cd-pipeline",
      "summary": {
        "replicas": 3,
        "cpu_limit": "1000m",
        "memory_limit": "2Gi",
        "image": "nesom/device-monitoring:1.2.0"
      }
    }
  ]
}
```

#### 4.1.2 创建部署配置
**端点**: `POST /api/v1/operations/deployments/configs`  
**描述**: 创建新的部署配置

**请求体**:
```json
{
  "service_name": "device-monitoring",
  "environment_id": "prod",
  "config_version": "v1.3.0",
  "config_type": "kubernetes",
  "config_content": {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {"name": "device-monitoring"},
    "spec": {
      "replicas": 3,
      "selector": {"matchLabels": {"app": "device-monitoring"}},
      "template": {
        "metadata": {"labels": {"app": "device-monitoring"}},
        "spec": {
          "containers": [{
            "name": "device-monitoring",
            "image": "nesom/device-monitoring:1.3.0",
            "resources": {
              "limits": {"cpu": "1000m", "memory": "2Gi"},
              "requests": {"cpu": "500m", "memory": "1Gi"}
            }
          }]
        }
      }
    }
  },
  "variables": {
    "LOG_LEVEL": "info",
    "DATABASE_URL": "$SECRET:database-url"
  },
  "dependencies": ["redis", "postgresql"],
  "health_check_config": {
    "liveness": {"path": "/health", "port": 8080},
    "readiness": {"path": "/ready", "port": 8080}
  },
  "rollback_from": "device-monitoring-prod-v1.2.0"
}
```

**响应体**:
```json
{
  "code": 201,
  "message": "部署配置创建成功",
  "data": {
    "config_id": "device-monitoring-prod-v1.3.0",
    "created_at": "2026-04-02T10:30:00Z",
    "validation_result": {
      "valid": true,
      "warnings": ["资源配置未设置安全上下文"],
      "suggestions": ["建议添加Pod安全上下文"]
    }
  }
}
```

#### 4.1.3 验证部署配置
**端点**: `POST /api/v1/operations/deployments/configs/validate`  
**描述**: 验证部署配置的合法性

**请求体**:
```json
{
  "config_content": {...},
  "environment_id": "prod",
  "config_type": "kubernetes"
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "配置验证完成",
  "data": {
    "valid": true,
    "errors": [],
    "warnings": [
      "未设置资源requests，可能导致Pod调度失败",
      "缺少Pod安全上下文配置"
    ],
    "suggestions": [
      "添加resources.requests配置",
      "添加securityContext配置"
    ],
    "estimated_resources": {
      "cpu": "3.0 cores",
      "memory": "6GiB",
      "storage": "10GiB"
    }
  }
}
```

### 4.2 部署操作管理

#### 4.2.1 执行部署
**端点**: `POST /api/v1/operations/deployments/execute`  
**描述**: 执行服务部署（生产环境需要审批）

**请求体**:
```json
{
  "config_id": "device-monitoring-prod-v1.3.0",
  "deployment_type": "upgrade",
  "strategy": "rolling_update",
  "parameters": {
    "max_unavailable": "25%",
    "max_surge": "25%",
    "timeout_seconds": 600
  },
  "notifications": {
    "on_start": ["slack:#deployments"],
    "on_success": ["slack:#deployments", "email:team@nesom.com"],
    "on_failure": ["slack:#alerts", "sms:+8613800138000"]
  },
  "approval_required": true,
  "approval_comment": "版本1.3.0包含性能优化和bug修复"
}
```

**响应体** (需要审批时):
```json
{
  "code": 202,
  "message": "部署需要审批",
  "data": {
    "deployment_id": "DEP-prod-20260402103000123-ABC123",
    "approval_id": "APPROVAL-123456",
    "approval_url": "/api/v1/operations/approvals/APPROVAL-123456",
    "approvers": ["admin1", "admin2"],
    "status": "pending_approval"
  }
}
```

**响应体** (直接执行时):
```json
{
  "code": 202,
  "message": "部署任务已提交",
  "data": {
    "deployment_id": "DEP-prod-20260402103000123-ABC123",
    "status_url": "/api/v1/operations/deployments/DEP-prod-20260402103000123-ABC123",
    "estimated_completion": "2026-04-02T10:35:00Z",
    "progress": 0
  }
}
```

#### 4.2.2 查询部署状态
**端点**: `GET /api/v1/operations/deployments/{deployment_id}`  
**描述**: 查询部署任务状态和详情

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "deployment_id": "DEP-prod-20260402103000123-ABC123",
    "service_name": "device-monitoring",
    "environment_id": "prod",
    "config_id": "device-monitoring-prod-v1.3.0",
    "deployment_type": "upgrade",
    "status": "in_progress",
    "progress": 60,
    "started_at": "2026-04-02T10:30:00Z",
    "estimated_completion": "2026-04-02T10:35:00Z",
    "current_step": "更新Pod 2/3",
    "steps": [
      {"name": "验证配置", "status": "completed", "duration": "5s"},
      {"name": "创建新ReplicaSet", "status": "completed", "duration": "10s"},
      {"name": "滚动更新Pod", "status": "in_progress", "duration": "30s", "details": "更新Pod 2/3"},
      {"name": "健康检查", "status": "pending"},
      {"name": "清理旧资源", "status": "pending"}
    ],
    "metrics": {
      "old_version": "v1.2.0",
      "new_version": "v1.3.0",
      "pods_updated": 2,
      "pods_total": 3,
      "errors": 0
    },
    "logs_url": "/api/v1/operations/deployments/DEP-prod-20260402103000123-ABC123/logs"
  }
}
```

#### 4.2.3 执行回滚
**端点**: `POST /api/v1/operations/deployments/{deployment_id}/rollback`  
**描述**: 回滚失败的部署

**请求体**:
```json
{
  "reason": "新版本导致内存泄漏",
  "target_config_id": "device-monitoring-prod-v1.2.0",
  "notifications": {
    "on_rollback": ["slack:#alerts", "email:team@nesom.com"]
  }
}
```

**响应体**:
```json
{
  "code": 202,
  "message": "回滚任务已提交",
  "data": {
    "rollback_id": "ROLLBACK-123456",
    "deployment_id": "DEP-prod-20260402103000123-ABC123",
    "status_url": "/api/v1/operations/deployments/rollbacks/ROLLBACK-123456",
    "estimated_completion": "2026-04-02T10:40:00Z"
  }
}
```

### 4.3 部署历史查询

#### 4.3.1 查询部署历史
**端点**: `GET /api/v1/operations/deployments/history`  
**描述**: 查询部署历史记录

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| environment_id | string | 否 | 环境ID过滤 |
| service_name | string | 否 | 服务名称过滤 |
| status | string | 否 | 状态过滤 |
| start_time | datetime | 否 | 开始时间(ISO8601) |
| end_time | datetime | 否 | 结束时间(ISO8601) |
| deployment_type | string | 否 | 部署类型过滤 |
| page | int | 否 | 页码 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "deployment_id": "DEP-prod-20260402103000123-ABC123",
      "service_name": "device-monitoring",
      "environment_id": "prod",
      "deployment_type": "upgrade",
      "status": "succeeded",
      "initiated_by": "ci-cd-pipeline",
      "initiated_at": "2026-04-02T10:30:00Z",
      "completed_at": "2026-04-02T10:35:00Z",
      "duration_seconds": 300,
      "previous_version": "v1.2.0",
      "target_version": "v1.3.0",
      "metrics": {
        "pods_updated": 3,
        "errors": 0,
        "downtime_seconds": 0
      }
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 150,
      "total_pages": 8
    },
    "summary": {
      "total_deployments": 150,
      "success_rate": "98.7%",
      "average_duration": "245s",
      "recent_failures": 2
    }
  }
}
```

## 5. 监控查询API

### 5.1 指标数据查询

#### 5.1.1 查询实时指标
**端点**: `GET /api/v1/operations/metrics/query`  
**描述**: 查询监控指标数据

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| environment_id | string | 是 | 环境ID |
| service_name | string | 否 | 服务名称 |
| metric_name | string | 是 | 指标名称 |
| start_time | datetime | 是 | 开始时间(ISO8601) |
| end_time | datetime | 是 | 结束时间(ISO8601) |
| interval | string | 否 | 聚合间隔: 1m/5m/1h/1d |
| aggregation | string | 否 | 聚合函数: avg/max/min/sum/count |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "metric": "cpu_usage_percent",
    "unit": "%",
    "data": [
      {"timestamp": "2026-04-02T10:00:00Z", "value": 45.2},
      {"timestamp": "2026-04-02T10:05:00Z", "value": 47.8},
      {"timestamp": "2026-04-02T10:10:00Z", "value": 52.1},
      {"timestamp": "2026-04-02T10:15:00Z", "value": 48.9}
    ],
    "statistics": {
      "min": 45.2,
      "max": 52.1,
      "avg": 48.5,
      "current": 48.9
    },
    "thresholds": {
      "warning": 70,
      "critical": 85
    }
  }
}
```

#### 5.1.2 WebSocket实时指标流
**端点**: `GET /api/v1/operations/metrics/stream`  
**描述**: 通过WebSocket获取实时指标数据流

**连接参数**:
```
ws://operations.internal/api/v1/operations/metrics/stream
?environment_id=prod
&service_name=device-monitoring
&metric_names=cpu_usage_percent,memory_usage_bytes
&interval=5s
&token={jwt_token}
```

**消息格式**:
```json
{
  "type": "metric_update",
  "timestamp": "2026-04-02T10:30:00Z",
  "data": {
    "cpu_usage_percent": 48.9,
    "memory_usage_bytes": 1073741824
  }
}
```

### 5.2 告警管理

#### 5.2.1 查询活动告警
**端点**: `GET /api/v1/operations/alerts`  
**描述**: 查询当前活动告警

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| environment_id | string | 否 | 环境ID过滤 |
| service_name | string | 否 | 服务名称过滤 |
| severity | string | 否 | 严重程度过滤 |
| status | string | 否 | 状态过滤（默认firing） |
| page | int | 否 | 页码 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "alert_id": "ALERT-20260402103000123-ABC123",
      "alert_name": "设备监控服务CPU使用率高",
      "environment_id": "prod",
      "service_name": "device-monitoring",
      "severity": "warning",
      "status": "firing",
      "start_time": "2026-04-02T10:25:00Z",
      "duration_seconds": 300,
      "labels": {
        "service": "device-monitoring",
        "instance": "device-monitoring-7f6d5c8b9",
        "severity": "warning"
      },
      "annotations": {
        "summary": "设备监控服务CPU使用率持续高于70%",
        "description": "CPU使用率: 75.2%，阈值: 70%",
        "value": "75.2%"
      },
      "acknowledged": false,
      "acknowledged_by": null
    }
  ],
  "meta": {
    "summary": {
      "total_alerts": 5,
      "by_severity": {"critical": 1, "warning": 4},
      "by_service": {"device-monitoring": 2, "data-collection": 3}
    }
  }
}
```

#### 5.2.2 确认告警
**端点**: `POST /api/v1/operations/alerts/{alert_id}/acknowledge`  
**描述**: 确认告警（表示已关注）

**请求体**:
```json
{
  "comment": "已收到告警，正在调查",
  "expected_resolution_time": "2026-04-02T11:30:00Z"
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "告警已确认",
  "data": {
    "alert_id": "ALERT-20260402103000123-ABC123",
    "acknowledged_at": "2026-04-02T10:30:00Z",
    "acknowledged_by": "user_123",
    "comment": "已收到告警，正在调查",
    "expected_resolution_time": "2026-04-02T11:30:00Z"
  }
}
```

#### 5.2.3 解决告警
**端点**: `POST /api/v1/operations/alerts/{alert_id}/resolve`  
**描述**: 标记告警为已解决

**请求体**:
```json
{
  "resolution_notes": "已扩容服务实例，CPU使用率恢复正常",
  "root_cause": "服务实例数不足导致负载过高",
  "preventive_actions": ["设置自动扩缩容", "优化查询性能"]
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "告警已解决",
  "data": {
    "alert_id": "ALERT-20260402103000123-ABC123",
    "resolved_at": "2026-04-02T10:35:00Z",
    "resolved_by": "user_123",
    "resolution_notes": "已扩容服务实例，CPU使用率恢复正常",
    "root_cause": "服务实例数不足导致负载过高",
    "preventive_actions": ["设置自动扩缩容", "优化查询性能"],
    "total_duration_seconds": 600
  }
}
```

### 5.3 监控配置管理

#### 5.3.1 创建监控规则
**端点**: `POST /api/v1/operations/monitoring/rules`  
**描述**: 创建监控告警规则

**请求体**:
```json
{
  "rule_name": "设备监控服务内存使用率高",
  "environment_id": "prod",
  "service_name": "device-monitoring",
  "rule_type": "metric_threshold",
  "metric_name": "memory_usage_percent",
  "condition": {
    "operator": ">",
    "value": 80,
    "for_duration": "5m"
  },
  "severity": "warning",
  "evaluation_interval": "60s",
  "notification_channels": [
    {
      "type": "slack",
      "config": {"channel": "#alerts", "mention": "@oncall"}
    },
    {
      "type": "email",
      "config": {"recipients": ["team@nesom.com"]}
    }
  ],
  "labels": {
    "service": "device-monitoring",
    "severity": "warning"
  },
  "annotations": {
    "summary": "{{$labels.service}}内存使用率过高",
    "description": "{{$labels.service}}内存使用率为{{$value}}%，超过阈值{{$threshold}}%"
  },
  "enabled": true
}
```

**响应体**:
```json
{
  "code": 201,
  "message": "监控规则创建成功",
  "data": {
    "rule_id": "metric_threshold-memory_usage_percent-prod-001",
    "created_at": "2026-04-02T10:30:00Z",
    "validation_result": {
      "valid": true,
      "promql": "memory_usage_percent{environment=\"prod\",service=\"device-monitoring\"} > 80"
    }
  }
}
```

## 6. 备份恢复API

### 6.1 备份管理

#### 6.1.1 创建备份策略
**端点**: `POST /api/v1/operations/backup/policies`  
**描述**: 创建备份策略

**请求体**:
```json
{
  "policy_name": "设备监控数据库每日备份",
  "environment_id": "prod",
  "service_name": "device-monitoring-db",
  "backup_type": "full",
  "data_source": {
    "type": "postgresql",
    "host": "postgres-prod.internal",
    "port": 5432,
    "database": "device_monitoring",
    "username": "$SECRET:backup-user"
  },
  "schedule": {
    "type": "cron",
    "expression": "0 2 * * *",
    "timezone": "Asia/Shanghai"
  },
  "retention_policy": {
    "daily": 7,
    "weekly": 4,
    "monthly": 12,
    "yearly": 3
  },
  "storage_location": {
    "type": "s3",
    "bucket": "nesom-backups",
    "path": "prod/device-monitoring-db/",
    "region": "cn-east-1"
  },
  "encryption_config": {
    "enabled": true,
    "algorithm": "AES-256-GCM",
    "key_id": "kms-key-123"
  },
  "compression_config": {
    "enabled": true,
    "algorithm": "zstd",
    "level": 3
  },
  "verification_policy": {
    "enabled": true,
    "method": "checksum",
    "schedule": "after_backup"
  },
  "enabled": true
}
```

**响应体**:
```json
{
  "code": 201,
  "message": "备份策略创建成功",
  "data": {
    "policy_id": "BACKUP-prod-device-monitoring-db-001",
    "next_execution": "2026-04-03T02:00:00Z",
    "estimated_size": "50GB",
    "estimated_duration": "30分钟"
  }
}
```

#### 6.1.2 触发即时备份
**端点**: `POST /api/v1/operations/backup/execute`  
**描述**: 立即触发备份执行

**请求体**:
```json
{
  "policy_id": "BACKUP-prod-device-monitoring-db-001",
  "backup_type": "full",
  "retention_override": {
    "expiry_days": 30
  },
  "notifications": {
    "on_completion": ["slack:#backups", "email:dba@nesom.com"]
  }
}
```

**响应体** (异步):
```json
{
  "code": 202,
  "message": "备份任务已提交",
  "data": {
    "backup_id": "BACKUP-20260402103000123-ABC123",
    "status_url": "/api/v1/operations/backup/backups/BACKUP-20260402103000123-ABC123",
    "estimated_completion": "2026-04-02T11:00:00Z",
    "progress": 0
  }
}
```

#### 6.1.3 查询备份状态
**端点**: `GET /api/v1/operations/backup/backups/{backup_id}`  
**描述**: 查询备份任务状态

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "backup_id": "BACKUP-20260402103000123-ABC123",
    "policy_id": "BACKUP-prod-device-monitoring-db-001",
    "environment_id": "prod",
    "service_name": "device-monitoring-db",
    "backup_type": "full",
    "status": "in_progress",
    "progress": 65,
    "start_time": "2026-04-02T10:30:00Z",
    "estimated_completion": "2026-04-02T11:00:00Z",
    "current_step": "上传到S3存储",
    "metrics": {
      "data_size": "45GB",
      "backup_size": "15GB",
      "compression_ratio": "3:1",
      "transfer_rate": "100MB/s"
    },
    "storage_location": "s3://nesom-backups/prod/device-monitoring-db/2026-04-02/",
    "verification_status": "pending"
  }
}
```

### 6.2 恢复管理

#### 6.2.1 查询可恢复的备份
**端点**: `GET /api/v1/operations/recovery/available-backups`  
**描述**: 查询可用于恢复的备份列表

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| environment_id | string | 是 | 环境ID |
| service_name | string | 是 | 服务名称 |
| backup_type | string | 否 | 备份类型过滤 |
| start_time | datetime | 否 | 开始时间 |
| end_time | datetime | 否 | 结束时间 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "backup_id": "BACKUP-20260401103000123-ABC123",
      "policy_id": "BACKUP-prod-device-monitoring-db-001",
      "backup_type": "full",
      "backup_time": "2026-04-01T02:00:00Z",
      "data_size": "48GB",
      "backup_size": "16GB",
      "compression_ratio": "3:1",
      "verification_status": "passed",
      "storage_location": "s3://nesom-backups/prod/device-monitoring-db/2026-04-01/",
      "metadata": {
        "database_version": "PostgreSQL 15.3",
        "tables_count": 25,
        "total_rows": "10M"
      }
    },
    {
      "backup_id": "BACKUP-20260331103000123-ABC123",
      "policy_id": "BACKUP-prod-device-monitoring-db-001",
      "backup_type": "full",
      "backup_time": "2026-03-31T02:00:00Z",
      "data_size": "47GB",
      "backup_size": "15.5GB",
      "compression_ratio": "3:1",
      "verification_status": "passed",
      "storage_location": "s3://nesom-backups/prod/device-monitoring-db/2026-03-31/",
      "metadata": {
        "database_version": "PostgreSQL 15.3",
        "tables_count": 25,
        "total_rows": "9.8M"
      }
    }
  ]
}
```

#### 6.2.2 执行恢复操作
**端点**: `POST /api/v1/operations/recovery/execute`  
**描述**: 执行数据恢复（生产环境需要审批）

**请求体**:
```json
{
  "backup_id": "BACKUP-20260401103000123-ABC123",
  "environment_id": "prod",
  "service_name": "device-monitoring-db",
  "recovery_type": "test",
  "recovery_reason": "验证备份可用性",
  "target_details": {
    "type": "temporary_instance",
    "instance_type": "db.r5.large",
    "storage_size": "100GB"
  },
  "verification_plan": {
    "data_integrity": true,
    "business_validation": true,
    "validation_queries": [
      "SELECT COUNT(*) FROM devices",
      "SELECT MAX(created_at) FROM device_metrics"
    ]
  },
  "approval_required": false,
  "notifications": {
    "on_start": ["slack:#backups"],
    "on_completion": ["slack:#backups", "email:dba@nesom.com"]
  }
}
```

**响应体** (异步):
```json
{
  "code": 202,
  "message": "恢复任务已提交",
  "data": {
    "recovery_id": "RECOVERY-20260402103000123-ABC123",
    "status_url": "/api/v1/operations/recovery/recoveries/RECOVERY-20260402103000123-ABC123",
    "estimated_completion": "2026-04-02T12:00:00Z",
    "progress": 0
  }
}
```

## 7. 运维工单API

### 7.1 工单管理

#### 7.1.1 创建运维工单
**端点**: `POST /api/v1/operations/tickets`  
**描述**: 创建运维工单

**请求体**:
```json
{
  "title": "生产环境设备监控服务扩容",
  "description": "由于业务增长，需要扩容设备监控服务实例数从3个增加到5个",
  "ticket_type": "change",
  "priority": "high",
  "environment_id": "prod",
  "service_name": "device-monitoring",
  "category": "capacity_management",
  "subcategory": "scale_up",
  "change_details": {
    "current_state": "3个实例，每个实例1CPU 2GB内存",
    "desired_state": "5个实例，每个实例1CPU 2GB内存",
    "impact_analysis": "预计提高处理能力66%，无数据丢失风险",
    "rollback_plan": "回滚到3个实例配置",
    "testing_plan": "在预发布环境验证扩容效果"
  },
  "attachments": [
    {
      "name": "容量分析报告.pdf",
      "url": "https://storage.nesom.com/reports/capacity-20260402.pdf"
    }
  ],
  "due_date": "2026-04-03T18:00:00Z"
}
```

**响应体**:
```json
{
  "code": 201,
  "message": "运维工单创建成功",
  "data": {
    "ticket_id": "TICKET-20260402-0001",
    "status": "new",
    "created_at": "2026-04-02T10:30:00Z",
    "sla_deadline": "2026-04-02T11:30:00Z",  // 高优先级1小时响应
    "approval_required": true,
    "next_steps": ["等待审批", "分配执行人"]
  }
}
```

#### 7.1.2 更新工单状态
**端点**: `PATCH /api/v1/operations/tickets/{ticket_id}`  
**描述**: 更新工单状态和工作日志

**请求体**:
```json
{
  "status": "in_progress",
  "assignee_id": "user_456",
  "assignee_name": "运维工程师张三",
  "work_logs": [
    {
      "timestamp": "2026-04-02T10:35:00Z",
      "action": "开始处理",
      "details": "分析扩容需求，准备执行计划",
      "user": "user_456"
    }
  ]
}
```

**响应体**:
```json
{
  "code": 200,
  "message": "工单更新成功",
  "data": {
    "ticket_id": "TICKET-20260402-0001",
    "status": "in_progress",
    "assignee": "运维工程师张三",
    "updated_at": "2026-04-02T10:35:00Z",
    "sla_status": "within_sla"
  }
}
```

#### 7.1.3 查询工单列表
**端点**: `GET /api/v1/operations/tickets`  
**描述**: 查询运维工单列表

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| status | string | 否 | 状态过滤 |
| priority | string | 否 | 优先级过滤 |
| environment_id | string | 否 | 环境ID过滤 |
| service_name | string | 否 | 服务名称过滤 |
| assignee_id | string | 否 | 受理人过滤 |
| ticket_type | string | 否 | 工单类型过滤 |
| created_start | datetime | 否 | 创建开始时间 |
| created_end | datetime | 否 | 创建结束时间 |
| page | int | 否 | 页码 |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "ticket_id": "TICKET-20260402-0001",
      "title": "生产环境设备监控服务扩容",
      "ticket_type": "change",
      "priority": "high",
      "status": "in_progress",
      "environment_id": "prod",
      "service_name": "device-monitoring",
      "requester_name": "业务负责人李四",
      "assignee_name": "运维工程师张三",
      "created_at": "2026-04-02T10:30:00Z",
      "due_date": "2026-04-03T18:00:00Z",
      "sla_status": "within_sla",
      "category": "capacity_management"
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 45,
      "total_pages": 3
    },
    "summary": {
      "by_status": {"new": 5, "in_progress": 15, "pending": 10, "resolved": 15},
      "by_priority": {"critical": 2, "high": 10, "medium": 25, "low": 8},
      "sla_compliance": "92.5%"
    }
  }
}
```

## 8. 容量规划API

### 8.1 容量分析

#### 8.1.1 查询容量使用情况
**端点**: `GET /api/v1/operations/capacity/usage`  
**描述**: 查询资源使用情况和趋势

**查询参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| environment_id | string | 是 | 环境ID |
| resource_type | string | 否 | 资源类型: cpu/memory/storage/network |
| service_name | string | 否 | 服务名称过滤 |
| time_range | string | 否 | 时间范围: 1h/24h/7d/30d |

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "environment_id": "prod",
    "analysis_time": "2026-04-02T10:30:00Z",
    "resource_summary": {
      "cpu": {"total": "40 cores", "used": "28.5 cores", "usage_percent": 71.3},
      "memory": {"total": "160GiB", "used": "112GiB", "usage_percent": 70.0},
      "storage": {"total": "5TiB", "used": "3.2TiB", "usage_percent": 64.0},
      "network": {"ingress": "2.5Gbps", "egress": "1.8Gbps"}
    },
    "top_consumers": [
      {
        "service_name": "device-monitoring",
        "cpu_usage": "4.2 cores",
        "memory_usage": "8GiB",
        "trend": "increasing",
        "growth_rate": "15%/月"
      },
      {
        "service_name": "data-collection",
        "cpu_usage": "3.8 cores",
        "memory_usage": "6GiB",
        "trend": "stable",
        "growth_rate": "5%/月"
      }
    ],
    "forecasts": {
      "3_month": {"cpu": "32 cores", "memory": "128GiB", "storage": "3.8TiB"},
      "6_month": {"cpu": "38 cores", "memory": "152GiB", "storage": "4.5TiB"},
      "12_month": {"cpu": "52 cores", "memory": "208GiB", "storage": "6.1TiB"}
    },
    "recommendations": [
      {
        "type": "scale_up",
        "resource": "cpu",
        "service": "device-monitoring",
        "reason": "使用率超过70%且增长趋势明显",
        "suggested_action": "扩容到6个实例或升级实例规格",
        "priority": "high"
      },
      {
        "type": "monitor",
        "resource": "storage",
        "service": "data-collection",
        "reason": "使用率64%，接近警告阈值",
        "suggested_action": "监控存储增长，准备扩容计划",
        "priority": "medium"
      }
    ]
  }
}
```

#### 8.1.2 生成容量规划报告
**端点**: `POST /api/v1/operations/capacity/reports/generate`  
**描述**: 生成容量规划报告

**请求体**:
```json
{
  "environment_id": "prod",
  "report_type": "quarterly",
  "time_range": {
    "start": "2026-01-01T00:00:00Z",
    "end": "2026-03-31T23:59:59Z"
  },
  "include_services": ["device-monitoring", "data-collection", "user-mgmt"],
  "analysis_depth": "detailed",
  "forecast_period": "12个月",
  "format": "pdf"
}
```

**响应体** (异步):
```json
{
  "code": 202,
  "message": "容量规划报告生成任务已提交",
  "data": {
    "report_id": "CAPACITY-REPORT-2026Q1",
    "status_url": "/api/v1/operations/capacity/reports/CAPACITY-REPORT-2026Q1",
    "estimated_completion": "2026-04-02T11:00:00Z",
    "delivery_methods": ["download", "email"]
  }
}
```

## 9. 作业管理API

### 9.1 作业状态查询

#### 9.1.1 查询作业状态
**端点**: `GET /api/v1/operations/jobs/{job_id}`  
**描述**: 查询异步作业状态

**响应体**:
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "job_id": "env_create_123456",
    "job_type": "environment_creation",
    "status": "running",
    "progress": 65,
    "created_at": "2026-04-02T10:30:00Z",
    "started_at": "2026-04-02T10:30:05Z",
    "updated_at": "2026-04-02T10:35:00Z",
    "estimated_completion": "2026-04-02T11:30:00Z",
    "current_step": "配置网络",
    "steps": [
      {"name": "初始化项目", "status": "completed", "duration": "30s"},
      {"name": "创建计算资源", "status": "completed", "duration": "2m"},
      {"name": "配置网络", "status": "in_progress", "duration": "2m30s"},
      {"name": "部署基础服务", "status": "pending"},
      {"name": "验证环境", "status": "pending"}
    ],
    "result": null,
    "error": null,
    "logs_url": "/api/v1/operations/jobs/env_create_123456/logs",
    "cancel_url": "/api/v1/operations/jobs/env_create_123456/cancel"
  }
}
```

#### 9.1.2 取消作业
**端点**: `POST /api/v1/operations/jobs/{job_id}/cancel`  
**描述**: 取消正在执行的作业

**响应体**:
```json
{
  "code": 200,
  "message": "作业取消请求已接受",
  "data": {
    "job_id": "env_create_123456",
    "status": "cancelling",
    "cancellation_reason": "用户请求取消",
    "cleanup_actions": ["释放已创建资源", "清理临时文件"]
  }
}
```

## 10. 安全设计

### 10.1 认证和授权

#### 10.1.1 权限矩阵
| API类别 | 所需权限 | 特殊要求 |
|---------|----------|----------|
| 环境管理 | operations:environments:read/write | 生产环境操作需要管理员权限 |
| 部署管理 | operations:deployments:read/write/execute | 生产部署需要审批流程 |
| 监控查询 | operations:metrics:read | 无特殊要求 |
| 备份恢复 | operations:backup:read/write/execute | 生产恢复需要DBA权限 |
| 运维工单 | operations:tickets:read/write/update | 工单状态变更需要受理人权限 |
| 容量规划 | operations:capacity:read | 无特殊要求 |

#### 10.1.2 审批流程
```yaml
# 生产环境操作审批流程
production_operations_approval:
  deployment:
    required: true
    approvers: ["platform-lead", "sre-lead"]
    quorum: 2
    timeout: "1小时"
    
  backup_restore:
    required: true
    approvers: ["dba-lead", "security-lead"]
    quorum: 2
    timeout: "2小时"
    
  environment_creation:
    required: true
    approvers: ["infrastructure-lead", "finance-lead"]
    quorum: 2
    timeout: "4小时"
```

### 10.2 审计日志

#### 10.2.1 审计事件记录
所有API调用自动记录审计日志，包括：
- 请求时间、调用者、IP地址
- 请求路径、方法、参数（敏感信息脱敏）
- 响应状态、处理时长
- 操作结果、错误信息（如果有）

#### 10.2.2 敏感操作告警
以下操作触发实时安全告警：
- 非工作时间的生产环境操作
- 批量删除操作
- 权限提升尝试
- 异常访问模式

## 11. 性能优化

### 11.1 缓存策略
| 数据类型 | 缓存位置 | TTL | 失效条件 |
|----------|----------|-----|----------|
| 环境配置 | Redis | 5分钟 | 环境配置变更 |
| 部署配置 | Redis | 10分钟 | 部署配置变更 |
| 监控规则 | 本地内存 | 1分钟 | 规则变更 |
| 容量数据 | Redis | 15分钟 | 定时刷新 |

### 11.2 批量操作支持
- **批量部署**: 单次请求部署多个服务
- **批量查询**: 单次查询多个指标
- **批量更新**: 单次更新多个配置
- **批量导出**: 导出大量数据时支持分页和流式传输

### 11.3 实时通知
- **WebSocket**: 实时推送部署状态、告警信息
- **Server-Sent Events**: 长轮询替代方案
- **Webhook回调**: 异步操作完成通知

## 12. 附录

### 12.1 OpenAPI规范位置
```
backend/docs/openapi/operations.yaml
backend/docs/openapi/operations.json
```

### 12.2 API客户端SDK
- **Python SDK**: `pip install nesom-operations-sdk`
- **JavaScript SDK**: `npm install @nesom/operations-sdk`
- **命令行工具**: `nesom-ops` (基于Python SDK)

### 12.3 监控指标
| 指标名称 | 采集频率 | 告警阈值 | 说明 |
|----------|----------|----------|------|
| API请求成功率 | 每分钟 | < 99% | API调用成功率 |
| API平均响应时间 | 每分钟 | > 1000ms | 平均响应时间 |
| 异步作业积压 | 每分钟 | > 100 | 待处理作业数 |
| 部署成功率 | 每小时 | < 95% | 部署成功比例 |
| 备份成功率 | 每天 | < 99% | 备份成功比例 |

### 12.4 部署配置
```yaml
# 运维API服务部署配置
operations-api:
  image: nesom/operations-api:1.0.0
  replicas: 3
  resources:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "1000m"
      memory: "2Gi"
  
  env:
    DATABASE_URL: mysql://operations:${DB_PASSWORD}@mysql:3306/operations
    REDIS_URL: redis://redis:6379
    JWT_SECRET: ${JWT_SECRET}
  
  healthcheck:
    path: /health
    interval: 30s
    timeout: 5s
  
  autoscaling:
    min: 3
    max: 10
    targetCPU: 70%
```

---

**下一步**：
1. 评审本API设计
2. 生成OpenAPI规范文档
3. 开发API客户端SDK
4. 编写API集成测试用例

**评审人**: API架构师、运维架构师、安全工程师  
**评审日期**: 2026-04-02
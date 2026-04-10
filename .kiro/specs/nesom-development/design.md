# NESOM 系统开发设计文档

## 概述

NESOM 系统采用前后端分离的模块化单体架构，基于已完成的详细设计文档进行实现。本设计文档汇总关键技术决策和实现要点，作为开发任务的参考。

## 架构

```
前端 (Vue 3 + TypeScript)
    ↓ HTTP/WebSocket
Nginx 反向代理
    ↓
后端 (FastAPI + Python 3.11)
    ↓
MySQL 8.0 + Redis 7.0 + MinIO
```

## 组件和接口

### 后端项目结构
```
backend/
├── src/
│   ├── main.py                 # FastAPI 应用入口
│   ├── core/
│   │   ├── config.py           # 配置管理 (pydantic-settings)
│   │   ├── security.py         # JWT 认证 (python-jose + passlib)
│   │   ├── middleware.py       # 中间件 (CORS, 日志, 请求ID)
│   │   └── exceptions.py      # 全局异常处理
│   ├── database/
│   │   ├── base.py             # SQLAlchemy 基础配置
│   │   └── session.py         # 数据库会话管理
│   ├── modules/
│   │   ├── auth/               # 用户权限管理模块
│   │   ├── device/             # 设备监控模块
│   │   ├── workorder/          # 工单管理模块
│   │   ├── sparepart/          # 备件管理模块
│   │   ├── inspection/         # 巡检管理模块
│   │   ├── report/             # 报表统计模块
│   │   └── system/             # 系统配置模块
│   └── shared/                 # 共享工具和基础类
├── alembic/                    # 数据库迁移
├── tests/                      # 测试文件
├── pyproject.toml
└── Dockerfile
```

### 前端项目结构
```
frontend/
├── src/
│   ├── main.ts                 # 应用入口
│   ├── App.vue
│   ├── router/                 # Vue Router 路由配置
│   ├── stores/                 # Pinia 状态管理
│   ├── api/                    # Axios API 封装
│   ├── views/                  # 页面组件
│   │   ├── auth/               # 登录/注册页面
│   │   ├── dashboard/          # 仪表盘
│   │   ├── device/             # 设备监控
│   │   ├── workorder/          # 工单管理
│   │   ├── sparepart/          # 备件管理
│   │   ├── inspection/         # 巡检管理
│   │   ├── report/             # 报表统计
│   │   └── system/             # 系统配置
│   ├── components/             # 公共组件
│   ├── utils/                  # 工具函数
│   └── types/                  # TypeScript 类型定义
├── package.json
├── vite.config.ts
└── Dockerfile
```

## 数据模型

核心数据模型已在各模块的数据库设计文档中详细定义，包括：
- `users`, `roles`, `permissions`, `user_roles`, `role_permissions` - 用户权限
- `devices`, `device_types`, `device_metrics`, `device_alerts` - 设备监控
- `work_orders`, `work_order_details`, `work_order_status_history` - 工单管理
- `spare_parts`, `inventory_transactions`, `warehouses` - 备件管理
- `inspection_plans`, `inspection_tasks`, `inspection_results` - 巡检管理

## 正确性属性

*属性是在系统所有有效执行中应该成立的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：JWT 令牌轮换
*对于任意* 有效的刷新令牌，使用它获取新的访问令牌后，旧的刷新令牌应该失效（轮换机制）
**验证：需求 2.4**

### 属性 2：库存操作原子性
*对于任意* 库存出库操作，如果操作失败，库存数量应该保持不变（事务回滚）
**验证：需求 5.4**

### 属性 3：工单状态机合法性
*对于任意* 工单状态变更，只有在状态机允许的转换路径上才能成功执行
**验证：需求 4.2**

### 属性 4：设备离线检测
*对于任意* 设备，如果其最后心跳时间超过 5 分钟，系统应该将其标记为离线状态
**验证：需求 3.2**

### 属性 5：权限最小化
*对于任意* API 请求，用户只能访问其角色权限范围内的资源
**验证：需求 2.3**

## 错误处理

所有 API 使用统一的错误响应格式：
```json
{
  "code": 400,
  "message": "错误描述",
  "detail": {"field": "字段名", "error": "具体错误"}
}
```

HTTP 状态码映射：
- 200/201/204：成功
- 400：请求参数错误
- 401：未认证
- 403：权限不足
- 404：资源不存在
- 409：资源冲突
- 422：业务规则验证失败
- 500：服务器内部错误

## 测试策略

### 单元测试
- 使用 pytest 测试后端业务逻辑
- 使用 Vitest 测试前端组件
- 重点测试状态机、权限验证、数据验证逻辑

### 属性测试
- 使用 Hypothesis (Python) 进行属性测试
- 测试库存操作的原子性
- 测试工单状态机的合法性
- 测试 JWT 令牌的安全属性

### 集成测试
- 使用 httpx 测试 API 端点
- 测试数据库事务和回滚
- 测试 WebSocket 实时推送
